import os
import socket
from dotenv import load_dotenv
from ldap3 import Server, Connection, ALL, NTLM, core

# Cargar variables de entorno (ajusta si tu .env no está un nivel arriba)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

LDAP_SERVER_IP = os.getenv("LDAP_SERVER_IP", "192.168.1.211").strip()
LDAP_PORT = int(os.getenv("LDAP_PORT", "389"))
LDAP_USE_SSL = os.getenv(
    "LDAP_USE_SSL", "false").lower() in ("1", "true", "yes")
LDAP_DOMAIN = os.getenv("LDAP_DOMAIN", "semefo.local").strip()

print("🔍 Configuración LDAP")
print(f"   Servidor: {LDAP_SERVER_IP}:{LDAP_PORT}  use_ssl={LDAP_USE_SSL}")
print(f"   Dominio:  {LDAP_DOMAIN}")

username = input("\n👤 Usuario (solo sAMAccountName, ej. forense1): ").strip()
password = input("🔐 Contraseña: ")


def base_dn_from_domain(domain: str) -> str:
    parts = [p for p in domain.split(".") if p]
    return ",".join([f"dc={p}" for p in parts]) if parts else ""


def parse_ad_invalid_message(msg: str) -> str:
    # AD suele poner "data 52e", "data 775", "data 532", etc.
    # Mapeo útil:
    # 525 user not found, 52e invalid creds, 530 not permitted to logon at this time,
    # 531 not permitted to logon at this workstation, 532 password expired,
    # 533 account disabled, 701 account expired, 773 user must reset password,
    # 775 user account locked
    codes = {
        "525": "Usuario no existe",
        "52e": "Credenciales inválidas",
        "530": "Logon no permitido en este horario",
        "531": "Logon no permitido en este equipo",
        "532": "Contraseña expirada",
        "533": "Cuenta deshabilitada",
        "701": "Cuenta expirada",
        "773": "Debe cambiar la contraseña",
        "775": "Cuenta bloqueada",
    }
    msg_low = (msg or "").lower()
    for k, v in codes.items():
        if f"data {k}" in msg_low:
            return f"{v} (data {k})"
    return msg or "Sin mensaje adicional del servidor"


def check_tcp(host: str, port: int, timeout=4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception as e:
        print(f"⚠️  No se pudo abrir conexión TCP a {host}:{port} ({e})")
        return False


def make_server():
    return Server(LDAP_SERVER_IP, port=LDAP_PORT, use_ssl=LDAP_USE_SSL, get_info=ALL, connect_timeout=6)


def try_bind(user: str, auth=None, start_tls=False):
    srv = make_server()
    conn = Connection(srv, user=user, password=password,
                      authentication=auth, raise_exceptions=False)
    opened = conn.open()
    tls_ok = None
    if start_tls and opened:
        try:
            tls_ok = conn.start_tls()
        except Exception:
            tls_ok = False
    bind_ok = conn.bind()

    result = conn.result or {}
    code = result.get("result")
    desc = result.get("description")
    message = result.get("message", "")
    last_error = getattr(conn, "last_error", "")

    print("\n--- Intento de bind --------------------------------")
    print(f"user: {user!r}  auth: {'NTLM' if auth==NTLM else 'SIMPLE'}  startTLS: {bool(start_tls)}  use_ssl: {LDAP_USE_SSL}")
    print(f"open: {opened}  start_tls: {tls_ok}  bind_ok: {bind_ok}")
    print(f"result code: {code}  description: {desc}")
    print(f"message: {message}")
    print(f"last_error: {last_error}")
    if str(code) == "49":  # invalidCredentials
        print(f"AD detail: {parse_ad_invalid_message(message or last_error)}")
    conn.unbind()
    return bind_ok, code, desc, message or last_error


try:
    from Crypto.Hash import MD4 as _MD4  # pycryptodome
    HAS_MD4 = True
except Exception:
    HAS_MD4 = False


def main():
    if not check_tcp(LDAP_SERVER_IP, LDAP_PORT):
        print("❌ No hay conectividad TCP al servidor/puerto indicado.")
        return

    base_dn = base_dn_from_domain(LDAP_DOMAIN)
    upn_user = username if "@" in username else f"{username}@{LDAP_DOMAIN}"
    netbios = LDAP_DOMAIN.split(".")[0].upper() if LDAP_DOMAIN else ""
    ntlm_user = f"{netbios}\\{username}" if netbios else username

    print(f"\n🔍 Base DN: {base_dn or '(no calculado)'}")

    # 1) UPN + StartTLS (solo si no es LDAPS)
    if not LDAP_USE_SSL:
        ok, code, _, _ = try_bind(upn_user, auth=None, start_tls=True)
        if ok:
            print("✅ Autenticación exitosa con UPN + StartTLS")
            return

    # 2) UPN simple / LDAPS
    ok, code, _, _ = try_bind(upn_user, auth=None, start_tls=False)
    if ok:
        print("✅ Autenticación exitosa con UPN")
        return

    # 3) NTLM DOMAIN\\user (solo si hay MD4 disponible)
    if HAS_MD4:
        ok, code, _, _ = try_bind(ntlm_user, auth=NTLM, start_tls=False)
        if ok:
            print("✅ Autenticación exitosa con NTLM")
            return
    else:
        print("\nℹ️ NTLM omitido: falta soporte MD4. Instala pycryptodome: pip install pycryptodome")

    print("\n❌ No fue posible autenticar. Revisa:")
    print("- Usuario en formato UPN (forense1@semefo.local) o NTLM (SEMEFO\\forense1)")
    print("- Si el servidor requiere canal seguro: usa LDAPS (LDAP_USE_SSL=true, puerto 636) o StartTLS")
    print("- Que la contraseña sea correcta (sin espacios extra)")
    print("- Políticas AD: contraseña expirada/bloqueada (ver mensaje AD arriba)")


if __name__ == "__main__":
    main()
