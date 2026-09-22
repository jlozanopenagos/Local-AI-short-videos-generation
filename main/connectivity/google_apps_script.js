/**
 * ==============================================================================
 * Google Apps Script: Sheet-to-JSON Exporter for shorts_automation
 * ==============================================================================
 * Instructions for Google Sheets:
 * 1. Open your Google Sheet.
 * 2. Click: Extensions > Apps Script.
 * 3. Delete any code in Code.gs and paste this entire file.
 * 4. Click 'Save' (disk icon).
 * 5. Click 'Deploy' > 'New deployment'.
 * 6. Select type: 'Web app'.
 * 7. Set:
 *    - Description: shorts_automation connectivity
 *    - Execute as: 'Me' (your account)
 *    - Who has access: 'Anyone' (IMPORTANT: allows local pipeline to read data)
 * 8. Click 'Deploy' and copy the resulting Web App URL:
 *    (e.g., https://script.google.com/macros/s/.../exec)
 * ==============================================================================
 */

function doGet(e) {
  try {
    let ss;

    // 1. Open specific spreadsheet by ID if passed (?id=... or ?spreadsheet_id=...),
    //    otherwise default to the active/container spreadsheet.
    const targetId = (e && e.parameter) ? (e.parameter.id || e.parameter.spreadsheet_id || e.parameter.sheet_id) : null;
    if (targetId && String(targetId).trim()) {
      ss = SpreadsheetApp.openById(String(targetId).trim());
    } else {
      ss = SpreadsheetApp.getActiveSpreadsheet();
    }

    // 2. Allow optional ?sheet= or ?tab= parameter, otherwise use active/first tab
    let sheet;
    const tabName = (e && e.parameter) ? (e.parameter.sheet || e.parameter.tab) : null;
    if (tabName && String(tabName).trim()) {
      sheet = ss.getSheetByName(String(tabName).trim());
      if (!sheet) {
        return createJsonResponse({
          status: "error",
          message: "Sheet tab '" + tabName + "' not found in spreadsheet: " + ss.getName()
        }, 404);
      }
    } else {
      sheet = ss.getActiveSheet() || ss.getSheets()[0];
    }

    const data = sheet.getDataRange().getValues();
    if (!data || data.length < 1) {
      return createJsonResponse({
        status: "success",
        count: 0,
        sheet_name: sheet.getName(),
        data: []
      });
    }

    // Header row (Row 1)
    const rawHeaders = data[0];
    const headers = rawHeaders.map(h => String(h || "").trim());

    // Locate target columns case-insensitively (columns A, B, C: ID, expression, script)
    let idColIdx = -1;
    let expressionColIdx = -1;
    let scriptColIdx = -1;

    for (let i = 0; i < headers.length; i++) {
      const normalized = headers[i].toUpperCase();
      if (normalized === "ID") {
        idColIdx = i;
      } else if (normalized === "EXPRESSION" || normalized === "TOPIC" || normalized === "SUBJECT") {
        expressionColIdx = i;
      } else if (normalized === "SCRIPT" || normalized === "SCRIPT_CHANGED" || normalized === "NEW_SCRIPT") {
        scriptColIdx = i;
      }
    }

    // Fallbacks to default columns A (0), B (1), C (2) if not matched by name
    if (idColIdx === -1 && headers.length > 0) idColIdx = 0;
    if (expressionColIdx === -1 && headers.length > 1) expressionColIdx = 1;
    if (scriptColIdx === -1 && headers.length > 2) scriptColIdx = 2;

    const records = [];

    // Extract rows
    for (let r = 1; r < data.length; r++) {
      const row = data[r];
      const idVal = String(row[idColIdx] || "").trim();
      
      // Skip rows with no ID
      if (!idVal) {
        continue;
      }

      const exprVal = expressionColIdx !== -1 ? String(row[expressionColIdx] || "").trim() : "";
      const scriptVal = scriptColIdx !== -1 ? String(row[scriptColIdx] || "").trim() : "";

      records.push({
        ID: idVal,
        expression: exprVal,
        script: scriptVal
      });
    }

    return createJsonResponse({
      status: "success",
      spreadsheet_name: ss ? ss.getName() : "Unknown",
      sheet_name: sheet.getName(),
      count: records.length,
      timestamp: new Date().toISOString(),
      data: records
    });

  } catch (error) {
    return createJsonResponse({
      status: "error",
      message: error.toString(),
      stack: error.stack
    }, 500);
  }
}

function createJsonResponse(dataObject, statusCode) {
  const output = ContentService.createTextOutput(JSON.stringify(dataObject, null, 2));
  output.setMimeType(ContentService.MimeType.JSON);
  return output;
}
