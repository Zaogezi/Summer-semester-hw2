from typing import Any
from datetime import datetime, timezone
import re
from sqlalchemy.orm import Session
from sqlalchemy import select, func

def time_now():
    return datetime.now(timezone.utc)

def page_query(db: Session, statement, page: int, page_size: int):
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    items = db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return items, total

def response(data=None, message="ok", code=200):
    return {"code": code,
            "message": message,
            "data": data}

def iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value else None

def model_dict(model: Any, exclude: set[str] | None = None) -> dict:
    excluded = exclude or set()
    result = {}
    for column in model.__table__.columns:
        if column.name not in excluded:
            value = getattr(model, column.name)
            result[column.name] = iso(value) if isinstance(value, datetime) else value
    return result

def truncate(value: str, limit: int = 4000) -> str:
    return value if len(value) <= limit else value[:limit] + "...[truncated]"


def sanitize(value: str) -> str:
    value = re.sub(r"[A-Za-z]:\\[^\s\"']*main\.py", "<submission>/main.py", value)
    value = re.sub(r"/([^/\s]+/)+main\.py", "<submission>/main.py", value)
    lines = value.splitlines()
    if "Traceback (most recent call last):" in value:
        lines = [line for line in lines if not line.lstrip().startswith("File ")]
    return truncate("\n".join(lines))



def page_data(items: list[Any], total: int, page: int, page_size: int) -> dict:
    return {"items": items, "total": total, "page": page, "page_size": page_size}
