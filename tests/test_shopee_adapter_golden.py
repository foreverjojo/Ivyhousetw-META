# -*- coding: utf-8 -*-
"""
檔案用途：Shopee adapter 的 golden regression test，確保 CSV->Unified 轉換結果穩定可重現。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def shopee_test_data_dir(project_root):
    """蝦皮測試資料目錄"""
    return project_root / "tests" / "golden"


@pytest.fixture
def sample_shopee_csv(shopee_test_data_dir):
    """範例蝦皮 CSV 檔案路徑"""
    csv_file = shopee_test_data_dir / "shopee_sample_input.csv"
    if not csv_file.exists():
        pytest.skip(f"測試資料檔案不存在：{csv_file}")
    return csv_file


def test_shopee_adapter_matches_golden(sample_shopee_csv, test_data_dir):
    """測試蝦皮 adapter 轉換結果與 golden file 一致"""
    expected_path = test_data_dir / "shopee_expected_output.json"
    if not expected_path.exists():
        pytest.skip(f"Golden file 不存在：{expected_path}")
    
    expected = _load_json(expected_path)
    expected.pop("__comment", None)
    
    from scripts.adapters.shopee_adapter import adapt_shopee_ad_csv
    
    actual = adapt_shopee_ad_csv(sample_shopee_csv)
    # 忽略時間戳差異
    actual["generated_at"] = expected["generated_at"]
    
    assert actual == expected


def test_shopee_adapter_record_count(sample_shopee_csv):
    """測試蝦皮 adapter 資料筆數正確"""
    from scripts.adapters.shopee_adapter import adapt_shopee_ad_csv
    
    result = adapt_shopee_ad_csv(sample_shopee_csv)
    
    assert len(result["data"]) == 3, f"預期 3 筆資料，實際 {len(result['data'])} 筆"


def test_shopee_adapter_required_fields(sample_shopee_csv):
    """測試蝦皮 adapter 產出包含必要欄位"""
    from scripts.adapters.shopee_adapter import adapt_shopee_ad_csv
    
    result = adapt_shopee_ad_csv(sample_shopee_csv)
    
    for record in result["data"]:
        # 必填欄位
        assert "platform" in record
        assert record["platform"] == "shopee"
        assert "level" in record
        assert "id" in record
        assert "name" in record
        assert "time_range" in record
        assert "currency" in record
        assert "metrics" in record
        
        # metrics 結構
        metrics = record["metrics"]
        assert "spend" in metrics
        assert "impressions" in metrics
        assert "clicks" in metrics
        assert "conversions" in metrics
        assert "funnel" in metrics
        
        # conversions 結構
        conv = metrics["conversions"]
        assert "truth" in conv
        assert "platform" in conv
        assert "count" in conv["truth"]
        assert "value" in conv["truth"]
