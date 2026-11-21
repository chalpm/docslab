# SPDX-License-Identifier: AGPL-3.0-only
"""Exportar el documento a PowerPoint (.pptx).

Dos modos:

* «editable»: cada página es una diapositiva del tamaño de la página. Cada línea de
  texto va como un cuadro de texto, en su sitio, con su tamaño, color, negrita y
  cursiva. Desde 1.9.0, con PyMuPDF, todo lo demás también es un objeto de PowerPoint
  (``pptx_formas.py``): cajas, bandas, líneas y flechas como formas; cada imagen por
  separado; y, como imagen pero una por pieza, solo lo que no se puede reconstruir
  (fórmulas, letras de figuras vectoriales, degradados). Sin PyMuPDF se hace como
  antes: el texto encima de una imagen de fondo con todo lo demás.
  Las animaciones de entrada y las transiciones del modelo se aplican aquí
  (``animaciones.py``).
* «imagen»: cada página es una imagen del póster entero. Se ve exactamente igual
  que el PDF, pero no se puede editar (sí lleva las transiciones).

PowerPoint no admite diapositivas de más de 56 pulgadas (142,24 cm): si el póster es
más grande, se reduce entero en la misma proporción (y se avisa).
"""
from __future__ import annotations

import html
import io
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from . import animaciones as AN, compilador, pptx_formas as PF, revision

EMU_PT = 12700
MAX_PT = 56 * 72                      # lado máximo de una diapositiva de PowerPoint
MAX_PX = 11000                        # lado máximo de las imágenes de fondo
MODOS = ("editable", "imagen")

# tipografías del PDF → la que se pide en PowerPoint (la que suele estar instalada)
_FAMILIAS = [
    (r"NimbusSan|Helvetica|TeXGyreHeros|Arial|LiberationSans|FreeSans", "Arial"),
    (r"NimbusRom|Times|TeXGyreTermes|LiberationSerif|FreeSerif|^CM[RBT]|^LM(Roman|Serif)|^SFRM", "Times New Roman"),
    (r"Palladio|Palatino|TeXGyrePagella|^URWPalladio|mathpazo", "Palatino Linotype"),
    (r"NimbusMon|Courier|TeXGyreCursor|^CMTT|^LMMono|FreeMono", "Courier New"),
    (r"Bookman|TeXGyreBonum", "Bookman Old Style"),
    (r"Charter|XCharter", "Georgia"),
    (r"URWGothic|AvantGarde|TeXGyreAdventor", "Century Gothic"),
    (r"DejaVuSansMono", "DejaVu Sans Mono"),
    (r"DejaVuSerif", "DejaVu Serif"),
    (r"DejaVuSans", "DejaVu Sans"),
]
# fórmulas y símbolos: mejor como imagen
_MATEMATICAS = re.compile(r"^(CMMI|CMSY|CMEX|CMMIB|CMBSY|MSAM|MSBM|EUFM|EUSM|EURM|RSFS|STMARY|WASY|LMMath|"
                          r"LatinModernMath|STIX|XITS|Symbol|Mathpazo|PazoMath|txsy|txex|txmi|pxsy|pxex|pxmi)",
                          re.I)
_CM = re.compile(r"^(CM[A-Z]|LM(Roman|Sans|Math)|SFRM|SFBX|SFTI|EC[A-Z][A-Z])", re.I)
_RE_PAGINA = re.compile(r'<page number="(\d+)"[^>]*?height="([\d.]+)" width="([\d.]+)"')
_RE_FUENTE = re.compile(r'<fontspec id="(\d+)" size="(-?[\d.]+)" family="([^"]*)" color="#([0-9a-fA-F]{6})"')
_RE_TEXTO = re.compile(r'<text top="(-?[\d.]+)" left="(-?[\d.]+)" width="(-?[\d.]+)" height="(-?[\d.]+)" '
                       r'font="(\d+)">(.*?)</text>', re.S)
ZOOM = 4


class ErrorPowerPoint(ValueError):
    pass


def disponible() -> dict:
    """Qué se puede hacer en este equipo."""
    import importlib.util
    hay_pptx = importlib.util.find_spec("pptx") is not None
    gs = bool(compilador.ghostscript())
    nativo = PF.disponible()
    texto = bool(shutil.which("pdftohtml"))
    return {"pptx": hay_pptx, "imagen": hay_pptx and (gs or bool(shutil.which("pdftoppm"))),
            "editable": hay_pptx and texto and (gs or nativo),
            "todo_editable": hay_pptx and texto and nativo}


# ---------------------------------------------------------------------- tipografías
def familia_ppt(fam: str) -> str:
    """Nombre de tipografía para PowerPoint a partir del del PDF."""
    f = re.sub(r"^[A-Z]{6}\+", "", fam or "")
    for patron, nombre in _FAMILIAS:
        if re.search(patron, f, re.I):
            return nombre
    base = re.split(r"[-,]", f)[0]
    base = re.sub(r"(Regular|Regu|Bold|Medium|Light|Semibold|SemiBold|Italic|Ital|Oblique|Obli)$", "", base)
    nombre = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", base).strip()
    return nombre or "Arial"


def _estilo_de_familia(fam: str) -> tuple[bool, bool]:
    f = fam.lower()
    return ("bold" in f or "-bol" in f or "semibold" in f or "black" in f,
            "italic" in f or "ital" in f or "oblique" in f or "obli" in f)


# ---------------------------------------------------------------------- texto del PDF
def lineas_pdf(pdf: Path) -> dict[int, dict]:
    """Por página: {ancho, alto (pt), lineas: [{x0, y0, x1, y1 (pt, desde arriba a la
    izquierda), tam (pt), familia, color, trozos: [(texto, negrita, cursiva)]}]}."""
    exe = shutil.which("pdftohtml")
    if not exe:
        raise ErrorPowerPoint("Hace falta pdftohtml (Poppler) para sacar el texto del PDF.")
    r = subprocess.run([exe, "-xml", "-i", "-stdout", "-q", "-zoom", str(ZOOM), "-nodrm", str(pdf)],
                       capture_output=True, timeout=180, stdin=subprocess.DEVNULL)
    s = r.stdout.decode("utf-8", "replace")
    info = revision.info_pdf(pdf) or {"tamanos": []}
    # pdftohtml quita el estilo del nombre («NimbusSanL-BoldItal» → «NimbusSanL»): el
    # nombre completo está en pdffonts, con el mismo prefijo del subconjunto
    completos = {}
    if shutil.which("pdffonts"):
        rf = subprocess.run(["pdffonts", str(pdf)], capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
        for x in rf.stdout.decode("utf-8", "replace").splitlines()[2:]:
            nombre = x.split(" ")[0]
            if "+" in nombre:
                completos[nombre.split("+")[0]] = nombre.split("+", 1)[1]
    fuentes = {}
    for mo in _RE_FUENTE.finditer(s):
        col = mo.group(4)
        fuentes[mo.group(1)] = (float(mo.group(2)), mo.group(3), tuple(int(col[i:i + 2], 16) for i in (0, 2, 4)))
    paginas = [(mo.start(), int(mo.group(1)), float(mo.group(2)), float(mo.group(3))) for mo in _RE_PAGINA.finditer(s)]
    salida = {}
    for i, (ini, num, alto_px, ancho_px) in enumerate(paginas):
        tams = info["tamanos"]
        w_pt, h_pt = tams[min(num - 1, len(tams) - 1)] if tams else (ancho_px / 3, alto_px / 3)
        k = ancho_px / w_pt if w_pt else 1.0            # px de pdftohtml por punto
        fin = paginas[i + 1][0] if i + 1 < len(paginas) else len(s)
        lineas = []
        for mo in _RE_TEXTO.finditer(s, ini, fin):
            f = fuentes.get(mo.group(5))
            if not f or f[0] <= 0:
                continue
            top, left, w, h = (float(mo.group(j)) / k for j in (1, 2, 3, 4))
            trozos = []
            prefijo = f[1].split("+")[0] if "+" in f[1] else ""
            fam_negrita, fam_cursiva = _estilo_de_familia(completos.get(prefijo) or f[1])
            for parte in re.finditer(r"((?:<[bi]>)*)([^<]*)((?:</[bi]>)*)", mo.group(6)):
                texto = html.unescape(parte.group(2))
                if texto:
                    etiquetas = parte.group(1) + parte.group(3)
                    trozos.append((texto, "b>" in etiquetas or fam_negrita, "i>" in etiquetas or fam_cursiva))
            if not trozos or not "".join(t for t, _, _ in trozos).strip():
                continue
            lineas.append({"x0": left, "y0": top, "x1": left + w, "y1": top + h, "tam": f[0] / k,
                           "familia": re.sub(r"^[A-Z]{6}\+", "", f[1]), "color": f[2], "trozos": trozos,
                           "ancho_cero": w <= 0.01})
        salida[num] = {"ancho": w_pt, "alto": h_pt, "lineas": lineas}
    return salida


_RE_PALABRA = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')


def palabras_pdf(pdf: Path) -> dict[int, list[tuple]]:
    """Por página, cada palabra con su caja (pt): sirve para ver los huecos dentro de una línea."""
    if not shutil.which("pdftotext"):
        return {}
    r = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, timeout=180, stdin=subprocess.DEVNULL)
    s = r.stdout.decode("utf-8", "replace")
    salida, n = {}, 0
    for trozo in s.split("<page ")[1:]:
        n += 1
        salida[n] = [(float(a), float(b), float(c), float(d), html.unescape(t))
                     for a, b, c, d, t in _RE_PALABRA.findall(trozo)]
    return salida


def partir_lineas(lineas: list[dict], palabras: list[tuple]) -> list[dict]:
    """pdftohtml junta en una línea trozos separados por un hueco grande (el número de
    una caja y su título, por ejemplo) y PowerPoint los pondría a un espacio normal:
    se parten donde el hueco entre palabras pasa de media letra."""
    salida = []
    for ln in lineas:
        cy0, cy1 = ln["y0"], ln["y1"]
        ws = sorted((w for w in palabras if cy0 - 1 <= (w[1] + w[3]) / 2 <= cy1 + 1
                     and ln["x0"] - 1 <= (w[0] + w[2]) / 2 <= ln["x1"] + 1), key=lambda w: w[0])
        letras = [(c, b, i) for t, b, i in ln["trozos"] for c in t]
        while letras and letras[0][0].isspace():
            letras.pop(0)
        while letras and letras[-1][0].isspace():
            letras.pop()
        fichas, actual = [], []
        for x in letras:
            if x[0].isspace():
                if actual:
                    fichas.append(actual)
                    actual = []
            else:
                actual.append(x)
        if actual:
            fichas.append(actual)
        if ln["ancho_cero"] or len(ws) != len(fichas) or len(ws) < 2 or \
                any("".join(c for c, _, _ in f) != w[4] for f, w in zip(fichas, ws)):
            salida.append(ln)
            continue
        cortes = [k for k in range(1, len(ws)) if ws[k][0] - ws[k - 1][2] > 0.55 * ln["tam"]]
        if not cortes:
            salida.append(ln)
            continue
        for a, b in zip([0] + cortes, cortes + [len(ws)]):
            chars = []
            for k in range(a, b):
                if chars:
                    chars.append((" ",) + chars[-1][1:])
                chars.extend(fichas[k])
            trozos = []
            for c, bb, ii in chars:
                if trozos and trozos[-1][1] == bb and trozos[-1][2] == ii:
                    trozos[-1] = (trozos[-1][0] + c, bb, ii)
                else:
                    trozos.append((c, bb, ii))
            salida.append(dict(ln, x0=ws[a][0], x1=ws[b - 1][2], trozos=trozos))
    return salida


def unir_lineas(lineas: list[dict]) -> list[dict]:
    """Junta los trozos de una misma línea con el mismo tamaño (una palabra en negrita,
    en cursiva…) en un solo cuadro de texto, con un espacio si lo había."""
    orden = sorted(lineas, key=lambda x: (round(x["y0"], 1), x["x0"]))

    def algo_en_medio(a, b):            # p. ej. un superíndice entre dos trozos
        return any(o is not a and o is not b and o["x0"] >= a["x1"] - 0.5 and o["x1"] <= b["x0"] + 0.5
                   and o["y0"] < b["y1"] and o["y1"] > b["y0"] for o in lineas)

    salida: list[dict] = []
    for ln in orden:
        prev = salida[-1] if salida else None
        if (prev and not ln["ancho_cero"] and not prev["ancho_cero"] and abs(prev["y0"] - ln["y0"]) < 0.15 * ln["tam"]
                and abs(prev["tam"] - ln["tam"]) < 0.05 * ln["tam"]
                and familia_ppt(prev["familia"]) == familia_ppt(ln["familia"]) and prev["color"] == ln["color"]
                and -0.1 * ln["tam"] <= ln["x0"] - prev["x1"] <= 0.3 * ln["tam"]
                and not algo_en_medio(prev["ultimo"], ln)):
            hueco = ln["x0"] - prev["x1"]
            trozos = list(ln["trozos"])
            if hueco > 0.12 * ln["tam"] and not prev["trozos"][-1][0].endswith(" "):
                t, b, i = trozos[0]
                trozos[0] = (" " + t, b, i)
            prev["trozos"] = prev["trozos"] + trozos
            prev["x1"] = max(prev["x1"], ln["x1"])
            prev["y1"] = max(prev["y1"], ln["y1"])
            prev["ultimo"] = ln
            continue
        salida.append(dict(ln, ultimo=ln))
    for x in salida:
        x.pop("ultimo", None)
    return salida


# ---------------------------------------------------------------------- zonas del modelo
def _zona_frac(c: dict, papel: dict) -> dict:
    return {"pagina": int(c.get("pagina") or 1), "x0": c["x0"] / papel["ancho"], "y0": c["y0"] / papel["alto"],
            "x1": c["x1"] / papel["ancho"], "y1": c["y1"] / papel["alto"]}


def zonas_modelo(modelo: dict | None, posiciones: dict | None) -> tuple[list[dict], list[dict], list[dict]]:
    """(figuras, girados, tapan): zonas (fracciones de la página) de los elementos con
    imagen, de los textos girados de las capas (con su giro, opacidad y texto) y de lo
    que, en las capas de delante, tapa el contenido (imágenes y cajas con fondo)."""
    if not modelo or not posiciones or not posiciones.get("papel"):
        return [], [], []
    papel, cajas = posiciones["papel"], posiciones.get("cajas") or {}
    nodos = revision.nodos_modelo(modelo)
    figuras = [_zona_frac(cajas[i], papel) for i, n in nodos.items()
               if n.get("tipo") == "elemento" and n.get("grupo") == "imagen" and i in cajas]
    girados, tapan = [], []
    for capa in modelo.get("capas", []):
        if capa.get("visible") is False:
            continue
        for it in capa.get("elementos", []):
            if it.get("visible") is False or it["id"] not in cajas:
                continue
            try:
                giro = float(it.get("rotacion") or 0)
            except (TypeError, ValueError):
                giro = 0.0
            try:
                op = float(it.get("opacidad", 1)) * float(capa.get("opacidad", 1))
                z_capa = float(capa.get("z", 1))
            except (TypeError, ValueError):
                op, z_capa = 1.0, 1.0
            z = _zona_frac(cajas[it["id"]], papel)
            z.update({"giro": giro, "opacidad": max(0.0, min(1.0, op)), "texto": _letras(it.get("texto"))})
            if it.get("tipo") == "texto" and abs(giro) >= 0.5:
                girados.append(z)
            elif z_capa > 0 and op >= 0.5 and (it.get("tipo") == "imagen" or str(it.get("fondo") or "").strip()):
                tapan.append(z)
    return figuras, girados, tapan


def _letras(t) -> str:
    """Solo letras y números, en minúsculas: para reconocer un texto aunque cambie el formato."""
    return re.sub(r"[\W_]+", "", str(t or "").lower())


def _texto(ln: dict) -> str:
    return "".join(t for t, _, _ in ln["trozos"])


def _dentro(ln: dict, z: dict, w: float, h: float) -> bool:
    cx, cy = (ln["x0"] + ln["x1"]) / 2 / w, (ln["y0"] + ln["y1"]) / 2 / h
    return z["x0"] - 0.002 <= cx <= z["x1"] + 0.002 and z["y0"] - 0.002 <= cy <= z["y1"] + 0.002


def _toca(ln: dict, z: dict, w: float, h: float) -> bool:
    return ln["x0"] / w < z["x1"] and ln["x1"] / w > z["x0"] and ln["y0"] / h < z["y1"] and ln["y1"] / h > z["y0"]


def clasificar(pagina: dict, num: int, figuras: list[dict], girados: list[dict], con_modelo: bool,
               tapan: list[dict] | None = None) -> dict:
    """Separa las líneas en: editables (cuadros de texto), de imagen (se quedan pintadas)
    y giradas (cuadros de texto girados). También dice qué zonas hay que pintar enteras."""
    w, h = pagina["ancho"], pagina["alto"]
    figs = [z for z in figuras if z["pagina"] == num]
    girs = [z for z in girados if z["pagina"] == num]
    lineas = pagina["lineas"]
    # las tipografías del póster: las de lo que no está dentro de una figura
    if con_modelo:
        del_poster = {ln["familia"] for ln in lineas if not any(_dentro(ln, z, w, h) for z in figs)}
    else:
        del_poster = None
    # Computer Modern: si el póster no lo usa para el texto, es de las fórmulas
    cuenta: dict[str, int] = {}
    for ln in lineas:
        cuenta[ln["familia"]] = cuenta.get(ln["familia"], 0) + len(_texto(ln))
    principal = max(cuenta, key=cuenta.get) if cuenta else ""
    formulas_cm = not _CM.match(principal)
    editables, imagen, giradas = [], [], {}
    for ln in lineas:
        # el texto de un elemento girado: dentro de su caja y con sus mismas letras
        g = next((i for i, z in enumerate(girs) if _dentro(ln, z, w, h) and _letras(_texto(ln))
                  and _letras(_texto(ln)) in z["texto"]), None)
        if g is not None:
            giradas.setdefault(g, []).append(ln)
            continue
        letras = _letras(_texto(ln))
        if any(_toca(ln, z, w, h) and not (letras and letras in z["texto"])
               for z in (tapan or []) if z["pagina"] == num):
            imagen.append(ln)            # queda debajo de algo de una capa de delante: como en el PDF
            continue
        if ln["ancho_cero"] or _MATEMATICAS.match(ln["familia"]) or (formulas_cm and _CM.match(ln["familia"])):
            imagen.append(ln)
            continue
        if del_poster is not None and ln["familia"] not in del_poster and any(_dentro(ln, z, w, h) for z in figs):
            imagen.append(ln)
            continue
        editables.append(ln)
    # figuras con letras que se quedan en la imagen: se pintan enteras
    zonas = [z for z in figs if any(_dentro(ln, z, w, h) for ln in imagen)]
    return {"editables": unir_lineas(editables), "imagen": imagen, "zonas": zonas,
            "giradas": [(girs[g], ls) for g, ls in giradas.items()]}


# ---------------------------------------------------------------------- imágenes
def _resolucion(w_pt: float, h_pt: float, ppp: int) -> int:
    return max(36, min(ppp, int(MAX_PX * 72 / max(w_pt, h_pt))))


_LIMITE_PIL = threading.Lock()


def abrir_render(ruta: Path, pixeles: int):
    """Abre en RGB una imagen que generó DocsLab a partir del PDF (no la subió nadie). Admite su tamaño,
    que se conoce de antemano, subiendo el límite de Pillow solo mientras se abre; nunca lo desactiva."""
    from PIL import Image
    with _LIMITE_PIL:
        antes = Image.MAX_IMAGE_PIXELS
        if antes is not None and pixeles > antes:
            Image.MAX_IMAGE_PIXELS = int(pixeles * 1.05) + 1
        try:
            with Image.open(ruta, formats=["PNG"]) as im:
                return im.convert("RGB")
        finally:
            Image.MAX_IMAGE_PIXELS = antes


def renderizar(pdf: Path, pagina: int, ppp: int, sin_texto: bool, destino: Path) -> Path:
    gs = compilador.ghostscript()
    if gs:
        orden = [gs, "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m", f"-r{ppp}",
                 f"-dFirstPage={pagina}", f"-dLastPage={pagina}", "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
                 f"-sOutputFile={destino}"]
        if sin_texto:
            orden.append("-dFILTERTEXT")
        subprocess.run(orden + [str(pdf)], capture_output=True, timeout=600, stdin=subprocess.DEVNULL)
    elif not sin_texto and shutil.which("pdftoppm"):
        base = destino.with_suffix("")
        subprocess.run(["pdftoppm", "-png", "-r", str(ppp), "-f", str(pagina), "-l", str(pagina), "-singlefile",
                        str(pdf), str(base)], capture_output=True, timeout=600)
    if not destino.exists():
        raise ErrorPowerPoint("No se pudo convertir el PDF en imagen (hace falta Ghostscript o Poppler).")
    return destino


def _caja_px(ln: dict, k: float, margen_x: float, margen_y: float, tam_img: tuple[int, int]) -> tuple[int, int, int, int]:
    x0 = max(0, int((ln["x0"] - margen_x) * k))
    y0 = max(0, int((ln["y0"] - margen_y) * k))
    x1 = min(tam_img[0], int((max(ln["x1"], ln["x0"] + 0.5 * ln["tam"]) + margen_x) * k) + 1)
    y1 = min(tam_img[1], int((ln["y1"] + margen_y) * k) + 1)
    return x0, y0, x1, y1


def fondo(lleno, sin_texto, clases: dict, w_pt: float, h_pt: float):
    """La imagen de fondo: el póster sin texto, con lo que se queda pintado."""
    k = lleno.size[0] / w_pt
    img = sin_texto.copy()
    for z in clases["zonas"]:
        caja = (int(z["x0"] * lleno.size[0]), int(z["y0"] * lleno.size[1]),
                int(z["x1"] * lleno.size[0]) + 1, int(z["y1"] * lleno.size[1]) + 1)
        img.paste(lleno.crop(caja), caja[:2])
    grupos = grupos_imagen(clases)
    pegadas = []
    for g in grupos:
        caja = (max(0, int(g[0] * k)), max(0, int(g[1] * k)), min(lleno.size[0], int(g[2] * k) + 1),
                min(lleno.size[1], int(g[3] * k) + 1))
        if caja[2] > caja[0] and caja[3] > caja[1]:
            img.paste(lleno.crop(caja), caja[:2])
            pegadas.append(caja)

    def se_cruzan(a, b):
        return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]
    # donde se ha pegado el póster con letras, el texto que va encima como cuadro de
    # texto se quita de la imagen (si no, se vería dos veces)
    for ln in clases["editables"]:
        caja = _caja_px(ln, k, 0.05 * ln["tam"], 0.08 * ln["tam"], lleno.size)
        if any(_dentro(ln, z, w_pt, h_pt) for z in clases["zonas"]) or any(se_cruzan(caja, c) for c in pegadas):
            img.paste(sin_texto.crop(caja), caja[:2])
    return img


def grupos_imagen(clases: dict) -> list[list[float]]:
    """Las líneas que se quedan pintadas, agrupadas (una fórmula entera, con sus símbolos
    grandes que sobresalen de la caja que da pdftohtml): cajas en pt."""
    grupos = []
    for ln in clases["imagen"]:
        mx, my = (0.3, 0.6) if _MATEMATICAS.match(ln["familia"]) or _CM.match(ln["familia"]) else (0.1, 0.15)
        grupos.append([ln["x0"] - mx * ln["tam"], ln["y0"] - my * ln["tam"],
                       max(ln["x1"], ln["x0"] + 0.5 * ln["tam"]) + mx * ln["tam"], ln["y1"] + my * ln["tam"]])
    unidos = True
    while unidos:
        unidos = False
        for i in range(len(grupos)):
            for j in range(i + 1, len(grupos)):
                a, b = grupos[i], grupos[j]
                if a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]:
                    grupos[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    del grupos[j]
                    unidos = True
                    break
            if unidos:
                break
    return grupos


# ---------------------------------------------------------------------- PowerPoint
def _rgb(c):
    from pptx.dml.color import RGBColor
    return RGBColor(*c)


def _cuadro(diapo, ln: dict, esc: float, giro: float = 0.0, opacidad: float = 1.0, texto: list | None = None):
    from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
    from pptx.util import Emu, Pt
    tam = ln["tam"]
    ancho = (ln["x1"] - ln["x0"]) * 1.06 + 0.35 * tam      # un poco de holgura: la letra de PowerPoint puede ser algo más ancha
    alto = max(ln["y1"] - ln["y0"], 1.2 * tam)
    x, y = ln["x0"], ln["y0"] - _subir(ln) * tam
    if giro:
        ancho, alto = ln["ancho_girado"], ln["alto_girado"]
        x, y = ln["cx"] - ancho / 2, ln["cy"] - alto / 2
    caja = diapo.shapes.add_textbox(Emu(int(x * esc * EMU_PT)), Emu(int(y * esc * EMU_PT)),
                                    Emu(int(ancho * esc * EMU_PT)), Emu(int(alto * esc * EMU_PT)))
    if giro:
        caja.rotation = -giro                 # TikZ gira al revés que PowerPoint
    tf = caja.text_frame
    tf.word_wrap = False
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE if giro else MSO_ANCHOR.TOP
    filas = texto or [ln["trozos"]]
    for n, trozos in enumerate(filas):
        p = tf.paragraphs[0] if n == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER if giro else PP_ALIGN.LEFT
        p.line_spacing = 1.0
        for t, negrita, cursiva in trozos:
            r = p.add_run()
            r.text = t
            f = r.font
            f.size = Pt(max(1.0, round(tam * esc, 1)))
            f.name = familia_ppt(ln["familia"])
            f.bold = negrita
            f.italic = cursiva
            f.color.rgb = _rgb(ln["color"])
            if opacidad < 0.999:
                _transparencia(f, opacidad)
    return caja


# Dónde queda la línea de base bajo el borde de arriba del cuadro, en tamaños de letra
# (PowerPoint y LibreOffice con interlineado sencillo; medido con Arial)
_BASE_PPT = {"Arial": 1.0, "Times New Roman": 0.98, "Courier New": 0.92, "Georgia": 1.0,
             "Palatino Linotype": 1.12, "Bookman Old Style": 1.0, "Century Gothic": 1.1}
_DESCENSO_PDF = 0.22      # parte de la caja de pdftohtml que queda bajo la línea de base


def _subir(ln: dict) -> float:
    """Cuánto subir el cuadro (en tamaños de letra) para que la línea de base coincida."""
    if not ln["tam"]:
        return 0.0
    ascenso_pdf = (ln["y1"] - ln["y0"]) / ln["tam"] - _DESCENSO_PDF
    return max(-0.2, min(0.5, _BASE_PPT.get(familia_ppt(ln["familia"]), 1.0) - ascenso_pdf))


def _transparencia(fuente, opacidad: float):
    """El color del texto con transparencia (python-pptx no lo tiene: se pone en el XML)."""
    from pptx.oxml.ns import qn
    rpr = fuente._rPr
    solido = rpr.find(qn("a:solidFill"))
    if solido is None or not len(solido):
        return
    color = solido[0]
    for a in color.findall(qn("a:alpha")):
        color.remove(a)
    alfa = color.makeelement(qn("a:alpha"), {"val": str(int(round(opacidad * 100000)))})
    color.append(alfa)


def _girada(z: dict, lineas: list[dict], w: float, h: float) -> dict:
    """Un cuadro girado a partir de la caja (sin girar) que ocupan sus líneas en el PDF."""
    import math
    x0, y0 = min(l["x0"] for l in lineas), min(l["y0"] for l in lineas)
    x1, y1 = max(l["x1"] for l in lineas), max(l["y1"] for l in lineas)
    tam = max(l["tam"] for l in lineas)
    th = math.radians(abs(z["giro"]) % 180)
    c, s = abs(math.cos(th)), abs(math.sin(th))
    alto_texto = 1.2 * tam * len(lineas)
    W, H = x1 - x0, y1 - y0
    ancho = (W - alto_texto * s) / c if c > 0.2 else (H - alto_texto * c) / max(s, 0.2)
    ancho = max(ancho, tam) * 1.08
    principal = max(lineas, key=lambda l: l["tam"])
    # el centro: el de la caja del elemento girado en el modelo (pdftohtml parte el texto girado en
    # trozos sueltos, y el centro de esos trozos puede quedar lejos)
    if all(k in z for k in ("x0", "y0", "x1", "y1")):
        cx, cy = (z["x0"] + z["x1"]) / 2 * w, (z["y0"] + z["y1"]) / 2 * h
    else:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return dict(principal, cx=cx, cy=cy, ancho_girado=ancho, alto_girado=alto_texto * 1.1)


def exportar(pdf: Path, destino: Path, modo: str = "editable", modelo: dict | None = None,
             posiciones: dict | None = None, ppp: int = 150, titulo: str = "", informar=None) -> dict:
    """Hace el .pptx. Devuelve {diapositivas, cuadros, escala, avisos}."""
    try:
        from pptx import Presentation
        from pptx.util import Emu
    except ImportError as exc:
        raise ErrorPowerPoint("Falta el paquete de Python «python-pptx»: instálalo en el entorno de DocsLab "
                              "(pip install python-pptx).") from exc
    modo = modo if modo in MODOS else "editable"
    nativo = modo == "editable" and PF.disponible()
    if modo == "editable" and not nativo and not compilador.ghostscript():
        raise ErrorPowerPoint("Para el texto editable hace falta PyMuPDF o Ghostscript (gs). Sin ellos se puede "
                              "exportar como imagen.")
    info = revision.info_pdf(pdf)
    if not info:
        raise ErrorPowerPoint("No se pudo leer el PDF del póster (hace falta Poppler).")
    paginas = info["paginas"]
    w_pt, h_pt = info["tamanos"][0]
    esc = min(1.0, MAX_PT / max(w_pt, h_pt))
    avisos = []
    if esc < 1:
        avisos.append(f"El póster es más grande que lo máximo de PowerPoint (142 cm): va reducido al "
                      f"{round(esc * 100)} %, con la letra en proporción. Al imprimir, amplíalo al tamaño real.")
    lineas = lineas_pdf(pdf) if modo == "editable" else {}
    palabras = palabras_pdf(pdf) if modo == "editable" else {}
    for n_pag, pag in lineas.items():
        pag["lineas"] = partir_lineas(pag["lineas"], palabras.get(n_pag, []))
    figuras, girados, tapan = zonas_modelo(modelo, posiciones) if modo == "editable" else ([], [], [])
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(int(w_pt * esc * EMU_PT)), Emu(int(h_pt * esc * EMU_PT))
    if titulo:
        prs.core_properties.title = titulo
    vacia = prs.slide_layouts[6]
    cuadros = formas = imagenes = piezas = animadas = 0
    docs = None
    if nativo:
        import pymupdf
        docs = (pymupdf.open(str(pdf)), pymupdf.open(str(pdf)))      # el segundo, para quitarle el texto editable
    with tempfile.TemporaryDirectory(prefix="pl-pptx-") as tmp:
        tmp = Path(tmp)
        for n in range(1, paginas + 1):
            pw, ph = info["tamanos"][min(n - 1, len(info["tamanos"]) - 1)]
            r = _resolucion(pw, ph, ppp)
            if informar:
                informar(f"Página {n} de {paginas}: imagen", 0.15 + 0.75 * (n - 1) / paginas)
            transicion = AN.xml_transicion(AN.transicion_de_pagina(modelo, n, posiciones))
            if nativo:
                pag = lineas.get(n) or {"ancho": pw, "alto": ph, "lineas": []}
                clases = clasificar(pag, n, figuras, girados, modelo is not None, tapan)
                diapo = prs.slides.add_slide(vacia)
                cuenta = _pagina_nativa(diapo, docs, n, clases, pw, ph, r, esc, modelo, posiciones)
                cuadros += cuenta["cuadros"]
                formas += cuenta["formas"]
                imagenes += cuenta["imagenes"]
                piezas += cuenta["piezas"]
                animadas += cuenta["animadas"]
                AN.poner_en_diapositiva(diapo, transicion, cuenta["timing"])
                continue
            px = int(pw / 72 * r + 2) * int(ph / 72 * r + 2)
            lleno = abrir_render(renderizar(pdf, n, r, False, tmp / f"lleno-{n}.png"), px)
            if modo == "editable":
                sin = abrir_render(renderizar(pdf, n, r, True, tmp / f"sin-{n}.png"), px)
                pag = lineas.get(n) or {"ancho": pw, "alto": ph, "lineas": []}
                clases = clasificar(pag, n, figuras, girados, modelo is not None, tapan)
                img = fondo(lleno, sin, clases, pw, ph)
            else:
                clases, img = None, lleno
            b = io.BytesIO()
            img.save(b, "JPEG", quality=90, optimize=True, subsampling=0)
            b.seek(0)
            diapo = prs.slides.add_slide(vacia)
            diapo.shapes.add_picture(b, 0, 0, prs.slide_width, prs.slide_height)
            if clases:
                if informar:
                    informar(f"Página {n} de {paginas}: texto", 0.15 + 0.75 * (n - 0.4) / paginas)
                for ln in clases["editables"]:
                    _cuadro(diapo, ln, esc)
                    cuadros += 1
                for z, ls in clases["giradas"]:
                    ls = sorted(ls, key=lambda l: l["y0"])
                    g = _girada(z, ls, pw, ph)
                    _cuadro(diapo, g, esc, giro=z["giro"], opacidad=z["opacidad"], texto=[l["trozos"] for l in ls])
                    cuadros += 1
            AN.poner_en_diapositiva(diapo, transicion, "")
            lleno.close()
    if docs:
        for d in docs:
            d.close()
    if modo == "editable" and not nativo:
        avisos.append("Sin PyMuPDF solo el texto es editable: lo demás va en una imagen de fondo "
                      "(instala pymupdf para que también lo sean las imágenes y las formas).")
    prs.save(str(destino))
    return {"diapositivas": paginas, "cuadros": cuadros, "formas": formas, "imagenes": imagenes, "piezas": piezas,
            "animadas": animadas, "escala": round(esc, 4), "avisos": avisos, "modo": modo,
            "todo_editable": bool(nativo)}


def _caja_linea(ln: dict) -> tuple[float, float, float, float]:
    return (ln["x0"], ln["y0"], ln["x1"], ln["y1"])


def _pagina_nativa(diapo, docs, n: int, clases: dict, pw: float, ph: float, r: int, esc: float,
                   modelo: dict | None, posiciones: dict | None) -> dict:
    """Una diapositiva con cada cosa de la página como objeto de PowerPoint (ver pptx_formas)."""
    import pymupdf
    from lxml import etree
    from pptx.oxml.ns import nsdecls, qn
    from pptx.util import Emu
    pagina = docs[0][n - 1]
    pz = PF.piezas(pagina)
    # la página sin el texto que va en cuadros de texto: de ahí salen las piezas que van como imagen
    limpia = docs[1][n - 1]
    editables = list(clases["editables"]) + [l for _, ls in clases["giradas"] for l in ls]
    for ln in editables:
        limpia.add_redact_annot(pymupdf.Rect(ln["x0"] + 0.02 * ln["tam"], ln["y0"] + 0.05 * ln["tam"],
                                             ln["x1"] - 0.02 * ln["tam"], ln["y1"] - 0.05 * ln["tam"]))
    if editables:
        limpia.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                                text=pymupdf.PDF_REDACT_TEXT_REMOVE)
    pix = limpia.get_pixmap(dpi=r, alpha=False)
    from PIL import Image
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    k = img.size[0] / pw
    zonas = [(z["x0"] * pw, z["y0"] * ph, z["x1"] * pw, z["y1"] * ph) for z in clases["zonas"]]
    lejos = 10 ** 9
    objetos = []                       # (z, orden, tipo, datos)
    z_zona = {i: lejos for i in range(len(zonas))}

    def en_zona(caja):
        for i, zona in enumerate(zonas):
            if PF._dentro(caja, zona, 1.0):
                return i
        return None
    # fondo de la página: un rectángulo que la cubre entera → color de fondo de la diapositiva
    dibujos = list(pz["dibujos"])
    if dibujos:
        p0 = dibujos[0]
        c0 = p0["rect"]
        if (PF._es_rectangulo(p0) and p0.get("fill") is not None and c0.x0 <= 1 and c0.y0 <= 1
                and c0.x1 >= pw - 1 and c0.y1 >= ph - 1 and (p0.get("fill_opacity") or 1) >= 0.999):
            from pptx.dml.color import RGBColor
            diapo.background.fill.solid()
            diapo.background.fill.fore_color.rgb = RGBColor.from_string(PF._hex(p0["fill"]))
            dibujos = dibujos[1:]
    for p in dibujos:
        caja = (p["rect"].x0, p["rect"].y0, p["rect"].x1, p["rect"].y1)
        i = en_zona(caja)
        if i is not None:
            z_zona[i] = min(z_zona[i], p["seqno"])
            continue
        objetos.append((p["seqno"], len(objetos), "forma", p))
    for im in pz["imagenes"]:
        i = en_zona(im["visible"])
        if i is not None:
            z_zona[i] = min(z_zona[i], im["z"])
            continue
        objetos.append((im["z"], len(objetos), "recorte" if im["giro"] or not im["xref"] else "imagen", im))
    for o in pz["otros"]:
        i = en_zona(o["caja"])
        if i is not None:
            z_zona[i] = min(z_zona[i], o["z"])
            continue
        objetos.append((o["z"], len(objetos), "recorte", {"visible": o["caja"]}))
    for i, zona in enumerate(zonas):
        z = min(z_zona[i], PF.z_de_caja(zona, pz["texto"], lejos))
        objetos.append((z, len(objetos), "recorte", {"visible": zona}))
    for g in grupos_imagen(clases):
        if en_zona(tuple(g)) is None:
            objetos.append((PF.z_de_caja(g, pz["texto"], lejos), len(objetos), "recorte", {"visible": tuple(g)}))
    for ln in clases["editables"]:
        objetos.append((PF.z_de_caja(_caja_linea(ln), pz["texto"], lejos), len(objetos), "texto", ln))
    for zg, ls in clases["giradas"]:
        ls = sorted(ls, key=lambda l: l["y0"])
        zt = min(PF.z_de_caja(_caja_linea(l), pz["texto"], lejos) for l in ls)
        objetos.append((zt, len(objetos), "girada", (zg, ls)))
    objetos.sort(key=lambda o: (o[0], o[1]))

    # imágenes de las capas con transparencia (en el PDF van en un grupo transparente que PyMuPDF no
    # describe): su opacidad sale del modelo
    atenuadas = []
    if modelo and posiciones and posiciones.get("papel"):
        papel, cajas = posiciones["papel"], posiciones.get("cajas") or {}
        fx, fy = pw / papel["ancho"], ph / papel["alto"]
        for capa in modelo.get("capas") or []:
            for it in capa.get("elementos") or []:
                c = cajas.get(it.get("id"))
                if it.get("tipo") != "imagen" or not c or int(c.get("pagina") or 1) != n:
                    continue
                try:
                    op = float(it.get("opacidad", 1)) * float(capa.get("opacidad", 1))
                except (TypeError, ValueError):
                    op = 1.0
                if op < 0.999:
                    atenuadas.append(((c["x0"] * fx, c["y0"] * fy, c["x1"] * fx, c["y1"] * fy), max(0.0, op)))
    arbol = diapo.shapes._spTree
    creados = []                       # (elemento XML, caja pt)
    cuenta = {"cuadros": 0, "formas": 0, "imagenes": 0, "piezas": 0, "animadas": 0, "timing": ""}

    def emu(v):
        return Emu(int(round(v * esc * EMU_PT)))
    for _, _, tipo, d in objetos:
        if tipo == "forma":
            hecho = PF.xml_forma(d, esc, diapo.shapes._next_shape_id)
            if hecho is None:
                if len(d["items"]) > PF.MAX_ITEMS_FORMA:
                    tipo, d = "recorte", {"visible": (d["rect"].x0, d["rect"].y0, d["rect"].x1, d["rect"].y1)}
                else:
                    continue
            else:
                xml, caja = hecho
                el = etree.fromstring(xml.replace("<p:sp>", f"<p:sp {nsdecls('p', 'a')}>", 1))
                arbol.append(el)
                creados.append((el, caja))
                cuenta["formas"] += 1
                continue
        if tipo == "imagen":
            try:
                datos = PF.bytes_imagen(docs[0], d["xref"])
            except (RuntimeError, ValueError):
                tipo, d = "recorte", {"visible": d["visible"]}
            else:
                c = d["caja"]
                foto = diapo.shapes.add_picture(io.BytesIO(datos), emu(c[0]), emu(c[1]), emu(c[2] - c[0]), emu(c[3] - c[1]))
                v = d["visible"]                 # lo que se ve, si la imagen va recortada en el PDF
                w, h = max(1e-6, c[2] - c[0]), max(1e-6, c[3] - c[1])
                recorte = [max(0.0, (v[0] - c[0]) / w), max(0.0, (v[1] - c[1]) / h),
                           max(0.0, (c[2] - v[2]) / w), max(0.0, (c[3] - v[3]) / h)]
                if any(x > 0.002 for x in recorte):
                    foto.crop_left, foto.crop_top, foto.crop_right, foto.crop_bottom = recorte
                    foto.left, foto.top = emu(max(v[0], c[0])), emu(max(v[1], c[1]))
                    foto.width, foto.height = emu(min(v[2], c[2]) - max(v[0], c[0])), emu(min(v[3], c[3]) - max(v[1], c[1]))
                foto.name = f"Imagen {foto.shape_id}"
                for zona, op in atenuadas:     # la misma imagen: casi la misma caja (intersección / unión)
                    inter = PF._area((max(v[0], zona[0]), max(v[1], zona[1]), min(v[2], zona[2]), min(v[3], zona[3])))
                    if inter > 0.7 * (PF._area(v) + PF._area(zona) - inter):
                        PF.opacidad_imagen(foto, op)
                        break
                creados.append((foto._element, (max(v[0], c[0]), max(v[1], c[1]), min(v[2], c[2]), min(v[3], c[3]))))
                cuenta["imagenes"] += 1
                continue
        if tipo == "recorte":
            v = d["visible"]
            datos = PF.recorte_png(img, v, k)
            if datos:
                foto = diapo.shapes.add_picture(io.BytesIO(datos), emu(v[0]), emu(v[1]), emu(v[2] - v[0]), emu(v[3] - v[1]))
                foto.name = f"Pieza {foto.shape_id}"
                creados.append((foto._element, tuple(v)))
                cuenta["piezas"] += 1
            continue
        if tipo == "texto":
            caja = _cuadro(diapo, d, esc)
            creados.append((caja._element, _caja_linea(d)))
            cuenta["cuadros"] += 1
        elif tipo == "girada":
            zg, ls = d
            g = _girada(zg, ls, pw, ph)
            caja = _cuadro(diapo, g, esc, giro=zg["giro"], opacidad=zg["opacidad"], texto=[l["trozos"] for l in ls])
            creados.append((caja._element, (min(l["x0"] for l in ls), min(l["y0"] for l in ls),
                                            max(l["x1"] for l in ls), max(l["y1"] for l in ls))))
            cuenta["cuadros"] += 1
    img.close()
    # agrupar lo de cada elemento animado y escribir la animación
    if modelo and posiciones and posiciones.get("papel"):
        papel, cajas = posiciones["papel"], posiciones.get("cajas") or {}
        fx, fy = pw / papel["ancho"], ph / papel["alto"]
        animados = [(i, a, prof) for i, a, prof in AN.nodos_animados(modelo)
                    if i in cajas and int(cajas[i].get("pagina") or 1) == n]
        reclamados, grupos = set(), {}
        for i, a, prof in sorted(animados, key=lambda x: -x[2]):     # primero lo más interior
            c = cajas[i]
            zona = (c["x0"] * fx, c["y0"] * fy, c["x1"] * fx, c["y1"] * fy)
            # lo que cae dentro de la caja del nodo (con algo de holgura: el texto sobresale un poco);
            # no basta con el centro: el marco de la caja que lo contiene también tiene el centro dentro
            holgura = max(3.0, 0.03 * max(zona[2] - zona[0], zona[3] - zona[1]))
            miembros = [el for el, caja in creados if id(el) not in reclamados and PF._dentro(caja, zona, holgura)]
            reclamados.update(id(el) for el in miembros)
            grupos[i] = miembros
        pasos, hechos = [], {}
        for i, a, _ in animados:                                     # en el orden del documento
            sid = PF.agrupar(diapo, grupos.get(i) or [], f"Animado {i}")
            if sid:
                pasos.append((sid, a))
                hechos[i] = sid
        # un elemento animado dentro de una caja animada va justo encima de ella (si no, el fondo de la
        # caja, que ahora es parte del grupo de la caja, lo taparía)
        por_id = {int(e.find(".//" + qn("p:cNvPr")).get("id")): e for e in arbol
                  if e.tag in (qn("p:sp"), qn("p:grpSp"), qn("p:pic"), qn("p:cxnSp"))}
        for i, _, prof in animados:
            if prof != 1 or i not in hechos:
                continue
            c = cajas[i]
            centro = ((c["x0"] + c["x1"]) / 2, (c["y0"] + c["y1"]) / 2)
            padre = next((j for j, _, pj in animados if pj == 0 and j in hechos
                          and cajas[j]["x0"] <= centro[0] <= cajas[j]["x1"] and cajas[j]["y0"] <= centro[1] <= cajas[j]["y1"]),
                         None)
            hijo, madre = por_id.get(hechos[i]), por_id.get(hechos.get(padre))
            if hijo is not None and madre is not None and list(arbol).index(hijo) < list(arbol).index(madre):
                arbol.remove(hijo)
                arbol.insert(list(arbol).index(madre) + 1, hijo)
        cuenta["animadas"] = len(pasos)
        cuenta["timing"] = AN.xml_animaciones(pasos)
    return cuenta
