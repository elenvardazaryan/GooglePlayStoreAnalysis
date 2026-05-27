"""
extract.py — the E in ETL.

Responsible for reading the raw Google Play Store CSVs from disk and returning
them as pandas DataFrames. No cleaning happens here; that's transform.py's job.
"""
import os
import zipfile
import pandas as pd


def unzip_if_needed(zip_path: str, extract_dir: str) -> None:
    """Extract the Kaggle archive if it hasn't been extracted yet."""
    if os.path.exists(extract_dir) and os.listdir(extract_dir):
        print(f"  [extract] {extract_dir} already populated, skipping unzip")
        return
    if not os.path.exists(zip_path):
        raise FileNotFoundError(
            f"Zip not found at {zip_path}. Download the Kaggle dataset "
            "'Google Play Store Apps' and place the archive there."
        )
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    print(f"  [extract] unzipped to {extract_dir}")


def load_apps(csv_path: str) -> pd.DataFrame:
    """Read the apps CSV into a raw DataFrame."""
    df = pd.read_csv(csv_path)
    print(f"  [extract] loaded apps: {df.shape}")
    return df


def load_reviews(csv_path: str) -> pd.DataFrame:
    """Read the user reviews CSV into a raw DataFrame."""
    df = pd.read_csv(csv_path)
    print(f"  [extract] loaded reviews: {df.shape}")
    return df
