from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from competitor_intelligence.social_monitor import HttpSocialCollector, SocialMonitorError
from competitor_intelligence.telegram_connector import TelegramConnectionService, TelegramMessage


@pytest.mark.parametrize("field", ["channelId", "externalId"])
def test_youtube_accepts_current_and_legacy_channel_metadata(monkeypatch, field):
    channel_id = "UC" + "a" * 22
    calls = []

    def get(url, params=None):
        calls.append((url, params))
        return SimpleNamespace(
            text=(f'{{"{field}" : "{channel_id}"}}' if params is None else "<feed/>")
        )

    monkeypatch.setattr(HttpSocialCollector, "_get", staticmethod(get))
    assert HttpSocialCollector()._youtube("Example") == []
    assert calls[-1][1] == {"channel_id": channel_id}


def test_telegram_collector_routes_through_tenant_connection(monkeypatch):
    db = object()
    source = SimpleNamespace(platform="TELEGRAM", external_id="example")
    seen = []

    def collect(self, item):
        seen.append((self.db, item))
        return ["post"]

    monkeypatch.setattr(
        TelegramConnectionService, "__init__", lambda self, session: setattr(self, "db", session)
    )
    monkeypatch.setattr(TelegramConnectionService, "channel_posts", collect)
    assert HttpSocialCollector(db).collect(source, None) == ["post"]
    assert seen == [(db, source)]


def test_channel_posts_uses_source_owner_and_preserves_post_identity():
    service = object.__new__(TelegramConnectionService)
    service.db = SimpleNamespace(scalar=lambda query: 42)
    owners = []
    service._required = lambda owner: (
        owners.append(owner)
        or SimpleNamespace(
            status="CONNECTED", encrypted_session="session", api_id=123, encrypted_api_hash="hash"
        )
    )
    service.cipher = SimpleNamespace(decrypt=lambda value: value)
    service._proxy = lambda item: {"protocol": "MTPROXY"}
    calls = []
    message = TelegramMessage("100", "Example", "example", 7, "Post", datetime.now(UTC), 10, 2)
    service.gateway = SimpleNamespace(
        channel_messages=lambda *args: calls.append(args) or [message]
    )
    posts = service.channel_posts(SimpleNamespace(competitor_id=3, external_id="example"))
    assert owners == [42]
    assert calls[0][-1] == {"protocol": "MTPROXY"}
    assert posts[0].external_id == "example/7"
    assert posts[0].url == "https://t.me/example/7"
    assert posts[0].views == 10


def test_missing_owner_never_uses_another_telegram_account():
    service = object.__new__(TelegramConnectionService)
    service.db = SimpleNamespace(scalar=lambda query: None)
    with pytest.raises(SocialMonitorError, match="Владелец"):
        service.channel_posts(SimpleNamespace(competitor_id=3))
