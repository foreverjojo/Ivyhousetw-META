"""
tests/test_validate_state_gate.py

State Gate 驗證腳本的測試套件，覆蓋：
- Index 領域不一致（存在另一份 Index）
- Index 重複（治理混淆）
- Index 存在且正確通過
- 豁免 commit 類型
- executor_tool=copilot-chat 超行數 → FAIL
- executor_tool=copilot-chat 路徑違規 → FAIL
- executor_tool=opencode 但 last_change_tool=copilot-chat → FAIL
- executor_tool=opencode，Cross-QA 違反（qa_tool==last_change_tool）→ FAIL
- executor_tool=opencode，qa_result=FAIL → FAIL
- EXECUTION_BLOCK 缺漏（找不到 Plan）→ FAIL
- executor_tool=copilot-chat 正常通過（行數/路徑合規）
"""

import importlib.util
import textwrap
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_validate_state_gate_module():
    """動態載入 validate_state_gate 模組"""
    module_path = REPO_ROOT / ".agent" / "scripts" / "validate_state_gate.py"
    spec = importlib.util.spec_from_file_location("validate_state_gate", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_index_file(path: Path, indices: list[str]) -> None:
    """建立測試用 Index 檔案，每個 index 一行表格列"""
    rows = [
        f"| {idx} | title | P2 | ✅ 已完成 | Manual | PASS | 1.0.0 | log | note |"
        for idx in indices
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_index_with_plan(path: Path, idx: str, plan_path: str) -> None:
    """建立帶有 Plan 路徑的 Index 檔案"""
    row = f"| {idx} | title | P2 | ✅ 已完成 | Manual | PASS | 1.0.0 | log | Plan：`{plan_path}` |"
    path.write_text(row + "\n", encoding="utf-8")


def write_plan_with_block(path: Path, block_content: str) -> None:
    """建立帶有 EXECUTION_BLOCK 的 Plan 檔案"""
    content = textwrap.dedent(f"""\
        # 測試 Plan

        <!-- EXECUTION_BLOCK_START -->
        {block_content}
        <!-- EXECUTION_BLOCK_END -->

        ## 📋 SPEC
        測試用 Plan 內容
    """)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# 原有測試（保留）
# ---------------------------------------------------------------------------


def test_state_gate_fails_when_index_in_other_index(capsys, tmp_path):
    """Index 存在於另一份 Index，應判定為領域不一致並 FAIL"""
    m = load_validate_state_gate_module()

    project_index = tmp_path / "project_index.md"
    workflow_index = tmp_path / "workflow_index.md"
    write_index_file(project_index, ["Idx-001"])
    write_index_file(workflow_index, ["Idx-019"])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    ok = m.validate_commit_message("feat(Idx-019): test", project_index)
    assert ok is False
    out = capsys.readouterr().out
    assert "代表領域不一致" in out


def test_state_gate_fails_on_duplicate_index(capsys, tmp_path):
    """Index 同時存在於兩份 Index，應判定為治理混淆並 FAIL"""
    m = load_validate_state_gate_module()

    project_index = tmp_path / "project_index.md"
    workflow_index = tmp_path / "workflow_index.md"
    write_index_file(project_index, ["Idx-019"])
    write_index_file(workflow_index, ["Idx-019"])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    ok = m.validate_commit_message("feat(Idx-019): test", project_index)
    assert ok is False
    out = capsys.readouterr().out
    assert "治理混淆" in out


def test_state_gate_passes_when_index_in_selected_index(tmp_path):
    """Index 存在且有合格的 EXECUTION_BLOCK，應通過"""
    m = load_validate_state_gate_module()

    project_index = tmp_path / "project_index.md"
    workflow_index = tmp_path / "workflow_index.md"

    plan_file = tmp_path / "Idx-019_plan.md"
    write_plan_with_block(
        plan_file,
        textwrap.dedent("""\
            executor_tool: opencode
            last_change_tool: opencode
            qa_tool: codex-cli
            qa_result: PASS
        """),
    )
    write_index_with_plan(project_index, "Idx-019", str(plan_file))
    write_index_file(workflow_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    ok = m.validate_commit_message("feat(Idx-019): test", project_index)
    assert ok is True


def test_state_gate_allows_scoped_exempt_commit(tmp_path):
    """豁免 commit 類型（chore(scope)：...）應直接通過，不做 Index 檢查"""
    m = load_validate_state_gate_module()

    project_index = tmp_path / "project_index.md"
    workflow_index = tmp_path / "workflow_index.md"
    write_index_file(project_index, [])
    write_index_file(workflow_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    ok = m.validate_commit_message("chore(service_manager): tweak PTY wrapper", project_index)
    assert ok is True


# ---------------------------------------------------------------------------
# 新增測試：AC#4 - executor_tool=opencode 但 last_change_tool=copilot-chat
# ---------------------------------------------------------------------------


def test_state_gate_fails_opencode_but_last_change_tool_is_copilot_chat(capsys, tmp_path):
    """
    AC#4：executor_tool=opencode 但 last_change_tool=copilot-chat
    → State Gate 應阻擋 commit（工具不一致）
    """
    m = load_validate_state_gate_module()

    plan_file = tmp_path / "Idx-099_plan.md"
    write_plan_with_block(
        plan_file,
        textwrap.dedent("""\
            executor_tool: opencode
            last_change_tool: copilot-chat
            qa_tool: codex-cli
            qa_result: PASS
        """),
    )

    workflow_index = tmp_path / "workflow_index.md"
    project_index = tmp_path / "project_index.md"
    write_index_with_plan(workflow_index, "Idx-099", str(plan_file))
    write_index_file(project_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    ok = m.validate_commit_message("feat(Idx-099): test opencode tool mismatch", workflow_index)
    assert ok is False
    out = capsys.readouterr().out
    assert "工具不一致" in out or "last_change_tool" in out


def test_state_gate_fails_codex_but_last_change_tool_is_copilot_chat(capsys, tmp_path):
    """
    AC#4：executor_tool=codex-cli 但 last_change_tool=copilot-chat
    → State Gate 應阻擋 commit（工具不一致）
    """
    m = load_validate_state_gate_module()

    plan_file = tmp_path / "Idx-098_plan.md"
    write_plan_with_block(
        plan_file,
        textwrap.dedent("""\
            executor_tool: codex-cli
            last_change_tool: copilot-chat
            qa_tool: opencode
            qa_result: PASS
        """),
    )

    workflow_index = tmp_path / "workflow_index.md"
    project_index = tmp_path / "project_index.md"
    write_index_with_plan(workflow_index, "Idx-098", str(plan_file))
    write_index_file(project_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    ok = m.validate_commit_message("feat(Idx-098): test codex-cli tool mismatch", workflow_index)
    assert ok is False
    out = capsys.readouterr().out
    assert "工具不一致" in out or "last_change_tool" in out


def test_state_gate_fails_cross_qa_violation(capsys, tmp_path):
    """
    AC#4：executor_tool=opencode，qa_tool == last_change_tool（Cross-QA 違反）
    → State Gate 應阻擋 commit
    """
    m = load_validate_state_gate_module()

    plan_file = tmp_path / "Idx-097_plan.md"
    write_plan_with_block(
        plan_file,
        textwrap.dedent("""\
            executor_tool: opencode
            last_change_tool: opencode
            qa_tool: opencode
            qa_result: PASS
        """),
    )

    workflow_index = tmp_path / "workflow_index.md"
    project_index = tmp_path / "project_index.md"
    write_index_with_plan(workflow_index, "Idx-097", str(plan_file))
    write_index_file(project_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    ok = m.validate_commit_message("feat(Idx-097): test cross-qa violation", workflow_index)
    assert ok is False
    out = capsys.readouterr().out
    assert "Cross-QA" in out


def test_state_gate_fails_qa_result_fail(capsys, tmp_path):
    """
    AC#4：qa_result=FAIL → State Gate 應阻擋 commit
    """
    m = load_validate_state_gate_module()

    plan_file = tmp_path / "Idx-096_plan.md"
    write_plan_with_block(
        plan_file,
        textwrap.dedent("""\
            executor_tool: opencode
            last_change_tool: opencode
            qa_tool: codex-cli
            qa_result: FAIL
        """),
    )

    workflow_index = tmp_path / "workflow_index.md"
    project_index = tmp_path / "project_index.md"
    write_index_with_plan(workflow_index, "Idx-096", str(plan_file))
    write_index_file(project_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    ok = m.validate_commit_message("feat(Idx-096): test qa_result fail", workflow_index)
    assert ok is False
    out = capsys.readouterr().out
    assert "qa_result" in out


# ---------------------------------------------------------------------------
# 新增測試：AC#5 - executor_tool=copilot-chat 小修正規則
# ---------------------------------------------------------------------------


def test_state_gate_fails_copilot_chat_exceeds_max_lines(capsys, tmp_path):
    """
    AC#5：executor_tool=copilot-chat 且 staged 變更行數超過上限
    → State Gate 應阻擋 commit
    """
    m = load_validate_state_gate_module()

    plan_file = tmp_path / "Idx-095_plan.md"
    write_plan_with_block(
        plan_file,
        textwrap.dedent("""\
            executor_tool: copilot-chat
            last_change_tool: copilot-chat
            qa_tool: codex-cli
            qa_result: PASS
            copilot_chat_small_fix_allowed: true
            copilot_chat_small_fix_reason: 小修正文件
            copilot_chat_max_changed_lines: 20
            copilot_chat_allowed_path_globs: ["doc/**", "README.md", "*.md"]
        """),
    )

    workflow_index = tmp_path / "workflow_index.md"
    project_index = tmp_path / "project_index.md"
    write_index_with_plan(workflow_index, "Idx-095", str(plan_file))
    write_index_file(project_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    # Mock get_staged_diff_stats：回傳超過 20 行的結果（行數 25，只有合規路徑）
    with mock.patch.object(m, "get_staged_diff_stats", return_value=(25, ["doc/README.md"])):
        ok = m.validate_commit_message("feat(Idx-095): test copilot-chat max lines", workflow_index)

    assert ok is False
    out = capsys.readouterr().out
    assert "超過小修正上限" in out or "max_changed_lines" in out or "行數" in out


def test_state_gate_fails_copilot_chat_path_violation(capsys, tmp_path):
    """
    AC#5：executor_tool=copilot-chat 且 staged 檔案包含不符合 glob 的路徑
    → State Gate 應阻擋 commit
    """
    m = load_validate_state_gate_module()

    plan_file = tmp_path / "Idx-094_plan.md"
    write_plan_with_block(
        plan_file,
        textwrap.dedent("""\
            executor_tool: copilot-chat
            last_change_tool: copilot-chat
            qa_tool: codex-cli
            qa_result: PASS
            copilot_chat_small_fix_allowed: true
            copilot_chat_small_fix_reason: 文件修正
            copilot_chat_max_changed_lines: 20
            copilot_chat_allowed_path_globs: ["doc/**", "README.md", "*.md"]
        """),
    )

    workflow_index = tmp_path / "workflow_index.md"
    project_index = tmp_path / "project_index.md"
    write_index_with_plan(workflow_index, "Idx-094", str(plan_file))
    write_index_file(project_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    # Mock get_staged_diff_stats：行數合規（10 行），但有不符合 glob 的 .py 檔
    with mock.patch.object(
        m,
        "get_staged_diff_stats",
        return_value=(10, ["doc/note.md", "core/some_module.py"]),
    ):
        ok = m.validate_commit_message(
            "feat(Idx-094): test copilot-chat path violation", workflow_index
        )

    assert ok is False
    out = capsys.readouterr().out
    assert "違規" in out or "allowed_path_globs" in out or "不符合" in out


def test_state_gate_fails_copilot_chat_small_fix_not_allowed(capsys, tmp_path):
    """
    AC#5：executor_tool=copilot-chat 但 copilot_chat_small_fix_allowed 不是 true
    → State Gate 應阻擋 commit
    """
    m = load_validate_state_gate_module()

    plan_file = tmp_path / "Idx-093_plan.md"
    write_plan_with_block(
        plan_file,
        textwrap.dedent("""\
            executor_tool: copilot-chat
            last_change_tool: copilot-chat
            qa_tool: codex-cli
            qa_result: PASS
            copilot_chat_small_fix_allowed: false
            copilot_chat_small_fix_reason: [TBD]
            copilot_chat_max_changed_lines: 20
            copilot_chat_allowed_path_globs: ["doc/**", "*.md"]
        """),
    )

    workflow_index = tmp_path / "workflow_index.md"
    project_index = tmp_path / "project_index.md"
    write_index_with_plan(workflow_index, "Idx-093", str(plan_file))
    write_index_file(project_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    with mock.patch.object(m, "get_staged_diff_stats", return_value=(5, ["doc/x.md"])):
        ok = m.validate_commit_message(
            "feat(Idx-093): test copilot-chat not allowed", workflow_index
        )

    assert ok is False
    out = capsys.readouterr().out
    assert "copilot_chat_small_fix_allowed" in out


def test_state_gate_passes_copilot_chat_valid_small_fix(tmp_path):
    """
    AC#5：executor_tool=copilot-chat，行數/路徑均合規，qa_result=PASS
    → State Gate 應通過
    """
    m = load_validate_state_gate_module()

    plan_file = tmp_path / "Idx-092_plan.md"
    write_plan_with_block(
        plan_file,
        textwrap.dedent("""\
            executor_tool: copilot-chat
            last_change_tool: copilot-chat
            qa_tool: codex-cli
            qa_result: PASS
            copilot_chat_small_fix_allowed: true
            copilot_chat_small_fix_reason: 更新文件小修正
            copilot_chat_max_changed_lines: 20
            copilot_chat_allowed_path_globs: ["doc/**", "README.md", "*.md"]
        """),
    )

    workflow_index = tmp_path / "workflow_index.md"
    project_index = tmp_path / "project_index.md"
    write_index_with_plan(workflow_index, "Idx-092", str(plan_file))
    write_index_file(project_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    # Mock get_staged_diff_stats：行數 8（< 20），路徑均合規
    with mock.patch.object(
        m,
        "get_staged_diff_stats",
        return_value=(8, ["doc/note.md", "README.md"]),
    ):
        ok = m.validate_commit_message("feat(Idx-092): test copilot-chat valid", workflow_index)

    assert ok is True


def test_state_gate_fails_missing_execution_block(capsys, tmp_path):
    """
    AC#3 Edge Case：Plan 找不到 / EXECUTION_BLOCK 不存在
    → State Gate 應顯示可行動錯誤訊息並 FAIL
    """
    m = load_validate_state_gate_module()

    plan_file = tmp_path / "Idx-091_plan.md"
    # Plan 存在但沒有 EXECUTION_BLOCK
    plan_file.write_text(
        "# 測試 Plan\n\n## 📋 SPEC\n只有 spec，沒有 EXECUTION_BLOCK\n", encoding="utf-8"
    )

    workflow_index = tmp_path / "workflow_index.md"
    project_index = tmp_path / "project_index.md"
    write_index_with_plan(workflow_index, "Idx-091", str(plan_file))
    write_index_file(project_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    ok = m.validate_commit_message("feat(Idx-091): test missing execution block", workflow_index)
    assert ok is False
    out = capsys.readouterr().out
    assert "EXECUTION_BLOCK" in out


def test_state_gate_fails_execution_block_placeholder_fields(capsys, tmp_path):
    """
    AC#3：EXECUTION_BLOCK 必填欄位仍為 placeholder（[TBD]）
    → State Gate 應阻擋 commit
    """
    m = load_validate_state_gate_module()

    plan_file = tmp_path / "Idx-090_plan.md"
    write_plan_with_block(
        plan_file,
        textwrap.dedent("""\
            executor_tool: [TBD]
            last_change_tool: [TBD]
            qa_tool: [TBD]
            qa_result: [PASS|PASS_WITH_RISK|FAIL]
        """),
    )

    workflow_index = tmp_path / "workflow_index.md"
    project_index = tmp_path / "project_index.md"
    write_index_with_plan(workflow_index, "Idx-090", str(plan_file))
    write_index_file(project_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    ok = m.validate_commit_message("feat(Idx-090): test placeholder fields", workflow_index)
    assert ok is False
    out = capsys.readouterr().out
    assert "placeholder" in out or "必填" in out or "TBD" in out


def test_state_gate_fails_plan_not_found(capsys, tmp_path):
    """
    AC#3 Edge Case：Index 中沒有記錄 Plan 路徑，且推斷也找不到
    → State Gate 應顯示可行動錯誤訊息並 FAIL
    """
    m = load_validate_state_gate_module()

    # Index 中有 Idx-089，但沒有 Plan 路徑，且 plan 目錄也不存在
    workflow_index = tmp_path / "workflow_index.md"
    project_index = tmp_path / "project_index.md"
    write_index_file(workflow_index, ["Idx-089"])
    write_index_file(project_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    ok = m.validate_commit_message("feat(Idx-089): test plan not found", workflow_index)
    assert ok is False
    out = capsys.readouterr().out
    assert "Plan" in out or "找不到" in out
