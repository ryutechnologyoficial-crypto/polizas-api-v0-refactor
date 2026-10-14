# ---- Etapa 1: construir el entorno virtual con las dependencias -----------------
FROM python:3.11.9-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---- Etapa 2: imagen final, sin herramientas de compilación ni caché de pip ----
FROM python:3.11.9-slim-bookworm AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DATABASE_URL=sqlite:////app/data/polizas.db \
    RUTA_EXCEL=/app/data/polizas_guardadas.xlsx

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app alembic.ini config.py database.py modelos.py esquemas.py excel.py main.py modelo.pkl ./
COPY --chown=app:app alembic/ ./alembic/
COPY --chown=app:app static/ ./static/
RUN mkdir -p /app/data && chown app:app /app/data

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import json,sys,urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3); sys.exit(0 if json.load(r).get('base_de_datos') else 1)"

# Aplica las migraciones sobre la base del contenedor y arranca sin --reload,
# escuchando en todas las interfaces para que el puerto publicado responda desde el host.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn main:app --host 0.0.0.0 --port 8000"]
