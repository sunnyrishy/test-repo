"""Admin routes must be closed once a key is configured."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client_with(tmp_path):
    """A client backed by a throwaway database, so a 401 is the only thing a
    guarded route can fail on."""
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path/'auth.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()

    def _build(api_key: str) -> TestClient:
        settings = Settings(
            database_url=str(engine.url), api_key=api_key, ai_provider="mock"
        )
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_db] = lambda: session
        return TestClient(app)

    yield _build
    app.dependency_overrides.clear()
    session.close()


def test_admin_is_open_when_no_key_is_configured(client_with):
    """Local development stays frictionless."""
    assert client_with("").post("/api/admin/deduplication/run").status_code == 200


def test_admin_requires_a_key_once_configured(client_with):
    assert client_with("s3cret").post("/api/admin/deduplication/run").status_code == 401


def test_wrong_key_is_rejected(client_with):
    client = client_with("s3cret")
    response = client.post(
        "/api/admin/deduplication/run", headers={"X-API-Key": "guess"}
    )
    assert response.status_code == 401


def test_correct_key_is_accepted(client_with):
    client = client_with("s3cret")
    response = client.post(
        "/api/admin/deduplication/run", headers={"X-API-Key": "s3cret"}
    )
    assert response.status_code == 200


def test_bearer_token_is_accepted_for_vercel_cron(client_with):
    """Vercel Cron authenticates with an Authorization: Bearer header."""
    client = client_with("s3cret")
    response = client.get(
        "/api/admin/cron", headers={"Authorization": "Bearer s3cret"}
    )
    assert response.status_code != 401


def test_cron_rejects_a_wrong_bearer_token(client_with):
    client = client_with("s3cret")
    assert (
        client.get("/api/admin/cron", headers={"Authorization": "Bearer nope"}).status_code
        == 401
    )


def test_reading_jobs_does_not_require_the_key(client_with):
    assert client_with("s3cret").get("/api/jobs").status_code == 200


def test_profile_writes_are_guarded_but_reads_are_not(client_with):
    client = client_with("s3cret")
    assert client.get("/api/profile").status_code == 200
    assert client.put("/api/profile", json={}).status_code == 401
