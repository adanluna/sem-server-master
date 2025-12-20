import os
from ldap3 import Server, Connection, ALL


def ldap_authenticate(username: str, password: str):
    LDAP_HOST = os.getenv("LDAP_SERVER_IP")
    LDAP_PORT = int(os.getenv("LDAP_PORT", 389))
    user_principal = f"{username}@fiscalianl.gob"

    try:
        server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)
        conn = Connection(
            server,
            user=user_principal,
            password=password,
            authentication="SIMPLE",
            auto_bind=False
        )

        try:
            conn.start_tls()
        except:
            pass

        if not conn.bind():
            return {"success": False, "message": "Credenciales inválidas"}

        search_base = "DC=fiscalianl,DC=gob"
        conn.search(
            search_base,
            f"(sAMAccountName={username})",
            attributes=["displayName", "mail"]
        )

        info = {}
        if conn.entries:
            e = conn.entries[0]
            info = {
                "displayName": str(e.displayName) if "displayName" in e else None,
                "mail": str(e.mail) if "mail" in e else None
            }

        conn.unbind()

        return {
            "success": True,
            "message": "Autenticación correcta",
            "user": {"username": username, **info}
        }

    except Exception as e:
        return {"success": False, "message": f"Error LDAP: {e}"}


def ldap_user_info(username: str):
    LDAP_HOST = os.getenv("LDAP_SERVER_IP")
    LDAP_PORT = int(os.getenv("LDAP_PORT", 389))

    try:
        server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)
        conn = Connection(server, auto_bind=True)

        search_base = "DC=fiscalianl,DC=gob"
        conn.search(
            search_base,
            f"(sAMAccountName={username})",
            attributes=["displayName", "userPrincipalName"]
        )

        if not conn.entries:
            return {"error": "Usuario no encontrado"}

        e = conn.entries[0]
        return {
            "username": username,
            "displayName": str(e.displayName),
            "userPrincipalName": str(e.userPrincipalName)
        }

    except Exception as e:
        return {"error": str(e)}
