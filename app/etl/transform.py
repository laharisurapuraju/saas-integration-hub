"""Validation and cleaning. Every function returns (valid_rows, rejected_rows).

A rejected row is a tuple: (entity, source_id, reason).
"""
Rejected = tuple[str, str, str]


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def transform_customers(raw: list[dict]) -> tuple[list[dict], list[Rejected]]:
    valid, rejected, seen = [], [], set()
    for row in raw:
        rid = row.get("id")
        if not _is_int(rid):
            rejected.append(("customer", str(rid), "missing or invalid id"))
            continue
        if rid in seen:
            rejected.append(("customer", str(rid), "duplicate id"))
            continue
        email = (row.get("email") or "").strip().lower()
        if "@" not in email:
            rejected.append(("customer", str(rid), "invalid email"))
            continue
        if not (row.get("firstName") or "").strip():
            rejected.append(("customer", str(rid), "missing first name"))
            continue
        seen.add(rid)
        address = row.get("address") or {}
        valid.append(
            {
                "id": rid,
                "first_name": row["firstName"].strip(),
                "last_name": (row.get("lastName") or "").strip(),
                "email": email,
                "country": (address.get("country") or "Unknown").strip(),
                "city": (address.get("city") or "").strip(),
            }
        )
    return valid, rejected


def transform_products(raw: list[dict]) -> tuple[list[dict], list[Rejected]]:
    valid, rejected, seen = [], [], set()
    for row in raw:
        rid = row.get("id")
        if not _is_int(rid):
            rejected.append(("product", str(rid), "missing or invalid id"))
            continue
        if rid in seen:
            rejected.append(("product", str(rid), "duplicate id"))
            continue
        price = row.get("price")
        if not isinstance(price, (int, float)) or price < 0:
            rejected.append(("product", str(rid), "invalid price"))
            continue
        if not (row.get("title") or "").strip() or not (row.get("category") or "").strip():
            rejected.append(("product", str(rid), "missing title or category"))
            continue
        seen.add(rid)
        valid.append(
            {
                "id": rid,
                "title": row["title"].strip(),
                "category": row["category"].strip(),
                "price": float(price),
                "stock": int(row.get("stock") or 0),
            }
        )
    return valid, rejected


def transform_orders(
    raw: list[dict], customer_ids: set[int], product_ids: set[int]
) -> tuple[list[dict], list[Rejected]]:
    valid, rejected, seen = [], [], set()
    for row in raw:
        rid = row.get("id")
        if not _is_int(rid):
            rejected.append(("order", str(rid), "missing or invalid id"))
            continue
        if rid in seen:
            rejected.append(("order", str(rid), "duplicate id"))
            continue
        if row.get("userId") not in customer_ids:
            rejected.append(("order", str(rid), "unknown customer"))
            continue
        items = []
        for line in row.get("products") or []:
            if line.get("id") not in product_ids:
                rejected.append(("order_item", f"{rid}/{line.get('id')}", "unknown product"))
                continue
            qty = line.get("quantity")
            if not _is_int(qty) or qty <= 0:
                rejected.append(("order_item", f"{rid}/{line.get('id')}", "invalid quantity"))
                continue
            unit_price = float(line.get("price") or 0)
            items.append(
                {
                    "product_id": line["id"],
                    "quantity": qty,
                    "unit_price": unit_price,
                    "line_total": round(unit_price * qty, 2),
                }
            )
        if not items:
            rejected.append(("order", str(rid), "no valid items"))
            continue
        seen.add(rid)
        valid.append(
            {
                "id": rid,
                "customer_id": row["userId"],
                "total": float(row.get("total") or 0),
                "discounted_total": float(row.get("discountedTotal") or row.get("total") or 0),
                "items": items,
            }
        )
    return valid, rejected
