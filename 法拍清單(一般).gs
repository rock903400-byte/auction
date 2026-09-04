/**
 * 自動初始化與更新司法院法拍系統的 Session 資訊
 * 包含 Cookie, CSRF Token 與 API Token
 */
function refreshSession() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const configSheetName = "設定(驗證資訊)";
  let configSheet = ss.getSheetByName(configSheetName);
  
  // 1. 確保設定工作表存在
  if (!configSheet) {
    configSheet = ss.insertSheet(configSheetName);
    configSheet.getRange("A1:A3").setValues([["Cookie"], ["CSRF"], ["Token"]]);
    configSheet.getRange("A1:A3").setFontWeight("bold").setBackground("#f3f3f3");
    configSheet.setColumnWidth(1, 100);
    configSheet.setColumnWidth(2, 500);
  }

  // 確保通知信箱設定存在
  if (!configSheet.getRange("A4").getValue()) {
    configSheet.getRange("A4:B4").setValues([["通知信箱", "rock90340@gmail.com"]]);
    configSheet.getRange("A4").setFontWeight("bold").setBackground("#f3f3f3");
  }

  Logger.log("🔄 正在嘗試從司法院網站獲取最新憑證...");

  try {
    const url = "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/V2.htm";
    const options = {
      "method": "get",
      "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
      },
      "muteHttpExceptions": true
    };

    const response = UrlFetchApp.fetch(url, options);
    const content = response.getContentText();
    const headers = response.getAllHeaders();

    // 2. 獲取 Cookie (處理 Set-Cookie 陣列或字串)
    let cookie = "";
    const setCookie = headers["Set-Cookie"];
    if (setCookie) {
      if (Array.isArray(setCookie)) {
        cookie = setCookie.map(c => c.split(';')[0]).join('; ');
      } else {
        cookie = setCookie.split(';')[0];
      }
    }

    // 3. 獲取 CSRF Token
    // <input type="hidden" name="_csrf" value="xxxx-xxxx-xxxx" />
    const csrfMatch = content.match(/name="_csrf"\s+value="([^"]+)"/);
    const csrf = csrfMatch ? csrfMatch[1] : "";

    // 4. 獲取 Token (通常在 JavaScript 變數中)
    // var token = 'xxxxxx'; 或 similar
    const tokenMatch = content.match(/var\s+token\s*=\s*['"]([^'"]+)['"]/i) || 
                       content.match(/name="token"\s+value="([^"]+)"/);
    const token = tokenMatch ? tokenMatch[1] : "";

    if (csrf && token) {
      configSheet.getRange("B1").setValue(cookie || configSheet.getRange("B1").getValue()); // 如果沒抓到新 Cookie 則保留舊的
      configSheet.getRange("B2").setValue(csrf);
      configSheet.getRange("B3").setValue(token);
      
      Logger.log("✅ 憑證更新成功！");
      Logger.log("CSRF: " + csrf);
      Logger.log("Token: " + token);
      return true;
    } else {
      Logger.log("❌ 無法解析憑證。可能是頁面結構改變或被阻擋。");
      return false;
    }

  } catch (e) {
    Logger.log("❌ 獲取憑證時發生錯誤: " + e.message);
    notifyError("Session 更新失敗", e, {step: "refreshSession"});
    return false;
  }
}

/**
 * 一般清單抓取邏輯
 * 針對一般程序 (第一、二、三拍) 進行抓取，具備自動分頁功能
 */
function scrapeLandStableBatch_General() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const configSheetName = "設定(驗證資訊)";
  const configSheet = ss.getSheetByName(configSheetName);
  
  if (!configSheet) return;

  const cookieVal = configSheet.getRange("B1").getValue().toString().trim();
  const csrfVal = configSheet.getRange("B2").getValue().toString().trim();
  const tokenVal = configSheet.getRange("B3").getValue().toString().trim();

  const targetSheetName = "法拍清單(一般)";
  let sheet = ss.getSheetByName(targetSheetName);
  if (!sheet) { sheet = ss.insertSheet(targetSheetName); }

  const headers = [
    "筆次", "法院名稱", "案號", "股別", "拍賣日期", "拍次",
    "縣市", "土地坐落", "面積", "總拍賣底價(元)",
    "點交", "空地", "標別", "看圖", "備註",
    "採通訊投標", "土地有無遭受污染", "地圖",
    "", "土地單價(元/㎡)",
    "預估補償金", "ROI (%)", "PDF 連結", "是否點交", "是否空地"
  ];

  function getSafeNum(val) {
    if (val == null || val === '') return 0;
    const n = parseFloat(String(val).replace(/,/g, ''));
    return (!isFinite(n) || isNaN(n)) ? 0 : Math.floor(n);
  }

  try {
    const url = "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/QUERY.htm";
    // 🔴 修正：根據使用者資料，精確設定 40 個鄉鎮市關鍵字
    var searchKeywords = CONST_KEYWORDS;

    let allFetchedData = [];
    let currentPage = 1;
    let totalRecords = 0;
    const pageSize = 100;

    // 取得今日民國日期 (格式: 01150503)
    const now = new Date();
    const rocYear = now.getFullYear() - 1911;
    const rocMonth = (now.getMonth() + 1).toString().padStart(2, '0');
    const rocDay = now.getDate().toString().padStart(2, '0');
    const todayROC = "0" + rocYear + rocMonth + rocDay;

    const __loopStart = Date.now();
    // 🔴 循環抓取分頁（含超時保護，避免 6 分鐘硬砍）
    do {
      if (Date.now() - __loopStart > 4.5 * 60 * 1000) {
        Logger.log("⏰ 一般分頁已超 4.5 分鐘，提前中止，已抓 " + allFetchedData.length + "/" + totalRecords);
        break;
      }
      Logger.log("📄 正在抓取第 " + currentPage + " 頁...");
      const payload = {
        "proptype": "C51",
        "saletype": "1", 
        "keyword": searchKeywords,
        "rrange": "ALL",
        "pageSize": pageSize.toString(),
        "page": currentPage.toString(),
        "token": tokenVal,
        "_csrf": csrfVal,
        "sorted_column": "A.CRMYY, A.CRMID, A.CRMNO, A.SALENO, A.ROWID",
        "sorted_type": "ASC",
        "is_search": "Y"
      };

      const options = {
        "method": "post",
        "headers": {
          "Cookie": cookieVal,
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          "Referer": "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/V2.htm",
          "X-Requested-With": "XMLHttpRequest"
        },
        "payload": payload,
        "muteHttpExceptions": true
      };

      const response = UrlFetchApp.fetch(url, options);
      const content = response.getContentText();
      const json = JSON.parse(content);

      if (json && json.data) {
        allFetchedData = allFetchedData.concat(json.data);
        totalRecords = parseInt(json.total || 0, 10);
        Logger.log("✅ 第 " + currentPage + " 頁抓取完成，累計: " + allFetchedData.length + "/" + totalRecords);
        
        if (json.data.length < pageSize) break; 
      } else {
        break;
      }

      currentPage++;
      Utilities.sleep(500); 
    } while (allFetchedData.length < totalRecords);

    if (allFetchedData.length > 0) {
      const uniqueData = new Map();

      allFetchedData.forEach(item => {
        // 過濾權利範圍：僅保留全部
        const share = (item.rrange || "").trim();
        if (share !== "全部") return;

        const saleDate = String(item.saledate || "0").padStart(8, '0');
        if (saleDate < todayROC) return;

        // 🔴 修正：使用更細緻的 Key (包含土地座落)，確保每一筆土地都保留
        const uniqueKey = item.hsimun + item.crmyy + item.crmid + item.crmno + (item.saleno || "") + (item.batchno || "") + (item.sec || "") + (item.landno || "");
        
        if (!uniqueData.has(uniqueKey)) {
          uniqueData.set(uniqueKey, item);
        }
      });

      const filteredData = Array.from(uniqueData.values());
      Logger.log("🧹 篩選後總筆數: " + filteredData.length + " 筆");

      // 拍次映射表
      const saleTypeMap = {
        "1": "第一拍",
        "2": "第二拍",
        "3": "第三拍",
        "4": "第四拍",
        "5": "第五拍",
        "6": "第六拍",
        "7": "第七拍",
        "8": "第八拍",
        "9": "第九拍",
        "99": "公告"
      };

      let allRows = filteredData.map((item, index) => {
        const totalSum = getSafeNum(item.summinprc);
        let individualPrice = getSafeNum(item.minprice) || getSafeNum(item.minprc) || totalSum;
        let _rawArea = parseFloat(item.area3);
        if (!isFinite(_rawArea) || _rawArea < 0) _rawArea = 0;
        const areaM2 = _rawArea;
        const areaTsubo = Math.round(areaM2 * 0.3025);
        const areaDisplay = areaTsubo + "坪(" + areaM2.toFixed(2) + "平方公尺) x " + (item.rrange || "全部") + "\n底價: " + individualPrice.toLocaleString() + " 元";
        let unitPriceDisplay = (areaM2 > 0 && individualPrice > 0) ? parseFloat((individualPrice / areaM2).toFixed(2)) : 0;
        const fullLocation = item.ctmd + (item.sec || "") + "段 " + (item.subsec || "小段 ") + (item.landno || "") + "號";
        const mapAddr = item.hsimun + item.ctmd + (item.sec || "") + "段" + (item.landno || "");
        const mapUrl = "https://www.google.com/maps/search/" + encodeURIComponent(mapAddr);
        const pdfUrl = item.filenm ? "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/DO_VIEWPDF.htm?filenm=" + item.filenm : "";
        const comp = Math.ceil(areaM2 * 6);
        const roi = totalSum > 0 ? parseFloat((comp / totalSum * 100).toFixed(2)) : 0;

        return [
          index + 1, item.hsimun + "地方法院", item.crmyy + "年" + item.crmid + "字第" + item.crmno + "號",
          "(" + (item.dpt || "") + "股)", item.saledate,
          saleTypeMap[item.saleno] || "一般程序",
          item.hsimun,
          '=HYPERLINK("' + mapUrl + '", "' + fullLocation + '")',
          areaDisplay, totalSum,
          item.checkyn === "Y" ? "點交" : "不點交", item.emptyyn === "Y" ? "是" : "否",
          item.batchno || "",
          pdfUrl ? '=HYPERLINK("' + pdfUrl + '", "查詢")' : "無檔",
          item.ttitle || "", item.comm_yn === "Y" ? "是" : "否", "無資訊", '=HYPERLINK("' + mapUrl + '", "查詢")',
          "", unitPriceDisplay,
          comp, roi, pdfUrl, item.checkyn === "Y" ? "是" : "否", item.emptyyn === "Y" ? "是" : "否"
        ];
      });

      if (allRows.length > 0) {
        sheet.clear();
        sheet.appendRow(headers);
        sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold").setBackground("#2d6a4f").setFontColor("white");
        sheet.getRange(1, 20).setBackground("#d9ead3").setFontColor("black");
        sheet.getRange(1, 21, 1, 5).setBackground("#fff2cc").setFontColor("black");
        sheet.getRange(2, 1, allRows.length, allRows[0].length).setValues(allRows);
        sheet.getRange(2, 9, allRows.length, 1).setWrap(true);
        sheet.getRange(2, 20, allRows.length, 1).setNumberFormat("#,##0.00");
        sheet.getRange(2, 21, allRows.length, 1).setNumberFormat("#,##0");
        sheet.getRange(2, 22, allRows.length, 1).setNumberFormat("0.00");
        sheet.autoResizeColumns(1, 25);
        Logger.log("🎯 【一般】清單更新完畢！");
        // Write-through：寫表成功立刻預熱快取，前端 doGet 直接命中、不必讀表
        if (typeof warmCacheTab === 'function') {
          try { warmCacheTab('general'); } catch (_e) { Logger.log("快取預熱略過: " + _e.message); }
        }
      } else {
        notifyError("一般篩選後為0筆", new Error("filteredData empty"), {step: "scrapeGeneral", raw: allFetchedData.length, filtered: filteredData.length});
      }
    } else {
      notifyError("一般API回傳0筆", new Error("allFetchedData empty"), {step: "scrapeGeneral"});
    }
  } catch (e) {
    Logger.log("❌ 執行一般清單錯誤: " + e.message);
    notifyError("一般清單抓取失敗", e, {step: "scrapeGeneral"});
  }
}

/**
 * 自動建立並初始化【會員名單】工作表
 */
function initMembershipSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetName = "會員名單";
  let sheet = ss.getSheetByName(sheetName);

  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
    sheet.getRange("A1:B1").setValues([["Email", "權限等級"]]);
    sheet.getRange("A1:B1").setFontWeight("bold").setBackground("#f3f3f3");
    sheet.setColumnWidth(1, 250);
    sheet.setColumnWidth(2, 150);

    let currentUserEmail = "";
    try {
      currentUserEmail = Session.getActiveUser().getEmail();
    } catch(e) {
      Logger.log("⚠️ 無法透過 Session 獲取 Email，請手動在會員名單 A2 填寫。");
    }

    if (currentUserEmail) {
      sheet.getRange("A2:B2").setValues([[currentUserEmail, "pro"]]);
      Logger.log("✅ 成功自動建立【會員名單】工作表，並已將您 (" + currentUserEmail + ") 設為 pro 權限！");
    } else {
      sheet.getRange("A2").setValue("請手動填寫您的 Email");
      sheet.getRange("B2").setValue("pro");
    }
  }
}

/**
 * 一鍵更新入口（含 5 分鐘超時保護 + LockService，避免併發清空試算表）
 */
function runAllUpdate() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    Logger.log("⚠️ runAllUpdate 取得鎖失敗，另有任務執行中，跳過");
    return;
  }
  try {
    const startTime = Date.now();
    function checkTimeout(step) {
      if (Date.now() - startTime > 5 * 60 * 1000) {
        notifyError("runAllUpdate 超時", new Error("執行超過 5 分鐘，提前中止"), {step: step, elapsed: Date.now() - startTime});
        Logger.log("⏰ " + step + " 階段超過 5 分鐘，提前中止");
        return true;
      }
      return false;
    }

    initMembershipSheet();
    if (checkTimeout("initMembershipSheet")) return;
    if (refreshSession()) {
      Logger.log("🚀 憑證已更新，開始完整抓取...");
      if (checkTimeout("refreshSession")) return;
      scrapeLandStableBatch_General();
      if (checkTimeout("scrapeGeneral")) return;
      if (typeof scrapeLandStableBatch_Buy === 'function') {
        scrapeLandStableBatch_Buy();
        if (checkTimeout("scrapeBuy")) return;
      }
      // 收尾：統一預熱快取（各爬蟲已預熱各自頁籤，此處確保 updatedAt 一致）
      if (typeof warmCache === 'function') {
        try { warmCache(); } catch (_e) { Logger.log("快取預熱略過: " + _e.message); }
      }
      Logger.log("✨ 所有清單更新完成！");
    } else {
      notifyError("refreshSession 失敗", new Error("runAllUpdate 無法取得憑證"), {step: "runAllUpdate"});
    }
  } finally {
    lock.releaseLock();
  }
}

// ─── Debug: 逐層計算過濾筆數 ─────────────────────────────────────────────────
function debugFilterCounts(saletypeOverride) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const configSheet = ss.getSheetByName("設定(驗證資訊)");
  if (!configSheet) { Logger.log("找不到設定表"); return; }

  const cookie = configSheet.getRange("B1").getValue().toString().trim();
  const csrf = configSheet.getRange("B2").getValue().toString().trim();
  const token = configSheet.getRange("B3").getValue().toString().trim();

  const url = "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/QUERY.htm";
  const allResults = [];
  var page = 1;
  const pageSize = 100;
  var totalRecords = 0;
  var saletypeVal = saletypeOverride || "1";

  do {
    try {
      var payload = {
        proptype: "C51", saletype: saletypeVal, keyword: CONST_KEYWORDS,
        rrange: "ALL", pageSize: String(pageSize), page: String(page),
        token: token, _csrf: csrf,
        sorted_column: "A.CRMYY, A.CRMID, A.CRMNO, A.SALENO, A.ROWID",
        sorted_type: "ASC", is_search: "Y"
      };
      var response = UrlFetchApp.fetch(url, {
        muteHttpExceptions: true,
        method: "post",
        headers: {
          Cookie: cookie,
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          "Referer": "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/V2.htm",
          "X-Requested-With": "XMLHttpRequest"
        },
        payload: payload
      });
      var content = response.getContentText();
      var json = JSON.parse(content);
      if (json && json.data) {
        for (var j = 0; j < json.data.length; j++) {
          allResults.push(json.data[j]);
        }
        if (page === 1) totalRecords = parseInt(json.total || 0, 10);
        Logger.log("Page " + page + ": " + json.data.length + " (累計 " + allResults.length + "/" + totalRecords + ")");
        if (json.data.length < pageSize) break;
      } else { break; }
    } catch (fetchErr) {
      Logger.log("Page " + page + " 錯誤: " + fetchErr.message);
      break;
    }
    page++;
    Utilities.sleep(300);
  } while (allResults.length < totalRecords);

  Logger.log("===== 原始筆數 =====");
  Logger.log("總計: " + allResults.length);
  if (allResults.length === 0) { Logger.log("可能原因: Cookie/CSRF/Token 過期或司法院網站改版"); }

  const now = new Date();
  var rocYear = (now.getFullYear() - 1911).toString();
  var mm = (now.getMonth()+1).toString().padStart(2,'0');
  var dd = now.getDate().toString().padStart(2,'0');
  var todayROC = "0" + rocYear + mm + dd;
  var isGeneral = (saletypeVal === "1");

  var cnt_share = 0;
  var cnt_share_full = 0, cnt_share_1of1 = 0, cnt_share_empty = 0, cnt_share_other_r = 0;
  var cnt_saleno_123 = 0, cnt_saleno_4 = 0, cnt_saleno_56 = 0, cnt_saleno_99 = 0;
  var cnt_saleno_12346 = 0;
  var cnt_date = 0, cnt_dedup = 0;
  var dedupSet = {};
  var saletitleDist = {};

  if (allResults.length > 0) {
    Logger.log("===== 第1筆原始資料欄位 =====");
    var first = allResults[0];
    for (var key in first) {
      Logger.log("  " + key + "=" + first[key]);
    }
  }
  var firstFields = allResults.length > 0 ? Object.keys(allResults[0]) : [];
  var paraBySaleno = {};
  for (var si = 0; si < allResults.length; si++) {
    var sr = allResults[si];
    var s = String(sr.saleno || "");
    if (!paraBySaleno[s]) paraBySaleno[s] = {};
    var paraPrefix = (sr.para || "").split("|")[0];
    if (!paraBySaleno[s][paraPrefix]) paraBySaleno[s][paraPrefix] = 0;
    paraBySaleno[s][paraPrefix]++;
  }
  var cnt_saleno_5 = 0, cnt_saleno_6 = 0, cnt_saleno_7 = 0, cnt_saleno_8 = 0, cnt_saleno_9 = 0;
  var cnt_saleno_other = 0;

  for (var i = 0; i < allResults.length; i++) {
    var item = allResults[i];
    var share = (item.rrange || "").trim();
    if (share === "全部") cnt_share_full++;
    else if (share === "1分之1") cnt_share_1of1++;
    else if (share === "") cnt_share_empty++;
    else cnt_share_other_r++;
    if (share !== "全部") continue;
    cnt_share++;

    var saleno = String(item.saleno || "");
    if (saleno === "1" || saleno === "2" || saleno === "3") cnt_saleno_123++;
    else if (saleno === "4") cnt_saleno_4++;
    else if (saleno === "5") cnt_saleno_5++;
    else if (saleno === "6") cnt_saleno_6++;
    else if (saleno === "7") cnt_saleno_7++;
    else if (saleno === "8") cnt_saleno_8++;
    else if (saleno === "9") cnt_saleno_9++;
    else if (saleno === "99") cnt_saleno_99++;
    else cnt_saleno_other++;

    var st = (item.saletitle || "").trim() || "(空白)";
    if (!saletitleDist[st]) saletitleDist[st] = 0;
    saletitleDist[st]++;

    // 內部小圈修正：saletype=4 應買無 saleno/日期過濾，僅 share=全部→去重
    if (isGeneral) {
      if (saleno !== "1" && saleno !== "2" && saleno !== "3" && saleno !== "4" && saleno !== "6") continue;
      cnt_saleno_12346++;

      var saleDate = String(item.saledate || "0").padStart(8,'0');
      if (saleDate < todayROC) continue;
      cnt_date++;
    } else {
      // 應買：跳過 saleno/日期，對齊 法拍清單(應買).gs:107 的真實邏輯
      cnt_saleno_12346 = cnt_share; // 佔位，避免 removed_by_saleno 誤導
      cnt_date = cnt_share;
    }

    var key = item.hsimun + item.crmyy + item.crmid + item.crmno + (item.saleno||"") + (item.batchno||"") + (item.sec||"") + (item.landno||"");
    if (!dedupSet[key]) { dedupSet[key] = true; cnt_dedup++; }
  }

  Logger.log("===== 原始 API 總計 =====");
  Logger.log("總筆數: " + allResults.length);
  Logger.log("===== 權利範圍分布 (全部原始) =====");
  Logger.log("全部: " + cnt_share_full + " | 1分之1: " + cnt_share_1of1 + " | 空白: " + cnt_share_empty + " | 其他: " + cnt_share_other_r);
  Logger.log("===== 篩選 權利範圍=全部 =====");
  Logger.log("通過: " + cnt_share + " (移除: " + (allResults.length-cnt_share) + ")");
  Logger.log("===== 各拍次分布 =====");
  Logger.log("1/2/3 拍: " + cnt_saleno_123);
  Logger.log("4: " + cnt_saleno_4);
  Logger.log("5: " + cnt_saleno_5);
  Logger.log("6: " + cnt_saleno_6);
  Logger.log("7: " + cnt_saleno_7);
  Logger.log("8: " + cnt_saleno_8);
  Logger.log("9: " + cnt_saleno_9);
  Logger.log("99 (公告): " + cnt_saleno_99);
  Logger.log("其他: " + cnt_saleno_other);
  Logger.log("===== saletitle 分布 =====");
  for (var st in saletitleDist) {
    Logger.log("  " + st + ": " + saletitleDist[st]);
  }
  if (isGeneral) {
    Logger.log("===== 篩選 拍次 1/2/3/4/6 =====");
    Logger.log("通過: " + cnt_saleno_12346 + " (移除: " + (cnt_share-cnt_saleno_12346) + ")");
    Logger.log("===== 過濾過期 (today=" + todayROC + ") =====");
    Logger.log("通過: " + cnt_date + " (移除: " + (cnt_saleno_12346-cnt_date) + ")");
  } else {
    Logger.log("===== 跳過 拍次/日期 (saletype=" + saletypeVal + " 應買無此過濾) =====");
  }
  Logger.log("===== 去重後 =====");
  if (isGeneral) {
    Logger.log("通過: " + cnt_dedup + " (移除: " + (cnt_date-cnt_dedup) + ")");
  } else {
    Logger.log("通過: " + cnt_dedup + " (移除: " + (cnt_share-cnt_dedup) + ")");
  }

  return {
    raw_total: allResults.length,
    share_full: cnt_share_full,
    share_1of1: cnt_share_1of1,
    share_empty: cnt_share_empty,
    share_other: cnt_share_other_r,
    after_share_all: cnt_share,
    saleno_123: cnt_saleno_123,
    saleno_4: cnt_saleno_4,
    saleno_5: cnt_saleno_5,
    saleno_6: cnt_saleno_6,
    saleno_7: cnt_saleno_7,
    saleno_8: cnt_saleno_8,
    saleno_9: cnt_saleno_9,
    saleno_99: cnt_saleno_99,
    saleno_other: cnt_saleno_other,
    after_saleno_12346: cnt_saleno_12346,
    removed_by_share: allResults.length - cnt_share,
    removed_by_saleno: cnt_share - cnt_saleno_12346,
    after_date: cnt_date,
    removed_by_date: cnt_saleno_12346 - cnt_date,
    after_dedup: cnt_dedup,
    removed_by_dedup: isGeneral ? (cnt_date - cnt_dedup) : (cnt_share - cnt_dedup),
    today_roc: todayROC,
    saletype_used: saletypeVal,
    isGeneral: isGeneral,
    saletitle_dist: saletitleDist,
    first_fields: firstFields,
    para_by_saleno: paraBySaleno
  };
}

