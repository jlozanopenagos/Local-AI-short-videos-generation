# Google Apps Script Deployment

This folder contains the Apps Script code required to deploy the Google Sheets Web App endpoint (Option A Master Router).

## Files:
- **`google_apps_script.sample.js`**: Canonical sample template tracked in git.
- **`google_apps_script.js`**: Standalone Web App deployment for `shorts_automation` (ignored in git to protect private sheet IDs). `doGet()` reads Columns A through J (`ID`, `expression`, `script`, `SCRIPT_CHANGED`, `script_ready`, `script_date`, `video_ready`, `video_date`, `short_description`, and `short_title` / `THUMBNAIL_TITLE` in Column J); `doPost()` supports `action: "update_scripts"` for Columns A:C or A:D only.

## Deployment Instructions:
1. Open [script.google.com](https://script.google.com/) (or your dedicated `shorts_automation_api` Apps Script project — keep it separate from `GoogleSheet_UI_auditor`).
2. Open `Code.gs` and paste the complete contents of `google_apps_script.js` (or `google_apps_script.sample.js`).
3. Click **Save** (💾).
4. Click **Deploy > Manage deployments** -> click the **pencil icon** (Edit) on the active Web App deployment.
5. Under **Version**, select **New version** and click **Deploy** so Column J (`short_title`) is returned by `doGet()`.
