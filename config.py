"""Configuración del servicio, leída del entorno y de `.env` (B2).

Los valores reales de los secretos nunca se versionan: van en `.env` (ignorado por
git) o en variables de entorno. `.env.example` trae valores de ejemplo.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///polizas.db"
    # Valor de desarrollo para que `docker run` arranque sin .env; en producción se
    # sustituye por la variable de entorno SECRETO_FIRMA.
    secreto_firma: str = "solo-desarrollo-cambiar"
    clave_api_reaseguro: str = ""
    ruta_modelo: str = "modelo.pkl"
    umbral_alto_riesgo: float = Field(default=0.6, ge=0, le=1)
    # Excel donde POST /exportar/excel guarda las pólizas (y de donde cargar_polizas.py las lee).
    ruta_excel: str = "datos/polizas_guardadas.xlsx"


@lru_cache
def get_settings() -> Settings:
    """Una sola instancia por proceso; se inyecta con `Depends(get_settings)`."""
    return Settings()
