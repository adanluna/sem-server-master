from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse
import ipaddress
import os
import logging
# sudo mkdir -p /opt/semefo/apks
# sudo chown -R semefo:semefo /opt/semefo/apks
# scp build/app/outputs/flutter-apk/app-release.apk semefo@172.21.82.2:/opt/semefo/apks/semefo-app.apk

router = APIRouter(prefix="/apk", tags=["apk"])
logger = logging.getLogger("apk")

_networks_str = os.getenv("ALLOWED_NETWORKS", "172.21.82.0/24")
ALLOWED_NETWORKS = [ipaddress.ip_network(
    net.strip()) for net in _networks_str.split(",") if net.strip()]

APK_PATH = os.getenv("APK_PATH", "/opt/semefo/apks/semefo-app.apk")


def get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host


def ip_autorizada(client_ip: str) -> bool:
    try:
        ip = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    return any(ip in net for net in ALLOWED_NETWORKS)


@router.get("/download")
def descargar_apk(request: Request):
    client_ip = get_client_ip(request)

    if not ip_autorizada(client_ip):
        logger.warning(f"[APK] DENY ip={client_ip}")
        raise HTTPException(status_code=403, detail="IP no autorizada")

    if not os.path.isfile(APK_PATH):
        logger.error(f"[APK] NOT_FOUND ip={client_ip} path={APK_PATH}")
        raise HTTPException(
            status_code=404, detail="APK no encontrado en el servidor")

    logger.info(f"[APK] DOWNLOAD ip={client_ip} file={APK_PATH}")
    resp = FileResponse(
        APK_PATH,
        media_type="application/vnd.android.package-archive",
        filename="semefo-app.apk",
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp
