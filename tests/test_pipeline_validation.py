import json
from pathlib import Path

from validation.benchmark_runner import run_benchmark
from validation.compatibility import compatibility_passed
from validation.load_tests import run_load_test
from validation.pipeline_validator import (
    PIPELINE_STAGES,
    execute_pipeline,
    validate_pipeline,
)
from validation.report_generator import render_html, write_reports


def test_e2e_pipeline_integrity_and_correlation() -> None:
    correlation_id = "correlation-test"
    stages = execute_pipeline(
        "Compare OpenAI and Qwen with sources",
        correlation_id=correlation_id,
    )

    assert set(PIPELINE_STAGES) <= set(stages)
    assert stages["intent"]["request_id"] == correlation_id
    assert stages["router"]["request_id"] == correlation_id
    assert stages["reason"]["correlation_id"] == correlation_id
    assert stages["knowledge_graph"]["correlation_id"] == correlation_id
    assert stages["response"]["correlation_id"] == correlation_id
    assert stages["executor"]["state"] == "COMPLETED"
    assert 0 <= stages["visibility"]["visibility_score"] <= 100


def test_full_validation_regression_report_is_pass() -> None:
    report = validate_pipeline("Compare OpenAI and Qwen with sources")

    assert report["status"] == "PASS"
    assert all(check["status"] == "PASS" for check in report["checks"])
    assert compatibility_passed(report["compatibility_matrix"])
    assert report["coverage"]["checks"]["percent"] == 100
    assert report["coverage"]["pipeline_stages"]["percent"] == 100
    assert report["performance"]["benchmark"]["p95_ms"] < 500
    assert report["performance"]["load"]["success_rate"] == 1.0
    assert report["coverage"]["adapter_stages"] == []


def test_report_generation_outputs_all_artifacts(tmp_path: Path) -> None:
    report = validate_pipeline("What is OpenAI?")
    paths = write_reports(report, tmp_path)

    assert set(paths) == {
        "json_report",
        "html_report",
        "coverage_report",
        "compatibility_matrix",
    }
    assert all(Path(path).exists() for path in paths.values())
    loaded = json.loads(Path(paths["json_report"]).read_text(encoding="utf-8"))
    assert loaded["status"] == "PASS"
    html = Path(paths["html_report"]).read_text(encoding="utf-8")
    assert "AI Ranking OS Pipeline Validation" in html
    assert "<strong class=\"pass\">PASS</strong>" in html


def test_html_renderer_escapes_untrusted_query() -> None:
    report = validate_pipeline("<script>alert(1)</script>")
    rendered = render_html(report)

    assert "<script>alert(1)</script>" not in rendered


def test_benchmark_and_load_helpers() -> None:
    benchmark = run_benchmark(lambda: execute_pipeline("What is AI?"), iterations=5)
    load = run_load_test(
        lambda index: execute_pipeline("What is AI?", correlation_id=f"test-{index}"),
        requests=8,
        concurrency=4,
    )

    assert benchmark["iterations"] == 5
    assert benchmark["p95_ms"] < 500
    assert load["failures"] == 0
    assert load["success_rate"] == 1.0
