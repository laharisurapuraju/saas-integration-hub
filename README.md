# SaaS Integration Hub

A small enterprise-style **data integration and reporting service**. It pulls customer, product and
order data from a SaaS REST API, validates and cleans it, loads it into a relational database,
and exposes the result through a secured REST API and SQL reports.

This is the day-to-day pattern of SaaS / technical-consultant work: integrate a source system,
keep the data clean, audit every run, and report on it.

## What it does

- **Extract** - pages through a REST API (default: [DummyJSON](https://dummyjson.com), a public demo API) with automatic retries and exponential back-off.
- **Transform** - validates every record (bad emails, negative prices, duplicates, unknown customers/products) and *rejects* bad rows with a reason instead of crashing.
- **Load** - idempotent upserts, so running a sync twice never creates duplicates.
- **Audit** - every run is stored in `sync_runs` (status, counts, error); every rejected record is stored in `rejected_records`.
- **Serve** - FastAPI REST API protected with an API key, plus CSV export of reports.
- **Report** - SQL aggregations (joins, GROUP BY, ordering): revenue by category and country, top customers, data-quality summary.

## Tech stack

Python 3.11, FastAPI, SQLAlchemy 2.0, PostgreSQL (SQLite for quick local runs), httpx, tenacity,
pytest, Docker / Docker Compose, GitHub Actions.

## Architecture

```
Source REST API --> client (paging + retry) --> transform (validate/clean)
                                                     |            \
                                                     v             v
                                               loader (upsert)   rejected_records
                                                     |
                                                     v
                         PostgreSQL: customers, products, orders, order_items, sync_runs
                                                     |
                                       FastAPI endpoints + SQL reports + CSV export
```

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then set API_KEY
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive API docs.

```bash
curl -X POST http://localhost:8000/sync -H "X-API-Key: change-me"
curl http://localhost:8000/reports/revenue-by-category -H "X-API-Key: change-me"
curl "http://localhost:8000/reports/top-customers?format=csv" -H "X-API-Key: change-me"
```

Command line:

```bash
python -m app.cli sync
python -m app.cli report revenue-by-category --out revenue.csv
```

## Run with PostgreSQL (Docker)

```bash
docker compose up --build
```

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check (no key needed) |
| POST | `/sync` | Run a sync now and return the audit record |
| GET | `/sync/runs` | Recent sync runs |
| GET | `/customers`, `/customers/{id}` | List (filter by `country`, paged) / detail |
| GET | `/orders/{id}` | Order with line items |
| GET | `/reports/revenue-by-category` | Revenue and units per category |
| GET | `/reports/revenue-by-country` | Revenue per customer country |
| GET | `/reports/top-customers` | Highest-spending customers |
| GET | `/reports/data-quality` | Rejected records from the latest sync |

Reports accept `?format=csv`. All endpoints except `/health` require the `X-API-Key` header.

## Tests

```bash
pytest -v
```

12 tests cover validation rules, idempotent loading, failure handling, API authentication, the
reports and CSV export. They use a fake source client, so no network is needed. The same suite runs on
every push through GitHub Actions.

## Possible next steps

- Scheduled syncs (cron or a task queue)
- Incremental sync using `updated_at`
- Alembic migrations
- Swap the source for Salesforce, Oracle Fusion or ServiceNow APIs
