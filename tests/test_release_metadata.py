"""A release must report the image it actually starts, without rewriting secrets."""

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path("deployment/production/scripts")


def _shell() -> str:
    shell = shutil.which("sh")
    if shell is None:
        pytest.skip("POSIX shell is required to exercise production scripts")
    return shell


def test_release_metadata_updates_only_version_fields(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# production settings\nBUILD_SHA=old\nSECRET=keep-unchanged\nIMAGE_TAG=old\n",
        encoding="utf-8",
    )
    original_mode = env_file.stat().st_mode

    subprocess.run(
        [_shell(), str(SCRIPTS / "record_release.sh"), str(env_file), "a" * 40, "a" * 12],
        check=True,
    )

    assert env_file.read_text(encoding="utf-8") == (
        f"# production settings\nBUILD_SHA={'a' * 40}\n"
        f"SECRET=keep-unchanged\nIMAGE_TAG={'a' * 12}\n"
    )
    assert env_file.stat().st_mode == original_mode
    assert not list(tmp_path.glob(".env.release.*"))


def test_invalid_release_identifier_does_not_change_settings(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("BUILD_SHA=old\nIMAGE_TAG=old\n", encoding="utf-8")

    result = subprocess.run(
        [_shell(), str(SCRIPTS / "record_release.sh"), str(env_file), "bad;cmd", "abc"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert env_file.read_text(encoding="utf-8") == "BUILD_SHA=old\nIMAGE_TAG=old\n"


def test_deploy_and_rollback_record_metadata_after_readiness() -> None:
    for name in ("deploy.sh", "rollback.sh"):
        script = (SCRIPTS / name).read_text(encoding="utf-8")
        assert script.index("curl --fail") < script.index("sh scripts/record_release.sh")
