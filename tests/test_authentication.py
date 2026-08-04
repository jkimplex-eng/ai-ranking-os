from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from authentication.dependencies import get_authentication_service
from authentication.models import AuthSession, AuthUser
from authentication.repository import SqlAlchemyAuthenticationRepository
from authentication.security import Argon2PasswordHasher, JwtTokenCodec, UtcClock
from authentication.service import AuthenticationError, AuthenticationService
from backend.app.config import get_settings
from backend.app.database import Base, get_db
from backend.app.main import app


@pytest.fixture
def auth_context():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = factory()
    settings = get_settings()
    service = AuthenticationService(
        SqlAlchemyAuthenticationRepository(db),
        Argon2PasswordHasher(),
        JwtTokenCodec(
            "unit-test-signing-material-with-sufficient-entropy",
            "HS256",
            settings.auth_jwt_issuer,
            settings.auth_jwt_audience,
        ),
        UtcClock(),
        access_minutes=15,
        refresh_days=30,
    )
    service.create_user("analyst@example.com", "correct horse battery staple", "Analyst")
    yield db, factory, service
    db.close()
    engine.dispose()


def test_password_hash_and_login(auth_context) -> None:
    db, _, service = auth_context
    user = db.query(AuthUser).one()
    assert user.password_hash.startswith("$argon2")
    assert "correct horse" not in user.password_hash
    pair = service.login("analyst@example.com", "correct horse battery staple", "127.0.0.1", "test")
    assert service.me(pair.access_token).email == "analyst@example.com"


def test_refresh_rotation_and_replay_revokes_family(auth_context) -> None:
    db, _, service = auth_context
    original = service.login("analyst@example.com", "correct horse battery staple", None, None)
    rotated = service.refresh(original.refresh_token, None, None)
    assert rotated.refresh_token != original.refresh_token
    with pytest.raises(AuthenticationError, match="reuse"):
        service.refresh(original.refresh_token, None, None)
    with pytest.raises(AuthenticationError, match="no longer valid"):
        service.authenticate(rotated.access_token)
    assert db.query(AuthSession).filter(AuthSession.revoked_at.is_(None)).count() == 0


def test_token_version_and_logout_revoke_access(auth_context) -> None:
    db, _, service = auth_context
    pair = service.login("analyst@example.com", "correct horse battery staple", None, None)
    user = db.query(AuthUser).one()
    user.token_version += 1
    db.commit()
    with pytest.raises(AuthenticationError):
        service.authenticate(pair.access_token)

    pair = service.login("analyst@example.com", "correct horse battery staple", None, None)
    service.logout(pair.access_token)
    with pytest.raises(AuthenticationError):
        service.authenticate(pair.access_token)


def test_auth_api_and_openapi(auth_context) -> None:
    db, factory, service = auth_context

    def override_db():
        with factory() as session:
            yield session

    def override_service():
        with factory() as session:
            settings = get_settings()
            yield AuthenticationService(
                SqlAlchemyAuthenticationRepository(session),
                Argon2PasswordHasher(),
                JwtTokenCodec(
                    "unit-test-signing-material-with-sufficient-entropy",
                    "HS256",
                    settings.auth_jwt_issuer,
                    settings.auth_jwt_audience,
                ),
                UtcClock(),
                access_minutes=15,
                refresh_days=30,
            )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_authentication_service] = override_service
    client = TestClient(app)
    response = client.post(
        "/auth/login",
        json={"email": "analyst@example.com", "password": "correct horse battery staple"},
    )
    assert response.status_code == 200
    tokens = response.json()
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["display_name"] == "Analyst"
    refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert client.get("/auth/me").status_code == 401
    assert {"/auth/login", "/auth/logout", "/auth/refresh", "/auth/me"} <= set(
        app.openapi()["paths"]
    )
    app.dependency_overrides.clear()
    assert datetime.now(UTC).year >= 2026
