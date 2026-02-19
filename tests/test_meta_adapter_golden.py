"""
檔案用途：Meta adapter 的 golden regression test，確保 CSV->Unified 轉換結果穩定可重現。
"""

from __future__ import annotations

import json
from pathlib import Path


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_meta_adset_adapter_matches_golden(sample_meta_csv, test_data_dir):
    expected_path = test_data_dir / "meta_expected_output.json"
    expected = _load_json(expected_path)
    expected.pop("__comment", None)

    from scripts.adapters.meta_adapter import adapt_meta_adset_csv

    actual = adapt_meta_adset_csv(sample_meta_csv)
    actual["generated_at"] = expected["generated_at"]

    assert actual == expected
