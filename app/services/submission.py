import asyncio
from pathlib import Path
from tempfile import gettempdir

from sqlalchemy import delete

from app.judge.runner import judge
from app.repositories.database import SessionLocal
from app.repositories.tables import JudgeLog, Problem, Submission
from app.utils.common import time_now

from fastapi import HTTPException

TEMP_ROOT = Path(gettempdir()) / "light-oj"
TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def start_judge(submission_id: str) -> None:
    asyncio.create_task(run_judge(submission_id))


async def run_judge(submission_id: str) -> None:
    with SessionLocal() as db:
        submission = db.get(Submission, submission_id)
        if not submission:
            raise HTTPException(404, "提交不存在")
        problem = db.get(Problem, submission.problem_id) if submission else None
        if not problem:
            raise HTTPException(404, "题目不存在")
        submission.status = "running"
        submission.started_at = time_now()
        db.commit()
        source_code, cases, limit = submission.source_code, problem.test_cases, problem.time_limit
    try:
        result = await asyncio.to_thread(judge, source_code, cases, limit, TEMP_ROOT)
        with SessionLocal() as db:
            submission = db.get(Submission, submission_id)
            db.execute(delete(JudgeLog).where(JudgeLog.submission_id == submission_id))
            db.add_all(JudgeLog(submission_id=submission_id, **item) for item in result["cases"])
            submission.status = "finished"
            submission.result = result["result"]
            submission.score = result["score"]
            submission.total_time = result["total_time"]
            submission.finished_at = time_now()
            db.commit()
    except Exception:
        with SessionLocal() as db:
            submission = db.get(Submission, submission_id)
            if submission:
                submission.status = "failed"
                submission.result = "SE"
                submission.finished_at = time_now()
                db.add(JudgeLog(submission_id=submission_id, case_id="system", result="SE", score=0, time_used=0, exit_code=None, input_data="", stdout="", stderr="", expected_output="", message="评测系统错误", is_hidden=True))
                db.commit()
