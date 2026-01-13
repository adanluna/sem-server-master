import platform
import subprocess
import shutil
import traceback
from datetime import datetime, timezone
from fastapi import HTTPException, Query


def _clamp_int(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _ping_probe(ip: str, timeout: int = 1, retries: int = 2) -> dict:
    """
    Ejecuta ping ICMP contra la IP.
    Devuelve dict:
      {
        "online": bool,
        "metodo": "icmp:<attempt>" | "icmp_fail" | "no-ping-bin",
        "debug": {...}
      }
    """
    debug = {}
    ping_bin = shutil.which("ping")
    debug["ping_bin"] = ping_bin
    debug["platform"] = platform.system().lower()
    debug["timeout"] = timeout
    debug["retries"] = retries

    if not ping_bin:
        return {"online": False, "metodo": "no-ping-bin", "debug": debug}

    for attempt in range(1, retries + 1):
        if debug["platform"] == "windows":
            # Windows: -n 1 (un ping), -w ms
            cmd = [ping_bin, "-n", "1", "-w", str(timeout * 1000), ip]
        else:
            # Linux (iputils): -n no DNS, -c 1 un ping, -W timeout por respuesta (segundos)
            cmd = [ping_bin, "-n", "-c", "1", "-W", str(timeout), ip]

        debug[f"icmp_cmd_{attempt}"] = cmd

        # OJO: subprocess timeout un poco mayor que -W para capturar salida/retorno
        r = subprocess.run(cmd, capture_output=True,
                           text=True, timeout=timeout + 2)

        debug[f"icmp_rc_{attempt}"] = r.returncode
        debug[f"icmp_stdout_{attempt}"] = (r.stdout or "").strip()[:500]
        debug[f"icmp_stderr_{attempt}"] = (r.stderr or "").strip()[:500]

        if r.returncode == 0:
            return {"online": True, "metodo": f"icmp:{attempt}", "debug": debug}

    return {"online": False, "metodo": "icmp_fail", "debug": debug}
