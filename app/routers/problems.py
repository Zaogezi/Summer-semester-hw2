from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.schemas import ProblemData
from app.repositories.database import get_db
from app.repositories.tables import Problem,User
from app.services.auth import current_user, teacher
from app.utils.common import model_dict, page_data, response,page_query
problems_router = APIRouter(prefix="/problems")


def problem_view(problem: Problem, full: bool) -> dict:
    item = model_dict(problem)
    if not full:
        item.pop("test_cases")
        item.pop("spj")
    return item


@problems_router.get("")
async def problems(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(current_user)):
    items, total = page_query(db, select(Problem).order_by(Problem.id), page, page_size)
    return response(data=page_data([problem_view(item, user.role in {"teacher", "admin"}) for item in items], total, page, page_size))


@problems_router.get("/{problem_id}")
async def problem_detail(problem_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="题目不存在")
    return response(problem_view(problem, user.role in {"teacher", "admin"}))


@problems_router.post("", status_code=201)
async def create_problem(body: ProblemData, db: Session = Depends(get_db), _: User = Depends(teacher)):
    if db.get(Problem, body.id):
        raise HTTPException(status_code=409, detail="题目编号已存在")
    problem = Problem(**body.model_dump())
    db.add(problem)
    db.commit()
    return response(problem_view(problem, True), "题目已创建", 201)


@problems_router.put("/{problem_id}")
async def update_problem(problem_id: str, body: ProblemData, db: Session = Depends(get_db), _: User = Depends(teacher)):
    if body.id != problem_id:
        raise HTTPException(status_code=400, detail="不能修改题目编号")
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="题目不存在")
    for key, value in body.model_dump().items():
        setattr(problem, key, value)
    db.commit()
    return response(problem_view(problem, True), "题目已更新")


@problems_router.delete("/{problem_id}")
async def delete_problem(problem_id: str, db: Session = Depends(get_db), _: User = Depends(teacher)):
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="题目不存在")
    db.delete(problem)
    db.commit()
    return response(message="题目已删除")
