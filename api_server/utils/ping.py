import subprocess
import platform


def ping_ip(ip: str, timeout: int = 1) -> bool:
    """
    Ping ICMP simple para verificar si un dispositivo está accesible en red.
    NO usa credenciales, NO consume APIs de la cámara.
    """
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
