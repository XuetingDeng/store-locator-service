from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas import AdminUserCreate, AdminUserUpdate, UserListResponse, UserResponse

router = APIRouter(prefix="/api/admin/users", tags=["admin users"])


def serialize_user(user: User) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role.name,
        status=user.status,
        must_change_password=user.must_change_password,
    )


def get_role(db: Session, role_name: str) -> Role:
    role = db.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role")
    return role


def next_user_id(db: Session) -> str:
    user_ids = db.execute(select(User.user_id).where(User.user_id.like("U%"))).scalars().all()
    max_number = 0
    for user_id in user_ids:
        suffix = user_id[1:]
        if suffix.isdigit():
            max_number = max(max_number, int(suffix))
    return f"U{max_number + 1:03d}"


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("users:write")),
) -> UserResponse:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    role = get_role(db, payload.role)
    user = User(
        user_id=next_user_id(db),
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_id=role.id,
        status=payload.status,
        must_change_password=payload.must_change_password,
    )
    db.add(user)
    db.commit()

    user = db.execute(
        select(User).options(selectinload(User.role)).where(User.user_id == user.user_id)
    ).scalar_one()
    return serialize_user(user)


@router.get("", response_model=UserListResponse)
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("users:read")),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> UserListResponse:
    total = db.execute(select(func.count()).select_from(User)).scalar_one()
    users = db.execute(
        select(User).options(selectinload(User.role)).order_by(User.user_id).limit(limit).offset(offset)
    ).scalars().all()
    return UserListResponse(total=total, limit=limit, offset=offset, items=[serialize_user(user) for user in users])


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("users:write")),
) -> UserResponse:
    user = db.execute(
        select(User).options(selectinload(User.role)).where(User.user_id == user_id)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.role is not None:
        user.role_id = get_role(db, payload.role).id
    if payload.status is not None:
        user.status = payload.status
    if payload.must_change_password is not None:
        user.must_change_password = payload.must_change_password
    user.updated_at = datetime.now(UTC)

    db.commit()
    db.expire_all()
    user = db.execute(
        select(User).options(selectinload(User.role)).where(User.user_id == user_id)
    ).scalar_one()
    return serialize_user(user)


@router.delete("/{user_id}", response_model=UserResponse)
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("users:delete")),
) -> UserResponse:
    user = db.execute(
        select(User).options(selectinload(User.role)).where(User.user_id == user_id)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.status = "inactive"
    user.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return serialize_user(user)
