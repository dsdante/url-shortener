import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./links.db")

CHECK_URL_AVAILABILITY = os.getenv("CHECK_URL_AVAILABILITY", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "5.0"))
HTTP_RETRIES = max(1, int(os.getenv("HTTP_RETRIES", "2")))

# Expose /docs, /redoc and /openapi.json. Set ENABLE_DOCS=false in production.
# Anything not in the truthy set is treated as false, so a typo fails closed.
ENABLE_DOCS = os.getenv("ENABLE_DOCS", "true").strip().lower() in (
    "1", "true", "yes", "on",
)