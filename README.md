# URL Shortener

A small, production-shaped URL shortener built with **FastAPI + SQLAlchemy**.
It exposes three endpoints:

| Method | Endpoint              | Description                                     |
| ------ | --------------------- | ----------------------------------------------- |
| POST   | `/links`              | Body `{"url": "..."}` → `{"code": "abc123"}`    |
| GET    | `/{code}`             | `302` redirect to the original URL              |
| GET    | `/links/{code}/stats` | `{"code", "url", "clicks"}`                     |

Interactive docs are at /docs and /redoc when ENABLE_DOCS=true (the default for local development). Production sets ENABLE_DOCS=false, which disables all three documentation routes.

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload