import os
import subprocess
import sys

# macOS fork-safety: numpy/scikit-learn load Apple's Accelerate framework, which
# initialises the Objective-C runtime. gunicorn's sync worker fork()s, and macOS
# kills the child for touching Obj-C after fork. This env var disables that check.
# It is macOS-only and ignored on Linux, so production deployment is unaffected.
os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

PORT = 8001
PROJECT_NAME = "TIAA"


def kill_existing_process(port):
    pids = subprocess.run(
        f"lsof -ti:{port}", shell=True, capture_output=True, text=True
    ).stdout.split()
    if pids:
        subprocess.run(["kill", "-9", *pids])
        print(f"Killed existing process on port {port}")
    else:
        print(f"No process found running on port {port}")


def run_gunicorn(daemon=False):
    kill_existing_process(PORT)
    command = [
        "gunicorn",
        "--bind", f"0.0.0.0:{PORT}",
        # Threaded workers handle browser keep-alive connections without a single
        # worker blocking; multiple workers + a longer timeout stop the constant
        # "WORKER TIMEOUT (no URI read)" reaping (and the model-reload churn it
        # caused, which produced intermittent 500s that cleared on reload).
        "--workers", "3",
        "--worker-class", "gthread",
        "--threads", "4",
        "--timeout", "120",
        "--graceful-timeout", "30",
        "--keep-alive", "5",
        f"{PROJECT_NAME}.wsgi:application",
    ]
    if daemon:
        command.append("--daemon")
    print(f"Running command: {' '.join(command)}")
    subprocess.call(command)


if __name__ == "__main__":
    daemon_mode = "-d" in sys.argv or "--daemon" in sys.argv
    run_gunicorn(daemon=daemon_mode)
