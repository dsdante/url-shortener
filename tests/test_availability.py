import socket

from app import services

PUBLIC_IP = "93.184.216.34"


class _FakeResp:
    def __init__(self, status: int):
        self.status_code = status


class _FakeClient:
    def __init__(self, status: int, *args, **kwargs):
        self._status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def head(self, _url):
        return _FakeResp(self._status)


def _mock_dns_to_public(monkeypatch):
    """Make every hostname resolve to a public IP.

    Needed because ``check_availability`` may perform an SSRF pre-check
    (per the security guide) that rejects hosts not resolving to a public
    address. Reserved TLDs like ``.example`` never resolve, so without this
    the function short-circuits before the retry loop. Harmless when the
    service doesn't do DNS.

    Both the module-level ``socket.getaddrinfo`` and a possibly-imported
    ``services.getaddrinfo`` are patched so ``import socket`` and
    ``from socket import getaddrinfo`` are both covered.
    """
    fake_infos = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, 0))]
    fake = lambda *a, **kw: fake_infos  # noqa: E731
    monkeypatch.setattr(socket, "getaddrinfo", fake)
    if hasattr(services, "getaddrinfo"):
        monkeypatch.setattr(services, "getaddrinfo", fake)
    # If the SSRF guard is exposed as a helper, neutralise it directly.
    if hasattr(services, "_is_public_ip"):
        monkeypatch.setattr(services, "_is_public_ip", lambda _host: True)


def _install(monkeypatch, status):
    monkeypatch.setattr(
        "httpx.Client", lambda *a, **kw: _FakeClient(status, *a, **kw)
    )


def test_2xx_is_reachable(monkeypatch):
    _mock_dns_to_public(monkeypatch)
    _install(monkeypatch, 200)
    assert services.check_availability("https://example.com") is True


def test_405_is_treated_as_reachable(monkeypatch):
    _mock_dns_to_public(monkeypatch)
    _install(monkeypatch, 405)
    assert services.check_availability("https://example.com") is True


def test_5xx_is_not_reachable(monkeypatch):
    _mock_dns_to_public(monkeypatch)
    _install(monkeypatch, 503)
    assert services.check_availability("https://example.com") is False


def test_retries_and_gives_up(monkeypatch):
    calls = {"n": 0}

    class FailingClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def head(self, _url):
            calls["n"] += 1
            raise services.httpx.ConnectError("boom")

    _mock_dns_to_public(monkeypatch)
    monkeypatch.setattr("httpx.Client", FailingClient)
    monkeypatch.setattr(services.time, "sleep", lambda _s: None)
    monkeypatch.setattr(services.config, "HTTP_RETRIES", 3)

    assert services.check_availability("https://example.com") is False
    assert calls["n"] == 3