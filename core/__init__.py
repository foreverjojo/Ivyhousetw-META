"""
core 模組：核心邏輯
"""

from core.env_loader import load_environment_variables
from core.config import HISTORY_ROOT, SCHEMAS_DIR, TAIPEI_TZ
from core.validation import (
    SchemaValidationError,
    validate_json,
    validate_report_summary,
)
from core.pipeline_state import (
    write_pipeline_state,
    restore_from_version_dir,
)
from core.logging import get_logger  # 新增：導出 logging 功能

__all__ = [
    # env_loader
    "load_environment_variables",
    # config
    "HISTORY_ROOT",
    "SCHEMAS_DIR",
    "TAIPEI_TZ",
    # validation
    "SchemaValidationError",
    "validate_json",
    "validate_report_summary",
    # pipeline_state
    "write_pipeline_state",
    "restore_from_version_dir",
]
