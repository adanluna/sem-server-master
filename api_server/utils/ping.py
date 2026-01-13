import platform
import subprocess
import shutil
import socket


def _tcp_probe(ip: str, port: int, timeout: float = 0.8) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def ping_camara(ip: str, timeout: int = 1) -> bool:
    """
    Verifica si un dispositivo está accesible.
    - 1) ICMP ping (si existe el binario)
    - 2) Fallback TCP (RTSP/HTTP/HTTPS) si no hay ping o falla
    """
    # ---------- 1) ICMP ----------
    ping_bin = shutil.which("ping")
    if ping_bin:
        system = platform.system().lower()

        # Linux en Debian/Ubuntu: -W es timeout en segundos (por paquete)
        # Windows: -w es timeout en ms
        if system == "windows":
            cmd = [ping_bin, "-n", "1", "-w", str(timeout * 1000), ip]
        else:
            cmd = [ping_bin, "-c", "1", "-W", str(timeout), ip]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout + 1
            )
            if result.returncode == 0:
                return True
        except Exception:
            # si falla ping por permisos/caps/timeout, seguimos a TCP
            pass

    # ---------- 2) TCP fallback ----------
    # Cámaras: RTSP 554 suele ser el mejor indicador real.
    for port in (554, 80, 443):
        if _tcp_probe(ip, port, timeout=float(timeout)):
            return True

    return False
