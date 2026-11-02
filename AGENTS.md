# AGENTS.md — 法拍補償 PRO

GAS Web App（GAS 爬蟲 + Google Sheets + 純 HTML 前端）。無 npm/bundler，前端從 GitHub Pages 跨域呼叫 GAS。

## 架構

| 檔案 | 角色 |
|---|---|
| `法拍清單(一般).gs` | 爬蟲：saletype=1，保留全部拍次 + 日期過濾 |
| `法拍清單(應買).gs` | 爬蟲：saletype=4，**無日期過濾**，僅 share=全部 + 去重 |
| `後端.gs` | Web App API 入口（doGet），讀 Sheet 回傳 JSON + 分塊快取 |
| `常數.gs` | CONST_KEYWORDS（47 偏鄉）、CONST_VERSION、GOOGLE_CLIENT_ID、fetchWithRetry、notifyError、台灣代理呼叫 `fetchViaTaiwanRelay_` |
| `cloud_relay/` | **實際抓取來源**：Cloud Run functions `judicial-relay`（asia-east1，私有），`judicial.py` 為抓取核心 |
| `relay_scrape.py` | 手動備援 / 診斷：台灣 IP 電腦上抓 → POST `doPost(action=ingest)`；`--dry-run` 只抓不送 |
| `index.html` | 前端（GitHub Pages 部署） |
| `live_site.html` | 前端模板（WIP，WEB_APP_URL 留空） |
| `*.py` | Legacy 驗證工具，非必要勿改 |

## 資料流（2026-10-29 起）

司法院**擋所有境外 IP**（2026-11-02 用 25 國測試點驗證）。GAS 在 Google 美國機房執行（`Address unavailable`），GitHub Actions 也被擋。**重試修不好，不要再往 fetchWithRetry 方向修。** Google Cloud asia-east1（彰化）IP 登記為台灣，可連。

GAS 時間觸發器（每天 9–10 點）→ `runAllUpdate` → `fetchViaTaiwanRelay_()` → Cloud Run `judicial-relay` 抓 V2.htm 憑證 + QUERY.htm saletype=1、4 原始 data → `ingestRaw_()` → `writeGeneralList_` / `writeBuyList_`（篩選寫表）→ 設 `LAST_INGEST_AT` + `warmCache`。失敗寄「台灣代理抓取失敗」，保留既有資料。

- 函式：GCP 專案 `ceremonial-tea-397301`（帳號 rock90340@gmail.com，計費「富邦」已達 5 專案上限，故共用此專案），標籤 `app=fapai-relay`
- 雙重驗證：Cloud Run IAM（**私有**，不可 `--allow-unauthenticated`）＋ header `X-Relay-Secret`
  - GAS 以 `ScriptApp.getIdentityToken()` 呼叫，需 `appsscript.json` 的 `openid` scope；token 的 aud（`RELAY_ID_AUD`，由 GAS 編輯器手動執行 `authorizeRelay()` 取得）須設為 Cloud Run custom audience：
    `gcloud run services update judicial-relay --region=asia-east1 --add-custom-audiences=<aud> --project=ceremonial-tea-397301`
  - **重新 `gcloud functions deploy` 後要確認 custom audience 還在**
- 密鑰位置：`RELAY_SECRET` 在函式環境變數＋本機 `.env`；GAS ScriptProperties `RELAY_PROXY_URL` / `RELAY_PROXY_SECRET`（以 doPost `setRelayProxy` 寫入，見 `relay_scrape.py` 的 `_post_json`）。**不可寫進程式或 git**
- 重新部署函式（密鑰從 .env 產生 env-vars 檔，部署後刪除，輸出勿印密鑰）：
  `gcloud functions deploy judicial-relay --gen2 --region=asia-east1 --runtime=python312 --source=cloud_relay --entry-point=relay --trigger-http --no-allow-unauthenticated --memory=256Mi --timeout=120s --max-instances=1 --update-labels=app=fapai-relay --env-vars-file=<tmp.yaml> --project=ceremonial-tea-397301`
- `?action=relayStatus&token=xxx`：最後寫入時間、`proxyConfigured`、`idAud`、`loginConfigured`
- `?action=runAllUpdate&token=xxx`：手動觸發（與觸發器同一路徑）；未設定代理時走舊路徑（`force=1` 強制 GAS 自抓）
- 備援：台灣 IP 電腦 `python relay_scrape.py`（讀 `.env` 的 ADMIN_TOKEN）

## 使用者權限

visitor=3 筆、free=10 筆、pro=無限。會員資料在「會員名單」工作表（A=Email, B=role）。

**身分只認 Google 登入的 ID token**（前端 GIS → `&id_token=`），後端 `verifyIdToken_` 經 tokeninfo 驗 aud=`GOOGLE_CLIENT_ID`、iss、email_verified、exp，結果快取 ≤1 小時。`?email=` 一律忽略（舊版可冒用他人信箱拿 pro）。

- OAuth 用戶端：GCP `ceremonial-tea-397301`，Client ID 為公開值，同時寫在 `常數.gs` 與 `index.html`
- Google 不接受 github.io 為授權網域 → 無法正式發布，**維持「測試」模式**：只有「目標對象 → 測試使用者」名單（上限 100）能登入。**新增會員要同時加到試算表「會員名單」和測試使用者**
- 隱私權頁：`foreclosure-compensation-analyzer/privacy.html`

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
- `常數.gs` → `CONST_VERSION`
- `index.html` → `#version-badge` 靜態文字、`APP_VERSION`、`WEB_APP_URL`

`verify_version.py --strict`（CI）另檢查：`.env` 未被 git 追蹤、程式裡沒有寫死的密鑰。

前端載入時比對 `data.version` vs `APP_VERSION`，不符時 toast 提示重整。

## 部署

```bash
npx clasp push -f            # 上傳所有檔案到 GAS（非互動環境需加 -f）
# 原地更新正式部署（URL 不變，不必改 index.html:247）
npx clasp deploy -i AKfycbz8lDXJsyjAvuhDTW_heIkNI6vGnFUAk9gB-4sVkcD499ObQDslO1mMoe8CljI_CXJv -d "說明"
git add -A && git commit -m "" && git push
```

**對外前端在另一個 repo `rock903400-byte/foreclosure-compensation-analyzer`（GitHub Pages）**：本 repo 的 `index.html` 改完要複製過去推上 main。本 repo 預設分支 `master` 只放轉址頁。

GAS 設定（appsscript.json）：`executeAs: USER_DEPLOYING`、`access: ANYONE_ANONYMOUS`、`runtimeVersion: V8`、明列 `oauthScopes`（含 `openid`）。**改 scope 後要先在 GAS 編輯器執行任一函式重新授權，才能更新正式部署**，否則 Web App 與觸發器會因缺授權而失敗。

## 開發命令

```bash
black .
ruff check . --fix
ruff check .
python test_100_users.py     # mock 測試（不需外部服務）
```

## 已知陷阱

- `runAllUpdate` 含 5 分鐘超時 + `LockService`，分頁迴圈另有 4.5 分鐘保護，避免 GAS 6 分鐘限制中途寫入不完整數據
- 司法院自 2026-10-29 起**持續**擋境外 IP（見「資料流」）；GAS 直連司法院的程式（refreshSession、scrapeGeneral/Buy、debug）都會失敗，只能走台灣代理
- 司法院網站 (`aomp109.judicial.gov.tw`) 偶發瞬時 `Address unavailable` 或 5xx：所有對外請求須透過 `常數.gs` 的 `fetchWithRetry(url, options, 3)`（指數退避 2s/4s）呼叫；`refreshSession` 失敗時由其單一處呼叫 `notifyError`，`runAllUpdate` 不重複告警且保留既有試算表與快取資料
- 應買**沒有**日期過濾（與一般不同），舊版曾錯誤加入導致筆數從 121 掉到 6
- WEB_APP_URL 必須指向**最新部署版本**，否則前端連不上 API
- `.clasp.json` 在 `.gitignore`（包含 scriptId），clone 後需自行設定
