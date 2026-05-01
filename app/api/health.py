from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict[str, object]:
    store_count = db.execute(text("SELECT count(*) FROM stores")).scalar_one()
    user_count = db.execute(text("SELECT count(*) FROM users")).scalar_one()

    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "database": {
            "connected": True,
            "stores": store_count,
            "users": user_count,
        },
    }
