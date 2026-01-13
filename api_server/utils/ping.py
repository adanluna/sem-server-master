import platform
import subprocess
import shutil


def _ping_probe(ip: str, timeout: int = 1, retries: int = 2) -> dict:
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
            cmd = [ping_bin, "-n", "1", "-w", str(timeout * 1000), ip]
        else:
            cmd = [ping_bin, "-n", "-c", "1", "-W", str(timeout), ip]

        debug[f"icmp_cmd_{attempt}"] = cmd

        r = subprocess.run(cmd, capture_output=True,
                           text=True, timeout=timeout + 2)
        debug[f"icmp_rc_{attempt}"] = r.returncode
        debug[f"icmp_stdout_{attempt}"] = (r.stdout or "").strip()[:300]
        debug[f"icmp_stderr_{attempt}"] = (r.stderr or "").strip()[:300]

        if r.returncode == 0:
            return {"online": True, "metodo": f"icmp:{attempt}", "debug": debug}

    return {"online": False, "metodo": "icmp_fail", "debug": debug}
