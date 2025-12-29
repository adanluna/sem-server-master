import os
import requests
import threading
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_SERVER_URL").rstrip("/")
HOSTNAME = os.getenv("WORKER_HOSTNAME", os.uname().nodename)
QUEUE = os.getenv("QUEUE_NAME", None)

HEARTBEAT_INTERVAL = 30  # segundos


def send_heartbeat(worker: str, status: str, pid: int, queue: str | None = None):
    try:
        requests.post(
            f"{API_URL}/infra/heartbeat",
            json={
                "worker": worker,
                "host": HOSTNAME,
                "queue": queue,
                "pid": pid,
                "status": status
            },
            timeout=3
        )
    except Exception as e:
        print(f"[HEARTBEAT] error: {e}")


def start_listening_heartbeat(worker, queues):
    pid = os.getpid()

    def loop():
        while True:
            send_heartbeat(
                worker=worker,
                status="listening",
                pid=pid,
                queues=queues
            )
            time.sleep(HEARTBEAT_INTERVAL)

    threading.Thread(target=loop, daemon=True).start()
