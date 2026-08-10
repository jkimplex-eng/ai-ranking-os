from collections import Counter
from datetime import UTC, datetime, timedelta
from statistics import fmean

from product_analytics.models import AnalyticsEvent, AnalyticsSession
from product_analytics.schemas import AnalyticsPeriod, DashboardRead


def _average(values: list[float]) -> float:
    return round(fmean(values), 2) if values else 0.0


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _top(values, limit: int = 10) -> list[dict]:
    return [{"key": key, "count": count} for key, count in Counter(values).most_common(limit)]


def _bucket(value: datetime, period: AnalyticsPeriod) -> str:
    if period is AnalyticsPeriod.HOURLY:
        return value.strftime("%Y-%m-%dT%H:00:00Z")
    if period is AnalyticsPeriod.DAILY:
        return value.strftime("%Y-%m-%d")
    if period is AnalyticsPeriod.WEEKLY:
        year, week, _ = value.isocalendar()
        return f"{year}-W{week:02d}"
    return value.strftime("%Y-%m")


class ProductAnalyticsEngine:
    def build(
        self,
        events: list[AnalyticsEvent],
        sessions: list[AnalyticsSession],
        period: AnalyticsPeriod,
        start: datetime,
        end: datetime,
    ) -> DashboardRead:
        def active(since: datetime) -> set[int]:
            return {
                event.user_id
                for event in events
                if event.user_id is not None and _aware(event.created_at) >= since
            }
        dau, wau, mau = len(active(end - timedelta(days=1))), len(
            active(end - timedelta(days=7))
        ), len(active(end - timedelta(days=30)))
        current_users = active(end - timedelta(days=7))
        previous_users = {
            event.user_id
            for event in events
            if event.user_id is not None
            and end - timedelta(days=14)
            <= _aware(event.created_at)
            < end - timedelta(days=7)
        }
        retention = (
            round(len(current_users & previous_users) / len(previous_users) * 100, 2)
            if previous_users
            else 0.0
        )
        research = [event for event in events if event.event_category == "RESEARCH"]
        finished = [event for event in research if event.event_name == "FINISH_RESEARCH"]
        successes = [
            event
            for event in finished
            if event.metadata_payload.get("success", True)
            and event.metadata_payload.get("status", "COMPLETED") == "COMPLETED"
        ]
        failures = [event for event in finished if event not in successes]
        reports = [event for event in events if event.event_category == "REPORT"]
        feedback = [event for event in events if event.event_category == "FEEDBACK"]
        errors = [event for event in events if event.event_category == "ERROR"]
        providers = [
            event.metadata_payload.get("provider")
            for event in events
            if event.metadata_payload.get("provider")
        ]
        bucketed: dict[str, Counter] = {}
        for event in events:
            values = bucketed.setdefault(_bucket(_aware(event.created_at), period), Counter())
            values["events"] += 1
            values["research"] += event.event_name == "CREATE_RESEARCH"
            values["reports"] += event.event_name == "OPEN_REPORT"
            values["errors"] += event.event_category == "ERROR"
            values["cost"] += float(event.metadata_payload.get("cost", 0) or 0)
        trends = [
            {"bucket": key, **{name: round(value, 6) for name, value in values.items()}}
            for key, values in sorted(bucketed.items())
        ]
        duration_values = [session.duration for session in sessions if session.duration is not None]
        research_duration = [
            float(event.metadata_payload["duration_ms"])
            for event in finished
            if event.metadata_payload.get("duration_ms") is not None
        ]
        report_duration = [
            float(event.metadata_payload["generation_ms"])
            for event in reports
            if event.metadata_payload.get("generation_ms") is not None
        ]
        token_values = [
            float(event.metadata_payload["tokens"])
            for event in events
            if event.metadata_payload.get("tokens") is not None
        ]
        cost_values = [float(event.metadata_payload.get("cost", 0) or 0) for event in events]
        cost_by_organization: Counter = Counter()
        cost_by_project: Counter = Counter()
        cost_by_model: Counter = Counter()
        for event in events:
            cost = float(event.metadata_payload.get("cost", 0) or 0)
            if event.organization_id is not None:
                cost_by_organization[event.organization_id] += cost
            if event.metadata_payload.get("project_id") is not None:
                cost_by_project[event.metadata_payload["project_id"]] += cost
            if event.metadata_payload.get("model"):
                cost_by_model[event.metadata_payload["model"]] += cost
        latency_values = [
            float(event.metadata_payload["latency_ms"])
            for event in events
            if event.metadata_payload.get("latency_ms") is not None
        ]
        visibility = [
            float(event.metadata_payload["visibility_score"])
            for event in finished
            if event.metadata_payload.get("visibility_score") is not None
        ]
        recommendations = sum(
            int(event.metadata_payload.get("recommendation_count", 0) or 0)
            for event in finished
        )
        return DashboardRead(
            period=period,
            range_start=start,
            range_end=end,
            overview={
                "events": len(events),
                "active_users": mau,
                "research": len(research),
                "reports": len(reports),
                "cost": round(sum(cost_values), 6),
            },
            users={
                "dau": dau,
                "wau": wau,
                "mau": mau,
                "retention_percent": retention,
                "top_users": _top(event.user_id for event in events if event.user_id),
            },
            organizations={
                "active": len({event.organization_id for event in events if event.organization_id}),
                "top": _top(
                    event.organization_id for event in events if event.organization_id
                ),
                "cost": [
                    {"key": key, "cost": round(value, 6)}
                    for key, value in cost_by_organization.most_common(10)
                ],
            },
            sessions={
                "count": len(sessions),
                "average_duration_seconds": _average(duration_values),
            },
            research={
                "count": len(research),
                "completed": len(successes),
                "failed": len(failures),
                "success_rate": round(len(successes) / len(finished) * 100, 2)
                if finished
                else 0.0,
                "failure_rate": round(len(failures) / len(finished) * 100, 2)
                if finished
                else 0.0,
                "average_duration_ms": _average(research_duration),
                "average_visibility": _average(visibility),
                "recommendations": recommendations,
                "queue": max(
                    0,
                    sum(event.event_name == "START_RESEARCH" for event in research)
                    - len(finished),
                ),
                "top_templates": _top(
                    event.metadata_payload.get("template")
                    for event in research
                    if event.metadata_payload.get("template")
                ),
            },
            reports={
                "count": len(reports),
                "average_generation_ms": _average(report_duration),
                "top_reports": _top(event.entity_id for event in reports if event.entity_id),
            },
            providers={
                "usage": _top(providers),
                "average_tokens": _average(token_values),
                "average_cost": _average(cost_values),
                "average_latency_ms": _average(latency_values),
                "routing_profiles": _top(
                    event.metadata_payload.get("routing_profile")
                    for event in events
                    if event.metadata_payload.get("routing_profile")
                ),
                "cost_by_project": [
                    {"key": key, "cost": round(value, 6)}
                    for key, value in cost_by_project.most_common(10)
                ],
                "cost_by_model": [
                    {"key": key, "cost": round(value, 6)}
                    for key, value in cost_by_model.most_common(10)
                ],
                "free_tokens": sum(
                    float(event.metadata_payload.get("tokens", 0) or 0)
                    for event in events
                    if event.metadata_payload.get("is_free")
                ),
                "paid_tokens": sum(
                    float(event.metadata_payload.get("tokens", 0) or 0)
                    for event in events
                    if not event.metadata_payload.get("is_free", False)
                ),
                "local": sum(
                    bool(event.metadata_payload.get("is_local")) for event in events
                ),
                "external": sum(
                    event.metadata_payload.get("provider") is not None
                    and not event.metadata_payload.get("is_local", False)
                    for event in events
                ),
            },
            feedback={"count": len(feedback)},
            errors={"count": len(errors), "top": _top(event.event_name for event in errors)},
            trends=trends,
            generated_at=datetime.now(UTC),
        )
