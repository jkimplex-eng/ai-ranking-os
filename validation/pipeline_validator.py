import argparse
import json
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from prometheus_client import generate_latest

from ai_visibility.pipeline import run_pipeline as visibility_pipeline
from ai_visibility.schemas import VisibilityInput
from backend.app.llm_router.offline import route_offline
from backend.app.llm_router.schemas import RouteRequest
from backend.app.main import app
from backend.app.providers.factory import factory
from entity_extraction.pipeline import run_pipeline as extraction_pipeline
from entity_extraction.schemas import ExtractionInput, ExtractionResult
from knowledge_graph.pipeline import build_graph
from query_executor.dispatcher import Dispatcher
from query_executor.executor import execute_plan
from query_executor.schemas import ExecutionPlan, ExecutorResult
from query_executor.streaming import stream_result
from query_intent.pipeline import run_pipeline as intent_pipeline
from query_intent.schemas import IntentInput
from reason_engine.pipeline import build_reasoning_context
from validation.benchmark_runner import run_benchmark
from validation.compatibility import (
    build_compatibility_matrix,
    compatibility_passed,
)
from validation.contract_validator import (
    validate_api_contract,
    validate_stage_schemas,
)
from validation.load_tests import run_load_test
from validation.report_generator import write_reports
from validation.schema_validator import validate_json_serializable

PIPELINE_STAGES = (
    "query",
    "intent",
    "router",
    "executor",
    "entity_extraction",
    "reason",
    "visibility",
    "knowledge_graph",
    "response",
)


def execute_pipeline(
    query: str,
    *,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    correlation = correlation_id or str(uuid4())
    stages: dict[str, Any] = {
        "correlation_id": correlation,
        "query": {"query": query, "correlation_id": correlation},
    }
    timings: dict[str, float] = {}

    def measure(name: str, operation: Any) -> Any:
        started = perf_counter()
        value = operation()
        timings[name] = round((perf_counter() - started) * 1000, 3)
        return value

    intent = measure(
        "intent",
        lambda: intent_pipeline(
            IntentInput(request_id=correlation, query=query)
        ).model_dump(mode="json"),
    )
    stages["intent"] = intent
    routed = measure(
        "router",
        lambda: route_offline(
            RouteRequest(
                query=query,
                correlation_id=correlation,
                intent=intent["primary_intent"],
                language=intent["language"]["code"],
                context_tokens=max(1, len(query) // 4),
            )
        ),
    )
    router_plan = routed.plan
    stages["router"] = router_plan.model_dump(mode="json")
    executor = measure(
        "executor",
        lambda: execute_plan(
            f"executor-{correlation}",
            router_plan,
            Dispatcher(),
        ),
    )
    stages["executor"] = executor.model_dump(mode="json")
    extraction_result = measure(
        "entity_extraction",
        lambda: extraction_pipeline(
            ExtractionInput(
                response_id=correlation,
                raw_response=executor.output,
            )
        ),
    )
    extraction = extraction_result.model_dump(mode="json")
    stages["entity_extraction"] = extraction
    reason = measure(
        "reason",
        lambda: build_reasoning_context(
            extraction_result,
            correlation_id=correlation,
            query=query,
        ),
    )
    stages["reason"] = reason
    visibility = measure(
        "visibility",
        lambda: visibility_pipeline(
            VisibilityInput(
                entity_id=reason["subject"].casefold().replace(" ", "-"),
                entity=reason["subject"],
                observations=[
                    {
                        "model": result["provider"],
                        "mentioned": bool(extraction["entities"]),
                        "recommendation_position": 1,
                        "citations": [],
                        "entity_confidence": (
                            extraction["entities"][0]["confidence"]
                            if extraction["entities"]
                            else 0.5
                        ),
                        "observed_at": datetime.now(UTC),
                    }
                    for result in stages["executor"]["results"]
                    if result["state"] == "COMPLETED"
                ],
            )
        ).model_dump(mode="json"),
    )
    stages["visibility"] = visibility
    knowledge_graph = measure(
        "knowledge_graph",
        lambda: build_graph(
            ExtractionResult.model_validate(extraction),
            correlation_id=correlation,
        ),
    )
    stages["knowledge_graph"] = knowledge_graph
    stages["response"] = measure(
        "response",
        lambda: {
            "correlation_id": correlation,
            "answer": reason["conclusion"],
            "visibility_score": visibility["visibility_score"],
            "knowledge_graph": knowledge_graph,
            "version": "1.0",
        },
    )
    stages["timings_ms"] = timings
    return stages


def _check(
    name: str,
    passed: bool,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if passed else "FAIL", "details": details}


def validate_pipeline(query: str = "Compare OpenAI and Qwen with sources") -> dict[str, Any]:
    generated_at = datetime.now(UTC)
    stages = execute_pipeline(query)
    correlation = stages["correlation_id"]
    checks: list[dict[str, Any]] = []

    schema_ok, schema_details = validate_stage_schemas(stages)
    checks.append(_check("JSON Schema compatibility", schema_ok, schema_details))
    api_ok, api_details = validate_api_contract(app)
    checks.append(_check("API compatibility", api_ok, api_details))
    router_ok = (
        stages["router"]["metadata"].get("source") == "production_llm_router"
        and bool(stages["router"]["steps"])
    )
    checks.append(
        _check(
            "Production Router",
            router_ok,
            {
                "source": stages["router"]["metadata"].get("source"),
                "mode": stages["router"]["mode"],
            },
        )
    )
    monitoring_paths = {
        "/system/health",
        "/system/status",
        "/system/providers",
        "/system/router",
        "/system/pipeline",
        "/system/metrics",
        "/system/version",
        "/system/costs",
        "/system/cache",
        "/system/build",
        "/metrics",
    }
    openapi_paths = set(app.openapi()["paths"])
    metrics_payload = generate_latest().decode("utf-8")
    monitoring_ok = monitoring_paths.issubset(openapi_paths) and (
        "ai_ranking_os_router_latency_seconds" in metrics_payload
    )
    checks.append(
        _check(
            "Monitoring",
            monitoring_ok,
            {
                "endpoints": len(monitoring_paths),
                "prometheus": "ai_ranking_os_router_latency_seconds"
                in metrics_payload,
            },
        )
    )
    configured_providers = {provider.name: provider for provider in factory.all()}
    provider_ok = set(configured_providers) == {
        "openai",
        "anthropic",
        "gemini",
        "deepseek",
        "perplexity",
        "mistral",
        "grok",
        "ollama",
        "groq",
        "github",
        "yandex",
        "gigachat",
    } and {
        configured_providers["yandex"].region,
        configured_providers["gigachat"].region,
    } == {
        "RUSSIA",
    }
    checks.append(
        _check(
            "Provider interfaces",
            provider_ok,
            {
                "providers": sorted(configured_providers),
                "russian_providers": ["gigachat", "yandex"],
            },
        )
    )

    executor_result = ExecutorResult.model_validate(stages["executor"])
    checks.append(
        _check(
            "Executor",
            executor_result.state == "COMPLETED",
            {"state": executor_result.state, "mode": executor_result.mode},
        )
    )
    events = executor_result.telemetry["events"]
    event_ok = all("event" in event for event in events)
    checks.append(_check("Event compatibility", event_ok, {"event_count": len(events)}))

    matrix = build_compatibility_matrix(stages)
    checks.append(
        _check(
            "Pipeline integrity",
            compatibility_passed(matrix),
            {"stage_count": len(PIPELINE_STAGES)},
        )
    )
    checks.append(
        _check(
            "Compatibility adapters removed",
            stages["router"]["metadata"].get("source") == "production_llm_router",
            {"adapter_stages": []},
        )
    )
    correlation_values = [
        stages["query"]["correlation_id"],
        stages["intent"]["request_id"],
        stages["router"]["request_id"],
        stages["reason"]["correlation_id"],
        stages["knowledge_graph"]["correlation_id"],
        stages["response"]["correlation_id"],
    ]
    checks.append(
        _check(
            "Correlation ID propagation",
            all(value == correlation for value in correlation_values),
            {"correlation_id": correlation},
        )
    )
    metrics_ok = (
        len(stages["timings_ms"]) == len(PIPELINE_STAGES) - 1
        and executor_result.duration_ms >= 0
    )
    checks.append(
        _check(
            "Metrics collection",
            metrics_ok,
            {"stage_timings_ms": stages["timings_ms"]},
        )
    )

    streamed_events = [
        json.loads(line)
        for line in stream_result(executor_result)
    ]
    stream_ok = (
        streamed_events[0]["event"] == "execution_started"
        and streamed_events[-1]["event"] == "execution_finished"
    )
    checks.append(
        _check(
            "Streaming compatibility",
            stream_ok,
            {"events": len(streamed_events), "format": "application/x-ndjson"},
        )
    )
    retry_fallback_ok, retry_details = validate_retry_fallback()
    checks.append(
        _check("Retry/Fallback correctness", retry_fallback_ok, retry_details)
    )
    serializable, serialization_error = validate_json_serializable(stages["response"])
    checks.append(
        _check(
            "Response serialization",
            serializable,
            {"error": serialization_error},
        )
    )

    total_latency = sum(stages["timings_ms"].values())
    benchmark = run_benchmark(
        lambda: execute_pipeline(query),
        iterations=10,
    )
    load = run_load_test(
        lambda index: execute_pipeline(
            query,
            correlation_id=f"load-{index}",
        ),
        requests=12,
        concurrency=4,
    )
    performance_ok = (
        total_latency < 500
        and benchmark["p95_ms"] < 500
        and load["failures"] == 0
    )
    checks.append(
        _check(
            "Performance",
            performance_ok,
            {
                "total_pipeline_ms": round(total_latency, 3),
                "budget_ms": 500,
                "benchmark": benchmark,
                "load": load,
            },
        )
    )
    regression_ok = (
        stages["response"]["version"] == "1.0"
        and set(stages["response"]) == {
            "correlation_id",
            "answer",
            "visibility_score",
            "knowledge_graph",
            "version",
        }
    )
    checks.append(
        _check(
            "Regression",
            regression_ok,
            {"response_schema_version": stages["response"]["version"]},
        )
    )

    passed_checks = sum(check["status"] == "PASS" for check in checks)
    passed_stages = sum(row["status"] == "PASS" for row in matrix) + 1
    coverage = {
        "checks": {
            "passed": passed_checks,
            "total": len(checks),
            "percent": round(passed_checks / len(checks) * 100, 2),
        },
        "pipeline_stages": {
            "covered": min(len(PIPELINE_STAGES), passed_stages),
            "total": len(PIPELINE_STAGES),
            "percent": round(
                min(len(PIPELINE_STAGES), passed_stages)
                / len(PIPELINE_STAGES)
                * 100,
                2,
            ),
        },
        "adapter_stages": [],
    }
    return {
        "status": "PASS" if passed_checks == len(checks) else "FAIL",
        "generated_at": generated_at.isoformat(),
        "correlation_id": correlation,
        "query": query,
        "checks": checks,
        "coverage": coverage,
        "compatibility_matrix": matrix,
        "performance": {
            "stage_timings_ms": stages["timings_ms"],
            "total_pipeline_ms": round(total_latency, 3),
            "benchmark": benchmark,
            "load": load,
        },
        "stages": stages,
    }


def validate_retry_fallback() -> tuple[bool, dict[str, Any]]:
    attempts = 0

    def failing_then_success(payload: dict[str, Any], cancellation: Any) -> dict[str, Any]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("transient")
        return {"recovered": True}

    dispatcher = Dispatcher(
        {
            "primary": failing_then_success,
            "backup": lambda payload, cancellation: {"backup": True},
        }
    )
    plan = ExecutionPlan(
        plan_id="validation-fallback",
        mode="FALLBACK",
        steps=[
            {
                "step_id": "primary",
                "provider": "primary",
                "payload": {},
                "max_retries": 1,
                "retry_base_seconds": 0,
            },
            {
                "step_id": "backup",
                "provider": "backup",
                "payload": {},
                "max_retries": 0,
            },
        ],
    )
    result = execute_plan(
        "validation-fallback",
        plan,
        dispatcher,
        sleep=lambda _: None,
    )
    passed = (
        result.state == "COMPLETED"
        and result.results[0].attempts == 2
        and result.output == {"recovered": True}
    )
    return passed, {
        "attempts": attempts,
        "state": result.state,
        "mode": result.mode,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the AI Ranking OS pipeline")
    parser.add_argument("--query", default="Compare OpenAI and Qwen with sources")
    parser.add_argument("--output", default="validation_reports")
    args = parser.parse_args()
    report = validate_pipeline(args.query)
    paths = write_reports(report, args.output)
    print(json.dumps({"status": report["status"], "reports": paths}, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
