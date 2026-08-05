from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .models import Connection, Zone, ZoneType, Drone 
from .planner_rrt_star import RRTStarPlanner

@dataclass
class Drone:
    drone_id: int
    token: str


class Simulation:
    def __init__(
        self,
        )
