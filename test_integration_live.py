#!/usr/bin/env python3
"""
真整合測試：直接打線上 GAS Web App (@26)，驗證權限/版本/快取/鑑權
執行：WEB_APP_URL 已內建，也可 env 覆蓋；FREE/PRO 帳號需在「會員名單」工作表 A:B
  python -m pytest test_integration_live.py -v
  或  WEB_APP_URL=... ADMIN_TOKEN=... FREE_EMAIL=... PRO_EMAIL=... pytest
若 FREE/PRO 未設，對應用例自動 skip，不影響 visitor 測試。
"""

import os
import time

import pytest
import requests

WEB_APP_URL = os.getenv(
    "WEB_APP_URL",
    "https://script.google.com/macros/s/AKfycbz8lDXJsyjAvuhDTW_heIkNI6vGnFUAk9gB-4sVkcD499ObQDslO1mMoe8CljI_CXJv/exec",
)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "02kEjSmOSw3lbG5Ee89zzpV6yHX_VhTv")
FREE_EMAIL = os.getenv("FREE_EMAIL", "")
PRO_EMAIL = os.getenv("PRO_EMAIL", "")

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
    assert j["version"] == "1.1.4"
    assert j["totalGeneral"] > 0 and j["totalSpecial"] > 0


def test_visitor_unknown_email():
    j = get("?email=unknown_test_999@example.com")
    assert j["userRole"] == "visitor"
    assert len(j["general"]) <= 3


def test_free_10():
    if not FREE_EMAIL:
        pytest.skip("FREE_EMAIL 未設，請在 env 或會員名單設定 free 帳號")
    j = get(f"?email={FREE_EMAIL}")
    assert j["userRole"] == "free", f"預期 free，實得 {j['userRole']}"
    assert len(j["general"]) <= 10
    assert j["totalGeneral"] >= len(j["general"])


def test_pro_infinity():
    if not PRO_EMAIL:
        pytest.skip("PRO_EMAIL 未設，請在 env 或會員名單設定 pro 帳號")
    j = get(f"?email={PRO_EMAIL}")
    assert j["userRole"] == "pro", f"預期 pro，實得 {j['userRole']}"
    assert len(j["general"]) == j["totalGeneral"], "pro 應回全量"
    assert len(j["special"]) == j["totalSpecial"]


def test_forbidden_no_token():
    j = get("?debug=1")
    assert j.get("error") == "forbidden"


def test_forbidden_wrong_token():
    j = get("?debug=1&token=wrong_token_123")
    assert j.get("error") == "forbidden"


def test_debug_with_token():
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
