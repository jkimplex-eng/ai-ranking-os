import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apikeys.repository import ApiKeyRepository
from apikeys.schemas import ApiKeyCreate
from apikeys.service import ApiKeyError, ApiKeyService
from backend.app.database import Base, get_db
from backend.app.main import app


def factory():
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def test_key_rotation_and_scope():
    engine, sessions = factory()
    with sessions() as db:
        service = ApiKeyService(ApiKeyRepository(db))
        created = service.create(ApiKeyCreate(name="CI", owner_id=1, scopes=["research:read"]))
        assert service.validate(created.secret, "research:read").owner_id == 1
        rotated = service.rotate(created.id)
        with pytest.raises(ApiKeyError):
            service.validate(created.secret)
        assert service.validate(rotated.secret).key_id == rotated.id
    engine.dispose()


def test_api_keys_api():
    engine, sessions = factory()

    def override():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    created = client.post("/api-keys", json={"name": "SDK", "owner_id": 2, "scopes": ["*"]})
    assert created.status_code == 201 and "secret" in created.json()
    assert client.post("/api-keys/validate", json={"credential": created.json()["secret"]}).json()[
        "valid"
    ]
    assert client.post(f"/api-keys/{created.json()['id']}/rotate").status_code == 200
    assert "/api-keys/validate" in app.openapi()["paths"]
    app.dependency_overrides.clear()
    engine.dispose()
