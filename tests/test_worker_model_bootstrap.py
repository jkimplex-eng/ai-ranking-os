"""The API imports more models than the worker: test a clean interpreter."""

import subprocess
import sys


def test_worker_registers_relationship_models_without_api_imports():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import backend.app.worker; "
            "from sqlalchemy.orm import configure_mappers; configure_mappers()",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
