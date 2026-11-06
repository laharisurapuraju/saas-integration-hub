"""Command line entry point:  python -m app.cli sync | report <name> [--out file.csv]"""
import argparse
import sys

from . import reports
from .config import settings
from .database import SessionLocal, init_db
from .etl.client import SourceClient
from .etl.pipeline import run_sync

REPORTS = {
    "revenue-by-category": reports.revenue_by_category,
    "revenue-by-country": reports.revenue_by_country,
    "top-customers": reports.top_customers,
    "data-quality": reports.data_quality,
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="hub")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sync", help="pull data from the source API into the database")
    rep = sub.add_parser("report", help="run a SQL report")
    rep.add_argument("name", choices=REPORTS)
    rep.add_argument("--out", help="write CSV to this file instead of printing")
    args = parser.parse_args(argv)

    init_db()
    with SessionLocal() as session:
        if args.command == "sync":
            run = run_sync(session, SourceClient(settings.source_base_url, settings.page_size))
            print(f"Sync #{run.id}: {run.status} | fetched={run.fetched} "
                  f"loaded={run.loaded} rejected={run.rejected}")
            return 0 if run.status != "failed" else 1
        text = reports.to_csv(REPORTS[args.name](session))
        if args.out:
            with open(args.out, "w", newline="") as fh:
                fh.write(text)
            print(f"Wrote {args.out}")
        else:
            print(text or "(no rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
