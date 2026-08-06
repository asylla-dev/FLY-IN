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
        connections: list[Connection],
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
        self._zones: dict[str, Zone] = {}
        self._connections: list[Connection] = []
        self._seen_edges: set[tuple[str, str]] = set()
        self._start: Optional[str] = None
        self._end: Optional[str] = None

    def parse(self) -> ParseResult:
        lines = self._read_lines()
        self._parse_lines(lines)
        self._validate_final()
        return ParseResult(
            num_drones=self._num_drones if self._num_drones is not None else 0,
            zones=self._zones,
            connections=self._connections,
            start_hub=self._start if self._start is not None else "",
            end_hub=self._end if self._end is not None else "",
        )

    def _read_lines(self) -> list[str]:
        try:
            with self.filename.open("r", encoding="utf-8") as f:
                return f.readlines()
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Input file not found: {self.filename}"
            ) from exc

    def _clean(self, raw: str) -> str:
        idx = raw.find("#")
        if idx >= 0:
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
                raise ValueError(
                    f"Line {self.line_no}: Invalid metadata '{item}'"
                )
            k, v = item.split("=", 1)
            k = k.strip().lower()
            v = v.strip()
            if not v:
                raise ValueError(
                    f"Line {self.line_no}: Empty metadata value for '{k}'"
                )
            out[k] = v
        return out

    def _extract_meta(self, text: str) -> tuple[str, dict[str, str]]:
        m = re.search(r"\[(.*?)\]", text)
        if m is None:
            return text.strip(), {}
        base = text[: m.start()].strip()
        return base, self._split_meta(m.group(1))

    def _parse_lines(self, lines: list[str]) -> None:
        first_data_seen = False
        for i, raw in enumerate(lines, start=1):
            self.line_no = i
            line = self._clean(raw)
            if not line:
                continue

            if not first_data_seen:
                self._parse_nb_drones(line)
                first_data_seen = True
                continue

            if line.startswith("start_hub:"):
                self._parse_zone(line, "start")
            elif line.startswith("end_hub:"):
                self._parse_zone(line, "end")
            elif line.startswith("hub:"):
                self._parse_zone(line, "hub")
            elif line.startswith("connection:"):
                self._parse_connection(line)
            else:
                raise ValueError(
                    f"Line {self.line_no}: Unknown command '{line}'"
                )

    def _parse_nb_drones(self, line: str) -> None:
        if not line.startswith("nb_drones:"):
            raise ValueError(
                f"Line {self.line_no}: First data line must be 'nb_drones:'"
            )
        raw = line.split(":", 1)[1].strip()
        try:
            n = int(raw)
        except ValueError as exc:
            raise ValueError(
                f"Line {self.line_no}: nb_drones must be integer"
            ) from exc
        if n <= 0:
            raise ValueError(
                f"Line {self.line_no}: nb_drones must be > 0"
            )
        self._num_drones = n

    def _parse_zone(self, line: str, role: str) -> None:
        prefix = "hub:" if role == "hub" else f"{role}_hub:"
        body = line.split(prefix, 1)[1].strip()
        base, meta = self._extract_meta(body)

        parts = base.split()
        if len(parts) != 3:
            raise ValueError(
                f"Line {self.line_no}: Invalid zone format"
            )

        name, sx, sy = parts
        if "-" in name or " " in name:
            raise ValueError(
                f"Line {self.line_no}: Zone name '{name}' cannot contain '-' or spaces"
            )
        if name in self._zones:
            raise ValueError(
                f"Line {self.line_no}: Duplicate zone '{name}'"
            )

        try:
            x = int(sx)
            y = int(sy)
        except ValueError as exc:
            raise ValueError(
                f"Line {self.line_no}: Coordinates must be integers"
            ) from exc

        zone_raw = meta.get("zone", "normal").lower()
        allowed = {z.value for z in ZoneType}
        if zone_raw not in allowed:
            raise ValueError(
                f"Line {self.line_no}: Invalid zone type '{zone_raw}'"
            )
        zone_type = ZoneType(zone_raw)

        color = meta.get("color")
        if role in ("start", "end"):
            max_drones = None
        else:
            md = meta.get("max_drones", "1")
            try:
                max_drones = int(md)
            except ValueError as exc:
                raise ValueError(
                    f"Line {self.line_no}: max_drones must be integer"
                ) from exc
            if max_drones <= 0:
                raise ValueError(
                    f"Line {self.line_no}: max_drones must be > 0"
                )

        zone = Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            max_drones=max_drones,
            role="hub" if role == "hub" else role,
        )
        self._zones[name] = zone

        if role == "start":
            if self._start is not None:
                raise ValueError(
                    f"Line {self.line_no}: Multiple start_hub definitions"
                )
            self._start = name
        if role == "end":
            if self._end is not None:
                raise ValueError(
                    f"Line {self.line_no}: Multiple end_hub definitions"
                )
            self._end = name

    def _parse_connection(self, line: str) -> None:
        body = line.split("connection:", 1)[1].strip()
        base, meta = self._extract_meta(body)

        if "-" not in base:
            raise ValueError(
                f"Line {self.line_no}: Invalid connection format"
            )
        a, b = [x.strip() for x in base.split("-", 1)]
        if not a or not b:
            raise ValueError(
                f"Line {self.line_no}: Empty zone name in connection"
            )
        if a not in self._zones or b not in self._zones:
            raise ValueError(
                f"Line {self.line_no}: Undefined zone in connection '{a}-{b}'"
            )

        k = tuple(sorted((a, b)))
        if k in self._seen_edges:
            raise ValueError(
                f"Line {self.line_no}: Duplicate connection '{a}-{b}'"
            )
        self._seen_edges.add(k)

        cap_raw = meta.get("max_link_capacity", "1")
        try:
            cap = int(cap_raw)
        except ValueError as exc:
            raise ValueError(
                f"Line {self.line_no}: max_link_capacity must be integer"
            ) from exc
        if cap <= 0:
            raise ValueError(
                f"Line {self.line_no}: max_link_capacity must be > 0"
            )

        self._connections.append(
            Connection(a=a, b=b, max_link_capacity=cap)
        )
        self._zones[a].neighbors.append(b)
        self._zones[b].neighbors.append(a)

    def _validate_final(self) -> None:
        if self._num_drones is None:
            raise ValueError("Missing nb_drones")
        if self._start is None:
            raise ValueError("Missing start_hub")
        if self._end is None:
            raise ValueError("Missing end_hub")
