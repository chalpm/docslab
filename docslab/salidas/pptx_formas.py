# SPDX-License-Identifier: AGPL-3.0-only
"""PowerPoint editable de verdad: cada cosa del PDF como un objeto de PowerPoint.

Lo que se dibuja en cada página del PDF se lee con PyMuPDF, en el orden en que se pinta:

* trazos y rellenos (cajas, bandas, líneas, flechas, círculos…) → formas de PowerPoint con
  geometría propia (líneas rectas y curvas de Bézier tal cual), su relleno, su borde y su
  transparencia; un rectángulo simple sale como rectángulo y uno de esquinas redondeadas
  como «rectángulo redondeado», para que se puedan cambiar como cualquier forma;
* imágenes → imágenes sueltas, con el archivo original (y su recorte, si lo tiene);
* lo que PowerPoint no sabe dibujar igual (degradados, máscaras, imágenes giradas) y las
  piezas que ya decidía dejar como imagen el modo anterior (fórmulas, letras de figuras
  vectoriales) → una imagen por pieza, en su sitio, no una imagen de fondo para todo;
* el texto lo pone ``powerpoint.py`` como hasta ahora, en cuadros de texto, y aquí solo se
  decide su lugar en el orden de dibujo.

Todo se apila en el mismo orden que en el PDF, así que una capa de delante tapa lo que tapaba.
"""
from __future__ import annotations

import io
import math

EMU_PT = 12700
MAX_ITEMS_FORMA = 4000            # una forma con más tramos que esto se pone como imagen
TIPOS_DIBUJO = {"fill-path", "stroke-path"}
TIPOS_TEXTO = {"fill-text", "stroke-text", "ignore-text"}
TIPOS_IMAGEN = {"fill-image"}
TIPOS_SIN_PINTURA = {"clip-path", "clip-stroke-path", "clip-text", "clip-stroke-text", "ignore-text",
                     "end-clip", "begin-group", "end-group", "begin-layer", "end-layer"}


def disponible() -> bool:
    import importlib.util
    return importlib.util.find_spec("pymupdf") is not None


# ------------------------------------------------------------------------- lectura del PDF
def _caja(r) -> tuple[float, float, float, float]:
    return (float(r[0]), float(r[1]), float(r[2]), float(r[3]))


def _area(c) -> float:
    return max(0.0, c[2] - c[0]) * max(0.0, c[3] - c[1])


def _dentro(c, z, holgura: float = 0.5) -> bool:
    """¿La caja c cae (casi) entera dentro de z?"""
    return c[0] >= z[0] - holgura and c[1] >= z[1] - holgura and c[2] <= z[2] + holgura and c[3] <= z[3] + holgura


def _centro_dentro(c, z, holgura: float = 1.0) -> bool:
    cx, cy = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
    return z[0] - holgura <= cx <= z[2] + holgura and z[1] - holgura <= cy <= z[3] + holgura


def piezas(pagina) -> dict:
    """Lo que hay en una página de PyMuPDF, en orden de dibujo.

    {"dibujos": [path de get_drawings con "seqno"], "imagenes": [{"xref", "caja", "visible", "z", "giro"}],
     "otros": [{"tipo", "caja", "z"}] (lo que no se convierte), "texto": [(z, caja)]}"""
    pag = _caja(pagina.rect)
    log = pagina.get_bboxlog()
    extendido = pagina.get_drawings(extended=True)
    dibujos = [d for d in extendido if d["type"] in ("f", "s", "fs")]
    # recortes («clip»): no llevan número de orden, pero van en su sitio de la lista; se guarda entre
    # qué números de orden cae cada uno, para saber a qué puede estar recortando
    recortes, ultimo, pendientes = [], -1, []
    for d in extendido:
        if d["type"] == "clip" and d.get("scissor") is not None:
            pendientes.append(_caja(d["scissor"]))
        elif d.get("seqno") is not None:
            recortes += [(ultimo, d["seqno"], s) for s in pendientes]
            pendientes, ultimo = [], d["seqno"]
    recortes += [(ultimo, 1 << 30, s) for s in pendientes]

    def visible(z: int, c: tuple) -> tuple:
        """La parte de c que se ve: dentro de la página y del recorte que más la toca."""
        c = (max(c[0], pag[0]), max(c[1], pag[1]), min(c[2], pag[2]), min(c[3], pag[3]))
        mejor, mayor = c, 0.0
        for desde, hasta, s in recortes:
            if desde < z < hasta:
                inter = (max(c[0], s[0]), max(c[1], s[1]), min(c[2], s[2]), min(c[3], s[3]))
                if _area(inter) > mayor:
                    mayor, mejor = _area(inter), inter
        return mejor

    texto = [(s["seqno"], _caja(s["bbox"])) for s in pagina.get_texttrace()]
    entradas = [(i, _caja(c)) for i, (t, c) in enumerate(log) if t in TIPOS_IMAGEN]
    infos = [i for i in pagina.get_image_info(xrefs=True) if i.get("xref")]
    # emparejar cada imagen dibujada con su imagen del PDF: primero las parejas más parecidas
    parejas = []
    for e, (z, c) in enumerate(entradas):
        for k, info in enumerate(infos):
            b = _caja(info["bbox"])
            if not (c[2] < b[0] or c[0] > b[2] or c[3] < b[1] or c[1] > b[3]):
                parejas.append((sum(abs(x - y) for x, y in zip(c, b)), e, k))
    usadas_e, usadas_k, imagenes = set(), set(), []
    for _, e, k in sorted(parejas):
        if e in usadas_e or k in usadas_k:
            continue
        usadas_e.add(e)
        usadas_k.add(k)
        z, c = entradas[e]
        info = infos[k]
        a, b, c_, d, _, _ = info["transform"]
        imagenes.append({"xref": info["xref"], "caja": _caja(info["bbox"]), "visible": visible(z, c), "z": z,
                         "giro": abs(b) > 1e-6 or abs(c_) > 1e-6 or a < 0 or d < 0})
    # las que PyMuPDF no sitúa (dentro de un grupo con transparencia, por ejemplo): por la forma
    sueltas = {x[0]: (x[2], x[3]) for x in pagina.get_images(full=True)
               if x[0] not in {i["xref"] for i in imagenes}}
    otros = []
    for e, (z, c) in enumerate(entradas):
        if e in usadas_e:
            continue
        proporcion = (c[2] - c[0]) / max(1e-6, c[3] - c[1])
        cand = [x for x, (w, h) in sueltas.items() if h and abs(w / h - proporcion) < 0.02 * proporcion]
        if cand:
            xref = cand[0]
            del sueltas[xref]
            imagenes.append({"xref": xref, "caja": c, "visible": visible(z, c), "z": z, "giro": False})
        else:
            otros.append({"tipo": "fill-image", "caja": visible(z, c), "z": z})
    for i, (t, c) in enumerate(log):
        if t in TIPOS_DIBUJO | TIPOS_TEXTO | TIPOS_IMAGEN | TIPOS_SIN_PINTURA:
            continue
        v = visible(i, _caja(c))
        if _area(v) > 0:
            otros.append({"tipo": t, "caja": v, "z": i})
    return {"dibujos": dibujos, "imagenes": imagenes, "otros": otros, "texto": texto}


def z_de_caja(caja, texto: list[tuple[int, tuple]], defecto: float) -> float:
    """El orden de dibujo del texto que cae en esa caja (el primero que se pinta)."""
    zs = [z for z, c in texto if _centro_dentro(c, caja, 0.5)]
    return min(zs) if zs else defecto


# ------------------------------------------------------------------------- formas
def _hex(rgb) -> str:
    return "".join(f"{max(0, min(255, round(float(v) * 255))):02X}" for v in rgb[:3])


def _relleno(rgb, opacidad) -> str:
    if rgb is None:
        return "<a:noFill/>"
    alfa = "" if opacidad is None or opacidad >= 0.999 else f'<a:alpha val="{int(max(0, opacidad) * 100000)}"/>'
    return f'<a:solidFill><a:srgbClr val="{_hex(rgb)}">{alfa}</a:srgbClr></a:solidFill>'


_CAP = {0: "flat", 1: "rnd", 2: "sq"}


def _borde(p: dict, esc: float) -> str:
    if p.get("type") not in ("s", "fs") or p.get("color") is None:
        return "<a:ln><a:noFill/></a:ln>"
    ancho = int(max(0.0, float(p.get("width") or 1.0)) * esc * EMU_PT)
    cap = p.get("lineCap")
    cap = cap[0] if isinstance(cap, (list, tuple)) else cap
    cap = _CAP.get(int(cap or 0), "flat")
    raya = str(p.get("dashes") or "").strip()
    discontinua = '<a:prstDash val="dash"/>' if raya and not raya.startswith("[] ") and raya not in ("[] 0", "[]") else ""
    union = {0: "<a:miter/>", 1: "<a:round/>", 2: "<a:bevel/>"}.get(int(p.get("lineJoin") or 0), "<a:miter/>")
    return (f'<a:ln w="{ancho}" cap="{cap}">{_relleno(p["color"], p.get("stroke_opacity"))}{discontinua}{union}'
            f'</a:ln>')


def _xfrm(x0, y0, x1, y1, esc) -> tuple[int, int, int, int]:
    x, y = int(round(x0 * esc * EMU_PT)), int(round(y0 * esc * EMU_PT))
    return x, y, max(1, int(round((x1 - x0) * esc * EMU_PT))), max(1, int(round((y1 - y0) * esc * EMU_PT)))


def _es_rectangulo(p) -> tuple | None:
    items = p["items"]
    if len(items) == 1 and items[0][0] == "re":
        r = items[0][1]
        return (r.x0, r.y0, r.x1, r.y1)
    if len(items) == 1 and items[0][0] == "qu":
        q = items[0][1]
        if q.is_rectangular and abs(q.ul.y - q.ur.y) < 0.01 and abs(q.ul.x - q.ll.x) < 0.01:
            r = q.rect
            return (r.x0, r.y0, r.x1, r.y1)
    return None


def _es_redondeado(p) -> tuple | None:
    """Rectángulo de esquinas redondeadas (como los de tcolorbox): 4 curvas y hasta 4 rectas."""
    items = p["items"]
    curvas = [i for i in items if i[0] == "c"]
    rectas = [i for i in items if i[0] == "l"]
    if len(curvas) != 4 or len(curvas) + len(rectas) != len(items):
        return None
    r = p["rect"]
    tol = 0.02 * max(1.0, min(r.width, r.height))
    radios = []
    for _, a, _, _, b in curvas:
        dx, dy = abs(b.x - a.x), abs(b.y - a.y)
        if dx < 0.01 or dy < 0.01 or abs(dx - dy) > 0.15 * max(dx, dy):
            return None
        radios.append((dx + dy) / 2)
        # cada curva va de un lado vertical de la caja a uno horizontal (una esquina)
        en_vertical = min(abs(a.x - r.x0), abs(a.x - r.x1), abs(b.x - r.x0), abs(b.x - r.x1)) <= tol
        en_horizontal = min(abs(a.y - r.y0), abs(a.y - r.y1), abs(b.y - r.y0), abs(b.y - r.y1)) <= tol
        if not (en_vertical and en_horizontal):
            return None
    radio = sum(radios) / 4
    if max(radios) - min(radios) > 0.2 * radio:
        return None
    return (r.x0, r.y0, r.x1, r.y1, radio)


def _geometria(p, x0, y0, esc) -> str:
    """<a:path> con los tramos del trazo (coordenadas relativas a la esquina de la forma, en EMU)."""
    def pt(q):
        return f'<a:pt x="{int(round((q.x - x0) * esc * EMU_PT))}" y="{int(round((q.y - y0) * esc * EMU_PT))}"/>'
    partes, actual = [], None
    for it in p["items"]:
        op = it[0]
        if op == "re":
            r = it[1]
            from pymupdf import Point
            esquinas = [Point(r.x0, r.y0), Point(r.x1, r.y0), Point(r.x1, r.y1), Point(r.x0, r.y1)]
            partes.append(f"<a:moveTo>{pt(esquinas[0])}</a:moveTo>" + "".join(f"<a:lnTo>{pt(e)}</a:lnTo>" for e in esquinas[1:]) + "<a:close/>")
            actual = None
            continue
        if op == "qu":
            q = it[1]
            esquinas = [q.ul, q.ur, q.lr, q.ll]
            partes.append(f"<a:moveTo>{pt(esquinas[0])}</a:moveTo>" + "".join(f"<a:lnTo>{pt(e)}</a:lnTo>" for e in esquinas[1:]) + "<a:close/>")
            actual = None
            continue
        ini = it[1]
        if actual is None or abs(actual.x - ini.x) > 1e-3 or abs(actual.y - ini.y) > 1e-3:
            partes.append(f"<a:moveTo>{pt(ini)}</a:moveTo>")
        if op == "l":
            partes.append(f"<a:lnTo>{pt(it[2])}</a:lnTo>")
            actual = it[2]
        elif op == "c":
            partes.append(f"<a:cubicBezTo>{pt(it[2])}{pt(it[3])}{pt(it[4])}</a:cubicBezTo>")
            actual = it[4]
    if p.get("closePath"):
        partes.append("<a:close/>")
    return "".join(partes)


def xml_forma(p: dict, esc: float, sid: int) -> tuple[str, tuple] | None:
    """El <p:sp> de PowerPoint para un trazo de PyMuPDF, y su caja (pt). None si no se dibuja nada."""
    relleno = p["fill"] if p.get("type") in ("f", "fs") else None
    if relleno is None and (p.get("type") not in ("s", "fs") or p.get("color") is None):
        return None
    if len(p["items"]) > MAX_ITEMS_FORMA:
        return None
    r = p["rect"]
    # un trazo sin relleno engorda la caja medio grosor (si no, una línea horizontal tendría alto 0)
    medio = (float(p.get("width") or 0) / 2) if p.get("type") in ("s", "fs") else 0.0
    caja = (r.x0 - medio, r.y0 - medio, r.x1 + medio, r.y1 + medio)
    rect, redondo = _es_rectangulo(p), _es_redondeado(p)
    if rect:
        x, y, cx, cy = _xfrm(*rect, esc)
        geom = '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        caja = rect if p.get("type") == "f" else caja
        nombre = "Rectángulo"
    elif redondo:
        x0, y0, x1, y1, radio = redondo
        x, y, cx, cy = _xfrm(x0, y0, x1, y1, esc)
        adj = int(max(0, min(50000, radio / max(1e-6, min(x1 - x0, y1 - y0)) * 100000)))
        geom = f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val {adj}"/></a:avLst></a:prstGeom>'
        caja = (x0, y0, x1, y1)
        nombre = "Rectángulo redondeado"
    else:
        x, y, cx, cy = _xfrm(r.x0, r.y0, r.x1, r.y1, esc)
        camino = _geometria(p, r.x0, r.y0, esc)
        if not camino:
            return None
        atrib = ' fill="none"' if relleno is None else ""
        geom = (f'<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/><a:rect l="0" t="0" r="r" b="b"/><a:pathLst>'
                f'<a:path w="{cx}" h="{cy}"{atrib}>{camino}</a:path></a:pathLst></a:custGeom>')
        nombre = "Forma"
    xml = (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{nombre} {sid}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
           f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>{geom}'
           f'{_relleno(relleno, p.get("fill_opacity"))}{_borde(p, esc)}</p:spPr></p:sp>')
    return xml, caja


# ------------------------------------------------------------------------- imágenes
def bytes_imagen(doc, xref: int) -> bytes:
    """El archivo de la imagen tal como va en el PDF (JPEG si lo era), o PNG con su transparencia."""
    import pymupdf
    info = doc.extract_image(xref) or {}
    smask = info.get("smask") or 0
    if not smask and info.get("ext") in ("jpeg", "jpg", "png") and (info.get("colorspace") or 3) in (1, 3):
        return info["image"]
    pix = pymupdf.Pixmap(doc, xref)
    if pix.colorspace and pix.colorspace.n >= 4:              # CMYK → RGB
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    if smask:
        try:
            mascara = pymupdf.Pixmap(doc, smask)
            if pix.alpha:
                pix = pymupdf.Pixmap(pix, 0)
            pix = pymupdf.Pixmap(pix, mascara)
        except (RuntimeError, ValueError):
            pass
    return pix.tobytes("png")


def opacidad_imagen(foto, op: float) -> None:
    """Transparencia de una imagen de PowerPoint (<a:alphaModFix>; python-pptx no la tiene)."""
    from pptx.oxml.ns import qn
    blip = foto._element.find(".//" + qn("a:blip"))
    if blip is not None:
        for viejo in blip.findall(qn("a:alphaModFix")):
            blip.remove(viejo)
        blip.insert(0, blip.makeelement(qn("a:alphaModFix"), {"amt": str(int(max(0.0, min(1.0, op)) * 100000))}))


def recorte_png(img, caja, k: float) -> bytes | None:
    """Un trozo (en pt) de la imagen renderizada de la página (k = px por pt), en PNG."""
    x0, y0, x1, y1 = (max(0, int(math.floor(caja[0] * k))), max(0, int(math.floor(caja[1] * k))),
                      min(img.size[0], int(math.ceil(caja[2] * k))), min(img.size[1], int(math.ceil(caja[3] * k))))
    if x1 - x0 < 1 or y1 - y0 < 1:
        return None
    b = io.BytesIO()
    img.crop((x0, y0, x1, y1)).save(b, "PNG", optimize=True)
    return b.getvalue()


# ------------------------------------------------------------------------- agrupar
def agrupar(diapo, elementos: list, nombre: str):
    """Mete en un grupo las formas dadas (sus elementos XML), en el sitio de la de más abajo.

    Devuelve el id del grupo (o el de la forma, si es una sola)."""
    from lxml import etree
    from pptx.oxml.ns import nsdecls, qn
    arbol = diapo.shapes._spTree
    elementos = [e for e in elementos if e.getparent() is arbol]
    if not elementos:
        return None
    if len(elementos) == 1:
        return int(elementos[0].find(".//" + qn("p:cNvPr")).get("id"))
    posiciones = [list(arbol).index(e) for e in elementos]
    x0 = y0 = 1 << 62
    x1 = y1 = -(1 << 62)
    for e in elementos:
        off = e.find(".//" + qn("a:off"))
        ext = e.find(".//" + qn("a:ext"))
        if off is None or ext is None:
            continue
        ox, oy, ex, ey = int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy"))
        x0, y0, x1, y1 = min(x0, ox), min(y0, oy), max(x1, ox + ex), max(y1, oy + ey)
    if x1 < x0:
        return None
    sid = diapo.shapes._next_shape_id
    grp = etree.fromstring(
        f'<p:grpSp {nsdecls("p", "a")}><p:nvGrpSpPr><p:cNvPr id="{sid}" name="{nombre}"/><p:cNvGrpSpPr/><p:nvPr/>'
        f'</p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="{x0}" y="{y0}"/><a:ext cx="{x1 - x0}" cy="{y1 - y0}"/>'
        f'<a:chOff x="{x0}" y="{y0}"/><a:chExt cx="{x1 - x0}" cy="{y1 - y0}"/></a:xfrm></p:grpSpPr></p:grpSp>')
    arbol.insert(min(posiciones), grp)
    for e in sorted(elementos, key=lambda e: list(arbol).index(e)):
        grp.append(e)
    return sid
