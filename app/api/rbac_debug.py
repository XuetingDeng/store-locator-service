from fastapi import APIRouter, Depends

from app.api.deps import require_permission, require_role
from app.models.user import User
from app.schemas import MessageResponse

router = APIRouter(prefix="/api/debug/rbac", tags=["rbac"])


@router.get("/stores-read", response_model=MessageResponse)
def can_read_stores(_: User = Depends(require_permission("stores:read"))) -> MessageResponse:
    return MessageResponse(message="stores:read granted")


@router.get("/users-write", response_model=MessageResponse)
def can_write_users(_: User = Depends(require_permission("users:write"))) -> MessageResponse:
    return MessageResponse(message="users:write granted")


@router.get("/admin-only", response_model=MessageResponse)
def admin_only(_: User = Depends(require_role("admin"))) -> MessageResponse:
    return MessageResponse(message="admin role granted")
