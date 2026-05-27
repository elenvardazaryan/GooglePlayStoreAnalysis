"""
transform.py — the T in ETL.

All the cleaning logic from the EDA notebook, packaged as functions.
Each function takes a raw DataFrame and returns a cleaned one. No I/O here.
"""
import numpy as np
import pandas as pd


# ---------- helpers ----------

def _parse_size(value) -> float:
    """Convert size strings like '19M', '512k', 'Varies with device' to MB (float)."""
    s = str(value)
    if "Varies" in s:
        return np.nan
    if s.endswith("k"):
        try:
            return float(s[:-1]) / 1024
        except ValueError:
            return np.nan
    if s.endswith("M"):
        try:
            return float(s[:-1])
        except ValueError:
            return np.nan
    return np.nan


# ---------- apps cleaning ----------

def clean_apps(df: pd.DataFrame) -> pd.DataFrame:
    """Apply every cleaning step from the EDA notebook to the apps DataFrame."""
    df = df.copy()

    # 1. Drop the known shifted row (Category accidentally contains '1.9')
    bad_mask = df["Category"] == "1.9"
    df = df[~bad_mask]

    # 2. Installs: strip '+' and ',' → int
    df["Installs"] = (
        df["Installs"].astype(str).str.replace(r"[+,]", "", regex=True)
    )
    df["Installs"] = pd.to_numeric(df["Installs"], errors="coerce").astype("Int64")

    # 3. Price: strip '$' → float
    df["Price"] = df["Price"].astype(str).str.replace("$", "", regex=False)
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")

    # 4. Reviews: strip non-digits → int
    df["Reviews"] = df["Reviews"].astype(str).str.replace(r"\D", "", regex=True)
    df["Reviews"] = pd.to_numeric(df["Reviews"], errors="coerce").astype("Int64")

    # 5. Size: convert to MB float
    df["Size_MB"] = df["Size"].apply(_parse_size).round(2)

    # 6. Last Updated → datetime
    df["Last Updated"] = pd.to_datetime(df["Last Updated"], errors="coerce")

    # 7. Drop rows missing critical fields
    df = df.dropna(subset=["Type", "Category"])

    # 8. Drop fully-identical duplicates AND duplicate App names (keep one snapshot)
    #    keep the row with the highest review count as the most reliable snapshot
    df = (
        df.sort_values("Reviews", ascending=False)
        .drop_duplicates(subset=["App"], keep="first")
        .reset_index(drop=True)
    )

    # 9. Impute missing Rating with the mean rating in its Installs bucket
    bins = [-1, 0, 10, 1000, 10000, 100000, 1000000, 10000000, 10000000000]
    labels = ["no", "Very low", "Low", "Moderate", "More than moderate",
              "High", "Very High", "Top Notch"]
    df["Installs_category"] = pd.cut(df["Installs"], bins=bins, labels=labels)
    df["Rating"] = df["Rating"].fillna(
        df.groupby("Installs_category", observed=True)["Rating"].transform("mean")
    )
    # Any remaining NaNs → overall mean
    df["Rating"] = df["Rating"].fillna(df["Rating"].mean())

    print(f"  [transform] cleaned apps: {df.shape}")
    return df


# ---------- reviews cleaning ----------

def clean_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the user reviews DataFrame."""
    df = df.copy()

    # Drop rows where every review field is null (placeholder rows from the source)
    df = df.dropna(
        subset=["Translated_Review", "Sentiment",
                "Sentiment_Polarity", "Sentiment_Subjectivity"],
        how="all",
    )
    # Drop rows missing the actual review text
    df = df.dropna(subset=["Translated_Review"]).reset_index(drop=True)

    # Constrain sentiment to the expected values
    df = df[df["Sentiment"].isin(["Positive", "Negative", "Neutral"])]

    print(f"  [transform] cleaned reviews: {df.shape}")
    return df
