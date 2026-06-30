// ─── 共用常數 ──────────────────────────────────────────
var CONST_KEYWORDS = "大同鄉 南澳鄉 員山鄉 烏來區 復興區 尖石鄉 五峰鄉 橫山鄉 關西鎮 泰安鄉 南庄鄉 獅潭鄉 和平區 仁愛鄉 信義鄉 魚池鄉 水里鄉 阿里山鄉 桃源區 那瑪夏區 茂林區 六龜區 獅子鄉 三地門鄉 牡丹鄉 來義鄉 泰武鄉 瑪家鄉 春日鄉 霧臺鄉 滿州鄉 車城鄉 內埔鄉 新埤鄉 秀林鄉 卓溪鄉 萬榮鄉 壽豐鄉 光復鄉 富里鄉 豐濱鄉 吉安鄉 鳳林鎮 玉里鎮 瑞穗鄉 花蓮市 新城鄉";
var CONST_VERSION = "1.0.0";

// ─── 共用通知函式 ──────────────────────────────────────
function notifyError(title, err, context) {
  var remaining = MailApp.getRemainingDailyQuota();
  if (remaining <= 0) return;

  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var cfg = ss && ss.getSheetByName("設定(驗證資訊)");

    var to = "";
    if (cfg) to = cfg.getRange("B4").getValue().toString().trim();
    if (!to) {
      try { to = Session.getActiveUser().getEmail(); } catch (e) { /**/ }
    }
    if (!to) to = "rock90340@gmail.com";

    var body = [
      "❌ " + title,
      "時間：" + new Date().toLocaleString('zh-TW', {timeZone:'Asia/Taipei'}),
      "錯誤：" + err.message,
      "上下文：" + JSON.stringify(context || {})
    ].join('\n');

    MailApp.sendEmail(to, "[法拍PRO] " + title, body);
  } catch (e) {
    Logger.log("notifyError 本身失敗: " + e.message);
  }
}
