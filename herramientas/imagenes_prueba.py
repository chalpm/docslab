#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Genera las imágenes de prueba de las plantillas (herramientas/fuentes/img/prueba1–6.png).

Son marcadores de posición: un degradado sobrio con su número, su proporción y su
tamaño en píxeles, para ver cómo queda cada variante sin usar figuras reales.

    python herramientas/imagenes_prueba.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DESTINO = Path(__file__).resolve().parent / "fuentes" / "img"

# (número, ancho, alto, proporción, color inicial, color final)
IMAGENES = [
    (1, 1600, 1200, "4:3", "4E6A82", "8AA1B4"),   # pizarra
    (2, 1920, 1080, "16:9", "5E7A68", "9BB0A0"),  # salvia
    (3, 1400, 1400, "1:1", "94685A", "C6A090"),   # arcilla apagada
    (4, 1200, 1600, "3:4", "6C5B72", "A495A8"),   # ciruela
    (5, 2700, 900, "3:1", "55606C", "929DA8"),    # niebla
    (6, 1500, 1000, "3:2", "8E7A4E", "C3B087"),   # arena
]


def _rgb(h: str) -> tuple[int, int, int]:
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _fuente(tam: int, negrita: bool = False):
    nombres = ["DejaVuSans-Bold.ttf" if negrita else "DejaVuSans.ttf",
               "/usr/share/fonts/truetype/dejavu/" + ("DejaVuSans-Bold.ttf" if negrita else "DejaVuSans.ttf")]
    for n in nombres:
        try:
            return ImageFont.truetype(n, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def imagen(n: int, ancho: int, alto: int, proporcion: str, c0: str, c1: str) -> Image.Image:
    a, b = _rgb(c0), _rgb(c1)
    im = Image.new("RGB", (ancho, alto))
    px = im.load()
    for y in range(alto):
        for x in range(ancho):
            t = (x / ancho * 0.65 + (1 - y / alto) * 0.35)
            px[x, y] = tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(3))
    d = ImageDraw.Draw(im, "RGBA")
    paso = max(40, min(ancho, alto) // 12)
    for x in range(0, ancho, paso):
        d.line([(x, 0), (x, alto)], fill=(255, 255, 255, 18), width=1)
    for y in range(0, alto, paso):
        d.line([(0, y), (ancho, y)], fill=(255, 255, 255, 18), width=1)
    d.line([(0, 0), (ancho, alto)], fill=(255, 255, 255, 40), width=2)
    d.line([(0, alto), (ancho, 0)], fill=(255, 255, 255, 40), width=2)
    lado = min(ancho, alto)
    r = int(lado * 0.3)
    cx, cy = ancho // 2, alto // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*a, 140), outline=(255, 255, 255, 220), width=max(3, lado // 160))
    f_num = _fuente(int(r * 1.05), True)
    d.text((cx, cy - r * 0.12), str(n), font=f_num, fill=(255, 255, 255, 240), anchor="mm")
    f_lab = _fuente(max(14, int(r * 0.17)), True)
    d.text((cx, cy + r * 0.62), "PRUEBA", font=f_lab, fill=(255, 255, 255, 230), anchor="mm")
    f_peq = _fuente(max(14, lado // 34))
    margen = max(12, lado // 40)
    d.text((margen, margen), f"imagen de prueba {n} · {proporcion}", font=f_peq, fill=(255, 255, 255, 225), anchor="lt")
    d.text((ancho - margen, alto - margen), f"{ancho} × {alto} px", font=f_peq, fill=(255, 255, 255, 225), anchor="rb")
    d.rectangle([0, 0, ancho - 1, alto - 1], outline=(255, 255, 255, 90), width=max(2, lado // 300))
    return im


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    for n, w, h, prop, c0, c1 in IMAGENES:
        ruta = DESTINO / f"prueba{n}.png"
        imagen(n, w, h, prop, c0, c1).save(ruta, optimize=True)
        print(ruta.relative_to(DESTINO.parent.parent.parent), f"{w}×{h}")


if __name__ == "__main__":
    main()
