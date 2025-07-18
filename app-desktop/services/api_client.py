import requests
import logging
# 🚀 Asegurar que tiene estos imports
from typing import Dict, Any, Optional, Union
import json


class ApiClient:
    def __init__(self, config_service, timeout: int = 10):
        """
        Cliente centralizado para todas las operaciones del API
        """
        self.config_service = config_service
        self.timeout = timeout
        self.base_url = None
        # No cargar la URL en __init__, hacerlo bajo demanda
        print(f"🔧 ApiClient inicializado")

    def _load_api_url(self):
        """Cargar la URL del API desde la configuración"""
        try:
            print(f"🔍 Cargando URL del API...")

            if not self.config_service:
                raise Exception("Config service no disponible")

            config = self.config_service.load_config()
            print(f"🔍 Config cargado: {config is not None}")

            if not config:
                raise Exception("No se ha cargado la configuración.")

            api_config = config.get('api', {})
            print(f"🔍 API config: {api_config}")

            api_server = api_config.get('server_ip', '')
            print(f"🔍 API server: {api_server}")

            if not api_server:
                raise Exception("No se ha configurado la IP del API.")

            # Asegurar que tiene el protocolo
            if not api_server.startswith(('http://', 'https://')):
                api_server = f"http://{api_server}"

            self.base_url = api_server
            print(f"✅ API URL configurada: {self.base_url}")
            return True

        except Exception as e:
            print(f"❌ Error configurando URL del API: {e}")
            logging.error(f"❌ Error configurando URL del API: {e}")
            raise e

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                      params: Optional[Dict] = None) -> requests.Response:
        """Método base para hacer peticiones HTTP"""

        # Cargar URL si no está cargada
        if not self.base_url:
            self._load_api_url()

        url = f"{self.base_url}{endpoint}"

        try:
            print(f"🌐 {method} {url}")
            logging.info(f"🌐 {method} {url}")

            if method.upper() == 'GET':
                response = requests.get(
                    url, params=params, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, timeout=self.timeout)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, timeout=self.timeout)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, timeout=self.timeout)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")

            print(f"📡 Respuesta: {response.status_code}")
            logging.info(f"📡 Respuesta: {response.status_code}")
            return response

        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión en {method} {url}: {e}")
            logging.error(f"❌ Error de conexión en {method} {url}: {e}")
            raise Exception(f"Error de conexión al API: {str(e)}")

    def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        """Hacer petición GET"""
        return self._make_request('GET', endpoint, params=params)

    def post(self, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """Hacer petición POST"""
        return self._make_request('POST', endpoint, data=data)

    # ============= SALUD DEL API =============

    def check_api_health(self) -> Dict[str, Any]:
        """Verificar el estado de salud del API"""
        result = {
            "status": "unknown",
            "message": "",
            "response_time": None,
            "version": None
        }

        try:
            print(f"🔍 Verificando salud del API...")

            # Primero asegurar que tenemos la URL
            if not self.base_url:
                self._load_api_url()

            import time
            start_time = time.time()

            # Intentar diferentes endpoints de salud
            endpoints = ["/health", "/status", "/api/health", "/"]

            for endpoint in endpoints:
                try:
                    print(f"🔍 Probando endpoint: {endpoint}")
                    response = self.get(endpoint)

                    if response.status_code == 200:
                        response_time = round(
                            (time.time() - start_time) * 1000, 2)
                        result.update({
                            "status": "online",
                            "message": f"API disponible ({response_time}ms)",
                            "response_time": response_time,
                            "endpoint": endpoint
                        })

                        print(
                            f"✅ API responde en {endpoint}: {response_time}ms")

                        # Intentar obtener información adicional
                        try:
                            if endpoint == "/health":
                                data = response.json()
                                result["version"] = data.get("version", "N/A")
                                result["message"] = f"API saludable ({response_time}ms)"
                        except:
                            pass

                        return result

                except Exception as e:
                    print(f"❌ Error en endpoint {endpoint}: {e}")
                    continue

            result.update({
                "status": "offline",
                "message": "API no responde"
            })
            print(f"❌ Ningún endpoint respondió")

        except Exception as e:
            result.update({
                "status": "error",
                "message": f"Error: {str(e)}"
            })
            print(f"❌ Error general verificando API: {e}")

        return result

    # ============= INVESTIGACIONES (EXPEDIENTES) =============

    def buscar_expediente(self, numero_expediente: str) -> Optional[int]:
        """Buscar expediente por número"""
        try:
            # 🚀 CORRECCIÓN: Tu API usa /investigaciones/ no /expedientes/
            endpoint = f"/investigaciones/{numero_expediente}"
            print(f"🔍 Buscando investigación en: {endpoint}")

            response = self.get(endpoint)

            if response.status_code == 200:
                data = response.json()
                print(f"🔍 Response data: {data}")

                # 🚀 PROBLEMA: Tu API no devuelve 'id' en el GET individual
                # Necesitamos buscar en la lista completa para obtener el ID
                expediente_id = data.get("id")

                if expediente_id:
                    logging.info(
                        f"✅ Investigación encontrada: {numero_expediente} -> ID {expediente_id}")
                    return expediente_id
                else:
                    # La investigación existe pero no tiene ID en la respuesta
                    # Buscar en la lista completa
                    print(
                        f"⚠️ Investigación existe pero sin ID, buscando en lista completa...")
                    return self._buscar_id_en_lista(numero_expediente)

            elif response.status_code == 404:
                print(f"📋 Investigación no existe: {numero_expediente}")
                logging.info(f"📋 Investigación no existe: {numero_expediente}")
                return None
            else:
                print(f"❌ Error response: {response.text}")
                raise Exception(
                    f"Error al consultar investigación: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Exception: {e}")
            logging.error(
                f"❌ Error buscando investigación {numero_expediente}: {e}")
            raise e

    def _buscar_id_en_lista(self, numero_expediente: str) -> Optional[int]:
        """Buscar ID de investigación en la lista completa"""
        try:
            print(f"🔍 Buscando ID en lista de investigaciones...")
            response = self.get("/investigaciones/")

            if response.status_code == 200:
                investigaciones = response.json()
                print(
                    f"🔍 Total investigaciones: {len(investigaciones) if isinstance(investigaciones, list) else 'No es lista'}")

                if isinstance(investigaciones, list):
                    for inv in investigaciones:
                        if inv.get("numero_expediente") == numero_expediente:
                            inv_id = inv.get("id")
                            print(
                                f"✅ ID encontrado en lista: {numero_expediente} -> {inv_id}")
                            logging.info(
                                f"✅ ID encontrado en lista: {numero_expediente} -> {inv_id}")
                            return inv_id
                else:
                    print(
                        f"⚠️ La respuesta no es una lista: {type(investigaciones)}")

                print(
                    f"❌ No se encontró ID para {numero_expediente} en la lista")
                return None
            else:
                print(
                    f"❌ Error obteniendo lista: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"❌ Error buscando ID en lista: {e}")
            return None

    def buscar_o_crear_expediente(self, numero_expediente: str) -> int:
        """Buscar expediente, si no existe lo crea"""
        try:
            print(f"🔍 Buscar o crear expediente: {numero_expediente}")

            # Primero intentar buscar
            expediente_id = self.buscar_expediente(numero_expediente)

            if expediente_id:
                print(
                    f"✅ Investigación existente: {numero_expediente} -> ID {expediente_id}")
                return expediente_id

            # Si no existe, crear uno nuevo
            print(f"🆕 Creando nueva investigación: {numero_expediente}")
            return self.crear_expediente(numero_expediente)

        except Exception as e:
            logging.error(
                f"❌ Error buscar/crear expediente {numero_expediente}: {e}")
            raise e

    def crear_expediente(self, numero_expediente: str) -> int:
        """Crear nueva investigación"""
        try:
            payload = {
                "numero_expediente": numero_expediente,
                "nombre_carpeta": numero_expediente,
                "observaciones": "Creado desde app desktop"
            }

            print(f"🔍 Creando investigación con payload: {payload}")

            response = self.post("/investigaciones/", payload)

            print(f"🔍 Create Status: {response.status_code}")
            print(f"🔍 Create Response: {response.text}")

            if response.status_code == 200:
                data = response.json()
                expediente_id = data.get("id")
                if expediente_id:
                    logging.info(
                        f"✅ Investigación creada: {numero_expediente} -> ID {expediente_id}")
                    return expediente_id
                else:
                    # Si no devuelve ID, buscar en la lista
                    print(f"⚠️ Creación exitosa pero sin ID, buscando en lista...")
                    expediente_id = self._buscar_id_en_lista(numero_expediente)
                    if expediente_id:
                        return expediente_id
                    else:
                        raise Exception(
                            "Investigación creada pero no se pudo obtener el ID")

            elif response.status_code == 400 and "ya existe" in response.text.lower():
                # La investigación ya existe, buscar su ID
                print(f"⚠️ Investigación ya existe, buscando ID...")
                expediente_id = self.buscar_expediente(numero_expediente)
                if expediente_id:
                    return expediente_id
                else:
                    raise Exception(
                        "Investigación existe pero no se pudo obtener el ID")

            elif response.status_code == 500:
                # Error 500 podría ser porque ya existe
                print(f"⚠️ Error 500, posiblemente ya existe. Intentando buscar...")
                expediente_id = self.buscar_expediente(numero_expediente)
                if expediente_id:
                    print(
                        f"✅ Investigación ya existía: {numero_expediente} -> ID {expediente_id}")
                    return expediente_id
                else:
                    print(f"❌ Error 500 real: {response.text}")
                    raise Exception(
                        f"Error 500 al crear investigación: {response.text}")
            else:
                print(f"❌ Error creating: Status {response.status_code}")
                print(f"❌ Error response: {response.text}")
                raise Exception(
                    f"Error al crear investigación: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Exception creating: {e}")
            logging.error(
                f"❌ Error creando investigación {numero_expediente}: {e}")
            raise e

    # ============= SESIONES =============

    def crear_sesion(self, numero_expediente: str, descripcion: str, usuario_ldap: str = "forense1", user_nombre: str = None) -> int:
        """Crear nueva sesión"""
        try:
            # 🚀 Primero necesitamos el ID de la investigación
            investigacion_id = self.buscar_expediente(numero_expediente)
            if not investigacion_id:
                investigacion_id = self.crear_expediente(numero_expediente)

            # 🚀 Obtener configuración del dispositivo
            config = self.config_service.load_config()
            dispositivo = config.get("dispositivo", {})
            tablet_id = dispositivo.get("tablet_id", "Tablet1")
            plancha_id = dispositivo.get("plancha", "Plancha1")

            # 🚀 CORRECCIÓN: user_nombre debe ser el nombre completo del usuario
            payload = {
                "investigacion_id": int(investigacion_id),
                "nombre_sesion": str(descripcion),
                "observaciones": "Sesión creada desde app desktop",
                # ✅ Username de LDAP (ej: "forense1")
                "usuario_ldap": str(usuario_ldap),
                "plancha_id": str(plancha_id),
                "tablet_id": str(tablet_id),
                # ✅ Nombre completo (ej: "Forense 1 F1. Martinez")
                "user_nombre": str(user_nombre or usuario_ldap),
                "estado": "en_progreso"
            }

            # ✅ Validar que no hay valores None o vacíos
            for key, value in payload.items():
                if value is None or value == "":
                    raise Exception(
                        f"Campo requerido '{key}' está vacío o es None")

            print(f"🔍 DEBUG: Payload para crear sesión: {payload}")

            response = self.post("/sesiones/", payload)

            print(f"🔍 DEBUG: Status Code: {response.status_code}")
            print(f"🔍 DEBUG: Response Text: {response.text}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"🔍 DEBUG: Response JSON: {data}")

                    # Buscar el ID en diferentes campos posibles
                    sesion_id = data.get("id") or data.get(
                        "sesion_id") or data.get("id_sesion")

                    print(f"🔍 DEBUG: ID extraído: {sesion_id}")

                    if sesion_id:
                        logging.info(
                            f"✅ Sesión creada: {descripcion} -> ID {sesion_id}")
                        return int(sesion_id)  # ✅ Asegurar que devuelve entero
                    else:
                        print(f"❌ No se encontró ID en la respuesta")
                        print(
                            f"❌ Campos disponibles: {list(data.keys()) if isinstance(data, dict) else 'No es dict'}")
                        raise Exception(
                            "Sesión creada pero no se pudo obtener el ID")

                except ValueError as e:
                    print(f"❌ Error parsing JSON: {e}")
                    print(f"❌ Response no es JSON válido: {response.text}")
                    raise Exception(
                        f"Respuesta del API no es JSON válido: {response.text}")

            elif response.status_code == 500:
                # ✅ Manejar error 500 específicamente
                print(f"❌ Error 500 - Internal Server Error")
                print(f"❌ Response: {response.text}")

                # Intentar parsear el error si es JSON
                try:
                    error_data = response.json()
                    error_detail = error_data.get(
                        "detail", "Error interno del servidor")
                    raise Exception(
                        f"Error interno del servidor: {error_detail}")
                except:
                    raise Exception(
                        f"Error interno del servidor (500): {response.text}")

            else:
                raise Exception(
                    f"Error al crear sesión: {response.status_code} - {response.text}")

        except Exception as e:
            logging.error(f"❌ Error creando sesión: {e}")
            print(f"❌ Exception completa: {e}")
            raise e

    # ============= PROCESAMIENTO =============

    def procesar_sesion(self, numero_expediente: str, id_sesion: int) -> bool:
        """Enviar sesión para procesamiento"""
        try:
            payload = {
                "numero_expediente": numero_expediente,
                "id_sesion": id_sesion
            }
            response = self.post("/procesar_sesion", payload)

            if response.status_code == 200:
                logging.info(
                    f"✅ Sesión enviada a procesamiento: {numero_expediente}/{id_sesion}")
                return True
            else:
                logging.error(
                    f"❌ Error procesando sesión: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logging.error(f"❌ Error procesando sesión: {e}")
            return False

    # ============= AGREGAR ENDPOINTS FALTANTES =============

    def procesar_audio(self, numero_expediente: str, id_sesion: int) -> bool:
        """Enviar audio para procesamiento - Placeholder"""
        try:
            # 🚀 Tu API no tiene este endpoint específico, usar procesar_sesion
            return self.procesar_sesion(numero_expediente, id_sesion)

        except Exception as e:
            logging.error(f"❌ Error procesando audio: {e}")
            return False

    def procesar_video(self, numero_expediente: str, id_sesion: int) -> bool:
        """Enviar video para procesamiento - Placeholder"""
        try:
            # 🚀 Tu API no tiene este endpoint específico, usar procesar_sesion
            return self.procesar_sesion(numero_expediente, id_sesion)

        except Exception as e:
            logging.error(f"❌ Error procesando video: {e}")
            return False

    # ============= USUARIOS/AUTENTICACIÓN =============

    def verificar_usuario_ldap(self, usuario: str, password: str) -> bool:
        """Verificar credenciales LDAP (si el API lo maneja)"""
        try:
            payload = {
                "usuario": usuario,
                "password": password
            }
            response = self.post("/auth/ldap", payload)

            return response.status_code == 200

        except Exception as e:
            logging.error(f"❌ Error verificando usuario LDAP: {e}")
            return False

    # ============= USUARIOS/SESIONES PENDIENTES =============

    def verificar_sesion_pendiente(self, usuario: str) -> Optional[Dict[str, Any]]:
        """Verificar sesiones pendientes de un usuario"""
        try:
            endpoint = f"/usuarios/{usuario}/sesion_pendiente"
            print(f"🔍 Verificando sesiones pendientes: {endpoint}")

            response = self.get(endpoint)
            print(f"🔍 Status verificación: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"🔍 Datos sesión pendiente: {data}")

                if data.get("pendiente"):
                    logging.info(
                        f"⚠️ Sesión pendiente encontrada para {usuario}")
                    return data
                else:
                    logging.info(
                        f"✅ No hay sesiones pendientes para {usuario}")
                    return None
            elif response.status_code == 404:
                logging.info(f"✅ No hay sesiones pendientes para {usuario}")
                return None
            else:
                logging.warning(
                    f"⚠️ Error verificando sesiones: {response.status_code}")
                return None

        except Exception as e:
            logging.error(f"❌ Error verificando sesiones pendientes: {e}")
            print(f"❌ Exception verificando sesiones: {e}")
            return None

    def cerrar_sesion_pendiente(self, id_sesion: int) -> bool:
        """Cerrar sesión pendiente"""
        try:
            # Tu API puede usar diferentes endpoints para cerrar sesiones
            # Vamos a usar el endpoint de procesar que ya tienes
            payload = {"id_sesion": id_sesion}
            response = self.post("/procesar_sesion", payload)

            if response.status_code == 200:
                logging.info(f"✅ Sesión {id_sesion} enviada a procesamiento")
                return True
            else:
                logging.error(
                    f"❌ Error procesando sesión {id_sesion}: {response.status_code}")
                return False

        except Exception as e:
            logging.error(f"❌ Error cerrando sesión {id_sesion}: {e}")
            return False

    def crear_sesion_sin_validacion(self, numero_expediente: str, descripcion: str, usuario_ldap: str) -> int:
        """Crear nueva sesión sin validar sesiones pendientes (para uso interno)"""
        try:
            # 🚀 Primero necesitamos el ID de la investigación
            investigacion_id = self.buscar_expediente(numero_expediente)
            if not investigacion_id:
                investigacion_id = self.crear_expediente(numero_expediente)

            # 🚀 Obtener configuración del dispositivo
            config = self.config_service.load_config()
            dispositivo = config.get("dispositivo", {})
            tablet_id = dispositivo.get("tablet_id", "tablet_desconocida")
            plancha_id = dispositivo.get("plancha", "plancha_desconocida")

            payload = {
                "investigacion_id": investigacion_id,
                "nombre_sesion": descripcion,
                "observaciones": f"Sesión creada desde app desktop",
                "usuario_ldap": usuario_ldap,
                "plancha_id": plancha_id,
                "tablet_id": tablet_id
            }

            response = self.post("/sesiones/", payload)

            if response.status_code == 200:
                data = response.json()
                sesion_id = data.get("id")
                logging.info(
                    f"✅ Sesión creada: {descripcion} -> ID {sesion_id}")
                return sesion_id
            else:
                raise Exception(
                    f"Error al crear sesión: {response.status_code} - {response.text}")

        except Exception as e:
            logging.error(f"❌ Error creando sesión: {e}")
            raise e

    def actualizar_sesion_estado(self, id_sesion: int, nuevo_estado: str) -> bool:
        """Actualizar el estado de una sesión"""
        try:
            payload = {"estado": nuevo_estado}
            endpoint = f"/sesiones/{id_sesion}"
            response = self._make_request('PUT', endpoint, data=payload)

            if response.status_code == 200:
                logging.info(
                    f"✅ Estado de la sesión {id_sesion} actualizado a '{nuevo_estado}'")
                return True
            else:
                logging.error(
                    f"❌ Error actualizando sesión {id_sesion}: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logging.error(
                f"❌ Error actualizando estado sesión {id_sesion}: {e}")
            return False
