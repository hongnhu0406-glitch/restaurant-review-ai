import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def find_free_port(start_port, end_port):
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free ports found in range {start_port}-{end_port}.")


def start_process(command, label, env=None):
    print(f"[{label}] Starting: {' '.join(command)}")
    process = subprocess.Popen(
        command,
        cwd=str(ROOT),
        stdout=sys.stdout,
        stderr=sys.stderr,
        text=True,
        shell=False,
        env=env,
    )
    return process


def wait_for_http(url, timeout=25):
    start = time.time()
    while time.time() - start < timeout:
        try:
            import urllib.request

            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return True
        except Exception:
            time.sleep(1)
    return False


def stop_process(process, label):
    if process is None:
        return
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait(timeout=10)
        print(f"[{label}] stopped.")
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


if __name__ == "__main__":
    backend_port = find_free_port(8000, 8010)
    streamlit_port = find_free_port(8501, 8510)

    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(ROOT) + os.pathsep + backend_env.get("PYTHONPATH", "")
    backend_env["PYTHONUNBUFFERED"] = "1"
    backend_env["PYTHONUTF8"] = "1"
    backend_env["PYTHONIOENCODING"] = "utf-8"

    backend = start_process(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(backend_port),
        ],
        label="BACKEND",
        env=backend_env,
    )

    backend_url = f"http://127.0.0.1:{backend_port}"
    if not wait_for_http(f"{backend_url}/health"):
        print("[BACKEND] Failed to start within timeout.")
        stop_process(backend, "BACKEND")
        raise SystemExit(1)

    streamlit_env = os.environ.copy()
    streamlit_env["API_BASE_URL"] = backend_url
    streamlit_env["RESTAURANT_API_URL"] = backend_url
    streamlit_env["PYTHONPATH"] = str(ROOT) + os.pathsep + streamlit_env.get("PYTHONPATH", "")
    streamlit_env["PYTHONUTF8"] = "1"
    streamlit_env["PYTHONIOENCODING"] = "utf-8"

    streamlit = start_process(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "single_review.py",
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(streamlit_port),
            "--browser.gatherUsageStats",
            "false",
        ],
        label="STREAMLIT",
        env=streamlit_env,
    )

    print("\nApplication started successfully.")
    print(f"Backend: {backend_url}")
    print(f"Frontend: http://127.0.0.1:{streamlit_port}")
    print("Press Ctrl+C to stop all services.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        stop_process(streamlit, "STREAMLIT")
        stop_process(backend, "BACKEND")
