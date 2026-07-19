from typing import Any
from uuid import uuid4

from sqlalchemy import (Boolean,
                        Float,
                        ForeignKey,
                        Integer,
                        JSON,
                        String,
                        Text,)
from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from .database import Base
from datetime import datetime
from app.utils.common import time_now

class User(Base):
    __tablename__ = "users"
    
    __table_args__ = (
        CheckConstraint(
            "length(trim(username)) BETWEEN 3 AND 32",
            name="ck_users_username_length",
        ),
    )
    id: Mapped[str] = mapped_column(String(),primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(32), unique=True) # len(username) >= 3
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default="student")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=time_now)
    updated_at: Mapped[datetime] = mapped_column(default=time_now, onupdate=time_now)
    
class Problem(Base):
    __tablename__ = "problems"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    constraints: Mapped[str] = mapped_column(Text, default="")
    input_description: Mapped[str] = mapped_column(Text)
    output_description: Mapped[str] = mapped_column(Text)
    samples: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    time_limit: Mapped[float]
    memory_limit: Mapped[float]
    difficulty: Mapped[str] = mapped_column(String())
    tags: Mapped[list[str]] = mapped_column(JSON)
    test_cases: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    
class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[str] = mapped_column(String(),primary_key=True,default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id"))# user/problem -> submission?
    language: Mapped[str] = mapped_column(String(10), default="python")
    source_code: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="pending")
    result: Mapped[str | None] = mapped_column(String(3), nullable=True)
    score: Mapped[int] = mapped_column(default=0)
    total_time: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=time_now)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]


class JudgeLog(Base):
    __tablename__ = "judge_logs"
    id: Mapped[str] = mapped_column(String(), primary_key=True, default=lambda: str(uuid4()))
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"))
    case_id: Mapped[str] = mapped_column(String())
    result: Mapped[str] = mapped_column(String())
    score: Mapped[int] 
    time_used: Mapped[float] 
    exit_code: Mapped[int | None]
    input_data: Mapped[str] = mapped_column(Text)
    stdout: Mapped[str] = mapped_column(Text)
    stderr: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    is_hidden: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(default=time_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    operator_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String())
    target_type: Mapped[str] = mapped_column(String())
    target_id: Mapped[str] = mapped_column(String())
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=time_now)


class Backup(Base):
    __tablename__ = "backups"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=time_now)
