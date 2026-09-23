import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import backend.app.main  # noqa: F401 - load ORM relationship targets
from backend.app.database import Base
from eis.repository import EISRepository
from eis.schemas import EISCalculateRequest
from eis.service import EISService
from frozen_prompts.repository import FrozenPromptRepository
from frozen_prompts.schemas import FanOutRequest, PromptSetCreate
from frozen_prompts.service import FrozenPromptService
from geo_platforms.repository import PlatformRepository
from geo_platforms.schemas import PlatformCreate
from geo_platforms.service import PlatformService
from organization_workspace.models import Organization


def _prompt_payload() -> PromptSetCreate:
    return PromptSetCreate.model_validate({
        "code": "buyer-questions", "version": 1, "name": "Buyer questions",
        "category": "BEAUTY", "language": "ru", "region": "RU",
        "templates": [{
            "key": "category", "query_type": "CATEGORY",
            "template": "Как выбрать {category}?",
        }],
    })


def test_prompt_sets_instances_activation_and_eis_are_tenant_scoped() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            Organization(id=1, name="First", slug="first"),
            Organization(id=2, name="Second", slug="second"),
        ])
        db.commit()
        prompts = FrozenPromptRepository(db)
        service = FrozenPromptService(prompts)

        db.info["geo_organization_id"] = 1
        first = service.create(_prompt_payload())
        first = service.fan_out(first.id, FanOutRequest(variables={"category": "крем"}))
        first_instance_id = first.instances[0].id
        service.activate(first.id)
        assert first.organization_id == 1

        db.info["geo_organization_id"] = 2
        assert prompts.list() == []
        assert prompts.get(first.id) is None
        assert prompts.get_instance(first_instance_id) is None
        second = service.create(_prompt_payload())
        assert second.organization_id == 2
        assert second.id != first.id
        second = service.fan_out(second.id, FanOutRequest(variables={"category": "сыворотку"}))
        service.activate(second.id)
        assert second.active is True

        platform = PlatformService(PlatformRepository(db)).create(
            PlatformCreate(name="Media", domain="example.ru", evidence={})
        )
        scorer = EISService(EISRepository(db), PlatformRepository(db), prompts)
        with pytest.raises(LookupError, match="Query"):
            scorer.calculate(EISCalculateRequest(
                platform_id=platform.id, query_id=first_instance_id, ai_engine="YandexGPT"
            ))

        db.info["geo_organization_id"] = 1
        assert prompts.get(first.id) is not None
        assert prompts.get_instance(first_instance_id) is not None
        assert prompts.get(second.id) is None
        assert prompts.get_instance(second.instances[0].id) is None
        assert prompts.get(first.id).active is True
    engine.dispose()
