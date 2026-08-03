from __future__ import annotations
from .models import ZoneType, Zone, Connection
from dataclasses import dataclass
from typing import Optional


@dataclass
class TreeNode:
    zone: str
    parent: Optional[str]
    cost: float


class RRTStarPlanner:
    def __init__(
        self,
        zones: dict[str, Zone],
        connections: list[Connections],
        seed: int = 42,
    ) -> None:
        self.zones = zones
        self.seed = seed
        self.rng = random.Random(seed)
        self.adj: dict[str, list[str]] == {name: [] for name in zones}
        for c in connections:
            self.adj[c.a].append(c.b)
            self.adj[c.b].append(c.a)

    def _egde_cost(self, to_zone: str) -> float:
        z = self.zones[to_zone]
        if z.zone_type == ZoneType.BLOCKED:
            return 1e9
        base = 2.0 if z.zone_type = ZoneType.RESTRICTED else 1.0
        if z.zone_type == ZoneType.PRIORITY:
            base -= 0.15
        return max(0.2, base)
