# Google Sheets Connectivity

Modular integration layer connecting Google Sheets to the `shorts_automation` pipeline using Google Apps Script Web App endpoints.

---

## Overview

Each Google Sheet (one per language and video format) exports data as a lightweight REST endpoint via **Google Apps Script**. The local pipeline fetches data from three target columns:
- **`ID`**: Canonical Script ID (e.g., `FE01`, `FR05`, `FG10`).
- **`expression`**: Target linguistic expression or idiom.
- **`SCRIPT_CHANGED`**: Raw or modified script content.

Fetched data is automatically parsed, validated, and saved to:
`D:\AI\output\connectivity\` (with automatic fallback to `OUTPUT_DIR / connectivity`).

Files generated per sync:
- `<language>_<video_type>_connectivity.csv`
- `<language>_<video_type>_connectivity.json`

---

## 1. Setting up Google Apps Script in Google Sheets

For each Google Sheet:
1. Open the Google Sheet in your browser.
2. Ensure columns `ID`, `expression`, and `SCRIPT_CHANGED` exist in row 1.
3. Click **Extensions > Apps Script**.
4. Replace the contents of `Code.gs` with the code in [`google_apps_script.js`](google_apps_script.js).
5. Click **Save** (disk icon).
6. Click **Deploy > New deployment**.
7. Under "Select type", choose **Web app**.
8. Configure:
   - **Description**: `shorts_automation connectivity`
   - **Execute as**: `Me`
   - **Who has access**: `Anyone` *(Critical: allows local scripts to fetch without OAuth)*
9. Click **Deploy** and copy the generated **Web App URL** (e.g., `https://script.google.com/macros/s/.../exec`).

---

## 2. Registering Multiple Endpoints

To register endpoints for each language and format, you can either:

### Option A: Via Environment Variables (`.env`)
```ini
SHEETS_ENDPOINT_FRENCH_EXPRESSION=https://script.google.com/macros/s/.../exec
SHEETS_ENDPOINT_FRENCH_ROLEPLAY=https://script.google.com/macros/s/.../exec
SHEETS_ENDPOINT_ENGLISH_EXPRESSION=https://script.google.com/macros/s/.../exec
SHEETS_ENDPOINT_SPANISH_EXPRESSION=https://script.google.com/macros/s/.../exec
```

### Option B: In Python Code (`endpoints.py`)
```python
from connectivity.endpoints import register_endpoint

register_endpoint("spanish", "expression", "https://script.google.com/macros/s/.../exec")
```

---

## 3. CLI Usage

```powershell
# 1. Fetch default (French Expression):
py main/connectivity/cli.py

# 2. Fetch by language and format:
py main/connectivity/cli.py --language french --video-type expression

# 3. Fetch from a custom / one-off URL:
py main/connectivity/cli.py --url "https://script.google.com/macros/s/YOUR_APPS_SCRIPT_WEBAPP_ID/exec"

# 4. List all configured endpoints:
py main/connectivity/cli.py --list
```

---

## 4. Python API Usage

```python
from connectivity.sheets_fetcher import sync_sheet

# Fetch and save automatically
result = sync_sheet(language="french", video_type="expression")
print(f"Fetched {result['count']} records.")
print(f"Saved to: {result['csv_path']}")
```
