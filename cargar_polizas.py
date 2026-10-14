"""
Carga pólizas desde un Excel A TRAVÉS DE LA API (mismas validaciones que un POST).

    python cargar_polizas.py                      # el Excel guardado, o el de demostración
    python cargar_polizas.py datos/otro.xlsx      # un archivo concreto

Qué archivo usa si no se indica ninguno:
  1. el Excel donde la app guarda las pólizas (RUTA_EXCEL, por defecto
     datos/polizas_guardadas.xlsx), si existe;
  2. si no, datos/polizas_demo.xlsx, las pólizas inventadas de demostración.

Es idempotente: una póliza cuyo número ya está en la base se salta (409), así que
se puede ejecutar en cada arranque sin duplicar nada. Escribe en la base que diga
DATABASE_URL; el esquema tiene que existir (`alembic upgrade head`).
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).parent.resolve()
DEMO = RAIZ / "datos" / "polizas_demo.xlsx"


def archivo_por_defecto(ruta_guardada: str) -> Path:
    guardado = Path(ruta_guardada)
    if not guardado.is_absolute():
        guardado = RAIZ / guardado
    return guardado if guardado.exists() else DEMO


def cargar(cliente, ruta: str | Path) -> dict:
    """Envía cada póliza del Excel con `cliente.post` y cuenta el resultado."""
    from excel import leer

    resultado = {"creadas": 0, "ya_existian": 0, "rechazadas": []}
    for poliza in leer(ruta):
        r = cliente.post("/polizas", json=poliza)
        if r.status_code == 201:
            resultado["creadas"] += 1
        elif r.status_code == 409:
            resultado["ya_existian"] += 1
        else:
            resultado["rechazadas"].append((poliza["numero"], r.status_code, r.text[:200]))
    return resultado


def main() -> int:
    import warnings
    warnings.filterwarnings("ignore", message=".*httpx.*")  # aviso interno de TestClient, irrelevante aquí
    sys.path.insert(0, str(RAIZ))
    from fastapi.testclient import TestClient

    from config import get_settings
    from main import app

    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else archivo_por_defecto(get_settings().ruta_excel)
    if not ruta.exists():
        print(f"No existe {ruta}: no se carga nada.")
        return 1
    res = cargar(TestClient(app), ruta)
    print(f"{ruta.name}: {res['creadas']} pólizas creadas, {res['ya_existian']} ya existían, "
          f"{len(res['rechazadas'])} rechazadas.")
    for numero, codigo, detalle in res["rechazadas"]:
        print(f"  · {numero}: {codigo} {detalle}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
