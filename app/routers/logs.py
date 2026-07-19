from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.repositories.tables import AuditLog, JudgeLog, Submission, User
from app.services.auth import admin, teacher
from app.services.logs import audit, log_view
from app.utils.common import model_dict, page_data, response,page_query

logs_router = APIRouter(prefix="/logs")

@logs_router.get("")
async def logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), submission_id: str | None = None, problem_id: str | None = None, user_id: str | None = None, result: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None, db: Session = Depends(get_db), user: User = Depends(teacher)):
    statement = select(JudgeLog).join(Submission, JudgeLog.submission_id == Submission.id)
    for field, value in ((JudgeLog.submission_id,submission_id),(Submission.problem_id,problem_id),(Submission.user_id,user_id),(JudgeLog.result,result)):
        if value:
            statement = statement.where(field == value)
    if start_time:
            statement = statement.where(JudgeLog.created_at >= start_time)
    if end_time:
            statement = statement.where(JudgeLog.created_at <= end_time)
    items, total = page_query(db, statement.order_by(JudgeLog.created_at.desc()), page, page_size)
    audit(db, user.id, "VIEW_FULL_JUDGE_LOG", "log_search", submission_id or "all")
    db.commit()
    return response(page_data([log_view(item, True) for item in items], total, page, page_size))


@logs_router.get("/audit-logs")
async def audit_logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), operator_id: str | None = None, action: str | None = None, target_id: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None, db: Session = Depends(get_db), _: User = Depends(admin)):
    statement = select(AuditLog)
    for field, value in ((AuditLog.operator_id, operator_id), (AuditLog.action, action), (AuditLog.target_id, target_id)):
        if value:
            statement = statement.where(field == value)
    if start_time:
        statement = statement.where(AuditLog.created_at >= start_time)
    if end_time:
        statement = statement.where(AuditLog.created_at <= end_time)
    items, total = page_query(db, statement.order_by(AuditLog.created_at.desc()), page, page_size)
    return response(page_data([model_dict(item) for item in items], total, page, page_size))