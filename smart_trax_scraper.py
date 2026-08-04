function syncImportedDataToSheet2() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // Sheet 1 (Raw Data) සහ Sheet 2 (Dashboard Sheet)
  var rawSheet = ss.getSheetByName("QAT Raw Data") || ss.getSheets()[0];
  var dashSheet = ss.getSheetByName("Sheet2") || ss.getSheets()[1];
  
  var rawData = rawSheet.getDataRange().getValues();
  if (rawData.length <= 1) return; // Data නැත්නම් return වෙයි
  
  var dashData = dashSheet.getDataRange().getValues();
  
  // Dashboard එකේ දැනට තියෙන Unique Task IDs / Row Identifiers එකතු කරගැනීම
  var existingKeys = new Set();
  for (var i = 1; i < dashData.length; i++) {
    // Column G (Index 6) Task ID එක ලෙසත්, Column A + B (Index 0,1) Compound Key ලෙසත් ගනී
    var primaryKey = dashData[i][6] ? dashData[i][6].toString().trim() : "";
    var fallbackKey = (dashData[i][0] + "_" + dashData[i][1] + "_" + dashData[i][5]).toString().trim();
    
    if (primaryKey !== "") existingKeys.add(primaryKey);
    existingKeys.add(fallbackKey);
  }
  
  var newRowsToAppend = [];
  
  // Dynamic Sync Engine: Raw Data එකේ සියලුම පේළි පරීක්ෂා කිරීම
  for (var r = 1; r < rawData.length; r++) {
    var rawRow = rawData[r];
    
    // Row එක හිස්දැයි පරීක්ෂා කිරීම
    if (!rawRow.join("").trim()) continue;
    
    var rawTaskId = rawRow[6] ? rawRow[6].toString().trim() : "";
    var rawFallbackKey = (rawRow[0] + "_" + rawRow[1] + "_" + rawRow[5]).toString().trim();
    
    // අලුත් Task / අලුත් User කෙනෙක් නම් Dashboard එකට Append කරයි
    var isDuplicate = false;
    if (rawTaskId !== "" && existingKeys.has(rawTaskId)) isDuplicate = true;
    if (existingKeys.has(rawFallbackKey)) isDuplicate = true;
    
    if (!isDuplicate) {
      newRowsToAppend.push(rawRow);
      if (rawTaskId !== "") existingKeys.add(rawTaskId);
      existingKeys.add(rawFallbackKey);
    }
  }
  
  // අලුත් Records ඇත්නම් Sheet2 එකට Auto Append කිරීම
  if (newRowsToAppend.length > 0) {
    dashSheet.getRange(dashSheet.getLastRow() + 1, 1, newRowsToAppend.length, newRowsToAppend[0].length).setValues(newRowsToAppend);
    Logger.log("✅ Successfully synced " + newRowsToAppend.length + " new dynamic records to Dashboard!");
  } else {
    Logger.log("ℹ️ All dynamic records are already up-to-date.");
  }
}
