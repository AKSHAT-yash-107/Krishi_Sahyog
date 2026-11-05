
"""
One-time importer for the Agriculture Marketing CSV.

Run from the backend folder:
python scripts/import_mandi_csv.py "data/apmc-arrivals-and-prices-new-source.csv"

Creates:
data/mandi_data.sqlite3

Uses batch processing so the entire 803 MB CSV
does not need to fit into RAM.
"""

import csv
import sqlite3
import sys
from pathlib import Path

BATCH_SIZE = 20_000

COLUMNS = [
    "id",
    "date",
    "state_name",
    "state_code",
    "district_name",
    "district_code",
    "market_center_name",
    "market_center_code",
    "category",
    "year_of_establishment",
    "latitude",
    "longitude",
    "commodity_name",
    "commodity_id",
    "variety",
    "grade",
    "arrival_quantity",
    "arrival_units",
    "min_price",
    "max_price",
    "modal_price",
    "price_unit",
]


def number(value):
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def integer(value):
    if value is None or value == "":
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def main():

    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python scripts/import_mandi_csv.py "
            "<csv_path> [sqlite_path]"
        )

    csv_path = Path(sys.argv[1]).expanduser().resolve()

    db_path = (
        Path(sys.argv[2]).expanduser().resolve()
        if len(sys.argv) > 2
        else Path("data/mandi_data.sqlite3").resolve()
    )

    if not csv_path.is_file():
        raise SystemExit(f"CSV not found: {csv_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        db_path.unlink()

    con = sqlite3.connect(db_path)

    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA temp_store=MEMORY")

    con.execute("""
        CREATE TABLE mandi_prices (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            state_name TEXT NOT NULL,
            state_code INTEGER,
            district_name TEXT,
            district_code INTEGER,
            market_center_name TEXT NOT NULL,
            market_center_code INTEGER,
            category TEXT,
            year_of_establishment INTEGER,
            latitude REAL,
            longitude REAL,
            commodity_name TEXT NOT NULL,
            commodity_id INTEGER,
            variety TEXT,
            grade TEXT,
            arrival_quantity REAL,
            arrival_units TEXT,
            min_price REAL,
            max_price REAL,
            modal_price REAL,
            price_unit TEXT
        )
    """)

    insert_sql = """
        INSERT INTO mandi_prices VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """

    batch = []
    total = 0

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        missing = [
            column
            for column in COLUMNS
            if column not in (reader.fieldnames or [])
        ]

        if missing:
            raise SystemExit(
                f"CSV missing required columns: {missing}"
            )

        for row in reader:

            batch.append((
                integer(row.get("id")),
                row.get("date") or "",
                row.get("state_name") or "",
                integer(row.get("state_code")),
                row.get("district_name") or "",
                integer(row.get("district_code")),
                row.get("market_center_name") or "",
                integer(row.get("market_center_code")),
                row.get("category") or "",
                integer(row.get("year_of_establishment")),
                number(row.get("latitude")),
                number(row.get("longitude")),
                row.get("commodity_name") or "",
                integer(row.get("commodity_id")),
                row.get("variety") or "",
                row.get("grade") or "",
                number(row.get("arrival_quantity")),
                row.get("arrival_units") or "",
                number(row.get("min_price")),
                number(row.get("max_price")),
                number(row.get("modal_price")),
                row.get("price_unit") or ""
            ))

            if len(batch) >= BATCH_SIZE:

                con.executemany(insert_sql, batch)

                total += len(batch)
                batch.clear()

                print(
                    f"Imported {total:,} rows",
                    flush=True
                )

        if batch:
            con.executemany(insert_sql, batch)
            total += len(batch)

    con.commit()

    print("Creating indexes...", flush=True)

    con.executescript("""
        CREATE INDEX idx_mandi_state_district
        ON mandi_prices(state_name, district_name);

        CREATE INDEX idx_mandi_filters
        ON mandi_prices(state_name, commodity_name, variety);

        CREATE INDEX idx_mandi_market
        ON mandi_prices(state_name, market_center_code);

        CREATE INDEX idx_mandi_price_lookup
        ON mandi_prices(
            state_name,
            district_name,
            commodity_name,
            market_center_name,
            date
        );

        CREATE INDEX idx_mandi_coordinates
        ON mandi_prices(state_name, latitude, longitude);

        CREATE INDEX idx_mandi_date
        ON mandi_prices(date);
    """)

    con.commit()
    con.close()

    print(
        f"Done. Imported {total:,} rows into {db_path}",
        flush=True
    )


if __name__ == "__main__":
    main()
