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
            if not v:
                raise ValueError(f"Line {self.line_no}: Empty metadata value for '{k}'")
            out[k] = v
        return out

    def _extract_meta(self, text: str) -> tuple[str, dict[str, str]]:
        m = re.search(r"\[(.*?)\]", text)
        if m is None:
            return text.strip(), {}
        base = text[: m.start()].strip()
        return base, self._split_meta(m.group(1))

    def _parse_zone(self, line: str, role: str) -> None:
        prefix = "hub:" if role == "hub" else f"{role}_hub:"
        body = line.split(prefix, 1)[1].strip()
        base, meta = self._extract_meta(body)
        parts = base.split()
        if len(parts) != 3:
            raise ValueError(f"Line {self.line_no}: Invalid zone format")
        name, sx, sy, = parts
        if "-" in name or " " in name:
            raise ValueError(f"Line {self.line_no}: Zone name '{name}' cannot contain '-' or spaces")
        if name in self._zones:
            raise ValueError(f"Line {self.line_no}: Duplicate zone '{name}'")
        try:
            x = int(sx)
            y = int(sy)
        except ValueError as e:
            raise ValueError(f"Line {self.line_no}: Coordinates must be integers") from e
        zone_raw = meta.get("zone", "normal").lower()
        allowed = {z.value for z in ZoneType}
        if zone_raw not in allowed:
            raise ValueError(f"Line {line_no}: Invalid zone type '{zone_raw}'")
        zone_type = ZoneType(zone_raw)
        color = meta.get("color")
        if role in ("start", "end"):
            max_drones = None
        else:
            md = meta.get("max_drones", "1")
            try:
                max_drones = int(md)
            except ValueError as e:
                raise ValueError(f"Line {self.line_no}: max_drones must be integer") from e
            if max_drones <= 0:
                raise ValueError(f"Line {self.line_no}: max drones must be > 0")
        zone = Zone(
            name=name,
            x=x,
            y=y,
            zone_type = zone_type,
            color=color,
            max_drones=max_drones,
            role="hub" if role == "hub" else role,
        )
        self._zones[name] = zone
        if role == "start":
            if self._start is not None:
                raise ValueError(f"Line {self.line_no}: Multiple start_hub definitions")
            self._start = name
        if role == "end":
            if self._end is not None:
                raise ValueError(f"Line {self.line_no}: Multiple end_hub definitions")
            self._end = name



    def _parse_lines(self, lines: list[str]) -> None:
        first_data_seen = False
        for i, raw in enumerate(lines, start=1):
            self.line_no = i
            line = self_clean(raw)
            if not line:
                continue
            if not first_data_seen:
                self_.parse_nb_drones(line)
                first_data_seen = True
                continue
            
