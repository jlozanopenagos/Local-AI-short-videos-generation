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

    // Locate target columns case-insensitively (columns A, B, C, D: ID, expression, script, SCRIPT_CHANGED)
    let idColIdx = -1;
    let expressionColIdx = -1;
    let scriptColIdx = -1;
    let scriptChangedColIdx = -1;

    for (let i = 0; i < headers.length; i++) {
      const normalized = headers[i].toUpperCase();
      if (normalized === "ID") {
        idColIdx = i;
      } else if (normalized === "EXPRESSION" || normalized === "TOPIC" || normalized === "SUBJECT") {
        expressionColIdx = i;
      } else if (normalized === "SCRIPT") {
        scriptColIdx = i;
      } else if (normalized === "SCRIPT_CHANGED" || normalized === "SCRIPT CHANGED" || normalized === "NEW_SCRIPT" || normalized === "CORRECTED_SCRIPT") {
        scriptChangedColIdx = i;
      }
    }

    // Fallbacks to default columns A (0), B (1), C (2), D (3) if not matched by name
    if (idColIdx === -1 && headers.length > 0) idColIdx = 0;
    if (expressionColIdx === -1 && headers.length > 1) expressionColIdx = 1;
    if (scriptColIdx === -1 && headers.length > 2) scriptColIdx = 2;
    if (scriptChangedColIdx === -1 && headers.length > 3) scriptChangedColIdx = 3;

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
      const scriptChangedVal = scriptChangedColIdx !== -1 ? String(row[scriptChangedColIdx] || "").trim() : "";

      records.push({
        ID: idVal,
        expression: exprVal,
        script: scriptVal,
        SCRIPT_CHANGED: scriptChangedVal
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

/**
 * Handles HTTP POST requests to update scripts in Google Sheets.
 * 
 * Safety Guarantee:
 * - Affects ONLY Columns A (ID), B (expression), C (script).
 * - Column D (SCRIPT_CHANGED) and subsequent columns are NEVER touched.
 * 
 * Expected JSON payload:
 * {
 *   "spreadsheet_id": "...", // Optional if query parameter ?id=... is present
 *   "tab": "...",            // Optional tab name
 *   "rows": [
 *     { "ID": "FE01", "expression": "...", "script": "..." },
 *     ...
 *   ]
 * }
 */
function doPost(e) {
  try {
    let payload = {};
    if (e && e.postData && e.postData.contents) {
      try {
        payload = JSON.parse(e.postData.contents);
      } catch (parseErr) {
        return createJsonResponse({
          status: "error",
          message: "Invalid JSON in POST body: " + parseErr.toString()
        }, 400);
      }
    } else if (e && e.parameter) {
      payload = e.parameter;
    }

    // 1. Resolve spreadsheet by ID
    let ss;
    const targetId = payload.spreadsheet_id || payload.id || (e && e.parameter ? (e.parameter.id || e.parameter.spreadsheet_id) : null);
    if (targetId && String(targetId).trim()) {
      ss = SpreadsheetApp.openById(String(targetId).trim());
    } else {
      ss = SpreadsheetApp.getActiveSpreadsheet();
    }

    if (!ss) {
      return createJsonResponse({
        status: "error",
        message: "No spreadsheet found and no spreadsheet_id provided."
      }, 400);
    }

    // 2. Resolve sheet tab
    let sheet;
    const tabName = payload.tab || payload.sheet || (e && e.parameter ? (e.parameter.sheet || e.parameter.tab) : null);
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

    const rowsToPost = Array.isArray(payload.rows) ? payload.rows : (Array.isArray(payload.data) ? payload.data : []);
    if (rowsToPost.length === 0) {
      return createJsonResponse({
        status: "success",
        message: "No rows provided to update.",
        updated_count: 0,
        appended_count: 0,
        total_affected: 0
      });
    }

    // 3. Ensure Header Row exists in columns A-D
    const lastRow = sheet.getLastRow();
    if (lastRow === 0) {
      sheet.getRange(1, 1, 1, 4).setValues([["ID", "expression", "script", "SCRIPT_CHANGED"]]);
    } else {
      const headerRow = sheet.getRange(1, 1, 1, Math.max(sheet.getLastColumn(), 4)).getValues()[0];
      if (!headerRow[0]) sheet.getRange(1, 1).setValue("ID");
      if (!headerRow[1]) sheet.getRange(1, 2).setValue("expression");
      if (!headerRow[2]) sheet.getRange(1, 3).setValue("script");
      if (!headerRow[3]) sheet.getRange(1, 4).setValue("SCRIPT_CHANGED");
    }

    // 4. Index incoming rows by ID for fast lookup
    const incomingMap = {};
    const incomingOrder = [];

    for (let i = 0; i < rowsToPost.length; i++) {
      const item = rowsToPost[i];
      const rowId = String(item.ID || item.id || "").trim();
      if (!rowId) continue;

      const expr = String(item.expression !== undefined ? item.expression : (item.EXPRESSION || item.topic || "")).trim();
      const sc = String(item.script !== undefined ? item.script : (item.SCRIPT || "")).trim();

      incomingMap[rowId] = { expression: expr, script: sc };
      incomingOrder.push(rowId);
    }

    let updatedCount = 0;
    let appendedCount = 0;
    const currentLastRow = sheet.getLastRow();

    // 5. Update existing rows in place (affecting ONLY Columns A:C)
    if (currentLastRow > 1) {
      const rangeABC = sheet.getRange(2, 1, currentLastRow - 1, 3);
      const valuesABC = rangeABC.getValues();
      let hasChanges = false;

      for (let r = 0; r < valuesABC.length; r++) {
        const existingId = String(valuesABC[r][0] || "").trim();
        if (existingId && incomingMap.hasOwnProperty(existingId)) {
          valuesABC[r][1] = incomingMap[existingId].expression;
          valuesABC[r][2] = incomingMap[existingId].script;
          updatedCount++;
          delete incomingMap[existingId]; // Mark handled
          hasChanges = true;
        }
      }

      if (hasChanges) {
        // Write back ONLY to columns 1 to 3 (A, B, C). Column D (SCRIPT_CHANGED) is untouched!
        rangeABC.setValues(valuesABC);
      }
    }

    // 6. Append any new IDs at the bottom (affecting ONLY Columns A:C)
    const newRowsToAppend = [];
    for (let j = 0; j < incomingOrder.length; j++) {
      const idKey = incomingOrder[j];
      if (incomingMap.hasOwnProperty(idKey)) {
        newRowsToAppend.push([idKey, incomingMap[idKey].expression, incomingMap[idKey].script]);
        delete incomingMap[idKey];
      }
    }

    if (newRowsToAppend.length > 0) {
      const appendStartRow = sheet.getLastRow() + 1;
      sheet.getRange(appendStartRow, 1, newRowsToAppend.length, 3).setValues(newRowsToAppend);
      appendedCount = newRowsToAppend.length;
    }

    return createJsonResponse({
      status: "success",
      spreadsheet_name: ss ? ss.getName() : "Unknown",
      sheet_name: sheet.getName(),
      updated_count: updatedCount,
      appended_count: appendedCount,
      total_affected: updatedCount + appendedCount,
      timestamp: new Date().toISOString()
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
