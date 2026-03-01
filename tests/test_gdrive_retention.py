"""
檔案用途：gdrive_retention.py 純本地單元測試
職責：
  - 測試週次資料夾名稱解析（parse_week_folder_name）
  - 測試週次資料夾排序（sort_week_folders）
  - 測試保留計算邏輯（compute_weeks_to_trash）
  - 不打外網、不呼叫 Drive API
"""

from __future__ import annotations

from scripts.gdrive_retention import (
    CONFIRM_STRING,
    compute_weeks_to_trash,
    parse_week_folder_name,
    sort_week_folders,
)

# ===========================
# parse_week_folder_name
# ===========================


class TestParseWeekFolderName:
    def test_valid_week_basic(self) -> None:
        """標準 YYYY-Www 格式應成功解析"""
        result = parse_week_folder_name("2026-W08")
        assert result == (2026, 8)

    def test_valid_week_large_number(self) -> None:
        """週次 W52 應成功解析"""
        result = parse_week_folder_name("2025-W52")
        assert result == (2025, 52)

    def test_valid_week_leading_zero(self) -> None:
        """週次 W01 應成功解析"""
        result = parse_week_folder_name("2026-W01")
        assert result == (2026, 1)

    def test_invalid_no_dash(self) -> None:
        """無破折號格式應回傳 None"""
        assert parse_week_folder_name("2026W08") is None

    def test_invalid_shopee_format(self) -> None:
        """Shopee 格式（非 YYYY-Www）應回傳 None"""
        assert parse_week_folder_name("Shopee_2026-02-20") is None

    def test_invalid_momo_format(self) -> None:
        """Momo 格式應回傳 None"""
        assert parse_week_folder_name("Momo_2026-02-20") is None

    def test_invalid_empty_string(self) -> None:
        """空字串應回傳 None"""
        assert parse_week_folder_name("") is None

    def test_invalid_partial_format(self) -> None:
        """部分符合格式應回傳 None"""
        assert parse_week_folder_name("2026-W") is None

    def test_invalid_lowercase_w(self) -> None:
        """小寫 w 不符合格式，應回傳 None"""
        assert parse_week_folder_name("2026-w08") is None

    def test_single_digit_week_not_allowed(self) -> None:
        """只有一位數的週次（無補零）應回傳 None（YYYY-W8）"""
        # 我們的正則要求兩位數（\d{2}）
        assert parse_week_folder_name("2026-W8") is None


# ===========================
# sort_week_folders
# ===========================


class TestSortWeekFolders:
    def _make_entries(self, names: list[str]) -> list[dict]:
        return [{"id": f"id_{name}", "name": name} for name in names]

    def test_sort_ascending(self) -> None:
        """舊週次應排在前面"""
        entries = self._make_entries(["2026-W08", "2026-W01", "2025-W52"])
        result = sort_week_folders(entries)
        names = [e["name"] for e in result]
        assert names == ["2025-W52", "2026-W01", "2026-W08"]

    def test_unparseable_sorted_to_end(self) -> None:
        """無法解析的資料夾應排到最後"""
        entries = self._make_entries(["2026-W08", "Shopee_2026-02", "2026-W01"])
        result = sort_week_folders(entries)
        names = [e["name"] for e in result]
        assert names[0] == "2026-W01"
        assert names[1] == "2026-W08"
        assert names[2] == "Shopee_2026-02"

    def test_empty_list(self) -> None:
        """空清單應回傳空清單"""
        assert sort_week_folders([]) == []

    def test_single_entry(self) -> None:
        """單一項目應保持不變"""
        entries = self._make_entries(["2026-W05"])
        result = sort_week_folders(entries)
        assert len(result) == 1
        assert result[0]["name"] == "2026-W05"


# ===========================
# compute_weeks_to_trash
# ===========================


class TestComputeWeeksToTrash:
    def _make_entries(self, names: list[str]) -> list[dict]:
        return [{"id": f"id_{name}", "name": name} for name in names]

    def test_keep_latest_12_from_14(self) -> None:
        """14 週時，最舊的 2 個應被移到 Trash"""
        names = [f"2025-W{w:02d}" for w in range(1, 15)]  # W01 ~ W14
        entries = self._make_entries(names)
        to_trash, to_keep = compute_weeks_to_trash(entries, keep_weeks=12)
        assert len(to_trash) == 2
        assert len(to_keep) == 12
        trash_names = [e["name"] for e in to_trash]
        assert "2025-W01" in trash_names
        assert "2025-W02" in trash_names

    def test_exact_keep_weeks_no_trash(self) -> None:
        """剛好 12 週時不應移除任何資料夾"""
        names = [f"2025-W{w:02d}" for w in range(1, 13)]  # W01 ~ W12
        entries = self._make_entries(names)
        to_trash, to_keep = compute_weeks_to_trash(entries, keep_weeks=12)
        assert len(to_trash) == 0
        assert len(to_keep) == 12

    def test_fewer_than_keep_weeks(self) -> None:
        """少於 keep_weeks 時不應移除任何資料夾"""
        names = [f"2025-W{w:02d}" for w in range(1, 6)]  # 只有 5 週
        entries = self._make_entries(names)
        to_trash, to_keep = compute_weeks_to_trash(entries, keep_weeks=12)
        assert len(to_trash) == 0
        assert len(to_keep) == 5

    def test_unparseable_never_trashed(self) -> None:
        """無法解析的資料夾不應被移到 Trash"""
        names = [f"2025-W{w:02d}" for w in range(1, 15)]  # W01~W14 共 14 個
        names.append("Shopee_2025-01")  # 無法解析的
        entries = self._make_entries(names)
        to_trash, to_keep = compute_weeks_to_trash(entries, keep_weeks=12)
        trash_names = [e["name"] for e in to_trash]
        # 無法解析的不應出現在 to_trash 中
        assert "Shopee_2025-01" not in trash_names
        # 只有 2 個舊週次應被移
        assert len(to_trash) == 2

    def test_cross_year_boundary(self) -> None:
        """跨年週次應正確排序與保留"""
        names = [
            "2024-W50",
            "2024-W51",
            "2024-W52",
            "2025-W01",
            "2025-W02",
        ]
        entries = self._make_entries(names)
        to_trash, to_keep = compute_weeks_to_trash(entries, keep_weeks=3)
        assert len(to_trash) == 2
        trash_names = [e["name"] for e in to_trash]
        assert "2024-W50" in trash_names
        assert "2024-W51" in trash_names

    def test_empty_list(self) -> None:
        """空清單時兩個結果都應為空"""
        to_trash, to_keep = compute_weeks_to_trash([], keep_weeks=12)
        assert to_trash == []
        assert to_keep == []

    def test_custom_keep_weeks(self) -> None:
        """自訂 keep_weeks=4 應保留最新 4 週"""
        names = [f"2026-W{w:02d}" for w in range(1, 9)]  # W01~W08
        entries = self._make_entries(names)
        to_trash, to_keep = compute_weeks_to_trash(entries, keep_weeks=4)
        assert len(to_trash) == 4
        assert len(to_keep) == 4
        keep_names = [e["name"] for e in to_keep]
        assert "2026-W05" in keep_names
        assert "2026-W06" in keep_names
        assert "2026-W07" in keep_names
        assert "2026-W08" in keep_names


# ===========================
# CONFIRM_STRING 常數
# ===========================


class TestConfirmString:
    def test_confirm_string_value(self) -> None:
        """確認字串值正確（防止意外修改）"""
        assert CONFIRM_STRING == "TRASH_OLDER_THAN_12_WEEKS"
