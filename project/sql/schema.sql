-- schema.sql
-- Google Play Store relational schema
--
-- Normalized to 3NF:
--   - categories is split into its own table to avoid repeating category
--     strings across thousands of app rows.
--   - apps references categories via category_id.
--   - reviews references apps via app_id.
--
-- CHECK constraints catch bad data at insert time.
-- Indexes are placed on foreign keys and common filter columns
-- (type, sentiment, last_updated) to keep JOINs and WHERE clauses fast.

DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS apps;
DROP TABLE IF EXISTS categories;

CREATE TABLE categories (
    category_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name  TEXT    NOT NULL UNIQUE
);

CREATE TABLE apps (
    app_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name        TEXT    NOT NULL UNIQUE,
    category_id     INTEGER NOT NULL,
    rating          REAL,
    reviews_count   INTEGER DEFAULT 0,
    size_mb         REAL,
    installs        INTEGER DEFAULT 0,
    type            TEXT    NOT NULL CHECK (type IN ('Free', 'Paid')),
    price           REAL    DEFAULT 0.0,
    content_rating  TEXT,
    last_updated    DATE,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE reviews (
    review_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id                 INTEGER NOT NULL,
    translated_review      TEXT,
    sentiment              TEXT    CHECK (sentiment IN ('Positive', 'Negative', 'Neutral')),
    sentiment_polarity     REAL,
    sentiment_subjectivity REAL,
    FOREIGN KEY (app_id) REFERENCES apps(app_id)
);

CREATE INDEX idx_apps_category     ON apps(category_id);
CREATE INDEX idx_apps_type         ON apps(type);
CREATE INDEX idx_apps_last_update  ON apps(last_updated);
CREATE INDEX idx_reviews_app       ON reviews(app_id);
CREATE INDEX idx_reviews_sentiment ON reviews(sentiment);
