from fastapi import APIRouter

from auth import auth_router
from users import users_router
from problems import  problems_router
from submission import submission_router
from logs import logs_router
from backup import backup_router

router = APIRouter(prefix="/api")

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(problems_router)
router.include_router(submission_router)
router.include_router(logs_router)
router.include_router(backup_router)