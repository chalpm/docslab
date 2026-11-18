# SPDX-License-Identifier: AGPL-3.0-only
"""Revisión antes de imprimir.

Mira el PDF ya compilado con las herramientas de Poppler (pdfinfo, pdfimages,
pdffonts, pdftohtml y pdftoppm) y lo cruza con el modelo del póster:

* imágenes: su resolución real al tamaño que tienen en el póster (ppi), las que
  faltan y las de ejemplo;
* letra: el tamaño del texto principal y lo más pequeño de cada parte (también
  dentro de las figuras), según el tamaño del póster;
* contraste entre cada texto y lo que tiene detrás (la fórmula de las WCAG);
* tipografías: incrustadas y sin mapas de bits;
* contenido: textos de ejemplo, citas sin referencia, líneas que se salen y
  cosas demasiado cerca del borde.

El resultado son secciones con comprobaciones. Cada una dice el elemento del
póster (si lo hay) y la zona de la página (en fracciones del ancho y del alto)
para que la aplicación la señale en la vista previa."""
from __future__ import annotations

import copy
import html
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..nucleo import modelo as M
from ..documento import variantes as V

AREA_A0 = 841 * 1189                 # mm²
MM_POR_BP = 25.4 / 72                # punto PostScript (el del PDF)
MM_POR_PT = 25.4 / 72.27             # punto de TeX (el de las posiciones)
ORDEN = {"problema": 0, "aviso": 1, "info": 2, "bien": 3}
EXT_RASTER = (".png", ".jpg", ".jpeg")

# Palabras que solo aparecen en el texto de relleno «lorem ipsum»
LOREM = {
    "lorem", "ipsum", "consectetuer", "consectetur", "adipiscing", "pellentesque", "curabitur", "vestibulum",
    "suspendisse", "phasellus", "vivamus", "ullamcorper", "porttitor", "nonummy", "malesuada", "scelerisque",
    "tincidunt", "euismod", "facilisis", "dignissim", "quisque", "donec", "aliquam", "praesent", "mauris",
    "molestie", "rhoncus", "viverra", "fermentum", "volutpat", "tristique", "vehicula", "placerat", "gravida",
    "interdum", "luctus", "eiusmod", "incididunt", "laboris", "nostrud", "exercitation", "ullamco", "aliquip",
    "consequat", "voluptate", "cillum", "fugiat", "pariatur", "excepteur", "occaecat", "cupidatat", "proident",
    "deserunt", "laborum", "sollicitudin", "condimentum", "elementum", "imperdiet", "pharetra", "sagittis",
}
# Textos que pone DocsLab de ejemplo (asistente, plantillas incluidas)
EJEMPLOS = [
    "título del póster", "mensaje principal en una línea", "nombre apellido", "nombre del congreso",
    "ciudad, año", "correo@", "@institución", ".example", "texto de la sección «", "escribe aquí",
    "texto de relleno", "artículo de relleno", "libro de relleno", "imágenes de relleno", "valores de relleno",
    "texto de ejemplo",
]
# Valores iniciales de los elementos que pueden quedarse tal cual (rótulos razonables)
DEFECTOS_VALIDOS = {"antes", "después", "cita", "ecuación", "cronología", "nota", "resultado", "resultado principal",
                    "mensaje para llevar"}
IMAGEN_EJEMPLO = re.compile(r"(^|/)(prueba\d*|qr_prueba|ejemplo[\w-]*|placeholder[\w-]*|relleno[\w-]*)\.(png|jpe?g|pdf)$",
                            re.I)


# ---------------------------------------------------------------------- utilidades
def herramientas() -> dict:
    return {n: bool(shutil.which(n)) for n in ("pdfinfo", "pdfimages", "pdffonts", "pdftohtml", "pdftoppm")}


def _correr(args: list[str], tiempo: int = 90) -> str | None:
    exe = shutil.which(args[0])
    if not exe:
        return None
    try:
        p = subprocess.run([exe, *args[1:]], capture_output=True, timeout=tiempo, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0 and not p.stdout:
        return None
    return p.stdout.decode("utf-8", "replace")


def a_mm(valor, defecto: float | None = None) -> float | None:
    mo = re.match(r"^\s*(-?[0-9.]+)\s*(mm|cm|in|pt|bp)?\s*$", str(valor or ""))
    if not mo:
        return defecto
    v = float(mo.group(1))
    return v * {"mm": 1, "cm": 10, "in": 25.4, "pt": MM_POR_PT, "bp": MM_POR_BP, None: 1}[mo.group(2)]


def _num(x: float, dec: int = 0) -> str:
    """Número a la española: 12,5."""
    s = f"{x:.{dec}f}" if dec else str(int(round(x)))
    return s.replace(".", ",")


def _cm(mm: float) -> str:
    return _num(mm / 10, 1 if mm < 1000 else 0)


def _plano(t) -> str:
    """Texto sin marcas (para nombres y muestras)."""
    t = str(t or "")
    t = re.sub(r"\{\{|\}\}", "", t)
    t = re.sub(r"\\[A-Za-z]+\*?(\[[^\]]*\])?", "", t)
    t = re.sub(r"[{}*_^$~]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _corto(t, n: int = 70) -> str:
    t = _plano(t)
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def luminancia(rgb) -> float:
    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(x)) for x in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b) -> float:
    la, lb = luminancia(a), luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _hex(rgb) -> str:
    return "#" + "".join(f"{int(x):02X}" for x in rgb[:3])


def item(nivel: str, titulo: str, detalle: str = "", consejo: str = "", elemento: str | None = None,
         zona: dict | None = None, muestra: str | None = None, accion: str | None = None, **extra) -> dict:
    d = {"nivel": nivel, "titulo": titulo}
    for k, v in (("detalle", detalle), ("consejo", consejo), ("elemento", elemento), ("zona", zona),
                 ("muestra", muestra), ("accion", accion)):
        if v:
            d[k] = v
    d.update({k: v for k, v in extra.items() if v is not None})
    return d


# ---------------------------------------------------------------------- lectura del PDF
def info_pdf(pdf: Path) -> dict | None:
    s = _correr(["pdfinfo", "-f", "1", "-l", "20", str(pdf)])
    if s is None:
        return None
    mo = re.search(r"^Pages:\s+(\d+)", s, re.M)
    tams = [(float(a), float(b)) for a, b in re.findall(r"^Page\s+\d+\s+size:\s+([\d.]+) x ([\d.]+)", s, re.M)]
    if not tams:
        tams = [(float(a), float(b)) for a, b in re.findall(r"^Page size:\s+([\d.]+) x ([\d.]+)", s, re.M)]
    return {"paginas": int(mo.group(1)) if mo else max(1, len(tams)), "tamanos": tams or [(2384.0, 3370.0)]}


_RE_PAGINA = re.compile(r'<page number="(\d+)"[^>]*?height="([\d.]+)" width="([\d.]+)"')
_RE_FUENTE = re.compile(r'<fontspec id="(\d+)" size="(-?[\d.]+)" family="([^"]*)" color="#([0-9a-fA-F]{6})"')
_RE_TEXTO = re.compile(r'<text top="(-?[\d.]+)" left="(-?[\d.]+)" width="([\d.]+)" height="([\d.]+)" '
                       r'font="(\d+)">(.*?)</text>', re.S)


def textos_pdf(pdf: Path) -> list[dict] | None:
    """Cada trozo de texto con su página, caja (pt del PDF, desde arriba a la izquierda),
    tamaño de letra (redondeado al punto), familia y color."""
    s = _correr(["pdftohtml", "-xml", "-i", "-stdout", "-q", "-zoom", "1", "-nodrm", str(pdf)])
    if s is None:
        return None
    fuentes = {}
    for mo in _RE_FUENTE.finditer(s):
        fam = re.sub(r"^[A-Z]{6}\+", "", mo.group(3))
        col = mo.group(4)
        fuentes[mo.group(1)] = (float(mo.group(2)), fam, tuple(int(col[i:i + 2], 16) for i in (0, 2, 4)))
    paginas = [(mo.start(), int(mo.group(1))) for mo in _RE_PAGINA.finditer(s)]
    salida = []
    for i, (ini, num) in enumerate(paginas):
        fin = paginas[i + 1][0] if i + 1 < len(paginas) else len(s)
        for mo in _RE_TEXTO.finditer(s, ini, fin):
            f = fuentes.get(mo.group(5))
            texto = html.unescape(re.sub(r"<[^>]+>", "", mo.group(6))).strip()
            if not f or not texto or f[0] <= 0:
                continue
            x, y, w, h = (float(mo.group(k)) for k in (2, 1, 3, 4))
            salida.append({"pagina": num, "x0": x, "y0": y, "x1": x + w, "y1": y + h, "texto": texto,
                           "tam": f[0], "familia": f[1], "color": f[2]})
    return salida


def imagenes_pdf(pdf: Path) -> list[dict] | None:
    s = _correr(["pdfimages", "-list", str(pdf)])
    if s is None:
        return None
    filas = []
    for ln in s.splitlines()[2:]:
        p = ln.split()
        if len(p) < 14 or not p[0].isdigit():
            continue
        try:
            filas.append({"pagina": int(p[0]), "tipo": p[2], "ancho": int(p[3]), "alto": int(p[4]), "color": p[5],
                          "objeto": int(p[10]), "ppi_x": float(p[12]), "ppi_y": float(p[13])})
        except ValueError:
            continue
    return filas


def fuentes_pdf(pdf: Path) -> list[dict] | None:
    s = _correr(["pdffonts", str(pdf)])
    if s is None:
        return None
    salida = []
    for ln in s.splitlines()[2:]:
        p = ln.split()
        if len(p) < 8:
            continue
        salida.append({"nombre": p[0], "tipo": " ".join(p[1:-6]), "incrustada": p[-5] == "yes"})
    return salida


def de_mapa_de_bits(f: dict) -> bool:
    """¿Una tipografía Type 3 de las que pdfTeX hace con píxeles (METAFONT)? Se llaman F37,
    ecrm1000… Las Type 3 de matplotlib (DejaVuSans) son vectoriales y no cuentan."""
    return f.get("tipo") == "Type 3" and bool(
        re.fullmatch(r"(?:[A-Z]{6}\+)?(?:\[none\]|F\d+|[a-z]{2,8}\d{2,5})", f.get("nombre") or "", re.I))


def renderizar(pdf: Path, pagina: int, ppp: float):
    """La página como imagen RGB de Pillow (o None)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    with tempfile.TemporaryDirectory(prefix="pl-rev-") as tmp:
        base = Path(tmp) / "pagina"
        if _correr(["pdftoppm", "-png", "-r", f"{ppp:.2f}", "-f", str(pagina), "-l", str(pagina),
                    "-singlefile", str(pdf), str(base)], tiempo=180) is None:
            return None
        p = base.with_suffix(".png")
        if not p.exists():
            return None
        with Image.open(p, formats=("PNG",)) as im:
            return im.convert("RGB")


def fondo_detras(img, caja_px: tuple[int, int, int, int], color_texto) -> tuple | None:
    """El color que más se repite en la caja del texto sin contar los del propio texto."""
    x0, y0, x1, y1 = caja_px
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.width, x1), min(img.height, y1)
    if x1 - x0 < 1 or y1 - y0 < 1:
        return None
    region = img.crop((x0, y0, x1, y1))
    colores = region.getcolors(maxcolors=(x1 - x0) * (y1 - y0) + 1) or []
    grupos: dict[tuple, list] = {}
    for n, c in colores:
        if sum((a - b) ** 2 for a, b in zip(c, color_texto)) < 30 ** 2:
            continue                        # píxeles del propio texto
        k = (c[0] >> 4, c[1] >> 4, c[2] >> 4)
        g = grupos.setdefault(k, [0, {}])
        g[0] += n
        g[1][c] = g[1].get(c, 0) + n
    if not grupos:
        return tuple(color_texto)           # no hay nada distinto del texto: no se lee
    k = max(grupos, key=lambda x: grupos[x][0])
    return max(grupos[k][1].items(), key=lambda kv: kv[1])[0]


# ---------------------------------------------------------------------- el modelo
def nodos_modelo(m: dict) -> dict:
    """id → {tipo, nombre, grupo} de lo que se ve del póster."""
    nodos = {}
    cab, pie = m.get("cabecera") or {}, m.get("pie") or {}
    if cab.get("visible", True):
        nodos["cabecera"] = {"tipo": "cabecera", "nombre": "la cabecera"}
    if pie.get("visible", True):
        nodos["pie"] = {"tipo": "pie", "nombre": "el pie del póster"}
    if m.get("clase") == "presentacion":
        n = 0
        for pg in m.get("paginas") or []:
            if pg.get("visible") is False:
                continue
            n += 1
            titulo = _corto(pg.get("nombre"), 40)
            nodos[pg["id"]] = {"tipo": "pagina", "nombre": f"la diapositiva {n}" + (f" («{titulo}»)" if titulo else "")}
    for fila in m.get("filas", []):
        if fila.get("visible") is False:
            continue
        nodos[fila["id"]] = {"tipo": "fila", "nombre": "una fila"}
        for col in fila.get("columnas", []):
            nodos[col["id"]] = {"tipo": "columna", "nombre": "una columna"}
            for b in col.get("bloques", []):
                if b.get("visible") is False:
                    continue
                titulo = _corto(b.get("titulo"), 40) or "una caja sin título"
                nb = f"«{titulo}»" if b.get("titulo") else titulo
                nodos[b["id"]] = {"tipo": "bloque", "nombre": nb}
                for e in b.get("elementos", []):
                    if e.get("visible") is False:
                        continue
                    tipo = str(e.get("tipo") or "")
                    v = V.POR_CLAVE.get(tipo)
                    if v:
                        nv, grupo = v["nombre"], v["grupo"]
                    elif tipo.startswith("cmp:"):
                        c = (m.get("componentes") or {}).get(tipo[4:]) or {}
                        nv, grupo = str(c.get("nombre") or "componente"), "componente"
                    else:
                        nv, grupo = tipo, "otros"
                    con_imagen = bool(M.campos_imagen_de(e, m))
                    nodos[e["id"]] = {"tipo": "elemento", "nombre": f"{nb} ({nv[:1].lower() + nv[1:]})",
                                      "grupo": "imagen" if grupo == "imagen" or con_imagen else grupo,
                                      "bloque": b["id"]}
    for capa in m.get("capas", []):
        if capa.get("visible") is False:
            continue
        for it in capa.get("elementos", []):
            if it.get("visible") is False:
                continue
            tipo = it.get("tipo")
            desc = {"imagen": "una imagen", "texto": "un texto", "forma": "una forma", "latex": "un dibujo"}.get(tipo, "un elemento")
            nodos[it["id"]] = {"tipo": "item", "nombre": f"{desc} de la capa «{capa.get('nombre') or capa['id']}»",
                               "grupo": "imagen" if tipo == "imagen" else "capa"}
    return nodos


def textos_modelo(m: dict) -> list[tuple[str, str, str]]:
    """(id, campo, texto) de todo lo escrito que se ve en el póster."""
    salida = []
    cab, pie = m.get("cabecera") or {}, m.get("pie") or {}
    if cab.get("visible", True):
        for k in ("titulo", "subtitulo", "autores", "afiliaciones"):
            if str(cab.get(k) or "").strip():
                salida.append(("cabecera", k, str(cab[k])))
    if pie.get("visible", True):
        for k in ("izquierda", "centro", "derecha"):
            if str(pie.get(k) or "").strip():
                salida.append(("pie", k, str(pie[k])))
    titulos = (m.get("estilo") or {}).get("mostrar_titulos", True)
    for fila in m.get("filas", []):
        if fila.get("visible") is False:
            continue
        for col in fila.get("columnas", []):
            for b in col.get("bloques", []):
                if b.get("visible") is False:
                    continue
                if titulos and b.get("mostrar_titulo", True) and str(b.get("titulo") or "").strip():
                    salida.append((b["id"], "titulo", str(b["titulo"])))
                for e in b.get("elementos", []):
                    if e.get("visible") is False:
                        continue
                    for c in M.campos_de(e, m):
                        k, tipo = c["nombre"], c.get("tipo")
                        val = e.get(k)
                        if k == "titulo" and e.get("mostrar_titulo") is False:
                            continue
                        for t in _textos_de_valor(tipo, val):
                            salida.append((e["id"], k, t))
    for capa in m.get("capas", []):
        if capa.get("visible") is False:
            continue
        for it in capa.get("elementos", []):
            if it.get("visible") is not False and it.get("tipo") == "texto" and str(it.get("texto") or "").strip():
                salida.append((it["id"], "texto", str(it["texto"])))
    return salida


def _textos_de_valor(tipo, val) -> list[str]:
    if tipo in ("texto", "parrafo") and isinstance(val, str) and val.strip():
        return [val]
    if tipo == "lista" and isinstance(val, list):
        return [x for x in val if isinstance(x, str) and x.strip()]
    if tipo in ("pares", "hitos") and isinstance(val, list):
        return [x for par in val if isinstance(par, list) for x in par if isinstance(x, str) and x.strip()]
    if tipo == "flechas" and isinstance(val, list):
        return [f[4] for f in val if isinstance(f, list) and len(f) >= 5 and isinstance(f[4], str) and f[4].strip()]
    if tipo == "tabla" and isinstance(val, dict) and isinstance(val.get("filas"), list):
        return [x for fila in val["filas"] if isinstance(fila, list) for x in fila if isinstance(x, str) and x.strip()]
    return []


def es_relleno(texto: str) -> bool:
    t = texto.lower()
    if "lorem ipsum" in t:
        return True
    palabras = set(re.findall(r"[a-z]+", t))
    return len(palabras & LOREM) >= 2


def es_ejemplo(texto: str) -> bool:
    t = texto.lower()
    return any(x in t for x in EJEMPLOS)


def imagenes_modelo(m: dict) -> list[tuple[str, str, str]]:
    """(id, campo, ruta) de cada imagen que se ve (ruta vacía = falta por poner)."""
    salida = []
    cab = m.get("cabecera") or {}
    if cab.get("visible", True):
        for k in ("logo_izquierdo", "logo_derecho"):
            if str(cab.get(k) or "").strip():
                salida.append(("cabecera", k, str(cab[k]).strip()))
        if cab.get("estilo") == "imagen" and str(cab.get("imagen") or "").strip():
            salida.append(("cabecera", "imagen", str(cab["imagen"]).strip()))
    for fila in m.get("filas", []):
        if fila.get("visible") is False:
            continue
        for col in fila.get("columnas", []):
            for b in col.get("bloques", []):
                if b.get("visible") is False:
                    continue
                for e in b.get("elementos", []):
                    if e.get("visible") is False:
                        continue
                    for k in M.campos_imagen_de(e, m):
                        salida.append((e["id"], k, str(e.get(k) or "").strip()))
    for capa in m.get("capas", []):
        if capa.get("visible") is False:
            continue
        for it in capa.get("elementos", []):
            if it.get("visible") is not False and it.get("tipo") == "imagen":
                salida.append((it["id"], "archivo", str(it.get("archivo") or "").strip()))
    return salida


# ---------------------------------------------------------------------- la revisión
class _Posiciones:
    """Las cajas de la última compilación (pt de TeX), para saber qué hay en cada sitio."""

    def __init__(self, posiciones: dict | None, nodos: dict):
        self.papel = (posiciones or {}).get("papel")
        self.cajas = {}
        lista = []
        for ident, c in ((posiciones or {}).get("cajas") or {}).items():
            if ident not in nodos or not self.papel:
                continue
            z = self.zona(c)
            self.cajas[ident] = z
            if nodos[ident]["tipo"] not in ("fila", "columna"):
                lista.append(((z["x1"] - z["x0"]) * (z["y1"] - z["y0"]), ident, z))
        self.lista = sorted(lista, key=lambda x: x[0])

    def zona(self, c: dict) -> dict:
        w, h = self.papel["ancho"], self.papel["alto"]
        return {"pagina": int(c.get("pagina") or 1), "x0": c["x0"] / w, "y0": c["y0"] / h,
                "x1": c["x1"] / w, "y1": c["y1"] / h}

    def en(self, pagina: int, fx: float, fy: float) -> str | None:
        for _, ident, z in self.lista:
            if z["pagina"] == pagina and z["x0"] - 1e-4 <= fx <= z["x1"] + 1e-4 and z["y0"] - 1e-4 <= fy <= z["y1"] + 1e-4:
                return ident
        return None


def _nombre_tamano(w_mm: float, h_mm: float) -> str:
    for nombre, (a, b) in M.TAMANOS.items():
        am, bm = a_mm(a), a_mm(b)
        if am and bm and ((abs(am - w_mm) < 2.5 and abs(bm - h_mm) < 2.5) or (abs(am - h_mm) < 2.5 and abs(bm - w_mm) < 2.5)):
            return nombre
    return ""


def _donde(zona: dict | None, varias_paginas: bool = False) -> str:
    """«la parte superior izquierda»… para lo que no tiene elemento (proyectos LaTeX)."""
    if not zona:
        return "el póster"
    cx, cy = (zona["x0"] + zona["x1"]) / 2, (zona["y0"] + zona["y1"]) / 2
    v = "superior" if cy < 1 / 3 else "inferior" if cy > 2 / 3 else "central"
    h = " izquierda" if cx < 1 / 3 else " derecha" if cx > 2 / 3 else ""
    pagina = f" de la página {zona.get('pagina', 1)}" if varias_paginas else ""
    return f"la parte {v}{h}{pagina}"


# ---------------------------------------------------------------------- color al imprimir
def _lab(rgb) -> tuple[float, float, float]:
    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(v)) for v in rgb[:3])
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def delta_e(a, b) -> float:
    """Diferencia de color perceptual (CIE76): 2 apenas se nota; más de 10 se ve claramente."""
    la, lb = _lab(a), _lab(b)
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(la, lb)))


def _rgb(hexa: str) -> tuple[int, int, int]:
    h = hexa.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _pdf_muestras(colores: list[str], lado: int = 20) -> bytes:
    """Un PDF mínimo con un cuadrado de cada color (RGB)."""
    cont = "".join(f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} rg {i * lado} 0 {lado} {lado} re f\n"
                   for i, (r, g, b) in enumerate(_rgb(c) for c in colores)).encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {len(colores) * lado} {lado}] /Contents 4 0 R "
            f"/Resources << >> >>".encode(),
            b"<< /Length " + str(len(cont)).encode() + b" >>\nstream\n" + cont + b"endstream"]
    out = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def colores_en_cmyk(colores: list[str]) -> dict[str, str] | None:
    """Cómo quedan unos colores (hexadecimal) al pasarlos a tinta: Ghostscript los
    convierte a CMYK con su perfil genérico y los vuelve a pintar en RGB."""
    from . import compilador
    gs = compilador.ghostscript()
    colores = [c.upper().lstrip("#") for c in colores if re.fullmatch(r"#?[0-9A-Fa-f]{6}", c or "")]
    if not gs or not colores:
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    lado = 20
    with tempfile.TemporaryDirectory(prefix="pl-cmyk-") as tmp:
        tmp = Path(tmp)
        (tmp / "rgb.pdf").write_bytes(_pdf_muestras(colores, lado))
        base = [gs, "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE"]
        try:
            subprocess.run(base + ["-sDEVICE=pdfwrite", "-sColorConversionStrategy=CMYK", "-sProcessColorModel=DeviceCMYK",
                                   f"-sOutputFile={tmp / 'cmyk.pdf'}", str(tmp / "rgb.pdf")],
                           capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
            subprocess.run(base + ["-sDEVICE=png16m", "-r72", f"-sOutputFile={tmp / 'vuelta.png'}", str(tmp / "cmyk.pdf")],
                           capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
            with Image.open(tmp / "vuelta.png", formats=("PNG",)) as im:
                im = im.convert("RGB")
                return {c: _hex(im.getpixel((i * lado + lado // 2, lado // 2))) for i, c in enumerate(colores)}
        except (OSError, subprocess.TimeoutExpired, ValueError):
            return None


NOMBRES_COLORES_TEMA = {"primario": "color principal", "secundario": "color secundario", "acento": "color de acento",
                        "fondo": "fondo del póster", "fondo_bloque": "fondo de las cajas", "texto": "color del texto",
                        "tenue": "color del texto secundario", "contraste": "texto sobre el color principal"}


def colores_modelo(m: dict) -> list[tuple[str, str, str | None]]:
    """(hexadecimal, para qué se usa, id) de los colores del póster: el tema y los que
    se han puesto a mano en cajas, cabecera, pie, capas y elementos."""
    vistos, salida = set(), []

    def poner(valor, uso, ident=None):
        v = str(valor or "").strip().lstrip("#").upper()
        if re.fullmatch(r"[0-9A-F]{6}", v) and v not in vistos:
            vistos.add(v)
            salida.append((v, uso, ident))
    for k, nombre in NOMBRES_COLORES_TEMA.items():
        poner((m.get("colores") or {}).get(k), nombre)
    for k, nombre in (("cabecera", "la cabecera"), ("pie", "el pie del póster")):
        parte = m.get(k) or {}
        poner(parte.get("fondo"), f"fondo de {nombre}", k)
        poner(parte.get("color_texto"), f"texto de {nombre}", k)
    for fila in m.get("filas", []):
        for col in fila.get("columnas", []):
            for b in col.get("bloques", []):
                op = b.get("opciones") or {}
                titulo = _corto(b.get("titulo"), 30) or "una caja"
                for k, uso in (("fondo", "fondo"), ("borde", "borde"), ("fondo_titulo", "fondo del título"),
                               ("color_titulo", "título"), ("color_texto", "texto")):
                    poner(op.get(k), f"{uso} de «{titulo}»", b["id"])
                for e in b.get("elementos", []):
                    for c in M.campos_de(e, m):
                        if c.get("tipo") == "color":
                            poner(e.get(c["nombre"]), f"color de un elemento de «{titulo}»", e["id"])
    for capa in m.get("capas", []):
        for it in capa.get("elementos", []):
            for k in ("fondo", "borde", "color"):
                poner(it.get(k), f"un elemento de la capa «{capa.get('nombre') or capa.get('id')}»", it.get("id"))
    return salida


def revisar(directorio: Path, pdf: Path, modelo: dict | None = None, compilacion: dict | None = None,
            tipo: str = "estructurado") -> dict:
    """Revisa el PDF de un póster. «modelo» solo en los del editor visual."""
    directorio, pdf = Path(directorio), Path(pdf)
    m = M.normalizar(modelo) if modelo else None
    comp = compilacion or {}
    nodos = nodos_modelo(m) if m else {}
    pos = _Posiciones(comp.get("posiciones"), nodos)
    faltan = [k for k, v in herramientas().items() if not v]
    secciones = {k: [] for k in ("pagina", "imagenes", "letra", "contraste", "color", "tipografias", "contenido")}

    def nombre(ident: str | None, zona: dict | None = None) -> str:
        if ident and ident in nodos:
            return nodos[ident]["nombre"]
        return _donde(zona, paginas > 1)

    info = info_pdf(pdf) if pdf.exists() else None
    paginas = (info or {}).get("paginas") or (comp.get("paginas") or 1)
    w_bp, h_bp = ((info or {}).get("tamanos") or [(0.0, 0.0)])[0]
    if not w_bp and pos.papel:
        w_bp, h_bp = pos.papel["ancho"] * 72 / 72.27, pos.papel["alto"] * 72 / 72.27
    w_mm, h_mm = w_bp * MM_POR_BP, h_bp * MM_POR_BP
    escala = math.sqrt(max(1.0, w_mm * h_mm) / AREA_A0) if w_mm else 1.0
    clase = m.get("clase", "poster") if m else "poster"
    perfil = perfil_lectura(clase, escala, h_mm)
    nombre_tam = _nombre_tamano(w_mm, h_mm)
    orient = "horizontal" if w_mm > h_mm else "vertical"

    # ------------------------------------------------------------------ página
    sp = secciones["pagina"]
    desc = (f"{nombre_tam} {orient}, " if nombre_tam else "") + f"{_num(w_mm)} × {_num(h_mm)} mm"
    sp.append(item("info", f"{perfil['Nombre']} {desc}", f"{paginas} {'página' if paginas == 1 else 'páginas'}."))
    if comp and not comp.get("ok", True):
        sp.append(item("problema", "La última compilación tiene errores",
                       "Se revisa el último PDF que compiló bien, que no tiene tus últimos cambios.",
                       "Corrige los errores (mira el registro bajo la vista previa) y vuelve a revisar."))
    largas = comp.get("diapositivas_largas") or []
    if clase == "presentacion":
        for ident in largas[:6]:
            sp.append(item("problema", f"No cabe en una página: {nombre(ident)}",
                           "Lo que no cabe pasa a una página aparte y descuadra la presentación.",
                           "Quita contenido, reduce las imágenes o usa «Ajustar a una página».",
                           elemento=ident, accion="ajustar"))
    elif paginas > 1 and clase != "poster":
        pass                                   # un documento tiene las páginas que necesite
    elif paginas > 1:
        if tipo == "estructurado":
            sp.append(item("problema", f"El póster ocupa {paginas} páginas",
                           "Lo que no cabe en el lienzo pasa a otra página y no se imprimiría.",
                           "Usa «Ajustar a una página» o reduce el contenido.", accion="ajustar"))
        else:
            sp.append(item("info", f"El documento tiene {paginas} páginas", "Comprueba que es lo que quieres imprimir."))
    no_caben = [a for a in comp.get("avisos") or [] if "no cabe" in str(a.get("mensaje"))]
    if no_caben and paginas == 1 and tipo == "estructurado" and clase == "poster":
        sp.append(item("problema", "Hay una fila que no cabe en el lienzo",
                       _corto(no_caben[0]["mensaje"], 140),
                       "Usa «Ajustar a una página» o quita contenido de esa fila.", accion="ajustar"))
    if m:
        margen = a_mm(m["lienzo"].get("margen"), 28) or 0
        if margen < 5:
            sp.append(item("aviso", f"El margen es de {_num(margen)} mm",
                           "Al cortar el papel, la imprenta puede desviarse 2 o 3 mm: el texto tan cerca del borde puede quedar cortado.",
                           "Deja al menos 10 mm de margen (pestaña Diseño, Lienzo)."))
        fondo = str(m["colores"].get("fondo") or "FFFFFF").upper().lstrip("#")
        if fondo not in ("FFFFFF", "") or any(nodos[i]["grupo"] == "imagen" and _toca_borde(z) for i, z in pos.cajas.items()
                                              if nodos[i]["tipo"] == "item"):
            sp.append(item("info", "Hay color o imágenes hasta el borde del papel",
                           "Para que al cortar no queden filos blancos, la imprenta suele pedir 3 mm de sangrado.",
                           "Descarga el «PDF para imprenta» con sangrado de 3 mm."))
    if not faltan and not any(i["nivel"] in ("problema", "aviso") for i in sp):
        sp.append(item("bien", "Tamaño y páginas en orden"))

    # ------------------------------------------------------------------ imágenes
    si = secciones["imagenes"]
    ppi_bueno = 150 if escala >= 0.7 else 200 if escala >= 0.45 else 250
    if clase == "presentacion":
        ppi_bueno = 110                        # se proyecta: con unos 1500 px de ancho basta
    ppi_malo = round(ppi_bueno * 2 / 3)
    usos = imagenes_modelo(m) if m else []
    archivos: dict[str, dict] = {}            # ruta → {dims, vectorial, usos}
    for ident, campo, ruta in usos:
        if not ruta:
            if ident == "cabecera":
                continue
            si.append(item("problema", f"Falta una imagen en {nombre(ident)}",
                           "En su lugar se imprimirá un recuadro gris con la palabra «imagen».",
                           "Elige la imagen en el inspector o en la pestaña Imágenes, o quita el elemento.",
                           elemento=ident, zona=pos.cajas.get(ident)))
            continue
        p = directorio / ruta
        if not p.is_file():
            si.append(item("problema", f"No se encuentra «{Path(ruta).name}»",
                           f"La usa {nombre(ident)}; en su lugar se imprimirá un recuadro vacío.",
                           "Vuelve a subir la imagen o elige otra.", elemento=ident, zona=pos.cajas.get(ident)))
            continue
        a = archivos.setdefault(ruta, {"usos": [], "dims": set(), "vectorial": p.suffix.lower() in (".pdf", ".eps")})
        a["usos"].append(ident)
        if IMAGEN_EJEMPLO.search(ruta):
            a["ejemplo"] = True
    if not m:                                  # proyecto LaTeX: las imágenes de la carpeta
        for p in sorted(directorio.rglob("*")):
            rel = p.relative_to(directorio).as_posix()
            if p.is_file() and p.suffix.lower() in (*EXT_RASTER, ".pdf") and not rel.startswith(("build/", "historial/")) \
                    and p.name not in (pdf.name,):
                archivos[rel] = {"usos": [], "dims": set(), "vectorial": p.suffix.lower() == ".pdf"}
    for ruta, a in archivos.items():
        p = directorio / ruta
        if p.suffix.lower() in EXT_RASTER:
            try:
                from PIL import Image
                with Image.open(p, formats=("PNG", "JPEG")) as im:
                    a["dims"].add(tuple(im.size))
            except Exception:
                pass
        elif p.suffix.lower() == ".pdf":
            for f in imagenes_pdf(p) or []:
                if f["tipo"] == "image":
                    a["dims"].add((f["ancho"], f["alto"]))
    ejemplos = [(r, a) for r, a in archivos.items() if a.get("ejemplo")]
    for ruta, a in ejemplos[:6]:
        si.append(item("aviso", f"«{Path(ruta).name}» parece una imagen de ejemplo",
                       f"La usa {nombre(a['usos'][0])}." if a["usos"] else "",
                       "Cámbiala por la tuya antes de imprimir.", elemento=a["usos"][0] if a["usos"] else None,
                       zona=pos.cajas.get(a["usos"][0]) if a["usos"] else None))
    filas = [f for f in (imagenes_pdf(pdf) or []) if f["tipo"] == "image"] if pdf.exists() else []
    por_archivo: dict[str, list] = {}
    sueltas = []
    for f in filas:
        candidatos = [r for r, a in archivos.items() if (f["ancho"], f["alto"]) in a["dims"]]
        if candidatos:
            por_archivo.setdefault(candidatos[0], []).append(f)
        elif f["ancho"] * f["alto"] >= 64 * 64:           # iconos y texturas diminutas no cuentan
            sueltas.append(f)
    bajas, minimo = [], None
    for ruta, fs in por_archivo.items():
        f = min(fs, key=lambda x: min(x["ppi_x"], x["ppi_y"]))
        ppi = min(f["ppi_x"], f["ppi_y"])
        minimo = ppi if minimo is None else min(minimo, ppi)
        if ppi < ppi_bueno:
            bajas.append((ppi, ruta, f))
    for ppi, ruta, f in sorted(bajas)[:12]:
        a = archivos[ruta]
        ident = a["usos"][0] if a["usos"] else None
        ancho_mm, alto_mm = f["ancho"] / f["ppi_x"] * 25.4, f["alto"] / f["ppi_y"] * 25.4
        nivel = "problema" if ppi < ppi_malo else "aviso"
        efecto = "se verá pixelada" if nivel == "problema" else "puede verse algo borrosa de cerca"
        if a["vectorial"]:
            titulo = f"La figura «{Path(ruta).name}» lleva una imagen de {_num(ppi)} ppi"
            consejo = (f"Al guardar la figura, sube la resolución (en matplotlib: savefig(..., dpi={max(300, ppi_bueno * 2)})) "
                       "o guárdala como vectorial.")
        else:
            titulo = f"«{Path(ruta).name}» tiene {_num(ppi)} ppi"
            px_w, px_h = math.ceil(ancho_mm / 25.4 * ppi_bueno), math.ceil(alto_mm / 25.4 * ppi_bueno)
            consejo = f"Usa una versión de al menos {px_w} × {px_h} px o ponla más pequeña."
        donde = f" ({nombre(ident)})" if ident else ""
        if w_mm and (ancho_mm > w_mm * 1.02 or alto_mm > h_mm * 1.02):
            donde += ", ampliada para cubrir y recortada"
        si.append(item(nivel, titulo,
                       f"A su tamaño en el póster, {_cm(ancho_mm)} × {_cm(alto_mm)} cm{donde}, {efecto}. "
                       f"Para {perfil['un']} de este tamaño conviene que tenga {ppi_bueno} ppi o más.",
                       consejo, elemento=ident, zona=pos.cajas.get(ident) if ident else None, ppi=round(ppi)))
    if sueltas:
        f = min(sueltas, key=lambda x: min(x["ppi_x"], x["ppi_y"]))
        ppi = min(f["ppi_x"], f["ppi_y"])
        if ppi < ppi_bueno:
            si.append(item("problema" if ppi < ppi_malo else "aviso",
                           f"Hay una imagen de {_num(ppi)} ppi que no sé situar",
                           f"Mide {f['ancho']} × {f['alto']} px y está dentro de una figura o de código LaTeX.",
                           "Búscala entre tus figuras PDF o en el código y usa una versión con más resolución.",
                           ppi=round(ppi)))
    vectoriales = [r for r, a in archivos.items() if a["vectorial"] and a["usos"] and r not in por_archivo]
    if filas or vectoriales:
        if not bajas and (minimo is None or minimo >= ppi_bueno):
            partes = []
            if por_archivo:
                partes.append(f"{len(por_archivo)} {'imagen' if len(por_archivo) == 1 else 'imágenes'} con "
                              f"{_num(minimo)} ppi o más")
            if vectoriales:
                partes.append(f"{len(vectoriales)} {'figura vectorial' if len(vectoriales) == 1 else 'figuras vectoriales'} "
                              "(nítidas a cualquier tamaño)")
            if partes:
                si.append(item("bien", "Las imágenes tienen buena resolución", "; ".join(partes).capitalize() + "."))
    elif not usos and not archivos:
        si.append(item("info", f"{perfil['El']} no tiene imágenes"))

    # ------------------------------------------------------------------ letra, contraste y textos
    textos = textos_pdf(pdf) if pdf.exists() else None
    tam_pagina = {}
    if info:
        for i, (w, h) in enumerate(info["tamanos"], start=1):
            tam_pagina[i] = (w, h)

    def zona_texto(t) -> dict:
        w, h = tam_pagina.get(t["pagina"], (w_bp or 1, h_bp or 1))
        return {"pagina": t["pagina"], "x0": t["x0"] / w, "y0": t["y0"] / h, "x1": t["x1"] / w, "y1": t["y1"] / h}

    sl, sc = secciones["letra"], secciones["contraste"]
    if textos:
        for t in textos:
            z = zona_texto(t)
            t["zona"] = z
            t["nodo"] = pos.en(t["pagina"], (z["x0"] + z["x1"]) / 2, (z["y0"] + z["y1"]) / 2)
        # familias del propio póster (lo que no está dentro de una figura)
        propias = {t["familia"] for t in textos if not (t["nodo"] and nodos.get(t["nodo"], {}).get("grupo") == "imagen")}
        for t in textos:
            info_nodo = nodos.get(t["nodo"], {}) if t["nodo"] else {}
            t["grupo"], t["tipo_nodo"] = info_nodo.get("grupo"), info_nodo.get("tipo")
            t["figura"] = t["grupo"] == "imagen" and t["familia"] not in propias
        _revisar_letra(sl, textos, perfil, nombre, pos)
        _revisar_contraste(sc, textos, pdf, tam_pagina, nombre, escala)
    elif "pdftohtml" in faltan:
        for s in (sl, sc):
            s.append(item("info", "No se pudo revisar", "Falta pdftohtml (viene con Poppler)."))
    elif textos is not None:
        sl.append(item("info", "El PDF no tiene texto"))

    # ------------------------------------------------------------------ color al imprimir
    scol = secciones["color"]
    if m:
        usados = colores_modelo(m)
        impresos = colores_en_cmyk([c for c, _, _ in usados])
        if impresos is None:
            scol.append(item("info", "No se pudo simular la tinta",
                             "Hace falta Ghostscript (gs) para ver cómo quedan los colores al imprimir."))
        else:
            cambian = []
            for c, uso, ident in usados:
                if c in impresos:
                    de = delta_e(_rgb(c), _rgb(impresos[c]))
                    if de >= 10:
                        cambian.append((de, c, uso, ident))
            for de, c, uso, ident in sorted(cambian, reverse=True)[:8]:
                scol.append(item("aviso", f"{uso[:1].upper() + uso[1:]}: se imprimirá {'bastante ' if de >= 25 else ''}más apagado",
                                 f"#{c} en pantalla queda más o menos como {impresos[c]} en tinta (CMYK).",
                                 "La pantalla muestra colores que la tinta no alcanza. Si ese tono importa, elige "
                                 "uno algo menos vivo o pide una prueba de color a la imprenta.",
                                 elemento=ident if ident in nodos else None,
                                 zona=pos.cajas.get(ident) if ident else None,
                                 color_antes=f"#{c}", color_despues=impresos[c], diferencia=round(de, 1)))
            if len(cambian) > 8:
                scol.append(item("info", f"Y {len(cambian) - 8} colores más que cambian al imprimir"))
            if not cambian:
                scol.append(item("bien", "Los colores se imprimen casi igual",
                                 f"{len(usados)} {'color revisado' if len(usados) == 1 else 'colores revisados'} "
                                 "con una simulación de la tinta (perfil CMYK genérico)."))

    # ------------------------------------------------------------------ tipografías
    st = secciones["tipografias"]
    fuentes = fuentes_pdf(pdf) if pdf.exists() else None
    if fuentes is None:
        st.append(item("info", "No se pudo revisar", "Falta pdffonts (viene con Poppler)."))
    else:
        sin = sorted({re.sub(r"^[A-Z]{6}\+", "", f["nombre"]) for f in fuentes if not f["incrustada"]})
        if sin:
            st.append(item("problema", f"{len(sin)} {'tipografía no está incrustada' if len(sin) == 1 else 'tipografías no están incrustadas'}",
                           ", ".join(sin[:6]) + ". La imprenta no tendría con qué dibujar ese texto.",
                           "Si vienen de una figura PDF, vuelve a exportarla incrustando las fuentes "
                           "(en matplotlib: plt.rcParams['pdf.fonttype'] = 42)."))
        bitmap = sorted({f["nombre"] for f in fuentes if de_mapa_de_bits(f)})
        if bitmap:
            st.append(item("problema", "Hay letra hecha de píxeles (Type 3 de mapa de bits)",
                           ", ".join(bitmap[:6]) + ": se verá dentada al imprimir en grande.",
                           "Instala las fuentes vectoriales de LaTeX (cm-super o lmodern) y vuelve a compilar."))
        if not sin and not bitmap:
            fams = sorted({re.sub(r"^[A-Z]{6}\+", "", f["nombre"]).split("-")[0] for f in fuentes})
            st.append(item("bien", "Todas las tipografías van dentro del PDF",
                           f"{len(fuentes)} {'fuente' if len(fuentes) == 1 else 'fuentes'} incrustadas"
                           + (f" ({', '.join(fams[:5])}{'…' if len(fams) > 5 else ''})." if fams else ".")))

    # ------------------------------------------------------------------ contenido
    sc2 = secciones["contenido"]
    if m:
        _revisar_contenido_modelo(sc2, m, nodos, pos, nombre)
    elif textos:
        rel = {}
        for t in textos:
            if es_relleno(t["texto"]) or es_ejemplo(t["texto"]):
                rel.setdefault(round(t["zona"]["y0"], 2), t)
        if rel:
            t = next(iter(rel.values()))
            sc2.append(item("aviso", "Queda texto de relleno o de ejemplo",
                            f"{len(rel)} {'línea' if len(rel) == 1 else 'líneas'}, por ejemplo en {_donde(t['zona'], paginas > 1)}.",
                            "Cámbialo por tu texto antes de imprimir.", zona=t["zona"], muestra=_corto(t["texto"])))
    _revisar_registro(sc2, comp, directorio, m, nodos, pos, nombre, tipo)
    if textos:
        _revisar_bordes(sc2, textos, w_bp, h_bp, nombre)
    if not any(i["nivel"] in ("problema", "aviso") for i in sc2):
        sc2.append(item("bien", "Sin textos de ejemplo ni citas sueltas", "Y nada demasiado cerca del borde."))

    # ------------------------------------------------------------------ resultado
    titulos = {"pagina": "Tamaño y páginas", "imagenes": "Imágenes", "letra": "Tamaño de letra",
               "contraste": "Contraste", "color": "Color al imprimir", "tipografias": "Tipografías",
               "contenido": "Contenido"}
    salida = []
    for k, items in secciones.items():
        if not items:
            continue
        items.sort(key=lambda x: ORDEN[x["nivel"]])
        niveles = {x["nivel"] for x in items}
        estado = next((n for n in ("problema", "aviso", "bien") if n in niveles), "info")
        salida.append({"id": k, "titulo": titulos[k], "estado": estado, "items": items})
    todos = [x for s in salida for x in s["items"]]
    return {
        "resumen": {"problemas": sum(1 for x in todos if x["nivel"] == "problema"),
                    "avisos": sum(1 for x in todos if x["nivel"] == "aviso"),
                    "bien": sum(1 for x in todos if x["nivel"] == "bien")},
        "papel": {"ancho_mm": round(w_mm, 1), "alto_mm": round(h_mm, 1), "nombre": nombre_tam, "paginas": paginas},
        "umbrales": {"ppi": ppi_bueno, "letra_minima": round(perfil["minimo_aviso"], 1),
                     "letra_texto": round(perfil["texto_aviso"], 1)},
        "clase": clase,
        "faltan": faltan, "secciones": salida,
    }


def _toca_borde(z: dict, tol: float = 0.002) -> bool:
    return z["x0"] <= tol or z["y0"] <= tol or z["x1"] >= 1 - tol or z["y1"] >= 1 - tol


# Margen al comparar tamaños: algunas familias se cargan algo reducidas (Helvetica al 95 %
# para igualar la altura de la x) y pdftohtml redondea al punto.
TOLERANCIA_LETRA = 0.94


def perfil_lectura(clase: str, escala: float, alto_mm: float) -> dict:
    """Tamaños de letra recomendados y cómo se nombra el documento, según su clase: un póster
    se lee a metro y medio, una presentación se proyecta y un documento se lee en la mano."""
    if clase == "presentacion":
        k = (alto_mm or 190.5) / 190.5
        return {"clase": clase, "Nombre": "Presentación", "un": "una presentación", "El": "La presentación",
                "este": "esta presentación", "todo": "toda la presentación", "lectura": "desde el fondo de la sala",
                "minimo_malo": 9 * k, "minimo_aviso": 12 * k, "texto_aviso": 16 * k}
    if clase in ("documento", "paper", "tesis"):
        return {"clase": clase, "Nombre": M.CLASES[clase]["nombre"], "un": "un documento", "El": "El documento",
                "este": "este documento", "todo": "todo el documento", "lectura": "en papel",
                "minimo_malo": 5.5, "minimo_aviso": 7.0, "texto_aviso": 9.5}
    return {"clase": "poster", "Nombre": "Póster", "un": "un póster", "El": "El póster", "este": "este póster",
            "todo": "todo el póster", "lectura": "a metro y medio",
            "minimo_malo": max(6.0, 12 * escala), "minimo_aviso": max(7.0, 18 * escala),
            "texto_aviso": max(9.0, 24 * escala)}


def _revisar_letra(sl: list, textos: list[dict], perfil: dict, nombre, pos: _Posiciones):
    minimo_malo, minimo_aviso, texto_aviso = perfil["minimo_malo"], perfil["minimo_aviso"], perfil["texto_aviso"]
    lectura, este = perfil["lectura"], perfil["este"]
    tol = TOLERANCIA_LETRA
    # tamaño del texto principal: el que más caracteres tiene, sin contar figuras, pies
    # de figura, cabecera ni pie del póster
    cuenta: dict[float, int] = {}
    for t in textos:
        if not t["figura"] and t.get("grupo") != "imagen" and t.get("tipo_nodo") not in ("cabecera", "pie"):
            cuenta[t["tam"]] = cuenta.get(t["tam"], 0) + len(t["texto"])
    if not cuenta:
        for t in textos:
            if not t["figura"]:
                cuenta[t["tam"]] = cuenta.get(t["tam"], 0) + len(t["texto"])
    if cuenta:
        principal = max(cuenta, key=lambda k: cuenta[k])
        if principal < texto_aviso * tol:
            sl.append(item("aviso", f"El texto principal mide {_num(principal)} pt",
                           f"Para leerlo cómodamente {lectura}, en {perfil['un']} de este tamaño conviene "
                           f"{_num(texto_aviso)} pt o más.",
                           "Sube «Tamaño de letra» en la pestaña Diseño (o recorta texto para que quepa)."))
        else:
            sl.append(item("bien", f"Texto principal de {_num(principal)} pt",
                           f"Se lee bien {lectura} (conviene {_num(texto_aviso)} pt o más)."))
    # lo más pequeño de cada parte (sin superíndices ni subíndices sueltos)
    peores: dict[tuple, dict] = {}
    for t in textos:
        if len(t["texto"].replace(" ", "")) < 3:
            continue
        clave = (t["nodo"] or f"zona-{round(t['zona']['x0'], 1)}-{round(t['zona']['y0'], 1)}", t["figura"])
        if clave not in peores or t["tam"] < peores[clave]["tam"]:
            peores[clave] = t
    malos = sorted((t for t in peores.values() if t["tam"] < minimo_aviso * tol), key=lambda t: t["tam"])
    for t in malos[:10]:
        nivel = "problema" if t["tam"] < minimo_malo * tol else "aviso"
        z = pos.cajas.get(t["nodo"]) if t["nodo"] else None
        donde = nombre(t["nodo"], t["zona"])
        if t["figura"]:
            sl.append(item(nivel, f"Letra de {_num(t['tam'])} pt dentro de la figura de {donde}",
                           f"Lo más pequeño que se lee {lectura} en {este} es {_num(minimo_aviso)} pt.",
                           "Vuelve a hacer la figura con letra más grande (en matplotlib, plt.rcParams['font.size'] = 14 "
                           "o más) o ponla más ancha.",
                           elemento=t["nodo"], zona=t["zona"], muestra=_corto(t["texto"], 50), tam=t["tam"]))
        else:
            sl.append(item(nivel, f"Letra de {_num(t['tam'])} pt en {donde}",
                           f"Lo más pequeño que se lee {lectura} en {este} es {_num(minimo_aviso)} pt.",
                           f"Sube la escala de esa parte (inspector) o el «Tamaño de letra» de {perfil['todo']}.",
                           elemento=t["nodo"], zona=z or t["zona"], muestra=_corto(t["texto"], 50), tam=t["tam"]))
    if len(malos) > 10:
        sl.append(item("info", f"Y {len(malos) - 10} partes más con letra pequeña"))
    if cuenta and not malos:
        menor = min((t["tam"] for t in peores.values()), default=None)
        if menor is not None:
            sl.append(item("bien", "Ningún texto es demasiado pequeño",
                           f"Lo más pequeño mide {_num(menor)} pt (mínimo recomendado: {_num(minimo_aviso)} pt)."))


def _revisar_contraste(sc: list, textos: list[dict], pdf: Path, tam_pagina: dict, nombre, escala: float):
    paginas = sorted({t["pagina"] for t in textos})[:3]
    vistos: dict[tuple, dict] = {}
    peor = None
    revisados = 0
    for num in paginas:
        w, h = tam_pagina.get(num, (2384.0, 3370.0))
        ppp = max(20.0, min(110.0, 1700 / (max(w, h) / 72)))
        img = renderizar(pdf, num, ppp)
        if img is None:
            sc.append(item("info", "No se pudo revisar", "Falta pdftoppm (viene con Poppler) o Pillow."))
            return
        k = ppp / 72
        for t in textos:
            # dentro de las figuras no: sus rótulos girados salen a trozos y con la caja
            # mal puesta, y los colores son cosa de quien hizo la figura
            if t["pagina"] != num or t["figura"] or len(t["texto"].replace(" ", "")) < 3:
                continue
            caja = (int(t["x0"] * k), int(t["y0"] * k), int(math.ceil(t["x1"] * k)), int(math.ceil(t["y1"] * k)))
            fondo = fondo_detras(img, caja, t["color"])
            if fondo is None:
                continue
            revisados += 1
            r = contraste(t["color"], fondo)
            t["contraste"] = r
            if peor is None or r < peor:
                peor = r
            grande = t["tam"] >= max(24.0, 36 * escala)          # títulos: basta con 3:1
            limite_aviso, limite_mal = (3.0, 2.0) if grande else (4.5, 3.0)
            if r >= limite_aviso:
                continue
            clave = (t["nodo"] or f"{round(t['zona']['x0'], 1)}-{round(t['zona']['y0'], 1)}", _hex(t["color"]), _hex(fondo))
            if clave not in vistos or r < vistos[clave]["r"]:
                vistos[clave] = {"r": r, "t": t, "fondo": fondo, "mal": r < limite_mal, "grande": grande}
    lista = sorted(vistos.values(), key=lambda x: x["r"])
    for v in lista[:10]:
        t = v["t"]
        sc.append(item("problema" if v["mal"] else "aviso",
                       f"Contraste de {_num(v['r'], 1)}:1 en {nombre(t['nodo'], t['zona'])}",
                       f"Texto {_hex(t['color'])} sobre {_hex(v['fondo'])}"
                       + (" (letra grande: conviene 3:1 o más)." if v["grande"] else " (conviene 4,5:1 o más)."),
                       "Oscurece el texto o aclara el fondo (o al revés). Al imprimir, los colores pierden algo de contraste.",
                       elemento=t["nodo"], zona=t["zona"], muestra=_corto(t["texto"], 50), contraste=round(v["r"], 2),
                       color_texto=_hex(t["color"]), color_fondo=_hex(v["fondo"])))
    if len(lista) > 10:
        sc.append(item("info", f"Y {len(lista) - 10} textos más con poco contraste"))
    if revisados and not lista:
        sc.append(item("bien", "Todo el texto se distingue bien de su fondo",
                       f"El menor contraste es {_num(peor, 1)}:1 (conviene 4,5:1 o más)."))


def _revisar_contenido_modelo(sc: list, m: dict, nodos: dict, pos: _Posiciones, nombre):
    textos = textos_modelo(m)
    # textos de ejemplo: los de relleno, los del asistente y los que traen los elementos al crearlos
    defectos = {}
    for v in V.VARIANTES:
        for c in v["campos"]:
            d = c.get("defecto")
            if c["tipo"] in ("texto", "parrafo") and isinstance(d, str) and len(d.strip()) > 3 \
                    and d.strip().lower() not in DEFECTOS_VALIDOS:
                defectos[(v["clave"], c["nombre"])] = d.strip()
    tipo_de = {}
    for _, e in M.recorrer_elementos(m):
        tipo_de[e["id"]] = e.get("tipo")
    hallados: dict[str, str] = {}
    for ident, campo, texto in textos:
        if ident in hallados:
            continue
        por_defecto = defectos.get((tipo_de.get(ident), campo)) == texto.strip()
        if es_relleno(texto) or es_ejemplo(texto) or por_defecto:
            hallados[ident] = texto
    for ident, texto in list(hallados.items())[:12]:
        sc.append(item("aviso", f"Texto de ejemplo en {nombre(ident)}",
                       "Es el texto que trae la plantilla o el elemento al crearlo.",
                       "Escribe el tuyo (doble clic sobre el póster) o quita el elemento.",
                       elemento=ident, zona=pos.cajas.get(ident), muestra=_corto(texto)))
    if len(hallados) > 12:
        sc.append(item("info", f"Y {len(hallados) - 12} partes más con texto de ejemplo"))
    # citas a referencias que no existen
    from ..documento import generador
    try:
        ctx = generador.preparar_citas(copy.deepcopy(m))
    except Exception:          # noqa: BLE001 (una referencia rara no debe tumbar la revisión)
        ctx = None
    desconocidas = set(getattr(ctx, "desconocidas", []) or [])
    if desconocidas:
        donde: dict[str, list] = {}
        for ident, _, texto in textos:
            for grupo in re.findall(r"\[([^\]]*@[^\]]*)\]", texto):
                for clave in re.findall(r"@([^\s;,\]]+)", grupo):
                    if clave in desconocidas:
                        donde.setdefault(clave, []).append(ident)
        for clave in sorted(desconocidas)[:10]:
            ids = donde.get(clave) or [None]
            sc.append(item("problema", f"La cita @{clave} no tiene referencia",
                           f"Está en {nombre(ids[0])}; en el póster sale marcada como cita desconocida." if ids[0]
                           else "En el póster sale marcada como cita desconocida.",
                           "Añade la referencia en la pestaña Referencias o corrige la clave.",
                           elemento=ids[0], zona=pos.cajas.get(ids[0]) if ids[0] else None))


def _revisar_registro(sc: list, comp: dict, directorio: Path, m: dict | None, nodos: dict, pos: _Posiciones,
                      nombre, tipo: str):
    """Líneas que se salen de su sitio (Overfull \\hbox) y referencias sin resolver (proyectos LaTeX)."""
    mapa, lineas = {}, []
    desbordes = []
    for a in comp.get("avisos") or []:
        mo = re.search(r"Overfull \\hbox \(([\d.]+)pt too wide\).*?lines? (\d+)", str(a.get("mensaje")))
        if mo and float(mo.group(1)) > 3:
            desbordes.append((float(mo.group(1)), int(mo.group(2))))
    if desbordes and m:
        from ..documento import generador
        try:
            _, mapa = generador.generar(m, marcas=True)
        except Exception:      # noqa: BLE001
            mapa = {}
    vistos = set()
    for cuanto, linea in sorted(desbordes, reverse=True):
        ident = None
        for k in range(linea, max(0, linea - 4), -1):
            if mapa.get(k):
                ident = mapa[k]
                break
        if ident in vistos:
            continue
        vistos.add(ident)
        mm = cuanto * MM_POR_PT
        sc.append(item("aviso", f"Una línea se sale {_num(mm, 1 if mm < 10 else 0)} mm de su sitio"
                       + (f" en {nombre(ident)}" if ident in nodos else f" (línea {linea} del código)"),
                       "Suele ser una palabra muy larga, una dirección web o una fórmula que no se puede partir.",
                       "Parte la palabra o la dirección, o dale más ancho a esa parte.",
                       elemento=ident if ident in nodos else None, zona=pos.cajas.get(ident) if ident else None))
        if len(vistos) >= 6:
            break
    if tipo != "estructurado":
        log = directorio / "build" / (Path(comp.get("principal") or "poster.tex").stem + ".log")
        try:
            texto = log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            texto = ""
        citas = sorted(set(re.findall(r"Citation [`']([^']+)' on page \d+ undefined", texto)))
        refs = sorted(set(re.findall(r"Reference [`']([^']+)' on page \d+ undefined", texto)))
        if citas:
            sc.append(item("problema", f"{len(citas)} {'cita sin referencia' if len(citas) == 1 else 'citas sin referencia'}",
                           ", ".join(citas[:8]) + ": en el PDF salen como [?].",
                           "Revisa las claves y el archivo .bib, y compila otra vez."))
        if refs:
            sc.append(item("problema", f"{len(refs)} {'referencia cruzada sin resolver' if len(refs) == 1 else 'referencias cruzadas sin resolver'}",
                           ", ".join(refs[:8]) + ": en el PDF salen como ??.",
                           "Revisa las etiquetas (\\label y \\ref) y compila otra vez."))


def _revisar_bordes(sc: list, textos: list[dict], w_bp: float, h_bp: float, nombre):
    if not w_bp or not h_bp:
        return
    limite = 5 / MM_POR_BP                       # 5 mm en pt del PDF
    cerca = []
    for t in textos:
        d = min(t["x0"], t["y0"], w_bp - t["x1"], h_bp - t["y1"])
        if d < limite:
            cerca.append((d, t))
    if cerca:
        d, t = min(cerca, key=lambda x: x[0])
        sc.append(item("aviso", f"Hay texto a {_num(max(0.0, d * MM_POR_BP), 1)} mm del borde del papel",
                       f"{len(cerca)} {'trozo' if len(cerca) == 1 else 'trozos'} de texto a menos de 5 mm del borde, "
                       f"por ejemplo en {nombre(t['nodo'], t['zona'])}. Al cortar el papel se pueden perder.",
                       "Aléjalo del borde o aumenta el margen del lienzo.",
                       elemento=t["nodo"], zona=t["zona"], muestra=_corto(t["texto"], 50)))
