from types import SimpleNamespace

import httpx
import pytest

from yandex_webmaster.service import YandexWebmasterService


@pytest.mark.parametrize(
    "flags,expected",
    [
        ({"verified": True}, True),
        ({"verified": False}, False),
        ({"verified": "false"}, False),
        ({"verification": {"verification_state": "VERIFIED"}}, True),
        ({"verification": None}, False),
        ({"verified": False, "verification": {"verification_state": "VERIFIED"}}, False),
    ],
)
def test_hosts_respects_api_boolean(flags, expected):
    service = object.__new__(YandexWebmasterService)
    service._connection = lambda _: (SimpleNamespace(yandex_user_id=1), "test-token")
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"hosts": [{"host_id": "https:example.org:443", **flags}]}
            )
        )
    ) as client:
        service.client = client
        assert service.hosts(1)[0].verified is expected
