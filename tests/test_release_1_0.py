from pathlib import Path

from backend.app.main import app


def test_release_operational_endpoints_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert {"/health", "/live", "/ready", "/metrics", "/system/resources"} <= paths.keys()


def test_release_automation_has_dns_tls_monitoring_and_dr() -> None:
    root = Path("deployment/production/scripts")
    expected = {
        "dns_readiness.sh",
        "enable_https.sh",
        "monitor.sh",
        "backup_redis.sh",
        "dr_validate.sh",
        "release_audit.py",
    }
    assert expected <= {item.name for item in root.iterdir()}
    tls = Path("deployment/production/nginx/host-vhost.conf.example").read_text()
    for header in (
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
    ):
        assert header in tls


def test_release_documentation_is_complete() -> None:
    for name in (
        "RELEASE_1.0.md",
        "RUNBOOK.md",
        "OPERATIONS_CHECKLIST.md",
        "INCIDENT_RESPONSE.md",
    ):
        assert Path("docs", name).is_file()
