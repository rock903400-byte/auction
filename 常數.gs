// ─── 共用常數 ──────────────────────────────────────────
var CONST_KEYWORDS = "大同鄉 南澳鄉 員山鄉 烏來區 復興區 尖石鄉 五峰鄉 橫山鄉 關西鎮 泰安鄉 南庄鄉 獅潭鄉 和平區 仁愛鄉 信義鄉 魚池鄉 水里鄉 阿里山鄉 桃源區 那瑪夏區 茂林區 六龜區 獅子鄉 三地門鄉 牡丹鄉 來義鄉 泰武鄉 瑪家鄉 春日鄉 霧臺鄉 滿州鄉 車城鄉 內埔鄉 新埤鄉 秀林鄉 卓溪鄉 萬榮鄉 壽豐鄉 光復鄉 富里鄉 豐濱鄉 吉安鄉 鳳林鎮 玉里鎮 瑞穗鄉 花蓮市 新城鄉";
var CONST_VERSION = "1.1.4";

// ─── 具備指數退避重試的 UrlFetch 工具函式 ──────────────────────────
function fetchWithRetry(url, options, maxAttempts) {
  var attempts = maxAttempts || 3;
  var lastErr = null;
  for (var i = 1; i <= attempts; i++) {
    try {
      var res = UrlFetchApp.fetch(url, options);
      var code = res.getResponseCode();
      if (code >= 500 && i < attempts) {
        Logger.log("⚠️ HTTP " + code + " (第 " + i + "/" + attempts + " 次)，等待重試: " + url);
        Utilities.sleep(2000 * i);
        continue;
      }
      return res;
    } catch (e) {
      lastErr = e;
      Logger.log("⚠️ 連線失敗 (第 " + i + "/" + attempts + " 次): " + e.message);
      if (i < attempts) {
        Utilities.sleep(2000 * i);
      }
    }
  }
  throw lastErr || new Error("fetchWithRetry 失敗: " + url);
}

// ─── 共用通知函式（先落盤 錯誤日誌 Sheet，再寄信）────────────────
function notifyError(title, err, context) {
  var sheetLogged = false;
  var mailOk = false;
  var remaining = -1;
  try { remaining = MailApp.getRemainingDailyQuota(); } catch (_e) { remaining = 1; }

  // 1. 先寫 Sheet（不依賴 Mail，避免 quota 耗盡時靜默）
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sh = ss.getSheetByName("錯誤日誌") || ss.insertSheet("錯誤日誌");
    if (sh.getLastRow() === 0) {
      sh.appendRow(["時間戳", "標題", "錯誤", "context", "來源", "Mail成功", "剩餘配額"]);
      sh.getRange(1, 1, 1, 7).setFontWeight("bold").setBackground("#f3f3f3");
      sh.setColumnWidth(1, 180); sh.setColumnWidth(2, 200); sh.setColumnWidth(3, 300); sh.setColumnWidth(4, 400);
    }
    sh.appendRow([
      new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' }),
      title,
      (err && err.message) ? err.message : String(err),
      JSON.stringify(context || {}).slice(0, 4000),
      (context && context.step) ? String(context.step) : "",
      "",
      remaining
    ]);
    if (sh.getLastRow() > 1000) sh.deleteRows(2, 200);
    sheetLogged = true;
  } catch (logE) {
    Logger.log("ErrorLog 寫入失敗: " + logE.message);
  }

  // 2. 再發 Mail（保留原邏輯，但 quota 耗盡時已落盤不算丟失）
  try {
    if (remaining <= 0) {
      Logger.log("Mail quota 耗盡，已落盤至 錯誤日誌 - " + title);
      return;
    }
    var ss2 = SpreadsheetApp.getActiveSpreadsheet();
    var cfg = ss2 && ss2.getSheetByName("設定(驗證資訊)");
    var to = "";
    if (cfg) to = cfg.getRange("B4").getValue().toString().trim();
    if (!to) {
      try { to = Session.getActiveUser().getEmail(); } catch (e) { /**/ }
    }
    if (!to) to = "rock90340@gmail.com";

    var body = [
      "❌ " + title,
      "時間：" + new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' }),
      "錯誤：" + ((err && err.message) ? err.message : String(err)),
      "上下文：" + JSON.stringify(context || {})
    ].join('\n');

    MailApp.sendEmail(to, "[法拍PRO] " + title, body);
    mailOk = true;
  } catch (e) {
    Logger.log("notifyError Mail 失敗: " + e.message);
  } finally {
    try {
      var ss3 = SpreadsheetApp.getActiveSpreadsheet();
      var sh3 = ss3 && ss3.getSheetByName("錯誤日誌");
      if (sh3 && sh3.getLastRow() > 1) {
        sh3.getRange(sh3.getLastRow(), 6).setValue(mailOk ? "Y" : "N");
      }
    } catch (_e2) { /**/ }
  }

  Logger.log("notifyError 已落盤 sheetLogged=" + sheetLogged + " mailOk=" + mailOk + " title=" + title);
}
