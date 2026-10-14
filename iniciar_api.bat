@echo off
setlocal
rem ==========================================================================
rem  Polizas API - arranque con doble clic (Windows)
rem  1) crea el entorno virtual la primera vez   2) instala dependencias
rem  3) crea .env desde .env.example            4) aplica migraciones (Alembic)
rem  5) abre el navegador en /ui/                6) arranca uvicorn
rem  Para detener el servicio: cierre esta ventana o pulse Ctrl+C.
rem ==========================================================================
title Polizas API
cd /d "%~dp0"

set "PUERTO=8000"
set "PY="

rem --- 1. Buscar Python 3.11 o superior -------------------------------------
py -3.11 -c "import sys" >nul 2>&1 && set "PY=py -3.11"
if not defined PY (
    py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [ERROR] No se encontro Python 3.11 o superior.
    echo         Instalelo desde https://www.python.org/downloads/ marcando "Add python.exe to PATH".
    goto :fallo
)

rem --- 2. Entorno virtual ----------------------------------------------------
if not exist "venv\Scripts\python.exe" (
    echo Creando el entorno virtual con %PY% ...
    %PY% -m venv venv || goto :fallo
)
set "VPY=venv\Scripts\python.exe"

rem --- 3. Dependencias (solo si requirements.txt cambio desde la ultima vez) -
fc /b requirements.txt venv\requirements.instalado >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias, puede tardar unos minutos la primera vez...
    "%VPY%" -m pip install --disable-pip-version-check -q -r requirements.txt || goto :fallo
    copy /y requirements.txt venv\requirements.instalado >nul
)

rem --- 4. Configuracion ------------------------------------------------------
if not exist ".env" (
    echo Creando .env a partir de .env.example ...
    copy /y .env.example .env >nul || goto :fallo
)

rem --- 5. Migraciones --------------------------------------------------------
echo Aplicando migraciones...
"%VPY%" -m alembic upgrade head || goto :fallo

rem --- 5b. Polizas: si existe el Excel guardado lo carga; si no, las de demostracion.
rem         Las que ya estan en la base se saltan, asi que no se duplica nada.
"%VPY%" cargar_polizas.py

rem --- 6. Abrir el navegador cuando el servicio este listo y arrancar -------
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; Start-Process 'http://127.0.0.1:%PUERTO%/ui/'"

echo.
echo  Interfaz:      http://127.0.0.1:%PUERTO%/ui/
echo  Documentacion: http://127.0.0.1:%PUERTO%/docs
echo  Salud:         http://127.0.0.1:%PUERTO%/health
echo  Para detener: cierre esta ventana o pulse Ctrl+C
echo.
"%VPY%" -m uvicorn main:app --host 127.0.0.1 --port %PUERTO%
goto :fin

:fallo
echo.
echo [ERROR] El arranque se detuvo. Revise el mensaje de arriba.
pause
exit /b 1

:fin
pause
endlocal
