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


