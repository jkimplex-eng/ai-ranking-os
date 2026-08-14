import hashlib
import json
import string
from itertools import product
from uuid import UUID

from frozen_prompts.models import FrozenPromptInstance, FrozenPromptSet
from frozen_prompts.repository import FrozenPromptRepository
from frozen_prompts.schemas import FanOutRequest, PromptSetCreate


class PromptSetNotFoundError(LookupError):
    pass


class FrozenPromptService:
    def __init__(self, repository: FrozenPromptRepository) -> None:
        self.repository = repository

    def create(self, payload: PromptSetCreate) -> FrozenPromptSet:
        if any(item.version == payload.version for item in self.repository.list(payload.code)):
            raise ValueError(f"Prompt set {payload.code} version {payload.version} already exists")
        templates = [item.model_dump() for item in payload.templates]
        return self.repository.save(
            FrozenPromptSet(
                **payload.model_dump(exclude={"templates"}),
                templates=templates,
                fingerprint=self._fingerprint({"templates": templates}),
                frozen=True,
            )
        )

    def activate(self, prompt_set_id: UUID) -> FrozenPromptSet:
        return self.repository.activate(self._get(prompt_set_id))

    def fan_out(self, prompt_set_id: UUID, payload: FanOutRequest) -> FrozenPromptSet:
        item = self._get(prompt_set_id)
        instances: list[FrozenPromptInstance] = []
        rendered: list[dict] = []
        for template in item.templates:
            names = [
                name for _, name, _, _ in string.Formatter().parse(template["template"]) if name
            ]
            missing = [name for name in names if name not in payload.variables]
            if missing:
                raise ValueError(f"Missing variables for {template['key']}: {', '.join(missing)}")
            values = [self._values(payload.variables[name]) for name in names]
            for combination in product(*values):
                variables = dict(zip(names, combination, strict=True))
                text = template["template"].format(**variables).strip()
                record = {
                    "template_key": template["key"],
                    "query_type": template["query_type"],
                    "text": text,
                    "variables": variables,
                }
                stable_key = self._fingerprint(record)
                rendered.append({**record, "stable_key": stable_key})
        rendered.sort(key=lambda row: (row["template_key"], row["text"], row["stable_key"]))
        current = [
            (instance.stable_key, instance.text, instance.query_type, instance.variables)
            for instance in sorted(item.instances, key=lambda value: value.position)
        ]
        requested = [
            (row["stable_key"], row["text"], row["query_type"], row["variables"])
            for row in rendered
        ]
        fingerprint = self._fingerprint(
            {"templates": item.templates, "instances": rendered, "version": item.version}
        )
        if current == requested and item.fingerprint == fingerprint:
            return item
        for position, row in enumerate(rendered):
            instances.append(
                FrozenPromptInstance(
                    stable_key=row["stable_key"],
                    text=row["text"],
                    query_type=row["query_type"],
                    variables=row["variables"],
                    position=position,
                )
            )
        item.fingerprint = fingerprint
        return self.repository.replace_instances(item, instances)

    def _get(self, prompt_set_id: UUID) -> FrozenPromptSet:
        item = self.repository.get(prompt_set_id)
        if item is None:
            raise PromptSetNotFoundError(f"Prompt set {prompt_set_id} not found")
        return item

    @staticmethod
    def _values(value: str | list[str]) -> list[str]:
        values = value if isinstance(value, list) else [value]
        cleaned = sorted({str(item).strip() for item in values if str(item).strip()})
        if not cleaned:
            raise ValueError("Fan-out variables cannot be empty")
        return cleaned

    @staticmethod
    def _fingerprint(value: object) -> str:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()
