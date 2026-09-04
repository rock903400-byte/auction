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

const CACHE_KEY = "auction_data_v3"; // 舊版合併快取（僅清快取時相容用）
const CACHE_KEY_GENERAL = "auction_data_general_v1";
const CACHE_KEY_SPECIAL = "auction_data_special_v1";
// 一天只爬一次，快取拉到 CacheService 上限 6 小時；爬蟲寫表後會主動預熱（write-through），
// 平時 doGet 幾乎不碰試算表
const CACHE_TTL = 6 * 60 * 60;
const ROLE_CACHE_PREFIX = "role_v1_";
const ROLE_CACHE_TTL = 30 * 60; // 會員權限 30 分鐘快取（改權限最多延遲 30 分鐘生效）

// ─── 入口點（JSON API，供 GitHub Pages 前端跨網域呼叫）────────────────────────
function doGet(e) {
  const params = (e && e.parameter) ? e.parameter : {};

  // ── 內部小圈：特權操作需 ADMIN_TOKEN（PropertiesService）────────────────
  if (params.action || params.debug === '1') {
    try {
      var _adminToken = PropertiesService.getScriptProperties().getProperty('ADMIN_TOKEN') || '';
    } catch (_err) { var _adminToken = ''; }
    if (!_adminToken || params.token !== _adminToken) {
      return ContentService
        .createTextOutput(JSON.stringify({ error: 'forbidden' }))
        .setMimeType(ContentService.MimeType.JSON);
    }
  }

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

  // Remote action endpoints (for clasp-free remote execution)
  if (params.action === 'refreshSession') {
    try { var ok = refreshSession(); } catch (e) { ok = false; }
    return ContentService
      .createTextOutput(JSON.stringify({ ok: ok }))
      .setMimeType(ContentService.MimeType.JSON);
  }
  if (params.action === 'scrapeGeneral') {
    try { scrapeLandStableBatch_General(); return ContentService.createTextOutput(JSON.stringify({ ok: true })).setMimeType(ContentService.MimeType.JSON); }
    catch (err) { return ContentService.createTextOutput(JSON.stringify({ ok: false, error: err.message })).setMimeType(ContentService.MimeType.JSON); }
  }
  if (params.action === 'scrapeBuy') {
    try { scrapeLandStableBatch_Buy(); return ContentService.createTextOutput(JSON.stringify({ ok: true })).setMimeType(ContentService.MimeType.JSON); }
    catch (err) { return ContentService.createTextOutput(JSON.stringify({ ok: false, error: err.message })).setMimeType(ContentService.MimeType.JSON); }
  }
  if (params.action === 'warmCache') {
    try {
      var warmed = warmCache();
      return ContentService.createTextOutput(JSON.stringify({ ok: true, general: warmed.general.length, special: warmed.special.length })).setMimeType(ContentService.MimeType.JSON);
    }
    catch (err) { return ContentService.createTextOutput(JSON.stringify({ ok: false, error: err.message })).setMimeType(ContentService.MimeType.JSON); }
  }
  if (params.action === 'clearCache') {
    try { clearCache(); return ContentService.createTextOutput(JSON.stringify({ ok: true })).setMimeType(ContentService.MimeType.JSON); }
    catch (err) { return ContentService.createTextOutput(JSON.stringify({ ok: false, error: err.message })).setMimeType(ContentService.MimeType.JSON); }
  }

  const email = params.email ? params.email.trim() : '';
  const role = email ? checkUserRole(email) : 'visitor';

  // tab=all（預設，相容舊前端）| general | special：只回傳該分頁陣列，total 兩個都給（前端 badge 用）
  const tab = params.tab ? params.tab.toString().toLowerCase() : 'all';
  const wantGeneral = tab !== 'special';
  const wantSpecial = tab !== 'general';

  let allData = null;
  try {
    allData = getLists();
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ error: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  const limit = role === 'pro' ? Infinity : (role === 'free' ? 10 : 3);
  return ContentService
    .createTextOutput(JSON.stringify({
      version:     CONST_VERSION,
      general:     wantGeneral ? allData.general.slice(0, limit) : [],
      special:     wantSpecial ? allData.special.slice(0, limit) : [],
      totalGeneral: allData.general.length,
      totalSpecial: allData.special.length,
      updatedAt:   allData.updatedAt,
      userEmail:   email,
      userRole:    role,
    }))
    .setMimeType(ContentService.MimeType.JSON);
}

// ─── 查詢會員權限（含 30 分鐘快取，避免每次請求都讀表）───────────────────────
function checkUserRole(email) {
  if (!email) return 'visitor';
  const norm = email.toString().trim().toLowerCase();
  if (!norm) return 'visitor';
  const key = ROLE_CACHE_PREFIX + norm;
  let cache = null;
  try {
    cache = CacheService.getScriptCache();
    const hit = cache.get(key);
    if (hit) return hit;
  } catch (e) { cache = null; }
  const role = lookupUserRole(norm);
  try { if (cache) cache.put(key, role, ROLE_CACHE_TTL); } catch (e) {}
  return role;
}

// ─── 會員權限實際查表（僅快取未命中時呼叫）────────────────────────────────────
function lookupUserRole(normEmail) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const memberSheet = ss.getSheetByName(SHEET_NAMES.MEMBERS);
    if (!memberSheet || memberSheet.getLastRow() < 2) return 'visitor';
    const data = memberSheet.getRange(2, 1, memberSheet.getLastRow() - 1, 2).getValues();
    for (const row of data) {
      if (row[0].toString().trim().toLowerCase() === normEmail) {
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
    allData = getLists();
  } catch (e) { allData = null; }

  if (!allData) {
    return { general: [], special: [], updatedAt: null, error: '讀取資料失敗', userEmail: email, userRole: role };
  }

  const limit = role === 'pro' ? Infinity : (role === 'free' ? 10 : 3);
  return {
    version:      CONST_VERSION,
    general:      allData.general.slice(0, limit),
    special:      allData.special.slice(0, limit),
    totalGeneral: allData.general.length,
    totalSpecial: allData.special.length,
    updatedAt:    allData.updatedAt,
    userEmail:    email,
    userRole:     role,
  };
}

// ─── 強制清除快取（含舊版合併快取鍵，相容用）──────────────────────────────────
function clearCache() {
  const cache = CacheService.getScriptCache();
  removeChunkedCache(cache, CACHE_KEY_GENERAL);
  removeChunkedCache(cache, CACHE_KEY_SPECIAL);
  removeChunkedCache(cache, CACHE_KEY);
  Logger.log('快取已清除');
}

// ─── 分拆快取讀寫層（general / special 各一組，避免互相拖累）──────────────────
function cacheKeyForList(name) {
  return name === 'special' ? CACHE_KEY_SPECIAL : CACHE_KEY_GENERAL;
}

function getCachedList(name) {
  try {
    const cache = CacheService.getScriptCache();
    const raw = getChunkedCache(cache, cacheKeyForList(name));
    if (raw) return JSON.parse(raw); // { items, updatedAt }
  } catch (e) {}
  return null;
}

function putCachedList(name, items, updatedAt) {
  try {
    const cache = CacheService.getScriptCache();
    putChunkedCache(cache, cacheKeyForList(name), JSON.stringify({ items: items, updatedAt: updatedAt }), CACHE_TTL);
    return true;
  } catch (e) {
    return false;
  }
}

// 僅在快取未命中時讀表（doGet 熱路徑平時不碰試算表）
function readSheetLists() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const updatedAt = new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' });
  return {
    general:   extractData(ss.getSheetByName(SHEET_NAMES.GENERAL)),
    special:   extractData(ss.getSheetByName(SHEET_NAMES.SPECIAL)),
    updatedAt: updatedAt,
  };
}

// 讀快取優先，miss 才讀表並回填；讀表失敗時有什麼吃什麼（部分快取降級）
function getLists() {
  const g = getCachedList('general');
  const s = getCachedList('special');
  if (g && s) {
    return { general: g.items, special: s.items, updatedAt: g.updatedAt, cacheHit: true };
  }
  let fresh = null;
  try {
    fresh = readSheetLists();
  } catch (err) {
    if (g || s) {
      return {
        general: g ? g.items : [], special: s ? s.items : [],
        updatedAt: (g || s).updatedAt, cacheHit: true, partial: true,
      };
    }
    throw err;
  }
  if (fresh.general.length > 0 || fresh.special.length > 0) {
    if (fresh.general.length > 0) putCachedList('general', fresh.general, fresh.updatedAt);
    if (fresh.special.length > 0) putCachedList('special', fresh.special, fresh.updatedAt);
  } else if (typeof notifyError === 'function') {
    // 零數據告警：防 121→6 類事故沉默（僅在非空快取穿透時觸發一次）
    try { notifyError("Sheet 空數據", new Error("both lists empty"), {step:"getLists", cacheHit:false}); } catch (_e) {}
  }
  return {
    // 空讀表不覆蓋舊快取，避免爬蟲中途清空時前端被洗白
    general: fresh.general.length > 0 ? fresh.general : (g ? g.items : []),
    special: fresh.special.length > 0 ? fresh.special : (s ? s.items : []),
    updatedAt: fresh.updatedAt,
    cacheHit: false,
  };
}

// ─── Write-through：爬蟲寫表成功後主動預熱，doGet 直接命中 ────────────────────
function warmCache() {
  const fresh = readSheetLists();
  if (fresh.general.length > 0) putCachedList('general', fresh.general, fresh.updatedAt);
  if (fresh.special.length > 0) putCachedList('special', fresh.special, fresh.updatedAt);
  Logger.log('快取已預熱 general=' + fresh.general.length + ' special=' + fresh.special.length);
  return fresh;
}

// 單表預熱（爬蟲各自呼叫：general → 'general'，應買 → 'special'）
function warmCacheTab(name) {
  const listName = name === 'special' ? 'special' : 'general';
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetName = listName === 'special' ? SHEET_NAMES.SPECIAL : SHEET_NAMES.GENERAL;
  const items = extractData(ss.getSheetByName(sheetName));
  if (items.length > 0) {
    putCachedList(listName, items, new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' }));
  }
  Logger.log('快取已預熱(' + listName + ')=' + items.length);
  return items.length;
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

function removeChunkedCache(cache, key) {
  try {
    const meta = cache.get(key + '_meta');
    const count = meta ? parseInt(meta, 10) : 0;
    const keys = [key + '_meta'];
    for (let i = 0; i < count; i++) keys.push(key + '_c' + i);
    cache.removeAll(keys);
  } catch (e) {
    try { cache.remove(key + '_meta'); } catch (_e) {}
  }
}

// ─── 工具函式 ──────────────────────────────────────────────────────────────────
function safeString(val) {
  return val != null ? val.toString().trim() : '';
}

function safeNumber(val) {
  if (val == null || val === '') return 0;
  const n = parseFloat(val.toString().replace(/,/g, ''));
  return (!isFinite(n) || isNaN(n)) ? 0 : n;
}
