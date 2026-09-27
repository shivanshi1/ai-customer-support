from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_check() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        groq_api_key="test-key",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
