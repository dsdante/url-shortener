def test_create_redirect_stats(client):
    r = client.post("/links", json={"url": "https://example.com"})
    assert r.status_code == 201, r.text
    code = r.json()["code"]
    assert code

    # Initial stats: 0 clicks
    s = client.get(f"/links/{code}/stats")
    assert s.status_code == 200
    assert s.json()["clicks"] == 0
    assert s.json()["url"] == "https://example.com"

    # Three redirects
    for _ in range(3):
        r = client.get(f"/{code}", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"].startswith("https://example.com")

    s = client.get(f"/links/{code}/stats")
    assert s.json()["clicks"] == 3


def test_unknown_code_returns_404(client):
    assert client.get("/does-not-exist").status_code == 404
    assert client.get("/links/does-not-exist/stats").status_code == 404


def test_invalid_url_returns_400(client):
    r = client.post("/links", json={"url": "javascript:alert(1)"})
    assert r.status_code == 400
    assert "scheme" in r.json()["detail"].lower()