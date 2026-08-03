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
        seed: int = 42,
    ) -> None:
        self.zones = zones
        self.seed = seed
        self.rng = random.Random(seed)
