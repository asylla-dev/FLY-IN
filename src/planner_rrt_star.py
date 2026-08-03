from __future__ import annotations
from .models import ZoneType, Zone, Connection
from dataclasses import dataclass
from typing import Optional


@dataclass
class TreeNode:
    zone: str
    parent: Optional[str]
    cost: float



