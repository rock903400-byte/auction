#!/usr/bin/env python3
"""
真整合測試：直接打線上 GAS Web App，驗證權限/版本/快取/鑑權
執行：WEB_APP_URL 已內建，也可 env 覆蓋
  python -m pytest test_integration_live.py -v
ADMIN_TOKEN 只從環境變數或同目錄 .env 讀取（**不可寫死在程式裡**，repo 是公開的）；
沒有就 skip 需要 token 的用例。
登入改用 Google ID token 後，free/pro 需真人登入，改由瀏覽器手動驗證；
這裡只測「自填 ?email= 不能冒用」與「假 id_token 一律降為訪客」。
"""

import os
import re
import time
from pathlib import Path

import pytest
import requests

HERE = Path(__file__).resolve().parent


def _dotenv(key):
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            k, _, v = line.partition("=")
            if k.strip() == key:
                return v.strip().strip("'\"")
    return ""


def _const_version():
    src = (HERE / "常數.gs").read_text(encoding="utf-8")
    return re.search(r'CONST_VERSION\s*=\s*"(.*?)"', src).group(1)


WEB_APP_URL = os.getenv(
    "WEB_APP_URL",
    "https://script.google.com/macros/s/AKfycbz8lDXJsyjAvuhDTW_heIkNI6vGnFUAk9gB-4sVkcD499ObQDslO1mMoe8CljI_CXJv/exec",
)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "") or _dotenv("ADMIN_TOKEN")

TIMEOUT = 60


def get(params=""):
    # GAS 冷啟動可能 10-30s，重試一次
    last_exc = None
    for attempt in range(2):
        try:
            r = requests.get(WEB_APP_URL + params, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ReadTimeout as e:
            last_exc = e
            time.sleep(2)
            continue
    raise last_exc


def test_visitor_no_email():
    j = get()
    assert j["userRole"] == "visitor"
    assert len(j["general"]) <= 3, f"visitor 應 <=3 筆，實得 {len(j['general'])}"
    assert j["totalGeneral"] >= len(j["general"])
    assert j["version"] == _const_version()
    assert j["totalGeneral"] > 0 and j["totalSpecial"] > 0


def test_email_param_cannot_impersonate():
    """資安回歸：舊版相信 ?email=，任何人填 pro 信箱就能看全部。現在必須一律忽略。"""
    j = get("?email=any_member_test@example.com")
    assert j["userRole"] == "visitor"
    assert j["userEmail"] == "", "後端不應採用自填的 email"
    assert len(j["general"]) <= 3


def test_fake_id_token_is_visitor():
    j = get("?id_token=not.a.real.token")
    assert j["userRole"] == "visitor"
    assert j["userEmail"] == ""
    assert j.get("authError"), "假 token 應回 authError 讓前端重新登入"
    assert len(j["general"]) <= 3


def test_forbidden_no_token():
    j = get("?debug=1")
    assert j.get("error") == "forbidden"


def test_forbidden_wrong_token():
    j = get("?debug=1&token=wrong_token_123")
    assert j.get("error") == "forbidden"


@pytest.mark.skip(
    reason="debugFilterCounts 由 GAS 直連司法院；2026-10-29 起境外 IP 被擋，必定逾時"
)
def test_debug_with_token():
    if not ADMIN_TOKEN:
        pytest.skip("ADMIN_TOKEN 未設（環境變數或 .env）")
    j = get(f"?debug=1&saletype=1&token={ADMIN_TOKEN}")
    # 有 token 應回 debug 結構，而非 forbidden
    assert "error" not in j or j.get("error") != "forbidden"
    assert "isGeneral" in j
    assert j["isGeneral"] is True
    assert "saletype_used" in j


def test_cache_hit_same_updatedAt():
    j1 = get()
    time.sleep(0.5)
    j2 = get()
    # 5 分鐘 TTL 內應命中同一快取
    assert j1["updatedAt"] == j2["updatedAt"]
