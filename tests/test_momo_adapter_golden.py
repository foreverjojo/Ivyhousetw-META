# -*- coding: utf-8 -*-
"""
檔案用途：MOMO adapter 的 golden regression test，確保 CSV->Unified 轉換結果穩定可重現。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def momo_test_data_dir(project_root):
    """MOMO 測試資料目錄"""
    return project_root / "tests" / "golden"


@pytest.fixture
def sample_momo_csv(momo_test_data_dir):
    """範例 MOMO CSV 檔案路徑"""
    csv_file = momo_test_data_dir / "momo_sample_input.csv"
    if not csv_file.exists():
        pytest.skip(f"測試資料檔案不存在：{csv_file}")
    return csv_file


def test_momo_adapter_matches_golden(sample_momo_csv, test_data_dir):
    """測試 MOMO adapter 轉換結果與 golden file 一致"""
    expected_path = test_data_dir / "momo_expected_output.json"
    if not expected_path.exists():
        pytest.skip(f"Golden file 不存在：{expected_path}")

    expected = _load_json(expected_path)
    expected.pop("__comment", None)

    from scripts.adapters.momo_adapter import adapt_momo_ad_report

    actual = adapt_momo_ad_report(sample_momo_csv)
    # 忽略時間戳差異
    actual["generated_at"] = expected["generated_at"]

    assert actual == expected


def test_momo_adapter_record_count(sample_momo_csv):
    """測試 MOMO adapter 資料筆數正確"""
    from scripts.adapters.momo_adapter import adapt_momo_ad_report

    result = adapt_momo_ad_report(sample_momo_csv)

    # 範例 input 有 5 筆，都有效
    assert len(result["data"]) == 5, f"預期 5 筆資料，實際 {len(result['data'])} 筆"


def test_momo_adapter_required_fields(sample_momo_csv):
    """測試 MOMO adapter 產出包含必要欄位"""
    from scripts.adapters.momo_adapter import adapt_momo_ad_report

    result = adapt_momo_ad_report(sample_momo_csv)

    for record in result["data"]:
        # 必填欄位
        assert "platform" in record
        assert record["platform"] == "momo"
        assert "level" in record
        assert "id" in record
        assert "name" in record
        assert "time_range" in record  # MOMO 可能為空字串，但 key 必須存在
        assert "currency" in record
        assert "metrics" in record

        # ID 必須為 product_id (字串形式)
        assert isinstance(record["id"], str)
        assert len(record["id"]) > 0

        # metrics 結構
        metrics = record["metrics"]
        assert "spend" in metrics
        assert "impressions" in metrics
        assert "clicks" in metrics
        assert "conversions" in metrics
        assert "funnel" in metrics

        # MOMO 特有：ATC
        assert "atc" in metrics["funnel"]

        # conversions 結構
        conv = metrics["conversions"]
        assert "platform" in conv
        assert "count" in conv["platform"]
        assert "value" in conv["platform"]
