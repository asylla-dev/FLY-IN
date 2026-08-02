from __future__ import annotations
import re
from pathlib import Path
from typing import Optional
from .models import Connection, Zone, ZoneType


class ParsingResult:
    def __init__(
        self,
        num_drones: int,
        zones: dict[str, Zone],
        connetions: list[Connections],
        start_hub: str,
        end_hub: str,
    ) -> None:
        self.num_drones = num_drones
        self.zones = zones
        self.connections = connections
        self.start_hub = start_hub
        self.end_hub = end_hub


class
