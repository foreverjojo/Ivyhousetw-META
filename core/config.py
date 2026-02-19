"""
檔案用途：全域設定與常數
職責：
  - 定義全域常數（HISTORY_ROOT, SCHEMAS_DIR）
  - 設定時區（TAIPEI_TZ）
  - Streamlit 頁面設定
"""

from pathlib import Path

from core.model_settings import (
    AVAILABLE_MODELS as _AVAILABLE_MODELS,
)
from core.model_settings import (
    get_default_model,
)

# =========================
# Timezone（固定台北時間）
# =========================
try:
    from zoneinfo import ZoneInfo  # Python 3.9 以上

    TAIPEI_TZ = ZoneInfo("Asia/Taipei")
except Exception:
    TAIPEI_TZ = None  # 備援：使用本地時間


# =========================
# 路徑常數
# =========================
HISTORY_ROOT = Path("history")
HISTORY_ROOT.mkdir(parents=True, exist_ok=True)

SCHEMAS_DIR = Path("schemas")

# =========================
# 模型設定（由 core.model_settings 集中管理）
# 注意：以下常數僅做相容層，請優先使用 core.model_settings.get_model()
# =========================

MODEL_CONSULTANT_A = get_default_model("consultant_a")
MODEL_CONSULTANT_B = get_default_model("consultant_b")
MODEL_CONSULTANT_C = get_default_model("consultant_c")
MODEL_MODERATOR = get_default_model("moderator")
MODEL_INSIGHTS = get_default_model("insights")
AVAILABLE_MODELS = _AVAILABLE_MODELS

# =========================
# 媒體素材目錄
# =========================
MEDIA_ASSETS_DIR = Path("attached_assets")
