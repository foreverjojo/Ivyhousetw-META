"""Cloud Run 入口點（Streamlit 啟動器）。

職責：
  - 監聽 `PORT` 環境變數（Cloud Run 必需）
  - 啟動 Streamlit 並處理 SIGTERM/SIGINT 優雅關機

注意：
  - Streamlit 本身會在該 PORT 提供 UI；健康檢查建議使用 `/`。
"""

import os
import signal
import subprocess
import sys

streamlit_process: subprocess.Popen[str] | None = None


def start_streamlit() -> None:
    """啟動 Streamlit server（blocking）。"""
    global streamlit_process

    port = int(os.environ.get("PORT", 8080))
    streamlit_cmd = [
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        str(port),
        "--server.address",
        "0.0.0.0",
        "--server.headless",
        "true",
        "--server.enableCORS",
        "false",
        "--server.enableXsrfProtection",
        "false",
        "--browser.gatherUsageStats",
        "false",
    ]

    streamlit_process = subprocess.Popen(streamlit_cmd)
    print(f"Streamlit started on port {port}")
    streamlit_process.wait()


def signal_handler(sig, frame) -> None:
    """處理關機訊號（SIGTERM/SIGINT）。"""
    print("Shutting down gracefully...")
    if streamlit_process:
        streamlit_process.terminate()
        streamlit_process.wait()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting application on port {port}")
    print("Starting Streamlit server...")
    start_streamlit()
