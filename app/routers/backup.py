import json
import shutil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.database import BACKUP_DIR, DB_PATH, SessionLocal, engine, get_db
from app.repositories.tables import Backup, User
from app.services.auth import admin
from app.services.logs import audit
from app.utils.common import model_dict, response, time_now

backup_router = APIRouter(prefix="/admin/backups")

@backup_router.post("", status_code=201)
async def create_backup(db: Session = Depends(get_db), user: User = Depends(admin)):
    backup_id = time_now().strftime("backup_%Y%m%d_%H%M%S_%f")
    folder = BACKUP_DIR / backup_id
    folder.mkdir(parents=True)
    db.add(Backup(id=backup_id))
    audit(db, user.id, "CREATE_BACKUP", "backup", backup_id)
    db.commit()
    engine.dispose()
    shutil.copy2(DB_PATH, folder / "oj.db")
    (folder / "manifest.json").write_text(json.dumps({"created_at": time_now().isoformat(), "storage": "sqlite", "files": ["oj.db"]}, ensure_ascii=False), encoding="utf-8")
    return response({"backup_id": backup_id, "created_at": time_now().isoformat()}, "备份已创建", 201)


@backup_router.get("")
async def backups(db: Session = Depends(get_db), _: User = Depends(admin)):
    items = db.scalars(select(Backup).order_by(Backup.created_at.desc())).all()
    return response([model_dict(item) for item in items])


@backup_router.post("/{backup_id}/restore")
async def restore_backup(backup_id: str, db: Session = Depends(get_db), user: User = Depends(admin)):
    folder = BACKUP_DIR / backup_id
    database, manifest_file = folder / "oj.db", folder / "manifest.json"
    if not database.exists() or not manifest_file.exists():
        raise HTTPException(status_code=404, detail="备份不存在")
    audit(db, user.id, "RESTORE_BACKUP", "backup", backup_id)
    db.commit()
    db.close()
    engine.dispose()
    replacement = DB_PATH.with_suffix(".restore")
    shutil.copy2(database, replacement)
    replacement.replace(DB_PATH)
    return response(message="备份已恢复，请重新登录")