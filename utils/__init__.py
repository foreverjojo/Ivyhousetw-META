"""
utils 模組：工具函式集合
"""

from utils.file_io import (
    read_json_if_exists,
    write_json,
    read_text_if_exists,
    write_text,
    read_csv,
)

from utils.hash_utils import (
    sha256_bytes,
    sha256_str,
    compute_file_fp,
    compute_inputs_fingerprint,
    fingerprint_key_for_version,
    fp_short,
)

from utils.week_utils import (
    normalize_week_id,
    parse_week_id,
    list_week_ids_on_disk,
    get_prev_week_id,
    WEEK_RE,
)

from utils.path_utils import (
    now_iso,
    week_meta_dir,
    versions_root,
    version_dir,
    latest_ptr_path,
    read_latest_ptr,
    write_latest_ptr,
    write_week_info,
    ensure_week_meta_dirs,
    staging_version_dir,
)

__all__ = [
    # file_io
    "read_json_if_exists",
    "write_json",
    "read_text_if_exists",
    "write_text",
    "read_csv",
    # hash_utils
    "sha256_bytes",
    "sha256_str",
    "compute_file_fp",
    "compute_inputs_fingerprint",
    "fingerprint_key_for_version",
    "fp_short",
    # week_utils
    "normalize_week_id",
    "parse_week_id",
    "list_week_ids_on_disk",
    "get_prev_week_id",
    "WEEK_RE",
    # path_utils
    "now_iso",
    "week_meta_dir",
    "versions_root",
    "version_dir",
    "latest_ptr_path",
    "read_latest_ptr",
    "write_latest_ptr",
    "write_week_info",
    "ensure_week_meta_dirs",
    "staging_version_dir",
]
