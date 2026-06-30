/**
 * 風的法拍投資系統 — 後端服務 (Code.gs)
 * 架構：GAS Web App + Google 試算表 + 會員名單權限控管
 */

// ─── 欄位索引常數（從 0 開始，對應試算表欄位）──────────────────────────────
const COL = {
  ITEM_NO:     0,   // A: 筆次
  COURT:       1,   // B: 法院名稱
  CASE_NO:     2,   // C: 案號
  DEPT:        3,   // D: 股別
  SALE_DATE:   4,   // E: 拍賣日期
  SALE_TYPE:   5,   // F: 拍次
  COUNTY:      6,   // G: 縣市
  ADDRESS:     7,   // H: 土地坐落
  AREA:        8,   // I: 面積
  PRICE:       9,   // J: 總拍賣底價
  HANDOVER:    10,  // K: 點交
  EMPTY_LAND:  11,  // L: 空地
  BATCH_NO:    12,  // M: 標別
  LINK_N:      13,  // N: 看圖
  NOTE:        14,  // O: 備註
  COMM_BID:    15,  // P: 採通訊投標
  POLLUTION:   16,  // Q: 土地有無遭受污染
  MAP:         17,  // R: 地圖
  EMPTY_COL:   18,  // S: (空)
  UNIT_PRICE:  19,  // T: 土地單價
  COMP:        20,  // U: 預估補償金
  ROI:         21,  // V: ROI (%)
  PDF_URL:     22,  // W: PDF 連結
  IS_HANDOVER: 23,  // X: 是否點交 (是/否)
  IS_EMPTY:    24,  // Y: 是否空地 (是/否)
};

const SHEET_NAMES = {
  GENERAL: "法拍清單(一般)",
  SPECIAL: "法拍清單(應買)",
  MEMBERS: "會員名單",
};

const CACHE_KEY = "auction_data_v3";
const CACHE_TTL = 5 * 60;

// ─── 入口點（JSON API，供 GitHub Pages 前端跨網域呼叫）────────────────────────
function doGet(e) {
  const params = (e && e.parameter) ? e.parameter : {};

  // Debug mode
  if (params.debug === '1') {
    try {
      const result = debugFilterCounts(params.saletype);
      return ContentService
        .createTextOutput(JSON.stringify(result))
        .setMimeType(ContentService.MimeType.JSON);
    } catch (err) {
      return ContentService
        .createTextOutput(JSON.stringify({ error: err.message, stack: err.stack || '' }))
        .setMimeType(ContentService.MimeType.JSON);
    }
  }

  const email = params.email ? params.email.trim() : '';
  const role = email ? checkUserRole(email) : 'visitor';

  const cache = CacheService.getScriptCache();
  let allData = null;
  try {
    const cached = getChunkedCache(cache, CACHE_KEY);
    if (cached) allData = JSON.parse(cached);
  } catch (err) { allData = null; }

  if (!allData) {
    try {
      const ss = SpreadsheetApp.getActiveSpreadsheet();
      allData = {
        general:   extractData(ss.getSheetByName(SHEET_NAMES.GENERAL)),
        special:   extractData(ss.getSheetByName(SHEET_NAMES.SPECIAL)),
        updatedAt: new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' }),
      };
      putChunkedCache(cache, CACHE_KEY, JSON.stringify(allData), CACHE_TTL);
    } catch (err) {
      return ContentService
        .createTextOutput(JSON.stringify({ error: err.message }))
        .setMimeType(ContentService.MimeType.JSON);
    }
  }

  const limit = role === 'pro' ? Infinity : (role === 'free' ? 10 : 3);
  return ContentService
    .createTextOutput(JSON.stringify({
      version:   CONST_VERSION,
      general:   allData.general.slice(0, limit),
      special:   allData.special.slice(0, limit),
      updatedAt: allData.updatedAt,
      userEmail: email,
      userRole:  role,
    }))
    .setMimeType(ContentService.MimeType.JSON);
}

// ─── 查詢會員權限 ──────────────────────────────────────────────────────────────
function checkUserRole(email) {
  if (!email) return 'visitor';
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const memberSheet = ss.getSheetByName(SHEET_NAMES.MEMBERS);
    if (!memberSheet || memberSheet.getLastRow() < 2) return 'visitor';
    const data = memberSheet.getRange(2, 1, memberSheet.getLastRow() - 1, 2).getValues();
    for (const row of data) {
      if (row[0].toString().trim().toLowerCase() === email.toLowerCase()) {
        return row[1].toString().trim().toLowerCase() || 'free';
      }
    }
    return 'visitor';
  } catch (e) {
    return 'visitor';
  }
}

// ─── 前端呼叫：取得試算表資料（附快取層 + 權限切片）─────────────────────────
function getSheetData() {
  let email = '';
  let role = 'visitor';
  try {
    email = Session.getActiveUser().getEmail();
    if (email) role = checkUserRole(email);
  } catch (e) {
    Logger.log('獲取用戶 Email 失敗：' + e.message);
  }

  const cache = CacheService.getScriptCache();
  let allData = null;

  try {
    const cached = getChunkedCache(cache, CACHE_KEY);
    if (cached) allData = JSON.parse(cached);
  } catch (e) { allData = null; }

  if (!allData) {
    try {
      const ss = SpreadsheetApp.getActiveSpreadsheet();
      allData = {
        general:   extractData(ss.getSheetByName(SHEET_NAMES.GENERAL)),
        special:   extractData(ss.getSheetByName(SHEET_NAMES.SPECIAL)),
        updatedAt: new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' }),
      };
      putChunkedCache(cache, CACHE_KEY, JSON.stringify(allData), CACHE_TTL);
    } catch (e) {
      Logger.log('getSheetData 錯誤：' + e.message);
      return { general: [], special: [], updatedAt: null, error: e.message, userEmail: email, userRole: role };
    }
  }

  const limit = role === 'pro' ? Infinity : (role === 'free' ? 10 : 3);
  return {
    version:   CONST_VERSION,
    general:   allData.general.slice(0, limit),
    special:   allData.special.slice(0, limit),
    updatedAt: allData.updatedAt,
    userEmail: email,
    userRole:  role,
  };
}

// ─── 強制清除快取 ──────────────────────────────────────────────────────────────
function clearCache() {
  CacheService.getScriptCache().remove(CACHE_KEY);
  Logger.log('快取已清除');
}

// ─── 解析單一工作表資料 ────────────────────────────────────────────────────────
function extractData(sheet) {
  if (!sheet) return [];
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];

  const totalCols = Math.max(...Object.values(COL)) + 1;
  const values = sheet.getRange(1, 1, lastRow, totalCols).getValues();

  return values.slice(1).reduce((acc, row) => {
    const county = safeString(row[COL.COUNTY]);
    if (!county) return acc;

    acc.push({
      court_name:     safeString(row[COL.COURT]),
      case_no:        safeString(row[COL.CASE_NO]),
      sale_date:      safeString(row[COL.SALE_DATE]),
      sale_type:      safeString(row[COL.SALE_TYPE]),
      county,
      address:        safeString(row[COL.ADDRESS]),
      area_display:   safeString(row[COL.AREA]).replace(/\n/g, ' '),
      base_price:     safeNumber(row[COL.PRICE]),
      unit_price:     safeNumber(row[COL.UNIT_PRICE]),
      estimated_comp: safeNumber(row[COL.COMP]),
      roi:            safeNumber(row[COL.ROI]),
      pdf_url:        safeString(row[COL.PDF_URL]),
      is_handover:    safeString(row[COL.IS_HANDOVER]) === '是',
      is_empty_land:  safeString(row[COL.IS_EMPTY]) === '是',
    });
    return acc;
  }, []);
}

// ─── 快取分段存儲（突破 100KB 限制）────────────────────────────────────────────
function putChunkedCache(cache, key, value, ttl) {
  const CHUNK_SIZE = 90 * 1024;
  const mapping = {};
  let i = 0;
  let chunkCount = 0;
  while (i < value.length) {
    mapping[key + '_c' + chunkCount] = value.substring(i, i + CHUNK_SIZE);
    i += CHUNK_SIZE;
    chunkCount++;
  }
  mapping[key + '_meta'] = String(chunkCount);
  cache.putAll(mapping, ttl);
}

function getChunkedCache(cache, key) {
  const meta = cache.get(key + '_meta');
  if (!meta) return null;
  const count = parseInt(meta, 10);
  const keys = Array.from({ length: count }, (_, i) => key + '_c' + i);
  const values = cache.getAll(keys);
  const parts = keys.map(k => values[k]);
  if (parts.some(p => p == null)) return null;
  return parts.join('');
}

// ─── 工具函式 ──────────────────────────────────────────────────────────────────
function safeString(val) {
  return val != null ? val.toString().trim() : '';
}

function safeNumber(val) {
  if (val == null || val === '') return 0;
  const n = parseFloat(val.toString().replace(/,/g, ''));
  return isNaN(n) ? 0 : n;
}
