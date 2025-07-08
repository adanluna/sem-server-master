import os
from dotenv import load_dotenv
import socket

# Cargar variables de entorno
load_dotenv(dotenv_path=".env.local")

ldap_server = os.getenv("LDAP_SERVER_IP")
ldap_port = int(os.getenv("LDAP_PORT", "389"))

print(f"🔍 Probando conexión a: {ldap_server}:{ldap_port}")

try:
    # Resolver el hostname a IP
    ip = socket.gethostbyname(ldap_server)
    print(f"📍 IP resuelta: {ip}")

    # Probar conexión TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    result = sock.connect_ex((ldap_server, ldap_port))
    sock.close()

    if result == 0:
        print("✅ Conexión exitosa al servidor LDAP")
    else:
        print(f"❌ No se puede conectar - Error código: {result}")

except socket.gaierror as e:
    print(f"❌ Error resolviendo hostname: {e}")
except Exception as e:
    print(f"❌ Error de conexión: {e}")
