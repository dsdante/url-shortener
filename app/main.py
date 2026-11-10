from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import config
from .db import Base, engine, get_db
from .models import Link
from .schemas import LinkCreate, LinkResponse, StatsResponse
from .services import check_availability, generate_code, validate_url

CODE_RETRIES = 10

# openapi_url=None removes the schema *and* both UIs, because /docs and
# /redoc are just HTML that fetch it. Setting docs_url/redoc_url alone is
# not enough — the schema would still be reachable at /openapi.json.
_DOCS_KWARGS = (
    {}
    if config.ENABLE_DOCS
    else {"docs_url": None, "redoc_url": None, "openapi_url": None}
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="URL Shortener",
    version="1.0.0",
    lifespan=lifespan,
    **_DOCS_KWARGS,
)


# Must be registered *before* /{code}: Starlette matches in order, so a
# later definition would be shadowed by the catch-all redirect route and
# would try to look up a link whose code is literally "health".
@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/links", response_model=LinkResponse, status_code=201)
def create_link(payload: LinkCreate, db: Session = Depends(get_db)) -> LinkResponse:
    try:
        url = validate_url(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if config.CHECK_URL_AVAILABILITY and not check_availability(url):
        raise HTTPException(status_code=422, detail="URL is not reachable")

    for _ in range(CODE_RETRIES):
        code = generate_code()
        db.add(Link(code=code, url=url))
        try:
            db.commit()
            return LinkResponse(code=code)
        except IntegrityError:
            db.rollback()
            continue

    raise HTTPException(status_code=500, detail="Could not generate a unique code")


@app.get("/{code}", status_code=302)
def redirect(code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    link = db.query(Link).filter(Link.code == code).first()
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")

    target = link.url
    db.execute(update(Link).where(Link.id == link.id).values(clicks=Link.clicks + 1))
    db.commit()

    return RedirectResponse(url=target, status_code=302)


@app.get("/links/{code}/stats", response_model=StatsResponse)
def stats(code: str, db: Session = Depends(get_db)) -> StatsResponse:
    link = db.query(Link).filter(Link.code == code).first()
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    return StatsResponse(code=link.code, url=link.url, clicks=link.clicks)