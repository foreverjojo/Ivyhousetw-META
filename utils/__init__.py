"""
utils 模組：工具函式集合
"""

from utils.file_io import (
    read_csv,
    read_json_if_exists,
    read_text_if_exists,
    write_json,
    write_text,
)
from utils.hash_utils import (
    compute_file_fp,
    compute_inputs_fingerprint,
    fingerprint_key_for_version,
    fp_short,
    sha256_bytes,
    sha256_str,
)
from utils.path_utils import (
    ensure_week_meta_dirs,
    latest_ptr_path,
    now_iso,
    read_latest_ptr,
    staging_version_dir,
    version_dir,
    versions_root,
    week_meta_dir,
    write_latest_ptr,
    write_week_info,
)
from utils.week_utils import (
    WEEK_RE,
    get_prev_week_id,
    list_week_ids_on_disk,
    normalize_week_id,
    parse_week_id,
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
