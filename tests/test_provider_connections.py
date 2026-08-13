from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.database import Base
from organization_workspace.models import Organization
from provider_connections.crypto import SecretCipher
from provider_connections.models import ProviderConnection
from provider_connections.repository import ProviderConnectionRepository
from provider_connections.schemas import ConnectionCreate
from provider_connections.service import (
    ProviderConnectionError,
    ProviderConnectionService,
    ProviderDetector,
)


def service() -> tuple[ProviderConnectionService, Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add(Organization(id=1, name="Test", slug="test"))
    db.commit()
    return ProviderConnectionService(
        ProviderConnectionRepository(db), SecretCipher("x" * 40)
    ), db


def test_detector_recognizes_unique_keys_without_network_probe() -> None:
    assert ProviderDetector.detect("sk-or-v1-example") == "openrouter"
    assert ProviderDetector.detect("gsk_example") == "groq"
    with pytest.raises(ProviderConnectionError, match="неоднозначен"):
        ProviderDetector.detect("sk-common-format")


@patch("provider_connections.service.httpx.get")
def test_connection_is_verified_encrypted_and_never_returns_secret(get: Mock) -> None:
    get.return_value = Mock(
        json=lambda: {"data": [{"id": "openrouter/free"}, {"id": "paid/model"}]},
        raise_for_status=lambda: None,
    )
    connection_service, db = service()
    secret = "sk-or-v1-super-secret-value"

    result = connection_service.create(1, 7, ConnectionCreate(api_key=secret))
    stored = db.scalar(select(ProviderConnection))

    assert result.provider == "openrouter"
    assert result.status == "CONNECTED"
    assert result.masked_key.endswith("alue")
    assert secret not in result.model_dump_json()
    assert stored is not None
    assert secret not in stored.secret_ciphertext
    assert connection_service.cipher.decrypt(stored.secret_ciphertext) == secret


@patch("provider_connections.service.httpx.get")
def test_connection_failure_is_sanitized_and_persisted(get: Mock) -> None:
    import httpx

    request = httpx.Request("GET", "https://example.invalid")
    response = httpx.Response(401, request=request)
    get.return_value = Mock(
        raise_for_status=Mock(
            side_effect=httpx.HTTPStatusError(
                "secret detail", request=request, response=response
            )
        )
    )
    connection_service, db = service()

    with pytest.raises(ProviderConnectionError, match="HTTP 401"):
        connection_service.create(1, 7, ConnectionCreate(api_key="gsk_invalid-secret"))

    stored = db.scalar(select(ProviderConnection))
    assert stored is not None
    assert stored.status == "UNAVAILABLE"
    assert stored.last_checked_at is not None
    assert "invalid-secret" not in (stored.last_error or "")
