# Bitácora de uso de IA

**Grupo:** <número> · **Integrantes:** <nombre 1>, <nombre 2>, <nombre 3>
**Herramientas usadas:** Claude (modo Cowork de la app de escritorio, modelo configurado `claude-opus-5-5`)

> Las tres secciones son obligatorias. **`## Rechazado` es la que se califica.**
> Una bitácora que solo lista prompts aceptados vale la mitad.
>
> Esta bitácora registra **una sesión real** con Claude, el 28 sep 2026. No se inventaron
> prompts ni respuestas. Para `ia_tests_propuesta.py` solo se cita el prompt que viene en el
> propio archivo. **Pendiente de los integrantes:** poner quién lanzó cada prompt y añadir
> las filas de lo que ustedes rechacen al revisar este trabajo; esas filas son las que cuentan.

## Prompts

| # | Parte | Quién | Prompt (resumido si es largo) |
|---|-------|-------|-------------------------------|
| 1 | A · B · C · D · E | <integrante> | «Actúa como un desarrollador senior de Python especializado en FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest y Docker […]». Trabajar sobre la carpeta `polizas-api-v0` sin modificarla, en una copia `polizas-api-v0-refactor`; no inventar errores, SHA, comandos ni salidas (escribir «NO VERIFICADO» si algo no se puede comprobar); conservar el contrato y los 12 tests de `tests/test_contrato.py`; hacer las partes A–E en orden (diagnóstico con 8–14 hallazgos y evidencia real, refactor B1–B10, medición con 10 y 2000 pólizas, auditoría de los tests de IA con mutaciones, bitácora); y mejorar la interfaz HTML/CSS sin alterar la API. |
| 2 | D (dato) | Asistente de IA (autor desconocido) | Prompt citado en `ia_tests_propuesta.py`: «Escribe con pytest y TestClient una batería de pruebas para esta API de pólizas. Aísla la base de datos para que las pruebas nunca toquen datos reales, cubre creación, consulta, errores y el endpoint de puntuación, y usa datos variados para no probar siempre lo mismo. Aplica buenas prácticas.» |
| 3 | Extras | <integrante> | «Crea una guía muy detallada de qué hiciste, además crea una lista de pólizas inventadas para que ya estén disponibles y dale una opción para que se guarden las pólizas creadas en un Excel de manera permanente». |

## Aceptado

| # | Qué propuso la IA | Por qué lo aceptamos | Qué cambiamos antes de usarlo |
|---|-------------------|----------------------|-------------------------------|
| 1 | Los 14 hallazgos de `HALLAZGOS.md`, cada uno con un comando ejecutado sobre `v0-semilla` | Cada salida se obtuvo ejecutando el comando con el servicio del semilla levantado; se pueden reproducir | Los comandos que crean pólizas usan `$RANDOM` en el número, para no chocar con el 409 si se repiten; H10 va el último porque deja la sesión global inservible |
| 2 | `get_db` como generador con `yield`/`close()` y una sesión por petición | Es la causa raíz de H10 (sesión global rota tras un `IntegrityError`) y lo exige B3 | Se añadió `expire_on_commit=False` para devolver el objeto tras el `commit` sin otra consulta |
| 3 | Estrategias de carga `selectinload` / `lazy` / `joinedload` / `agregada` | Se aceptaron **después** de medir las tres alternativas en copias temporales del servicio (tabla en `HALLAZGOS.md` · Parte C) | El 5 de `/polizas` con 2000 pólizas se verificó registrando las sentencias: `selectinload` parte el `IN` en lotes de 500 |
| 4 | Aislamiento de los tests propios con una base temporal migrada con Alembic y `dependency_overrides[database.get_db]` | Así se prueban también las migraciones y la base de la app no cambia (comprobado: el SHA-256 de `app.db` era igual antes y después) | Se restaura el override anterior al terminar, para no interferir con la fixture de `test_contrato.py` |
| 5 | Interfaz estática en `/ui/` (HTML + CSS + JS sin dependencias) | Solo consume los endpoints existentes; al montarse con `StaticFiles` no añade rutas de API | Se probó con un navegador sin interfaz: crear póliza (201), duplicado (409), fechas invertidas (422), declarar siniestro y puntuar |
| 6 | Pólizas de demostración en `datos/polizas_demo.xlsx`, cargadas con `cargar_polizas.py` por la API, y botón «Guardar en Excel» (`POST /exportar/excel`) | La carga pasa por las mismas validaciones que un `POST`; es idempotente (409 = se salta); el Excel exportado se puede volver a cargar | Probado: 30 creadas y luego 0 duplicadas; tras borrar la base, el arranque recupera las 31 pólizas del Excel guardado |

## Rechazado

| # | Qué propuso la IA | Por qué lo rechazamos | Qué hicimos en su lugar |
|---|-------------------|-----------------------|-------------------------|
| 1 | `ia_tests_propuesta.py`: sustituir la sesión con un `get_db` **propio** que devuelve `MagicMock()` | La clave de `dependency_overrides` no es `database.get_db`, así que nunca se aplica. Comprobado: la base «real» pasó de 0 a 7 pólizas tras correrla. Y un mock que acepta cualquier llamada tampoco probaría nada | Fixture `cliente` en `tests/conftest.py` que sustituye `database.get_db` por una sesión sobre una base temporal (DICTAMEN_IA.md · Defecto 2) |
| 2 | `ia_tests_propuesta.py`: aserciones como `status_code in (200, 201, 422)`, `in (200, 404)` o `< 500` | No pueden fallar. Con el 201 quitado del servicio siguió `6 passed` | Un código esperado por test (`== 201`, `== 404`, `== 422`, `== 409`) y comparación de valores (Defecto 1) |
| 3 | `ia_tests_propuesta.py`: «datos variados» con `random` sin semilla | Con el mismo código mutado, 10 corridas dieron 5 en verde y 5 en rojo: el resultado depende del azar | Casos fijos parametrizados, incluidos los bordes (Defecto 3) |
| 4 | (Claude, alternativa que llegó a escribir y luego descartó) Quitar `.title()` del validador de `asegurado` para «conservar lo enviado» | El defecto (H7) era que el validador no devolvía el valor, no la normalización. `"Carla Ibáñez".title()` conserva el nombre y el test de contrato pasa | `return " ".join(v.split()).title()`: se corrige el `return` y se mantiene la intención del autor |
| 5 | (Claude, alternativa considerada y descartada) `joinedload` también en `/polizas`, porque da 1 consulta en vez de 5 | Midió lo mismo (179.2 frente a 173.4 ms con 2000 pólizas); en uno-a-muchos repite las columnas de la póliza en cada fila y obliga a `.unique()` | `selectinload`, que no duplica filas, y se explica el 5 en la Parte C |
| 6 | (Claude, alternativa considerada y descartada) Servir la interfaz con una ruta `GET /` que devuelva el HTML | Sería una ruta sin `response_model`, en contra de B6, que exige `response_model` en **todas** las rutas, y no aporta nada a la API | `app.mount("/ui", StaticFiles(...))`: un montaje estático, no una ruta de la API |
| 7 | (Claude, alternativa considerada y descartada) Crear las tablas en las fixtures de los tests con `Base.metadata.create_all` | Funciona, pero así los tests no ejercitan las migraciones que usa el calificador | La fixture aplica `alembic upgrade head` una vez por sesión de pytest y copia esa base a cada test |
| 8 | (Claude, alternativa considerada y descartada) Descargar la imagen base de Docker desde otro registro cuando Docker Hub dio 403 en el entorno de trabajo | Habría sido saltarse la política de red del entorno, y la imagen no sería la que exige B9 | Se pidió al usuario permitir `registry-1.docker.io`, `auth.docker.io` y `production.cloudfront.docker.com`; con eso se descargó la imagen oficial y se verificó el contenedor (build, `/health` desde el host, usuario `app`, `HEALTHCHECK` healthy, restart y contenedor nuevo) |
| 9 | (Claude, alternativa considerada y descartada) Añadir al `Dockerfile` del repositorio la configuración del certificado del proxy de su entorno para que `pip install` funcionara dentro del `docker build` | Es un requisito de la red de ese entorno de pruebas (proxy que inspecciona TLS), no del proyecto: en la máquina del calificador sobraría y metería en el repositorio configuración ajena | El `Dockerfile` entregado no se tocó. Para la prueba local se construyó con una copia temporal fuera del repositorio que solo cambia la línea `RUN pip install` de la etapa 1 (monta el certificado como *secret* de BuildKit, que no queda en la imagen); la etapa final es idéntica |
| 10 | (Claude, alternativa considerada y descartada) Insertar las pólizas de demostración en una migración de Alembic o en el arranque de la app | El calificador y los tests esperan que `alembic upgrade head` cree una base vacía; con datos sembrados fallarían los tests que comparan listas exactas y cambiarían los conteos de `CONSULTAS.csv` | La carga es un script aparte (`cargar_polizas.py`) que solo ejecuta `iniciar_api.bat` |
| 11 | (Claude, alternativa considerada y descartada) Una ruta de descarga del Excel con `FileResponse` | Sería una ruta sin `response_model` (B6) | `POST /exportar/excel` escribe el archivo en disco y responde con un `response_model` (ruta, número de pólizas y siniestros, hora) |
