"""Idempotent loading: running the same sync twice never creates duplicates."""
from sqlalchemy.orm import Session

from ..models import Customer, Order, OrderItem, Product


def load_all(session: Session, customers: list[dict], products: list[dict], orders: list[dict]) -> None:
    for row in customers:
        session.merge(Customer(**row))
    for row in products:
        session.merge(Product(**row))
    session.flush()

    for row in orders:
        existing = session.get(Order, row["id"])
        if existing is not None:
            session.delete(existing)  # cascade removes old items, so they are rebuilt cleanly
            session.flush()
        items = [OrderItem(**item) for item in row["items"]]
        session.add(
            Order(
                id=row["id"],
                customer_id=row["customer_id"],
                total=row["total"],
                discounted_total=row["discounted_total"],
                items=items,
            )
        )
    session.flush()
