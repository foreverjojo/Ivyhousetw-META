#!/usr/bin/env python3
"""
State Gate 驗證腳本

功能：
1. 驗證 Commit Message 格式（feat(Idx-NNN): ...）
2. 檢查 Index 是否存在於 Implementation_Plan_index.md
3. 驗證任務鎖一致性
4. 豁免規則：chore:, docs:, style:, ci:, build:, revert:
5. 解析 Plan 的 EXECUTION_BLOCK，強制工具一致性與小修正限制

基於五條鐵律中的 State Gate 原則
"""

import fnmatch
import re
import subprocess
import sys
from pathlib import Path

# Index 檔案會根據變更路徑自動選擇
PROJECT_INDEX_FILE = Path("doc/Implementation_Plan_index.md")
WORKFLOW_INDEX_FILE = Path(".agent/Workflow_Plan_index.md")
LOCK_FILE = Path(".agent/active_task.lock")

# Commit message 豁免類型（不需要 Index）
# 支援：
# - chore: <description>
# - chore(scope): <description>
EXEMPT_TYPES = [
    "chore",
    "docs",
    "style",
    "ci",
    "build",
    "revert",
]

EXEMPT_COMMIT_RE = re.compile(rf"^({'|'.join(EXEMPT_TYPES)})(\([^)]*\))?:")

# EXECUTION_BLOCK 必填欄位（不可為 placeholder）
REQUIRED_EXECUTION_BLOCK_FIELDS = [
    "executor_tool",
    "last_change_tool",
    "qa_tool",
    "qa_result",
]

# 可接受的 qa_result 值
VALID_QA_RESULTS = {"PASS", "PASS_WITH_RISK"}

# 預設小修正最大行數
DEFAULT_SMALL_FIX_MAX_LINES = 20

# 預設小修正允許路徑
DEFAULT_SMALL_FIX_GLOBS = ["doc/**", "README.md", "CHANGELOG.md", "CHECKLIST.md", "*.md"]


def detect_index_file():
    """
    根據 git staged 變更自動判斷要驗證哪一份 Index

    規則：
    - 若變更包含 .agent/** 路徑 → 驗證 .agent/Workflow_Plan_index.md
    - 否則 → 驗證 doc/Implementation_Plan_index.md

    Returns:
        Path: 要驗證的 Index 檔案路徑
    """
    try:
        # 取得 staged 變更的檔案清單
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # 無法取得 git 狀態，預設使用專案 Index
            print("⚠️  警告: 無法取得 git staged 檔案清單，使用預設 Index")
            return PROJECT_INDEX_FILE

        changed_files = result.stdout.strip().split("\n")
        changed_files = [f for f in changed_files if f]  # 過濾空行

        # 檢查是否有 .agent/ 開頭的檔案
        has_agent_changes = any(f.startswith(".agent/") for f in changed_files)

        if has_agent_changes:
            print("🔀 偵測到 .agent/ 變更，使用 Workflow Index")
            return WORKFLOW_INDEX_FILE
        else:
            print("🔀 偵測到專案檔案變更，使用 Project Index")
            return PROJECT_INDEX_FILE

    except Exception as e:
        print(f"⚠️  警告: 偵測變更檔案時發生錯誤: {e}")
        print("   使用預設 Project Index")
        return PROJECT_INDEX_FILE


def is_exempt_commit(message: str) -> bool:
    """檢查是否為豁免的 commit 類型"""
    return bool(EXEMPT_COMMIT_RE.match(message.strip()))


def extract_index(commit_message: str) -> str | None:
    """從 commit message 中提取 Index"""
    # 匹配格式：<type>(Idx-NNN): <description>
    pattern = r"\(Idx-(\d+)\):"
    match = re.search(pattern, commit_message)

    if match:
        return f"Idx-{match.group(1)}"
    return None


def check_index_exists(index: str, index_file: Path) -> bool:
    """檢查 Index 是否存在於指定的 Index 檔案中"""
    if not index_file.exists():
        print(f"❌ 錯誤: {index_file} 不存在")
        return False

    with open(index_file, encoding="utf-8") as f:
        content = f.read()

    # 檢查是否包含 Index（例如：| Idx-001 |）
    if f"| {index} |" in content or f"|{index}|" in content:
        return True

    return False


def check_index_duplication(index: str) -> tuple[bool, bool]:
    """檢查 Index 是否同時存在於兩份 Index（避免治理混淆）。"""
    in_project = check_index_exists(index, PROJECT_INDEX_FILE)
    in_workflow = check_index_exists(index, WORKFLOW_INDEX_FILE)
    return in_project, in_workflow


def check_lock_consistency(index: str) -> bool | None:
    """檢查任務鎖一致性"""
    if not LOCK_FILE.exists():
        print("⚠️  警告: 沒有活動的任務鎖")
        print("   建議先執行: python scripts/check_active_task.py acquire <index>")
        return None  # 警告但不阻擋

    import json

    try:
        with open(LOCK_FILE, encoding="utf-8") as f:
            lock_data = json.load(f)

        if lock_data["index"] != index:
            print("❌ 錯誤: 任務鎖不一致")
            print(f"   Commit Index: {index}")
            print(f"   鎖定 Index: {lock_data['index']}")
            return False

        return True

    except (json.JSONDecodeError, KeyError):
        print("⚠️  警告: 任務鎖檔案格式錯誤")
        return None


def find_plan_file(index: str, index_file: Path) -> Path | None:
    """
    從 Index 檔案解析對應 Plan 路徑

    支援格式：
    - Plan：`.agent/plans/Idx-NNN_plan.md`
    - Plan：`doc/plans/Idx-NNN_plan.md`
    - 表格欄位中含 .agent/plans/ 或 doc/plans/ 的連結
    - 直接在行內出現 .agent/plans/Idx-NNN_plan.md

    Args:
        index: 例如 "Idx-041"
        index_file: Index 檔案路徑

    Returns:
        Path 或 None（若找不到）
    """
    if not index_file.exists():
        return None

    with open(index_file, encoding="utf-8") as f:
        content = f.read()

    # 先找包含此 index 的行
    target_lines = []
    for line in content.splitlines():
        if index in line:
            target_lines.append(line)

    if not target_lines:
        return None

    # 常見格式嘗試（從精確到寬鬆）
    plan_patterns = [
        # 明確寫出 Plan：`path` 格式
        r"Plan[：:]\s*[`'\"]?([^\s`'\"]+\.md)[`'\"]?",
        # 表格欄位裡的路徑（含 Markdown 連結語法）
        r"\[?`?([^\[\]`\s]+Idx-\d+[^\[\]`\s]*\.md)`?\]?",
        # 直接路徑
        r"((?:\.agent/plans|doc/plans)/[^\s|`'\",]+\.md)",
    ]

    for line in target_lines:
        for pat in plan_patterns:
            m = re.search(pat, line, re.IGNORECASE)
            if m:
                plan_path_str = m.group(1).strip("`'\"\\ ")
                plan_path = Path(plan_path_str)
                if plan_path.exists():
                    return plan_path
                # 若相對路徑不存在，嘗試兩個常見根路徑
                for prefix in [".agent/plans", "doc/plans"]:
                    candidate = Path(prefix) / plan_path.name
                    if candidate.exists():
                        return candidate

    # fallback：根據 index 推斷可能的路徑
    index_num = index.replace("Idx-", "")
    for candidate_dir in [".agent/plans", "doc/plans"]:
        for plan_path in (
            Path(candidate_dir).glob(f"Idx-{index_num}*.md") if Path(candidate_dir).exists() else []
        ):
            return plan_path

    return None


def parse_execution_block(plan_path: Path) -> dict[str, str]:
    """
    解析 Plan 檔案中 EXECUTION_BLOCK 區段的 key:value 欄位

    Args:
        plan_path: Plan 文件路徑

    Returns:
        dict，key 為欄位名稱，value 為欄位值（字串）
    """
    if not plan_path.exists():
        return {}

    with open(plan_path, encoding="utf-8") as f:
        content = f.read()

    # 提取 EXECUTION_BLOCK 區段
    block_pattern = re.compile(
        r"<!--\s*EXECUTION_BLOCK_START\s*-->(.*?)<!--\s*EXECUTION_BLOCK_END\s*-->",
        re.DOTALL,
    )
    block_match = block_pattern.search(content)
    if not block_match:
        return {}

    block_text = block_match.group(1)
    fields: dict[str, str] = {}

    # 解析 key: value 格式（忽略以 # 開頭的註釋行）
    field_pattern = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.+)$")
    for line in block_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = field_pattern.match(line)
        if m:
            key = m.group(1)
            value = m.group(2).strip()
            fields[key] = value

    return fields


def is_placeholder(value: str) -> bool:
    """
    判斷欄位值是否為 placeholder（未填寫）

    placeholder 的特徵：
    - 以 [ 開頭或包含 [TBD]、[TBD|...]
    - 值為空字串
    - 包含 "TBD"（case-insensitive）
    - 值為 "pending"（視為尚未完成）

    Returns:
        True 表示為 placeholder，需要填寫
    """
    v = value.strip()
    if not v:
        return True
    if v.startswith("[") and v.endswith("]"):
        return True
    if "[TBD" in v.upper() or "TBD" == v.upper():
        return True
    # "pending" 在 commit_hash 欄位是正常的，但在 executor_tool 等欄位代表未填
    # 不把 "pending" 視為 placeholder，因為 commit_hash: pending 是合法狀態
    return False


def get_staged_diff_stats() -> tuple[int, list[str]]:
    """
    取得 staged 變更的行數與檔案清單

    Returns:
        (總行數, 檔案清單)
    """
    # 取得 staged 檔案清單
    files_result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    staged_files: list[str] = []
    if files_result.returncode == 0:
        staged_files = [f for f in files_result.stdout.strip().split("\n") if f]

    # 計算 staged 變更行數
    numstat_result = subprocess.run(
        ["git", "diff", "--cached", "--numstat"],
        capture_output=True,
        text=True,
        check=False,
    )
    total_lines = 0
    if numstat_result.returncode == 0:
        for line in numstat_result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    added = int(parts[0]) if parts[0] != "-" else 0
                    deleted = int(parts[1]) if parts[1] != "-" else 0
                    total_lines += added + deleted
                except ValueError:
                    pass

    return total_lines, staged_files


def check_paths_match_globs(files: list[str], globs: list[str]) -> list[str]:
    """
    檢查哪些檔案不符合任何 glob 規則

    Args:
        files: 檔案路徑清單
        globs: glob pattern 清單（例如 ["doc/**", "*.md"]）

    Returns:
        不符合任何 glob 的檔案清單
    """
    violations: list[str] = []
    for file_path in files:
        matched = False
        for pattern in globs:
            if fnmatch.fnmatch(file_path, pattern):
                matched = True
                break
            # 嘗試只匹配檔名（basename）
            basename = Path(file_path).name
            if fnmatch.fnmatch(basename, pattern):
                matched = True
                break
        if not matched:
            violations.append(file_path)
    return violations


def parse_allowed_path_globs(raw_value: str) -> list[str]:
    """
    解析 copilot_chat_allowed_path_globs 欄位的值

    支援：
    - JSON 格式：["doc/**", "README.md"]
    - 逗號分隔：doc/**, README.md
    """
    raw = raw_value.strip()
    if raw.startswith("["):
        # 嘗試 JSON 解析
        import json

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(g).strip() for g in parsed]
        except json.JSONDecodeError:
            pass
        # 退而求其次：移除括號後逗號分隔
        raw = raw.strip("[]")

    return [g.strip().strip("\"'") for g in raw.split(",") if g.strip().strip("\"'")]


def check_execution_block(index: str, index_file: Path) -> bool:
    """
    核心函式：解析 Plan 的 EXECUTION_BLOCK 並執行工具一致性 / 小修正限制檢查

    僅對含 Idx-NNN 的非豁免提交執行。

    AC#3-5 的實作：
    - AC#3：必填欄位不可為 placeholder
    - AC#4：executor_tool=opencode|codex-cli 時，last_change_tool 必須一致，qa_tool 必須不同且 qa_result 必須通過
    - AC#5：executor_tool=copilot-chat 時，小修正限制驗證

    Returns:
        True 表示通過，False 表示阻擋 commit
    """
    # 找 Plan 檔
    plan_path = find_plan_file(index, index_file)
    if plan_path is None:
        print(f"❌ 錯誤: 找不到 {index} 對應的 Plan 檔案")
        print(f"   請確認 {index_file} 中有記錄 Plan 路徑，或 Plan 檔案確實存在")
        print("   可行動步驟：在 Index 的備註欄位加入「Plan：`.agent/plans/Idx-NNN_plan.md`」")
        return False

    print(f"📄 找到 Plan 檔: {plan_path}")

    # 解析 EXECUTION_BLOCK
    fields = parse_execution_block(plan_path)
    if not fields:
        print(f"❌ 錯誤: {plan_path} 缺少 EXECUTION_BLOCK 或格式不正確")
        print(
            "   可行動步驟：確認 Plan 包含 <!-- EXECUTION_BLOCK_START --> ... <!-- EXECUTION_BLOCK_END -->"
        )
        return False

    # AC#3：必填欄位不可為 placeholder
    missing_fields: list[str] = []
    for field in REQUIRED_EXECUTION_BLOCK_FIELDS:
        value = fields.get(field, "")
        if not value or is_placeholder(value):
            missing_fields.append(field)

    if missing_fields:
        print("❌ 錯誤: EXECUTION_BLOCK 必填欄位尚未回填（仍為 placeholder）")
        for field in missing_fields:
            raw_val = fields.get(field, "(缺漏)")
            print(f"   - {field}: {raw_val}")
        print()
        print("   可行動步驟：在 Plan 的 EXECUTION_BLOCK 填入實際值（不可留 [TBD] 或 placeholder）")
        return False

    executor_tool = fields.get("executor_tool", "").lower().strip()
    last_change_tool = fields.get("last_change_tool", "").lower().strip()
    qa_tool = fields.get("qa_tool", "").lower().strip()
    qa_result = fields.get("qa_result", "").upper().strip()

    print(f"   executor_tool:    {executor_tool}")
    print(f"   last_change_tool: {last_change_tool}")
    print(f"   qa_tool:          {qa_tool}")
    print(f"   qa_result:        {qa_result}")

    # AC#4：executor_tool=opencode|codex-cli 的規則
    if executor_tool in ("opencode", "codex-cli"):
        ok = True

        # last_change_tool 必須等於 executor_tool
        if last_change_tool != executor_tool:
            print()
            print("❌ 錯誤: 工具不一致（executor_tool 與 last_change_tool 不符）")
            print(f"   Plan 指定 executor_tool={executor_tool}")
            print(f"   但 last_change_tool={last_change_tool}")
            if last_change_tool == "copilot-chat":
                print()
                print("   原因：你選了 opencode/codex-cli 作為 executor，")
                print("   但 last_change_tool 是 copilot-chat，代表實際修改工具不一致。")
                print("   → 請用 opencode/codex-cli 執行修改並回填 last_change_tool，")
                print("     或改選 executor_tool=copilot-chat（需滿足小修正條件）。")
            ok = False

        # qa_tool 必須存在且不等於 last_change_tool（Cross-QA）
        if not qa_tool or is_placeholder(qa_tool):
            print()
            print("❌ 錯誤: qa_tool 未填寫（Cross-QA 必須指定 QA 工具）")
            ok = False
        elif qa_tool == last_change_tool:
            print()
            print("❌ 錯誤: Cross-QA 規則違反（qa_tool == last_change_tool）")
            print(f"   qa_tool={qa_tool}，last_change_tool={last_change_tool}")
            print("   可行動步驟：選擇與 last_change_tool 不同的 qa_tool")
            ok = False

        # qa_result 必須是 PASS 或 PASS_WITH_RISK
        if qa_result not in VALID_QA_RESULTS:
            print()
            print(f"❌ 錯誤: qa_result={qa_result} 不合格（必須是 PASS 或 PASS_WITH_RISK）")
            print("   可行動步驟：完成 QA 並確認 qa_result 填入正確值後再 commit")
            ok = False

        if ok:
            print()
            print("✅ EXECUTION_BLOCK 工具一致性驗證通過（executor_tool=opencode|codex-cli）")
        return ok

    # AC#5：executor_tool=copilot-chat 的規則
    elif executor_tool == "copilot-chat":
        ok = True

        # copilot_chat_small_fix_allowed 必須為 true
        small_fix_allowed = fields.get("copilot_chat_small_fix_allowed", "").lower().strip()
        if small_fix_allowed != "true":
            print()
            print("❌ 錯誤: executor_tool=copilot-chat 但 copilot_chat_small_fix_allowed 不是 true")
            print(f"   copilot_chat_small_fix_allowed={small_fix_allowed}")
            print("   可行動步驟：在 EXECUTION_BLOCK 明確填入 copilot_chat_small_fix_allowed: true")
            ok = False

        # 解析允許的路徑 glob
        raw_globs = fields.get("copilot_chat_allowed_path_globs", "")
        allowed_globs = (
            parse_allowed_path_globs(raw_globs)
            if raw_globs and not is_placeholder(raw_globs)
            else DEFAULT_SMALL_FIX_GLOBS
        )

        # 解析最大行數
        max_lines_raw = fields.get(
            "copilot_chat_max_changed_lines", str(DEFAULT_SMALL_FIX_MAX_LINES)
        )
        try:
            max_lines = int(max_lines_raw)
        except ValueError:
            max_lines = DEFAULT_SMALL_FIX_MAX_LINES

        # 取得 staged 變更資訊
        total_lines, staged_files = get_staged_diff_stats()

        # 檢查行數限制
        if total_lines > max_lines:
            print()
            print(f"❌ 錯誤: staged 變更行數 {total_lines} 超過小修正上限 {max_lines}")
            print(f"   copilot_chat_max_changed_lines={max_lines}")
            print(f"   實際變更行數（add+del）={total_lines}")
            print("   可行動步驟：縮減變更範圍，或改選 opencode/codex-cli 作為 executor_tool")
            ok = False

        # 檢查路徑限制
        violations = check_paths_match_globs(staged_files, allowed_globs)
        if violations:
            print()
            print("❌ 錯誤: 部分 staged 檔案不符合 copilot_chat_allowed_path_globs")
            print(f"   允許路徑: {allowed_globs}")
            print("   違規檔案:")
            for vf in violations:
                print(f"   - {vf}")
            print("   可行動步驟：移除違規檔案的變更，或改選 opencode/codex-cli 作為 executor_tool")
            ok = False

        # qa_result 仍需 PASS 或 PASS_WITH_RISK
        if qa_result not in VALID_QA_RESULTS:
            print()
            print(f"❌ 錯誤: qa_result={qa_result} 不合格（即使是小修正，仍需 QA 通過）")
            print("   可行動步驟：完成 QA 並填入 qa_result: PASS 或 PASS_WITH_RISK")
            ok = False

        if ok:
            print()
            print(
                f"✅ EXECUTION_BLOCK 小修正驗證通過（executor_tool=copilot-chat，行數={total_lines}/{max_lines}）"
            )
        return ok

    else:
        # 未知 executor_tool，視為 placeholder 未填
        print()
        print(f"❌ 錯誤: executor_tool={executor_tool} 不是有效值")
        print("   有效值：codex-cli, opencode, copilot-chat")
        return False


def validate_commit_message(message: str, index_file: Path) -> bool:
    """驗證 commit message"""
    print(f"🔍 驗證 Commit Message: {message[:80]}...")
    print()

    # 檢查豁免
    if is_exempt_commit(message):
        print("✅ 豁免類型，跳過 Index 檢查")
        m = EXEMPT_COMMIT_RE.match(message.strip())
        commit_type = m.group(1) if m else message.split(":")[0]
        print(f"   類型: {commit_type}")
        return True

    # 提取 Index
    index = extract_index(message)
    if not index:
        print("❌ 錯誤: Commit message 格式錯誤")
        print()
        print("正確格式：")
        print("  <type>(Idx-NNN): <description>")
        print()
        print("範例：")
        print("  feat(Idx-001): 實作新功能")
        print("  fix(Idx-002): 修復 bug")
        print()
        print("或使用豁免前綴：")
        for t in EXEMPT_TYPES:
            print(f"  {t}: <description>")
            print(f"  {t}(scope): <description>")
        return False

    print(f"✅ Index 格式正確: {index}")

    # 檢查 Index 是否同時存在於兩份 Index（屬於治理錯誤，必須先解掉）
    in_project, in_workflow = check_index_duplication(index)
    if in_project and in_workflow:
        print("❌ 錯誤: Index 同時存在於兩份 Index（治理混淆）")
        print(f"   - {PROJECT_INDEX_FILE}: ✅ 存在")
        print(f"   - {WORKFLOW_INDEX_FILE}: ✅ 存在")
        print()
        print("請先移除其中一份（依 doc/FILE_OWNERSHIP.md 的領域歸屬規則）。")
        return False

    # 檢查 Index 存在性（依 staged 路徑選擇的 index_file）
    if check_index_exists(index, index_file):
        print(f"✅ Index 存在於 {index_file.name}")
    else:
        other_index_file = (
            WORKFLOW_INDEX_FILE if index_file == PROJECT_INDEX_FILE else PROJECT_INDEX_FILE
        )

        # 如果 Index 存在於另一份 Index，代表 staged 路徑與 Index 領域不一致
        if check_index_exists(index, other_index_file):
            print("❌ 錯誤: Index 存在於另一份 Index，代表領域不一致")
            print(f"   State Gate 選擇 Index: {index_file}")
            print(f"   但 {index} 實際存在於: {other_index_file}")
            print()
            print("建議修正方式（二選一）：")
            print("  1) 將本次變更拆成兩個 commit（workflow vs project 分離）")
            print("  2) 改用正確領域的 Index，或改用豁免前綴（例如 chore: / docs:）")
            return False

        # Index 在兩份 Index 都不存在
        print(f"❌ 錯誤: {index} 不存在於 {index_file}")
        print()
        print(f"請先在 {index_file} 中註冊此 Index")
        return False

    # 檢查鎖一致性
    lock_check = check_lock_consistency(index)
    if lock_check is False:
        return False
    elif lock_check is True:
        print("✅ 任務鎖一致")
    # lock_check is None：警告但不阻擋

    # EXECUTION_BLOCK 工具一致性 / 小修正限制檢查（AC#3-5）
    print()
    print("🔒 檢查 EXECUTION_BLOCK 工具一致性...")
    if not check_execution_block(index, index_file):
        return False

    print()
    print("🎉 State Gate 驗證通過！")
    return True


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("用法:")
        print('  python scripts/validate_state_gate.py "feat(Idx-001): 描述"')
        print()
        print("或在 commit-msg hook 中使用（傳入 commit message 檔案路徑）：")
        print("  python scripts/validate_state_gate.py .git/COMMIT_EDITMSG")
        sys.exit(1)

    # 自動偵測要使用的 Index 檔案
    index_file = detect_index_file()
    print(f"📋 使用 Index: {index_file}")
    print()

    arg = sys.argv[1]
    commit_message = arg
    msg_path = Path(arg)
    if msg_path.exists() and msg_path.is_file():
        commit_message = msg_path.read_text(encoding="utf-8", errors="replace").strip()

    if validate_commit_message(commit_message, index_file):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
