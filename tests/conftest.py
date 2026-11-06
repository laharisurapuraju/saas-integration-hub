import os

os.environ["DATABASE_URL"] = "sqlite://"  # in-memory, set before the app is imported

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app, get_source_client

API_KEY = "test-key"


class FakeClient:
    """Stands in for the real source API so tests never touch the network."""

    def __init__(self, users=None, products=None, carts=None, fail=False):
        self.data = {"users": users or [], "products": products or [], "carts": carts or []}
        self.fail = fail

    def fetch_all(self, resource, key):
        if self.fail:
            raise ConnectionError("source system unavailable")
        return self.data[resource]


def sample_data():
    users = [
        {"id": 1, "firstName": "Asha", "lastName": "Rao", "email": "asha@example.com",
         "address": {"city": "Pune", "country": "India"}},
        {"id": 2, "firstName": "Ben", "lastName": "Lee", "email": "ben@example.com",
         "address": {"city": "Austin", "country": "United States"}},
        {"id": 3, "firstName": "Bad", "lastName": "Email", "email": "not-an-email"},
    ]
    products = [
        {"id": 10, "title": "Laptop", "category": "laptops", "price": 1000, "stock": 5},
        {"id": 11, "title": "Mouse", "category": "accessories", "price": 20, "stock": 50},
        {"id": 12, "title": "Broken", "category": "accessories", "price": -5, "stock": 1},
    ]
    carts = [
        {"id": 100, "userId": 1, "total": 1040, "discountedTotal": 1000,
         "products": [{"id": 10, "quantity": 1, "price": 1000}, {"id": 11, "quantity": 2, "price": 20}]},
        {"id": 101, "userId": 2, "total": 20, "discountedTotal": 20,
         "products": [{"id": 11, "quantity": 1, "price": 20}, {"id": 999, "quantity": 1, "price": 5}]},
        {"id": 102, "userId": 77, "total": 5, "products": [{"id": 11, "quantity": 1, "price": 5}]},
    ]
    return users, products, carts


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture()
def client(db):
    users, products, carts = sample_data()
    settings.api_key = API_KEY
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_source_client] = lambda: FakeClient(users, products, carts)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def auth():
    return {"X-API-Key": API_KEY}
