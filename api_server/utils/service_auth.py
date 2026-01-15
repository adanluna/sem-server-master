import ipaddress
from typing import Optional, Set

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import func

from api_server.database import get_db
from api_server import models

bearer = HTTPBearer(auto_error=False)


def _parse_roles(roles_str: str) -> Set[str]:
    # roles guardados como "role1,role2" o "role1 role2"
    raw = (roles_str or "").replace(" ", ",")
    return {r.strip() for r in raw.split(",") if r.strip()}


def _ip_allowed(client_ip: str, allowed_ips: Optional[str]) -> bool:
    """
    allowed_ips:
      - NULL/empty => permite cualquiera
      - lista separada por coma/espacio:
          "172.21.82.4, 172.21.82.0/24, 10.0.0.10"
    """
    if not allowed_ips:
        return True

    ip = ipaddress.ip_address(client_ip)
    parts = allowed_ips.replace(" ", ",").split(",")

    for p in parts:
        p = p.strip()
        if not p:
            continue
        try:
            if "/" in p:
                net = ipaddress.ip_network(p, strict=False)
                if ip in net:
                    return True
            else:
                if ip == ipaddress.ip_address(p):
                    return True
        except ValueError:
            # Si alguien metió basura en allowed_ips, no truena el API;
            # pero por seguridad, NO autoriza por esa entrada.
            continue

    return False


def require_service_bearer(*required_roles: str):
    """
    ✅ Implementación tal cual pediste:
    Authorization: Bearer <client_secret_hash>
    Se valida buscando un service_client cuyo client_secret_hash coincida EXACTO.
    """

    async def _dep(
        request: Request,
        creds: HTTPAuthorizationCredentials = Depends(bearer),
        db: Session = Depends(get_db),
    ):
        if not creds or creds.scheme.lower() != "bearer" or not creds.credentials:
            raise HTTPException(status_code=401, detail="Missing Bearer token")

        token = creds.credentials.strip()
        client_ip = request.client.host if request.client else "0.0.0.0"

        sc = (
            db.query(models.ServiceClient)
            .filter(
                models.ServiceClient.activo.is_(True),
                models.ServiceClient.client_secret_hash == token,
            )
            .first()
        )

        if not sc:
            # Importante: no revelar si existe o no
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not _ip_allowed(client_ip, sc.allowed_ips):
            raise HTTPException(status_code=403, detail="IP not allowed")

        if required_roles:
            roles = _parse_roles(sc.roles)
            if not any(r in roles for r in required_roles):
                raise HTTPException(
                    status_code=403, detail="Insufficient role")

        # actualizar last_used_at (sin romper si hay concurrencia)
        sc.last_used_at = func.now()
        db.commit()

        # retornamos el service client por si quieres loguear client_id (sin token)
        return sc

    return _dep


# ------------------------------------------------------------
# ✅ VARIANTE RECOMENDADA (más segura) por si la adoptas luego:
# Authorization: Bearer <client_id>:<secret>
# (o Bearer base64(client_id:secret))
# ------------------------------------------------------------
def require_service_bearer_clientid_secret(*required_roles: str):
    async def _dep(
        request: Request,
        creds: HTTPAuthorizationCredentials = Depends(bearer),
        db: Session = Depends(get_db),
    ):
        if not creds or creds.scheme.lower() != "bearer" or not creds.credentials:
            raise HTTPException(status_code=401, detail="Missing Bearer token")

        raw = creds.credentials.strip()
        if ":" not in raw:
            raise HTTPException(status_code=401, detail="Invalid token format")

        client_id, secret = raw.split(":", 1)
        client_id = client_id.strip()
        secret = secret.strip()

        if not client_id or not secret:
            raise HTTPException(status_code=401, detail="Invalid token format")

        client_ip = request.client.host if request.client else "0.0.0.0"

        sc = (
            db.query(models.ServiceClient)
            .filter(models.ServiceClient.activo.is_(True), models.ServiceClient.client_id == client_id)
            .first()
        )
        if not sc:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # aquí compararías secret vs sc.client_secret_hash con bcrypt insight
        # ejemplo si usas passlib (lo mismo que tu pwd_context):
        # if not pwd_context.verify(secret, sc.client_secret_hash):
        #    raise HTTPException(status_code=401, detail="Invalid credentials")

        if not _ip_allowed(client_ip, sc.allowed_ips):
            raise HTTPException(status_code=403, detail="IP not allowed")

        if required_roles:
            roles = _parse_roles(sc.roles)
            if not any(r in roles for r in required_roles):
                raise HTTPException(
                    status_code=403, detail="Insufficient role")

        sc.last_used_at = func.now()
        db.commit()
        return sc

    return _dep
