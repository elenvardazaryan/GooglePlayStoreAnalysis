"""
load.py — the L in ETL.

Creates the database schema and loads the cleaned DataFrames into it,
respecting foreign-key order: categories → apps → reviews.
"""
import os
import sqlite3
from pathlib import Path

import pandas as pd


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def _to_py(value):
    """Convert pandas NaN/NaT/pd.NA to None so SQLite stores NULL."""
    if pd.isna(value):
        return None
    return value


def init_db(db_path: str) -> sqlite3.Connection:
    """Create a fresh database from schema.sql and return an open connection."""
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    print(f"  [load] schema initialized at {db_path}")
    return conn


def load_categories(conn: sqlite3.Connection, apps_df: pd.DataFrame) -> dict:
    """Insert distinct categories. Returns {category_name: category_id}."""
    unique_cats = sorted(apps_df["Category"].dropna().unique())
    conn.executemany(
        "INSERT INTO categories (category_name) VALUES (?);",
        [(c,) for c in unique_cats],
    )
    conn.commit()
    cat_map = dict(
        conn.execute("SELECT category_name, category_id FROM categories;").fetchall()
    )
    print(f"  [load] {len(cat_map)} categories")
    return cat_map


def load_apps(conn: sqlite3.Connection, apps_df: pd.DataFrame, cat_map: dict) -> dict:
    """Insert apps. Returns {app_name: app_id}."""
    rows = []
    for _, r in apps_df.iterrows():
        rows.append((
            r["App"],
            cat_map[r["Category"]],
            _to_py(r["Rating"]),
            _to_py(r["Reviews"]),
            _to_py(r["Size_MB"]),
            _to_py(r["Installs"]),
            r["Type"],
            _to_py(r["Price"]),
            _to_py(r["Content Rating"]),
            r["Last Updated"].date().isoformat() if pd.notna(r["Last Updated"]) else None,
        ))

    conn.executemany("""
        INSERT INTO apps
        (app_name, category_id, rating, reviews_count, size_mb, installs,
         type, price, content_rating, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, rows)
    conn.commit()

    app_map = dict(
        conn.execute("SELECT app_name, app_id FROM apps;").fetchall()
    )
    print(f"  [load] {len(app_map)} apps")
    return app_map


def load_reviews(conn: sqlite3.Connection, reviews_df: pd.DataFrame, app_map: dict) -> int:
    """Insert reviews for apps that exist in the apps table."""
    # FK integrity: only insert reviews whose app is in our apps table
    filtered = reviews_df[reviews_df["App"].isin(app_map.keys())].copy()

    rows = []
    for _, r in filtered.iterrows():
        rows.append((
            app_map[r["App"]],
            r["Translated_Review"],
            r["Sentiment"],
            _to_py(r["Sentiment_Polarity"]),
            _to_py(r["Sentiment_Subjectivity"]),
        ))

    conn.executemany("""
        INSERT INTO reviews
        (app_id, translated_review, sentiment,
         sentiment_polarity, sentiment_subjectivity)
        VALUES (?, ?, ?, ?, ?);
    """, rows)
    conn.commit()
    print(f"  [load] {len(rows)} reviews")
    return len(rows)
