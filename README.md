
# Sistema Integral de Grabación y Gestión de Autopsias - SEMEFO

Este proyecto implementa un sistema completo para el manejo de grabaciones forenses en SEMEFO que incluye:

- 📹 Grabación multi-cámara y audio Bluetooth en autopsias.
- 🗂️ Almacenamiento organizado en carpetas por expediente y sesión.
- 🔄 Conversión automática de videos (AVI a WEBM) con FFmpeg.
- 📝 Transcripción automática en español con Whisper local (GPU).
- 🔌 API REST para consulta del sistema central.
- 🔐 Autenticación LDAP con Active Directory.
- 🖥️ Aplicación Windows con PySide6 para médicos forenses.

---

## 🚀 Estructura del Proyecto

- `api-server/`: API FastAPI para gestionar expedientes, sesiones y consultas.
- `app-desktop/`: Aplicación Windows PySide6 (LDAP, grabación, configuración, sesiones).
- `worker/`: Workers Celery para procesamiento batch (videos y transcripciones).
- `scripts/`: Scripts utilitarios para manejo del sistema.
- `docker-compose.yml`: Orquestación de servicios con Docker.
- `Makefile`: Comandos rápidos para desarrollo y despliegue.

---

## ⚙️ Scripts incluidos (`/scripts`)

### `iniciar_workers.sh`
- Arranca los workers Celery configurados para procesar conversiones de video y transcripciones de audio.

### `detener_workers.sh`
- Detiene de forma segura los workers de Celery evitando procesos huérfanos.

### `rebuild_docker.sh`
- Realiza un `docker-compose down`, limpia caché y reconstruye la infraestructura Docker desde cero (útil para actualizar dependencias o corregir errores de entorno).

---

## 🛠️ Funcionalidades del `Makefile`

Para facilitar el trabajo diario, se incluyeron los siguientes comandos rápidos:

- `make up`  
  Levanta el stack completo con Docker Compose.

- `make down`  
  Detiene y elimina los contenedores y redes actuales.

- `make stop`  
  Solo detiene los contenedores, manteniéndolos listos para reanudar con `docker-compose start`.

- `make rebuild`  
  Realiza un rebuild de los contenedores desde cero.

- `make logs`  
  Muestra los logs en tiempo real de todos los servicios.

- `make restart`  
  Reinicia los contenedores rápidamente para aplicar cambios menores.

- `make psql`  
  Abre la consola interactiva de PostgreSQL dentro del contenedor.

- `make bash-db`  
  Accede a un shell bash dentro del contenedor de la base de datos.

- `make bash-api`  
  Accede a un shell bash dentro del contenedor de la API.

- `make bash-celery`  
  Accede a un shell bash dentro del contenedor de los workers.

- `make backup-db`  
  Genera un respaldo SQL de la base de datos en el directorio `backups`.

- `make restore-db`  
  Restaura el respaldo desde `backups/semefo_backup.sql` al contenedor PostgreSQL.

---

## 🚀 Uso rápido

### Levantar el entorno
```bash
make up
```

### Detener todo eliminando contenedores
```bash
make down
```

### Solo detener contenedores sin eliminar
```bash
make stop
```

### Ver logs
```bash
make logs
```

### Reconstruir entorno desde cero
```bash
make rebuild
```

### Iniciar workers manualmente
```bash
./scripts/iniciar_workers.sh
```

### Detener workers manualmente
```bash
./scripts/detener_workers.sh
```

---

## ⚠️ Consideraciones

- El sistema depende de RabbitMQ y PostgreSQL corriendo en Docker.
- La autenticación LDAP requiere conectividad a Active Directory (`LDAP_SERVER_IP` definido en `.env`).
- El procesamiento por GPU del transcriptor Whisper puede saturar el servidor si no se gestiona la cola adecuadamente.
- Los workers asumen tener configurada la estructura de carpetas:
  ```
  storage/
   ├─ archivos_grabados/
   ├─ archivos/
   └─ ...
  ```

---

## 📄 Licencia
Proyecto desarrollado para el Gobierno del Estado de Nuevo León. Todos los derechos reservados.
