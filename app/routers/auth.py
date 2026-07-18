from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.schemas import Credentials
from app.repositories.database import get_db
from app.repositories.tables import User
from app.services.auth import current_user, password_hash, password_matches
from app.utils.common import model_dict, response

auth_router = APIRouter(prefix="/auth")


@auth_router.post("/register", status_code=201)
async def register(body: Credentials, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(username=body.username, password_hash=password_hash(body.password))
    db.add(user)
    db.commit()
    return response(data=model_dict(model=user, exclude={"password_hash"}),
                    message="注册成功",
                    code=201)


@auth_router.post("/login")
async def login(body: Credentials, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not password_matches(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")
    request.session["user_id"] = user.id
    return response(data=model_dict(user, {"password_hash"}), message="登录成功")


@auth_router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return response(message="已登出")


@auth_router.get("/me")
async def me(user: User = Depends(current_user)):
    return response(model_dict(user, {"password_hash"}))