import socket
import platform
import subprocess


def _tcp_ping(ip: str, port: int, timeout: int = 2) -> bool:
    """
    Verifica si un puerto TCP responde (más fiable que ICMP).
    """
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def ping_camara(ip: str, timeout: int = 2) -> bool:
    """
    Verifica si una cámara está ONLINE desde server master.

    Prioridad:
    1) RTSP (554)  ← criterio REAL
    2) HTTP (80 / 443)
    3) ICMP (solo como último fallback)
    """

    # 1️⃣ RTSP (lo que importa para SEMEFO)
    if _tcp_ping(ip, 554, timeout):
        return True

    # 2️⃣ Web UI (opcional)
    if _tcp_ping(ip, 80, timeout):
        return True

    if _tcp_ping(ip, 443, timeout):
        return True

    # 3️⃣ ICMP (último recurso)
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), ip]
    else:
        cmd = ["ping", "-c", "1", "-W", str(timeout), ip]

    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return result.returncode == 0
