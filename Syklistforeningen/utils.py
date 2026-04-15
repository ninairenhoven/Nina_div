"""Shared helpers for loading lookup tables, enriching survey DataFrames, and writing SPSS files."""
import pandas as pd
import pyreadstat
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


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


def add_kommune_fylke(df, vlabels, clabels):
    """Add numeric Kommune and Fylke columns derived from hFiler1.

    Kommune is set to the kommunenummer (same as hFiler1).
    Fylke is derived by removing the last two digits of hFiler1.
    Returns df, vlabels, clabels with Kommune entries added.
    """
    kommuner = pd.read_csv(SCRIPT_DIR / "fylker-kommuner-2024.csv", encoding="utf-8-sig")
    kommune_labels = dict(zip(kommuner["Kommunenummer"].astype(int), kommuner["Kommunenavn norsk"]))
    fylke_labels = dict(zip(kommuner["Fylkesnummer"].astype(int), kommuner["Fylkesnavn"]))
    df["Kommune"] = df["hFiler1"].astype(float)
    df["Fylke"] = (df["hFiler1"].astype("Int64") // 100).astype(float)
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
        print(f"Saved to {path}")
        break
