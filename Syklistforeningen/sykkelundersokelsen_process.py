"""Main pipeline for processing Syklistforeningen survey data.

Reads the raw SPSS .sav file, enriches each row with municipality/county
labels, population figures, and a size category, then writes the result
back to a new .sav file together with two CSV exports:

* antall_svar_kommuner.csv  – one row per municipality with response count
                              and target (use --dummy for the _dummy variant)
* svar_data.csv             – one row per respondent with key columns
                              (use --dummy for the _dummy variant)

Usage
-----
    python sykkelundersokelsen_process.py
    python sykkelundersokelsen_process.py --dummy 500
"""
import argparse
from datetime import datetime
import os
from pathlib import Path

import dropbox
from dropbox.files import WriteMode
import numpy as np
import pandas as pd
import pyreadstat

from utils import load_lookups, add_kommune_fylke, add_befolkning, add_kategori, write_sav


def upload_to_dropbox(local_path: Path):
    """Upload a file to the Dropbox app folder, overwriting any existing file.

    Requires environment variables:
        DROPBOX_APP_KEY_SYKKEL, DROPBOX_APP_SECRET_SYKKEL, DROPBOX_REFRESH_TOKEN_SYKKEL
    """
    app_key       = os.getenv("DROPBOX_APP_KEY_SYKKEL")
    app_secret    = os.getenv("DROPBOX_APP_SECRET_SYKKEL")
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN_SYKKEL")

    missing = [k for k, v in {
        "DROPBOX_APP_KEY_SYKKEL": app_key,
        "DROPBOX_APP_SECRET_SYKKEL": app_secret,
        "DROPBOX_REFRESH_TOKEN_SYKKEL": refresh_token,
    }.items() if not v]
    if missing:
        raise EnvironmentError(f"Mangler miljøvariabler: {', '.join(missing)}")

    dbx = dropbox.Dropbox(
        oauth2_refresh_token=refresh_token,
        app_key=app_key,
        app_secret=app_secret,
    )
    with open(local_path, "rb") as f:
        dbx.files_upload(f.read(), f"/{local_path.name}", mode=WriteMode.overwrite)
    print(f"Uploaded {local_path.name} to Dropbox")

SAV_PATH = r"C:\Users\NinaIrenHoven\Opinion AS\Opinion SharePoint - Syklistforeningen\Data 2026\260315.sav"

# Required number of answers per municipality size category (Kommune_kategori 1–5)
TARGETS = {
    1: 50,   # Under 20 000
    2: 50,   # 20 000–49 999
    3: 75,   # 50 000–99 999
    4: 100,  # 100 000–199 999
    5: 200,  # Over 200 000
}


def generate_dummy_dates(n):
    """Return a list of n date strings spread over the last 7 days (inclusive of today)."""
    rng = np.random.default_rng(42)
    today = pd.Timestamp.today().normalize()
    offsets = rng.integers(0, 8, size=n)  # 0–7 days ago
    return [(today - pd.Timedelta(days=int(d))).strftime("%Y-%m-%d") for d in offsets]


def generate_dummy(n, kommuner, befolkning_map):
    """Generate n dummy survey rows sampled from the 20 largest + 20 random municipalities.

    Sampling is population-weighted within the combined pool.
    Returns a DataFrame with a single column ``hFiler1`` (kommunenummer as str).
    """
    rng = np.random.default_rng(42)

    kommunenr = kommuner["Kommunenummer"].astype(int).values
    populations = np.array([befolkning_map.get(k, 0) for k in kommunenr], dtype=float)

    sorted_idx = np.argsort(populations)[::-1]
    top20_idx = sorted_idx[:20]
    rest_idx = sorted_idx[20:]
    random20_idx = rng.choice(rest_idx, size=20, replace=False)

    pool_idx = np.concatenate([top20_idx, random20_idx])
    pool = kommunenr[pool_idx]
    pool_populations = populations[pool_idx]
    weights = pool_populations / pool_populations.sum()

    sampled = rng.choice(pool, size=n, replace=True, p=weights)
    return pd.DataFrame({"hFiler1": sampled.astype(str)})


def save_detail_csv(df, path, vlabels):
    """Save a pre-aggregated CSV with one row per (municipality, date).

    Columns: Kommunenummer, Kommune, Dato, Antall.
    """
    out = pd.DataFrame()
    out["Kommunenummer"] = df["Kommune"].astype("Int64")
    out["Kommune"]       = df["Kommune"].map(vlabels["Kommune"])
    out["Dato"]          = df["StartTime"].str[:10]
    detail = out.groupby(["Kommunenummer", "Kommune", "Dato"], as_index=False).size().rename(columns={"size": "Antall"})
    detail = detail.sort_values(["Kommunenummer", "Dato"])
    detail.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Saved detail CSV to {path}")


def save_data_csv(df, path, vlabels):
    """Save a row-per-respondent CSV with key columns.

    Columns: uuid, Dato, Kommunenummer, Kommune, Fylkesnummer, Fylke,
             Befolkning, Kommunestørrelse.
    """
    out = pd.DataFrame()
    out["uuid"]              = df["uuid"]
    out["Dato"]              = df["StartTime"].str[:10]
    out["Kommunenummer"]     = df["Kommune"].astype("Int64")
    out["Kommune"]           = df["Kommune"].map(vlabels["Kommune"])
    out["Fylkesnummer"]      = df["Fylke"].astype("Int64")
    out["Fylke"]             = df["Fylke"].map(vlabels["Fylke"])
    out["Befolkning"]        = df["Kommune_befolkning"]
    out["Kommunestørrelse"]  = df["Kommune_kategori"].map(vlabels["Kommune_kategori"])
    out.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Saved data CSV to {path}")


def save_csv(df, path, vlabels):
    """Save an aggregated CSV with one row per municipality.

    Columns: Kommunenummer, Kommune, Fylke, Befolkning, Kommunestørrelse,
             Target (required responses), Antall (actual responses).
    """
    summary = df.groupby("Kommune", as_index=False).agg(
        Fylke=("Fylke", "first"),
        Befolkning=("Kommune_befolkning", "first"),
        Kommunestørrelse=("Kommune_kategori", "first"),
        Antall=("Kommune", "count"),
    )
    summary["Target"]         = summary["Kommunestørrelse"].map(TARGETS)
    summary["Kommunenummer"]  = summary["Kommune"].astype(int)
    summary["Kommune"]        = summary["Kommune"].map(vlabels["Kommune"])
    summary["Fylke"]          = summary["Fylke"].map(vlabels["Fylke"])
    summary["Kommunestørrelse"] = summary["Kommunestørrelse"].map(vlabels["Kommune_kategori"])
    summary = summary[["Kommunenummer", "Kommune", "Fylke", "Befolkning", "Kommunestørrelse", "Target", "Antall"]]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(f"Oppdatert,{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        summary.to_csv(f, index=False)
    print(f"Saved CSV to {path}")


def main():
    """Entry point: read, enrich, and export survey data."""
    parser = argparse.ArgumentParser(description="Prepare Syklistforeningen survey data.")
    parser.add_argument("--dummy", type=int, metavar="N", help="Append N dummy cases and save to _dummy.sav")
    args = parser.parse_args()

    kommuner, _, _, befolkning_map = load_lookups()

    df, meta = pyreadstat.read_sav(SAV_PATH)
    vlabels = meta.variable_value_labels
    clabels = meta.column_names_to_labels
    print("Columns:", df.columns.tolist())
    print("Shape:", df.shape)

    df, vlabels, clabels = add_kommune_fylke(df, vlabels, clabels)
    df, vlabels, clabels = add_befolkning(df, befolkning_map, vlabels, clabels)
    df, vlabels, clabels = add_kategori(df, vlabels, clabels)

    print("\nKommune_kategori value counts:")
    print(df["Kommune_kategori"].value_counts(dropna=False))

    sav_stem = Path(SAV_PATH).stem
    sav_dir = Path(SAV_PATH).parent

    if args.dummy:
        dummy = generate_dummy(args.dummy, kommuner, befolkning_map)
        dummy["StartTime"] = generate_dummy_dates(args.dummy)
        dummy, _, _ = add_kommune_fylke(dummy, {}, {})
        dummy, _, _ = add_befolkning(dummy, befolkning_map, {}, {})
        dummy, _, _ = add_kategori(dummy, {}, {})
        n_original = len(df)
        df = pd.concat([df, dummy], ignore_index=True)
        out_path = sav_dir / f"{sav_stem}_processed_dummy.sav"
        suffix_label = f"({n_original} original + {args.dummy} dummy)"
    else:
        out_path = sav_dir / f"{sav_stem}_processed.sav"
        suffix_label = ""

    csv_name = "summary_kommuner_dummy.csv" if args.dummy else "summary_kommuner.csv"
    summary_path = sav_dir / csv_name
    save_csv(df, summary_path, vlabels)

    data_csv_name = "data_kommuner_dummy.csv" if args.dummy else "data_kommuner.csv"
    data_path = sav_dir / data_csv_name
    save_data_csv(df, data_path, vlabels)

    detail_csv_name = "detail_kommuner_dummy.csv" if args.dummy else "detail_kommuner.csv"
    detail_path = sav_dir / detail_csv_name
    save_detail_csv(df, detail_path, vlabels)

    upload_to_dropbox(summary_path)
    upload_to_dropbox(data_path)
    upload_to_dropbox(detail_path)

    write_sav(df, out_path, column_labels=clabels, variable_value_labels=vlabels)
    print(f"\nSaved {len(df)} rows {suffix_label}to {out_path}".replace("  ", " "))
    print("\nKommune_kategori value counts:")
    print(df["Kommune_kategori"].value_counts(dropna=False))

    return df


if __name__ == "__main__":
    main()
