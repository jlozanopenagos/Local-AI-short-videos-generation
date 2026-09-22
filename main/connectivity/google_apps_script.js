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
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    
    // Allow optional ?sheet=SheetName parameter, otherwise use the active/first sheet
    let sheet;
    if (e && e.parameter && e.parameter.sheet) {
      sheet = ss.getSheetByName(e.parameter.sheet);
      if (!sheet) {
        return createJsonResponse({
          status: "error",
          message: "Sheet '" + e.parameter.sheet + "' not found in spreadsheet."
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

    // Locate target columns case-insensitively
    let idColIdx = -1;
    let expressionColIdx = -1;
    let scriptChangedColIdx = -1;

    for (let i = 0; i < headers.length; i++) {
      const normalized = headers[i].toUpperCase();
      if (normalized === "ID") {
        idColIdx = i;
      } else if (normalized === "EXPRESSION") {
        expressionColIdx = i;
      } else if (normalized === "SCRIPT_CHANGED" || normalized === "SCRIPT CHANGED" || normalized === "NEW_SCRIPT") {
        scriptChangedColIdx = i;
      }
    }

    if (idColIdx === -1) {
      return createJsonResponse({
        status: "error",
        message: "Required column 'ID' was not found in sheet headers.",
        found_headers: headers
      }, 400);
    }

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
      const scriptChangedVal = scriptChangedColIdx !== -1 ? String(row[scriptChangedColIdx] || "").trim() : "";

      records.push({
        ID: idVal,
        expression: exprVal,
        SCRIPT_CHANGED: scriptChangedVal
      });
    }

    return createJsonResponse({
      status: "success",
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
