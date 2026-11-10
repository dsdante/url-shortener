import json
import os
import subprocess
import sys

import pytest


def _run(env_overrides: dict[str, str], code: str, project_root) -> str:
    """Run `python -c code` in a clean subprocess and return stdout."""
    result = subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, **env_overrides},
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"subprocess failed (rc={result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result.stdout.strip()


# --- HTTP behaviour with the default (docs-enabled) app --------------------

def test_docs_enabled_by_default(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    assert client.get("/openapi.json").status_code == 200


# --- ENABLE_DOCS parsing (subprocess — isolates config module state) ------

@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("FALSE", False),
        ("0", False),
        ("", False),
        ("flase", False),   # typo → must fail closed, not expose docs
    ],
)
def test_enable_docs_parsing(value, expected, project_root):
    out = _run(
        {"ENABLE_DOCS": value},
        "from app import config; print(config.ENABLE_DOCS)",
        project_root,
    )
    assert out == str(expected), f"ENABLE_DOCS={value!r} produced {out!r}"


# --- Wiring into the FastAPI app (openapi_url is the single switch) -------

@pytest.mark.parametrize(
    "value,expected_json",
    [
        ("true", '"/openapi.json"'),
        ("false", "null"),
    ],
)
def test_openapi_url_wiring(value, expected_json, project_root):
    """``openapi_url=None`` disables the schema *and* both UIs.

    Checking ``docs_url`` / ``redoc_url`` alone is insufficient — the
    schema would still be served at ``/openapi.json``.
    """
    out = _run(
        {"ENABLE_DOCS": value},
        "import app.main, json; print(json.dumps(app.main.app.openapi_url))",
        project_root,
    )
    assert out == expected_json