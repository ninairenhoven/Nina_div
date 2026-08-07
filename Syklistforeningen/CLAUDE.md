# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Survey data processing pipeline for the Norwegian Cyclists' Association (Syklistforeningen), developed by Opinion AS. Reads raw SPSS survey responses, enriches them with Norwegian municipality/county and population data, exports CSVs, uploads them to Dropbox, and serves a live dashboard via HTML.

## Running the Pipeline

```bash
# Process real survey data and upload to Dropbox
python sykkelundersokelsen_process.py

# Process with N synthetic dummy respondents appended
python sykkelundersokelsen_process.py --dummy 500

# One-time setup: convert raw SSB population CSV to lookup table
python setup_befolkning.py

# Debug pyreadstat write failures
python debug.py
```

There is no test suite and no build step.

## Architecture

```
sykkelundersokelsen_process.py  ← main entry point
utils.py                        ← shared helpers (load_lookups, add_kommune_fylke,
                                   add_befolkning, add_kategori, write_sav)
setup_befolkning.py             ← one-time SSB data conversion (not part of main pipeline)
debug.py                        ← pyreadstat diagnostics → debug.log

sykkelundersøkelsen_datainnsamling_dashboard/                                          ← all dashboard files
  oversikt_sykkelundersokelsen.html        ← overview page (all municipalities)
  kommune_detail.html                               ← per-municipality detail page
  logo/
    Opinion_Logo_Horizontal.png
    SLF_logo_farge.png
```

**Data flow:**

1. Read SPSS file from SharePoint (`C:\Users\NinaIrenHoven\Opinion AS\Opinion SharePoint - Syklistforeningen\Data 2026\260315.sav`) — path is hardcoded.
2. Derive `Kommune` and `Fylke` from the `hFiler1` respondent field.
3. Join `fylker-kommuner-2024.csv` for municipality/county names.
4. Join `befolkning-kommuner-2026.csv` for 2026 population figures.
5. Bin municipalities into 5 size categories based on population thresholds.
6. Optionally append synthetic dummy respondents.
7. Write `{stem}_processed[_dummy].sav` to the SharePoint folder.
8. Write `summary_kommuner[_dummy].csv` and `data_kommuner[_dummy].csv` to the SharePoint folder, then upload both to Dropbox (overwriting existing files to keep share links stable).

## CSV Outputs

| File | Contents |
|---|---|
| `summary_kommuner.csv` | One row per municipality: Kommunenummer, Kommune, Fylke, Befolkning, Kommunestørrelse, Target, Antall. First line is `Oppdatert,YYYY-MM-DD HH:MM` (read by the dashboard as a timestamp). |
| `data_kommuner.csv` | One row per respondent: uuid, Dato, Kommunenummer, Kommune, Fylkesnummer, Fylke, Befolkning, Kommunestørrelse. |

## Dashboard

Two HTML files in `sykkelundersøkelsen_datainnsamling_dashboard/` that fetch CSVs directly from Dropbox and render in the browser — no server needed.

- **`oversikt_sykkelundersokelsen.html`** — overview table with filter dropdowns (Fylke, Kommunestørrelse, Kommune) and sortable columns (including Fremgang). Summary pills show total respondents, kommuner count, kommuner i mål, and snitt fremgang. Clicking a municipality name navigates to the detail page. Clicking a Fylke cell or Størrelse badge filters the table.
- **`kommune_detail.html`** — per-municipality page (opened via `?nr=<kommunenummer>`). Hero bar shows municipality name, fylke, innbyggere, størrelse, and mål. Shows a donut chart (progress % vs target, colour-coded red/yellow/teal) and a bar+line combo timeline (daily responses left axis, cumulative right axis). The right axis uses fixed step size (`target/10`, or `target/5` for target=75) so the target value always falls on a tick, highlighted in teal.

The "Oppdatert" timestamp in the footer is read from the first line of `summary_kommuner.csv`.

### Chart colours
- Teal `#71C3B4` — bars, donut fill (when on track), left y-axis labels
- Dark teal `#45A290` — left y-axis title
- Orange `#F26649` — cumulative line, right y-axis labels/title
- Target tick on right axis highlighted in teal

### Sorting
- All columns sortable; click header to toggle asc/desc
- Størrelse sorts by numeric category (1–5), not alphabetically by label

## Dropbox Upload

After each pipeline run, both CSVs are uploaded to the Dropbox app folder (`/Apps/Sykkelundersøkelsen_opinion/`) using the Dropbox Python SDK. Files are overwritten in place so existing share links remain valid.

Requires three environment variables (set via System Settings → Environment Variables → User Variables):

| Variable | Description |
|---|---|
| `DROPBOX_APP_KEY_SYKKEL` | App key from Dropbox App Console |
| `DROPBOX_APP_SECRET_SYKKEL` | App secret from Dropbox App Console |
| `DROPBOX_REFRESH_TOKEN_SYKKEL` | Long-lived refresh token (never expires) |

The Dropbox app is named **Sykkelundersøkelsen_opinion** and uses App folder access (scoped). It is separate from the RVU project's Dropbox app, which uses the `DROPBOX_*` env vars (no suffix).

## Lookup Files

| File | Contents |
|---|---|
| `fylker-kommuner-2024.csv` | Kommunenummer → municipality name + county name/number |
| `befolkning-kommuner-2026.csv` | Kommunenummer → 2026 population (generated by `setup_befolkning.py` from SSB raw data) |

`setup_befolkning.py` must be re-run whenever SSB releases updated population data; it converts their semicolon-separated, latin-1 encoded CSV into the clean lookup format the pipeline expects.

## Key Dependencies

- `pandas` — DataFrames and CSV I/O
- `pyreadstat` — Reading/writing SPSS `.sav` files with variable metadata
- `numpy` — Dummy data generation
- `dropbox` — Dropbox Python SDK for uploading CSVs

No `requirements.txt` exists; install dependencies manually.

## pyreadstat Pitfalls

See `feedback_pyreadstat_write.md` in memory. In short:
- Pre-check that the output `.sav` path is writable before calling `pyreadstat.write_sav`.
- Only pass `variable_value_labels` for **numeric** columns — passing labels for string columns causes silent failures.
