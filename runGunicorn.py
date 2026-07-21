import os
import subprocess
import sys

# --- Core stability settings (must be set BEFORE numpy/scikit-learn import) ---

# macOS fork-safety: numpy/scikit-learn load Apple's Accelerate framework, which
# initialises the Objective-C runtime. Forking a worker after that init makes
# macOS kill the child unless this is disabled. macOS-only; ignored on Linux.
os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

# Force single-threaded BLAS/OpenMP. Multi-threaded native math libraries can
# DEADLOCK inside forked/threaded gunicorn workers, leaving a worker hung forever
# (the "server goes stale / gateway timeout" symptom). Single-threaded is plenty
# for this workload and removes that entire class of hangs.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

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
        # Threaded workers serve browser keep-alive connections without blocking;
        # several workers mean one is always free.
        "--workers", "3",
        "--worker-class", "gthread",
        "--threads", "4",
        # Load the app (and the ML model) ONCE in the master, then fork. Workers
        # start instantly with no cold first-request stall, and share memory.
        "--preload",
        # Recycle workers periodically so none can drift into a stale state.
        "--max-requests", "1000",
        "--max-requests-jitter", "100",
        # A slow request eventually returns instead of hanging forever.
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
