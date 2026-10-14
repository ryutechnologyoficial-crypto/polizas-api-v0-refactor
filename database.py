"""Conexión a la base de datos: motor, fábrica de sesiones y sesión por petición."""
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import get_settings


class Base(DeclarativeBase):
    pass


def crear_engine(url: str) -> Engine:
    """Crea el motor; en SQLite activa las claves foráneas en cada conexión (B4)."""
    es_sqlite = url.startswith("sqlite")
    engine = create_engine(url, connect_args={"check_same_thread": False} if es_sqlite else {})
    if es_sqlite:
        @event.listens_for(engine, "connect")
        def _activar_fk(conexion_dbapi, _registro):
            cursor = conexion_dbapi.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


engine = crear_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Una sesión por petición: se abre, se entrega con `yield` y siempre se cierra (B3)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
