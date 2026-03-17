"""Integration tests for clawforce FastAPI endpoints using TestClient."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Each test gets a fresh, isolated data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("ADMIN_STORAGE_ROOT", str(data_dir))
    monkeypatch.setenv("CLAWFORCE_ENV", "development")
    monkeypatch.setenv("ADMIN_RUNTIME_BACKEND", "process")
    # Disable rate limiting in tests (slowapi honours this env var)
    monkeypatch.setenv("RATELIMIT_ENABLED", "0")
    # Force re-initialisation of the cached database singleton
    from clawforce.core import database as db_module

    db_module.get_database.cache_clear()
    yield data_dir
    db_module.get_database.cache_clear()


@pytest.fixture
def client(isolated_data_dir: Path):
    """Return a TestClient with a fresh app instance."""
    # Import after env vars are patched so the app picks up the test data dir
    from clawforce.app import create_app

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def admin_user(client: TestClient):
    """Create an admin user and return (username, password)."""
    from clawforce.auth import hash_password
    from clawforce.core.database import get_database
    from clawforce.core.store.users import UserStore

    store = UserStore(get_database())
    store.create_user(username="testadmin", password_hash=hash_password("testpass"), role="admin")
    return "testadmin", "testpass"


@pytest.fixture
def auth_headers(client: TestClient, admin_user):
    """Return Authorization headers with a valid JWT."""
    username, password = admin_user
    resp = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


class TestAuthLogin:
    def test_login_success(self, client: TestClient, admin_user):
        username, password = admin_user
        resp = client.post("/api/auth/login", data={"username": username, "password": password})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, admin_user):
        username, _ = admin_user
        resp = client.post("/api/auth/login", data={"username": username, "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client: TestClient):
        resp = client.post("/api/auth/login", data={"username": "nobody", "password": "x"})
        assert resp.status_code == 401

    def test_me_authenticated(self, client: TestClient, auth_headers, admin_user):
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == admin_user[0]
        assert body["role"] == "admin"

    def test_me_unauthenticated(self, client: TestClient):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_stream_token_endpoint(self, client: TestClient, auth_headers):
        resp = client.post("/api/auth/stream-token", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body
        assert len(body["token"]) > 20

    def test_stream_token_requires_auth(self, client: TestClient):
        resp = client.post("/api/auth/stream-token")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Agent CRUD endpoints
# ---------------------------------------------------------------------------


class TestAgentCRUD:
    def test_list_agents_empty(self, client: TestClient, auth_headers):
        resp = client.get("/api/agents", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_agent(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/agents",
            json={"name": "Test Bot", "description": "A test agent"},
            headers=auth_headers,
        )
        assert resp.status_code in (200, 201)
        body = resp.json()
        assert body["name"] == "Test Bot"
        assert "id" in body
        assert "agent_token" in body  # token returned at creation time

    def test_get_agent(self, client: TestClient, auth_headers):
        create = client.post("/api/agents", json={"name": "Fetch Me"}, headers=auth_headers)
        assert create.status_code in (200, 201)
        agent_id = create.json()["id"]

        resp = client.get(f"/api/agents/{agent_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Fetch Me"

    def test_get_agent_not_found(self, client: TestClient, auth_headers):
        resp = client.get("/api/agents/nonexistent-id", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_agent(self, client: TestClient, auth_headers):
        create = client.post("/api/agents", json={"name": "Old Name"}, headers=auth_headers)
        agent_id = create.json()["id"]

        resp = client.put(
            f"/api/agents/{agent_id}", json={"name": "New Name"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_delete_agent(self, client: TestClient, auth_headers):
        create = client.post("/api/agents", json={"name": "Doomed Bot"}, headers=auth_headers)
        agent_id = create.json()["id"]

        resp = client.delete(f"/api/agents/{agent_id}", headers=auth_headers)
        assert resp.status_code == 200

        # Verify it's gone
        get = client.get(f"/api/agents/{agent_id}", headers=auth_headers)
        assert get.status_code == 404

    def test_create_requires_auth(self, client: TestClient):
        resp = client.post("/api/agents", json={"name": "Sneaky"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Config API
# ---------------------------------------------------------------------------


class TestConfigApi:
    """Config via config API. Env vars via Variables API."""

    def _create_agent(self, client: TestClient, auth_headers) -> str:
        resp = client.post("/api/agents", json={"name": "SecretAgent"}, headers=auth_headers)
        return resp.json()["id"]

    def test_config_returns_ok(self, client: TestClient, auth_headers):
        agent_id = self._create_agent(client, auth_headers)
        resp = client.get(f"/api/agents/{agent_id}/config", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "_meta" in body

    def test_config_requires_auth(self, client: TestClient, auth_headers):
        agent_id = self._create_agent(client, auth_headers)
        resp = client.get(f"/api/agents/{agent_id}/config")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Variables API (env vars for process/container; maps to Variables tab)
# ---------------------------------------------------------------------------


class TestVariablesApi:
    """Env variables are managed via Variables API (GET/PUT /api/agents/{id}/variables)."""

    def _create_agent(self, client: TestClient, auth_headers) -> str:
        resp = client.post("/api/agents", json={"name": "VarAgent"}, headers=auth_headers)
        return resp.json()["id"]

    def test_get_variables_defaults_on_create(self, client: TestClient, auth_headers):
        """Newly created agents get default git identity variables (non-secret, visible)."""
        agent_id = self._create_agent(client, auth_headers)
        resp = client.get(f"/api/agents/{agent_id}/variables", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "GIT_AUTHOR_NAME" in body
        assert "GIT_AUTHOR_EMAIL" in body
        assert body["GIT_AUTHOR_NAME"] == "VarAgent"

    def test_put_variables_success(self, client: TestClient, auth_headers):
        agent_id = self._create_agent(client, auth_headers)
        resp = client.put(
            f"/api/agents/{agent_id}/variables",
            json={"variables": {"MY_API_KEY": "secret-value-123"}, "secret_keys": ["MY_API_KEY"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "MY_API_KEY" in body
        assert body["MY_API_KEY"].startswith("***")

    def test_variables_persisted(self, client: TestClient, auth_headers):
        agent_id = self._create_agent(client, auth_headers)
        client.put(
            f"/api/agents/{agent_id}/variables",
            json={"variables": {"PERSIST_KEY": "persistent"}, "secret_keys": ["PERSIST_KEY"]},
            headers=auth_headers,
        )
        resp = client.get(f"/api/agents/{agent_id}/variables", headers=auth_headers)
        val = resp.json().get("PERSIST_KEY")
        assert val is not None
        assert val.startswith("***")

    def test_variables_requires_auth(self, client: TestClient, auth_headers):
        agent_id = self._create_agent(client, auth_headers)
        resp = client.get(f"/api/agents/{agent_id}/variables")
        assert resp.status_code == 401

    def test_variables_non_secret_visible(self, client: TestClient, auth_headers):
        """Non-secret variables are returned as plain values."""
        agent_id = self._create_agent(client, auth_headers)
        client.put(
            f"/api/agents/{agent_id}/variables",
            json={
                "variables": {
                    "API_KEY": "secret",  # pragma: allowlist secret
                    "LOG_LEVEL": "debug",
                },
                "secret_keys": ["API_KEY"],
            },
            headers=auth_headers,
        )
        resp = client.get(f"/api/agents/{agent_id}/variables", headers=auth_headers)
        body = resp.json()
        assert body["API_KEY"].startswith("***")
        assert body["LOG_LEVEL"] == "debug"

    def test_variables_merge(self, client: TestClient, auth_headers):
        agent_id = self._create_agent(client, auth_headers)
        client.put(
            f"/api/agents/{agent_id}/variables",
            json={"variables": {"KEY1": "val1"}, "secret_keys": []},
            headers=auth_headers,
        )
        client.put(
            f"/api/agents/{agent_id}/variables",
            json={"variables": {"KEY2": "val2"}, "secret_keys": []},
            headers=auth_headers,
        )
        resp = client.get(f"/api/agents/{agent_id}/variables", headers=auth_headers)
        assert "KEY1" in resp.json()
        assert "KEY2" in resp.json()


# ---------------------------------------------------------------------------
# Stream token integration
# ---------------------------------------------------------------------------


class TestStreamToken:
    def test_stream_token_verifiable(self, client: TestClient, auth_headers):
        """Stream token issued by endpoint must be verifiable via the library."""
        from clawforce.core.stream_token import verify_stream_token

        resp = client.post("/api/auth/stream-token", headers=auth_headers)
        token = resp.json()["token"]
        claims = verify_stream_token(token)
        assert claims is not None
        assert "sub" in claims

    def test_stream_token_expires(self):
        """Expired tokens should not verify."""
        import time

        from clawforce.core.stream_token import _tokens, create_stream_token, verify_stream_token

        token = create_stream_token({"sub": "test"})
        # Manually expire it
        claims, _ = _tokens[token]
        _tokens[token] = (claims, time.monotonic() - 1)

        assert verify_stream_token(token) is None

    def test_invalid_stream_token_returns_none(self):
        from clawforce.core.stream_token import verify_stream_token

        assert verify_stream_token("totally-fake-token") is None
        assert verify_stream_token("") is None
