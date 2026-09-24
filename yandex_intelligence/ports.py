from typing import Protocol

from yandex_webmaster.schemas import WebmasterEvidenceRead


class WebmasterEvidencePort(Protocol):
    def evidence(self, organization_id: int) -> WebmasterEvidenceRead: ...
