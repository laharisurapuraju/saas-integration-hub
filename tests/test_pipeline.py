from sqlalchemy import func, select

from app.etl.pipeline import run_sync
from app.models import Customer, Order, OrderItem, RejectedRecord
from tests.conftest import FakeClient, sample_data


def test_sync_loads_valid_rows_and_records_rejections(db):
    users, products, carts = sample_data()
    run = run_sync(db, FakeClient(users, products, carts))

    assert run.status == "partial"
    assert db.scalar(select(func.count()).select_from(Customer)) == 2
    assert db.scalar(select(func.count()).select_from(Order)) == 2
    assert db.scalar(select(func.count()).select_from(OrderItem)) == 3
    reasons = {r.reason for r in db.scalars(select(RejectedRecord))}
    assert {"invalid email", "invalid price", "unknown product", "unknown customer"} <= reasons


def test_sync_is_idempotent(db):
    users, products, carts = sample_data()
    run_sync(db, FakeClient(users, products, carts))
    run_sync(db, FakeClient(users, products, carts))
    assert db.scalar(select(func.count()).select_from(Customer)) == 2
    assert db.scalar(select(func.count()).select_from(Order)) == 2
    assert db.scalar(select(func.count()).select_from(OrderItem)) == 3  # no duplicated lines


def test_clean_data_gives_success_status(db):
    users, products, carts = sample_data()
    run = run_sync(db, FakeClient(users[:2], products[:2], carts[:1]))
    assert run.status == "success" and run.rejected == 0


def test_source_failure_is_recorded_not_raised(db):
    run = run_sync(db, FakeClient(fail=True))
    assert run.status == "failed"
    assert "unavailable" in run.error
    assert run.finished_at is not None
