"""SQL reports. Each returns a list of dicts so the API and CLI can reuse them."""
import csv
import io

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from .models import Customer, Order, OrderItem, Product, RejectedRecord, SyncRun


def revenue_by_category(session: Session) -> list[dict]:
    stmt = (
        select(
            Product.category,
            func.count(func.distinct(OrderItem.order_id)).label("orders"),
            func.sum(OrderItem.quantity).label("units_sold"),
            func.sum(OrderItem.line_total).label("revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.category)
        .order_by(desc("revenue"))
    )
    return [
        {"category": r.category, "orders": r.orders, "units_sold": int(r.units_sold),
         "revenue": round(float(r.revenue), 2)}
        for r in session.execute(stmt)
    ]


def top_customers(session: Session, limit: int = 10) -> list[dict]:
    stmt = (
        select(
            Customer.id,
            Customer.first_name,
            Customer.last_name,
            Customer.country,
            func.count(Order.id).label("orders"),
            func.sum(Order.discounted_total).label("spend"),
        )
        .join(Order, Order.customer_id == Customer.id)
        .group_by(Customer.id)
        .order_by(desc("spend"))
        .limit(limit)
    )
    return [
        {"customer_id": r.id, "name": f"{r.first_name} {r.last_name}".strip(),
         "country": r.country, "orders": r.orders, "spend": round(float(r.spend), 2)}
        for r in session.execute(stmt)
    ]


def revenue_by_country(session: Session) -> list[dict]:
    stmt = (
        select(Customer.country, func.sum(Order.discounted_total).label("revenue"),
               func.count(Order.id).label("orders"))
        .join(Order, Order.customer_id == Customer.id)
        .group_by(Customer.country)
        .order_by(desc("revenue"))
    )
    return [{"country": r.country, "orders": r.orders, "revenue": round(float(r.revenue), 2)}
            for r in session.execute(stmt)]


def data_quality(session: Session) -> list[dict]:
    """Rejected records from the most recent sync, grouped by entity and reason."""
    last_run = session.execute(select(func.max(SyncRun.id))).scalar()
    if last_run is None:
        return []
    stmt = (
        select(RejectedRecord.entity, RejectedRecord.reason, func.count().label("count"))
        .where(RejectedRecord.run_id == last_run)
        .group_by(RejectedRecord.entity, RejectedRecord.reason)
        .order_by(desc("count"))
    )
    return [{"run_id": last_run, "entity": r.entity, "reason": r.reason, "count": r.count}
            for r in session.execute(stmt)]


def to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
