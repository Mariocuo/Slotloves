// Google Apps Script per SlotLove
function doPost(e) {
  try {
    // Ottieni i dati dalla richiesta
    const data = JSON.parse(e.postData.contents);
    
    // Ottieni il foglio attivo
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    
    // Prepara i dati da inserire
    const rowData = [
      new Date(), // Timestamp
      data.category || '',
      data.code || '',
      data.label || '',
      data.feedback || '',
      data.combination || ''
    ];
    
    // Inserisci la riga
    sheet.appendRow(rowData);
    
    // Restituisci successo
    return ContentService
      .createTextOutput(JSON.stringify({ success: true }))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    // Restituisci errore
    return ContentService
      .createTextOutput(JSON.stringify({ 
        success: false, 
        error: error.toString() 
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService
    .createTextOutput("SlotLove API is running!")
    .setMimeType(ContentService.MimeType.TEXT);
} 