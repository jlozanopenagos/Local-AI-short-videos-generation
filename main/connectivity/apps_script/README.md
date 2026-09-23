# Google Apps Script Deployment

This folder contains the Apps Script code required to deploy the Google Sheets Web App endpoint (Option A Master Router).

## Files:
- **`google_apps_script.sample.js`**: Canonical sample template tracked in git.
- **`google_apps_script.js`**: Local deployment file with configured spreadsheet IDs (ignored in git to protect private sheet IDs).

## Deployment Instructions:
1. Open your master Google Sheet.
2. Go to **Extensions > Apps Script**.
3. Replace the contents of `Code.gs` with the complete code from `google_apps_script.sample.js` (or `google_apps_script.js`).
4. Click **Save** (💾).
5. Click **Deploy > Manage deployments**.
6. Click the **pencil icon** (Edit) on the active deployment.
7. Under **Version**, select **New version**.
8. Click **Deploy**.
