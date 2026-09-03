#!/usr/bin/env python3
"""版號與 90+ 門檻檢查：常數.gs / index.html / 後端 / 前端安全 / 部署"""

import re
import pathlib
import sys

root = pathlib.Path(__file__).parent
ok = True
strict = "--strict" in sys.argv

# 1. 常數.gs
const_gs = (root / "常數.gs").read_text(encoding="utf-8")
m = re.search(r'CONST_VERSION\s*=\s*"(.*?)"', const_gs)
const_ver = m.group(1) if m else None
print(f"常數.gs CONST_VERSION = {const_ver}")

# 2. index.html APP_VERSION
html = (root / "index.html").read_text(encoding="utf-8")
m2 = re.search(r"var\s+APP_VERSION\s*=\s*'(.*?)'", html)
app_ver = m2.group(1) if m2 else None
print(f"index.html APP_VERSION = {app_ver}")

# 3. version-badge 閉環
if "v1.0.0" in html and app_ver != "1.0.0":
    print("[WARN] index.html 仍含寫死 v1.0.0，請確認已改為動態 textContent")
else:
    print("version-badge：已改為動態（ok）")

# 3b. 嚴格：badge 靜態文本必須等於 APP_VERSION
if strict:
    m_badge = re.search(
        r'<span[^>]*id="version-badge"[^>]*>(.*?)</span>', html, re.DOTALL
    )
    badge_text = m_badge.group(1).strip() if m_badge else ""
    expected = f"v{app_ver}" if app_ver else ""
    if badge_text != expected:
        print(f"[FAIL] badge 文本 {badge_text!r} != 預期 {expected!r}")
        ok = False
    else:
        print(f"[OK] badge 文本閉環：{badge_text}")

if const_ver != app_ver:
    print(f"[FAIL] 版號不同步：{const_ver} vs {app_ver}")
    ok = False
else:
    print(f"[OK] 版號同步：{const_ver}")

# 3c. 嚴格：WEB_APP_URL 必須為 exec 格式且非空
if strict:
    m_url = re.search(r"var\s+WEB_APP_URL\s*=\s*'(.*?)'", html)
    url = m_url.group(1) if m_url else ""
    if not url or "script.google.com/macros/s/" not in url or not url.endswith("/exec"):
        print(f"[FAIL] WEB_APP_URL 格式錯誤或為空：{url!r}")
        ok = False
    else:
        print(f"[OK] WEB_APP_URL 格式正確：{url[:60]}...")

# 4. 檢查後端是否回傳 total
backend = (root / "後端.gs").read_text(encoding="utf-8")
if "totalGeneral" in backend and "totalSpecial" in backend:
    print("[OK] 後端已回傳 totalGeneral/totalSpecial")
else:
    print("[FAIL] 後端未回傳 total")
    ok = False

# 5. 檢查 ADMIN_TOKEN
if "ADMIN_TOKEN" in backend:
    print("[OK] 後端 ADMIN_TOKEN 鑑權已加入")
else:
    print("[FAIL] 缺少 ADMIN_TOKEN")
    ok = False

# 6. 前端安全：esc / isSafeUrl / data-addr
for kw in ["function esc(", "function isSafeUrl(", 'data-addr="', "getRoleLimit"]:
    if kw in html:
        print(f"[OK] 前端含 {kw.strip()}")
    else:
        print(f"[FAIL] 前端缺少 {kw.strip()}")
        ok = False

# 7. live_site DEPRECATED
live = (root / "live_site.html").read_text(encoding="utf-8")
if "DEPRECATED" in live:
    print("[OK] live_site.html 已標 DEPRECATED 凍結")
elif strict:
    print("[FAIL] live_site.html 未標 DEPRECATED")
    ok = False

# 8. debug 分支：isGeneral
general_gs = (root / "法拍清單(一般).gs").read_text(encoding="utf-8")
if "var isGeneral" in general_gs and "應買無此過濾" in general_gs:
    print("[OK] debugFilterCounts 已依 saletype 分支")
elif strict:
    print("[FAIL] debugFilterCounts 未分支 isGeneral")
    ok = False

# 9. .clasp.json 檢查（strict）
if strict:
    import json

    try:
        clasp = json.loads((root / ".clasp.json").read_text(encoding="utf-8"))
        if clasp.get("rootDir") != ".":
            print(
                f"[FAIL] .clasp.json rootDir 應為 \".\"，目前 {clasp.get('rootDir')!r}"
            )
            ok = False
        else:
            print('[OK] .clasp.json rootDir 為 "."')
    except Exception as e:
        print(f"[WARN] 無法檢查 .clasp.json：{e}")

    claspignore = root / ".claspignore"
    if not claspignore.exists():
        print("[FAIL] 缺少 .claspignore")
        ok = False
    else:
        print("[OK] .claspignore 存在")

sys.exit(0 if ok else 1)
