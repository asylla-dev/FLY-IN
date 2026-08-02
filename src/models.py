from __future__ import annotations
from dataclases import dataclass, field
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
