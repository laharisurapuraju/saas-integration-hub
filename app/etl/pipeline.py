"""Extract -> Transform -> Load, with a full audit trail in sync_runs."""
import logging

from sqlalchemy.orm import Session

from ..models import RejectedRecord, SyncRun, utcnow
from .loader import load_all
from .transform import transform_customers, transform_orders, transform_products

logger = logging.getLogger(__name__)


def run_sync(session: Session, client) -> SyncRun:
    run = SyncRun(status="running")
    session.add(run)
    session.commit()
    run_id = run.id
    try:
        raw_customers = client.fetch_all("users", "users")
        raw_products = client.fetch_all("products", "products")
        raw_orders = client.fetch_all("carts", "carts")

        customers, rej_c = transform_customers(raw_customers)
        products, rej_p = transform_products(raw_products)
        orders, rej_o = transform_orders(
            raw_orders, {c["id"] for c in customers}, {p["id"] for p in products}
        )
        rejected = rej_c + rej_p + rej_o

        load_all(session, customers, products, orders)

        for entity, source_id, reason in rejected:
            session.add(
                RejectedRecord(run_id=run_id, entity=entity, source_id=source_id, reason=reason)
            )
        run = session.get(SyncRun, run_id)
        run.fetched = len(raw_customers) + len(raw_products) + len(raw_orders)
        run.loaded = len(customers) + len(products) + len(orders)
        run.rejected = len(rejected)
        run.status = "partial" if rejected else "success"
        logger.info("Sync %s: loaded=%s rejected=%s", run_id, run.loaded, run.rejected)
    except Exception as exc:  # the audit row must record every failure
        session.rollback()
        logger.exception("Sync %s failed", run_id)
        run = session.get(SyncRun, run_id)
        run.status = "failed"
        run.error = str(exc)[:1000]
    finally:
        run.finished_at = utcnow()
        session.commit()
    return run
