"""
main.py — orchestrate the full ETL pipeline.

Usage:
    python app/main.py

Reads the Kaggle archive from data/, cleans it, and loads it into
data/playstore.db. After running, you can open the database in any
SQLite client and run the queries from sql/queries.sql.
"""
import os
from pathlib import Path

from extract import unzip_if_needed, load_apps, load_reviews
from transform import clean_apps, clean_reviews
import load as L


# ---- paths ----
PROJECT_ROOT  = Path(__file__).resolve().parent.parent
DATA_DIR      = PROJECT_ROOT / "data"
ZIP_PATH      = DATA_DIR / "archive.zip"
EXTRACT_DIR   = DATA_DIR / "extracted"
APPS_CSV      = EXTRACT_DIR / "googleplaystore.csv"
REVIEWS_CSV   = EXTRACT_DIR / "googleplaystore_user_reviews.csv"
DB_PATH       = DATA_DIR / "playstore.db"


def run() -> None:
    print("=== ETL pipeline starting ===")

    # Extract
    print("\n[1/3] Extract")
    unzip_if_needed(str(ZIP_PATH), str(EXTRACT_DIR))
    apps_raw    = load_apps(str(APPS_CSV))
    reviews_raw = load_reviews(str(REVIEWS_CSV))

    # Transform
    print("\n[2/3] Transform")
    apps_clean    = clean_apps(apps_raw)
    reviews_clean = clean_reviews(reviews_raw)

    # Load
    print("\n[3/3] Load")
    conn    = L.init_db(str(DB_PATH))
    cat_map = L.load_categories(conn, apps_clean)
    app_map = L.load_apps(conn, apps_clean, cat_map)
    L.load_reviews(conn, reviews_clean, app_map)

    # Sanity check
    print("\n=== Row counts ===")
    for table in ["categories", "apps", "reviews"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:12} {n:>7,}")

    conn.close()
    print(f"\nDatabase ready at {DB_PATH}")
    print("Run the analyses in sql/queries.sql to see the insights.")


if __name__ == "__main__":
    run()
