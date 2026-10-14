# Hallazgos — Parte A

**Grupo:** <número> · **Integrantes:** <nombre 1>, <nombre 2>, <nombre 3>

> Todas las salidas son literales: se obtuvieron ejecutando cada comando sobre `v0-semilla`
> (`5a5cc5b`) con `uvicorn main:app --host 127.0.0.1 --port 8000` levantado sobre el `app.db`
> del semilla. H10 deja la sesión global inservible: **ejecútenlo el último** (o reinicien el
> servicio después). H13 se ejecuta en la raíz del repositorio (usa `git`).
>
> **Pendiente de los integrantes:** donde dice «sección NO VERIFICADA» hay que poner el título
> exacto de la lección tal como aparece en el menú lateral del material; no tuvimos acceso a él
> y no se inventó ninguno.

| ID | Síntoma observable | Causa | Módulo · Sección | SHA donde se observa | Comando de evidencia | Salida obtenida | Corrección aplicada |
|----|--------------------|-------|------------------|----------------------|----------------------|-----------------|---------------------|
| H1 | `GET /health` no existe: 404 | `main.py` no declara ninguna ruta de salud | M6 · 5. Routing y CRUD | `v0-semilla` | `curl -s -o /dev/null -w "%{http_code}" localhost:8000/health` | `404` | `GET /health` con `response_model=Salud`; ejecuta `SELECT 1` con la sesión de `get_db` y devuelve `{"estado","base_de_datos"}` |
| H2 | `POST /polizas` responde 200 en lugar de 201 | `@app.post("/polizas")` (main.py:44) sin `status_code=201` | M6 · 5. Routing y CRUD | `v0-semilla` | `curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/polizas -H "Content-Type: application/json" -d "{\"numero\":\"POL-H2-$RANDOM\",\"asegurado\":\"Ana Rueda\",\"tipo\":\"auto\",\"prima\":1250000,\"fecha_inicio\":\"2026-01-15\",\"fecha_fin\":\"2027-01-14\"}"` | `200` | `status_code=201` en `POST /polizas` y `POST /polizas/{id}/siniestros` |
| H3 | La respuesta expone `token_firma`, un hash derivado del secreto de firma | `crear_poliza` devuelve el objeto ORM (main.py:57) y `_poliza` copia `token_firma` (main.py:38); no hay `response_model` que filtre | M6 · 5. Routing y CRUD | `v0-semilla` | `curl -s -X POST localhost:8000/polizas -H "Content-Type: application/json" -d "{\"numero\":\"POL-H3-$RANDOM\",\"asegurado\":\"Ana Rueda\",\"tipo\":\"auto\",\"prima\":1250000,\"fecha_inicio\":\"2026-01-15\",\"fecha_fin\":\"2027-01-14\"}" \| grep -o '"token_firma"'` | `"token_firma"` | `response_model=PolizaSalida` (sin `token_firma`) en todas las rutas de pólizas |
| H4 | Recursos inexistentes responden 200 con `{"error": ...}` en `GET /polizas/{id}`, `PUT /polizas/{id}` y `POST /score` | Los handlers hacen `return {"error": ...}` (main.py:69, 77, 114) en vez de `raise HTTPException(404)` | M6 · 5. Routing y CRUD | `v0-semilla` | `for m in "GET /polizas/999999" "PUT /polizas/999999" "POST /score"; do set -- $m; curl -s -o /dev/null -w "%{http_code} " -X $1 localhost:8000$2 -H "Content-Type: application/json" -d '{"prima":10,"numero":"POL-NO-EXISTE"}'; done` | `200 200 200 ` | `HTTPException(status_code=404)` en los tres casos |
| H5 | Se puede declarar un siniestro a una póliza que no existe: 200 y fila huérfana | `declarar_siniestro` no comprueba la póliza (main.py:87) y SQLite no aplica claves foráneas porque nunca se activa `PRAGMA foreign_keys` (database.py:12) | M9 · sección NO VERIFICADA | `v0-semilla` | `curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/polizas/999999/siniestros -H "Content-Type: application/json" -d '{"fecha":"2026-03-02","monto":850000,"descripcion":"Choque leve"}'` | `200` | 404 si la póliza no existe + listener `connect` que ejecuta `PRAGMA foreign_keys=ON` en cada conexión |
| H6 | `PUT` con un solo campo borra los demás (quedan en `null`) | `datos.model_dump()` (main.py:78) incluye los campos no enviados con valor `None` y se asignan todos | M6 · 5. Routing y CRUD | `v0-semilla` | `curl -s -X PUT localhost:8000/polizas/1 -H "Content-Type: application/json" -d '{"prima":999000}' \| grep -o '"asegurado":[^,]*,"tipo":[^,]*'` | `"asegurado":null,"tipo":null` | `model_dump(exclude_unset=True)`: solo se asignan los campos enviados |
| H7 | El asegurado se guarda como `null` aunque se envíe | El `field_validator` `normalizar_asegurado` (esquemas.py:28) calcula el valor pero no lo devuelve: Pydantic usa `None` | M7 · sección NO VERIFICADA | `v0-semilla` | `curl -s -X POST localhost:8000/polizas -H "Content-Type: application/json" -d "{\"numero\":\"POL-H7-$RANDOM\",\"asegurado\":\"Carla Ibáñez\",\"tipo\":\"auto\",\"prima\":1250000,\"fecha_inicio\":\"2026-01-15\",\"fecha_fin\":\"2027-01-14\"}" \| grep -o '"asegurado":[^,]*'` | `"asegurado":null` | El validador hace `return " ".join(v.split()).title()`: conserva la normalización que pretendía el autor y devuelve el valor |
| H8 | Una póliza con `fecha_fin` anterior a `fecha_inicio` se acepta (200) | `PolizaEntrada` no tiene `model_validator` que compare las fechas (esquemas.py:15-28) | M7 · sección NO VERIFICADA | `v0-semilla` | `curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/polizas -H "Content-Type: application/json" -d "{\"numero\":\"POL-H8-$RANDOM\",\"asegurado\":\"Ana Rueda\",\"tipo\":\"auto\",\"prima\":1250000,\"fecha_inicio\":\"2027-01-14\",\"fecha_fin\":\"2026-01-15\"}"` | `200` | `@model_validator(mode="after")` que lanza `ValueError` si `fecha_fin <= fecha_inicio` → 422 |
| H9 | Un siniestro anidado con monto negativo se acepta (200) | `siniestros: list[dict]` (esquemas.py:22): el contenido no se valida; `SiniestroEntrada` existe pero no se usa | M7 · sección NO VERIFICADA | `v0-semilla` | `curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/polizas -H "Content-Type: application/json" -d "{\"numero\":\"POL-H9-$RANDOM\",\"asegurado\":\"Ana Rueda\",\"tipo\":\"auto\",\"prima\":1250000,\"fecha_inicio\":\"2026-01-15\",\"fecha_fin\":\"2027-01-14\",\"siniestros\":[{\"fecha\":\"2026-03-02\",\"monto\":-50,\"descripcion\":\"Choque leve\"}]}"` | `200` | `siniestros: list[SiniestroEntrada]` → 422 |
| H10 | Un número de póliza repetido da 500 y, a partir de ahí, **todo** el servicio responde 500 | Sesión única a nivel de módulo (database.py:16) compartida por todas las peticiones: el `IntegrityError` deja la transacción en `PendingRollbackError` y nadie hace `rollback` | M8 · sección NO VERIFICADA | `v0-semilla` | `n=POL-DUP-$RANDOM; for i in 1 2; do curl -s -o /dev/null -w "%{http_code} " -X POST localhost:8000/polizas -H "Content-Type: application/json" -d "{\"numero\":\"$n\",\"asegurado\":\"Ana Rueda\",\"tipo\":\"auto\",\"prima\":1250000,\"fecha_inicio\":\"2026-01-15\",\"fecha_fin\":\"2027-01-14\"}"; done; curl -s -o /dev/null -w "%{http_code}" localhost:8000/polizas` | `200 500 500` | `get_db` generador con `yield` y `close()` (una sesión por petición) + `IntegrityError` → `rollback` y 409 |
| H11 | `GET /predicciones` no dice a qué póliza (número) corresponde cada predicción | `listar_predicciones` (main.py:128) devuelve solo `poliza_id` | M9 · sección NO VERIFICADA | `v0-semilla` | `curl -s -o /dev/null -X POST localhost:8000/score -H "Content-Type: application/json" -d '{"numero":"POL-2026-00001"}'; curl -s localhost:8000/predicciones \| grep -c '"numero"'` | `0` | `PrediccionSalida` con `numero` y `puntaje`; la consulta hace `join` con `Poliza` |
| H12 | La app ignora `DATABASE_URL` y los secretos viven en el código | `config.py` son constantes (líneas 4-7): no hay `BaseSettings` ni lectura de `.env`; `database.py:12` usa `config.DATABASE_URL` fijo | M8 · sección NO VERIFICADA | `v0-semilla` | `DATABASE_URL=sqlite:///otra.db python -c "import config, database; print(database.engine.url, config.SECRETO_FIRMA)"` | `sqlite:///app.db aseguradora-santo-tomas-2026-firma-7c1e` | `Settings(BaseSettings)` que lee `.env`, `get_settings()` con `lru_cache` inyectada con `Depends`; secretos fuera del repositorio, `.env.example` con valores de ejemplo |
| H13 | Entorno no reproducible: dependencias sin versión y la base de datos versionada | `requirements.txt` sin `==`; `.gitignore` solo cubre `*.pyc`, así que `app.db` está en el índice | M8 · sección NO VERIFICADA | `v0-semilla` | `echo $(grep -c "==" requirements.txt) $(git ls-files \| grep -c "\.db$")` | `0 1` | Versiones fijadas con las que se probó; `.gitignore` con `.env`, `*.db`, `venv/`; `git rm --cached app.db` |
| H14 | La imagen no es apta para producción ni responde desde el host | `Dockerfile`: `FROM python:latest` (no fijado, una sola etapa), sin `USER` ni `HEALTHCHECK`, `CMD` con `--reload` y `--host 127.0.0.1` (solo escucha dentro del contenedor) | M11 · sección NO VERIFICADA | `v0-semilla` | `echo $(grep -cE "^(USER\|HEALTHCHECK)" Dockerfile) $(grep -oE -- "python:latest\|--reload\|127\.0\.0\.1" Dockerfile)` | `0 python:latest --reload 127.0.0.1` | Dockerfile multietapa sobre `python:3.11.9-slim-bookworm`, usuario `app` sin root, `HEALTHCHECK` contra `/health`, `CMD` sin `--reload` y con `--host 0.0.0.0`, `.dockerignore` |

**Otros defectos observados que no se incluyen como fila** (para no pasar de 14):

- `Base.metadata.create_all(engine)` en el arranque (main.py:17) y ausencia de Alembic: el esquema no tiene migraciones versionadas. Corregido con `alembic/` (restricción B5).
- `tests/test_api.py` escribe en `app.db` y **falla la segunda vez** que se corre (`IntegrityError` por `POL-TEST-00001` repetido). Comprobado sobre una copia del semilla: 1.ª corrida `2 passed`, 2.ª corrida `2 failed`, y el SHA-256 de `app.db` cambió. Corregido: ahora usa `dependency_overrides` sobre una base temporal (B8).

**Modificación de `contar_consultas.py`:** ver sección «Parte C».

---

# Parte C — Interpretación de las consultas

**Cómo se midió.** `python contar_consultas.py` (10 y 2000 pólizas, 3 siniestros cada una,
sembradas por la API sobre una base temporal migrada con Alembic). **Modificación de
`contar_consultas.py`:** solo se añadió el diccionario `ESTRATEGIAS` para rellenar la columna
`estrategia` con lo que quedó en `main.py`; el conteo no se tocó.

**Antes de decidir se midieron las alternativas.** Se generaron tres copias temporales de
`main.py` (todas las relaciones `lazy`, todas `selectinload`, todas `joinedload`; en `/resumen`
esas variantes cargan las pólizas con sus siniestros y cuentan en Python) y se pasó el mismo
`contar_consultas.py` a cada una, de forma secuencial. Consultas SQL (tiempo en ms, una sola
medición en nuestra máquina, solo orientativo):

| Endpoint | n | `lazy` | `selectinload` | `joinedload` | `agregada` |
|---|---:|---:|---:|---:|---:|
| `/polizas` | 10 | 11 (6.8) | 2 (4.8) | 1 (3.2) | — |
| `/polizas` | 2000 | 2001 (716.9) | 5 (173.4) | 1 (179.2) | — |
| `/polizas/{id}` | 10 | 2 (2.7) | 2 (3.8) | 1 (2.6) | — |
| `/polizas/{id}` | 2000 | 2 (3.3) | 2 (4.3) | 1 (3.1) | — |
| `/siniestros` | 10 | 11 (5.4) | 2 (3.7) | 1 (3.3) | — |
| `/siniestros` | 2000 | 2001 (567.4) | 5 (212.1) | 1 (140.8) | — |
| `/resumen` | 10 | 11 (5.3) | 2 (3.6) | 1 (3.4) | 1 (2.5) |
| `/resumen` | 2000 | 2001 (595.1) | 5 (127.6) | 1 (195.7) | 1 (39.2) |

Las salidas crudas de esas tres corridas están en `mediciones/alternativa_*.csv` (mismas
columnas que `CONSULTAS.csv`). La columna `agregada` de `/resumen` y todas las filas de `CONSULTAS.csv` salen de la corrida
final sobre el código entregado.

**La regla «cargar todo de una vez es más eficiente» falla de dos maneras distintas:**

1. **Seguirla empeora el rendimiento — `/resumen`.** Cargar pólizas *y* siniestros de una
   vez (`joinedload`) da 1 consulta, pero trae a Python las 6000 filas de siniestros (con las
   columnas de la póliza repetidas en cada una) solo para contarlas y sumarlas: 195.7 ms, peor
   incluso que `selectinload` (127.6 ms). La consulta agregada también es 1, pero la base
   devuelve 2000 filas de tres columnas ya calculadas: 39.2 ms.
2. **El código la incumple y la medición dice que da exactamente igual — `/polizas/{id}`.**
   Dejarlo `lazy` (no «cargar todo de una vez») da 2 consultas, las mismas 2 que
   `selectinload`, con 10 y con 2000 pólizas: el `lazy` solo es un problema (N+1) cuando se
   recorre una colección de padres, y aquí hay un único padre.

## `/polizas`

**Estrategia: `selectinload` · 2 consultas con 10 pólizas, 5 con 2000.** La primera consulta
trae las pólizas; `selectinload` trae después los siniestros con
`WHERE siniestros.poliza_id IN (...)`. SQLAlchemy parte esa lista `IN` en lotes de 500
identificadores (lo comprobamos registrando las sentencias: con 2000 pólizas salen 4 `SELECT`
de siniestros de 500 parámetros cada uno), por eso con 2000 son 1 + ⌈2000/500⌉ = 5 y con 10 son
1 + 1 = 2. Crece con N/500, no con N: con `lazy` serían 1 + N (11 y 2001). `joinedload` da 1
consulta y tardó lo mismo (179.2 frente a 173.4 ms), pero en una relación uno-a-muchos
multiplica filas —cada póliza se repite tantas veces como siniestros tenga— y obliga a
`.unique()`; `selectinload` no duplica nada. Nos sorprendió que no fueran 2 fijas: el tamaño del
lote explica el 5.

## `/polizas/{id}`

**Estrategia: `lazy` · 2 consultas con 10 y con 2000 pólizas.** `db.get` trae la póliza por
clave primaria (1) y, al serializar `siniestros`, la carga perezosa emite la segunda (2). No
depende del tamaño de la cartera porque siempre hay un solo padre. `selectinload` da las mismas
2 (medido); `joinedload` daría 1, pero es un endpoint de un registro con 3 siniestros: la
diferencia medida es de décimas de milisegundo (3.3 frente a 3.1 ms). Se deja `lazy`, que es el
comportamiento por defecto de la relación y no necesita opciones; este es el caso en que
«incumplir» la regla da exactamente igual.

## `/siniestros`

**Estrategia: `joinedload` · 1 consulta con 10 y con 2000 pólizas.** Aquí la relación es
muchos-a-uno (cada siniestro tiene una póliza): el `JOIN` añade las columnas de la póliza a la
fila del siniestro **sin multiplicar filas** (6000 siniestros → 6000 filas). Por eso una sola
consulta, constante. Con `lazy` serían 1 + (pólizas distintas) = 11 y 2001 (el mapa de
identidad evita repetir la misma póliza, pero hay una por póliza); con `selectinload`,
1 + ⌈2000/500⌉ = 5.

## `/resumen`

**Estrategia: `agregada` · 1 consulta con 10 y con 2000 pólizas.** `SELECT numero,
COUNT(siniestros.id), ROUND(COALESCE(SUM(monto),0),2) … LEFT OUTER JOIN siniestros … GROUP BY
polizas.id`: la base cuenta y suma y devuelve una fila por póliza; no se construye ningún
objeto `Siniestro`. El `LEFT OUTER JOIN` y el `COALESCE` mantienen las pólizas sin siniestros
(con 0). Es 1 consulta sea cual sea N, y es el caso en que cargar todo de una vez
(`joinedload`, 1 consulta, 195.7 ms) rinde peor que no cargar nada (39.2 ms con 2000 pólizas).
