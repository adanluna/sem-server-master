import requests
import logging
import time
from typing import Dict, Any, Optional


class ApiService:
    def __init__(self, base_url=None, timeout: int = 5):
        """
        Servicio para verificar estado de APIs

        Args:
            base_url: URL base del servidor (ej: "http://192.168.1.220:8000")
            timeout: Timeout en segundos para las peticiones
        """
        self.base_url = base_url or "http://localhost:8000"
        self.timeout = timeout

    def make_request(self, method, endpoint, data=None, server=None):
        """Hacer petición HTTP al servidor API con debug detallado"""
        print(f"🔍 DEBUG ApiService: make_request() entrada")
        print(f"🔍 DEBUG ApiService: Method: {method}")
        print(f"🔍 DEBUG ApiService: Endpoint: {endpoint}")
        print(f"🔍 DEBUG ApiService: Server: {server}")
        print(f"🔍 DEBUG ApiService: Data: {data}")

        try:
            if server:
                # Agregar http:// si no está presente
                if not server.startswith(('http://', 'https://')):
                    server = f"http://{server}"
                url = f"{server}{endpoint}"
            else:
                url = f"{self.base_url}{endpoint}"

            print(f"🔍 DEBUG ApiService: URL final: {url}")

            # Headers por defecto
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            # Hacer la petición según el método
            if method.upper() == 'GET':
                print(f"🔍 DEBUG ApiService: Haciendo GET request...")
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                print(f"🔍 DEBUG ApiService: Haciendo POST request...")
                response = requests.post(
                    url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'PUT':
                print(f"🔍 DEBUG ApiService: Haciendo PUT request...")
                response = requests.put(
                    url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'DELETE':
                print(f"🔍 DEBUG ApiService: Haciendo DELETE request...")
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                print(f"🔍 DEBUG ApiService: Método no soportado: {method}")
                return {
                    'success': False,
                    'error': f'Método {method} no soportado'
                }

            print(f"🔍 DEBUG ApiService: Status code: {response.status_code}")
            print(
                f"🔍 DEBUG ApiService: Response headers: {dict(response.headers)}")

            # Intentar parsear JSON
            try:
                response_data = response.json()
                print(f"🔍 DEBUG ApiService: Response JSON: {response_data}")
            except ValueError:
                print(f"🔍 DEBUG ApiService: Response no es JSON válido")
                print(f"🔍 DEBUG ApiService: Response text: {response.text}")
                response_data = {'text': response.text}

            # Verificar código de estado
            if response.status_code == 200:
                print(f"🔍 DEBUG ApiService: Petición exitosa")
                return {
                    'success': True,
                    'data': response_data,
                    'status_code': response.status_code
                }
            else:
                print(
                    f"🔍 DEBUG ApiService: Petición falló con código {response.status_code}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response_data}',
                    'status_code': response.status_code,
                    'data': response_data
                }

        except requests.exceptions.ConnectionError as e:
            print(f"🔍 DEBUG ApiService: Error de conexión: {e}")
            return {
                'success': False,
                'error': f'Error de conexión: No se pudo conectar al servidor {url}'
            }
        except requests.exceptions.Timeout as e:
            print(f"🔍 DEBUG ApiService: Timeout: {e}")
            return {
                'success': False,
                'error': f'Timeout: El servidor no respondió en 10 segundos'
            }
        except Exception as e:
            print(f"🔍 DEBUG ApiService: Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }

    def check_api_status(self, server_url):
        """Verificar el estado del servidor API"""
        print(
            f"🔍 DEBUG ApiService.check_api_status: Entrada con server_url: '{server_url}'")

        try:
            start_time = time.time()

            # Agregar http:// si no está presente
            if not server_url.startswith(('http://', 'https://')):
                server_url = f"http://{server_url}"

            print(
                f"🔍 DEBUG ApiService.check_api_status: URL final: '{server_url}'")

            # Intentar primero el endpoint de salud
            health_url = f"{server_url}/health"
            print(
                f"🔍 DEBUG ApiService.check_api_status: Probando health endpoint: '{health_url}'")

            try:
                response = requests.get(health_url, timeout=5)
                response_time = int((time.time() - start_time) * 1000)  # ms

                print(
                    f"🔍 DEBUG ApiService.check_api_status: Health response status: {response.status_code}")

                if response.status_code == 200:
                    return {
                        'status': 'online',
                        'response_time': response_time,
                        'server': server_url,
                        'endpoint': '/health'
                    }
                elif response.status_code == 404:
                    print(
                        "🔍 DEBUG ApiService.check_api_status: /health no existe, probando endpoint raíz...")
                    # Si /health no existe, probar el endpoint raíz
                    root_url = server_url
                    root_response = requests.get(root_url, timeout=5)
                    response_time = int((time.time() - start_time) * 1000)

                    print(
                        f"🔍 DEBUG ApiService.check_api_status: Root response status: {root_response.status_code}")

                    if root_response.status_code == 200:
                        return {
                            'status': 'online',
                            'response_time': response_time,
                            'server': server_url,
                            'endpoint': '/'
                        }
                    else:
                        return {
                            'status': 'error',
                            'response_time': response_time,
                            'error': f'HTTP {root_response.status_code}',
                            'server': server_url
                        }
                else:
                    return {
                        'status': 'error',
                        'response_time': response_time,
                        'error': f'HTTP {response.status_code}',
                        'server': server_url
                    }

            except requests.exceptions.ConnectionError as e:
                print(
                    f"🔍 DEBUG ApiService.check_api_status: Connection error: {e}")
                return {
                    'status': 'offline',
                    'error': 'No se pudo conectar',
                    'server': server_url
                }

        except requests.exceptions.Timeout as e:
            print(f"🔍 DEBUG ApiService.check_api_status: Timeout: {e}")
            return {
                'status': 'timeout',
                'error': 'Timeout',
                'server': server_url
            }
        except Exception as e:
            print(
                f"🔍 DEBUG ApiService.check_api_status: Error inesperado: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'server': server_url
            }

    def test_api_connection(self, server_url: str) -> bool:
        """
        Prueba simple de conexión al API

        Returns:
            True si el API está disponible, False en caso contrario
        """
        status = self.check_api_status(server_url)
        return status["status"] == "online"

    def get(self, endpoint, params=None, server=None):
        """Método GET simplificado"""
        return self.make_request('GET', endpoint, data=params, server=server)

    def post(self, endpoint, data=None, server=None):
        """Método POST simplificado"""
        return self.make_request('POST', endpoint, data=data, server=server)

    def put(self, endpoint, data=None, server=None):
        """Método PUT simplificado"""
        return self.make_request('PUT', endpoint, data=data, server=server)

    def delete(self, endpoint, server=None):
        """Método DELETE simplificado"""
        return self.make_request('DELETE', endpoint, server=server)
