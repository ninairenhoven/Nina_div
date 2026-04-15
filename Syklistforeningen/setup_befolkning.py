"""One-time setup script: converts the raw SSB population CSV to a clean lookup file.

Input:  "Befolkning kommuner 2026.csv"  (semicolon-separated, latin-1, SSB format)
Output: befolkning-kommuner-2026.csv    (Kommunenummer, Kommune, Befolkning)

Run once whenever the raw SSB file is updated.
"""
import pandas as pd
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

df = pd.read_csv(
    SCRIPT_DIR / "Befolkning kommuner 2026.csv",
    sep=";",
    encoding="latin-1",
    skiprows=1,
    header=0,
)

df.columns = ["region", "Befolkning"]

df["Kommunenummer"] = df["region"].str.extract(r"^(\d+)").astype(int)
df["Kommune"] = df["region"].str.extract(r"^\d+\s+(.+)$")
df = df[["Kommunenummer", "Kommune", "Befolkning"]]

out_path = SCRIPT_DIR / "befolkning-kommuner-2026.csv"
df.to_csv(out_path, index=False, encoding="utf-8-sig")
print(f"Saved {len(df)} rows to {out_path}")
print(df.head(10).to_string(index=False))
