from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from alice_learning.automation_ports import (
    AutomationLaunchRequest,
    AutomationNotificationPort,
    AutomationResearchPort,
    AutomationTemplatePort,
)
from alice_learning.automation_repository import AliceAutomationRepository
from alice_learning.automation_schemas import (
    AutomationDashboard,
    AutomationPlanCreate,
    AutomationPlanRead,
    AutomationPlanUpdate,
    AutomationRunRead,
)
from alice_learning.models import AliceAutomationPlan, AliceAutomationRun, AliceQuerySet


class AliceAutomationError(ValueError):
    pass


class AliceAutomationService:
    """Automate reproducible Alice observations without claiming black-box causality."""

    VERSION = "1.0"

    def __init__(
        self,
        repository: AliceAutomationRepository,
        research: AutomationResearchPort,
        templates: AutomationTemplatePort,
        notifications: AutomationNotificationPort,
        *,
        clock=lambda: datetime.now(UTC),
    ) -> None:
        self.repository = repository
        self.research = research
        self.templates = templates
        self.notifications = notifications
        self.clock = clock

    def create(
        self, organization_id: int, owner_user_id: int, payload: AutomationPlanCreate
    ) -> AliceAutomationPlan:
        context = self.templates.context(
            organization_id, payload.template_research_id, str(payload.website_url)
        )
        now = self._aware(self.clock())
        plan = self.repository.save(
            AliceAutomationPlan(
                organization_id=organization_id,
                owner_user_id=owner_user_id,
                template_research_id=payload.template_research_id,
                brand=payload.brand.strip(),
                website_url=str(payload.website_url),
                language=payload.language,
                region=payload.region,
                research_profile=payload.research_profile,
                routing_profile=payload.routing_profile,
                models=payload.models,
                repetitions=payload.repetitions,
                daily_query_limit=payload.daily_query_limit,
                weekly_query_limit=payload.weekly_query_limit,
                daily_budget_usd=payload.daily_budget_usd,
                monthly_budget_usd=payload.monthly_budget_usd,
                monitoring_frequency=payload.monitoring_frequency,
                is_enabled=payload.is_enabled,
                next_run_at=self._next_run(now, payload.monitoring_frequency),
            )
        )
        self._query_set(plan, "CONTROL", list(context.queries), context.metadata)
        self._query_set(plan, "ADAPTIVE", list(context.queries), context.metadata)
        return plan

    def update(self, organization_id: int, plan_id: int, payload: AutomationPlanUpdate):
        plan = self._plan(organization_id, plan_id)
        values = payload.model_dump(exclude_unset=True)
        daily = values.get("daily_budget_usd", plan.daily_budget_usd)
        monthly = values.get("monthly_budget_usd", plan.monthly_budget_usd)
        if monthly < daily:
            raise AliceAutomationError("Месячный бюджет не может быть меньше дневного")
        for key, value in values.items():
            setattr(plan, key, value)
        if "monitoring_frequency" in values:
            plan.next_run_at = self._next_run(self._aware(self.clock()), plan.monitoring_frequency)
        return self.repository.save(plan)

    def list(self, organization_id: int):
        return self.repository.plans(organization_id)

    def dashboard(self, organization_id: int) -> AutomationDashboard:
        return AutomationDashboard(
            plans=[AutomationPlanRead.model_validate(item) for item in self.list(organization_id)],
            latest_runs=[
                AutomationRunRead.model_validate(item)
                for item in self.repository.runs(organization_id)
            ],
            methodology={
                "version": self.VERSION,
                "daily": "Frozen control queries; three independent repetitions by default.",
                "weekly": "Control plus adaptive buyer, competitor and observed-demand queries.",
                "monthly": "Full set used as a stable long-window checkpoint.",
                "causality": (
                    "Model associations are hypotheses. Causal impact requires a pre-registered "
                    "publication experiment and a holdout or before/after verification window."
                ),
            },
        )

    def run_due(self) -> list[AliceAutomationRun]:
        now = self._aware(self.clock())
        results = []
        for plan in self.repository.due(now):
            kind = plan.monitoring_frequency
            results.append(
                self.run(plan.organization_id, plan.id, kind, scheduled_for=plan.next_run_at)
            )
        return results

    def run(
        self,
        organization_id: int,
        plan_id: int,
        kind: str,
        *,
        scheduled_for: datetime | None = None,
    ) -> AliceAutomationRun:
        plan = self._plan(organization_id, plan_id)
        if self.repository.active_run(plan.id):
            raise AliceAutomationError("Автоматическое исследование уже выполняется")
        now = self._aware(self.clock())
        context = self.templates.context(
            organization_id, plan.template_research_id, plan.website_url
        )
        query_kind = "CONTROL" if kind == "DAILY" else "ADAPTIVE"
        query_set = self._query_set(plan, query_kind, list(context.queries), context.metadata)
        limit = plan.daily_query_limit if kind == "DAILY" else plan.weekly_query_limit
        base_queries = [str(item["text"]) for item in query_set.queries[:limit]]
        queries = tuple(query for query in base_queries for _ in range(plan.repetitions))
        task_count = len(queries) * max(len(plan.models), 1)
        estimated = round(task_count * (0.0 if self._all_local(plan.models) else 0.01), 6)
        spent_daily, spent_monthly = self._spent(plan, now)
        if (
            spent_daily + estimated > plan.daily_budget_usd
            or spent_monthly + estimated > plan.monthly_budget_usd
        ):
            run = self.repository.save(
                AliceAutomationRun(
                    plan_id=plan.id,
                    query_set_id=query_set.id,
                    run_kind=kind,
                    status="BUDGET_BLOCKED",
                    task_count=task_count,
                    estimated_cost_usd=estimated,
                    scheduled_for=scheduled_for or now,
                    started_at=now,
                    finished_at=now,
                    error="Автоматический запуск остановлен бюджетным ограничением",
                    result={"daily_spent": spent_daily, "monthly_spent": spent_monthly},
                )
            )
            self._notify(
                plan,
                "BUDGET_EXCEEDED",
                "Автоматическое исследование остановлено",
                "Дневной или месячный бюджет проекта исчерпан",
                "HIGH",
                run.id,
            )
            plan.next_run_at = self._next_run(now, plan.monitoring_frequency)
            self.repository.save(plan)
            return run
        run = AliceAutomationRun(
            plan_id=plan.id,
            query_set_id=query_set.id,
            run_kind=kind,
            status="RUNNING",
            task_count=task_count,
            estimated_cost_usd=estimated,
            scheduled_for=scheduled_for or now,
            started_at=now,
        )
        try:
            self.repository.save(run)
        except IntegrityError as error:
            raise AliceAutomationError("Автоматическое исследование уже выполняется") from error
        try:
            result = self.research.launch(
                AutomationLaunchRequest(
                    owner_user_id=plan.owner_user_id,
                    template_research_id=plan.template_research_id,
                    brand=plan.brand,
                    website_url=plan.website_url,
                    language=plan.language,
                    region=plan.region,
                    research_profile=plan.research_profile,
                    routing_profile=plan.routing_profile,
                    models=tuple(plan.models),
                    queries=queries,
                )
            )
            run.research_id = result.research_id
            run.actual_cost_usd = result.actual_cost_usd
            run.result = result.result
            run.error = result.error
            run.status = "COMPLETED" if result.succeeded else "FAILED"
        except Exception as error:  # noqa: BLE001 - persisted automation boundary
            run.status = "FAILED"
            run.error = str(error)[:4000]
        run.finished_at = self._aware(self.clock())
        plan.last_run_at = run.finished_at
        plan.next_run_at = self._next_run(run.finished_at, plan.monitoring_frequency)
        self.repository.save(run)
        self.repository.save(plan)
        event = "RESEARCH_COMPLETED" if run.status == "COMPLETED" else "RESEARCH_FAILED"
        self._notify(
            plan,
            event,
            "Автоматическое исследование Алисы завершено"
            if run.status == "COMPLETED"
            else "Ошибка автоматического исследования Алисы",
            f"Бренд: {plan.brand}; режим: {kind}; проверок: {task_count}",
            "NORMAL" if run.status == "COMPLETED" else "HIGH",
            run.id,
        )
        return run

    def _query_set(self, plan, kind: str, rows: list[dict], metadata: dict) -> AliceQuerySet:
        cleaned = self._select_queries(rows, kind, plan)
        raw = json.dumps(cleaned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(raw.encode()).hexdigest()
        latest = self.repository.latest_query_set(plan.id, kind)
        if latest and latest.fingerprint == fingerprint:
            return latest
        return self.repository.save(
            AliceQuerySet(
                plan_id=plan.id,
                version=(latest.version + 1 if latest else 1),
                kind=kind,
                fingerprint=fingerprint,
                queries=cleaned,
                source_metadata={**metadata, "algorithm_version": self.VERSION},
            )
        )

    @staticmethod
    def _select_queries(rows: list[dict], kind: str, plan) -> list[dict]:
        unique = []
        seen = set()
        for row in rows:
            text = str(row.get("text", "")).strip()
            if not text or text.casefold() in seen:
                continue
            seen.add(text.casefold())
            unique.append({**row, "text": text})
        if kind == "ADAPTIVE":
            return unique[: plan.weekly_query_limit]
        priority = {
            "category_discovery": 0,
            "problem_solution": 1,
            "brand_control": 2,
            "yandex_webmaster_observed": 3,
            "price_comparison": 4,
        }
        unique.sort(key=lambda item: (priority.get(item.get("cluster"), 9), item.get("id", "")))
        return unique[: plan.daily_query_limit]

    def _spent(self, plan, now):
        runs = self.repository.runs(plan.organization_id, limit=1000)
        values = [
            (self._aware(item.started_at), float(item.actual_cost_usd or 0))
            for item in runs
            if item.plan_id == plan.id
        ]
        daily = sum(cost for at, cost in values if at.date() == now.date())
        monthly = sum(cost for at, cost in values if (at.year, at.month) == (now.year, now.month))
        return round(daily, 8), round(monthly, 8)

    def _plan(self, organization_id: int, plan_id: int):
        plan = self.repository.plan(plan_id)
        if plan is None:
            raise AliceAutomationError("План автоматизации не найден")
        if plan.organization_id != organization_id:
            raise PermissionError("Нет доступа к плану автоматизации")
        return plan

    def _notify(self, plan, event, title, message, priority, run_id):
        self.notifications.emit(
            event,
            title,
            message,
            user_id=plan.owner_user_id,
            resource_type="alice_automation_run",
            resource_id=str(run_id),
            metadata={"plan_id": plan.id, "brand": plan.brand},
            channels=("UI",),
            category="RESEARCH",
            priority=priority,
        )

    @staticmethod
    def _all_local(models: list[dict]) -> bool:
        return bool(models) and all(item.get("provider") in {"ollama", "local"} for item in models)

    @staticmethod
    def _next_run(value: datetime, frequency: str) -> datetime:
        days = 7 if frequency == "WEEKLY" else 1
        return value.replace(hour=3, minute=0, second=0, microsecond=0) + timedelta(days=days)

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
