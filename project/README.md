# Google Play Store — Data Ingestion & Analytics Pipeline

A small ETL + SQL analytics project built around the public **Google Play Store Apps** dataset
from Kaggle. Raw CSVs are cleaned in Python and loaded into a normalized SQLite database,
then analysed with SQL covering aggregations, joins, and window functions.

---

## 1. Project overview

The pipeline answers questions like:

- Which app categories dominate the store by install count?
- Do paid apps get better reviews than free ones?
- For each category, which apps are the top performers?
- How does an app's rating compare to the average for its category?

Raw scraped CSVs are messy — prices have `$` signs, install counts have `+` and `,`,
sizes mix megabytes and kilobytes, one row is column-shifted, and some apps appear
multiple times with slightly different snapshot values. The pipeline cleans all of
this and produces a queryable database in a few seconds.

---

## 2. Dataset

- **Source:** [Google Play Store Apps on Kaggle](https://www.kaggle.com/datasets/lava18/google-play-store-apps)
- **Files:**
  - `googleplaystore.csv` — ~10,800 apps with metadata (Category, Rating, Reviews, Size,
    Installs, Type, Price, Content Rating, Genres, Last Updated, versions)
  - `googleplaystore_user_reviews.csv` — ~64,000 pre-processed reviews with sentiment
    labels (Positive / Negative / Neutral) and polarity/subjectivity scores

To run the pipeline, place the downloaded `archive.zip` from Kaggle into `data/`.

---

## 3. Pipeline description

Three modules under `app/`, plus an orchestrator:

| File | Role |
|---|---|
| `extract.py` | Unzips the Kaggle archive and reads the two CSVs into raw pandas DataFrames |
| `transform.py` | Cleans both DataFrames (see below) |
| `load.py` | Reads `sql/schema.sql`, builds the database, and inserts the cleaned data |
| `main.py` | Wires the three steps together |

### Cleaning steps (transform.py)

**Apps:**
- Drop the one column-shifted row where `Category == "1.9"` (originally row 10472).
- `Installs` — strip `+` and `,`, cast to nullable `Int64`.
- `Price` — strip `$`, cast to `float`.
- `Reviews` — strip non-digits, cast to nullable `Int64`.
- `Size` — convert `"19M"` → `19.0`, `"512k"` → `0.5` (KB→MB), `"Varies with device"` → `NaN`.
- `Last Updated` — parse strings like `"February 11, 2018"` into real `datetime` values.
- Drop rows missing `Type` or `Category` (very few).
- **Deduplicate on App name** (keeping the snapshot with the most reviews) — many apps
  appear multiple times with slightly different scrape values, and SQL's `UNIQUE`
  constraint requires a single row per app.
- Impute missing `Rating` using the mean rating within the app's install-volume bucket
  (apps with similar download counts tend to have similar rating distributions).
  Any remaining NaNs fall back to the overall mean.

**Reviews:**
- Drop rows where all four review fields are NaN (placeholder rows).
- Drop rows where the actual review text is missing.
- Restrict `Sentiment` to the three allowed values (`Positive`, `Negative`, `Neutral`).

---

## 4. Database schema

Three normalized tables. Diagram:

```
categories (category_id PK, category_name UNIQUE NOT NULL)
     ↑
     │ FK
     │
apps (app_id PK, app_name UNIQUE NOT NULL, category_id FK,
      rating, reviews_count, size_mb, installs,
      type CHECK('Free','Paid'), price, content_rating, last_updated)
     ↑
     │ FK
     │
reviews (review_id PK, app_id FK, translated_review,
         sentiment CHECK('Positive','Negative','Neutral'),
         sentiment_polarity, sentiment_subjectivity)
```

Design decisions:

- **`categories` in its own table** so the category name is not repeated thousands of
  times across the `apps` table (3NF).
- **`apps.app_name UNIQUE`** so reviews can be joined to apps cleanly via foreign key.
- **`CHECK` constraints** on `type` and `sentiment` reject bad values at insert time.
- **Indexes** on the FK columns and on the most common filter columns (`type`,
  `sentiment`, `last_updated`) keep JOINs and `WHERE` clauses fast.

Full DDL in [`sql/schema.sql`](sql/schema.sql).

---

## 5. How to run

### Requirements
- Python ≥ 3.10
- `pip install -r requirements.txt` (just pandas + numpy)

### Steps

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd project

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download the Kaggle dataset and put archive.zip into data/
#    (Kaggle login required: https://www.kaggle.com/datasets/lava18/google-play-store-apps)

# 4. Run the pipeline
python app/main.py
```

After this, you'll have `data/playstore.db` — a populated SQLite database.

### Running the analysis queries

Any SQLite client works. From the command line:

```bash
sqlite3 data/playstore.db < sql/queries.sql
```

Or open `data/playstore.db` in DB Browser for SQLite, DBeaver, or VS Code's SQLite extension
and run the queries from `sql/queries.sql` one at a time.

---

## 6. SQL analysis — what each query covers

All ten queries live in [`sql/queries.sql`](sql/queries.sql).

| # | Query | Type covered |
|---|---|---|
| Q1 | Catalogue-wide summary stats | Summary statistics |
| Q2 | Per-category app counts, avg rating, total installs | `GROUP BY`, `HAVING`, `ORDER BY`, filtering |
| Q3 | Top 10 most-installed apps with category | Top-N + JOIN |
| Q4 | Bottom 10 rated apps (≥ 1000 reviews to remove noise) | Bottom-N + filter + JOIN |
| Q5 | Apps updated per year | **Trend analysis** |
| Q6 | Sentiment breakdown per category | **3-table JOIN** + aggregation |
| Q7 | Top 3 most-installed apps per category | **Window function** (`RANK` + `PARTITION BY`) |
| Q8 | Each app's rating vs. its category average | **Window function** (`AVG OVER PARTITION`) |
| Q9 | Cumulative installs across top categories | **Window function** (running total) |
| Q10 | Do paid apps receive more positive reviews than free ones? | Analytical question + 2-table JOIN |

---

## 7. Summary of analytical results

Headline findings from running the queries against the cleaned dataset (numbers will
vary slightly depending on how missing-value imputation lands):

- **Free apps dominate the store.** Roughly 93% of apps are free; only ~7% are paid.
- **Game and Communication categories dwarf others in installs.** Together they account
  for a large share of the cumulative install total (see Q9).
- **Paid apps don't get noticeably better reviews.** Q10 shows that the positive-review
  percentage and average polarity for free vs. paid apps are very close, despite paid
  apps having slightly higher average star ratings — paying for an app does not strongly
  correlate with happier reviewers.
- **Top-rated apps per category cluster around 4.5–4.8** (Q7, Q8) — once you filter to
  apps with enough reviews to be statistically reasonable, ratings tighten significantly.
- **Apps updated more recently tend to have higher average ratings** (Q5) — older,
  less-maintained apps drag down the rating distribution.

The presentation script walks through these findings in more detail.

---

## 8. Repository structure

```
project/
├── data/
│   ├── README.txt              (instructions for placing the Kaggle archive)
│   ├── archive.zip             (downloaded — not committed)
│   ├── extracted/              (auto-generated)
│   └── playstore.db            (auto-generated)
├── app/
│   ├── extract.py              Extract step
│   ├── transform.py            Transform step
│   ├── load.py                 Load step
│   └── main.py                 Orchestrator
├── sql/
│   ├── schema.sql              DDL: tables, constraints, indexes
│   └── queries.sql             Ten analytical queries
├── README.md                   This file
└── requirements.txt            Python dependencies
```

---

## 9. Notes & limitations

- The dataset is a **single snapshot** scraped in 2018; trend analysis is bounded by
  that timeframe.
- A handful of apps in the source CSV appear multiple times with conflicting metadata.
  The pipeline keeps the snapshot with the highest review count, on the assumption that
  it's the freshest/most complete; this is documented inline in `transform.py`.
- Sentiment labels in the reviews CSV are pre-computed by the dataset author, not by
  this pipeline — we treat them as ground truth.
