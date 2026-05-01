from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin_stores import router as admin_stores_router
from app.api.admin_users import router as admin_users_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.rbac_debug import router as rbac_debug_router
from app.api.stores_public import router as stores_public_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(admin_stores_router)
    app.include_router(admin_users_router)
    app.include_router(stores_public_router)
    app.include_router(rbac_debug_router)
    return app


app = create_app()
