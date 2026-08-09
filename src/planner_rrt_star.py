from __future__ import annotations
from .models import ZoneType, Zone, Connection
from dataclasses import dataclass
from typing import Optional
import random

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
        self.adj: dict[str, list[str]] = {name: [] for name in zones}
        for c in connections:
            self.adj[c.a].append(c.b)
            self.adj[c.b].append(c.a)

    def _edge_cost(self, to_zone: str) -> float:
        z = self.zones[to_zone]
        if z.zone_type == ZoneType.BLOCKED:
            return 1e9
        base = 2.0 if z.zone_type == ZoneType.RESTRICTED else 1.0
        if z.zone_type == ZoneType.PRIORITY:
            base -= 0.15
        return max(0.2, base)

    def _dist(self, a: str, b: str) -> float:
        za = self.zones[a]
        zb = self.zones[b]
        dx = za.x - zb.x
        dy = za.y - zb.y
        return (dx * dx + dy * dy) ** 0.5

    def _nearest(self, tree: dict[str, TreeNode], sample: str) -> str:
        best = None
        bestd = 1e18
        for n in tree:
            d = self._dist(n, sample)
            if d < bestd:
                bestd = d
                best = n
        return best if best is not None else sample

    def _choose_parent(
        self,
        near: list[str],
        new_zone: str,
        tree: dict[str, TreeNode]
    ) -> str:
        best_parent = near[0]
        best_cost = tree[best_parent].cost + self._edge_cost(new_zone)
        for n in near[1:]:
            c = tree[n].cost + self._edge_cost(new_zone)
            if c < best_cost:
                best_cost = c
                best_parent = n
        return best_parent

    def _extract_path(
        self,
        tree: dict[str, TreeNode],
        goal: str
    ) -> list[str]:
        path: list[str] = [goal]
        cur = goal
        while tree[cur].parent is not None:
            cur = tree[cur].parent if tree[cur].parent is not None else cur
            path.append(cur)
        path.reverse()
        return path

    def plan(
        self,
        start: str,
        goal: str,
        iters: int = 700,
        gamma: float = 3.0
    ) -> list[str]:
        if start == goal:
            return [start]
        tree: dict[str, TreeNode] = {start: TreeNode(
            zone=start, parent=None, cost=0.0)}
        all_names = list(self.zones.keys())
        best_goal: Optional[str] = None
        best_goal_cost = 1e18
        for _ in range(iters):
            sample = goal if self.rng.random() < 0.15 else self.rng.choice(all_names)
            if self.zones[sample].zone_type == ZoneType.BLOCKED:
                continue
            near0 = self._nearest(tree, sample)
            neighbors = [
                n for n in self.adj.get(near0, [])
                if self.zones[n].zone_type != ZoneType.BLOCKED and n not in tree
            ]
            if not neighbors:
                continue
           new_zone = min(neighbors, key=lambda n: self._dist(n, sample))
            if new_zone in tree:
                continue
            r = max(1.0, gamma)
            near_nodes = [n for n in tree if self._dist(n, new_zone) <= r and new_zone in self.adj[n]]
            if not near_nodes:
                near_nodes = [near0]
            parent = self._choose_parent(near_nodes, new_zone, tree)
            cost = tree[parent].cost + self._edge_cost(new_zone)
            tree[new_zone] = TreeNode(zone=new_zone, parent=parent, cost=cost)
            for n in near_nodes:
                if n == parent:
                    continue
                if n not in self.adj[new_zone]:
                    continue
                new_cost = tree[new_zone].cost + self._edge_cost(n)
                if new_cost < tree[n].cost:
                    tree[n].parent = new_zone
                    tree[n].cost = new_cost
            if goal in self.adj[new_zone]:
                g_cost = tree[new_zone].cost + self._edge_cost(goal)
                if g_cost < best_goal_cost:
                    best_goal_cost = g_cost
                    best_goal = goal
                    tree[goal] = TreeNode(zone=goal, parent=new_zone, cost=g_cost)

        if best_goal is None and goal in tree:
            best_goal = goal
        if best_goal is None:
            return []
        return self._extract_path(tree, best_goal)
