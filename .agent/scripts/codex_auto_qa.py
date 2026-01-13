#!/usr/bin/env python3
"""
Codex CLI 自動化 QA 腳本（使用 pty）
"""
import sys
import time
import subprocess
import select

def run_codex_with_prompt(prompt: str, timeout: int = 90) -> str:
    """在 pseudo-terminal 中執行 codex 並送入 prompt"""
    import pty
    import os

    # 建立 pseudo-terminal
    master, slave = pty.openpty()

    # 啟動 codex
    proc = subprocess.Popen(
        ['codex', prompt],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True
    )

    os.close(slave)

    output = []
    start_time = time.time()

    try:
        while time.time() - start_time < timeout:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    data = os.read(master, 1024)
                    if data:
                        output.append(data.decode('utf-8', errors='ignore'))
                    else:
                        break
                except OSError:
                    break

            # 檢查進程是否結束
            if proc.poll() is not None:
                # 再讀一次確保拿到所有輸出
                time.sleep(0.5)
                while select.select([master], [], [], 0.1)[0]:
                    try:
                        data = os.read(master, 1024)
                        if data:
                            output.append(data.decode('utf-8', errors='ignore'))
                    except OSError:
                        break
                break
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            proc.kill()
        os.close(master)

    return ''.join(output)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: codex_auto_qa.py <prompt>")
        sys.exit(1)

    prompt = ' '.join(sys.argv[1:])
    print(f"Running: codex \"{prompt[:100]}...\"")

    result = run_codex_with_prompt(prompt)
    print(result)
