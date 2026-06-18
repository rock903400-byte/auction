# AGENTS.md — 法拍補償 PRO

## 專案結構

```
法拍清單(一般).gs   → 爬蟲：抓一般法拍資料 → 寫入 Google Sheet「法拍清單(一般)」
法拍清單(應買).gs   → 爬蟲：抓應買資料 → 寫入 Google Sheet「法拍清單(應買)」
後端.gs             → Web App API：讀上面兩個 Sheet → JSON API
index.html          → 前端（GitHub Pages 部署）
live_site.html      → 前端模板（WEB_APP_URL 為空，需手動填入）
test_100_users.py   → 模擬測試
*.py (其他)         → Legacy 分析腳本，非必要勿改
```

## 部署

- **前端**: `index.html` → GitHub Pages (`rock903400-byte/auction`)
- **後端**: `.gs` 全部放在同一個 GAS 專案（script.google.com），手動貼入
- **Google Sheet**: 需有 `法拍清單(一般)`、`法拍清單(應買)`、`會員名單` 三個工作表

## 開發命令（Python）

```bash
black .                     # format
ruff check . --fix          # lint auto-fix
ruff check .                # lint check
flake8 .                    # flake8
python test_100_users.py    # test
```

執行順序建議：`black → ruff check . --fix → ruff check . → python test_100_users.py`

## 關鍵業務邏輯（`後端.gs`）

- 篩選：只追蹤 40+ 偏鄉地區、持分須為「全部」或「1分之1」
- 計算：補償金 = `ceil(面積m² × 6)`、ROI = 補償金 / 底價 × 100
- 權限：visitor=3 筆、free=10 筆、pro=無限
- 快取：分段快取（ChunkedCache）突破 GAS 100KB 限制，TTL=5 分鐘

## 前端注意 (`index.html`)

- `index.html:237` — `WEB_APP_URL` 指向 GAS Web App 部署網址
- 部署 HTTP 環境時 copy() 有 textarea fallback（已修復）
- 無 TypeScript、無 npm、無 bundler

## 測試腳本 (`test_100_users.py`)

- 模擬 100 用戶並發存取（threading）
- 檢查：登入成功率、UI 響應時間、權限違規、排序/篩選正確性
- 純 mock 數據，不需外部服務
