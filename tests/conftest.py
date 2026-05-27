import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.database import get_db
from app.main import app


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(
        anthropic_api_key="test-key",
        java_api_url="http://localhost:8080",
        db_url="postgresql://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379",
    )


@pytest.fixture
def mock_db():
    db = MagicMock()
    return db


@pytest.fixture
def client(mock_settings, mock_db):
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
