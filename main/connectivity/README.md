# Google Sheets Connectivity Suite

Modular integration layer connecting Google Sheets to the `shorts_automation` pipeline using Google Apps Script Web App endpoints.

---

## Architecture Overview

The `main/connectivity` package is partitioned into focused functional submodules:

```text
main/connectivity/
├── core/                                # Shared infrastructure & HTTP client
│   ├── endpoints.py                     # All 16 endpoints, Option A master router & spreadsheet ID extractor
│   ├── client.py                        # Resilient HTTP GET & POST client (302 redirects, auto-retries, error parsing)
│   └── __init__.py                      # Package exports
├── sheet_sync/                          # Feature 1: Sheet to CSV Sync
│   ├── sync_service.py                  # Fetches Columns A, B, C into D:\AI\output\connectivity\
│   └── __init__.py                      # Package exports
├── corrected_scripts/                   # Feature 2: Corrected Scripts Fetching
│   ├── fetcher.py                       # Fetches Column D (SCRIPT_CHANGED) into main/input/csv/script_to_change/
│   └── __init__.py                      # Package exports
├── post_scripts/                        # Feature 3: Post Scripts to Sheets
│   ├── poster.py                        # Pushes scripts from D:\AI\output\scripts_to_see to Google Sheets (Cols A-C only)
│   └── __init__.py                      # Package exports
├── google_apps_script.sample.js         # Canonical Apps Script sample template (doGet & doPost)
├── cli.py                               # CLI entry point for Feature 1 (Sync Sheets)
├── corrected_scripts_fetching.py        # Interactive CLI for Feature 2 (Fetch Corrected Scripts)
├── post_scripts.py                      # Interactive CLI for Feature 3 (Post Scripts to Sheets)
└── README.md                            # Comprehensive connectivity manual
```

---

## The 3 Features

### 1. Sync Sheets Data (`cli.py`)
- **Action**: Pulls `ID`, `expression`, and `script` (Columns A, B, C) from Google Sheets.
- **Destination**:
  `D:\AI\output\connectivity\<language>\<video_type>\<language>_<type>_connectivity.csv`
- **Usage**:
  ```powershell
  # Sync all 16 sheets in batch mode:
  py main/connectivity/cli.py --all

  # Sync specific sheet:
  py main/connectivity/cli.py -l french -t expression
  ```

### 2. Fetch Corrected Scripts (`corrected_scripts_fetching.py`)
- **Action**: Extracts Column D (`SCRIPT_CHANGED`) and exports rows that have corrections.
- **Destination**:
  `C:\AI\shorts_automation\main\input\csv\script_to_change\<language>_<type>_script_to_change.csv` with schema `ID, NEW_SCRIPT`.
- **Interactive Options**:
  - `[1] Single Sheet`: pick language & video type, then filter by:
    - `[1] All Entries`
    - `[2] By Range` (e.g. `01-50`)
    - `[3] By IDs` (e.g. `FE01, FE04`)
    - `[4] By CSV` (reads `main/input/csv/script_to_change/ids_to_fetch.csv`)
  - `[2] All Sheets`: fetches across all 16 sheets.
- **Usage**:
  ```powershell
  py main/connectivity/corrected_scripts_fetching.py
  ```

### 3. Post Scripts to Google Sheets (`post_scripts.py`)
- **Action**: Reads script files from `D:\AI\output\scripts_to_see\<language>\<video_type>\<language>_<type>_scripts.csv` and updates Google Sheets.
- **Safety Guarantee**: Affects **ONLY** Columns A (`ID`), B (`expression`), and C (`script`). Column D (`SCRIPT_CHANGED`) and any subsequent columns are **never touched or overwritten**.
- **Interactive Options**:
  - `[1] Specific Sheet — All entries`
  - `[2] Specific Sheet — By Range` (e.g. `10-20`)
  - `[3] Specific Sheet — By ID(s)` (e.g. `FE01, FE05`)
  - `[4] ALL Sheets — All 16 sheets in one batch`
- **Usage**:
  ```powershell
  py main/connectivity/post_scripts.py
  ```

---

## Google Apps Script Deployment (Option A Master Router)

We use **Option A** dynamic routing: a single deployed Web App script acts as the master router for all 16 Google Sheets via `?id=<SPREADSHEET_ID>`.

### Deployment Instructions:
1. Open your master Google Sheet.
2. Go to **Extensions > Apps Script**.
3. Replace the contents of `Code.gs` with the complete code from [`google_apps_script.sample.js`](google_apps_script.sample.js).
4. Click **Save** (💾).
5. Click **Deploy > Manage deployments**.
6. Click the **pencil icon** (Edit) on the active deployment.
7. Under **Version**, select **New version**.
8. Click **Deploy**.

---

## Python API Reference

```python
# 1. Sync sheet data to D:\AI\output\connectivity\
from connectivity import sync_sheet, sync_all_sheets
sync_sheet(language="french", video_type="expression")
sync_all_sheets()

# 2. Fetch corrected scripts from Column D
from connectivity import fetch_and_save_corrected_scripts, fetch_all_sheets_corrected_scripts
fetch_and_save_corrected_scripts(language="french", video_type="expression", mode="all")
fetch_all_sheets_corrected_scripts()

# 3. Post scripts to Google Sheets (Columns A, B, C)
from connectivity import post_single_sheet, post_all_sheets
post_single_sheet(language="french", video_type="expression", mode="range", range_spec="01-20")
post_all_sheets()
```
