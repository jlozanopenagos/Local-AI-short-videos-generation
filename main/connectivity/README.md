# Google Sheets Connectivity Suite

Modular integration layer connecting Google Sheets to the `shorts_automation` pipeline using Google Apps Script Web App endpoints.

---

## Architecture Overview

The `main/connectivity` package is organized into dedicated functional subpackages, keeping **only the principal executable runner scripts** (and lightweight backward-compatibility aliases) at the root:

```text
main/connectivity/
├── sync_sheets.py                       # Principal Runner 1: Syncs Sheets to synced_sheets/_3_columns/ or _4_columns/
├── fetch_corrected_scripts.py           # Principal Runner 2: Pulls Column D (SCRIPT_CHANGED) to CSV
├── reconcile_scripts.py                 # Principal Runner 3: Audits & reorganizes local scripts against Sheets
├── post_scripts.py                      # Principal Runner 4: Posts scripts to Google Sheets (Cols A-C or A:D)
├── scan_ready_scripts.py                # Principal Runner 5: Scans ready scripts and exports by date
├── cli.py                               # Backward-compatibility alias for sync_sheets.py
├── corrected_scripts_fetching.py        # Backward-compatibility alias for fetch_corrected_scripts.py
├── core/                                # Shared infrastructure & HTTP client
│   ├── endpoints.py                     # All 16 endpoints, Option A master router & spreadsheet ID extractor
│   ├── client.py                        # Resilient HTTP GET & POST client (302 redirects, auto-retries, error parsing)
│   └── __init__.py                      # Package exports
├── apps_script/                         # Google Apps Script Web App source code & deployment
│   ├── google_apps_script.js            # Active Web App implementation (doGet & doPost) [gitignored]
│   ├── google_apps_script.sample.js     # Canonical template sample for Code.gs deployment
│   └── README.md                        # Step-by-step Apps Script Web App deployment guide
├── sheet_sync/                          # Feature 1 Implementation: Sheet to CSV Sync
│   ├── sync_service.py                  # Fetches records into D:\AI\output\connectivity\synced_sheets\_3_columns or _4_columns
│   └── __init__.py                      # Package exports
├── corrected_scripts/                   # Feature 2 Implementation: Corrected Scripts Fetching
│   ├── fetcher.py                       # Fetches Column D into main/input/csv/script_to_change/
│   └── __init__.py                      # Package exports
├── reconcile/                           # Feature 3 Implementation: Reconcile & Reorganize
│   ├── service.py                       # Reorganizes local scripts to match Google Sheets order
│   └── __init__.py                      # Package exports
├── post_scripts/                        # Feature 4 Implementation: Post Scripts to Sheets
│   ├── poster.py                        # Pushes scripts to Google Sheets with 3-col or 4-col options
│   └── __init__.py                      # Package exports
├── ready_scripts/                       # Feature 5 Implementation: Scan Ready Scripts by Date
│   ├── scanner.py                       # Filters Columns E-H and exports daily tracking CSVs
│   └── __init__.py                      # Package exports
└── README.md                            # Comprehensive connectivity manual
```

---

## The 5 Features & Principal Runner Scripts

### 1. Sync Sheets Data (`sync_sheets.py`)
- **Action**: Pulls Google Sheets records. Interactively prompts whether to export:
  - **3 columns**: `ID`, `expression`, `script` (Standard)
  - **4 columns**: `ID`, `expression`, `script`, `SCRIPT_CHANGED`
- **Destination**:
  - 3 columns: `D:\AI\output\connectivity\synced_sheets\_3_columns\<language>\<video_type>\<language>_<type>_connectivity.csv`
  - 4 columns: `D:\AI\output\connectivity\synced_sheets\_4_columns\<language>\<video_type>\<language>_<type>_connectivity.csv`
- **Usage**:
  ```powershell
  # Interactive mode (asks whether to include 4th column):
  py main/connectivity/sync_sheets.py --all

  # Explicitly export 4 columns (bypasses prompt):
  py main/connectivity/sync_sheets.py --all --four-columns

  # Explicitly export standard 3 columns (bypasses prompt):
  py main/connectivity/sync_sheets.py --all --three-columns

  # Sync specific sheet:
  py main/connectivity/sync_sheets.py -l french -t expression

  # (Backward-compatibility alias: py main/connectivity/cli.py also supported)
  ```

### 2. Fetch Corrected Scripts (`fetch_corrected_scripts.py`)
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
  py main/connectivity/fetch_corrected_scripts.py

  # (Backward-compatibility alias: py main/connectivity/corrected_scripts_fetching.py also supported)
  ```

### 3. Reconcile & Reorganize Scripts (`reconcile_scripts.py`)
- **Action**: Audits and reconciles local scripts (`D:\AI\output\scripts_to_see`) against Google Sheets connectivity data (`D:\AI\output\connectivity\synced_sheets\_3_columns`).
- **Ordering & Preservation Rules**:
  - Strictly preserves Google Sheets row order.
  - Keeps Google Sheets canonical expression names when local has scenario notes or variants.
  - Appends new local entries (not found in Google Sheets, such as `FF06`–`FF15`) to the end of the file.
  - Preserves Google Sheets entries not in local in place.
- **Output Destination**:
  - Saves clean, mass-update-ready CSVs to `D:\AI\output\connectivity\scripts_to_post\<language>\<type>\<lang>_<type>_scripts.csv`.
  - Seamlessly recognized by `post_scripts.py` as the top-priority source folder.
- **Interactive Options**:
  - `[1] Check & audit differences across all 16 sheets (Dry Run)`
  - `[2] Reorganize ALL 16 sheets and save to scripts_to_post`
  - `[3] Check & reorganize a specific sheet`
  - `[4] Reorganize ALL sheets and immediately launch post_scripts.py`
  - `[0] Exit`
- **Usage**:
  ```powershell
  py main/connectivity/reconcile_scripts.py
  py main/connectivity/reconcile_scripts.py --dry-run
  py main/connectivity/reconcile_scripts.py --all
  ```

### 4. Post Scripts to Google Sheets (`post_scripts.py`)
- **Action**: Reads script files from `D:\AI\output\connectivity\scripts_to_post` (or fallback `scripts_to_see` / `_4_columns`) and updates Google Sheets.
- **Safety Guarantee**: In standard mode (choice 1), affects **ONLY** Columns A (`ID`), B (`expression`), and C (`script`). Column D (`SCRIPT_CHANGED`) is strictly preserved untouched unless option 2 (4 columns) is explicitly chosen.
- **Interactive Options**:
  - `[1] Update a specific sheet (all entries)`
	- `1) ID, expression, script columns`
	- `2) ID, expression, script and script_changed columns`
  - `[2] Update a specific sheet by range (e.g. 10-20)`
	- `1) ID, expression, script columns`
	- `2) ID, expression, script and script_changed columns`
  - `[3] Update a specific sheet by ID(s) (e.g. FE01, FE05)`
	- `1) ID, expression, script columns`
	- `2) ID, expression, script and script_changed columns`
  - `[4] Update ALL languages and types (all 16 sheets)`
	- `1) ID, expression, script columns`
	- `2) ID, expression, script and script_changed columns`
  - `[0] Exit`
- **Shortcuts**: Supports compound inputs directly on the menu prompt (e.g., `1.1` for operation 1 with 3 columns, `1.2` or `4.2` for 4 columns).
### 5. Scan Ready Scripts by Date (`scan_ready_scripts.py`)
- **Action**: Scans Google Sheets for rows where `script_ready` (Column E) is checked and `video_ready` (Column G) is NOT checked.
- **Exclusion Rule**: If `video_ready` is checked (`TRUE`), the ID is strictly **SKIPPED** (video is already done).
- **Date Grouping**: Groups matching `ID` and `expression` records by `script_date` (Column F, normalized to canonical `YYYY-MM-DD`). Supports both 4-digit (`2026-09-23`) and 2-digit (`23/09/26`) year notations across `/`, `-`, and `.` separators.
- **Primary Export**:
  `D:\AI\output\connectivity\ready_scripts\<YYYY-MM-DD>_ready_scripts.csv` (Schema: `ID,expression`).
- **Interactive Work-With Export (`ready_scripts_to_work_with.csv`)**:
  Before finishing (in both All Sheets and Single Sheet modes), prompts the user in the terminal whether to also generate a CSV with `ID` and `SCRIPT_CHANGE` (Column D):
  - File: `D:\AI\output\connectivity\ready_scripts\<YYYY-MM-DD>_ready_scripts_to_work_with.csv` (Schema: `ID,SCRIPT_CHANGE`).
  - **Error Handling (`error_report.csv`)**: If any script is marked `script_ready` but has an empty `SCRIPT_CHANGE` cell, it is logged to `D:\AI\output\connectivity\ready_scripts\error_report.csv` with schema `ID,problem`. Valid scripts continue to be exported normally.
  - **Auto-Pruning Errors**: When the user subsequently fixes `SCRIPT_CHANGE` in Google Sheets and re-scans, resolved IDs are automatically removed from `error_report.csv` (and the file is deleted once all errors are cleared).
- **Missing Date Fallback & Auto-Pruning**: If `script_ready` is checked but `script_date` is blank, records are saved to `undated_ready_scripts.csv` (and `undated_ready_scripts_to_work_with.csv` if requested). When dates are subsequently filled in on Google Sheets, the scanner automatically prunes resolved items from the undated files.
- **Interactive Options**:
  - `[1] Scan ALL 16 Google Sheets and export by date (Default)`
  - `[2] Scan a specific sheet`
  - `[0] Exit`
- **Usage**:
  ```powershell
  # Interactive mode (prompts for work_with CSV export):
  py main/connectivity/scan_ready_scripts.py

  # Scan all sheets non-interactively without prompt:
  py main/connectivity/scan_ready_scripts.py --all --work-with     # exports both CSVs
  py main/connectivity/scan_ready_scripts.py --all --no-work-with  # exports only ready_scripts.csv

  # Scan specific sheet:
  py main/connectivity/scan_ready_scripts.py -l french -t expression
  ```

---

## Google Apps Script Deployment (Option A Master Router)

We use **Option A** dynamic routing: a single deployed Web App script acts as the master router for all 16 Google Sheets via `?id=<SPREADSHEET_ID>`.

### Deployment Instructions:
1. Open your master Google Sheet.
2. Go to **Extensions > Apps Script**.
3. Replace the contents of `Code.gs` with the complete code from [`apps_script/google_apps_script.sample.js`](apps_script/google_apps_script.sample.js).
4. Click **Save** (💾).
5. Click **Deploy > Manage deployments**.
6. Click the **pencil icon** (Edit) on the active deployment.
7. Under **Version**, select **New version**.
8. Click **Deploy**.
For detailed setup instructions, see [`apps_script/README.md`](apps_script/README.md).

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

# 3. Reconcile and reorganize scripts to follow Google Sheets order
from connectivity import reconcile_sheet_data, reconcile_single_sheet, reconcile_all_sheets
summary = reconcile_all_sheets()  # saves to D:\AI\output\connectivity\scripts_to_post

# 4. Post scripts to Google Sheets (Columns A, B, C or A:D)
from connectivity import post_single_sheet, post_all_sheets
post_single_sheet(language="french", video_type="expression", mode="range", range_spec="01-20")
post_all_sheets()

# 5. Scan ready scripts and export by date
from connectivity import scan_sheet_ready_scripts, scan_all_sheets_ready_scripts, save_ready_scripts_by_date
summary = scan_all_sheets_ready_scripts()
save_ready_scripts_by_date(summary["date_groups"])  # saves to D:\AI\output\connectivity\ready_scripts
```

