#!/usr/bin/env python3
"""
🚨 此檔案已遷移至 .agent/scripts/validate_state_gate.py
此 shim 將在 3 周後移除（2026-02-09）

State Gate 驗證腳本現在支援雙 Index 架構：
- 專案功能開發 → doc/Implementation_Plan_index.md
- Workflow 改善 → .agent/Workflow_Plan_index.md

會根據 git staged 變更自動選擇正確的 Index 檔案。
"""

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    print("=" * 70)
    print("⚠️  警告：validate_state_gate.py 已遷移至 .agent/scripts/")
    print("    請更新你的引用路徑")
    print("    此 shim 將在 2026-02-09 後移除")
    print("=" * 70)
    print()

    # 執行新位置的腳本
    new_script = Path(__file__).parent.parent / ".agent" / "scripts" / "validate_state_gate.py"
    sys.argv[0] = str(new_script)
    runpy.run_path(str(new_script), run_name="__main__")
