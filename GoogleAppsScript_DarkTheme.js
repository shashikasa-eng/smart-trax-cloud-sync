/**
 * Google Apps Script - Apply Dark Theme & Conditional Formatting
 * Automatically formats the Sheet into a Dark Theme every time data updates.
 */
function applyDarkThemeFormat() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("QAT Raw Data");
  if (!sheet) return;

  var lastRow = sheet.getLastRow();
  var lastCol = sheet.getLastColumn();
  if (lastRow < 1) return;

  // 1. Header Styling (Midnight Navy / Slate)
  var headerRange = sheet.getRange(1, 1, 1, lastCol);
  headerRange.setBackground("#0B132B")
             .setFontColor("#FFFFFF")
             .setFontWeight("bold")
             .setFontFamily("Segoe UI")
             .setHorizontalAlignment("center");

  // 2. Data Rows Dark Background & Zebra Striping
  if (lastRow > 1) {
    var dataRange = sheet.getRange(2, 1, lastRow - 1, lastCol);
    dataRange.setFontFamily("Segoe UI")
             .setFontColor("#E2E8F0");
             
    for (var r = 2; r <= lastRow; r++) {
      var rowRange = sheet.getRange(r, 1, 1, lastCol);
      if (r % 2 === 0) {
        rowRange.setBackground("#1E293B"); // Dark Card
      } else {
        rowRange.setBackground("#172033"); // Dark Alt Row
      }
    }
  }

  // 3. Status Column Formatting (Column I - QAT Status)
  var statusRange = sheet.getRange(2, 9, Math.max(lastRow - 1, 1), 1);
  var values = statusRange.getValues();
  
  for (var i = 0; i < values.length; i++) {
    var cell = statusRange.getCell(i + 1, 1);
    var val = String(values[i][0]).toLowerCase().trim();
    
    if (val === "online") {
      cell.setBackground("#064E3B").setFontColor("#34D399").setFontWeight("bold");
    } else if (val === "idle") {
      cell.setBackground("#78350F").setFontColor("#FBBF24").setFontWeight("bold");
    } else if (val === "break") {
      cell.setBackground("#7F1D1D").setFontColor("#F87171").setFontWeight("bold");
    }
  }
}
