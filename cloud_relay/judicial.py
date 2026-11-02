"""司法院法拍查詢核心（雲端函式 cloud_relay/main.py 與本機 relay_scrape.py 共用）。

只連司法院固定端點 V2.htm（取 Cookie/_csrf/token）與 QUERY.htm（分頁查詢），
回傳原始 data 不做篩選；篩選與寫表一律在 GAS（writeGeneralList_ / writeBuyList_）。
僅使用標準函式庫。
"""

from __future__ import annotations

import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02"
V2_URL = BASE + "/V2.htm"
QUERY_URL = BASE + "/QUERY.htm"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
PAGE_SIZE = 100


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
