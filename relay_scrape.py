"""司法院法拍資料中繼抓取（relay）。

背景：自 2026-10-29 起司法院網站阻擋 Google Apps Script 的出口 IP，
GAS 內的 UrlFetchApp 一律回 `Address unavailable`。本腳本改由非 Google 的
機器（GitHub Actions 或本機）抓取原始資料，再 POST 給 GAS `doPost`
(action=ingest)，篩選、寫表、預熱快取仍由 GAS 原邏輯處理。

用法：
    python relay_scrape.py --dry-run          # 只抓取並列出筆數，不送 GAS
    ADMIN_TOKEN=xxx python relay_scrape.py    # 抓取並送 GAS

環境變數：
    ADMIN_TOKEN  必填（非 dry-run），與 GAS 專案屬性 ADMIN_TOKEN 相同
    GAS_URL      選填，預設讀 index.html 的 WEB_APP_URL

僅使用標準函式庫，無需 pip install。
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02"
V2_URL = BASE + "/V2.htm"
QUERY_URL = BASE + "/QUERY.htm"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
PAGE_SIZE = 100
HERE = Path(__file__).resolve().parent


def read_keywords() -> str:
    """從 常數.gs 讀 CONST_KEYWORDS，保持單一來源。"""
    src = (HERE / "常數.gs").read_text(encoding="utf-8")
    m = re.search(r'var\s+CONST_KEYWORDS\s*=\s*"([^"]+)"', src)
    if not m:
        raise RuntimeError("常數.gs 找不到 CONST_KEYWORDS")
    return m.group(1)


def read_web_app_url() -> str:
    src = (HERE / "index.html").read_text(encoding="utf-8")
    m = re.search(r"var\s+WEB_APP_URL\s*=\s*'([^']+/exec)'", src)
    if not m:
        raise RuntimeError("index.html 找不到 WEB_APP_URL")
    return m.group(1)


def with_retry(fn, attempts: int = 3, label: str = ""):
    """指數退避重試（2s/4s），對應 GAS fetchWithRetry。"""
    last: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            return fn()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            print(f"⚠️ {label} 第 {i}/{attempts} 次失敗: {e}", file=sys.stderr)
            if i < attempts:
                time.sleep(2 * i)
    raise RuntimeError(f"{label} 重試 {attempts} 次仍失敗: {last}")


class Judicial:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )
        self.csrf = ""
        self.token = ""

    def _open(self, req: urllib.request.Request) -> str:
        with self.opener.open(req, timeout=60) as res:
            return res.read().decode("utf-8", errors="replace")

    def refresh_session(self) -> None:
        """對應 GAS refreshSession：取 Cookie / _csrf / token。"""
        for attempt in range(1, 4):
            req = urllib.request.Request(
                V2_URL,
                headers={
                    "User-Agent": UA,
                    "Accept": "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                },
            )
            html = with_retry(lambda: self._open(req), label="V2.htm")
            m_csrf = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
            m_tok = re.search(
                r"var\s+token\s*=\s*['\"]([^'\"]+)['\"]", html, re.I
            ) or re.search(r'name="token"\s+value="([^"]+)"', html)
            self.csrf = m_csrf.group(1) if m_csrf else ""
            self.token = m_tok.group(1) if m_tok else ""
            if self.csrf and self.token:
                print(f"✅ 憑證取得成功（cookies={len(self.jar)}）")
                return
            print(f"⚠️ 第 {attempt} 次未解析出 CSRF/Token", file=sys.stderr)
            time.sleep(2 * attempt)
        raise RuntimeError("無法解析憑證 (CSRF/Token 為空)，可能頁面改版或被阻擋")

    def query_all(self, saletype: str, keywords: str) -> list[dict]:
        """對應 GAS 分頁迴圈：回傳 QUERY.htm 原始 data（未篩選）。"""
        rows: list[dict] = []
        page, total = 1, 0
        while True:
            form = {
                "proptype": "C51",
                "saletype": saletype,
                "keyword": keywords,
                "rrange": "ALL",
                "pageSize": str(PAGE_SIZE),
                "page": str(page),
                "token": self.token,
                "_csrf": self.csrf,
                "sorted_column": "A.CRMYY, A.CRMID, A.CRMNO, A.SALENO, A.ROWID",
                "sorted_type": "ASC",
                "is_search": "Y",
            }
            req = urllib.request.Request(
                QUERY_URL,
                data=urllib.parse.urlencode(form).encode("utf-8"),
                headers={
                    "User-Agent": UA,
                    "Referer": V2_URL,
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Content-Type": "application/x-www-form-urlencoded; "
                    "charset=UTF-8",
                },
            )
            text = with_retry(
                lambda: self._open(req), label=f"QUERY saletype={saletype} p{page}"
            )
            try:
                js = json.loads(text)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"saletype={saletype} 第 {page} 頁非 JSON（憑證失效？）: "
                    f"{text[:200]!r}"
                ) from e
            data = js.get("data") or []
            rows.extend(data)
            total = int(js.get("total") or 0)
            print(
                f"  saletype={saletype} 第 {page} 頁 {len(data)} 筆，累計 "
                f"{len(rows)}/{total}"
            )
            if len(data) < PAGE_SIZE or len(rows) >= total:
                break
            page += 1
            time.sleep(0.5)
        return rows


def post_to_gas(url: str, token: str, general: list, buy: list) -> dict:
    body = json.dumps(
        {"action": "ingest", "token": token, "general": general, "buy": buy},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    # GAS doPost 回 302 → googleusercontent，urllib 會自動改用 GET 跟隨
    with urllib.request.urlopen(req, timeout=300) as res:
        text = res.read().decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"GAS 回應非 JSON: {text[:300]!r}") from e


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="只抓取，不送 GAS")
    ap.add_argument("--dump", help="把原始資料另存成 JSON 檔（除錯用）")
    args = ap.parse_args()

    token = os.environ.get("ADMIN_TOKEN", "").strip()
    if not args.dry_run and not token:
        print("❌ 缺少環境變數 ADMIN_TOKEN", file=sys.stderr)
        return 2

    keywords = read_keywords()
    j = Judicial()
    j.refresh_session()
    print("📄 抓取一般（saletype=1）")
    general = j.query_all("1", keywords)
    print("📄 抓取應買（saletype=4）")
    buy = j.query_all("4", keywords)
    print(f"📦 原始筆數：一般 {len(general)}、應買 {len(buy)}")

    if args.dump:
        Path(args.dump).write_text(
            json.dumps({"general": general, "buy": buy}, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"💾 已存 {args.dump}")

    if not general and not buy:
        print("❌ 兩類皆 0 筆，不送 GAS（避免覆蓋既有資料）", file=sys.stderr)
        return 1
    if args.dry_run:
        print("🧪 dry-run，不送 GAS")
        return 0

    gas_url = os.environ.get("GAS_URL", "").strip() or read_web_app_url()
    res = post_to_gas(gas_url, token, general, buy)
    print("📨 GAS 回應:", json.dumps(res, ensure_ascii=False))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
