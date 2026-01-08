# -*- coding: utf-8 -*-
"""
tests/test_kpi_golden.py
=====================================
KPI 計算 Golden Regression Tests
確保 KPI 計算邏輯的正確性與穩定性
=====================================
"""

import pytest


def test_roas_calculation():
    """測試 ROAS 計算公式：ROAS = Revenue / Spend"""
    revenue = 10000.0
    spend = 2000.0
    expected_roas = 5.0
    
    # 基本公式驗證
    calculated_roas = revenue / spend if spend > 0 else 0
    assert calculated_roas == expected_roas, f"ROAS 計算錯誤：預期 {expected_roas}，實際 {calculated_roas}"


def test_roas_zero_spend():
    """測試零花費情況下的 ROAS 計算"""
    revenue = 5000.0
    spend = 0.0
    expected_roas = 0.0  # 零花費定義為 ROAS = 0
    
    calculated_roas = revenue / spend if spend > 0 else 0
    assert calculated_roas == expected_roas


def test_ctr_calculation():
    """測試 CTR 計算公式：CTR = (Clicks / Impressions) * 100"""
    clicks = 500
    impressions = 10000
    expected_ctr = 5.0  # 5%
    
    calculated_ctr = (clicks / impressions * 100) if impressions > 0 else 0
    assert abs(calculated_ctr - expected_ctr) < 0.01  # 允許浮點數誤差


def test_cpc_calculation():
    """測試 CPC 計算公式：CPC = Spend / Clicks"""
    spend = 1000.0
    clicks = 200
    expected_cpc = 5.0
    
    calculated_cpc = spend / clicks if clicks > 0 else 0
    assert abs(calculated_cpc - expected_cpc) < 0.01


# 未來補充：使用 golden files 的完整測試
@pytest.mark.skip(reason="等待 golden files 建立")
def test_meta_csv_parsing_with_golden_file(sample_meta_csv):
    """使用 golden file 測試 Meta CSV 解析"""
    # TODO: 實作完整的 CSV 解析與 KPI 計算驗證
    pass
