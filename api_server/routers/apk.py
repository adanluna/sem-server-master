from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
import ipaddress
import os
import logging
from datetime import datetime, timezone

# sudo mkdir -p /opt/semefo/apks
# sudo chown -R semefo:semefo /opt/semefo/apks
# scp build/app/outputs/flutter-apk/app-release.apk semefo@172.21.82.2:/opt/semefo/apks/semefo-app.apk

router = APIRouter(prefix="/apk", tags=["apk"])
logger = logging.getLogger("apk")

_networks_str = os.getenv("ALLOWED_NETWORKS", "172.21.82.0/24")
ALLOWED_NETWORKS = [
    ipaddress.ip_network(net.strip())
    for net in _networks_str.split(",")
    if net.strip()
]

APK_PATH = os.getenv("APK_PATH", "/opt/semefo/apks/semefo-app.apk")
APK_DOWNLOAD_NAME = os.getenv("APK_DOWNLOAD_NAME", "semefo-app.apk")


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


def _verificar_acceso_apk(request: Request) -> str:
    client_ip = get_client_ip(request)
    if not ip_autorizada(client_ip):
        logger.warning(f"[APK] DENY ip={client_ip}")
        raise HTTPException(status_code=403, detail="IP no autorizada")
    if not os.path.isfile(APK_PATH):
        logger.error(f"[APK] NOT_FOUND ip={client_ip} path={APK_PATH}")
        raise HTTPException(
            status_code=404, detail="APK no encontrado en el servidor"
        )
    return client_ip


def _format_size(num_bytes: int) -> str:
    mb = num_bytes / (1024 * 1024)
    if mb >= 1:
        return f"{mb:.1f} MB"
    kb = num_bytes / 1024
    return f"{kb:.0f} KB"


def _format_mtime(path: str) -> str:
    ts = os.path.getmtime(path)
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()
    return dt.strftime("%d/%m/%Y %H:%M")


@router.get("/download", response_class=HTMLResponse)
def pagina_descarga_apk(request: Request):
    """Página con botón de descarga (no fuerza descarga automática)."""
    client_ip = _verificar_acceso_apk(request)
    stat = os.stat(APK_PATH)
    size_label = _format_size(stat.st_size)
    updated_label = _format_mtime(APK_PATH)

    logger.info(f"[APK] PAGE ip={client_ip} file={APK_PATH}")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Descargar SEMEFO App</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: linear-gradient(145deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
      color: #e2e8f0;
      padding: 24px;
    }}
    .card {{
      width: 100%;
      max-width: 440px;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 16px;
      padding: 32px 28px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.45);
      text-align: center;
    }}
    .logo {{
      font-size: 1.75rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      color: #38bdf8;
      margin-bottom: 8px;
    }}
    h1 {{
      font-size: 1.25rem;
      font-weight: 600;
      margin: 0 0 8px;
      color: #f8fafc;
    }}
    .subtitle {{
      font-size: 0.95rem;
      color: #94a3b8;
      margin: 0 0 24px;
      line-height: 1.5;
    }}
    .meta {{
      font-size: 0.85rem;
      color: #64748b;
      margin-bottom: 28px;
      line-height: 1.6;
    }}
    .btn {{
      display: inline-block;
      width: 100%;
      padding: 16px 24px;
      font-size: 1.05rem;
      font-weight: 700;
      color: #0f172a;
      background: #38bdf8;
      border: none;
      border-radius: 10px;
      text-decoration: none;
      cursor: pointer;
      transition: background 0.15s ease, transform 0.1s ease;
    }}
    .btn:hover {{
      background: #7dd3fc;
    }}
    .btn:active {{
      transform: scale(0.98);
    }}
    .hint {{
      margin-top: 20px;
      font-size: 0.8rem;
      color: #64748b;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <main class="card">
    <div class="logo">SEMEFO</div>
    <h1>App para tablets</h1>
    <p class="subtitle">
      Instale la aplicación oficial de grabación forense en su dispositivo Android.
    </p>
    <p class="meta">
      Archivo: <strong>{APK_DOWNLOAD_NAME}</strong><br />
      Tamaño: {size_label}<br />
      Actualizado: {updated_label}
    </p>
    <a class="btn" href="/apk/file" download="{APK_DOWNLOAD_NAME}">
      Descargar APK
    </a>
    <p class="hint">
      Tras descargar, abra el archivo en la tablet y permita la instalación
      de orígenes desconocidos si el sistema lo solicita.
    </p>
  </main>
</body>
</html>"""
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


@router.get("/file")
def descargar_apk_archivo(request: Request):
    """Entrega el binario APK (invocado desde el botón de la página)."""
    client_ip = _verificar_acceso_apk(request)
    logger.info(f"[APK] DOWNLOAD ip={client_ip} file={APK_PATH}")
    resp = FileResponse(
        APK_PATH,
        media_type="application/vnd.android.package-archive",
        filename=APK_DOWNLOAD_NAME,
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp
