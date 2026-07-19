from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.schemas import SubmissionCreate
from app.repositories.database import get_db
from app.repositories.tables import JudgeLog, Problem, Submission, User
from app.services.auth import current_user,teacher
from app.services.logs import audit, log_view
from app.services.submission import start_judge
from app.utils.common import model_dict, page_data, response

from utils.common import page_query

submission_router = APIRouter(prefix="/submissions")

@submission_router.post("", status_code=202)
async def create_submission(body: SubmissionCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not body.source_code.strip():
        raise HTTPException(status_code=422, detail="代码不能为空")
    if len(body.source_code.encode("utf-8")) > 65536:
        raise HTTPException(status_code=422, detail="代码不能超过 64 KB")
    if not db.get(Problem, body.problem_id):
        raise HTTPException(status_code=404, detail="题目不存在")
    submission = Submission(user_id=user.id, **body.model_dump())
    db.add(submission)
    db.commit()
    start_judge(submission.id)
    return response({"submission_id": submission.id, "status": submission.status}, "提交已创建", 202)


def submission_filters(statement, problem_id, user_id, status, result, start_time, end_time):
    for field, value in ((Submission.problem_id, problem_id), (Submission.user_id, user_id), (Submission.status, status), (Submission.result, result)):
        if value:
            statement = statement.where(field == value)
    if start_time:
        statement = statement.where(Submission.created_at >= start_time)
    if end_time:
        statement = statement.where(Submission.created_at <= end_time)
    return statement


@submission_router.get("")
async def submissions(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), problem_id: str | None = None, user_id: str | None = None, status: str | None = None, result: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owner = user.id if user.role == "student" else user_id
    statement = submission_filters(select(Submission), problem_id, owner, status, result, start_time, end_time).order_by(Submission.created_at.desc())
    items, total = page_query(db, statement, page, page_size)
    return response(page_data([model_dict(item) for item in items], total, page, page_size))


def get_submission(db: Session, submission_id: str, user: User) -> Submission:
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")
    if user.role == "student" and submission.user_id != user.id:
        raise HTTPException(status_code=403, detail="学生只能查看自己的提交")
    return submission


@submission_router.get("/{submission_id}")
async def submission_detail(submission_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return response(data=model_dict(get_submission(db, submission_id, user)))


@submission_router.post("/{submission_id}/rejudge", status_code=202)
async def rejudge(submission_id: str, db: Session = Depends(get_db), user: User = Depends(teacher)):
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")
    if submission.status not in {"finished", "failed"}:
        raise HTTPException(status_code=409, detail="当前状态不能重新评测")
    submission.status, submission.result, submission.score = "pending", None, 0
    submission.total_time = submission.started_at = submission.finished_at = None
    audit(db, user.id, "REJUDGE_SUBMISSION", "submission", submission.id)
    db.commit()
    start_judge(submission.id)
    return response(data={"submission_id": submission.id, "status": "pending"}, message="已进入重评队列", code=202)


@submission_router.get("/{submission_id}/logs")
async def submission_logs(submission_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    submission = get_submission(db, submission_id, user)
    full = user.role in {"teacher", "admin"}
    logs = db.scalars(select(JudgeLog).where(JudgeLog.submission_id == submission.id).order_by(JudgeLog.id)).all()
    if full:
        audit(db, user.id, "VIEW_FULL_JUDGE_LOG", "submission", submission.id)
        db.commit()
    return response(data={"submission": model_dict(submission), 
                          "cases": [log_view(item, full) for item in logs]})