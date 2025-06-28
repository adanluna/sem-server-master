import subprocess
import sys
import os


def run_app_desktop():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    desktop_main = os.path.join(current_dir, "app-desktop", "main.py")
    subprocess.run([sys.executable, desktop_main])


if __name__ == "__main__":
    run_app_desktop()
