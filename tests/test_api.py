def test_health_needs_no_key(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_protected_routes_reject_missing_or_wrong_key(client):
    assert client.get("/customers").status_code == 401
    assert client.get("/customers", headers={"X-API-Key": "wrong"}).status_code == 401


def test_sync_then_query_and_reports(client, auth):
    run = client.post("/sync", headers=auth)
    assert run.status_code == 201 and run.json()["status"] == "partial"

    customers = client.get("/customers", headers=auth).json()
    assert [c["name"] for c in customers] == ["Asha Rao", "Ben Lee"]
    assert client.get("/customers?country=India", headers=auth).json()[0]["id"] == 1
    assert client.get("/customers/999", headers=auth).status_code == 404

    order = client.get("/orders/100", headers=auth).json()
    assert len(order["items"]) == 2 and order["items"][0]["title"] in {"Laptop", "Mouse"}

    by_cat = client.get("/reports/revenue-by-category", headers=auth).json()
    assert by_cat[0] == {"category": "laptops", "orders": 1, "units_sold": 1, "revenue": 1000.0}

    top = client.get("/reports/top-customers?limit=1", headers=auth).json()
    assert top[0]["name"] == "Asha Rao" and top[0]["spend"] == 1000.0

    quality = client.get("/reports/data-quality", headers=auth).json()
    assert any(row["reason"] == "invalid email" for row in quality)

    assert len(client.get("/sync/runs", headers=auth).json()) == 1


def test_csv_export(client, auth):
    client.post("/sync", headers=auth)
    response = client.get("/reports/revenue-by-category?format=csv", headers=auth)
    assert response.headers["content-type"].startswith("text/csv")
    assert response.text.splitlines()[0] == "category,orders,units_sold,revenue"
