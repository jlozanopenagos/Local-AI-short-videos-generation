# Google Sheets & Google Drive Connectivity Suite

Modular integration layer connecting Google Sheets (via Google Apps Script Web App endpoints) and Google Drive (via Drive API v3) to the `shorts_automation` pipeline.

---

## Architecture Overview

The `main/connectivity` package is organized into dedicated functional subpackages, keeping **only the principal executable runner scripts** at the root:

```text
main/connectivity/
├── sync_sheets.py                       # Principal Runner 1: Syncs Sheets to synced_sheets/_3_columns/ or _4_columns/
├── fetch_corrected_scripts.py           # Principal Runner 2: Pulls Column D (SCRIPT_CHANGED) to CSV
├── reconcile_scripts.py                 # Principal Runner 3: Audits & reorganizes local scripts against Sheets
├── post_scripts.py                      # Principal Runner 4: Posts scripts to Google Sheets (Cols A-C or A:D)
├── scan_ready_scripts.py                # Principal Runner 5: Scans ready scripts and exports by date
├── sync_drive.py                        # Principal Runner 6: Google Drive bundle replacement
├── core/                                # Shared infrastructure & HTTP client
│   ├── endpoints.py                     # All 16 endpoints, Option A master router & spreadsheet ID extractor
│   ├── client.py                        # Resilient HTTP GET & POST client (302 redirects, auto-retries, error parsing)
│   └── __init__.py                      # Package exports
├── apps_script/                         # Google Apps Script Web App source code & deployment
│   ├── google_apps_script.js            # Active Web App implementation (doGet & doPost) [gitignored]
│   ├── google_apps_script.sample.js     # Canonical template sample for Code.gs deployment
│   └── README.md                        # Step-by-step Apps Script Web App deployment guide
├── drive_sync/                          # Feature 6 Implementation: Google Drive Export & Replacement Sync
│   ├── drive_client.py                  # GoogleDriveClient (OAuth2/Service Account, Shared Drives, Trash fallback)
│   ├── sync_service.py                  # Folder mapping, local asset check, clean deletion & resumable upload
│   └── __init__.py                      # Package exports
├── sheet_sync/                          # Feature 1 Implementation: Sheet to CSV Sync
│   ├── sync_service.py                  # Fetches records into <OUTPUT_DIR>/connectivity\synced_sheets\_3_columns or _4_columns
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
  - 3 columns: `<OUTPUT_DIR>/connectivity\synced_sheets\_3_columns\<language>\<video_type>\<language>_<type>_connectivity.csv`
  - 4 columns: `<OUTPUT_DIR>/connectivity\synced_sheets\_4_columns\<language>\<video_type>\<language>_<type>_connectivity.csv`
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
  ```

### 2. Fetch Corrected Scripts (`fetch_corrected_scripts.py`)
- **Action**: Extracts Column D (`SCRIPT_CHANGED` or `SCRIPT_CHANGE` alias) and Column B (`EXPRESSION`) across all 16 sheets (including `FUN_FACTS`) and exports rows with corrections.
- **Destination**:
  `main/input/csv/script_to_change/<language>_<type>_script_to_change.csv` with schema `ID, NEW_SCRIPT, EXPRESSION` (also compatible with legacy `ID, NEW_SCRIPT`).
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
  ```


### 2b. Audit & Synchronize Script Changes (`main/tools/check_script_changes.py`)
- **Action**: Bridges the gap between fetched Column D corrections (+ Column B `EXPRESSION` updates) in `main/input/csv/script_to_change/` and local State JSON files (`main/state/`).
- **Functionality**:
  - Compares every row in every CSV in `script_to_change/` against its local State JSON across all 4 formats (`EXPRESSION`, `GAME`, `ROLEPLAY`, `FUN_FACTS`).
  - Normalizes speaker prefixes (`Narrator:`), quotation marks, and line structures to eliminate false-positive diff reports, and uses **`collections.Counter` multiset diffing** for `GAME` scripts (with legacy duplicate `pressure == challenge` deduplication) so swapped/replaced words that appear elsewhere in the script are never missed.
  - **GAME & FUN_FACTS Format Awareness**: Merges blank-line-separated `GAME` options (`A:`/`B:`/`C:`/`D:`) into `challenge`, detects 5-paragraph no-pressure reveals via expanded `answer_patterns` (`script_modifier.py`), strips stress giveaways and connectors, synchronizes `chalkboard_exercise` with `challenge`, and parses 5-section `FUN_FACTS` (`hook`, `setup`, `discovery`, `explanation`, `payoff`).
  - Displays word count diffs and snippet previews.
  - Applying updates (`--apply`) saves modified scripts with zero section duplication, propagates Column B `EXPRESSION` topic updates (invalidating stale titles and visual anchors so downstream stages regenerate cleanly), and resets downstream stages (`voice_generation`, `image_generation`, `thumbnail_generation`, `video_assembly`) to `'pending'`.
- **Usage**:
  ```powershell
  # Check for differences without modifying state JSONs:
  py main/tools/check_script_changes.py --check-only

  # Apply all detected script updates across all sheets:
  py main/tools/check_script_changes.py --apply

  # Target a specific CSV or script ID:
  py main/tools/check_script_changes.py --csv english_game_script_to_change.csv --apply
  py main/tools/check_script_changes.py --script-id EE56 --apply
  ```

### 3. Reconcile & Reorganize Scripts (`reconcile_scripts.py`)
- **Action**: Audits and reconciles local scripts (`<OUTPUT_DIR>/scripts_to_see`) against Google Sheets connectivity data (`<OUTPUT_DIR>/connectivity\synced_sheets\_3_columns`).
- **Ordering & Preservation Rules**:
  - Strictly preserves Google Sheets row order.
  - Keeps Google Sheets canonical expression names when local has scenario notes or variants.
  - Appends new local entries (not found in Google Sheets, such as `FF06`–`FF15`) to the end of the file.
  - Preserves Google Sheets entries not in local in place.
- **Output Destination**:
  - Saves clean, mass-update-ready CSVs to `<OUTPUT_DIR>/connectivity\scripts_to_post\<language>\<type>\<lang>_<type>_scripts.csv`.
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
- **Action**: Reads script files from `<OUTPUT_DIR>/connectivity\scripts_to_post` (or fallback `scripts_to_see` / `_4_columns`) and updates Google Sheets.
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
- **Action**: Scans Google Sheets for approved scripts that still need production.
- **Exclusion Rule**: An undated `video_ready` row preserves the legacy completion rule. If the row has a release date (Column H), the scanner checks the local assembly status before excluding it.
- **Date Grouping**: Groups matching `ID` and `expression` records by `script_date` (Column F, normalized to canonical `YYYY-MM-DD`). Supports both 4-digit (`2026-09-23`) and 2-digit (`23/09/26`) year notations across `/`, `-`, and `.` separators.
- **Primary Export**:
  `<OUTPUT_DIR>/connectivity\ready_scripts\<YYYY-MM-DD>_ready_scripts.csv` (Schema: `ID,expression`).
- **Interactive Work-With Export (`ready_scripts_to_work_with.csv`)**:
  Before finishing (in both All Sheets and Single Sheet modes), prompts the user in the terminal whether to also generate a CSV with `ID` and `SCRIPT_CHANGE` (Column D):
  - File: `<OUTPUT_DIR>/connectivity\ready_scripts\<YYYY-MM-DD>_ready_scripts_to_work_with.csv` (Schema: `ID,SCRIPT_CHANGE`).
  - **Error Handling (`error_report.csv`)**: If any script is marked `script_ready` but has an empty `SCRIPT_CHANGE` cell, it is logged to `<OUTPUT_DIR>/connectivity\ready_scripts\error_report.csv` with schema `ID,problem`. Valid scripts continue to be exported normally.
  - **Auto-Pruning Errors**: When the user subsequently fixes `SCRIPT_CHANGE` in Google Sheets and re-scans, resolved IDs are automatically removed from `error_report.csv` (and the file is deleted once all errors are cleared).
- **Missing Date Fallback & Auto-Pruning**: If `script_ready` is checked but `script_date` is blank, records are saved to `undated_ready_scripts.csv` (and `undated_ready_scripts_to_work_with.csv` if requested). When dates are subsequently filled in on Google Sheets, the scanner automatically prunes resolved items from the undated files.
- **Pipeline Integration**: Apply Sheets revisions in **Sheets Sync**, then select the corresponding IDs in **Mass Creation**. You can upload a scanner export as the ID CSV and queue each required production stage in the studio.
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

### 6. Google Drive Scoped Replacement Sync (`sync_drive.py`)
- **Action**: Uploads completed `<script_id>.mp4` and/or `<script_id>_thumbnail.png` (for Spanish: both `<script_id>_thumbnail_latam.png` and `<script_id>_thumbnail_spain.png`) to Google Drive and retires old versions of the replaced assets.
- **Credential Resolution & Auto-Reauth**: Resolves credentials in strict priority order: explicit `--credentials` flag -> `GOOGLE_APPLICATION_CREDENTIALS` env var -> `main/credentials/` (`token.json` -> `service_account.json` -> `client_secret.json`). When an OAuth `token.json` is expired or revoked, `GoogleDriveClient` automatically falls back to `client_secret.json` for interactive browser re-authentication and refreshes `token.json`. See [`../credentials/README.md`](../credentials/README.md) for OAuth 2.0 Desktop App and Service Account setup instructions.
- **Drive Folder Hierarchy (`GOOGLE_DRIVE_ROOT_FOLDER_ID`)**:
  ```text
  <root_folder_id> / <language> (english|french|italian|spanish)
                     / <video_type> (expressions|fun_facts|game|role_play)
                       / <script_id> (e.g. EE01, FR21, IG09)
                         ├── <script_id>.mp4
                         └── <script_id>_thumbnail.png  (or _thumbnail_latam.png & _thumbnail_spain.png for ES)
  ```
- **Scoped Bundle Replacement (`drive_scope` = `all` | `video` | `thumbnail`)**:
  - **Local Validation**: Checks only the asset(s) required for the active `drive_scope` before calling Drive.
  - **Replacement Order**: Captures existing matching target IDs, uploads replacements, and saves links before retiring prior files for those target asset types.
  - **Permission-Safe Deletion (`delete_file`)**: Attempts permanent `files().delete()`, falls back automatically to `trashed: True` on HTTP 400/403, safely ignores HTTP 404, and evicts `_folder_cache` entries on deletion.
  - **Rollback Safety**: If a paired upload fails partway through (`all` scope), sync attempts to clean up the partial replacement and preserve the previous Drive files.
- **Usage**:
  ```powershell
  # Upload a single script bundle
  py main/connectivity/sync_drive.py --script-id EE01

  # Upload all completed scripts for a language and format
  py main/connectivity/sync_drive.py --all --language spanish --video-type game

  # Upload all completed scripts across all languages with custom credentials or root folder
  py main/connectivity/sync_drive.py --all
  py main/connectivity/sync_drive.py --script-id IG09 --credentials main/credentials/service_account.json --root-folder-id <FOLDER_ID>
  ```

---

## WebUI Google Sheets Sync Studio

In addition to CLI runners, the complete Google Sheets connectivity workflow is natively integrated into the modern browser WebUI (`py main/tools/webui.py` -> **Google Sheets Sync** tab):

- **Script Revisions Sync (`POST /api/sheets/sync`)**:
  1. **Fetch External Revisions**: Pulls Column D (`SCRIPT_CHANGED` / `SCRIPT_CHANGE`) and Column B (`EXPRESSION`) across all 16 sheets (including `FUN_FACTS`) into local CSVs.
  2. **Check & Audit Differences**: Runs `Counter`-based diffing across all 4 formats (deduplicating legacy `pressure == challenge` copies) and renders side-by-side diff previews and word count deltas.
  3. **Apply Detected Changes**: Applies script and Column B `EXPRESSION` updates cleanly (merging blank-line `GAME` `A:`/`B:`/`C:`/`D:` options into `challenge`), invalidates stale titles/anchors on topic change, and resets downstream stages to pending.
- **Thumbnail Titles Sync (`POST /api/sheets/sync-thumbnails`)**:
  - Fetches **Column J (`THUMBNAIL_TITLE`)** across all 16 sheets (`normalize_sheet_rows()` supports named headers or positional Column J fallback), updates `content_metadata.thumbnail_title`, and marks **only `thumbnail_generation` = `pending`** (leaving voice, scene images, and video assembly untouched).
- **REST Endpoints**: Powered by `main/webui/routers/sheets.py` (`/api/sheets/status`, `/api/sheets/sync`, `/api/sheets/sync-thumbnails`, `/api/sheets/reset`).

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
# 1. Sync sheet data to <OUTPUT_DIR>/connectivity\
from connectivity import sync_sheet, sync_all_sheets
sync_sheet(language="french", video_type="expression")
sync_all_sheets()

# 2. Fetch corrected scripts from Column D
from connectivity import fetch_and_save_corrected_scripts, fetch_all_sheets_corrected_scripts
fetch_and_save_corrected_scripts(language="french", video_type="expression", mode="all")
fetch_all_sheets_corrected_scripts()

# 3. Reconcile and reorganize scripts to follow Google Sheets order
from connectivity import reconcile_sheet_data, reconcile_single_sheet, reconcile_all_sheets
summary = reconcile_all_sheets()  # saves to <OUTPUT_DIR>/connectivity\scripts_to_post

# 4. Post scripts to Google Sheets (Columns A, B, C or A:D)
from connectivity import post_single_sheet, post_all_sheets
post_single_sheet(language="french", video_type="expression", mode="range", range_spec="01-20")
post_all_sheets()

# 5. Scan ready scripts and export by date
from connectivity import scan_sheet_ready_scripts, scan_all_sheets_ready_scripts, save_ready_scripts_by_date
summary = scan_all_sheets_ready_scripts()
save_ready_scripts_by_date(summary["date_groups"])  # saves to <OUTPUT_DIR>/connectivity\ready_scripts

# 6. Upload video + thumbnail bundles to Google Drive (bundle replacement)
from connectivity.drive_sync import GoogleDriveClient, upload_script_to_drive, upload_completed_scripts_to_drive
client = GoogleDriveClient()
client.authenticate()
result = upload_script_to_drive(script_id="EE01", client=client)
```

