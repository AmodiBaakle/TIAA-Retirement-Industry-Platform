import subprocess
import sys

PORT = 8001
PROJECT_NAME = "TIAA"

def kill_existing_process(port):
    try:
        subprocess.run(f"kill -9 $(lsof -ti:{port})", shell=True, check=True)
        print(f"Killed existing process on port {port}")
    except subprocess.CalledProcessError:
        print(f"No process found running on port {port}")


def run_gunicorn(daemon=False):
    kill_existing_process(PORT)
    command = ["gunicorn", "--bind", f"0.0.0.0:{PORT}", f"{PROJECT_NAME}.wsgi:application"]
    if daemon:
        command.append("--daemon")
    print(f"Running command: {' '.join(command)}")
    subprocess.call(command)


if __name__ == "__main__":
    daemon_mode = "-d" in sys.argv or "--daemon" in sys.argv
    run_gunicorn(daemon=daemon_mode)
