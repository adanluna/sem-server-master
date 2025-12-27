import os
from fastapi import Header, HTTPException, Depends
import hashlib
import secrets
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import timedelta, datetime, timezone

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "dev_inseguro")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_ISSUER = os.getenv("JWT_ISSUER", "semefo-api")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "semefo")

AUTH_ENFORCE = os.getenv("AUTH_ENFORCE", "0") == "1"

ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
REFRESH_TOKEN_HOURS = int(os.getenv("REFRESH_TOKEN_HOURS", "12"))
SERVICE_TOKEN_HOURS = int(os.getenv("SERVICE_TOKEN_HOURS", "24"))


def _now_utc():
    return datetime.now(timezone.utc)


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def create_access_token(sub: str, roles: list[str], ttl_minutes: int):
    jti = secrets.token_urlsafe(16)
    payload = {
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "sub": sub,
        "roles": roles,
        "type": "access",
        "jti": jti,
        "iat": int(_now_utc().timestamp()),
        "exp": int((_now_utc() + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def create_refresh_token(sub: str, roles: list[str], ttl_hours: int):
    jti = secrets.token_urlsafe(20)
    raw = secrets.token_urlsafe(48)
    # refresh real que regresas al cliente:
    refresh_token = f"{jti}.{raw}"

    # lo que guardas en DB (hash):
    token_hash = _sha256(refresh_token)
    expires_at = _now_utc() + timedelta(hours=ttl_hours)

    return refresh_token, jti, token_hash, expires_at


def decode_token(token: str):
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALG],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER
    )


def get_current_principal(authorization: str = Header(default=None)):
    if not authorization:
        if AUTH_ENFORCE:
            raise HTTPException(status_code=401, detail="Falta Authorization")
        return {"sub": "anon", "roles": ["anon"]}

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization inválido")

    token = authorization.split(" ", 1)[1].strip()

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=401, detail="Token inválido (type)")
        return {"sub": payload.get("sub"), "roles": payload.get("roles", [])}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido/expirado")


def require_roles(*allowed: str):
    def dep(principal=Depends(get_current_principal)):
        roles = set(principal.get("roles", []))
        if AUTH_ENFORCE and not roles.intersection(set(allowed)):
            raise HTTPException(status_code=403, detail="Sin permisos")
        return principal
    return dep
