#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Genera static/img/variantes/<clave>.png: una miniatura de cada variante de
elemento, recortada de un póster de muestra compilado con marcas de posición."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from docslab import compilador, generador, modelo as M, variantes as V  # noqa: E402

IMG = RAIZ / "herramientas" / "fuentes" / "img"
DESTINO = RAIZ / "static" / "img" / "variantes"
COLUMNAS = 4
PPP = 110

IMAGENES = ["prueba1.png", "prueba6.png", "prueba3.png", "prueba4.png", "prueba2.png", "prueba5.png"]


def elemento(clave: str, i: int) -> dict:
    e = V.elemento_nuevo(clave, f"e-{clave.lower()}")
    v = V.POR_CLAVE[clave]
    k = 0
    for c in v["campos"]:
        if c["tipo"] == "imagen":
            e[c["nombre"]] = "recursos/" + ("qr_prueba.png" if clave == "txtContacto" else IMAGENES[(i + k) % len(IMAGENES)])
            k += 1
    if clave in ("txtCitaBarra", "txtResaltado", "txtRecuadro", "txtInvertido", "txtEcuacion", "txtLineaTiempo"):
        e["mostrar_titulo"] = False
    if clave == "espacio":
        e["alto"] = "3em"
    if clave == "bibliografia":
        e["incluir"] = "todas"
    return e


# Referencias de muestra (inventadas, con la forma de las reales) para la miniatura de T36
REFERENCIAS = [
    {"tipo": "articulo", "autores": ["Apellido, Ana", "Ejemplo, Bruno"], "anio": "2024",
     "titulo": "Un título de artículo para mostrar el formato", "revista": "Revista de Ejemplo",
     "volumen": "12", "numero": "3", "paginas": "45–58"},
    {"tipo": "libro", "autores": ["Muestra, Carla"], "anio": "2021", "titulo": "Un libro de referencia",
     "editorial": "Editorial Ejemplo"},
    {"tipo": "web", "autores": ["{Instituto de Ejemplo}"], "anio": "2025", "titulo": "Datos abiertos del proyecto",
     "url": "https://ejemplo.org/datos"},
]


def miniatura_espacio(destino: Path):
    """Un espacio vertical no se ve: se dibuja lo que hace (separar dos bloques)."""
    from PIL import Image, ImageDraw
    w, h = 360, 200
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    gris, linea, flecha = (243, 245, 248), (200, 206, 212), (128, 80, 111)
    d.rounded_rectangle((24, 14, w - 24, 62), 6, fill=gris)
    d.rounded_rectangle((24, h - 62, w - 24, h - 14), 6, fill=gris)
    for x in range(24, w - 24, 14):
        d.line((x, 74, x + 7, 74), fill=linea, width=2)
        d.line((x, h - 74, x + 7, h - 74), fill=linea, width=2)
    cx = w // 2
    d.line((cx, 82, cx, h - 82), fill=flecha, width=3)
    d.polygon([(cx - 8, 92), (cx + 8, 92), (cx, 80)], fill=flecha)
    d.polygon([(cx - 8, h - 92), (cx + 8, h - 92), (cx, h - 80)], fill=flecha)
    im.save(destino, optimize=True)


def main():
    claves = [v["clave"] for v in V.VARIANTES]
    m = M.normalizar({})
    m["lienzo"].update({"tamano": "personalizado", "ancho": "640mm", "alto": "3200mm", "margen": "12mm"})
    m["tipografia"]["fuente"] = 15
    m["cabecera"]["visible"] = False
    m["pie"]["visible"] = False
    m["estilo"].update({"separacion_columnas": "14mm", "separacion_bloques": "6mm"})
    filas = []
    for i in range(0, len(claves), COLUMNAS):
        cols = []
        for j, clave in enumerate(claves[i:i + COLUMNAS]):
            b = {"id": f"b-{clave.lower()}", "titulo": "", "mostrar_titulo": False, "estilo": "ninguno",
                 "elementos": [elemento(clave, i + j)]}
            cols.append({"id": f"c-{clave.lower()}", "bloques": [b], "distribucion": "arriba"})
        filas.append({"id": f"f-{i}", "columnas": cols, "rejilla": COLUMNAS, "igualar": False})
    m["filas"] = filas
    m["bibliografia"] = {"estilo": "apa", "referencias": REFERENCIAS}
    m = M.normalizar(m)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "recursos").mkdir()
        for p in IMG.glob("*.png"):
            shutil.copy(p, d / "recursos" / p.name)
        tex, _ = generador.generar(m, marcas=True)
        (d / "poster.tex").write_text(tex, encoding="utf-8")
        res = compilador.compilar(d, "poster.tex", max_pasadas=3)
        if not res.get("ok"):
            print("Error al compilar:", res.get("errores"))
            sys.exit(1)
        pdf = d / "build" / "poster.pdf"
        subprocess.run(["pdftoppm", "-png", "-r", str(PPP), "-singlefile", str(pdf), str(d / "pagina")], check=True)
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        pagina = Image.open(d / "pagina.png").convert("RGB")
        cajas = res["posiciones"]["cajas"]
        DESTINO.mkdir(parents=True, exist_ok=True)
        hechas = 0
        for clave in claves:
            if clave == "espacio":            # un espacio en blanco: se dibuja aparte
                miniatura_espacio(DESTINO / "espacio.png")
                hechas += 1
                continue
            c = cajas.get(f"e-{clave.lower()}")
            if not c:
                print("sin posición:", clave)
                continue
            f = PPP / 72.27
            margen = 6
            caja = (max(0, int(c["x0"] * f) - margen), max(0, int(c["y0"] * f) - margen),
                    int(c["x1"] * f) + margen, int(c["y1"] * f) + margen)
            if caja[3] - caja[1] < 20:            # elementos muy bajos (banda, espacio)
                caja = (caja[0], caja[1] - 14, caja[2], caja[3] + 14)
            rec = pagina.crop(caja)
            rec.thumbnail((360, 200), Image.LANCZOS)
            rec.save(DESTINO / f"{clave}.png", optimize=True)
            hechas += 1
        print(f"{hechas} miniaturas en {DESTINO}")


if __name__ == "__main__":
    main()
