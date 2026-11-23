#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-only
# DocsLab: prepara lo que hace falta la primera vez y abre el editor en el navegador.
#
#   macOS:  doble clic en este archivo, o en la Terminal:  sh iniciar.command
#   Linux:  sh iniciar.command
#
# Las dependencias de Python van en un entorno propio (.venv, dentro de esta carpeta),
# sin tocar el Python del sistema. Se instalan la primera vez y cuando cambia
# requirements.txt. Lo que escribas después se pasa al servidor, por ejemplo:
#   sh iniciar.command --puerto 9000 --datos ~/DocsLab
# Con otro Python:  DOCSLAB_PYTHON=python3.12 sh iniciar.command
cd "$(dirname "$0")" || exit 1

# Python 3.11 o posterior: el de DOCSLAB_PYTHON si se indica; si no, python3 o el más nuevo que haya
valido() { "$1" -c 'import sys; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; }
PY=""
if [ -n "$DOCSLAB_PYTHON" ]; then
  valido "$DOCSLAB_PYTHON" && PY="$DOCSLAB_PYTHON"
else
  for c in python3 python3.14 python3.13 python3.12 python3.11; do
    if command -v "$c" >/dev/null 2>&1 && valido "$c"; then PY="$c"; break; fi
  done
fi
if [ -z "$PY" ]; then
  viejo="$("${DOCSLAB_PYTHON:-python3}" -c 'import platform; print(platform.python_version())' 2>/dev/null)"
  if [ -n "$viejo" ]; then
    echo "DocsLab necesita Python 3.11 o posterior y el que encuentro es $viejo."
  else
    echo "No encuentro Python 3."
  fi
  echo "  macOS:          brew install python"
  echo "  Ubuntu 24.04+ / Debian 12+:  sudo apt install python3 python3-venv"
  echo "  Ubuntu 22.04:   sudo apt install python3.11 python3.11-venv"
  echo "  Luego vuelve a abrir este archivo (o usa DOCSLAB_PYTHON=python3.12 sh iniciar.command)."
  exit 1
fi

# entorno propio; si quedó a medias (sin pip) o es de un Python anterior a 3.11, se rehace
if [ ! -x .venv/bin/python ] || ! valido .venv/bin/python || ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  echo "Preparando DocsLab (un par de minutos; con $PY)..."
  if ! "$PY" -m venv --clear .venv; then
    echo "No se pudo crear el entorno de Python (.venv)."
    echo "  Ubuntu/Debian:  sudo apt install python3-venv (o python3.11-venv)   y vuelve a intentarlo"
    exit 1
  fi
fi

# dependencias: la primera vez y cuando cambia requirements.txt
if ! cmp -s requirements.txt .venv/requirements-instalados.txt 2>/dev/null; then
  echo "Instalando las dependencias de Python..."
  if ! .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt; then
    echo "Falló la instalación de las dependencias. Revisa la conexión a internet y vuelve a intentarlo."
    exit 1
  fi
  cp requirements.txt .venv/requirements-instalados.txt
fi

# avisos (DocsLab arranca igual; el editor también los muestra)
PATH="$PATH:/Library/TeX/texbin"      # MacTeX, por si esta ventana se abrió antes de instalarlo
export PATH
if ! command -v pdflatex >/dev/null 2>&1; then
  echo "Aviso: no encuentro LaTeX (pdflatex), sin él no hay vista previa."
  echo "  macOS:          brew install --cask mactex-no-gui"
  echo "  Ubuntu/Debian:  ver «Instalación» en README.md"
fi
if ! command -v pdftoppm >/dev/null 2>&1; then
  echo "Aviso: no encuentro Poppler (miniaturas y revisión para imprimir)."
  echo "  macOS:          brew install poppler"
  echo "  Ubuntu/Debian:  sudo apt install poppler-utils"
fi

.venv/bin/python servidor.py --abrir "$@"
codigo=$?
[ "$codigo" -eq 3 ] && exit 0          # ya estaba abierto: solo se abrió el navegador
exit "$codigo"
