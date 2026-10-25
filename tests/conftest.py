from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from madrid.app import create_app

PASSWORD = "synthetic-test-password-only"


@pytest.fixture
def client(tmp_path: Path):
    with TestClient(create_app(tmp_path / "store"), headers={"X-Requested-With": "Madrid"}) as client:
        assert client.post("/api/auth/setup", json={"password": PASSWORD}).status_code == 200
        assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 200
        yield client
