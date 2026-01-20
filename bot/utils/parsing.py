from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class FilterArgs:
    tags: list[str]
    start_dt: datetime | None
    end_dt: datetime | None
    page: int


def parse_filter_args(raw: str) -> FilterArgs:
    tags: list[str] = []
    start_dt: datetime | None = None
    end_dt: datetime | None = None
    page = 1

    parts = [part.strip() for part in raw.split() if part.strip()]
    for part in parts:
        if part.startswith("#"):
            tags.extend([t.lstrip("#") for t in part.split(",") if t.lstrip("#")])
        elif part.startswith("days="):
            value = part.split("=", 1)[1]
            if value.isdigit():
                start_dt = datetime.utcnow() - timedelta(days=int(value))
        elif part.startswith("from="):
            value = part.split("=", 1)[1]
            start_dt = _parse_date(value)
        elif part.startswith("to="):
            value = part.split("=", 1)[1]
            end_dt = _parse_date(value)
        elif part.startswith("page="):
            value = part.split("=", 1)[1]
            if value.isdigit():
                page = max(1, int(value))

    tags = [tag.lower() for tag in tags if tag]
    return FilterArgs(tags=tags, start_dt=start_dt, end_dt=end_dt, page=page)


def _parse_date(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None

