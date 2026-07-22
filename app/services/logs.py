from app.repositories.tables import AuditLog, JudgeLog
from app.utils.common import model_dict, sanitize
from sqlalchemy.orm import Session


def audit(db: Session, user_id: str, action: str, target_type: str, target_id: str) -> None:
    db.add(AuditLog(operator_id=user_id, action=action, target_type=target_type, target_id=target_id))


def log_view(log: JudgeLog, full: bool) -> dict | None:
    item = model_dict(log)
    item["stderr"] = sanitize(item["stderr"])
    item["message"] = sanitize(item["message"])
    if full:
        return item
    if log.is_hidden:
        item.pop("input_data")
        item.pop("stdout")
        item.pop("expected_output")
    return item
