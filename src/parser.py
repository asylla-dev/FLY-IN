from __future__ import annotations
import re
from pathlib import Path
from typing import Optional
from .models import Connection, Zone, ZoneType


class ParseResult:
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

class Parser:
    def __init__(self, filename: str) -> None:
        self.filename = Path(filename)
        self.line_no = 0
        self._num_drones: Optional[int] = None
        self._zones: Dict[str, Zone] = {}
        self._connections: list[Connection] = []
        self._seen_edges: set[tuple[str, str]] = set()
        self._start: Optional[str] = None
        self._end: Optional[str] = None


    def parse(self) -> ParsingResult:
        lines = self._read_lines()
        self._parse_lines(lines)
        self._validate_final()
        return ParseResult(
            num_drones=self._num_drones if self._num_drones is not None else 0,
            zones=self._zones,
            connections=self._connections,
            start_hub=self._start if self._start_hub is not None else "",
            end_hub=self._end if self._end is not None else "",
        )

    def _read_lines(self) -> list[str]:
        try:
            with self.filename.open("r", encoding="utf-8") as f:
                return f.readlines()
        except FileNotFound error as e:
            raise ValueError(f"Input file not found: {e}")


    def _clean(self, raw: str) -> str:
        idx = raw.find("#")
        if idx > 0:
            raw = raw[:idx]
        return raw.strip()

    def _split_meta(self, raw: str) -> dict[str, str]:
        if not raw.strip():
            return {}
        items = re.split(r"[,\s]+", raw.strip())
        out: dict[str, str] = {}
        for item in items:
            if not item:
                continue
            if "=" not in item:
                raise ValueError(f"Line {self.line_no}: Invalid metadata '{item}')
            k, v = item.split("=", 1)
            k = k.strip().lower()
            v = v.strip
