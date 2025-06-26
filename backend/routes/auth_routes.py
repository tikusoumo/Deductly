from fastapi import APIRouter
from controllers import auth_controller

router = APIRouter()
router.include_router(auth_controller.router, prefix="/auth")
