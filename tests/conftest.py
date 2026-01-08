# -*- coding: utf-8 -*-
"""
tests/conftest.py
=====================================
Pytest 配置檔案
提供測試共用的 fixtures
=====================================
"""

import pytest
from pathlib import Path


@pytest.fixture
def project_root():
    """專案根目錄"""
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir(project_root):
    """測試資料目錄"""
    return project_root / "tests" / "golden"


@pytest.fixture
def sample_meta_csv(test_data_dir):
    """範例 Meta CSV 檔案路徑"""
    csv_file = test_data_dir / "meta_sample_input.csv"
    if not csv_file.exists():
        pytest.skip(f"測試資料檔案不存在：{csv_file}")
    return csv_file
