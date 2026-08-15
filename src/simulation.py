from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import Connection, Drone, Zone, ZoneType
from .planner_rrt_star import RRTStarPlanner


@dataclass
class Move:
    drone_id: int
    token: str


class Simulation:
    def __init__(
        self,
        zones: dict[str, Zone],
        connections: list[Connection],
        start_hub: str,
        end_hub: str,
        num_drones: int,
        planner: RRTStarPlanner,
    ) -> None:
        self.zones = zones
        self.connections = connections
        self.start = start_hub
        self.end = end_hub
        self.num_drones = num_drones
        self.planner = planner

        self.edge_caps: dict[tuple[str, str], int] = {
            c.key(): c.max_link_capacity for c in connections
        }
        self.turn = 0
        self.drones: list[Drone] = [
            Drone(drone_id=i + 1, current_zone=start_hub)
            for i in range(num_drones)
        ]
        self.paths: dict[int, list[str]] = {}
        self.path_index: dict[int, int] = {}

        self._init_paths()
        print(f"DEBUG: paths={self.paths})

    def _init_paths(self) -> None:
        for d in self.drones:
            p = self.planner.plan(self.start, self.end)
            if not p:
                raise ValueError(
                    f"No path found from '{self.start}' to '{self.end}'"
                )
            self.paths[d.drone_id] = p
            self.path_index[d.drone_id] = 0

    def _zone_occ(self) -> dict[str, int]:
        occ: dict[str, int] = {z: 0 for z in self.zones}
        for d in self.drones:
            if d.delivered or d.in_transit:
                continue
            occ[d.current_zone] += 1
        return occ

    def _can_enter(
        self,
        zone_name: str,
        planned_in: int,
        occ_after_out: dict[str, int]
    ) -> bool:
        z = self.zones[zone_name]
        if z.is_unbounded:
            return True
        cap = z.max_drones if z.max_drones is not None else 1
        return occ_after_out.get(zone_name, 0) + planned_in <= cap

    def _next_zone_for(self, d: Drone) -> Optional[str]:
        p = self.paths[d.drone_id]
        i = self.path_index[d.drone_id]
        if i >= len(p) - 1:
            return None
        return p[i + 1]

    def _reroute(self, d: Drone) -> None:
        p = self.planner.plan(d.current_zone, self.end)
        if p:
            self.paths[d.drone_id] = p
            self.path_index[d.drone_id] = 0

    def step(self) -> list[str]:
        self.turn += 1
        moves: list[Move] = []
        just_arrived: set[int] = set()

        for d in self.drones:
            if not d.in_transit:
                continue
            d.transit_remaining -= 1
            if d.transit_remaining == 0 and d.transit_to is not None:
                d.current_zone = d.transit_to
                d.in_transit = False
                d.transit_from = None
                d.transit_to = None
                just_arrived.add(d.drone_id)
                if d.current_zone == self.end:
                    d.delivered = True
                else:
                    self.path_index[d.drone_id] += 1
                    moves.append(Move(d.drone_id, d.current_zone))

        occ = self._zone_occ()

        leaving: dict[str, int] = {z: 0 for z in self.zones}
        intentions: list[tuple[Drone, str]] = []

        for d in self.drones:
            if d.delivered or d.in_transit or d.drone_id in just_arrived:
                continue
            nxt = self._next_zone_for(d)
            if nxt is None:
                if d.current_zone == self.end:
                    d.delivered = True
                continue
            intentions.append((d, nxt))
            leaving[d.current_zone] += 1
        edge_use: dict[tuple[str, str], int] = {}
        planned_in: dict[str, int] = {z: 0 for z in self.zones}
        planned_out: dict[str, int] = {z: 0 for z in self.zones}
        for d, nxt in intentions:
            if self.zones[nxt].zone_type == ZoneType.BLOCKED:
                self._reroute(d)
                continue
            edge = tuple(sorted((d.current_zone, nxt)))
            cap = self.edge_caps.get(edge, 1)
            if edge_use.get(edge, 0) >= cap:
                continue
            current_occ_here = occ.get(nxt, 0) - planned_out.get(nxt, 0)
            if not self._can_enter(
                nxt, planned_in.get(nxt, 0) + 1,
                {**occ, nxt: current_occ_here}
            ):
                continue
            edge_use[edge] = edge_use.get(edge, 0) + 1
            planned_in[nxt] = planned_in.get(nxt, 0) + 1
            planned_out[d.current_zone] = planned_out.get(d.current_zone, 0) + 1
            cost = self.zones[nxt].move_cost
            if cost == 1:
                d.current_zone = nxt
                self.path_index[d.drone_id] += 1
                if nxt == self.end:
                    d.delivered = True
                moves.append(Move(d.drone_id, nxt))
            elif cost == 2:
                d.in_transit = True
                d.transit_from = d.current_zone
                d.transit_to = nxt
                d.transit_remaining = 2
                moves.append(
                    Move(d.drone_id, f"{d.current_zone}-{nxt}")
                )
            moves.sort(key=lambda m: m.drone_id)
        return [f"D{m.drone_id}-{m.token}" for m in moves]

    def all_delivered(self) -> bool:
        return all(d.delivered for d in self.drones)

    def run(self, max_turns: int = 10000) -> list[str]:
        log: list[str] = []
        stagnation = 0
        while not self.all_delivered() and self.turn < max_turns:
            line = self.step()
            if line:
                log.append(" ".join(line))
                stagnation = 0
            else:
                log.append("")
                stagnation += 1
                if stagnation > 50:
                    raise RuntimeError(
                        "Simulation stalled (possible deadlock)"
                    )
        if not self.all_delivered():
            raise RuntimeError("Simulation exceeded max turns")
        return log

    def get_drone_position(
        self,
        drone_id: int
    ) -> Optional[tuple[int, int]]:
        for d in self.drones:
            if d.drone_id != drone_id:
                continue
            if (
                d.in_transit
                and d.transit_from is not None
                and d.transit_to is not None
            ):
                a = self.zones[d.transit_from]
                b = self.zones[d.transit_to]
                total = 2
                prog = (total - d.transit_remaining) / total
                x = a.x + (b.x - a.x) * prog
                y = a.y + (b.y - a.y) * prog
                return (round(x), round(y))
            z = self.zones[d.current_zone]
            return (z.x, z.y)
        return None
