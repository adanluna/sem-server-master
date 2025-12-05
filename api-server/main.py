from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import os
from celery import chain

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
    SesionArchivoEstadoUpdate,
    PausaCreate,
    PausaResponse
)

from worker.celery_app import celery_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema Forense SEMEFO",
    description="API del Sistema Integral de Grabación y Gestión de Autopsias del Gobierno del Estado de Nuevo León.",
    version="1.0.0"
)

# ============================================================
#  VARIABLES GLOBALES
# ============================================================

SMB_ROOT = os.getenv("WINDOWS_WAVE_SHARE_MOUNT", "/mnt/wave").rstrip("/")
GRABADOR_UUID = os.getenv("WINDOWS_WAVE_UUID", "").strip()

if not GRABADOR_UUID:
    print("⚠ ADVERTENCIA: GRABADOR_UUID no definido en .env")


# ============================================================
#  RUTAS BÁSICAS
# ============================================================

@app.get("/")
async def root():
    return {"message": "SEMEFO API Server", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# ============================================================
#  INVESTIGACIONES
# ============================================================

@app.post("/investigaciones/", response_model=InvestigacionCreate)
def create_investigacion(invest: InvestigacionCreate, db: Session = Depends(get_db)):
    nueva = models.Investigacion(**invest.dict())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/investigaciones/")
def list_investigaciones(db: Session = Depends(get_db)):
    return db.query(models.Investigacion).all()


@app.get("/investigaciones/{numero_expediente}", response_model=InvestigacionCreate)
def get_investigacion(numero_expediente: str, db: Session = Depends(get_db)):
    inv = db.query(models.Investigacion).filter_by(
        numero_expediente=numero_expediente).first()
    if not inv:
        raise HTTPException(
            status_code=404, detail="Investigación no encontrada")
    return inv


@app.put("/investigaciones/{numero_expediente}", response_model=InvestigacionCreate)
def update_investigacion(numero_expediente: str, datos: InvestigacionUpdate, db: Session = Depends(get_db)):
    inv = db.query(models.Investigacion).filter_by(
        numero_expediente=numero_expediente).first()
    if not inv:
        raise HTTPException(
            status_code=404, detail="Investigación no encontrada")

    if datos.nombre_carpeta is not None:
        inv.nombre_carpeta = datos.nombre_carpeta
    if datos.observaciones is not None:
        inv.observaciones = datos.observaciones

    db.commit()
    db.refresh(inv)
    return inv


# ============================================================
#  SESIONES
# ============================================================

@app.post("/sesiones/")
def crear_sesion(sesion_data: SesionCreate, db: Session = Depends(get_db)):
    investigacion = db.query(models.Investigacion).filter_by(
        id=sesion_data.investigacion_id).first()

    if not investigacion:
        raise HTTPException(
            status_code=404, detail="Investigación no encontrada")

    nueva = models.Sesion(
        **sesion_data.dict(exclude_unset=True)
    )

    db.add(nueva)
    db.commit()
    db.refresh(nueva)

    log = models.LogEvento(
        tipo_evento="crear_sesion",
        descripcion=f"Sesión creada en plancha {nueva.plancha_id}, tablet {nueva.tablet_id}",
        usuario_ldap=nueva.usuario_ldap
    )
    db.add(log)
    db.commit()

    return nueva


@app.put("/sesiones/finalizar/{sesion_id}")
def finalizar_sesion(sesion_id: int, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()

    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if sesion.estado != "en_progreso":
        return {"message": "Sesión ya está finalizada o cerrada"}

    sesion.estado = "finalizada"
    db.commit()

    log = models.LogEvento(
        tipo_evento="finalizar_sesion",
        descripcion=f"Sesión {sesion_id} finalizada",
        usuario_ldap=sesion.usuario_ldap
    )
    db.add(log)
    db.commit()

    return {"message": "Sesión finalizada exitosamente"}


# ============================================================
#  ARCHIVOS
# ============================================================

@app.post("/archivos/", response_model=SesionArchivoResponse)
def registrar_archivo(data: SesionArchivoCreate, db: Session = Depends(get_db)):
    archivo = models.SesionArchivo(**data.dict())
    db.add(archivo)
    db.commit()
    db.refresh(archivo)
    return archivo


@app.get("/sesiones/{sesion_id}/archivos", response_model=list[SesionArchivoResponse])
def listar_archivos(sesion_id: int, db: Session = Depends(get_db)):
    return db.query(models.SesionArchivo).filter_by(sesion_id=sesion_id).all() or []


@app.put("/archivos/{sesion_id}/{tipo}/actualizar_estado")
def actualizar_estado(sesion_id: int, tipo: str, data: SesionArchivoEstadoUpdate, db: Session = Depends(get_db)):
    archivo = db.query(models.SesionArchivo).filter_by(
        sesion_id=sesion_id, tipo_archivo=tipo).first()

    if not archivo:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

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
    return {"message": f"Archivo {tipo} actualizado"}


# ============================================================
#  PROCESAR SESIÓN — MANIFEST + AUDIO + VIDEO
# ============================================================

@app.post("/procesar_sesion")
def procesar_sesion(payload: dict, db: Session = Depends(get_db)):
    ses = payload.get("sesion_activa")
    if not ses:
        raise HTTPException(status_code=400, detail="Falta 'sesion_activa'")

    expediente = ses.get("expediente")
    id_sesion = ses.get("id_sesion")
    cam1 = ses.get("camara1_mac_address")
    cam2 = ses.get("camara2_mac_address")

    if not expediente or not id_sesion:
        raise HTTPException(
            status_code=400, detail="Faltan expediente o id_sesion")

    if not cam1 or not cam2:
        raise HTTPException(status_code=400, detail="Faltan MAC addresses")

    # ============================================
    #  Convertir inicio/fin en datetime
    # ============================================
    try:
        inicio_iso = ses["inicio"]
        fin_iso = ses["fin"]
        inicio_dt = datetime.fromisoformat(inicio_iso)
        fin_dt = datetime.fromisoformat(fin_iso)
    except:
        raise HTTPException(
            status_code=400, detail="Formato inválido de inicio/fin")

    # ============================================
    #  Buscar si la sesión ya existe
    # ============================================
    sesion_obj = db.query(models.Sesion).filter_by(id=id_sesion).first()

    if not sesion_obj:
        # Crear la sesión — usando SOLO campos existentes en el modelo
        sesion_obj = models.Sesion(
            id=id_sesion,
            investigacion_id=1,   # ⚠️ DE MOMENTO HARDCODEADO — luego lo amarramos al expediente real
            nombre_sesion=ses.get("nombre", f"Sesion_{id_sesion}"),
            usuario_ldap=ses["forense"]["id_usuario"],
            plancha_id=ses.get("plancha", "desconocida"),
            tablet_id=ses.get("tablet", "desconocida"),
            estado="en_progreso",
            user_nombre=ses["forense"]["nombre"],
            camara1_mac_address=cam1,
            camara2_mac_address=cam2,
            app_version=ses.get("version_app", "1.0.0")
        )
        db.add(sesion_obj)
        db.commit()
        db.refresh(sesion_obj)

        print(f"[SESION] Creada sesión {id_sesion}")

    else:
        print(f"[SESION] Sesión {id_sesion} ya existía")

    # ============================================
    #  Registrar pausas de la APP (ahora sí existe la sesión)
    # ============================================
    pausas = ses.get("pausas", [])
    for p in pausas:
        try:
            inicio_p = datetime.fromisoformat(p["inicio"])
            fin_p = datetime.fromisoformat(p["fin"])
            dur = (fin_p - inicio_p).total_seconds()

            nueva = models.LogPausa(
                sesion_id=sesion_obj.id,
                inicio=inicio_p,
                fin=fin_p,
                duracion=dur,
                fuente="app"
            )
            db.add(nueva)
        except Exception as e:
            print(f"[PAUSAS] Error guardando pausa APP: {e}")

    db.commit()

    # ============================================
    #   Construcción de rutas manifest
    # ============================================
    fecha_solo = inicio_iso.split("T")[0]
    yyyy, mm, dd = fecha_solo.split("-")

    path_manifest1 = f"/mnt/wave/manifests/{GRABADOR_UUID}/{cam1}/{yyyy}/{mm}/{dd}/manifest.json"
    path_manifest2 = f"/mnt/wave/manifests/{GRABADOR_UUID}/{cam2}/{yyyy}/{mm}/{dd}/manifest.json"

    # ============================================
    #   PROCESO COMPLETO: GENERAR MANIFEST → UNIR VIDEO
    # ============================================

    chain(
        celery_app.signature(
            "tasks.generar_manifest",
            args=[cam1, fecha_solo],
            queue="manifest"
        ),
        celery_app.signature(
            "worker.tasks.unir_video",
            args=[expediente, id_sesion, path_manifest1, inicio_iso, fin_iso],
            queue="uniones_video"
        )
    ).apply_async()

    chain(
        celery_app.signature(
            "tasks.generar_manifest",
            args=[cam2, fecha_solo],
            queue="manifest"
        ),
        celery_app.signature(
            "worker.tasks.unir_video2",
            args=[expediente, id_sesion, path_manifest2, inicio_iso, fin_iso],
            queue="videos2"
        )
    ).apply_async()

    return {
        "status": "procesando",
        "expediente": expediente,
        "id_sesion": id_sesion,
        "inicio_sesion": inicio_iso,
        "fin_sesion": fin_iso,
        "pausas_app_registradas": len(pausas),
        "manifest1": path_manifest1,
        "manifest2": path_manifest2
    }


@app.post("/sesiones/{sesion_id}/pausas_detectadas")
def registrar_pausas_detectadas(sesion_id: int, data: dict, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    nuevas = data.get("pausas", [])

    # Si ya existen pausas detectadas, las unimos
    previas = sesion.pausas_detectadas or []

    sesion.pausas_detectadas = previas + nuevas
    db.commit()

    return {"message": "Pausas registradas", "total": len(sesion.pausas_detectadas)}


@app.post("/sesiones/{sesion_id}/pausas", response_model=PausaResponse)
def registrar_pausa(sesion_id: int, data: PausaCreate, db: Session = Depends(get_db)):
    # Validar sesión
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    pausa = models.LogPausa(
        sesion_id=sesion_id,
        inicio=data.inicio,
        fin=data.fin,
        duracion=data.duracion,
        fuente=data.fuente
    )

    db.add(pausa)
    db.commit()
    db.refresh(pausa)

    return pausa


@app.post("/sesiones/{sesion_id}/pausas_auto")
def registrar_pausas_auto(sesion_id: int, data: dict, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    pausas = data.get("pausas", [])
    count = 0

    for p in pausas:
        try:
            inicio = datetime.fromisoformat(p["inicio"])
            fin = datetime.fromisoformat(p["fin"])
            dur = float(p["duracion"])

            nueva = models.LogPausa(
                sesion_id=sesion_id,
                inicio=inicio,
                fin=fin,
                duracion=dur,
                fuente="auto"
            )
            db.add(nueva)
            count += 1

        except Exception as e:
            print(f"[PAUSA AUTO] Error procesando pausa: {e}")

    db.commit()

    return {"registradas": count}
