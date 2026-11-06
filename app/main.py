"""REST API. Everything except /health requires an X-API-Key header."""
import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import reports
from .config import settings
from .database import get_db, init_db
from .etl.client import SourceClient
from .etl.pipeline import run_sync
from .models import Customer, Order, SyncRun

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="SaaS Integration Hub", version="1.0.0", lifespan=lifespan)


def require_api_key(x_api_key: str = Header(default="")) -> None:
    if not secrets.compare_digest(x_api_key.encode(), settings.api_key.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def get_source_client() -> SourceClient:
    return SourceClient(settings.source_base_url, page_size=settings.page_size)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


api = APIRouter(dependencies=[Depends(require_api_key)])


def _run_to_dict(run: SyncRun) -> dict:
    return {
        "id": run.id, "status": run.status, "fetched": run.fetched, "loaded": run.loaded,
        "rejected": run.rejected, "error": run.error,
        "started_at": run.started_at, "finished_at": run.finished_at,
    }


@api.post("/sync", status_code=201)
def trigger_sync(db: Session = Depends(get_db), client=Depends(get_source_client)) -> dict:
    return _run_to_dict(run_sync(db, client))


@api.get("/sync/runs")
def list_sync_runs(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)) -> list[dict]:
    runs = db.scalars(select(SyncRun).order_by(SyncRun.id.desc()).limit(limit)).all()
    return [_run_to_dict(r) for r in runs]


@api.get("/customers")
def list_customers(
    country: str | None = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(Customer).order_by(Customer.id).limit(limit).offset(offset)
    if country:
        stmt = stmt.where(Customer.country == country)
    return [
        {"id": c.id, "name": f"{c.first_name} {c.last_name}".strip(), "email": c.email,
         "country": c.country, "city": c.city}
        for c in db.scalars(stmt)
    ]


@api.get("/customers/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)) -> dict:
    c = db.get(Customer, customer_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"id": c.id, "name": f"{c.first_name} {c.last_name}".strip(), "email": c.email,
            "country": c.country, "city": c.city, "order_ids": [o.id for o in c.orders]}


@api.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)) -> dict:
    o = db.get(Order, order_id)
    if o is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": o.id, "customer_id": o.customer_id, "total": o.total,
        "discounted_total": o.discounted_total,
        "items": [{"product_id": i.product_id, "title": i.product.title, "quantity": i.quantity,
                   "unit_price": i.unit_price, "line_total": i.line_total} for i in o.items],
    }


def _respond(rows: list[dict], fmt: str, name: str):
    if fmt == "csv":
        return Response(reports.to_csv(rows), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{name}.csv"'})
    return rows


@api.get("/reports/revenue-by-category")
def report_category(format: str = Query("json", pattern="^(json|csv)$"), db: Session = Depends(get_db)):
    return _respond(reports.revenue_by_category(db), format, "revenue_by_category")


@api.get("/reports/revenue-by-country")
def report_country(format: str = Query("json", pattern="^(json|csv)$"), db: Session = Depends(get_db)):
    return _respond(reports.revenue_by_country(db), format, "revenue_by_country")


@api.get("/reports/top-customers")
def report_customers(
    limit: int = Query(10, ge=1, le=100),
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    return _respond(reports.top_customers(db, limit), format, "top_customers")


@api.get("/reports/data-quality")
def report_quality(format: str = Query("json", pattern="^(json|csv)$"), db: Session = Depends(get_db)):
    return _respond(reports.data_quality(db), format, "data_quality")


app.include_router(api)
