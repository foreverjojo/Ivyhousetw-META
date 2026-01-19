"""
檔案用途：全域設定與常數
職責：
  - 定義全域常數（HISTORY_ROOT, SCHEMAS_DIR）
  - 設定時區（TAIPEI_TZ）
  - Streamlit 頁面設定
"""

import os
from pathlib import Path

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
# 2026 模型常數（OpenRouter）
# 注意：這些是備援預設值，應透過環境變數 MODEL_CONSULTANT_X 覆蓋
# =========================

MODEL_CONSULTANT_A = os.getenv("MODEL_CONSULTANT_A", "openai/gpt-4o-mini")
MODEL_CONSULTANT_B = os.getenv("MODEL_CONSULTANT_B", "google/gemini-pro-1.5")
MODEL_CONSULTANT_C = os.getenv("MODEL_CONSULTANT_C", "anthropic/claude-3.5-sonnet")
MODEL_MODERATOR = os.getenv("MODEL_MODERATOR", "openai/gpt-4o-mini")
MODEL_INSIGHTS = os.getenv("MODEL_INSIGHTS", "openai/gpt-4o-mini")

# 定義 UI 可選模型 (用於快速切換)
AVAILABLE_MODELS = {
    "GPT-4o Mini": "openai/gpt-4o-mini",
    "GPT-4o": "openai/gpt-4o",
    "Claude 3.5 Sonnet": "anthropic/claude-3.5-sonnet",
    "Gemini 1.5 Pro": "google/gemini-pro-1.5",
    "Gemini 1.5 Flash": "google/gemini-flash-1.5",
    "DeepSeek V3": "deepseek/deepseek-chat",
}

# =========================
# 媒體素材目錄
# =========================
MEDIA_ASSETS_DIR = Path("attached_assets")
