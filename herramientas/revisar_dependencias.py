#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""¿Está todo al día? Revisa las dependencias de DocsLab antes de publicar una versión.

    python herramientas/revisar_dependencias.py

1. Python (requirements.txt): vulnerabilidades conocidas con pip-audit (pip install pip-audit).
2. JavaScript incluido en static/vendor: versión incluida frente a la última publicada en npm.
   Para actualizar uno: npm install <paquete>@<versión> en una carpeta aparte y copiar el archivo.

Necesita conexión a internet. No cambia nada: solo informa. Sale con 1 si encuentra algo.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VENDOR = RAIZ / "static" / "vendor"

# paquete npm → (archivo incluido, expresión que saca su versión, rama que se sigue)
JS = {
    "vue": ("vue.global.prod.js", r"vue v(\d+\.\d+\.\d+)", "3"),
    "pdfjs-dist": ("pdf.min.mjs", r"apiVersion:\"(\d+\.\d+\.\d+)\"", "4"),
    "codemirror": ("codemirror/codemirror.js", r"CodeMirror\.version = \"(\d+\.\d+\.\d+)\"", "5"),
}


def version_incluida(archivo: str, patron: str) -> str | None:
    m = re.search(patron, (VENDOR / archivo).read_text(encoding="utf-8", errors="ignore"))
    return m.group(1) if m else None


def ultima_npm(paquete: str, rama: str) -> str | None:
    npm = shutil.which("npm")
    if not npm:
        return None
    r = subprocess.run([npm, "view", f"{paquete}@{rama}", "version", "--json"], capture_output=True, text=True)
    if r.returncode:
        return None
    v = json.loads(r.stdout or "null")
    return v[-1] if isinstance(v, list) else v


def main() -> int:
    problemas = 0
    print("== Python (requirements.txt)")
    if shutil.which("pip-audit") or subprocess.run([sys.executable, "-m", "pip_audit", "--version"],
                                                   capture_output=True).returncode == 0:
        r = subprocess.run([sys.executable, "-m", "pip_audit", "-r", str(RAIZ / "requirements.txt"), "--desc", "off"],
                           capture_output=True, text=True)
        print((r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr).strip() else "(sin salida)")
        problemas += r.returncode != 0
    else:
        print("pip-audit no está instalado: pip install pip-audit")
        problemas += 1
    print("\n== JavaScript incluido (static/vendor)")
    for paquete, (archivo, patron, rama) in JS.items():
        incluida, ultima = version_incluida(archivo, patron), ultima_npm(paquete, rama)
        estado = "al día" if incluida and incluida == ultima else (f"hay {ultima}" if ultima else "no se pudo consultar npm")
        print(f"{paquete:12s} incluida {incluida or '?':10s} → {estado} (rama {rama}.x)")
        problemas += incluida != ultima
    print("\nNota: pdf.js se mantiene en la rama 4.x a propósito (ver docs/ARQUITECTURA.md y CHANGELOG 1.6.0).")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
