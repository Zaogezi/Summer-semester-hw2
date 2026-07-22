from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware

from app.repositories.database import Base, SessionLocal, engine
from app.repositories.tables import JudgeLog, Problem, Submission, User
from app.routers.api import router
from app.services.auth import password_hash
from app.utils.common import time_now
from app.utils.common import response


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.username == "admin")):
            db.add(User(username="admin", password_hash=password_hash("admin12345"), role="admin"))
        if not db.scalar(select(User).where(User.username == "teacher")):
            db.add(User(username="teacher", password_hash=password_hash("teacher123"), role="teacher"))
        for submission in db.scalars(select(Submission).where(Submission.status.in_(["pending", "running"]))):
            submission.status, submission.result, submission.finished_at = "failed", "SE", time_now()
            db.add(JudgeLog(submission_id=submission.id, case_id="system", result="SE", score=0, time_used=0, exit_code=None, input_data="", stdout="", stderr="", expected_output="", message="服务重启导致评测中断", is_hidden=True))
        db.commit()
    yield


app = FastAPI(title="Light OJ", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key="secret-key") # to be replaced


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(content=response(message=str(exc.detail), code=exc.status_code),
                        status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    message = exc.errors()[0].get("msg", "参数校验失败")
    return JSONResponse(content=response(message=message, code=422),
                        status_code=422)


app.include_router(router)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
