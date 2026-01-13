import platform
import subprocess
import shutil
import socket
from datetime import datetime, timezone
from fastapi import HTTPException


def _tcp_probe(ip: str, port: int, timeout: float = 0.8) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def ping_camara(ip: str, timeout: int = 1) -> dict:
    debug = {}

    ping_bin = shutil.which("ping")
    debug["ping_bin"] = ping_bin
    debug["platform"] = platform.system().lower()

    # 1) ICMP
    if ping_bin:
        cmd = [ping_bin, "-n", "-c", "1", "-W", str(timeout), ip]
        cmd_fallback = [ping_bin, "-n", "-c", "1", "-w", str(timeout), ip]
        debug["icmp_cmd"] = cmd

        try:
            r = subprocess.run(cmd, capture_output=True,
                               text=True, timeout=timeout + 1)
            debug["icmp_rc"] = r.returncode
            debug["icmp_stdout"] = (r.stdout or "").strip()[:500]
            debug["icmp_stderr"] = (r.stderr or "").strip()[:500]

            if r.returncode == 0:
                return {"online": True, "metodo": "icmp", "debug": debug}
        except Exception as e:
            debug["icmp_exc"] = str(e)

    # 2) TCP fallback (si ICMP no está o falla)
    for port in (554, 80, 443):
        ok = _tcp_probe(ip, port, timeout=float(timeout))
        debug[f"tcp_{port}"] = ok
        if ok:
            return {"online": True, "metodo": f"tcp:{port}", "debug": debug}

    return {"online": False, "metodo": "none", "debug": debug}
