# AGENTS.md — 法拍補償 PRO

GAS Web App（GAS 爬蟲 + Google Sheets + 純 HTML 前端）。無 npm/bundler，前端從 GitHub Pages 跨域呼叫 GAS。

## 架構

| 檔案 | 角色 |
|---|---|
| `法拍清單(一般).gs` | 爬蟲：saletype=1，保留全部拍次 + 日期過濾 |
| `法拍清單(應買).gs` | 爬蟲：saletype=4，**無日期過濾**，僅 share=全部 + 去重 |
| `後端.gs` | Web App API 入口（doGet），讀 Sheet 回傳 JSON + 分塊快取 |
| `常數.gs` | CONST_KEYWORDS（47 偏鄉）、CONST_VERSION、fetchWithRetry（指數退避重試）、notifyError |
| `index.html` | 前端（GitHub Pages 部署） |
| `live_site.html` | 前端模板（WIP，WEB_APP_URL 留空） |
| `*.py` | Legacy 驗證工具，非必要勿改 |

## 使用者權限

visitor=3 筆、free=10 筆、pro=無限。會員資料在「會員名單」工作表（A=Email, B=role）。

## 爬蟲篩選邏輯

篩選順序：share=全部 → （一般：日期過濾） → 去重

- **一般**：share="全部" + `saleDate >= todayROC`（跳過過期） + 去重 → **保留全部拍次**
- **應買**：share="全部" + 去重 → **無日期過濾，無拍次過濾**

兩者均透過 CONST_KEYWORDS（47 偏鄉）篩選地區。

## 計算

補償金 = `Math.ceil(areaM2 × 6)`，ROI = 補償金 / 底價 × 100

## Debug

`?debug=1&saletype=X&token=ADMIN_TOKEN` 回傳逐層筆數。注意 debug 內含 `saleno 1/2/3/4/6` 過濾（在日期檢查前），**不等於實際爬蟲邏輯**，尤其 saletype=4 時 after_dedup 會誤導。

Remote actions（不需 clasp 即可觸發爬蟲，需 ADMIN_TOKEN）：
`?action=refreshSession&token=xxx` → `?action=scrapeGeneral&token=xxx` → `?action=scrapeBuy&token=xxx` → `?action=warmCache&token=xxx`（或一鍵 `?action=runAllUpdate&token=xxx`）
> `ADMIN_TOKEN` 設於 GAS 專案屬性：`PropertiesService.getScriptProperties().setProperty('ADMIN_TOKEN','xxx')`

## 設定

「設定(驗證資訊)」工作表存放：B1=Cookie、B2=CSRF、B3=Token、B4=通知信箱。

## 版本號

四處需同步更新（可用 `python verify_version.py` 驗證）：
- `常數.gs:3` → `CONST_VERSION`
- `index.html:187` → `#version-badge` 靜態文字
- `index.html:245` → `APP_VERSION`  
- `index.html:247` → `WEB_APP_URL`

前端載入時比對 `data.version` vs `APP_VERSION`，不符時 toast 提示重整。

## 部署

```bash
npx clasp push -f            # 上傳所有檔案到 GAS（非互動環境需加 -f）
npx clasp undeploy <舊版ID>  # 先移除舊版
npx clasp deploy -d "說明"   # 產生新版 URL（如 @28）
# 更新 index.html:247 的 WEB_APP_URL → 新版 URL
npx clasp push -f            # 同步 index.html
git add -A && git commit -m "" && git push
```

GAS 設定（appsscript.json）：`executeAs: USER_DEPLOYING`、`access: ANYONE_ANONYMOUS`、`runtimeVersion: V8`。

## 開發命令

```bash
black .
ruff check . --fix
ruff check .
python test_100_users.py     # mock 測試（不需外部服務）
```

## 已知陷阱

- `runAllUpdate` 含 5 分鐘超時 + `LockService`，分頁迴圈另有 4.5 分鐘保護，避免 GAS 6 分鐘限制中途寫入不完整數據
- 司法院網站 (`aomp109.judicial.gov.tw`) 偶發瞬時 `Address unavailable` 或 5xx：所有對外請求須透過 `常數.gs` 的 `fetchWithRetry(url, options, 3)`（指數退避 2s/4s）呼叫；`refreshSession` 失敗時由其單一處呼叫 `notifyError`，`runAllUpdate` 不重複告警且保留既有試算表與快取資料
- 應買**沒有**日期過濾（與一般不同），舊版曾錯誤加入導致筆數從 121 掉到 6
- WEB_APP_URL 必須指向**最新部署版本**，否則前端連不上 API
- `.clasp.json` 在 `.gitignore`（包含 scriptId），clone 後需自行設定
