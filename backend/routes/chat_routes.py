from fastapi import APIRouter
from controllers import chat_controller

router = APIRouter()
router.include_router(chat_controller.router, prefix="/chat")
