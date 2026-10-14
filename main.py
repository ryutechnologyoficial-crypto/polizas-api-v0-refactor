"""
polizas-api-v0 — Gestión de pólizas y siniestros.
Aseguradora Santo Tomás · prototipo interno.

El esquema lo crea Alembic (`alembic upgrade head`), no el arranque de la app.
"""
import hashlib
import pickle
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from config import Settings, get_settings
import excel
from database import get_db
from esquemas import (ExportacionExcel, PolizaActualizacion, PolizaEntrada, PolizaSalida, PrediccionSalida,
                      PuntuacionEntrada, PuntuacionSalida, ResumenPoliza, Salud,
                      SiniestroConPoliza, SiniestroCreado, SiniestroEntrada)
from modelos import Poliza, Prediccion, Siniestro

app = FastAPI(title="Pólizas API", version="1.0.0")

# Interfaz web estática (no forma parte del contrato de la API): /ui/
_ESTATICOS = Path(__file__).parent / "static"
if _ESTATICOS.is_dir():
    app.mount("/ui", StaticFiles(directory=_ESTATICOS, html=True), name="ui")


# --- Dependencias -----------------------------------------------------------

@lru_cache
def cargar_modelo(ruta: str) -> Any:
    """Carga el modelo una sola vez por proceso (y solo cuando se necesita)."""
    with open(ruta, "rb") as fh:
        return pickle.load(fh)


def get_modelo(settings: Settings = Depends(get_settings)) -> Any:
    return cargar_modelo(settings.ruta_modelo)


def firmar(numero: str, secreto: str) -> str:
    return hashlib.sha256(f"{numero}:{secreto}".encode()).hexdigest()


def _poliza_o_404(db: Session, id_poliza: int) -> Poliza:
    poliza = db.get(Poliza, id_poliza)
    if poliza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no existe la póliza {id_poliza}")
    return poliza


# --- Salud --------------------------------------------------------------------

@app.get("/health", response_model=Salud)
def health(db: Session = Depends(get_db)):
    """200 siempre que el proceso responda; `base_de_datos` dice si la base contesta."""
    try:
        db.execute(text("SELECT 1"))
        return Salud(estado="ok", base_de_datos=True)
    except Exception:
        return Salud(estado="degradado", base_de_datos=False)


# --- Pólizas ------------------------------------------------------------------

@app.post("/polizas", response_model=PolizaSalida, status_code=status.HTTP_201_CREATED)
def crear_poliza(datos: PolizaEntrada, db: Session = Depends(get_db),
                 settings: Settings = Depends(get_settings)):
    poliza = Poliza(**datos.model_dump(exclude={"siniestros"}),
                    token_firma=firmar(datos.numero, settings.secreto_firma))
    poliza.siniestros = [Siniestro(**s.model_dump()) for s in datos.siniestros]
    db.add(poliza)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"ya existe la póliza {datos.numero}")
    return poliza


@app.get("/polizas", response_model=list[PolizaSalida])
def listar_polizas(db: Session = Depends(get_db)):
    # Parte C · selectinload: 1 consulta de pólizas + 1 de siniestros (IN ...), sea cual sea N.
    consulta = select(Poliza).options(selectinload(Poliza.siniestros)).order_by(Poliza.id)
    return db.scalars(consulta).all()


@app.get("/polizas/{id_poliza}", response_model=PolizaSalida)
def obtener_poliza(id_poliza: int, db: Session = Depends(get_db)):
    # Parte C · lazy: get por clave primaria + la carga perezosa de sus siniestros al
    # serializar = 2 consultas; selectinload daría las mismas 2 (medido en CONSULTAS.csv).
    return _poliza_o_404(db, id_poliza)


@app.put("/polizas/{id_poliza}", response_model=PolizaSalida)
def actualizar_poliza(id_poliza: int, datos: PolizaActualizacion, db: Session = Depends(get_db)):
    poliza = _poliza_o_404(db, id_poliza)
    cambios = datos.model_dump(exclude_unset=True)
    if "fecha_fin" in cambios and cambios["fecha_fin"] <= poliza.fecha_inicio:
        raise HTTPException(422,
                            "fecha_fin debe ser posterior a fecha_inicio")
    for campo, valor in cambios.items():
        setattr(poliza, campo, valor)
    db.commit()
    return poliza


@app.post("/polizas/{id_poliza}/siniestros", response_model=SiniestroCreado,
          status_code=status.HTTP_201_CREATED)
def declarar_siniestro(id_poliza: int, datos: SiniestroEntrada, db: Session = Depends(get_db)):
    _poliza_o_404(db, id_poliza)
    siniestro = Siniestro(poliza_id=id_poliza, **datos.model_dump())
    db.add(siniestro)
    db.commit()
    return siniestro


# --- Siniestros y resumen -------------------------------------------------------

@app.get("/siniestros", response_model=list[SiniestroConPoliza])
def listar_siniestros(db: Session = Depends(get_db)):
    # Parte C · joinedload: relación muchos-a-uno, el JOIN trae la póliza en la misma
    # fila sin multiplicar filas → 1 consulta.
    consulta = select(Siniestro).options(joinedload(Siniestro.poliza)).order_by(Siniestro.id)
    return [SiniestroConPoliza(id=s.id, poliza_id=s.poliza_id, numero_poliza=s.poliza.numero,
                               fecha=s.fecha, monto=s.monto, descripcion=s.descripcion,
                               estado=s.estado)
            for s in db.scalars(consulta)]


@app.get("/resumen", response_model=list[ResumenPoliza])
def resumen(db: Session = Depends(get_db)):
    # Parte C · agregada: COUNT y SUM los calcula la base con GROUP BY → 1 consulta,
    # sin traer ningún siniestro a Python. El OUTER JOIN conserva pólizas sin siniestros.
    consulta = (
        select(Poliza.numero,
               func.count(Siniestro.id).label("n_siniestros"),
               func.round(func.coalesce(func.sum(Siniestro.monto), 0), 2).label("monto_total"))
        .outerjoin(Siniestro, Siniestro.poliza_id == Poliza.id)
        .group_by(Poliza.id)
        .order_by(Poliza.id)
    )
    return db.execute(consulta).all()


# --- Puntuación -------------------------------------------------------------------

@app.post("/score", response_model=PuntuacionSalida)
def puntuar(datos: PuntuacionEntrada, db: Session = Depends(get_db),
            settings: Settings = Depends(get_settings), modelo: Any = Depends(get_modelo)):
    poliza = db.scalar(select(Poliza).where(Poliza.numero == datos.numero))
    if poliza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no existe la póliza {datos.numero}")
    n_siniestros, monto_total = db.execute(
        select(func.count(Siniestro.id), func.coalesce(func.sum(Siniestro.monto), 0))
        .where(Siniestro.poliza_id == poliza.id)).one()
    rasgos = [[poliza.prima, n_siniestros, monto_total, (date.today() - poliza.fecha_inicio).days]]
    puntaje = float(modelo.predict_proba(rasgos)[0][1])
    prediccion = Prediccion(poliza_id=poliza.id, puntaje=puntaje,
                            alto_riesgo=puntaje > settings.umbral_alto_riesgo)
    db.add(prediccion)
    db.commit()
    return PuntuacionSalida(numero=poliza.numero, puntaje=round(puntaje, 4),
                            alto_riesgo=prediccion.alto_riesgo)


@app.get("/predicciones", response_model=list[PrediccionSalida])
def listar_predicciones(db: Session = Depends(get_db)):
    consulta = (select(Prediccion.id, Prediccion.poliza_id, Poliza.numero, Prediccion.puntaje,
                       Prediccion.alto_riesgo, Prediccion.creado_en)
                .join(Poliza, Prediccion.poliza_id == Poliza.id)
                .order_by(Prediccion.id))
    return db.execute(consulta).all()


@app.post("/exportar/excel", response_model=ExportacionExcel)
def exportar_excel(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Guarda TODAS las pólizas y sus siniestros en el Excel de RUTA_EXCEL (lo reescribe).

    Ruta añadida (no forma parte del contrato del taller): copia permanente en Excel,
    que `cargar_polizas.py` puede volver a cargar en una base vacía.
    """
    try:
        info = excel.exportar(db, settings.ruta_excel)
    except PermissionError:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"no se pudo escribir {settings.ruta_excel}: ciérrelo si está abierto en Excel")
    return ExportacionExcel(**info, guardado_en=datetime.now())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
