import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_validate_state_gate_module():
    module_path = REPO_ROOT / ".agent" / "scripts" / "validate_state_gate.py"
    spec = importlib.util.spec_from_file_location("validate_state_gate", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_index_file(path: Path, indices: list[str]) -> None:
    rows = [
        f"| {idx} | title | P2 | ✅ 已完成 | Manual | PASS | 1.0.0 | log | note |"
        for idx in indices
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_state_gate_fails_when_index_in_other_index(capsys, tmp_path):
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
    m = load_validate_state_gate_module()

    project_index = tmp_path / "project_index.md"
    workflow_index = tmp_path / "workflow_index.md"
    write_index_file(project_index, ["Idx-019"])
    write_index_file(workflow_index, [])

    m.PROJECT_INDEX_FILE = project_index
    m.WORKFLOW_INDEX_FILE = workflow_index
    m.LOCK_FILE = tmp_path / "lock.json"

    ok = m.validate_commit_message("feat(Idx-019): test", project_index)
    assert ok is True


def test_state_gate_allows_scoped_exempt_commit(tmp_path):
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
