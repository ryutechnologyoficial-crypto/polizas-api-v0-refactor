# polizas-api-v0 (refactorizado)

Servicio de gestión de pólizas de la Aseguradora Santo Tomás. Registra pólizas
y los siniestros que se les declaran, resume la cartera y puntúa el riesgo de
cada póliza con un modelo, guardando cada predicción.

Requiere **Python 3.11** (la misma versión que la imagen de Docker).

## Puesta en marcha local

**En Windows, con doble clic:** `iniciar_api.bat`. La primera vez crea `venv`, instala las
dependencias y crea `.env`; siempre aplica las migraciones, carga las pólizas del Excel
(ver abajo), arranca el servicio en
<http://127.0.0.1:8000> y abre la interfaz en el navegador. Para detenerlo, cierre la ventana.

A mano (cualquier sistema):

```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                # Windows: copy .env.example .env
alembic upgrade head                # crea el esquema en la base de DATABASE_URL
uvicorn main:app --host 127.0.0.1 --port 8000
```

- API: <http://localhost:8000/docs> · salud: <http://localhost:8000/health>
- Interfaz web: <http://localhost:8000/ui/>

La configuración se lee de variables de entorno o de `.env` (ver `config.py`):

| Variable | Ejemplo | Para qué |
|---|---|---|
| `DATABASE_URL` | `sqlite:///polizas.db` | Base de datos; la usan la app y Alembic |
| `SECRETO_FIRMA` | *(secreto real, nunca en git)* | Firma interna de cada póliza |
| `CLAVE_API_REASEGURO` | *(secreto real, nunca en git)* | Reservada para la integración de reaseguro |
| `RUTA_MODELO` | `modelo.pkl` | Modelo de puntuación |
| `UMBRAL_ALTO_RIESGO` | `0.6` | Puntaje a partir del cual una póliza es de alto riesgo |

El esquema lo crean **las migraciones**, no el arranque: si cambian los modelos,
`alembic revision --autogenerate -m "..."` y `alembic upgrade head`.

## En contenedor

```bash
docker build -t polizas-api .
docker run -p 8000:8000 polizas-api
curl localhost:8000/health
```

La imagen es multietapa (`python:3.11.9-slim-bookworm`), corre con el usuario `app`
(no root), tiene `HEALTHCHECK` contra `/health` y no incluye `.env` ni bases de datos.
Al arrancar aplica `alembic upgrade head` sobre `/app/data/polizas.db` y lanza `uvicorn`
en `0.0.0.0:8000`.

**Datos y ciclo de vida del contenedor:** la base vive en el sistema de archivos del
contenedor. `docker restart` conserva los datos (es el mismo contenedor); borrar el
contenedor y crear otro desde la imagen empieza con una base vacía. Para conservarlos
entre contenedores: `docker run -p 8000:8000 -v polizas-datos:/app/data polizas-api`.

En producción, pasen los secretos al contenedor: `-e SECRETO_FIRMA=...`.

## Endpoints

| Método | Ruta | Qué hace | Códigos |
|---|---|---|---|
| POST | `/polizas` | Crea una póliza, con sus siniestros si ya tiene | 201 · 409 número repetido · 422 |
| GET | `/polizas` | Lista las pólizas con sus siniestros | 200 |
| GET | `/polizas/{id}` | Consulta una póliza | 200 · 404 |
| PUT | `/polizas/{id}` | Actualización **parcial**: solo cambia lo enviado | 200 · 404 · 422 |
| POST | `/polizas/{id}/siniestros` | Declara un siniestro | 201 · 404 · 422 |
| GET | `/siniestros` | Lista los siniestros con el número de su póliza | 200 |
| GET | `/resumen` | Número de siniestros y monto total por póliza | 200 |
| POST | `/score` | Puntúa el riesgo de una póliza y guarda la predicción | 200 · 404 · 422 |
| GET | `/predicciones` | Histórico de predicciones con el `numero` de la póliza | 200 |
| GET | `/health` | Indica si el servicio y la base de datos responden | 200 |
| POST | `/exportar/excel` | *(añadida)* Guarda todas las pólizas y siniestros en el Excel de `RUTA_EXCEL` | 200 · 409 si el archivo está abierto |

### Ejemplo

```bash
curl -X POST localhost:8000/polizas \
  -H "Content-Type: application/json" \
  -d '{"numero": "POL-2026-09001", "asegurado": "Ana Rueda", "tipo": "auto", "prima": 1250000,
       "fecha_inicio": "2026-01-15", "fecha_fin": "2027-01-14"}'
```

```bash
curl -X POST localhost:8000/score -H "Content-Type: application/json" -d '{"numero": "POL-2026-09001"}'
```

## Pólizas de demostración y copia en Excel

- `datos/polizas_demo.xlsx` trae **30 pólizas inventadas** (personas ficticias) con 36 siniestros.
  Se generan con `python datos/generar_demo.py` (siempre las mismas).
- `python cargar_polizas.py` las carga **a través de la API** (mismas validaciones que un `POST`).
  Si existe el Excel guardado (`RUTA_EXCEL`, por defecto `datos/polizas_guardadas.xlsx`) carga ese;
  si no, el de demostración. Las pólizas cuyo número ya existe se saltan: se puede correr en cada
  arranque sin duplicar nada. `iniciar_api.bat` lo hace automáticamente.
- En la interfaz (`/ui/`, pestaña Pólizas), **«Guardar en Excel»** reescribe `datos/polizas_guardadas.xlsx`
  con todas las pólizas (hojas `Polizas`, `Siniestros` y `Resumen`). Con **«Guardar automáticamente al crear»**
  marcado, se guarda solo después de cada póliza o siniestro creado desde la interfaz.
- Así el Excel es una copia permanente: aunque se borre la base (`polizas.db`), el siguiente arranque
  vuelve a cargar lo guardado.

Nada de esto cambia el contrato del taller: la carga no está en las migraciones ni en el arranque de
`main:app`, así que `alembic upgrade head` sigue creando una base **vacía** (la que esperan los tests y el
calificador) y Docker arranca vacío.

## Pruebas

```bash
pytest                              # tests/ : contrato + propios + batería de IA corregida
pytest tests/test_contrato.py -v    # la batería de contrato, intacta
```

Los tests propios sustituyen `database.get_db` con `app.dependency_overrides` por una
base temporal migrada con Alembic (`tests/conftest.py`): no tocan la base de la aplicación
y pasan igual dos veces seguidas.

## Utilidades

- `sembrar_datos.py` crea pólizas de ejemplo a través de la API.
- `contar_consultas.py` cuenta las sentencias SQL que emite cada endpoint y escribe `CONSULTAS.csv`.
- `verificar_entrega.py` comprueba la forma de la entrega.

## Entregables del taller

`HALLAZGOS.md` (partes A y C) · `CONSULTAS.csv` · `DICTAMEN_IA.md` y
`tests/test_ia_corregido.py` (parte D) · `BITACORA_IA.md` (parte E) · `EQUIPO.md`.
