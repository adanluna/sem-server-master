
import json
import os
from services.api_service import ApiService
from services.config_service import ConfigService
import sys
# Agregar el directorio app-desktop al path ANTES de importar
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app-desktop"))


# AHORA importar los servicios (después de agregar el path)

print("🔍 Debug: Verificando sesiones pendientes para forense1")

# Configuración
config_service = ConfigService("config.json")
config = config_service.load_config()

if not config:
    print("❌ No se pudo cargar config.json")
    exit(1)

api_config = config.get('api', {})
api_server = api_config.get('server_ip', '').strip()
username = "forense1"

print(f"📡 API Server: {api_server}")
print(f"👤 Username: {username}")

# Usar ApiService
api_service = ApiService()

# Verificar sesiones pendientes
print(f"\n🔍 Llamando a endpoint: /usuarios/{username}/sesion_pendiente")
endpoint = f"/usuarios/{username}/sesion_pendiente"
response = api_service.make_request('GET', endpoint, server=api_server)

print(f"📋 Respuesta completa:")
print(json.dumps(response, indent=2, default=str))

if response and response.get('success', False):
    session_data = response.get('data', {})
    print(f"\n✅ Datos de sesión:")
    print(f"   Pendiente: {session_data.get('pendiente', False)}")

    if session_data.get('pendiente', False):
        print(f"   ID Sesión: {session_data.get('id_sesion')}")
        print(f"   Expediente: {session_data.get('numero_expediente')}")
        print(f"   Nombre: {session_data.get('nombre_sesion')}")
        print(f"   Plancha: {session_data.get('plancha')}")
        print(f"   Tablet: {session_data.get('tablet')}")
        print(f"   Estado: {session_data.get('estado')}")
    else:
        print("   ℹ️ No hay sesiones pendientes")
else:
    print(
        f"❌ Error en la respuesta: {response.get('error') if response else 'Sin respuesta'}")
