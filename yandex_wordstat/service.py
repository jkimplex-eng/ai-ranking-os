from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from provider_connections.crypto import SecretCipher
from research.models import ExtractedEntity, Research, ResearchTask, Response
from yandex_wordstat.models import WordstatConnection, WordstatDemandSnapshot
from yandex_wordstat.repository import WordstatRepository
from yandex_wordstat.schemas import (
    WordstatAnalyticsRead,
    WordstatConnectionRead,
    WordstatDiscoveryRequest,
    WordstatQueryAnalyticsItem,
    WordstatQueryRead,
    WordstatSnapshotRead,
)


class WordstatError(ValueError):
    pass


class WordstatService:
    BASE_URL = "https://searchapi.api.cloud.yandex.net"
    VERSION = "1.0"

    def __init__(
        self,
        db: Session,
        repository: WordstatRepository,
        cipher: SecretCipher,
        client: httpx.Client | None = None,
    ) -> None:
        self.db = db
        self.repository = repository
        self.cipher = cipher
        self.client = client or httpx.Client(timeout=30)

    def connect(
        self,
        organization_id: int,
        user_id: int,
        folder_id: str,
        auth_type: str,
        credential: str,
    ) -> WordstatConnectionRead:
        self._request(
            credential,
            auth_type,
            "/v2/wordstat/topRequests",
            {
                "phrase": "яндекс",
                "numPhrases": 1,
                "regions": ["213"],
                "devices": ["DEVICE_ALL"],
                "folderId": folder_id.strip(),
            },
        )
        now = datetime.now(UTC)
        connection = self.repository.connection(organization_id)
        if connection is None:
            connection = WordstatConnection(
                organization_id=organization_id,
                folder_id=folder_id.strip(),
                auth_type=auth_type,
                credential_ciphertext=self.cipher.encrypt(credential.strip()),
                created_by=user_id,
            )
        else:
            connection.folder_id = folder_id.strip()
            connection.auth_type = auth_type
            connection.credential_ciphertext = self.cipher.encrypt(credential.strip())
        connection.status = "CONNECTED"
        connection.last_checked_at = now
        connection.last_success_at = now
        connection.last_error = None
        return self.read(self.repository.save(connection))

    def status(self, organization_id: int) -> WordstatConnectionRead:
        return self.read(self.repository.connection(organization_id))

    def disconnect(self, organization_id: int) -> None:
        connection = self.repository.connection(organization_id)
        if connection:
            self.repository.delete(connection)

    def discover(
        self, organization_id: int, user_id: int, payload: WordstatDiscoveryRequest
    ) -> WordstatSnapshotRead:
        connection, credential = self._connection(organization_id)
        device_names = {
            "all": "DEVICE_ALL",
            "desktop": "DEVICE_DESKTOP",
            "phone": "DEVICE_PHONE",
            "tablet": "DEVICE_TABLET",
        }
        request_payload: dict[str, object] = {
            "phrase": payload.category.strip(),
            "numPhrases": min(payload.limit * 3, 150),
            "devices": [device_names[payload.device]],
            "folderId": connection.folder_id,
        }
        if payload.region_ids:
            request_payload["regions"] = [str(value) for value in payload.region_ids]
        data = self._request(
            credential,
            connection.auth_type,
            "/v2/wordstat/topRequests",
            request_payload,
        )
        rows: list[tuple[str, int, str]] = []
        for key, source_type in (("results", "TOP"), ("associations", "SIMILAR")):
            for item in data.get(key, []) if isinstance(data, dict) else []:
                if not isinstance(item, dict):
                    continue
                query = str(item.get("phrase", "")).strip()
                count = int(item.get("count") or 0)
                if query and count >= 0:
                    rows.append((query, count, source_type))
        deduplicated: dict[str, tuple[str, int, str]] = {}
        for query, count, source_type in rows:
            normalized = " ".join(query.casefold().split())
            previous = deduplicated.get(normalized)
            if previous is None or count > previous[1]:
                deduplicated[normalized] = (query, count, source_type)
        ordered = sorted(deduplicated.values(), key=lambda item: (-item[1], item[0]))
        brand_key = payload.brand.casefold().strip()
        unbranded = [item for item in ordered if brand_key not in item[0].casefold()]
        branded = [item for item in ordered if brand_key in item[0].casefold()]
        selected = [*unbranded[: payload.limit], *branded[:2]]
        queries = [
            WordstatQueryRead(
                query=query,
                frequency=count,
                demand_rank=index,
                source_type=source_type,
                branded=brand_key in query.casefold(),
                selected_for_alice=index <= payload.limit,
            )
            for index, (query, count, source_type) in enumerate(selected, 1)
        ]
        snapshot = self.repository.save(
            WordstatDemandSnapshot(
                organization_id=organization_id,
                brand=payload.brand.strip(),
                category=payload.category.strip(),
                region_ids=payload.region_ids,
                device=payload.device,
                status="READY" if queries else "EMPTY",
                queries=[item.model_dump(mode="json") for item in queries],
                raw_count=len(rows),
                limitations=[
                    "Частотность Wordstat отражает запросы к Яндекс Поиску за период API, "
                    "а не число запросов к Алисе.",
                    "Проверка Алисы выполняется отдельно через подключённый YandexGPT; "
                    "публичный интерфейс Алисы может отличаться.",
                    "Совпадение частотности и рекомендации является наблюдением, "
                    "а не доказательством причинного влияния.",
                ],
                algorithm_version=self.VERSION,
                created_by=user_id,
            )
        )
        connection.last_checked_at = datetime.now(UTC)
        connection.last_success_at = connection.last_checked_at
        connection.last_error = None
        self.repository.save(connection)
        return self._snapshot(snapshot)

    def latest(self, organization_id: int, brand: str | None = None) -> WordstatSnapshotRead:
        snapshot = self.repository.latest(organization_id, brand)
        if snapshot is None:
            raise WordstatError("Исследование спроса Wordstat ещё не выполнялось")
        return self._snapshot(snapshot)

    def analytics(self, organization_id: int, brand: str | None = None) -> WordstatAnalyticsRead:
        snapshot = self.repository.latest(organization_id, brand)
        if snapshot is None:
            raise WordstatError("Сначала соберите частотные запросы Wordstat")
        queries = [WordstatQueryRead.model_validate(item) for item in snapshot.queries]
        query_keys = {item.query.casefold().strip(): item for item in queries}
        researches = list(
            self.db.scalars(select(Research).order_by(Research.created_at.desc()).limit(100))
        )
        matching_researches = [
            item
            for item in researches
            if item.metadata_payload.get("organization_id") == organization_id
            and str(item.metadata_payload.get("brand", "")).casefold() == snapshot.brand.casefold()
        ]
        research_ids = [item.id for item in matching_researches]
        rows = []
        if research_ids:
            rows = self.db.execute(
                select(Response, ResearchTask)
                .join(ResearchTask, Response.research_task_id == ResearchTask.id)
                .where(
                    ResearchTask.research_id.in_(research_ids),
                    Response.provider.in_(["yandex", "yandexgpt"]),
                )
            ).all()
        grouped: dict[str, list[tuple[Response, ResearchTask]]] = {key: [] for key in query_keys}
        for response, task in rows:
            key = " ".join(task.query.casefold().split())
            if key in grouped:
                grouped[key].append((response, task))
        items = []
        numerator = 0.0
        denominator = 0.0
        for key, query in query_keys.items():
            observations = grouped[key]
            mentions = 0
            recommendations = 0
            competitors: set[str] = set()
            domains: set[str] = set()
            used_researches: set[int] = set()
            for response, task in observations:
                content = response.content.casefold()
                mentioned = snapshot.brand.casefold() in content
                recommended = mentioned and any(
                    token in content for token in ("рекоменд", "совету", "подойд", "выбор")
                )
                mentions += int(mentioned)
                recommendations += int(recommended)
                used_researches.add(task.research_id)
                for url in re.findall(r"https?://[^\s)\]}>]+", response.content):
                    domain = (urlparse(url).hostname or "").casefold().removeprefix("www.")
                    if domain:
                        domains.add(domain)
                entity_rows = self.db.scalars(
                    select(ExtractedEntity).where(
                        ExtractedEntity.response_id == response.id,
                        ExtractedEntity.entity_type == "BRAND",
                    )
                )
                competitors.update(
                    entity.canonical_name
                    for entity in entity_rows
                    if entity.canonical_name.casefold() != snapshot.brand.casefold()
                )
            response_count = len(observations)
            if response_count:
                denominator += query.frequency
                numerator += query.frequency * (recommendations / response_count)
            items.append(
                WordstatQueryAnalyticsItem(
                    query=query.query,
                    frequency=query.frequency,
                    demand_rank=query.demand_rank,
                    response_count=response_count,
                    mention_count=mentions,
                    recommendation_count=recommendations,
                    mention_rate=round(mentions / response_count * 100, 1) if response_count else 0,
                    recommendation_rate=(
                        round(recommendations / response_count * 100, 1) if response_count else 0
                    ),
                    competing_brands=sorted(competitors),
                    citation_domains=sorted(domains),
                    evidence_status="MEASURED" if response_count else "NOT_MEASURED",
                    research_ids=sorted(used_researches),
                )
            )
        checked = sum(item.response_count > 0 for item in items)
        return WordstatAnalyticsRead(
            snapshot_id=snapshot.id,
            brand=snapshot.brand,
            category=snapshot.category,
            query_count=len(items),
            checked_query_count=checked,
            total_frequency=sum(item.frequency for item in queries),
            weighted_visibility=round(numerator / denominator * 100, 1) if denominator else None,
            numerator=round(numerator, 4),
            denominator=round(denominator, 4),
            status="MEASURED"
            if checked == len(items) and items
            else "PARTIAL"
            if checked
            else "NOT_MEASURED",
            items=items,
            methodology_version=self.VERSION,
            limitations=[
                "Взвешенная видимость = сумма(частотность × доля рекомендаций бренда) / "
                "сумма частотностей проверенных запросов.",
                "Непроверенные запросы не входят в знаменатель и явно помечены NOT_MEASURED.",
                "Метрика относится только к сохранённой выборке Wordstat, региону, "
                "периоду и ответам YandexGPT.",
            ],
        )

    @staticmethod
    def read(connection: WordstatConnection | None) -> WordstatConnectionRead:
        if connection is None:
            return WordstatConnectionRead(connected=False, status="NOT_CONFIGURED")
        return WordstatConnectionRead(
            connected=connection.status == "CONNECTED",
            status=connection.status,
            folder_id=connection.folder_id,
            auth_type=connection.auth_type,
            last_checked_at=connection.last_checked_at,
            last_success_at=connection.last_success_at,
            last_error=connection.last_error,
        )

    def _connection(self, organization_id: int) -> tuple[WordstatConnection, str]:
        connection = self.repository.connection(organization_id)
        if connection is None:
            raise WordstatError("Сначала подключите API Яндекс Wordstat в настройках")
        try:
            credential = self.cipher.decrypt(connection.credential_ciphertext)
        except ValueError as error:
            raise WordstatError("Сохранённый токен Wordstat не удалось расшифровать") from error
        return connection, credential

    def _request(
        self,
        credential: str,
        auth_type: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> dict:
        try:
            response = self.client.request(
                "POST",
                self.BASE_URL + path,
                headers={
                    "Authorization": (
                        f"Api-key {credential}"
                        if auth_type == "API_KEY"
                        else f"Bearer {credential}"
                    ),
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.HTTPError as error:
            raise WordstatError("Не удалось соединиться с API Яндекс Wordstat") from error
        if response.status_code == 401:
            raise WordstatError("Яндекс отклонил API-ключ или IAM-токен Wordstat")
        if response.status_code == 403:
            raise WordstatError(
                "Нет доступа к Wordstat: проверьте роль search-api.webSearch.user, "
                "область API-ключа yc.search-api.execute и идентификатор каталога."
            )
        if response.status_code == 429:
            raise WordstatError("Исчерпана персональная квота Wordstat; повторите позже")
        if response.status_code >= 400:
            raise WordstatError(f"Wordstat API вернул HTTP {response.status_code}")
        data = response.json()
        return data if isinstance(data, dict) else {"items": data}

    @staticmethod
    def _snapshot(item: WordstatDemandSnapshot) -> WordstatSnapshotRead:
        return WordstatSnapshotRead(
            id=item.id,
            organization_id=item.organization_id,
            brand=item.brand,
            category=item.category,
            region_ids=item.region_ids,
            device=item.device,
            status=item.status,
            queries=[WordstatQueryRead.model_validate(value) for value in item.queries],
            raw_count=item.raw_count,
            limitations=item.limitations,
            algorithm_version=item.algorithm_version,
            created_at=item.created_at,
        )


class WordstatQuerySource:
    """Read-only port for adding observed demand to the Research Wizard."""

    def __init__(self, db: Session) -> None:
        self.repository = WordstatRepository(db)

    def queries(self, organization_id: int, brand: str, limit: int = 12) -> tuple[int, list[str]]:
        snapshot = self.repository.latest(organization_id, brand)
        if snapshot is None:
            return 0, []
        rows = [WordstatQueryRead.model_validate(item) for item in snapshot.queries]
        selected = [item.query for item in rows if item.selected_for_alice and not item.branded]
        return snapshot.id, selected[:limit]
