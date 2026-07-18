from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.schemas import UserUpdate
from app.repositories.database import get_db
from app.repositories.tables import User
from app.services.auth import admin
from app.services.logs import audit
from app.utils.common import model_dict, page_data, response
from utils.common import page_query

users_router = APIRouter(prefix="/users")

@users_router.get("")
async def users(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(admin)):
    items, total = page_query(db, select(User).order_by(User.created_at.desc()), page, page_size)
    return response(data=page_data([model_dict(item, {"password_hash"}) for item in items], total, page, page_size))


@users_router.get("/{user_id}")
async def user_detail(user_id: str, db: Session = Depends(get_db), _: User = Depends(admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return response(model_dict(user, exclude={"password_hash"}))


@users_router.put("/{user_id}")
async def update_user(user_id: str, body: UserUpdate, db: Session = Depends(get_db), operator: User = Depends(admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == operator.id and not body.is_active:
        raise HTTPException(status_code=400, detail="不能禁用自己")
    actions = []
    if user.role != body.role:
        actions.append("UPDATE_USER_ROLE")
    if user.is_active and not body.is_active:
        actions.append("DISABLE_USER")
    user.role, user.is_active = body.role, body.is_active
    for action in actions:
        audit(db, operator.id, action, "user", user.id)
    db.commit()
    return response(data=model_dict(user, exclude={"password_hash"}), 
                    message="用户已更新")
