import bcrypt
from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.repositories.tables import User

def  password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def password_matches(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")
    return user


def teacher(user: User = Depends(current_user)) -> User:
    if user.role not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="权限不足，仅教师和管理员拥有该权限")
    return user


def admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足，仅管理员拥有该权限")
    return user