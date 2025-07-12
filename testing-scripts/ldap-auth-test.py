import os
from dotenv import load_dotenv
from ldap3 import Server, Connection, ALL, core

# Cargar variables de entorno
load_dotenv(dotenv_path="../.env")

ldap_server_ip = os.getenv("LDAP_SERVER_IP", "192.168.1.211")
ldap_port = int(os.getenv("LDAP_PORT", "389"))
domain = os.getenv("LDAP_DOMAIN", "semefo.local")

print(f"🔍 Configuración LDAP:")
print(f"   Servidor: {ldap_server_ip}:{ldap_port}")
print(f"   Dominio: {domain}")

# Solicitar credenciales de prueba
username = input("\n👤 Ingresa un usuario para probar: ")
password = input("🔐 Ingresa la contraseña: ")


def test_ldap_auth(username, password):
    user_bind = f"{username}@{domain}"

    # Calcular base DN
    try:
        parts = domain.split(".")
        base_dn = ",".join([f"dc={part}" for part in parts])
    except Exception as e:
        print(f"❌ Error procesando dominio: {e}")
        return False

    try:
        print(f"\n🔍 Intentando autenticar: {user_bind}")
        print(f"🔍 Base DN: {base_dn}")

        server = Server(ldap_server_ip, port=ldap_port, get_info=ALL)
        conn = Connection(server, user=user_bind,
                          password=password, auto_bind=True)

        print("✅ Autenticación exitosa!")

        # Buscar información del usuario
        print("🔍 Buscando información del usuario...")
        conn.search(base_dn,
                    f'(sAMAccountName={username})',
                    attributes=['displayName', 'mail', 'memberOf'])

        if conn.entries:
            for entry in conn.entries:
                print(f"📋 Información del usuario:")
                print(
                    f"   Nombre: {entry.displayName.value if entry.displayName else 'No disponible'}")
                print(
                    f"   Email: {entry.mail.value if entry.mail else 'No disponible'}")
                print(
                    f"   Grupos: {len(entry.memberOf) if entry.memberOf else 0} grupos encontrados")
        else:
            print("⚠️ Usuario autenticado pero no se encontró información adicional")

        conn.unbind()
        return True

    except core.exceptions.LDAPBindError:
        print(f"❌ Error de autenticación: Credenciales inválidas")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


# Ejecutar prueba
test_ldap_auth(username, password)
