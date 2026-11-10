import secrets
import string
import time
from urllib.parse import urlparse

import httpx

import ipaddress
import socket
from urllib.parse import urlparse

from . import config

_CODE_ALPHABET = string.ascii_letters + string.digits


def generate_code(length: int = 7) -> str:
    """Return a cryptographically-random base62 code."""
    if length <= 0:
        raise ValueError("length must be positive")
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


def validate_url(raw: str) -> str:
    if not isinstance(raw, str):
        raise ValueError("url must be a string")
    url = raw.strip()
    if not url:
        raise ValueError("url must not be empty")
    if len(url) > 2048:
        raise ValueError("url is too long (max 2048 characters)")

    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("url scheme must be 'http' or 'https'")
    if not parsed.netloc:
        raise ValueError("url must include a host")

    host = parsed.hostname
    if not host:
        raise ValueError("url must include a valid host")
    if host != "localhost" and "." not in host:
        raise ValueError("url host must be a domain name")

    return url


# Networks we never allow the availability check to reach.
# Covers loopback, RFC-1918, link-local/metadata, CGNAT, documentation,
# multicast/reserved, and the IPv6 equivalents including IPv4-mapped space.
_BLOCKED_NETWORKS = tuple(
    ipaddress.ip_network(n) for n in (
        "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
        "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24", "192.0.2.0/24",
        "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24",
        "203.0.113.0/24", "224.0.0.0/4", "240.0.0.0/4",
        "::/128", "::1/128", "::ffff:0:0/96", "64:ff9b::/96",
        "100::/64", "2001::/23", "2001:db8::/32", "fc00::/7",
        "fe80::/10", "ff00::/8",
    )
)


def _parse_ip(raw: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Normalise a getaddrinfo address for comparison against the blocklist."""
    # IPv6 link-local addresses may carry a zone id ("fe80::1%eth0"),
    # which ipaddress.ip_address() rejects.
    if "%" in raw:
        raw = raw.split("%", 1)[0]
    ip = ipaddress.ip_address(raw)
    # ::ffff:127.0.0.1 is a classic blocklist bypass — unwrap it.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def _is_public_ip(host: str) -> bool:
    """True only if *every* address `host` resolves to is public.

    A DNS failure returns False — an unresolvable host is unreachable by
    definition, and must not surface as a 500.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError):
        return False

    for info in infos:
        try:
            ip = _parse_ip(info[4][0])
        except ValueError:
            return False
        for net in _BLOCKED_NETWORKS:
            if net.version == ip.version and ip in net:
                return False
    return True


def check_availability(url: str) -> bool:
    """Perform at most one availability check, bounded by retries.

    The private-IP guard runs *before* any outbound connection, so SSRF
    targets are rejected without a single packet leaving the container.
    Redirects are not followed, closing the redirect-based SSRF escape.
    """
    parsed = urlparse(url)
    host = parsed.hostname
    if not host or not _is_public_ip(host):
        return False

    for attempt in range(config.HTTP_RETRIES):
        try:
            with httpx.Client(
                timeout=config.HTTP_TIMEOUT,
                follow_redirects=False,          # do not chase 3xx to private IPs
                headers={"User-Agent": "url-shortener/1.0"},
            ) as client:
                resp = client.head(url)
            # A 3xx means "reachable, redirects somewhere" — accept it.
            if resp.status_code < 400 or resp.status_code in (405, 501):
                return True
            return False
        except httpx.HTTPError:
            if attempt < config.HTTP_RETRIES - 1:
                time.sleep(0.3 * (attempt + 1))
    return False