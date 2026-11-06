from app.etl.transform import transform_customers, transform_orders, transform_products


def test_customers_rejects_bad_email_and_duplicates():
    raw = [
        {"id": 1, "firstName": "A", "email": "A@Example.com"},
        {"id": 1, "firstName": "A", "email": "a@example.com"},
        {"id": 2, "firstName": "B", "email": "nope"},
        {"id": None, "firstName": "C", "email": "c@example.com"},
    ]
    valid, rejected = transform_customers(raw)
    assert [c["id"] for c in valid] == [1]
    assert valid[0]["email"] == "a@example.com"  # normalised to lower case
    assert {r[2] for r in rejected} == {"duplicate id", "invalid email", "missing or invalid id"}


def test_products_rejects_negative_price():
    valid, rejected = transform_products(
        [{"id": 1, "title": "X", "category": "c", "price": 5},
         {"id": 2, "title": "Y", "category": "c", "price": -1}]
    )
    assert len(valid) == 1 and rejected == [("product", "2", "invalid price")]


def test_orders_drop_unknown_products_but_keep_valid_lines():
    raw = [{"id": 1, "userId": 1, "total": 30,
            "products": [{"id": 5, "quantity": 2, "price": 10}, {"id": 99, "quantity": 1, "price": 10}]}]
    valid, rejected = transform_orders(raw, {1}, {5})
    assert len(valid) == 1 and len(valid[0]["items"]) == 1
    assert valid[0]["items"][0]["line_total"] == 20
    assert ("order_item", "1/99", "unknown product") in rejected


def test_orders_reject_unknown_customer():
    raw = [{"id": 1, "userId": 42, "products": [{"id": 5, "quantity": 1, "price": 10}]}]
    valid, rejected = transform_orders(raw, {1}, {5})
    assert valid == [] and rejected == [("order", "1", "unknown customer")]
