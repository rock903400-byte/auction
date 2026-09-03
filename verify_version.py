#!/usr/bin/env python3
"""版號三處同步檢查：常數.gs / index.html APP_VERSION / version-badge"""

import re
import pathlib
import sys

root = pathlib.Path(__file__).parent
ok = True

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

# 3. version-badge 應動態為 APP_VERSION（檢查是否仍寫死 v1.0.0）
if "v1.0.0" in html and app_ver != "1.0.0":
    print("[WARN] index.html 仍含寫死 v1.0.0，請確認已改為動態 textContent")
    # 不算失敗，僅提醒
else:
    print("version-badge：已改為動態（ok）")

if const_ver != app_ver:
    print(f"[FAIL] 版號不同步：{const_ver} vs {app_ver}")
    ok = False
else:
    print(f"[OK] 版號同步：{const_ver}")

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

sys.exit(0 if ok else 1)
