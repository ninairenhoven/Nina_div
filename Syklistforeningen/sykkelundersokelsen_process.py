"""Main pipeline for processing Syklistforeningen survey data.

By default, downloads the latest SPSS data from Decipher before processing.
Use --local to skip the download and use the existing local file instead.

Reads the raw SPSS .sav file, enriches each row with municipality/county
labels, population figures, and a size category, then writes the result
back to a new .sav file together with three CSV exports:

* summary_kommuner.csv  – one row per municipality: Kommunenummer, Kommune,
                          Fylke, Befolkning, Kommunestørrelse, Requirement,
                          Goal, Antall. First line is 'Oppdatert,YYYY-MM-DD HH:MM'
                          (dashboard timestamp). Uploaded to Dropbox.

* detail_kommuner.csv   – one row per (municipality, date): Kommunenummer,
                          Kommune, Dato, Antall. Used by the detail page timeline
                          chart. Uploaded to Dropbox.

* data_kommuner.csv     – one row per respondent: uuid, Dato, Kommunenummer,
                          Kommune, Fylkesnummer, Fylke, Befolkning,
                          Kommunestørrelse. Saved locally only (not uploaded).

Append _dummy to each name when using --dummy.

Usage
-----
    python sykkelundersokelsen_process.py               # download from Decipher, then process
    python sykkelundersokelsen_process.py --local       # use existing local .sav file
    python sykkelundersokelsen_process.py --dummy 500   # append 500 synthetic respondents
"""
import argparse
from datetime import datetime, timedelta
import io
import os
from pathlib import Path
import re
import zipfile

import dropbox
from dropbox.files import WriteMode
import numpy as np
import pandas as pd
import pyreadstat

os.environ.setdefault('BEACON_HOST', 'https://opiniongroup.decipherinc.com')
from decipher.beacon import api

SCRIPT_DIR = Path(__file__).parent

# ── Decipher configuration ────────────────────────────────────────────────────
# Survey path and layout ID from opiniongroup.decipherinc.com.
# Requires environment variable: BEACON_KEY (64-character API key).
DECIPHER_SURVEY = 'surveys/selfserve/4923/260315'
DECIPHER_LAYOUT = 399
SAV_PATH = r"C:\Users\NinaIrenHoven\Opinion AS\Opinion SharePoint - Syklistforeningen\Data 2026\260315_api.sav"
OUTPUT_DIR = Path(SAV_PATH).parent
OUTPUT_STEM = "sykkelundersøkelsen"

# ── Response thresholds ───────────────────────────────────────────────────────
# Required number of answers per municipality size category (Kommune_kategori 1–5)
REQUIREMENTS = {
    1: 50,   # Under 20 000
    2: 50,   # 20 000–49 999
    3: 75,   # 50 000–99 999
    4: 100,  # 100 000–199 999
    5: 200,  # Over 200 000
}

# Aspirational targets (higher than minimum requirements)
GOALS = {
    1: 100,   # Under 20 000
    2: 200,   # 20 000–49 999
    3: 500,   # 50 000–99 999
    4: 750,   # 100 000–199 999
    5: 1000,   # Over 200 000
}

# SPSS dates are stored as seconds since this epoch
SPSS_EPOCH = datetime(1582, 10, 14)

# Google Maps zoom level labels (applied to _r12 columns)
ZOOM_LABELS = {
    0:  "0 World/continent",
    1:  "1 World/continent",
    2:  "2 World/continent",
    3:  "3 World/continent",
    4:  "4 Country",
    5:  "5 Country",
    6:  "6 Country",
    7:  "7 Region/large area",
    8:  "8 Region/large area",
    9:  "9 Region/large area",
    10: "10 City level",
    11: "11 City level",
    12: "12 City level",
    13: "13 Neighbourhood/street",
    14: "14 Neighbourhood/street",
    15: "15 Neighbourhood/street",
    16: "16 Block/building",
    17: "17 Block/building",
    18: "18 Block/building",
    19: "19 Very precise (entrance level)",
    20: "20 Very precise (entrance level)",
}


# ── Lookup helpers ────────────────────────────────────────────────────────────

def load_lookups():
    """Load municipality/county and population lookup tables from CSV files.

    Returns:
        kommuner: DataFrame with Kommunenummer, Fylkesnummer, and name columns.
        kommune_labels: Dict mapping kommunenummer (int) to Norwegian municipality name.
        fylke_labels: Dict mapping fylkesnummer (int) to county name.
        befolkning_map: Dict mapping kommunenummer (int) to population (2026).
    """
    kommuner = pd.read_csv(SCRIPT_DIR / "fylker-kommuner-2024.csv", encoding="utf-8-sig")
    befolkning = pd.read_csv(SCRIPT_DIR / "befolkning-kommuner-2026.csv", encoding="utf-8-sig")

    kommune_labels = dict(zip(kommuner["Kommunenummer"].astype(int), kommuner["Kommunenavn norsk"]))
    fylke_labels = dict(zip(kommuner["Fylkesnummer"].astype(int), kommuner["Fylkesnavn"]))
    befolkning_map = dict(zip(befolkning["Kommunenummer"].astype(int), befolkning["Befolkning"]))

    return kommuner, kommune_labels, fylke_labels, befolkning_map


def add_kommune_fylke(df, vlabels, clabels, kommune_labels, fylke_labels):
    """Add numeric Kommune and Fylke columns derived from Municipality_number.

    Kommune is set to the kommunenummer (same as Municipality_number).
    Fylke is derived by removing the last two digits of Municipality_number.
    Returns df, vlabels, clabels with Kommune entries added.
    """
    df["Kommune"] = df["Municipality_number"].astype(float)
    df["Fylke"] = (df["Municipality_number"].astype("Int64") // 100).astype(float)
    vlabels["Kommune"] = {float(k): v for k, v in kommune_labels.items()}
    vlabels["Fylke"] = {float(k): v for k, v in fylke_labels.items()}
    clabels["Kommune"] = "Kommune"
    clabels["Fylke"] = "Fylke"
    return df, vlabels, clabels


def add_befolkning(df, befolkning_map, vlabels, clabels):
    """Add Kommune_befolkning column with population per municipality (2026).

    Returns df, vlabels, clabels with Kommune_befolkning column label added.
    """
    df["Kommune_befolkning"] = df["Kommune"].astype("Int64").map(befolkning_map)
    clabels["Kommune_befolkning"] = "Befolkning (2026)"
    return df, vlabels, clabels


def add_kategori(df, vlabels, clabels):
    """Add Kommune_kategori column categorising municipalities by population size.

    Categories: Under 20 000 / 20 000–49 999 / 50 000–99 999 / 100 000–199 999 / Over 200 000.
    Returns df, vlabels, clabels with Kommune_kategori entries added.
    """
    categories = {1: "Under 20 000", 2: "20 000–49 999", 3: "50 000–99 999", 4: "100 000–199 999", 5: "Over 200 000"}
    df["Kommune_kategori"] = pd.cut(
        df["Kommune_befolkning"],
        bins=[0, 20000, 50000, 100000, 200000, float("inf")],
        labels=list(categories.keys()),
        right=True,
    ).astype(float)
    vlabels["Kommune_kategori"] = {float(k): v for k, v in categories.items()}
    clabels["Kommune_kategori"] = "Kommunestørrelse"
    return df, vlabels, clabels


def clean_column_labels(clabels):
    """Strip the variable name prefix from column labels.

    Decipher often exports labels in the form "varname: Human readable text".
    This function removes the leading "varname: " so only the readable part remains.

    Example:
        {"Q5_elr6": "Q5_elr6: Funksjonstilpasset sykkel ..."}
        → {"Q5_elr6": "Funksjonstilpasset sykkel ..."}
    """
    cleaned = {}
    for col, label in clabels.items():
        label = label.strip().rstrip(":")
        prefix = f"{col}: "
        if label.startswith(prefix):
            remainder = label[len(prefix):].strip().rstrip(":")
            cleaned[col] = col if remainder in ("Captured variable", "") else remainder
        else:
            cleaned[col] = label if label else col

    _strip_prefix = "Du har markert"
    _strip_substrings = [
        "Vennligst plasser markøren så nøyaktig som mulig i kartet.",
        "beskriv kort, utdyp på neste side",
        "Klikk direkte i kartet, eller skriv i søkefeltet og velg riktig adresse fra listen. Vær så presis som mulig.",
        "Hvis du vil endre plasseringen, klikk på Forrige for å gå tilbake til kartet",
    ]
    result = {}
    for col, label in cleaned.items():
        if label.startswith(_strip_prefix):
            label = label[len(_strip_prefix):].strip()
        for s in _strip_substrings:
            label = label.replace(s, "").strip()
        label = label.strip().rstrip(":")
        result[col] = label if label else col
    return result


def write_sav(df, path, column_labels=None, variable_value_labels=None):
    """Write a DataFrame to an SPSS .sav file.

    If the file is open in SPSS, the user is prompted to close it before retrying.
    """
    path = Path(path)
    kwargs = {}
    if column_labels is not None:
        kwargs["column_labels"] = column_labels
    if variable_value_labels is not None:
        kwargs["variable_value_labels"] = variable_value_labels
    while True:
        try:
            path.open("ab").close()
        except PermissionError:
            input(f"File is open: {path.name}\nClose it in SPSS, then press Enter to retry...")
            continue
        pyreadstat.write_sav(df, str(path), **kwargs)
        break


def download_from_decipher(output_path: Path) -> Path:
    """Download the latest SPSS data from Decipher and save to output_path.

    Decipher returns a zip archive containing a .sav file; this function
    extracts it. If the response is already a raw .sav, it is written directly.

    Requires environment variable: BEACON_KEY
    """
    api_kwargs = {'layout': DECIPHER_LAYOUT} if DECIPHER_LAYOUT else {}
    print(f'Laster ned SPSS-data fra Decipher ({DECIPHER_SURVEY})...')

    if output_path.exists():
        try:
            output_path.rename(output_path)   # check file is not open in another program
        except PermissionError:
            raise PermissionError(
                f'Filen er åpen i et annet program. Lukk den og prøv igjen: {output_path}'
            )

    data = api.get(
        DECIPHER_SURVEY + '/data',
        format='spss16',
        cond='qualified or partial',
        **api_kwargs,
    )

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            sav_files = [f for f in zf.namelist() if f.endswith('.sav')]
            if not sav_files:
                raise ValueError(f'Ingen .sav-fil i zip-arkivet. Innhold: {zf.namelist()}')
            sav_content = zf.read(sav_files[0])
    except zipfile.BadZipFile:
        sav_content = data   # response was already a raw .sav

    with open(output_path, 'wb') as f:
        f.write(sav_content)
    print(f'Lagret til {output_path.name}')
    return output_path


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

def generate_dummy_dates(n):
    """Return a list of n random date strings (YYYY-MM-DD) spread from April 1st to today (inclusive).

    Used to populate the StartTime column of dummy respondents.
    """
    rng = np.random.default_rng(42)
    today = pd.Timestamp.today().normalize()
    start = pd.Timestamp(today.year, 4, 1)
    n_days = (today - start).days + 1
    offsets = rng.integers(0, n_days, size=n)
    return [(start + pd.Timedelta(days=int(d))).strftime("%Y-%m-%d") for d in offsets]


def generate_dummy(n, kommuner, befolkning_map):
    """Generate n dummy survey rows sampled from the 20 largest + 20 random municipalities.

    Sampling is population-weighted within the combined pool.
    Returns a DataFrame with a single column ``Municipality_number`` (kommunenummer as int).
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
    return pd.DataFrame({"Municipality_number": sampled})


def save_detail_csv(df, path, vlabels):
    """Save a pre-aggregated CSV with one row per (municipality, date).

    Columns: Kommunenummer, Kommune, Dato, Antall.
    """
    out = pd.DataFrame()
    out["Kommunenummer"] = df["Kommune"].astype("Int64")
    out["Kommune"]       = df["Kommune"].map(vlabels["Kommune"])
    # Responses before survey launch (2026-04-22) are rebucketed to launch date
    out["Dato"]          = df["StartTime"].str[:10].clip(lower="2026-04-22")
    detail = out.groupby(["Kommunenummer", "Kommune", "Dato"], as_index=False).size().rename(columns={"size": "Antall"})
    detail = detail.sort_values(["Kommunenummer", "Dato"])
    print(path.name)
    detail.to_csv(path, index=False, encoding="utf-8-sig")


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
    print(path.name)
    out.to_csv(path, index=False, encoding="utf-8-sig")


def save_alldata_csv(df, path, vlabels, columns):
    """Save selected respondent columns to CSV, applying value labels where available.

    Args:
        columns: list of column names to include (must exist in df).
    Columns with entries in vlabels are replaced with their label strings.
    """
    out = df[columns].copy()

    for col, labels in vlabels.items():
        if col in out.columns:
            out[col] = out[col].map(labels)

    print(path.name)
    out.to_csv(path, index=False, encoding="utf-8-sig")


def save_stacked_csv(df, path, vlabels, id_cols, columns):
    """Save a stacked (long-format) CSV for map columns.

    Builds a 3-level column MultiIndex (question, rank, suffix), sets id_cols as
    the row index, replaces 0 and empty strings with NaN, then stacks on the rank
    level (dropna=True removes rows where all values are NaN). Flattens the
    remaining (question, suffix) MultiIndex back to "Q{n}_{suffix}".

    Returns {base_col: rank1_orig_col} for building column labels externally.
    """
    rank_pattern = re.compile(r'^(Q\d+)_([123])(.*)$')

    parsed = [(col, m.group(1), int(m.group(2)), m.group(3))
              for col in columns if col not in id_cols
              for m in [rank_pattern.match(col)] if m]

    orig_cols = [col for col, *_ in parsed]

    sub = df.set_index(id_cols)[orig_cols].copy()
    sub.columns = pd.MultiIndex.from_tuples(
        [(q, rank, suffix) for _, q, rank, suffix in parsed],
        names=['question', 'rank', 'suffix'],
    )

    # Treat 0 and empty strings as missing so stack dropna removes empty rows
    sub = sub.mask(sub == 0).mask(sub == "")

    stacked = sub.stack(level='rank', future_stack=True).dropna(how='all')
    stacked.columns = [f"{q}_{s}" if s else q for q, s in stacked.columns]
    out = stacked.reset_index()

    rank1_map = {(f"{q}_{s}" if s else q): col for col, q, rank, s in parsed if rank == 1}

    # Apply value labels for id_cols by original name, base cols via rank1_map
    for col in id_cols:
        if col in vlabels and col in out.columns:
            out[col] = out[col].map(vlabels[col])
    for base, orig in rank1_map.items():
        if orig in vlabels and base in out.columns:
            out[base] = out[base].map(vlabels[orig])

    print(path.name)
    out.to_csv(path, index=False, encoding='utf-8-sig')

    return rank1_map


def save_csv(df, path, vlabels):
    """Save an aggregated CSV with one row per municipality.

    Columns: Kommunenummer, Kommune, Fylke, Befolkning, Kommunestørrelse,
             Requirement (min required responses), Goal (aspirational target), Antall (actual responses).
    """
    summary = df.groupby("Kommune", as_index=False).agg(
        Fylke=("Fylke", "first"),
        Befolkning=("Kommune_befolkning", "first"),
        Kommunestørrelse=("Kommune_kategori", "first"),
        Antall=("Kommune", "count"),
    )
    summary["Requirement"]    = summary["Kommunestørrelse"].map(REQUIREMENTS)
    summary["Goal"]           = summary["Kommunestørrelse"].map(GOALS)
    summary["Kommunenummer"]  = summary["Kommune"].astype(int)
    summary["Kommune"]        = summary["Kommune"].map(vlabels["Kommune"])
    summary["Fylke"]          = summary["Fylke"].map(vlabels["Fylke"])
    summary["Kommunestørrelse"] = summary["Kommunestørrelse"].map(vlabels["Kommune_kategori"])
    summary = summary[["Kommunenummer", "Kommune", "Fylke", "Befolkning", "Kommunestørrelse", "Requirement", "Goal", "Antall"]]
    print(path.name)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(f"Oppdatert,{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        summary.to_csv(f, index=False)


def main():
    """Entry point: optionally download from Decipher, then read, enrich, and export survey data."""
    parser = argparse.ArgumentParser(description="Prepare Syklistforeningen survey data.")
    parser.add_argument("--local",  action="store_true", help="Skip Decipher download and use existing local .sav file")
    parser.add_argument("--dummy", type=int, metavar="N", help="Append N dummy cases and save to _dummy.sav")
    args = parser.parse_args()

    read_path = Path(SAV_PATH)

    if args.local:
        print(f"--local: bruker eksisterende fil: {SAV_PATH}")
    else:
        download_from_decipher(read_path)

    kommuner, kommune_labels, fylke_labels, befolkning_map = load_lookups()

    df, meta = pyreadstat.read_sav(read_path)
    vlabels = dict(meta.variable_value_labels)
    clabels = clean_column_labels(meta.column_names_to_labels)

    # Cast zoom columns to numeric and add human-readable zoom level labels
    for col in df.columns:
        if re.search(r'_[123]r12$', col):
            df[col] = pd.to_numeric(df[col], errors='coerce')
            vlabels[col] = {float(k): v for k, v in ZOOM_LABELS.items()}
    print("Columns:", ", ".join(df.columns.tolist()))
    print("Shape:", df.shape)

    df["date_dt"] = df["date"].apply(
        lambda s: SPSS_EPOCH + timedelta(seconds=s) if pd.notna(s) else None
    )
    df["date_str"] = df["date_dt"].apply(
        lambda d: d.strftime('%Y-%m-%d') if d is not None else None
    )

    n_before = len(df)
    df = df[df["status"] == 3].reset_index(drop=True)
    print(f"Filtered to status==3 (Qualified): {len(df)} of {n_before} rows")

    df, vlabels, clabels = add_kommune_fylke(df, vlabels, clabels, kommune_labels, fylke_labels)
    df, vlabels, clabels = add_befolkning(df, befolkning_map, vlabels, clabels)
    df, vlabels, clabels = add_kategori(df, vlabels, clabels)

    print("\nKommune_kategori value counts:")
    print(df["Kommune_kategori"].map(vlabels["Kommune_kategori"]).value_counts(dropna=False))

    print("\nMunicipality value counts:")
    print(df["Kommune"].map(vlabels["Kommune"]).value_counts(dropna=False))

    print("\nDate value counts:")
    print(df["date_str"].value_counts(dropna=False).sort_index())
    print()

    d = "_dummy" if args.dummy else ""

    if args.dummy:
        dummy = generate_dummy(args.dummy, kommuner, befolkning_map)
        dummy["StartTime"] = generate_dummy_dates(args.dummy)
        dummy, _, _ = add_kommune_fylke(dummy, {}, {}, kommune_labels, fylke_labels)
        dummy, _, _ = add_befolkning(dummy, befolkning_map, {}, {})
        dummy, _, _ = add_kategori(dummy, {}, {})
        n_original = len(df)
        df = pd.concat([df, dummy], ignore_index=True)
        suffix_label = f"({n_original} original + {args.dummy} dummy)"
    else:
        suffix_label = ""

    out_path = OUTPUT_DIR / f"{OUTPUT_STEM}_completes_processed{d}.sav"

    print(f"Output folder: {OUTPUT_DIR}")

    # Exclude municipality 2211 from dashboard exports only; map data files are unaffected.
    df_dashboard = df[df["Kommune"] != 2211]

    summary_path = OUTPUT_DIR / f"summary_kommuner{d}.csv"
    save_csv(df_dashboard, summary_path, vlabels)

    data_path = OUTPUT_DIR / f"data_kommuner{d}.csv"
    save_data_csv(df_dashboard, data_path, vlabels)

    detail_path = OUTPUT_DIR / f"detail_kommuner{d}.csv"
    save_detail_csv(df_dashboard, detail_path, vlabels)

    df["Dato"] = df["StartTime"].str[:10]
    id_cols = ["uuid", "Dato", "Q1", "Municipality_number"]
    mapdata_cols = id_cols + [c for c in df.columns if re.match(r'^Q1[3-6]', c)]
    # alldata_path = OUTPUT_DIR / f"{OUTPUT_STEM}_mapdata{d}.csv"
    # save_alldata_csv(df, alldata_path, vlabels, mapdata_cols)

    # labels_path = OUTPUT_DIR / f"{OUTPUT_STEM}_mapdata_column_labels.csv"
    # print(labels_path.name)
    # pd.DataFrame(
    #     [(col, clabels.get(col, "")) for col in mapdata_cols],
    #     columns=["Column", "Label"],
    # ).to_csv(labels_path, index=False, encoding="utf-8-sig")

    stacked_path = OUTPUT_DIR / f"{OUTPUT_STEM}_mapdata_stacked{d}.csv"
    base_rename = save_stacked_csv(df, stacked_path, vlabels, id_cols, mapdata_cols)

    # Build column label CSV for stacked output: id_cols + rank + base cols (labels from rank-1 originals)
    id_col_labels = {**{c: clabels.get(c, "") for c in id_cols}, "Dato": "Responsdato"}
    stacked_label_rows = (
        [(c, id_col_labels.get(c, "")) for c in id_cols]
        + [("rank", "Posisjon nummer (1–3)")]
        + [(base, clabels.get(orig, "")) for base, orig in base_rename.items()]
    )
    stacked_labels_path = OUTPUT_DIR / f"{OUTPUT_STEM}_mapdata_stacked_column_labels.csv"
    print(stacked_labels_path.name)
    pd.DataFrame(stacked_label_rows, columns=["Column", "Label"]).to_csv(
        stacked_labels_path, index=False, encoding="utf-8-sig"
    )

    upload_to_dropbox(summary_path)
    # upload_to_dropbox(data_path)  # not used by dashboard
    upload_to_dropbox(detail_path)
    # upload_to_dropbox(alldata_path)
    # upload_to_dropbox(labels_path)
    upload_to_dropbox(stacked_path)
    upload_to_dropbox(stacked_labels_path)

    print(f"\nSaving {out_path.name} ({len(df)} rows {suffix_label})".replace("  ", " ").rstrip())
    write_sav(df, out_path, column_labels=clabels, variable_value_labels=vlabels)

    return df


if __name__ == "__main__":
    main()
