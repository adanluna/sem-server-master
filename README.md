
# ⚖️ SEMEFO Forense Stack (con `.env` único)

Sistema integral para grabación, gestión y transcripción de autopsias, diseñado para el **Gobierno del Estado de Nuevo León**.

Incluye:

✅ **FastAPI** — API REST para gestión de investigaciones y sesiones  
✅ **PostgreSQL** — Base de datos para almacenamiento seguro  
✅ **RabbitMQ** — Broker de colas para procesos asíncronos  
✅ **Celery** — Workers para conversión de videos y transcripción con Whisper  
✅ Configuración **centralizada en un solo `.env`**

---

## 🚀 Usar

1️⃣ Configura tu archivo `.env` en la raíz del proyecto.  
Ejemplo:

```env
DB_HOST=postgres_db
DB_PORT=5432
DB_NAME=semefo
DB_USER=semefo_user
DB_PASS=Claudia01$!

RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//

LDAP_SERVER_IP=192.168.1.211
LDAP_PORT=389
LDAP_DOMAIN=semefo.local

CONFIG_ENCRYPTION_KEY=ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=
```

2️⃣ Levanta los servicios con:

```bash
docker-compose up -d --build
```

✅ ¡Todo configurado desde tu `.env`!

---

## 🔥 Accede

- **FastAPI:** [http://localhost:8000/docs](http://localhost:8000/docs)  
  (Swagger auto-documentado)

- **RabbitMQ admin:** [http://localhost:15672](http://localhost:15672)  
  Usuario: `guest` / Contraseña: `guest`

---

## ⚙️ Uso rápido con `Makefile`

Este proyecto incluye un `Makefile` para facilitar las tareas diarias:

| Comando             | Descripción                             |
|----------------------|----------------------------------------|
| `make up`            | Levanta todo el stack con Docker       |
| `make down`          | Detiene los contenedores               |
| `make restart`       | Reinicia con rebuild                   |
| `make logs`          | Logs en tiempo real                    |
| `make psql`          | Conecta a la DB PostgreSQL             |
| `make bash-db`       | Bash dentro del contenedor de postgres |
| `make bash-api`      | Bash dentro del contenedor FastAPI     |
| `make bash-celery`   | Bash dentro del worker Celery          |
| `make backup-db`     | Crea dump en `./backups/semefo_backup.sql` |
| `make restore-db`    | Restaura desde ese dump                |

---