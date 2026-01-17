# -*- coding: utf-8 -*-
"""建立蝦皮 Golden Test 檔案"""

import sys

sys.path.insert(0, ".")
from scripts.adapters.shopee_adapter import adapt_shopee_ad_csv
from pathlib import Path
import json

# 建立 golden test 輸入 (取前 3 筆資料的 CSV)
csv_path = Path("examples/蝦皮廣告-總體-數據-2025_12_04-2025_12_09.csv")

# 讀取原始檔案的 header + 前 3 筆資料
with open(csv_path, "r", encoding="utf-8-sig") as f:
    lines = f.readlines()

# 取 metadata (前7行) + header (第8行) + 前3筆資料 (第9-11行)
sample_lines = lines[:7] + [lines[7]] + lines[8:11]

# 寫入 golden test 輸入
golden_input = Path("tests/golden/shopee_sample_input.csv")
with open(golden_input, "w", encoding="utf-8-sig") as f:
    f.writelines(sample_lines)

print(f"已建立: {golden_input}")
print(f"行數: {len(sample_lines)}")

# 轉換並產生 expected output
result = adapt_shopee_ad_csv(golden_input)
result["generated_at"] = "1970-01-01T00:00:00+00:00"  # 固定時間戳
result["__comment"] = "檔案用途：Shopee Adapter Golden Test 預期輸出"

golden_output = Path("tests/golden/shopee_expected_output.json")
with open(golden_output, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"已建立: {golden_output}")
print(f"資料筆數: {len(result['data'])}")
