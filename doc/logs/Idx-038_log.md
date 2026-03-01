# Task Execution Log: Idx-038

**Index**: Idx-038
**Plan Version**: 2026-02-23-v1
**Task Description**: 修正 E2 交叉審核輸出對齊 schema（移除 schema 驗證警告）

---

## 說明（補登記）

此 log 用於補齊 Idx-038 的稽核軌跡：Index 仍標示為「待處理」，但 repo 內已存在 E2 輸出 deterministic 正規化（normalize）與對應測試。
本次補登記僅基於「repo 內程式碼與單元測試結果」提供證據；未進行任何需要真實 LLM 呼叫的端到端驗收（避免在無金鑰/無網路條件下產生不可靠結論）。

---

## Evidence（Repo 內實作）

- E2 schema 正規化：`scripts/consultants.py`
  - `normalize_consultant_cross_review(...)`
  - `_single_cross_review(...)` 會在 parse/repair 後呼叫 normalize
- UI（E2 skip 時也會 normalize 舊落盤）：`ui/steps.py`
  - `run_step_e2(...)`：若已有 `consultant_cross_reviews.json` 且 skip，仍會 normalize 舊格式並做 schema 驗證提示
- 單元測試：`tests/test_e2_cross_review.py`
  - 覆蓋「常見不合規輸出 → normalize 後通過 schema」

---

## QA Commands（本次補登記實際執行）

- `pytest -q tests/test_e2_cross_review.py` ✅ PASS

---

## QA Result

- **Status**: ⚠️ PASS WITH RISK
- **Risk Notes**:
  - 未以真實 LLM 產出跑完整 E2 UI 流程（僅以 unit tests 驗證 normalize + schema validator）。

---

## 最小 E2E 驗收清單（使用者可在安全環境執行）

> ⚠️ **資安提醒**：執行前請確認不會在終端輸出任何 API key/token 值；下列步驟僅做存在性檢查，不洩漏憑證內容。

### 前置條件

- `OPENAI_API_KEY` 或 `OPENROUTER_API_KEY` 已設定（只檢查存在性，不輸出值）
- 有可用的 input 資料（可用 `examples/meta/`）

### Step 1：Headless Pipeline（Step C/E）

**指令**（需已設定 `OPENAI_API_KEY` 或 `OPENROUTER_API_KEY`）：

```bash
./.venv/bin/python scripts/debug_pipeline.py --input-dir examples/meta
```

**驗收點**：
- 終端列出 `Artifacts:` 清單，確認有產生：`report_insights.json`、`consultant_notes.json`、`workflow_state.json`、`meeting.md`
- `report_insights.json` 與 `consultant_notes.json` 內不應包含 `error` 欄位（或 error 為空）

### Step 2：E2 交叉審核 schema 驗證

**指令**（以 Step 1 終端輸出的 vdir 路徑替換 `<PASTE_VDIR_PATH_HERE>`）：

```bash
./.venv/bin/python - <<'PY'
import json
from pathlib import Path

from core import SCHEMAS_DIR
from core.validation import validate_consultant_cross_review
from scripts.consultants import generate_consultant_cross_reviews

vdir = Path("<PASTE_VDIR_PATH_HERE>")

def load(p: Path):
  return json.loads(p.read_text(encoding="utf-8"))

rs = load(vdir / "report_summary.json")
ri = load(vdir / "report_insights.json")
cn = load(vdir / "consultant_notes.json")

cr = generate_consultant_cross_reviews(rs, ri, cn, version_fp=vdir.name)
(vdir / "consultant_cross_reviews.json").write_text(
  json.dumps(cr, ensure_ascii=False, indent=2),
  encoding="utf-8",
)

reviews = (cr.get("reviews") or {})
for reviewer_key, review in reviews.items():
  validate_consultant_cross_review(review, SCHEMAS_DIR)

print("E2 schema OK")
print("success_count=", cr.get("success_count"), "error_count=", cr.get("error_count"))
PY
```

**驗收點**：
- `error_count == 0`
- schema validator 全數通過，終端印出 `E2 schema OK`

---

## Marker Evidence

```
[QA_DONE]
TIMESTAMP=2026-03-01T00:00:00Z
TASK_ID=Idx-038
QA_RESULT=PASS_WITH_RISK
NOTE=補登記；僅含 repo 內證據與本機測試
```

---

**Log Created**: 2026-03-01
**Last Updated**: 2026-03-01
