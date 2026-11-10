import pytest

from app.services import validate_url


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://example.com/path?query=1#frag",
        "https://sub.example.com:8080/a/b",
        "  https://example.com  ",
        "http://localhost:8000/dev",
    ],
)
def test_valid_urls(url):
    assert validate_url(url) == url.strip()


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "example.com",          # no scheme
        "ftp://example.com",    # wrong scheme
        "file:///etc/passwd",
        "javascript:alert(1)",
        "https://",             # no host
        "http://",
        "https://" + "a" * 2100,
        "http://nodots",
    ],
)
def test_invalid_urls(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_non_string_rejected():
    with pytest.raises(ValueError):
        validate_url(None)  # type: ignore[arg-type]