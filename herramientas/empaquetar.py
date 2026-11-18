#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Crea los zips para entregar:

    dist/docslab.zip                              la aplicación completa (carpeta docslab/)
    dist/plantilla_postercientifico_overleaf.zip    la plantilla LaTeX sola, lista para Overleaf
"""
from __future__ import annotations

import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIST = RAIZ / "dist"
OMITIR_DIRS = {"datos", "dist", "__pycache__", ".pytest_cache", ".ipynb_checkpoints", ".git", "build", ".venv", "venv"}
OMITIR_EXT = {".pyc", ".aux", ".log", ".out", ".pos"}

LEEME_OVERLEAF = """Plantilla postercientifico.sty (versión 2, por capas)
=====================================================

Archivos
  main.tex                  póster de ejemplo (A1) con capas, filas y cajas con título opcional
  catalogo.tex              catálogo de 6 páginas: 34 imágenes, 35 textos, 12 estilos de caja,
                            filas, capas, tipografías y todas las claves de configuración
  postercientifico.sty      la plantilla
  img/                      imágenes de prueba (cámbialas por las tuyas)

En Overleaf
  1. New Project > Upload Project y elige este zip.
  2. Menu > Compiler: pdfLaTeX (es el valor por defecto).
  3. Recompile. Para ver el catálogo: Menu > Main document > catalogo.tex.

En tu equipo
  pdflatex main.tex   y repítelo mientras el registro diga «Rerun ... (vuelve a compilar)»:
                      2 o 3 veces si una fila usa alto=llenar o una caja usa estirar

Lo esencial
  \\posterconfig{tamano=A0, tema=verde, columnas=3, fuente=30pt, estilo bloque=barra}
  \\begin{fila}[columnas=3, alto=llenar]
    \\begin{columna}
      \\begin{caja}[titulo={Métodos}, mostrar titulo=false] ... \\end{caja}
    \\end{columna}
  \\end{fila}
  \\colocartexto[capa=frente, x=0.5, y=0.5, rotacion=30, escala=9, opacidad=0.1]{BORRADOR}
  \\nuevacapa[z=5]{notas}    \\ocultarcapa{frente}    \\configcapa{fondo}{opacidad=0.5}

Tipografías
  familia=sourcesans, familia titulos=merriweather     (clásicas y libres de TeX Live: ver el catálogo)
  Una propia (.ttf u .otf), compilando con LuaLaTeX (Menu > Compiler: LuaLaTeX):
    \\posterfamilia{mia}{fuentes/}{Mia-Regular.ttf}{Mia-Bold.ttf}{}{}   y   familia=mia

Para la imprenta
  \\posterconfig{sangrado=3mm, marcas corte=true}     el fondo pasa 3 mm del borde y marcas de corte
"""


def _incluir(p: Path) -> bool:
    rel = p.relative_to(RAIZ)
    if any(parte in OMITIR_DIRS for parte in rel.parts):
        return False
    return p.is_file() and p.suffix.lower() not in OMITIR_EXT


def app():
    DIST.mkdir(exist_ok=True)
    destino = DIST / "docslab.zip"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(RAIZ.rglob("*")):
            if _incluir(p):
                z.write(p, "docslab/" + p.relative_to(RAIZ).as_posix())
    return destino


def overleaf():
    DIST.mkdir(exist_ok=True)
    destino = DIST / "plantilla_postercientifico_overleaf.zip"
    fuentes = RAIZ / "herramientas" / "fuentes"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(RAIZ / "latex" / "postercientifico.sty", "postercientifico.sty")
        z.write(fuentes / "ejemplo_capas.tex", "main.tex")
        z.write(fuentes / "catalogo.tex", "catalogo.tex")
        for img in sorted((fuentes / "img").glob("*.png")):
            z.write(img, "img/" + img.name)
        z.writestr("LEEME.txt", LEEME_OVERLEAF)
    return destino


if __name__ == "__main__":
    for f in (app(), overleaf()):
        with zipfile.ZipFile(f) as z:
            n = len(z.namelist())
        print(f"{f.relative_to(RAIZ)}  {f.stat().st_size / 1e6:.1f} MB  {n} archivos")
