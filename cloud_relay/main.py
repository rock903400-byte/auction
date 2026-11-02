"""台灣機房代抓函式（Cloud Run functions, asia-east1）。

司法院擋所有境外 IP，GAS 在 Google 美國機房執行，連不上；asia-east1（彰化）
的 IP 登記為台灣。GAS 時間觸發器 runAllUpdate → fetchViaTaiwanRelay_() 呼叫本函式，
本函式抓原始資料回傳，GAS 再沿用 writeGeneralList_ / writeBuyList_ 寫表。

安全：
- 沒有正確的 X-Relay-Secret → 直接 403，不對外發任何請求
- 只連司法院固定端點（見 judicial.py），不接受任意 URL，不能當開放代理
- keyword 長度上限；不記錄密鑰
"""

from __future__ import annotations

import hmac
import json
import os
import time

import functions_framework

from judicial import Judicial

MAX_KEYWORD_LEN = 2000


def _json(obj: dict, status: int = 200):
    return (
        json.dumps(obj, ensure_ascii=False),
        status,
        {"Content-Type": "application/json; charset=utf-8"},
    )


@functions_framework.http
def relay(request):
    secret = os.environ.get("RELAY_SECRET", "")
    got = request.headers.get("X-Relay-Secret", "")
    if not secret or not hmac.compare_digest(got.encode(), secret.encode()):
        return _json({"ok": False, "error": "forbidden"}, 403)
    if request.method != "POST":
        return _json({"ok": False, "error": "method not allowed"}, 405)

    body = request.get_json(silent=True) or {}
    probe = bool(body.get("probe"))
    keyword = str(body.get("keyword") or "").strip()
    if not probe and (not keyword or len(keyword) > MAX_KEYWORD_LEN):
        return _json({"ok": False, "error": "bad keyword"}, 400)

    t0 = time.time()
    try:
        j = Judicial()
        j.refresh_session()
        if probe:
            return _json({"ok": True, "probe": True, "cookies": len(j.jar)})
        general = j.query_all("1", keyword)
        buy = j.query_all("4", keyword)
    except Exception as e:  # noqa: BLE001 — 任何失敗都回 502 給 GAS 告警
        return _json({"ok": False, "error": f"{type(e).__name__}: {e}"[:500]}, 502)
    return _json(
        {
            "ok": True,
            "general": general,
            "buy": buy,
            "elapsed": round(time.time() - t0, 1),
        }
    )
