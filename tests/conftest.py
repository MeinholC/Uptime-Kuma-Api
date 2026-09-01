import os

os.environ.setdefault("UPTIME_KUMA_URL", "http://kuma.example.invalid")
os.environ.setdefault("UPTIME_KUMA_USERNAME", "admin")
os.environ.setdefault("UPTIME_KUMA_PASSWORD", "test-password")
os.environ.setdefault("API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

from app.main import app

API_KEY = os.environ["API_KEY"]


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": API_KEY}
