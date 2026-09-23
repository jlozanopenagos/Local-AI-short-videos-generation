/**
 * ==============================================================================
 * Google Apps Script: Generic Web App Endpoint (Sample Model)
 * ==============================================================================
 * 
 * This is a generic sample template illustrating how to configure an Apps Script
 * Web App to read from and write to Google Sheets via JSON APIs.
 * 
 * Setup Instructions:
 * 1. Open Google Sheets -> Extensions -> Apps Script.
 * 2. Paste this code into Code.gs (and adapt to your sheet structure).
 * 3. Deploy as a Web App:
 *    - Click 'Deploy' > 'New deployment'
 *    - Select type: 'Web app'
 *    - Execute as: 'Me'
 *    - Who has access: 'Anyone'
 * 4. Copy the resulting Web App URL and add it to your .env:
 *    SHEETS_MASTER_WEBAPP_URL=https://script.google.com/macros/s/YOUR_APPS_SCRIPT_ID/exec
 * ==============================================================================
 */

/**
 * Handles HTTP GET requests to read data from Google Sheets.
 * Supports querying by spreadsheet ID (?id=...) and tab name (?sheet=...).
 */
function doGet(e) {
  try {
    const params = (e && e.parameter) ? e.parameter : {};

    // 1. Resolve spreadsheet by ID or fallback to the container spreadsheet
    const spreadsheetId = params.id || params.spreadsheet_id;
    const ss = spreadsheetId
      ? SpreadsheetApp.openById(String(spreadsheetId).trim())
      : SpreadsheetApp.getActiveSpreadsheet();

    if (!ss) {
      return createJsonResponse({ status: "error", message: "Spreadsheet not found" }, 404);
    }

    // 2. Resolve sheet tab (defaults to active sheet if omitted)
    const tabName = params.sheet || params.tab;
    const sheet = tabName ? ss.getSheetByName(String(tabName).trim()) : ss.getActiveSheet();

    if (!sheet) {
      return createJsonResponse({ status: "error", message: "Sheet tab not found" }, 404);
    }

    // 3. Read sheet data
    const data = sheet.getDataRange().getValues();
    if (!data || data.length < 2) {
      return createJsonResponse({ status: "success", count: 0, data: [] });
    }

    // 4. Map rows to JSON objects using header row (Row 1)
    const headers = data[0].map(h => String(h || "").trim());
    const records = [];

    for (let r = 1; r < data.length; r++) {
      const row = data[r];
      const record = {};
      headers.forEach((header, colIdx) => {
        if (header) {
          record[header] = row[colIdx];
        }
      });
      records.push(record);
    }

    return createJsonResponse({
      status: "success",
      count: records.length,
      data: records
    });

  } catch (err) {
    return createJsonResponse({ status: "error", message: err.toString() }, 500);
  }
}

/**
 * Handles HTTP POST requests to write or update rows in Google Sheets.
 * Supports include_script_changed (boolean) in payload to write 4 columns vs 3.
 */
function doPost(e) {
  try {
    let payload = {};
    if (e && e.postData && e.postData.contents) {
      payload = JSON.parse(e.postData.contents);
    } else if (e && e.parameter) {
      payload = e.parameter;
    }

    // 1. Resolve spreadsheet
    const spreadsheetId = payload.spreadsheet_id || payload.id;
    const ss = spreadsheetId
      ? SpreadsheetApp.openById(String(spreadsheetId).trim())
      : SpreadsheetApp.getActiveSpreadsheet();

    if (!ss) {
      return createJsonResponse({ status: "error", message: "Spreadsheet not found" }, 404);
    }

    // 2. Resolve sheet tab
    const tabName = payload.sheet || payload.tab;
    const sheet = tabName ? ss.getSheetByName(String(tabName).trim()) : ss.getActiveSheet();

    if (!sheet) {
      return createJsonResponse({ status: "error", message: "Sheet tab not found" }, 404);
    }

    // 3. Process rows (customize update/append logic to your requirements)
    const rows = Array.isArray(payload.rows) ? payload.rows : [];
    rows.forEach(item => {
      // Example: append values to the sheet
      sheet.appendRow(Object.values(item));
    });

    // Flush pending changes to prevent Google Drive redirect lock issues
    SpreadsheetApp.flush();
    Utilities.sleep(300);

    return createJsonResponse({
      status: "success",
      message: "Data processed successfully",
      count: rows.length
    });

  } catch (err) {
    return createJsonResponse({ status: "error", message: err.toString() }, 500);
  }
}

/**
 * Helper to construct JSON HTTP response.
 */
function createJsonResponse(dataObject, statusCode) {
  const output = ContentService.createTextOutput(JSON.stringify(dataObject, null, 2));
  output.setMimeType(ContentService.MimeType.JSON);
  return output;
}
