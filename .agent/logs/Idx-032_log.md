# Log: Idx-032

**Index**: Idx-032
**Date**: 2026-01-23
**Goal**: Ruff/Pytest 健康檢查 + extensions 同步 + 一鍵恢復對齊現況

---

## ✅ 結果摘要

- Ruff：✅ lint/format 通過
- Pytest：✅ 全綠（1 個 golden files 相關測試為預期 skip）
- Extensions：✅ 三方清單一致（devcontainer / .vscode / idx），且已將 local extension 的安裝納入 Dev Container restore
- 一鍵恢復：✅ `verify_restore_state.py` 通過，並補強檢查 dev deps 與 local extension install

---

## 🧪 健康檢查

### Ruff
- `python -m ruff check . --select=E9,F63,F7,F82 --target-version=py311`：pass
- `python -m ruff check core utils scripts tests main.py --target-version=py311`：pass
- `python -m ruff format --check core utils scripts tests main.py`：pass

### Pytest
- `pytest tests/`：pass（skipped: 1）

---

## 🧩 Extensions

### 已安裝 extensions（Dev Container）
- 確認存在 marketplace extensions + local extension `ivyhouse-local.ivyhouse-terminal-orchestrator@0.0.1`

### Repo 內 extensions 清單
- `.devcontainer/devcontainer.json`
- `.vscode/extensions.json`
- `.idx/dev.nix`

---

## 🔁 一鍵恢復（portable / devcontainer）

### Restore 狀態檢查
- `python scripts/portable/check_extensions_consistency.py`：pass
- `python scripts/portable/verify_restore_state.py`：pass

差異與修正：
- Dev Container / GHCR template：改為在 `uv.lock` 存在時使用 `uv sync --frozen --extra dev`，確保 ruff/pytest 等 dev tools 會被安裝
- Dev Container：在 `postCreateCommand` 自動執行 `scripts/vscode/install_terminal_orchestrator.sh`，讓 local terminal orchestrator extension 可重現
- Portable scripts：補充文件說明；並將多個 `.sh` 腳本加上可執行權限（chmod +x）

---

## 🧾 Commit / Push

- Commit：cac749a
- Pushed branch：`feature/idx-024-clear-on-pass`
