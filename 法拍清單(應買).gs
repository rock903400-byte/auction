function scrapeLandStableBatch_Buy() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // 🔴 步驟 1：讀取共用的「設定(驗證資訊)」工作表
  const configSheetName = "設定(驗證資訊)";
  let configSheet = ss.getSheetByName(configSheetName);
  
  if (!configSheet) {
    Logger.log("❌ 找不到【" + configSheetName + "】工作表，請先執行一般清單的程式來建立設定檔。");
    return;
  }
  
  const cookieVal = configSheet.getRange("B1").getValue().toString().trim();
  const csrfVal = configSheet.getRange("B2").getValue().toString().trim();
  const tokenVal = configSheet.getRange("B3").getValue().toString().trim();
  
  if (!cookieVal || !csrfVal || !tokenVal || cookieVal.includes("請將您抓到的")) {
    Logger.log("❌ 尚未填入完整的驗證資訊，請至【" + configSheetName + "】確認。");
    return;
  }

  // 🔴 步驟 2：準備目標資料表 (應買)
  const targetSheetName = "法拍清單(應買)";
  let sheet = ss.getSheetByName(targetSheetName);
  if (!sheet) { sheet = ss.insertSheet(targetSheetName); }

  const headers_excel = [
    "筆次", "法院名稱", "案號", "股別", "拍賣日期", "特別程序",
    "縣市", "土地坐落", "面積", "總拍賣底價(元)",
    "點交", "空地", "標別", "看圖", "備註",
    "採通訊投標", "土地有無遭受污染", "地圖",
    "", "土地單價(元/㎡)",
    "預估補償金", "ROI (%)", "PDF 連結", "是否點交", "是否空地"
  ];

  function getSafeNum(val) {
    if (val == null || val === '') return 0;
    const n = parseFloat(String(val).replace(/,/g, ''));
    return isNaN(n) ? 0 : Math.floor(n);
  }

  try {
    const url = "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/QUERY.htm";
    // 🔴 修正：根據使用者資料，精確設定 40 個鄉鎮市關鍵字
    var searchKeywords = CONST_KEYWORDS;

    let allFetchedData = [];
    let currentPage = 1;
    let totalRecords = 0;
    const pageSize = 100;

    // 🔴 循環抓取分頁 (應買程序)
    do {
      Logger.log("📄 正在抓取第 " + currentPage + " 頁 (應買)...");
      const payload = {
        "proptype": "C51",
        "saletype": "4", 
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
          "X-Requested-With": "XMLHttpRequest",
          "Accept": "application/json, text/javascript, */*; q=0.01"
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
        Logger.log("✅ 應買第 " + currentPage + " 頁完成，累計: " + allFetchedData.length + "/" + totalRecords);
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
        const share = (item.rrange || "").trim();
        if (share !== "全部") return;

        const uniqueKey = item.hsimun + item.crmyy + item.crmid + item.crmno + (item.saleno || "") + (item.batchno || "") + (item.sec || "") + (item.landno || "");
        if (!uniqueData.has(uniqueKey)) {
          uniqueData.set(uniqueKey, item);
        }
      });

      const filteredData = Array.from(uniqueData.values());
      Logger.log("🧹 應買篩選後總筆數: " + filteredData.length + " 筆");

      let allRows = filteredData.map((item, index) => {
        const totalSum = getSafeNum(item.summinprc);
        let individualPrice = getSafeNum(item.minprice) || getSafeNum(item.minprc) || totalSum;

        const areaM2 = parseFloat(item.area3) || 0;
        const areaTsubo = Math.round(areaM2 * 0.3025);
        
        const areaDisplay = areaTsubo + "坪(" + areaM2.toFixed(2) + "平方公尺) x " + (item.rrange || "全部") + "\n土地拍賣底價:新台幣 " + individualPrice.toLocaleString() + " 元";
        let unitPriceDisplay = (areaM2 > 0 && individualPrice > 0) ? parseFloat((individualPrice / areaM2).toFixed(2)) : "無法解析";

        const fullLocation = item.ctmd + (item.sec || "") + "段 " + (item.subsec || "小段 ") + (item.landno || "") + "號";
        const mapAddr = item.hsimun + item.ctmd + (item.sec || "") + "段" + (item.landno || "");
        const mapUrl = "https://www.google.com/maps/search/" + encodeURIComponent(mapAddr);
        const pdfUrl = item.filenm ? "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/DO_VIEWPDF.htm?filenm=" + item.filenm : "";
        const comp = Math.ceil(areaM2 * 6);
        const roi = totalSum > 0 ? parseFloat((comp / totalSum * 100).toFixed(2)) : 0;

        return [
          index + 1, item.hsimun + "地方法院", item.crmyy + "年" + item.crmid + "字第" + item.crmno + "號",
          "(" + (item.dpt || "") + "股)", item.saledate,
          item.saletitle || (item.saleno === "4" ? "應買" : "特別程序"),
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
        sheet.appendRow(headers_excel);
        sheet.getRange(1, 1, 1, headers_excel.length).setFontWeight("bold").setBackground("#444444").setFontColor("white");
        sheet.getRange(1, 20).setBackground("#d9ead3").setFontColor("black");
        sheet.getRange(1, 21, 1, 5).setBackground("#fff2cc").setFontColor("black");
        sheet.getRange(2, 1, allRows.length, allRows[0].length).setValues(allRows);
        sheet.getRange(2, 9, allRows.length, 1).setWrap(true);
        sheet.getRange(2, 20, allRows.length, 1).setNumberFormat("#,##0.00");
        sheet.getRange(2, 21, allRows.length, 1).setNumberFormat("#,##0");
        sheet.getRange(2, 22, allRows.length, 1).setNumberFormat("0.00");
        sheet.autoResizeColumns(1, 25);
        Logger.log("🎯 【應買】清單更新完畢！");
      } else {
        notifyError("應買篩選後為0筆", new Error("filteredData empty"), {step: "scrapeBuy", raw: allFetchedData.length, filtered: filteredData.length});
      }
      
    } else {
      notifyError("應買API回傳0筆", new Error("allFetchedData empty"), {step: "scrapeBuy"});
    }

  } catch (e) {
    Logger.log("❌ 執行應買發生錯誤: " + e.message);
    notifyError("應買清單抓取失敗", e, {step: "scrapeBuy"});
  }
}