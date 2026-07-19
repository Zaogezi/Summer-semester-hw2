from fastapi import APIRouter

from app.routers.auth import auth_router
from app.routers.users import users_router
from app.routers.problems import  problems_router
from app.routers.submission import submission_router
from app.routers.logs import logs_router
from app.routers.backup import backup_router

router = APIRouter(prefix="/api")

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(problems_router)
router.include_router(submission_router)
router.include_router(logs_router)
router.include_router(backup_router)