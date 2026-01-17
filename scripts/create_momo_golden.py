# -*- coding: utf-8 -*-
"""建立 MOMO Golden Test 檔案"""

import sys

sys.path.insert(0, ".")
from scripts.adapters.momo_adapter import adapt_momo_ad_report
from pathlib import Path
import json

# MOMO Golden Test 輸入 (已由前一步驟從 xlsx 轉為 csv)
csv_input = Path("tests/golden/momo_sample_input.csv")

if not csv_input.exists():
    print(f"錯誤：找不到輸入檔案 {csv_input}")
    sys.exit(1)

print(f"讀取輸入: {csv_input}")

# 轉換並產生 expected output
result = adapt_momo_ad_report(csv_input)
result["generated_at"] = "1970-01-01T00:00:00+00:00"  # 固定時間戳
result["__comment"] = "檔案用途：MOMO Adapter Golden Test 預期輸出"

golden_output = Path("tests/golden/momo_expected_output.json")
with open(golden_output, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"已建立: {golden_output}")
print(f"資料筆數: {len(result['data'])}")
