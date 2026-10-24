"""Import legacy sources without overwriting current MongoDB records or deleting files."""
import argparse
import json
from pathlib import Path
from legacy_storage import import_legacy, plan_import, read_legacy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent / "data" / "processed")
    parser.add_argument("--dry-run", action="store_true", help="Count local sources without connecting to MongoDB")
    parser.add_argument("--check", action="store_true", help="Compare with MongoDB without writing")
    args = parser.parse_args()
    snapshot = read_legacy(args.source)
    print(json.dumps({"source_counts": {name: len(rows) for name, rows in snapshot.items()}}, ensure_ascii=False))
    if args.dry_run:
        return 0
    from app.services.mongo_client import get_mongo_database
    database = get_mongo_database()
    if args.check:
        plan = plan_import(snapshot, database)
        print(json.dumps({key: value for key, value in plan.items() if key != "operations"}, ensure_ascii=False))
    else:
        print(json.dumps(import_legacy(snapshot, database), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
