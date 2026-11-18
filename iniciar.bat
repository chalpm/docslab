@echo off
rem SPDX-License-Identifier: AGPL-3.0-only
rem DocsLab: prepara lo que hace falta la primera vez y abre el editor en el navegador.
rem Doble clic en este archivo. Lo que escribas despues se pasa al servidor, por ejemplo:
rem   iniciar.bat --puerto 9000
rem Las dependencias de Python van en un entorno propio (.venv, dentro de esta carpeta),
rem sin tocar el Python del sistema. Se instalan la primera vez y cuando cambia requirements.txt.
setlocal
cd /d "%~dp0"

rem Python 3.11 o posterior: el lanzador "py" de python.org (el mas nuevo que haya) o, si no,
rem "python". Se prueban de verdad: el "python" de la Microsoft Store sin Python instalado no sirve.
set "PY="
for %%V in (3 3.14 3.13 3.12 3.11) do if not defined PY call :probar "py -%%V"
if not defined PY call :probar "python"
if not defined PY goto sin_python

rem entorno propio; si quedo a medias (sin pip) o es de un Python anterior a 3.11, se rehace
set "VPY=.venv\Scripts\python.exe"
if not exist "%VPY%" goto crear
"%VPY%" -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
if errorlevel 1 goto crear
call "%VPY%" -m pip --version >nul 2>nul
if errorlevel 1 goto crear
goto dependencias

:crear
echo Preparando DocsLab, tarda un par de minutos...
call %PY% -m venv --clear .venv
if errorlevel 1 goto sin_entorno
if not exist "%VPY%" goto sin_entorno

:dependencias
rem la primera vez y cuando cambia requirements.txt
if not exist ".venv\requirements-instalados.txt" goto instalar
fc /b requirements.txt .venv\requirements-instalados.txt >nul 2>nul
if not errorlevel 1 goto arrancar
:instalar
echo Instalando las dependencias de Python...
call "%VPY%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto sin_dependencias
copy /y requirements.txt .venv\requirements-instalados.txt >nul

:arrancar
rem si falta LaTeX, el servidor lo dice al arrancar
"%VPY%" servidor.py --abrir %*
rem 3: ya estaba abierto (solo se abrio el navegador)
if errorlevel 3 exit /b 0
echo.
echo DocsLab se ha cerrado.
pause
exit /b 0

:probar
rem %~1 es la orden ("py -3.12" o "python"): vale si existe y es 3.11 o posterior
%~1 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
if not errorlevel 1 set "PY=%~1"
exit /b 0

:sin_python
echo DocsLab necesita Python 3.11 o posterior y no lo encuentro
echo (o el que hay es mas antiguo). Instalalo desde https://www.python.org/downloads/
echo y marca la casilla "Add python.exe to PATH". Luego vuelve a abrir este archivo.
pause
exit /b 1

:sin_entorno
echo No se pudo crear el entorno de Python ^(.venv^).
echo Si no tienes Python, instalalo desde https://www.python.org/downloads/
echo y marca la casilla "Add python.exe to PATH".
pause
exit /b 1

:sin_dependencias
echo Fallo la instalacion de las dependencias. Revisa la conexion a internet y vuelve a intentarlo.
pause
exit /b 1
