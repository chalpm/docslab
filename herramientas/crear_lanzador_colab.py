#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Crea abrir_docslab_en_colab.ipynb: el cuaderno que instala y abre DocsLab en Google Colab."""
from pathlib import Path

import nbformat as nbf

RAIZ = Path(__file__).resolve().parent.parent

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

celdas = [
    md("""# DocsLab en Google Colab

Este cuaderno instala LaTeX en la máquina de Colab y abre **DocsLab**, el editor de pósters, presentaciones, artículos, tesis y documentos con LaTeX, en una pestaña nueva del navegador.

Desde Colab, DocsLab puede ejecutar tus cuadernos (`.ipynb`) guardados en Google Drive y colocar sus figuras en tus documentos: en el editor, ve a **Cuadernos › Abrir desde una carpeta (Drive)**.

**Cómo usarlo**
1. Sube `docslab.zip` a tu Google Drive, en la carpeta `DocsLab` (o deja que la celda 2 te lo pida).
2. Ejecuta las celdas en orden (menú *Entorno de ejecución › Ejecutar todas*). La instalación de LaTeX tarda unos 3–4 minutos la primera vez.
3. Abre el enlace que aparece al final.

Tus proyectos se guardan en `MyDrive/DocsLab/datos`, así que siguen ahí la próxima vez. El enlace solo funciona mientras este cuaderno esté conectado a Colab."""),
    code("""#@title 1 · Opciones
GUARDAR_EN_DRIVE = True  #@param {type:"boolean"}
CARPETA_DRIVE = "/content/drive/MyDrive/DocsLab"  #@param {type:"string"}
PUERTO = 8765  #@param {type:"integer"}"""),
    code("""#@title 2 · Traer DocsLab (desde Drive o subiendo el zip)
import os, shutil, zipfile, pathlib

if GUARDAR_EN_DRIVE:
    from google.colab import drive
    drive.mount("/content/drive")
    pathlib.Path(CARPETA_DRIVE).mkdir(parents=True, exist_ok=True)

DESTINO = pathlib.Path("/content/docslab")
zip_drive = pathlib.Path(CARPETA_DRIVE) / "docslab.zip"
if GUARDAR_EN_DRIVE and zip_drive.exists():
    origen = zip_drive
else:
    from google.colab import files
    print("Sube docslab.zip:")
    subido = files.upload()
    origen = pathlib.Path(next(iter(subido)))

if DESTINO.exists():
    shutil.rmtree(DESTINO)
with zipfile.ZipFile(origen) as z:
    z.extractall("/content")
# el zip trae la carpeta docslab/
if not (DESTINO / "servidor.py").exists():
    candidatos = list(pathlib.Path("/content").glob("*/servidor.py"))
    if candidatos:
        candidatos[0].parent.rename(DESTINO)
print("DocsLab en", DESTINO, "·", "listo" if (DESTINO / "servidor.py").exists() else "NO se encontró servidor.py")"""),
    code("""#@title 3 · Instalar LaTeX y las dependencias (3–4 minutos la primera vez)
import subprocess, shutil
if shutil.which("pdflatex") is None:
    subprocess.run("apt-get -qq update && DEBIAN_FRONTEND=noninteractive apt-get -qq install -y --no-install-recommends "
                   "texlive-latex-recommended texlive-latex-extra texlive-pictures texlive-fonts-recommended "
                   "lmodern poppler-utils > /dev/null", shell=True, check=True)
subprocess.run("pip -q install flask nbclient nbformat ipykernel pillow python-pptx seaborn plotly kaleido", shell=True, check=True)
print(subprocess.run(["pdflatex", "--version"], capture_output=True, text=True).stdout.splitlines()[0])"""),
    code("""#@title 4 · Abrir DocsLab
import subprocess, time, sys, pathlib, urllib.request
datos = pathlib.Path(CARPETA_DRIVE) / "datos" if GUARDAR_EN_DRIVE else pathlib.Path("/content/docslab_datos")
# si venías de PosterLab, tus proyectos se copian una vez a la carpeta nueva (los originales no se tocan)
import shutil
viejos = pathlib.Path("/content/drive/MyDrive/PosterLab/datos")
if GUARDAR_EN_DRIVE and viejos.exists() and not datos.exists():
    shutil.copytree(viejos, datos)
    print("Se copiaron tus proyectos de PosterLab a", datos)
datos.mkdir(parents=True, exist_ok=True)
registro = open("/content/docslab.log", "a")
proceso = subprocess.Popen([sys.executable, "/content/docslab/servidor.py", "--colab", "--puerto", str(PUERTO),
                            "--datos", str(datos), "--raices", "/content"],
                           stdout=registro, stderr=subprocess.STDOUT)
for _ in range(60):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/api/estado", timeout=1)
        break
    except Exception:
        time.sleep(0.5)
else:
    print("DocsLab no arrancó; mira /content/docslab.log")

from google.colab.output import eval_js, serve_kernel_port_as_window
print("Proyectos guardados en", datos)
print("Enlace:", eval_js(f"google.colab.kernel.proxyPort({PUERTO})"))
serve_kernel_port_as_window(PUERTO, path="/")"""),
    md("""Si prefieres trabajar dentro de esta página, ejecuta la celda siguiente: muestra DocsLab incrustado (es más cómodo en una pestaña aparte)."""),
    code("""#@title 5 · (Opcional) Ver DocsLab dentro del cuaderno
from google.colab.output import serve_kernel_port_as_iframe
serve_kernel_port_as_iframe(PUERTO, path="/", height=900)"""),
    code("""#@title 6 · Detener DocsLab
proceso.terminate()
print("DocsLab detenido. Tus proyectos siguen en", datos)"""),
]

nb = nbf.v4.new_notebook(cells=celdas, metadata={
    "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
    "language_info": {"name": "python"},
    "colab": {"provenance": [], "name": "abrir_docslab_en_colab.ipynb"},
})
destino = RAIZ / "abrir_docslab_en_colab.ipynb"
nbf.write(nb, str(destino))
nbf.validate(nbf.read(str(destino), as_version=4))
print("escrito", destino)
