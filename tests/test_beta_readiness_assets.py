from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_closed_beta_operational_package_is_complete() -> None:
    required = [
        "docs/BETA_GUIDE.md",
        "docs/BETA_PRODUCTION_CHECKLIST.md",
        "docs/TROUBLESHOOTING.md",
        "docs/BACKUP.md",
        "docs/Monitoring.md",
        "docs/Deployment.md",
        "scripts/seed_closed_beta.py",
    ]

    assert all((ROOT / path).is_file() for path in required)


def test_beta_seed_requires_external_password_and_is_idempotent_by_design() -> None:
    source = (ROOT / "scripts/seed_closed_beta.py").read_text(encoding="utf-8")

    assert "BETA_DEMO_PASSWORD" in source
    assert "demo-organization" in source
    assert "skip-research" in source
    assert "get_user_by_email" in source
    assert "Organization.slug" in source
