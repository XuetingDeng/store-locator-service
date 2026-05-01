import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.store import Store, StoreService
from app.models.user import User


TEST_STORE_IDS = ("S9988", "S9989", "S9998", "S9999")
TEST_EMAILS = ("pytest-user@test.com", "api-user-test@test.com")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_cleanup():
    cleanup_test_data()
    yield
    cleanup_test_data()


def cleanup_test_data() -> None:
    db = SessionLocal()
    try:
        db.execute(delete(StoreService).where(StoreService.store_id.in_(TEST_STORE_IDS)))
        db.execute(delete(Store).where(Store.store_id.in_(TEST_STORE_IDS)))
        db.execute(delete(User).where(User.email.in_(TEST_EMAILS)))
        db.commit()
    finally:
        db.close()


def login(client: TestClient, email: str, password: str = "TestPassword123!") -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
