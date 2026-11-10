def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_not_shadowed_by_redirect_route(client):
    """Regression guard for route ordering.

    ``GET /{code}`` is registered *after* ``/health`` in ``main.py``. If
    someone moves ``/health`` below the catch-all, Starlette matches
    ``/health`` against ``/{code}`` with ``code="health"`` and the handler
    returns 404 "Link not found" — the container's healthcheck then fails
    even though the app is up. This test pins that ordering.
    """
    r = client.get("/health")
    assert r.status_code == 200, (
        "GET /health was matched by /{code} — move the /health route "
        "above the catch-all redirect route in app/main.py"
    )
    assert r.json() == {"status": "ok"}


def test_health_excluded_from_openapi_schema(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200, (
        "docs must be enabled for this test — conftest sets ENABLE_DOCS=true"
    )
    schema = r.json()
    assert "/health" not in schema.get("paths", {}), (
        "/health should be hidden via include_in_schema=False"
    )