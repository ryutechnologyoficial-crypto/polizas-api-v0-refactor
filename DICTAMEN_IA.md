# Dictamen sobre `ia_tests_propuesta.py` — Parte D

**Grupo:** <número> · **Integrantes:** <nombre 1>, <nombre 2>, <nombre 3>

> **Cómo se hicieron las comprobaciones.** Cada mutación se aplicó sobre una **copia
> desechable** del servicio ya refactorizado (el repositorio no se tocó). En cada copia:
> `DATABASE_URL=sqlite:///<copia>/real.db`, `alembic upgrade head`, y luego
> `pytest ia_tests_propuesta.py -q` y `pytest tests/test_ia_corregido.py -q`. La base «real»
> hace falta porque la batería original, como se explica en el defecto 2, escribe en la base
> de la aplicación. Las salidas son literales; de la corrida corregida se copian las líneas
> `FAILED` y el resumen.
>
> Sobre el código sano: original `6 passed`, corregida `30 passed` (dos corridas seguidas).
>
> **Pendiente de los integrantes:** completar el título exacto de la sección del material
> donde dice «sección NO VERIFICADA».

## Defecto 1

- **Qué está mal**: tests que no pueden fallar. Las aserciones aceptan cualquier resultado posible: `test_crear_poliza_responde` y `test_primas_variadas_son_aceptadas` aceptan `(200, 201, 422)`, es decir, éxito con el código incorrecto, éxito con el correcto y rechazo; `test_consultar_poliza_inexistente` acepta `(200, 404)` (200 es justo el defecto H4 del semilla); `test_listar_polizas_no_falla` solo exige `< 500`; y `test_score_de_poliza_recien_creada` acepta `"puntaje" in r.json() or "error" in r.json()`.
- **Por qué es un defecto** (módulo · sección): M10 · sección NO VERIFICADA. Un test solo aporta información si existe una implementación incorrecta que lo ponga en rojo. Aquí el contrato exige **201** al crear (B6), y el test acepta 200: si el servicio deja de devolver 201, nadie se entera.
- **Cómo lo comprobamos**: quitamos el `status_code=201` de `POST /polizas`. La batería original sigue en verde; la corregida falla en todos los tests que crean pólizas y afirman `== 201`.

```diff
--- a/main.py
+++ b/main.py
@@ -72,3 +72,3 @@
 
-@app.post("/polizas", response_model=PolizaSalida, status_code=status.HTTP_201_CREATED)
+@app.post("/polizas", response_model=PolizaSalida)
 def crear_poliza(datos: PolizaEntrada, db: Session = Depends(get_db),
```

```
$ pytest ia_tests_propuesta.py -q
......                                                                   [100%]
6 passed in 1.65s
```

```
$ pytest tests/test_ia_corregido.py -q
FAILED tests/test_ia_corregido.py::test_crear_poliza_devuelve_201_con_los_datos_enviados
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[0.01-auto]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[0.01-hogar]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[0.01-vida]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[350000-auto]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[350000-hogar]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[350000-vida]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[4800000-auto]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[4800000-hogar]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[4800000-vida]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[25000000-auto]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[25000000-hogar]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[25000000-vida]
FAILED tests/test_ia_corregido.py::test_numero_duplicado_da_409 - AssertionEr...
FAILED tests/test_ia_corregido.py::test_score_de_poliza_recien_creada_registra_la_prediccion
15 failed, 15 passed in 1.99s
```

- **Corrección**: cada test afirma **un** resultado: `== 201` y los campos devueltos iguales a los enviados (`test_crear_poliza_devuelve_201_con_los_datos_enviados`); `== 404` para `GET`/`PUT /polizas/999999`, `POST /polizas/999999/siniestros` y `POST /score` de un número inexistente (`test_recurso_inexistente_da_404`); `== 422` para cada entrada inválida; `== 409` para el duplicado.

## Defecto 2

- **Qué está mal**: tests que no prueban lo que dicen probar. (a) El bloque «Aislamiento de la base de datos» dice que las pruebas nunca escriben en la base de la aplicación, pero define **su propia** función `get_db` (línea 27) y la registra como clave en `app.dependency_overrides[get_db] = get_db` (línea 31). La app nunca depende de esa función, sino de `database.get_db`, así que la sustitución no se aplica nunca y todas las pruebas escriben en la base real. Además, si se aplicara, un `MagicMock` como sesión no prueba nada: aceptaría cualquier llamada. (b) `test_resumen_devuelve_lista` dice probar el resumen y solo comprueba que la respuesta sea una lista: no mira ni una cifra.
- **Por qué es un defecto** (módulo · sección): M10 · sección NO VERIFICADA (sustitución de dependencias con `app.dependency_overrides`, restricción B8). La clave de `dependency_overrides` tiene que ser el mismo objeto función que la ruta declara en `Depends(...)`.
- **Cómo lo comprobamos**: primero, el aislamiento. Sobre el código sano, con una base «real» vacía y migrada:

```
$ cnt(){ python3 -c "import sqlite3;print(sqlite3.connect('real.db').execute('select count(*) from polizas').fetchone()[0])"; }
$ echo "antes: $(cnt)"; pytest tests/test_ia_corregido.py -q | tail -1; echo "tras corregida: $(cnt)"; pytest ia_tests_propuesta.py -q | tail -1; echo "tras original: $(cnt)"
antes: 0
30 passed in 1.95s
tras corregida: 0
6 passed in 1.44s
tras original: 7
$ python -c "import ia_tests_propuesta as t, database; print('clave sustituida es database.get_db?', list(t.app.dependency_overrides)[0] is database.get_db)"
clave sustituida es database.get_db? False
```

Después, la mutación: el resumen cuenta mal. `COUNT(*)` en lugar de `COUNT(siniestros.id)` hace que, con el `LEFT OUTER JOIN`, una póliza **sin** siniestros aparezca con 1.

```diff
--- a/main.py
+++ b/main.py
@@ -143,3 +143,3 @@
         select(Poliza.numero,
-               func.count(Siniestro.id).label("n_siniestros"),
+               func.count().label("n_siniestros"),
                func.round(func.coalesce(func.sum(Siniestro.monto), 0), 2).label("monto_total"))
```

```
$ pytest ia_tests_propuesta.py -q
......                                                                   [100%]
6 passed in 1.62s
```

```
$ pytest tests/test_ia_corregido.py -q
E         At index 1 diff: {'numero': 'POL-IA-000002', 'n_siniestros': 1, 'monto_total': 0.0} != {'numero': 'POL-IA-000002', 'n_siniestros': 0, 'monto_total': 0}
FAILED tests/test_ia_corregido.py::test_resumen_cuenta_y_suma_los_siniestros_de_cada_poliza
1 failed, 29 passed in 2.00s
```

- **Corrección**: la fixture `cliente` (`tests/conftest.py`) sustituye **`database.get_db`** por una sesión sobre una base SQLite temporal, nueva en cada test y migrada con Alembic; al terminar restaura el override anterior. `test_la_poliza_creada_queda_guardada` comprueba que lo escrito está en esa base temporal. Los tests leen de vuelta lo que escriben: el resumen se compara con las cifras exactas (2 siniestros y 1 000 000; 0 y 0), la póliza creada se vuelve a pedir por `GET`, y la predicción aparece en `/predicciones` con su `numero`. Así también detectan un `commit` que se quita (comprobado: con `db.flush()` en lugar de `db.commit()` en `POST /polizas`, `/polizas/{id}/siniestros` o `/score`, la corregida falla con 6, 1 y 1 tests, respectivamente).

## Defecto 3

- **Qué está mal**: tests que unas veces pasan y otras no. `_poliza()` genera la entrada con `random` **sin semilla**: `tipo = random.choice([...])` y `prima = random.uniform(1, 5_000_000)`. Cada corrida prueba datos distintos, y como además escribe en la base real (defecto 2), el resultado depende de la suerte y del estado previo. Si el servicio rechaza solo una parte del rango, `test_score_de_poliza_recien_creada` falla o pasa según la prima que salga: la creación devuelve 422 (no se comprueba) y el `/score` devuelve 404.
- **Por qué es un defecto** (módulo · sección): M10 · sección NO VERIFICADA. Un test debe ser determinista: la misma entrada y el mismo código tienen que dar siempre el mismo resultado. Si no, un rojo no se puede reproducir para depurarlo y un verde no garantiza nada. «Datos variados» se consigue con casos fijos parametrizados, no con azar.
- **Cómo lo comprobamos**: mutación: un validador que rechaza primas válidas por encima de 2 500 000. Con el mismo código, **diez corridas seguidas** de la batería original dan resultados distintos: 5 en verde y 5 en rojo. La corregida falla siempre, en los mismos 6 casos.

```diff
--- a/esquemas.py
+++ b/esquemas.py
@@ -23,3 +23,3 @@
     tipo: TipoPoliza = Field(description="auto, hogar o vida")
-    prima: float = Field(gt=0, description="Prima anual, en pesos")
+    prima: float = Field(gt=0, le=2_500_000, description="Prima anual, en pesos")
     fecha_inicio: date
```

```
$ for i in $(seq 1 10); do printf "corrida %2d: " $i; pytest ia_tests_propuesta.py -q | tail -1; done
corrida  1: 1 failed, 5 passed in 1.55s
corrida  2: 6 passed in 1.48s
corrida  3: 6 passed in 1.52s
corrida  4: 6 passed in 1.61s
corrida  5: 6 passed in 1.44s
corrida  6: 1 failed, 5 passed in 1.63s
corrida  7: 1 failed, 5 passed in 1.44s
corrida  8: 6 passed in 1.50s
corrida  9: 1 failed, 5 passed in 1.66s
corrida 10: 1 failed, 5 passed in 1.66s

$ pytest ia_tests_propuesta.py -q | grep -E "FAILED|assert|passed|failed"   # una corrida en rojo
>       assert r.status_code == 200
E       assert 404 == 200
FAILED ia_tests_propuesta.py::test_score_de_poliza_recien_creada - assert 404...
1 failed, 5 passed in 1.55s
```

```
$ pytest tests/test_ia_corregido.py -q
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[4800000-auto]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[4800000-hogar]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[4800000-vida]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[25000000-auto]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[25000000-hogar]
FAILED tests/test_ia_corregido.py::test_primas_y_tipos_validos_son_aceptados[25000000-vida]
6 failed, 24 passed in 1.87s
```

- **Corrección**: sin `random`. Datos fijos y `@pytest.mark.parametrize`: los tres tipos × cuatro primas (0.01, 350 000, 4 800 000, 25 000 000), cada combinación con `== 201`; y los bordes inválidos (`prima` 0 y −1, tipo `moto`, asegurado de 1 carácter, fechas invertidas o iguales, siniestro con monto negativo), cada uno con `== 422` y comprobando que no se guardó nada. Los números de póliza también son fijos, lo que es seguro porque cada test tiene su propia base.

---

**Otras mutaciones con las que se validó la batería corregida** (el calificador usa tres que no
conocemos): quitar el 404 de `GET /polizas/{id}` (`return db.get(...)`) → la corregida da
`1 failed`; anular el `model_validator` de fechas → `2 failed`; `flush` en lugar de `commit` en
siniestros y en `/score` → `1 failed` cada una. En todas, la original quedó `6 passed`, salvo
dos: con el `commit` quitado en `POST /polizas` y con el 404 quitado de `GET /polizas/{id}` dio
`1 failed, 5 passed`. Lo decimos porque es cierto: la batería original no es ciega del todo.
