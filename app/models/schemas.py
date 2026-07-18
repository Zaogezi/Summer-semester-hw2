import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from fastapi import HTTPException

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    role: Literal["student", "teacher", "admin"]
    is_active: bool


class Sample(BaseModel):
    input: str
    output: str


class TestCase(BaseModel):
    case_id: str = Field(min_length=1)
    input: str
    output: str
    score: int = Field(ge=0)
    is_hidden: bool = True


class ProblemData(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    input_description: str = Field(min_length=1)
    output_description: str = Field(min_length=1)
    samples: list[Sample] = Field(min_length=1)
    constraints: str = ""
    time_limit: float = Field(gt=0)
    memory_limit: float = Field(gt=0)
    difficulty: Literal["easy", "medium", "hard"]
    tags: list[str] = []
    test_cases: list[TestCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_problem(self):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.id):
            raise HTTPException(status_code=422, detail="题目编号只能包含字母、数字、下划线和连字符")
        case_ids = [case.case_id for case in self.test_cases]
        if len(case_ids) != len(set(case_ids)):
            raise HTTPException(status_code=422, detail="测试点编号不能重复")
        if sum([case.score for case in self.test_cases]) != 100:
            raise HTTPException(status_code=422, detail="测试点分值总和必须为 100")
        return self


class SubmissionCreate(BaseModel):
    problem_id: str
    language: Literal["python"] = "python"
    source_code: str = Field(min_length=1, max_length=65536)
