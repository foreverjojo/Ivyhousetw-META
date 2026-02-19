"""
Flask wrapper for Streamlit app - Google Cloud Run compatible
Listens on PORT environment variable
"""

import os
import signal
import subprocess
import sys

from flask import Flask

app = Flask(__name__)

# Store streamlit process
streamlit_process = None


def start_streamlit():
    """Start Streamlit server"""
    global streamlit_process
    port = int(os.environ.get("PORT", 8080))

    # Streamlit configuration
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

    # Wait for streamlit process
    streamlit_process.wait()


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print("Shutting down gracefully...")
    if streamlit_process:
        streamlit_process.terminate()
        streamlit_process.wait()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


@app.route("/")
def root():
    """Health check endpoint"""
    return {"status": "ok", "app": "Ivy House Meta Weekly MVP", "message": "Streamlit is running"}


@app.route("/health")
def health():
    """Health check for Cloud Run"""
    return {"status": "healthy"}, 200


if __name__ == "__main__":
    # Get port from environment
    port = int(os.environ.get("PORT", 8080))

    print(f"Starting application on port {port}")
    print("Starting Streamlit server...")

    # Start Streamlit in the main process
    start_streamlit()
