from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.security import create_access_token, create_refresh_token, hash_token, verify_password
from app.db.session import get_db
from app.models.user import RefreshToken, User
from app.schemas import LoginRequest, LogoutRequest, MessageResponse, RefreshRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> TokenResponse:
    user = db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.email == payload.email)
    ).scalar_one_or_none()

    if user is None or user.status != "active" or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token(user)
    refresh_token, expires_at = create_refresh_token()
    db.add(RefreshToken(user_id=user.user_id, token_hash=hash_token(refresh_token), expires_at=expires_at))
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> TokenResponse:
    token_hash = hash_token(payload.refresh_token)
    refresh_token = db.execute(
        select(RefreshToken)
        .options(selectinload(RefreshToken.user).selectinload(User.role))
        .where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()

    now = datetime.now(UTC)
    if (
        refresh_token is None
        or refresh_token.revoked_at is not None
        or refresh_token.expires_at <= now
        or refresh_token.user.status != "active"
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return TokenResponse(
        access_token=create_access_token(refresh_token.user),
        refresh_token=None,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> MessageResponse:
    token_hash = hash_token(payload.refresh_token)
    refresh_token = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if refresh_token is not None and refresh_token.revoked_at is None:
        refresh_token.revoked_at = datetime.now(UTC)
        db.commit()

    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role.name,
        status=current_user.status,
        must_change_password=current_user.must_change_password,
    )
