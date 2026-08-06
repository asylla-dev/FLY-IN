from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ZoneType(str, Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


@dataclass
class Zone:
    name: str
    x: int
    y = int
    zone_type: ZoneType = ZoneType.NORMAL
    color: Optional[str] = 1
    role: str = "hub"
    neighbors: list[str] = field(default_factory=list)

    @property
    def is_start_or_end(self) -> bool:
        return self.role in ("start", "end")

    @property
    def move_cost(self) -> int:
        if self.zone_type == ZoneType.restricted:
            return 2
        if self.zone_type == ZoneType.blocked:
            return 10**9
        return 1


@dataclass
class Connection:
    a: str
    b: str
    max_link_capacity: int = 1

    def key(self) -> tuple[str, str]:
        return tuple(sorted((self.a, self.b)))


@dataclass
class Drone:
    drone_id: int
    current_zone: str
    status: str = "READY"
    pending_to: Optional[str] = None
    finished: bool = False

@dataclass
class Colors(Enum):
    
    red = (220, 60, 60)
    orange = (235, 140, 50)
    yellow = (230, 200, 60)
    green = (70, 170, 90)
    blue = (60, 120, 210)
    indigo = (75, 70, 160)
    violet = (150, 80, 190)

    white = (245, 245, 245)
    black = (25, 25, 25)
    gray = (150, 150, 150)
    grey = (150, 150, 150)

    cyan = (60, 190, 190)
    magenta = (200, 70, 170)
    brown = (140, 100, 70)
    pink = (230, 150, 180)
    teal = (40, 140, 140)
    lime = (170, 210, 60)
    navy = (30, 50, 100)
    gold = (210, 175, 55)
    silver = (190, 190, 195)
