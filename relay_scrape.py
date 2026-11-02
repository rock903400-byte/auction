"""司法院法拍資料中繼抓取（relay）。

背景：自 2026-10-29 起司法院擋所有境外 IP（GAS、GitHub Actions 都連不上）。
正式流程是 GAS 時間觸發器呼叫台灣機房函式（cloud_relay/）代抓；本腳本是
**手動備援 / 診斷工具**：在台灣 IP 的電腦上抓原始資料，POST 給 GAS `doPost`
(action=ingest)，篩選、寫表、預熱快取仍由 GAS 原邏輯處理。

用法：
    python relay_scrape.py --dry-run          # 只抓取並列出筆數，不送 GAS
    ADMIN_TOKEN=xxx python relay_scrape.py    # 抓取並送 GAS

環境變數（或同目錄 .env 檔，KEY=VALUE）：
    ADMIN_TOKEN  必填（非 dry-run），與 GAS 專案屬性 ADMIN_TOKEN 相同
    GAS_URL      選填，預設讀 index.html 的 WEB_APP_URL

僅使用標準函式庫，無需 pip install。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

from cloud_relay.judicial import Judicial

HERE = Path(__file__).resolve().parent


def load_dotenv() -> None:
    """讀同目錄 .env（KEY=VALUE，已 gitignore / claspignore），不覆蓋既有環境變數。"""
    env = HERE / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


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


def _post_json(url: str, payload: dict, timeout: int = 300) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    # GAS doPost 回 302 → googleusercontent，urllib 會自動改用 GET 跟隨
    with urllib.request.urlopen(req, timeout=timeout) as res:
        text = res.read().decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"GAS 回應非 JSON: {text[:300]!r}") from e


def post_to_gas(url: str, token: str, general: list, buy: list) -> dict:
    return _post_json(
        url, {"action": "ingest", "token": token, "general": general, "buy": buy}
    )


def report_failure(url: str, token: str, error: str) -> None:
    """抓取失敗時請 GAS 寄告警信（GAS 本身連不到司法院，但收得到這裡的 POST）。"""
    try:
        res = _post_json(
            url, {"action": "report", "token": token, "error": error}, timeout=60
        )
        print("📮 已回報 GAS:", json.dumps(res, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001 — 回報失敗不可蓋掉原錯誤
        print(f"⚠️ 回報 GAS 失敗: {e}", file=sys.stderr)


def run(args: argparse.Namespace, token: str, gas_url: str) -> int:
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
        raise RuntimeError("兩類皆 0 筆，不送 GAS（避免覆蓋既有資料）")
    if args.dry_run:
        print("🧪 dry-run，不送 GAS")
        return 0

    res = post_to_gas(gas_url, token, general, buy)
    print("📨 GAS 回應:", json.dumps(res, ensure_ascii=False))
    if not res.get("ok"):
        raise RuntimeError(f"GAS ingest 未成功: {json.dumps(res, ensure_ascii=False)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="只抓取，不送 GAS")
    ap.add_argument("--dump", help="把原始資料另存成 JSON 檔（除錯用）")
    ap.add_argument("--log", help="輸出附加寫入此檔")
    args = ap.parse_args()

    if args.log:
        log_path = Path(args.log)
        if not log_path.is_absolute():
            log_path = HERE / log_path
        if log_path.exists() and log_path.stat().st_size > 1_000_000:
            log_path.replace(log_path.with_suffix(".old.log"))
        f = open(log_path, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stderr = f
    print(f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} relay_scrape 開始 =====")

    load_dotenv()
    token = os.environ.get("ADMIN_TOKEN", "").strip()
    if not args.dry_run and not token:
        print("❌ 缺少 ADMIN_TOKEN（環境變數或 .env）", file=sys.stderr)
        return 2
    gas_url = os.environ.get("GAS_URL", "").strip() or read_web_app_url()

    try:
        return run(args, token, gas_url)
    except Exception as e:  # noqa: BLE001 — 任何失敗都要回報後再以非 0 結束
        msg = f"{type(e).__name__}: {e}"
        print(f"❌ {msg}", file=sys.stderr)
        if not args.dry_run:
            report_failure(gas_url, token, msg)
        return 1


if __name__ == "__main__":
    sys.exit(main())
