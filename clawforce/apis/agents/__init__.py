"""Agent API: CRUD, lifecycle, templates, A2A."""

from fastapi import APIRouter

from .a2a import router as _a2a_router
from .crud import router as _crud_router
from .templates import router as _templates_router

router = APIRouter()
router.include_router(_templates_router)
router.include_router(_crud_router)
router.include_router(_a2a_router)
