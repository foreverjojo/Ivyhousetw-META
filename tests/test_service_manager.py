import os
import shutil
import subprocess
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
SERVICE_SCRIPT = os.path.join(ROOT, "scripts", "service_manager.sh")


def has_cmd(name):
    return shutil.which(name) is not None


@pytest.mark.skipif(not has_cmd("script"), reason="`script` not available")
@pytest.mark.skipif(has_cmd("tmux"), reason="tmux available; PTY wrapper not used")
def test_start_with_pty(tmp_path):
    # Start a short-lived sleep process wrapped with PTY
    cmd = [SERVICE_SCRIPT, "start", "dummy_pty", "--cmd", "sleep 60", "--pty"]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, f"start failed: {p.stderr}"

    # Allow some time for process to start
    time.sleep(0.3)

    s = subprocess.run(
        [SERVICE_SCRIPT, "status", "dummy_pty"], cwd=ROOT, capture_output=True, text=True
    )
    assert s.returncode == 0, f"status failed: {s.stderr}"

    # Stop and cleanup
    stop = subprocess.run(
        [SERVICE_SCRIPT, "stop", "dummy_pty"], cwd=ROOT, capture_output=True, text=True
    )
    assert stop.returncode == 0, f"stop failed: {stop.stderr}"


def test_auto_fallback_to_pty(tmp_path):
    # Simulate a service that needs a TTY: it exits without TTY, sleeps with TTY
    tt_cmd = "bash -lc 'if [[ -t 0 ]]; then echo OK; exec sleep 60; else echo stdin is not a terminal; exit 1; fi'"
    p = subprocess.run(
        [SERVICE_SCRIPT, "start", "tty_auto", "--cmd", tt_cmd],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, f"start failed: {p.stderr}"

    # Allow time for fallback logic and startup
    time.sleep(0.6)

    s = subprocess.run(
        [SERVICE_SCRIPT, "status", "tty_auto"], cwd=ROOT, capture_output=True, text=True
    )
    assert s.returncode == 0, f"status failed (service may not have started with PTY): {s.stderr}"

    # Validate that a sleep process is running (the PTY wrapper should have exec'd sleep)
    pids = subprocess.run(["pgrep", "-f", "sleep 60"], capture_output=True, text=True)
    assert pids.returncode == 0, "No sleep 60 process found; PTY fallback may have failed"

    # Stop and cleanup
    stop = subprocess.run(
        [SERVICE_SCRIPT, "stop", "tty_auto"], cwd=ROOT, capture_output=True, text=True
    )
    assert stop.returncode == 0, f"stop failed: {stop.stderr}"
