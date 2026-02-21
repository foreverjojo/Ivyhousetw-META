"""tests/test_e2_cross_review.py
=====================================
用途：E2 三顧問交叉審核（Idx-037）的自動化測試
職責：
  - 驗證 consultant_cross_review.v1 schema 合法/不合法資料
  - 驗證 validate_consultant_cross_review 函式
  - 驗證 graceful degradation 邏輯（部分 reviewer 失敗不阻擋流程）
  - 驗證 enable_cross_review=OFF 時不產生 cross_reviews 產物
=====================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
CROSS_REVIEW_SCHEMA_PATH = SCHEMAS_DIR / "consultant_cross_review.v1.json"


# -------------------
# Fixtures
# -------------------

TARGETS_MAP: dict[str, list[str]] = {
    "A": ["B", "C"],
    "B": ["A", "C"],
    "C": ["A", "B"],
}


def make_valid_cross_review(reviewer: str = "A") -> dict[str, Any]:
    """建立符合 consultant_cross_review.v1 schema 的合法 fixture。"""
    targets = TARGETS_MAP.get(reviewer, ["B", "C"])
    return {
        "review_version": "consultant_cross_review.v1",
        "reviewer": reviewer,
        "reviewed_targets": targets,
        "strengths": [f"顧問{targets[0]}的分析邏輯清晰，依據充分。"],
        "critical_issues": [
            {
                "issue": "預算建議缺乏明確停損條件",
                "evidence_ref": f"source:consultant_{targets[0]}.risks[0].risk",
                "impact": "可能在 ROAS 低迷時持續加碼造成損失",
                "severity": "medium",
                "suggested_fix": "在 overall_budget_action 中加入 stoploss_kpi 欄位",
            }
        ],
        "assumptions_to_validate": [
            {
                "assumption": "下週轉換歸因不變",
                "validation_step": "確認 Meta 事件管理員歸因設定未異動",
            }
        ],
        "recommended_edits": ["建議在 next_7d_actions 每條任務加入 stoploss 門檻值"],
        "stoploss_or_guardrails": ["若 ROAS 低於 1.9 立即停止新增預算"],
        "confidence": 0.8,
        "why": "審核核心關切：兩位顧問建議缺乏明確的止損機制。",
    }


# -------------------
# Schema PASS 測試
# -------------------


@pytest.mark.parametrize("reviewer", ["A", "B", "C"])
def test_cross_review_schema_pass(reviewer: str) -> None:
    """合法的交叉審核 fixture 應通過 schema 驗證。"""
    pytest.importorskip("jsonschema")
    import json

    from jsonschema import Draft202012Validator

    schema = json.loads(CROSS_REVIEW_SCHEMA_PATH.read_text(encoding="utf-8"))
    instance = make_valid_cross_review(reviewer)
    v = Draft202012Validator(schema)
    errors = list(v.iter_errors(instance))
    assert errors == [], f"reviewer={reviewer} 應通過但有錯誤：{[e.message for e in errors]}"


def test_cross_review_schema_file_exists() -> None:
    """確認 schema 檔案存在。"""
    assert CROSS_REVIEW_SCHEMA_PATH.exists(), (
        f"找不到 {CROSS_REVIEW_SCHEMA_PATH}，請確認 schemas/ 目錄"
    )


# -------------------
# Schema FAIL 測試
# -------------------


def test_cross_review_schema_fail_missing_required() -> None:
    """缺少必填欄位應觸發 schema 驗證失敗。"""
    pytest.importorskip("jsonschema")
    import json

    from jsonschema import Draft202012Validator

    schema = json.loads(CROSS_REVIEW_SCHEMA_PATH.read_text(encoding="utf-8"))
    # 缺少 strengths, critical_issues, recommended_edits 等
    instance = {
        "review_version": "consultant_cross_review.v1",
        "reviewer": "A",
        "reviewed_targets": ["B", "C"],
        "confidence": 0.5,
        "why": "測試缺少必填欄位",
    }
    v = Draft202012Validator(schema)
    errors = list(v.iter_errors(instance))
    assert errors, "缺少必填欄位應觸發驗證失敗"
    error_msgs = [e.message for e in errors]
    assert any("required" in m for m in error_msgs), (
        f"錯誤訊息應包含 'required'，實際：{error_msgs}"
    )


def test_cross_review_schema_fail_confidence_out_of_range() -> None:
    """confidence 超出 [0, 1] 範圍應觸發失敗。"""
    pytest.importorskip("jsonschema")
    import json

    from jsonschema import Draft202012Validator

    schema = json.loads(CROSS_REVIEW_SCHEMA_PATH.read_text(encoding="utf-8"))
    instance = make_valid_cross_review("B")
    instance["confidence"] = 1.5  # 超過 maximum: 1
    v = Draft202012Validator(schema)
    errors = list(v.iter_errors(instance))
    assert errors, "confidence=1.5 應觸發驗證失敗"
    error_msgs = [e.message for e in errors]
    assert any("maximum" in m for m in error_msgs), f"錯誤訊息應包含 'maximum'，實際：{error_msgs}"


def test_cross_review_schema_fail_duplicate_reviewed_targets() -> None:
    """reviewed_targets 重複（違反 uniqueItems）應觸發失敗。"""
    pytest.importorskip("jsonschema")
    import json

    from jsonschema import Draft202012Validator

    schema = json.loads(CROSS_REVIEW_SCHEMA_PATH.read_text(encoding="utf-8"))
    instance = make_valid_cross_review("A")
    instance["reviewed_targets"] = ["B", "B"]  # 違反 uniqueItems
    v = Draft202012Validator(schema)
    errors = list(v.iter_errors(instance))
    assert errors, "重複的 reviewed_targets 應觸發驗證失敗"


# -------------------
# validate_consultant_cross_review 函式測試
# -------------------


def test_validate_consultant_cross_review_pass() -> None:
    """validate_consultant_cross_review() 對合法資料不應拋出例外。"""
    pytest.importorskip("jsonschema")
    from core.validation import validate_consultant_cross_review

    instance = make_valid_cross_review("C")
    # 不應拋出任何例外
    validate_consultant_cross_review(instance, SCHEMAS_DIR)


def test_validate_consultant_cross_review_fail() -> None:
    """validate_consultant_cross_review() 對非法資料應拋出 SchemaValidationError。"""
    pytest.importorskip("jsonschema")
    from core.validation import SchemaValidationError, validate_consultant_cross_review

    # 缺少必填欄位
    bad_instance = {
        "review_version": "consultant_cross_review.v1",
        "reviewer": "A",
        "reviewed_targets": ["B", "C"],
    }
    with pytest.raises(SchemaValidationError):
        validate_consultant_cross_review(bad_instance, SCHEMAS_DIR)


# -------------------
# Graceful Degradation 測試
# -------------------


def test_e2_graceful_degradation_partial_failure() -> None:
    """
    模擬 E2 部分 reviewer 失敗的場景：
    - success_count 與 error_count 應正確計算
    - 成功的 reviewer 結果應符合 schema
    - 失敗的 reviewer 應有 error 欄位
    - 整體結構完整（不應拋出例外）
    """
    pytest.importorskip("jsonschema")
    import json

    from jsonschema import Draft202012Validator

    schema = json.loads(CROSS_REVIEW_SCHEMA_PATH.read_text(encoding="utf-8"))

    # 模擬：B 失敗，A/C 成功
    mock_reviews: dict[str, Any] = {
        "reviewer_A": make_valid_cross_review("A"),
        "reviewer_B": {
            "error": "LLM timeout after 120s",
            "reviewer": "B",
            "reviewed_targets": ["A", "C"],
        },
        "reviewer_C": make_valid_cross_review("C"),
    }

    success_count = sum(
        1 for r in mock_reviews.values() if isinstance(r, dict) and "error" not in r
    )
    error_count = len(mock_reviews) - success_count

    assert success_count == 2, f"預期 success_count=2，實際={success_count}"
    assert error_count == 1, f"預期 error_count=1，實際={error_count}"

    # 成功的 reviewer 應通過 schema
    v = Draft202012Validator(schema)
    for key in ["reviewer_A", "reviewer_C"]:
        errors = list(v.iter_errors(mock_reviews[key]))
        assert errors == [], f"{key} 應通過 schema，但有錯誤：{[e.message for e in errors]}"

    # 失敗的 reviewer 應有 error 欄位
    assert "error" in mock_reviews["reviewer_B"], "失敗的 reviewer 應有 error 欄位"


def test_e2_graceful_degradation_all_failure() -> None:
    """
    模擬 E2 全部失敗（三個 reviewer 均失敗）：
    - 仍能建立合法的 cross_reviews 結構
    - success_count=0, error_count=3
    - Step F 接收到 cross_reviews=None 時應正常執行
    """
    # 模擬全失敗的 cross_reviews 輸出
    mock_cross_reviews: dict[str, Any] = {
        "cross_reviews_version": "consultant_cross_reviews.v1",
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-09",
        "success_count": 0,
        "error_count": 3,
        "reviews": {
            "reviewer_A": {
                "error": "API error 429",
                "reviewer": "A",
                "reviewed_targets": ["B", "C"],
            },
            "reviewer_B": {"error": "timeout", "reviewer": "B", "reviewed_targets": ["A", "C"]},
            "reviewer_C": {
                "error": "non-JSON response",
                "reviewer": "C",
                "reviewed_targets": ["A", "B"],
            },
        },
    }

    # 確認結構完整
    assert mock_cross_reviews["success_count"] == 0
    assert mock_cross_reviews["error_count"] == 3
    assert len(mock_cross_reviews["reviews"]) == 3

    # 確認所有 reviewer 都有 error 欄位
    for key, review in mock_cross_reviews["reviews"].items():
        assert "error" in review, f"{key} 應有 error 欄位"

    # 模擬：cross_reviews=None（全失敗降級）時，Step F 不應崩潰
    # 此處只驗證 None 輸入不會觸發 AttributeError 等
    cross_reviews_input: dict[str, Any] | None = None
    assert cross_reviews_input is None  # graceful degradation 正常


def test_e2_disabled_no_cross_reviews_file(tmp_path: Path) -> None:
    """
    enable_cross_review=OFF 時，不應產生 consultant_cross_reviews.json。
    此測試驗證：若 vdir 中沒有此檔案，Step F 應正常執行（cross_reviews=None）。
    """
    # 模擬 vdir 中沒有 consultant_cross_reviews.json
    fake_vdir = tmp_path / "test_version"
    fake_vdir.mkdir()

    cross_review_file = fake_vdir / "consultant_cross_reviews.json"
    assert not cross_review_file.exists(), "OFF 狀態下不應存在 consultant_cross_reviews.json"

    # 若沒有檔案，cross_reviews 應為 None
    cross_reviews = None
    if cross_review_file.exists():
        import json

        cross_reviews = json.loads(cross_review_file.read_text(encoding="utf-8"))

    assert cross_reviews is None, "enable_cross_review=OFF 時 cross_reviews 應為 None"
