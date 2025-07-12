import os
from dotenv import load_dotenv
import socket
import subprocess

# Debug: Mostrar información de rutas
print("🔍 Información de rutas:")
print(f"   Directorio actual: {os.getcwd()}")
print(f"   Archivo script: {__file__}")
print(f"   Directorio del script: {os.path.dirname(__file__)}")

# Cargar variables de entorno - ajustar la ruta correcta
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
print(f"   Ruta del .env: {env_path}")
print(f"   ¿Existe el archivo? {os.path.exists(env_path)}")

# Listar archivos .env en el directorio padre
parent_dir = os.path.dirname(os.path.dirname(__file__))
print(f"   Directorio padre: {parent_dir}")
env_files = [f for f in os.listdir(parent_dir) if f.startswith('.env')]
print(f"   Archivos .env encontrados: {env_files}")

load_dotenv(dotenv_path=env_path)

# Verificar que las variables se cargaron
ldap_server = os.getenv("LDAP_SERVER_IP")
ldap_port = os.getenv("LDAP_PORT")
ldap_domain = os.getenv("LDAP_DOMAIN")

print(f"\n🔍 Variables de entorno cargadas:")
print(f"   LDAP_SERVER_IP: {ldap_server}")
print(f"   LDAP_PORT: {ldap_port}")
print(f"   LDAP_DOMAIN: {ldap_domain}")

if not ldap_server:
    print("\n❌ Error: LDAP_SERVER_IP no está definido")
    print("📋 Contenido del archivo .env.local:")
    try:
        with open(env_path, 'r') as f:
            print(f.read())
    except FileNotFoundError:
        print("   ❌ Archivo .env.local no encontrado")
    except Exception as e:
        print(f"   ❌ Error leyendo archivo: {e}")
    exit(1)

ldap_ports = [389, 636, 3268, 3269]  # Puertos comunes de LDAP

print(f"\n🔍 Probando conexión a servidor: {ldap_server}")

try:
    # Resolver el hostname a IP
    ip = socket.gethostbyname(ldap_server)
    print(f"📍 IP resuelta: {ip}")

    # Hacer ping básico
    print("\n🏓 Probando conectividad básica...")
    ping_result = subprocess.run(['ping', '-c', '3', ldap_server],
                                 capture_output=True, text=True, timeout=10)
    if ping_result.returncode == 0:
        print("✅ Servidor responde a ping")
        # Mostrar tiempo de respuesta
        lines = ping_result.stdout.split('\n')
        for line in lines:
            if 'time=' in line:
                print(f"   📶 {line.strip()}")
    else:
        print("❌ Servidor no responde a ping")
        print(f"   Error: {ping_result.stderr}")

    # Probar múltiples puertos LDAP
    print(f"\n🔍 Probando puertos LDAP...")
    for port in ldap_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((ldap_server, port))
            sock.close()

            if result == 0:
                print(f"✅ Puerto {port} - ABIERTO")
            else:
                print(f"❌ Puerto {port} - CERRADO")
        except Exception as e:
            print(f"❌ Puerto {port} - Error: {e}")

    # Usar netcat para verificar conectividad
    print(f"\n🔧 Verificación adicional con netcat...")
    for port in [389, 636]:
        try:
            nc_result = subprocess.run(['nc', '-zv', ldap_server, str(port)],
                                       capture_output=True, text=True, timeout=5)
            if nc_result.returncode == 0:
                print(f"✅ nc - Puerto {port} accesible")
            else:
                print(f"❌ nc - Puerto {port} no accesible")
        except subprocess.TimeoutExpired:
            print(f"⏰ nc - Timeout en puerto {port}")
        except Exception as e:
            print(f"❌ nc - Error probando puerto {port}: {e}")

except socket.gaierror as e:
    print(f"❌ Error resolviendo hostname: {e}")
except Exception as e:
    print(f"❌ Error general: {e}")

print(f"\n📋 Resumen:")
print(f"   Servidor: {ldap_server}")
print(f"   Puerto configurado: {ldap_port}")
print(f"   Dominio: {ldap_domain}")
