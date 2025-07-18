from schemas import SesionArchivoEstadoUpdate
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import os

from database import get_db, engine
import models
from schemas import (
    InvestigacionCreate,
    InvestigacionUpdate,
    SesionCreate,
    JobCreate,
    JobUpdate,
    SesionArchivoCreate,
    SesionArchivoResponse,
)

from worker.tasks import unir_audio, unir_video

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear tablas automáticamente
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema Forense SEMEFO",
    description="API del Sistema Integral de Grabación y Gestión de Autopsias del Gobierno del Estado de Nuevo León.",
    version="1.0.0",
    contact={"name": "Gobierno del Estado de Nuevo León",
             "url": "https://www.nl.gob.mx"},
    license_info={"name": "Privativo Fiscalía NL",
                  "url": "https://www.fiscalianl.gob.mx/"},
)


@app.get("/")
async def root():
    return {"message": "SEMEFO API Server", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "API funcionando correctamente"}


@app.post("/investigaciones/", response_model=InvestigacionCreate)
def create_investigacion(invest: InvestigacionCreate, db: Session = Depends(get_db)):
    nueva = models.Investigacion(
        numero_expediente=invest.numero_expediente,
        nombre_carpeta=invest.nombre_carpeta,
        observaciones=invest.observaciones
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/investigaciones/")
def list_investigaciones(db: Session = Depends(get_db)):
    return db.query(models.Investigacion).all()


@app.get("/investigaciones/{numero_expediente}", response_model=InvestigacionCreate)
def get_investigacion_by_expediente(numero_expediente: str, db: Session = Depends(get_db)):
    investigacion = db.query(models.Investigacion).filter_by(
        numero_expediente=numero_expediente).first()
    if not investigacion:
        raise HTTPException(
            status_code=404, detail="Investigación no encontrada")
    return investigacion


@app.put("/investigaciones/{numero_expediente}", response_model=InvestigacionCreate)
def update_investigacion(numero_expediente: str, datos: InvestigacionUpdate, db: Session = Depends(get_db)):
    investigacion = db.query(models.Investigacion).filter_by(
        numero_expediente=numero_expediente).first()
    if not investigacion:
        raise HTTPException(
            status_code=404, detail="Investigación no encontrada")
    if datos.nombre_carpeta is not None:
        investigacion.nombre_carpeta = datos.nombre_carpeta
    if datos.observaciones is not None:
        investigacion.observaciones = datos.observaciones
    db.commit()
    db.refresh(investigacion)
    return investigacion


@app.post("/sesiones/")
def crear_sesion(sesion_data: SesionCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"🔍 API: Recibiendo datos de sesión: {sesion_data}")
        logger.info(f"🔍 API: Tipo de datos: {type(sesion_data)}")

        # Validar que investigacion_id existe
        investigacion = db.query(models.Investigacion).filter(
            models.Investigacion.id == sesion_data.investigacion_id).first()
        if not investigacion:
            logger.error(
                f"❌ API: Investigación {sesion_data.investigacion_id} no encontrada")
            raise HTTPException(
                status_code=404, detail=f"Investigación {sesion_data.investigacion_id} no encontrada")

        logger.info(
            f"✅ API: Investigación encontrada: {investigacion.numero_expediente}")

        nueva_sesion = models.Sesion(
            investigacion_id=sesion_data.investigacion_id,
            nombre_sesion=sesion_data.nombre_sesion,
            observaciones=sesion_data.observaciones,
            usuario_ldap=sesion_data.usuario_ldap,
            plancha_id=sesion_data.plancha_id,
            tablet_id=sesion_data.tablet_id,
            estado=getattr(sesion_data, 'estado', 'en_progreso'),
            user_nombre=getattr(sesion_data, 'user_nombre',
                                sesion_data.usuario_ldap)
        )

        logger.info(f"🔍 API: Objeto sesión creado: {nueva_sesion}")

        db.add(nueva_sesion)
        db.commit()
        db.refresh(nueva_sesion)

        logger.info(f"✅ API: Sesión guardada con ID: {nueva_sesion.id}")

        log = models.LogEvento(
            tipo_evento="crear_sesion",
            descripcion=f"Sesión creada en plancha {nueva_sesion.plancha_id}, tablet {nueva_sesion.tablet_id}",
            usuario_ldap=nueva_sesion.usuario_ldap
        )
        db.add(log)
        db.commit()

        logger.info(f"✅ API: Log evento creado")

        response_data = {
            "id": nueva_sesion.id,
            "investigacion_id": nueva_sesion.investigacion_id,
            "nombre_sesion": nueva_sesion.nombre_sesion,
            "observaciones": nueva_sesion.observaciones,
            "usuario_ldap": nueva_sesion.usuario_ldap,
            "plancha_id": nueva_sesion.plancha_id,
            "tablet_id": nueva_sesion.tablet_id,
            "estado": nueva_sesion.estado
        }

        logger.info(f"✅ API: Devolviendo respuesta: {response_data}")
        return response_data

    except HTTPException as he:
        logger.error(f"❌ API: HTTPException: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"❌ API: Error creando sesión: {e}")
        logger.error(f"❌ API: Tipo de error: {type(e)}")
        import traceback
        logger.error(f"❌ API: Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.get("/sesiones/pendientes/{usuario_ldap}")
def get_sesion_pendiente(usuario_ldap: str, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(
        usuario_ldap=usuario_ldap,
        estado="en_progreso"
    ).first()
    if not sesion:
        return {"message": f"No hay sesiones pendientes para el usuario {usuario_ldap}"}
    return {
        "sesion_id": sesion.id,
        "investigacion_id": sesion.investigacion_id,
        "plancha_id": sesion.plancha_id,
        "tablet_id": sesion.tablet_id,
        "estado": sesion.estado
    }


@app.put("/sesiones/finalizar/{sesion_id}")
def finalizar_sesion(sesion_id: int, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if sesion.estado != "en_progreso":
        return {"message": "La sesión ya está finalizada o cerrada."}

    sesion.estado = "finalizada"
    db.commit()
    db.refresh(sesion)

    log = models.LogEvento(
        tipo_evento="finalizar_sesion",
        descripcion=f"Sesión {sesion_id} finalizada en plancha {sesion.plancha_id}, tablet {sesion.tablet_id}",
        usuario_ldap=sesion.usuario_ldap
    )
    db.add(log)
    db.commit()

    return {"message": "Sesión finalizada exitosamente"}


@app.put("/sesiones/{sesion_id}/cerrar")
def cerrar_sesion(sesion_id: int, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if sesion.estado == "cerrada":
        return {"message": f"La sesión con ID {sesion_id} ya estaba cerrada."}

    sesion.estado = "cerrada"
    sesion.fecha_cierre = datetime.utcnow()
    db.commit()

    log = models.LogEvento(
        tipo_evento="cerrar_sesion",
        descripcion=f"Sesión cerrada manualmente en plancha {sesion.plancha_id}, tablet {sesion.tablet_id}",
        usuario_ldap=sesion.usuario_ldap
    )
    db.add(log)
    db.commit()

    return {"message": f"Sesión {sesion_id} cerrada correctamente."}


@app.get("/usuarios/{username}/sesion_pendiente")
def get_usuario_sesion_pendiente(username: str, db: Session = Depends(get_db)):
    print(f"🔍 Buscando sesiones pendientes para username: '{username}'")

    sesion = db.query(models.Sesion).filter(
        models.Sesion.usuario_ldap == username,
        models.Sesion.estado == "en_progreso"
    ).first()

    if sesion:
        print(f"✅ Sesión encontrada para username {username}: ID {sesion.id}")
        investigacion = db.query(models.Investigacion).filter(
            models.Investigacion.id == sesion.investigacion_id
        ).first()

        return {
            "pendiente": True,
            "tablet_id": sesion.tablet_id,
            "plancha_id": sesion.plancha_id,
            "numero_expediente": investigacion.numero_expediente if investigacion else "Desconocido",
            "nombre_sesion": sesion.nombre_sesion,
            "id_sesion": sesion.id
        }
    else:
        print(f"❌ No hay sesiones para username {username}")
        return {"pendiente": False}


@app.post("/procesar_sesion")
def procesar_sesion(payload: dict, db: Session = Depends(get_db)):
    numero_expediente = payload.get("numero_expediente")
    id_sesion = payload.get("id_sesion")
    if not numero_expediente or not id_sesion:
        raise HTTPException(status_code=400, detail="Faltan parámetros")

    # 🔥 Llamadas reales a Celery
    unir_audio.delay(numero_expediente, id_sesion)
    unir_video.delay(numero_expediente, id_sesion)

    return {"message": f"Procesamiento lanzado para expediente {numero_expediente}, sesión {id_sesion}"}


@app.post("/procesar_audio")
def procesar_audio(payload: dict, db: Session = Depends(get_db)):
    numero_expediente = payload.get("numero_expediente")
    id_sesion = payload.get("id_sesion")
    if not numero_expediente or not id_sesion:
        raise HTTPException(status_code=400, detail="Faltan parámetros")

    return {"message": f"Procesamiento de audio lanzado para expediente {numero_expediente}, sesión {id_sesion}"}


@app.post("/procesar_video")
def procesar_video(payload: dict, db: Session = Depends(get_db)):
    numero_expediente = payload.get("numero_expediente")
    id_sesion = payload.get("id_sesion")
    if not numero_expediente or not id_sesion:
        raise HTTPException(status_code=400, detail="Faltan parámetros")

    return {"message": f"Procesamiento de video lanzado para expediente {numero_expediente}, sesión {id_sesion}"}


@app.post("/jobs/crear")
def crear_job(job: JobCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"📥 API: Recibiendo nuevo job desde worker: {job}")
        investigacion = db.query(models.Investigacion).filter_by(
            numero_expediente=job.numero_expediente).first()
        if not investigacion:
            raise HTTPException(
                status_code=404, detail="Investigación no encontrada")

        sesion = db.query(models.Sesion).filter_by(
            id=job.id_sesion, investigacion_id=investigacion.id).first()
        if not sesion:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")

        nuevo_job = models.Job(
            investigacion_id=investigacion.id,
            sesion_id=sesion.id,
            tipo=job.tipo,
            archivo=job.archivo,
            estado=job.estado,
            resultado=job.resultado,
            error=job.error,
        )

        db.add(nuevo_job)
        db.commit()
        db.refresh(nuevo_job)

        logger.info(f"✅ API: Job registrado correctamente (ID {nuevo_job.id})")

        return {
            "message": "Job creado correctamente",
            "job_id": nuevo_job.id,
            "estado": nuevo_job.estado,
        }

    except HTTPException as he:
        logger.error(f"❌ API: Error HTTP al crear job: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"❌ API: Error inesperado al crear job: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Error interno al crear el job")


@app.put("/jobs/{job_id}/actualizar")
def actualizar_job(job_id: int, datos: JobUpdate, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    if datos.estado:
        job.estado = datos.estado
    if datos.resultado:
        job.resultado = datos.resultado
    if datos.error:
        job.error = datos.error

    db.commit()
    db.refresh(job)
    return {"message": "Job actualizado", "job_id": job.id, "estado": job.estado}


@app.post("/archivos/", response_model=SesionArchivoResponse)
def registrar_archivo(data: SesionArchivoCreate, db: Session = Depends(get_db)):
    archivo = models.SesionArchivo(**data.dict())
    db.add(archivo)
    db.commit()
    db.refresh(archivo)
    return archivo


@app.get("/sesiones/{sesion_id}/archivos", response_model=list[SesionArchivoResponse])
def listar_archivos_por_sesion(sesion_id: int, db: Session = Depends(get_db)):
    archivos = db.query(models.SesionArchivo).filter_by(
        sesion_id=sesion_id).all()
    if not archivos:
        return []
    return archivos


@app.put("/archivos/{sesion_id}/{tipo}/actualizar_estado")
def actualizar_estado_archivo(
    sesion_id: int,
    tipo: str,
    data: SesionArchivoEstadoUpdate,
    db: Session = Depends(get_db)
):
    archivo = db.query(models.SesionArchivo).filter_by(
        sesion_id=sesion_id,
        tipo_archivo=tipo
    ).first()

    if not archivo:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró archivo de tipo {tipo} para la sesión {sesion_id}"
        )

    archivo.estado = data.estado

    if data.mensaje:
        archivo.mensaje = data.mensaje

    if data.fecha_finalizacion:
        archivo.fecha_finalizacion = datetime.utcnow()

    if data.ruta_convertida:
        archivo.ruta_convertida = data.ruta_convertida

    if data.conversion_completa is not None:
        archivo.conversion_completa = data.conversion_completa

    db.commit()
    db.refresh(archivo)

    return {
        "message": f"Estado del archivo {tipo} en sesión {sesion_id} actualizado a '{data.estado}'"
    }
