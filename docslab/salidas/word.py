# SPDX-License-Identifier: AGPL-3.0-only
"""Exportar un documento, artículo o tesis a Word (.docx), todo editable.

Se escribe desde el modelo (no desde el PDF), con los estilos de Word, para que se pueda seguir
trabajando en Word: títulos con «Título 1, 2, 3…» (y el índice se rehace solo), párrafos, listas,
tablas de Word, figuras con su pie numerado (campo SEQ, así funciona el índice de figuras), citas y
bibliografía en el estilo del proyecto, encabezado y número de página.

Ecuaciones: con pandoc, ecuaciones de Word (OMML) editables; sin pandoc, una imagen de cada
fórmula (hecha con LaTeX) con su código como texto alternativo.

Lo que no tiene equivalente en Word (código LaTeX libre, componentes propios, imágenes anotadas
con flechas) va como una imagen recortada del PDF compilado, en su sitio.
"""
from __future__ import annotations

import copy
import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from ..documento import bibliografia as B, texto as T, variantes as V
from ..nucleo import modelo as M

CLASES = ("documento", "paper", "tesis")
FUENTES_WORD = {"helvetica": "Arial", "avantgarde": "Century Gothic", "palatino": "Palatino Linotype",
                "times": "Times New Roman", "bookman": "Bookman Old Style", "charter": "Georgia"}
IDIOMAS = {"es": "es-ES", "en": "en-US", "pt": "pt-BR", "fr": "fr-FR", "de": "de-DE", "it": "it-IT", "ca": "ca-ES"}
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


class ErrorWord(ValueError):
    pass


def disponible() -> dict:
    import importlib.util
    return {"docx": importlib.util.find_spec("docx") is not None, "pandoc": bool(shutil.which("pandoc"))}


def _mm(v, defecto: float) -> float:
    """«25mm», «2.5cm», «1in», «72pt» → mm."""
    m = re.match(r"^\s*([\d.]+)\s*(mm|cm|in|pt)?\s*$", str(v or ""))
    if not m:
        return defecto
    n, u = float(m.group(1)), (m.group(2) or "mm")
    return n * {"mm": 1, "cm": 10, "in": 25.4, "pt": 25.4 / 72}[u]


# ======================================================================= texto con marcado
class Trozo:
    """Un trozo de texto con estilo, o una fórmula, o un salto de línea."""
    __slots__ = ("texto", "b", "i", "sup", "sub", "code", "mate", "salto", "smallcaps")

    def __init__(self, texto="", b=False, i=False, sup=False, sub=False, code=False, mate=False, salto=False,
                 smallcaps=False):
        self.texto, self.b, self.i, self.sup, self.sub = texto, b, i, sup, sub
        self.code, self.mate, self.salto, self.smallcaps = code, mate, salto, smallcaps

    def con(self, **k):
        t = copy.copy(self)
        for a, v in k.items():
            setattr(t, a, v)
        return t


_ORDEN_LATEX = re.compile(r"\\(?P<orden>PCcitasup|PCcita|PCcitadesconocida|textbf|textit|emph|textsuperscript|textsubscript|"
                          r"texttt|codigo|textsc)\s*\{")


def _llave(s: str, i: int) -> int:
    """Índice de la llave que cierra la que abre en s[i-1]."""
    prof = 1
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            prof += 1
        elif c == "}":
            prof -= 1
            if prof == 0:
                return i
        i += 1
    return len(s)


def _plano_latex(s: str) -> str:
    """LaTeX → texto, conservando los espacios de los extremos (separan de lo que viene al lado)."""
    if not s:
        return ""
    t = B.latex_a_texto(s)
    if s[:1].isspace() and t:
        t = " " + t
    if s[-1:].isspace() and t:
        t = t + " "
    return t if t.strip() else (" " if s.strip() == "" and s else t)


def trozos_latex(s: str, base: Trozo | None = None) -> list[Trozo]:
    """LaTeX en línea → trozos: negrita, cursiva, sup/sub, citas, $fórmulas$; el resto, como texto."""
    base = base or Trozo()
    salida: list[Trozo] = []
    pos = 0
    patron = re.compile(r"(?<!\\)\$(?P<m>[^$]+?)\$|\\\((?P<m2>.+?)\\\)|" + _ORDEN_LATEX.pattern + r"|\\\\|\\newline\b")
    for mo in patron.finditer(s):
        if mo.start() < pos:
            continue
        if mo.start() > pos:
            salida.append(base.con(texto=_plano_latex(s[pos:mo.start()])))
        if mo.group("m") is not None or mo.group("m2") is not None:
            salida.append(base.con(texto=mo.group("m") if mo.group("m") is not None else mo.group("m2"), mate=True))
            pos = mo.end()
            continue
        if mo.group(0) in ("\\\\", "\\newline"):
            salida.append(Trozo(salto=True))
            pos = mo.end()
            continue
        orden = mo.group("orden")
        fin = _llave(s, mo.end())
        dentro = s[mo.end():fin]
        pos = fin + 1
        if orden == "PCcita":
            salida.append(base.con(texto=_plano_latex(dentro)))
        elif orden == "PCcitasup":
            salida.append(base.con(texto=_plano_latex(dentro), sup=True))
        elif orden == "PCcitadesconocida":
            salida.append(base.con(texto=f"[?{_plano_latex(dentro)}]", b=True))
        elif orden == "textbf":
            salida += trozos_latex(dentro, base.con(b=True))
        elif orden in ("textit", "emph"):
            salida += trozos_latex(dentro, base.con(i=not base.i))
        elif orden == "textsuperscript":
            salida += trozos_latex(dentro, base.con(sup=True))
        elif orden == "textsubscript":
            salida += trozos_latex(dentro, base.con(sub=True))
        elif orden in ("texttt", "codigo"):
            salida.append(base.con(texto=_plano_latex(dentro), code=True))
        elif orden == "textsc":
            salida += trozos_latex(dentro, base.con(smallcaps=True))
    if pos < len(s):
        salida.append(base.con(texto=_plano_latex(s[pos:])))
    return [t for t in salida if t.salto or t.mate or t.texto]


def trozos_simple(s: str, base: Trozo | None = None) -> list[Trozo]:
    """El marcado sencillo de DocsLab (**negrita**, *cursiva*, ^sup^, ~sub~, `código`, $mate$, {{LaTeX}})."""
    base = base or Trozo()
    salida: list[Trozo] = []
    for crudo, parte in T._trozos_crudos(s):
        if crudo:
            salida += trozos_latex(parte, base)
            continue
        pos = 0
        for mo in T._MARCADO.finditer(parte):
            if mo.start() > pos:
                salida.append(base.con(texto=parte[pos:mo.start()]))
            tipo, valor = mo.lastgroup, mo.group(mo.lastgroup)
            if tipo == "mate":
                salida.append(base.con(texto=valor, mate=True))
            elif tipo == "codigo":
                salida.append(base.con(texto=valor, code=True))
            elif tipo == "negrita":
                salida += trozos_simple(valor, base.con(b=True))
            elif tipo == "cursiva":
                salida += trozos_simple(valor, base.con(i=not base.i))
            elif tipo == "sup":
                salida += trozos_simple(valor, base.con(sup=True))
            elif tipo == "sub":
                salida += trozos_simple(valor, base.con(sub=True))
            pos = mo.end()
        if pos < len(parte):
            salida.append(base.con(texto=parte[pos:]))
    return [t for t in salida if t.salto or t.mate or t.texto]


def parrafos(texto, formato: str, separar: bool = True) -> list[list[Trozo]]:
    """Un campo de texto → párrafos (listas de trozos). Una línea en blanco separa párrafos;
    un salto de línea simple corta la línea."""
    if texto is None:
        return []
    texto = str(texto).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not texto:
        return []
    bloques = [b for b in re.split(r"\n\s*\n", texto) if b.strip()] if separar else [texto]
    salida = []
    for b in bloques:
        if formato == "latex":
            b = re.sub(r"\s*\n\s*", " ", b.strip())
            salida.append(trozos_latex(b))
            continue
        lineas = [ln.strip() for ln in b.split("\n") if ln.strip()]
        trozos: list[Trozo] = []
        for n, ln in enumerate(lineas):
            if n:
                trozos.append(Trozo(salto=True))
            trozos += trozos_simple(ln)
        salida.append(trozos)
    return salida


def formulas_de(m: dict) -> list[tuple[str, bool]]:
    """Todas las fórmulas del documento (código, en bloque), sin repetir, para convertirlas de una vez."""
    vistas, lista = set(), []

    def mirar(t, _p):
        for par in parrafos(t, m.get("formato_texto", "simple")):
            for tr in par:
                if tr.mate and (tr.texto, False) not in vistas:
                    vistas.add((tr.texto, False))
                    lista.append((tr.texto, False))
        return t
    M.transformar_textos(copy.deepcopy(m), mirar)
    for b in M.bloques_de_flujo(m):
        for e in b.get("elementos") or []:
            if e.get("tipo") == "txtEcuacion" and str(e.get("ecuacion") or "").strip():
                clave = (_limpiar_ecuacion(e["ecuacion"]), True)
                if clave not in vistas:
                    vistas.add(clave)
                    lista.append(clave)
    return lista


def _limpiar_ecuacion(s: str) -> str:
    """Una ecuación en bloque sin sus delimitadores (\\[ \\], $$, equation…)."""
    s = str(s).strip()
    for a, b in (("\\[", "\\]"), ("$$", "$$"), ("\\begin{equation*}", "\\end{equation*}"),
                 ("\\begin{equation}", "\\end{equation}"), ("$", "$")):
        if s.startswith(a) and s.endswith(b) and len(s) > len(a) + len(b):
            return s[len(a):-len(b)].strip()
    return s


# ======================================================================= fórmulas
class Formulas:
    """Convierte las fórmulas: con pandoc a OMML (ecuaciones de Word); si no, a imagen (LaTeX)."""

    def __init__(self, preambulo: str = ""):
        self.omml: dict[tuple[str, bool], object] = {}
        self.png: dict[tuple[str, bool], tuple[bytes, float, float]] = {}   # (png, ancho pt, alto pt)
        self.preambulo = preambulo
        self.pandoc = shutil.which("pandoc")

    def preparar(self, lista: list[tuple[str, bool]]):
        if not lista:
            return
        if self.pandoc:
            self._con_pandoc(lista)
        faltan = [f for f in lista if f not in self.omml]
        if faltan:
            self._con_latex(faltan)

    def _con_pandoc(self, lista):
        from lxml import etree
        # una fórmula que cierra su $ o \\] podría colar texto fuera de las matemáticas: esa va como imagen
        lista = [f for f in lista if not re.search(r"(?<!\\)\$|\\\]|\\\)|XXFINXX", f[0])]
        if not lista:
            return
        partes = []
        for codigo, bloque in lista:
            partes.append(("\\[" + codigo + "\\]") if bloque else ("$" + codigo + "$"))
        fuente = "\n\nXXFINXX\n\n".join(partes)
        with tempfile.TemporaryDirectory(prefix="pl-omml-") as tmp:
            entrada, salida = Path(tmp) / "f.tex", Path(tmp) / "f.docx"
            entrada.write_text(fuente, encoding="utf-8")
            try:
                orden = [self.pandoc, "--sandbox", "-f", "latex", "-t", "docx", "-o", str(salida), str(entrada)]
                r = subprocess.run(orden, capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
                if r.returncode != 0:
                    # pandoc anterior a 2.15 no conoce --sandbox, y algunos 3.x no encuentran con él sus
                    # plantillas de docx. Sin él también es seguro: solo le llegan fórmulas sueltas (que pandoc
                    # no expande) y las que intentan salir de las matemáticas se han quitado arriba.
                    orden.remove("--sandbox")
                    r = subprocess.run(orden, capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
                if r.returncode != 0:
                    return
                xml = zipfile.ZipFile(salida).read("word/document.xml")
            except (subprocess.SubprocessError, OSError, KeyError, zipfile.BadZipFile):
                return
        cuerpo = etree.fromstring(xml).find(f"{{{NS_W}}}body")
        grupos, actual = [], []
        for p in cuerpo:
            texto = "".join(p.itertext())
            if texto.strip() == "XXFINXX":
                grupos.append(actual)
                actual = []
            elif p.tag == f"{{{NS_W}}}p":
                actual.append(p)
        grupos.append(actual)
        if len(grupos) != len(lista):
            return
        for clave, ps in zip(lista, grupos):
            mates = [x for p in ps for x in p.iter(f"{{{NS_M}}}oMathPara", f"{{{NS_M}}}oMath")]
            if not mates:
                continue
            principal = mates[0]
            if clave[1] and principal.tag == f"{{{NS_M}}}oMath":
                envoltorio = etree.Element(f"{{{NS_M}}}oMathPara")
                envoltorio.append(principal)
                principal = envoltorio
            if not clave[1] and principal.tag == f"{{{NS_M}}}oMathPara":
                principal = principal.find(f"{{{NS_M}}}oMath")
            if principal is not None:
                self.omml[clave] = principal

    def _con_latex(self, lista):
        """Una página por fórmula (preview), con pdfLaTeX, y cada página a PNG con PyMuPDF."""
        from . import compilador
        exe = compilador.pdflatex()
        if not exe:
            return
        try:
            import pymupdf
        except ImportError:
            return
        for preambulo in (self.preambulo, ""):
            cuerpo = "\n".join(("\\begin{preview}$\\displaystyle " if b else "\\begin{preview}$") + c + "$\\end{preview}"
                               for c, b in lista)
            tex = ("\\documentclass[10pt]{article}\\usepackage{amsmath,amssymb}\\usepackage[active,tightpage]{preview}"
                   "\\setlength\\PreviewBorder{1pt}\n" + preambulo + "\n\\begin{document}\n" + cuerpo + "\n\\end{document}\n")
            with tempfile.TemporaryDirectory(prefix="pl-formulas-") as tmp:
                (Path(tmp) / "f.tex").write_text(tex, encoding="utf-8")
                r = subprocess.run([exe, "-interaction=nonstopmode", "-no-shell-escape", "f.tex"], cwd=tmp,
                                   capture_output=True, timeout=180, stdin=subprocess.DEVNULL)
                pdf = Path(tmp) / "f.pdf"
                if r.returncode != 0 or not pdf.exists():
                    continue
                doc = pymupdf.open(str(pdf))
                if len(doc) != len(lista):
                    continue
                for clave, pg in zip(lista, doc):
                    pix = pg.get_pixmap(dpi=300, alpha=True)
                    self.png[clave] = (pix.tobytes("png"), pg.rect.width, pg.rect.height)
                return


# ======================================================================= el documento
class Exportador:
    def __init__(self, m: dict, dir_proyecto: Path, pdf: Path | None = None, posiciones: dict | None = None,
                 informar=None):
        if m.get("clase") not in CLASES:
            raise ErrorWord("Word está disponible para documentos, artículos y tesis.")
        from ..documento import generador as G
        self.m = M.normalizar(copy.deepcopy(m))
        self.ctx = G.preparar_citas(self.m)           # cambia [@clave] por la cita (como en el PDF)
        self._numero = G.numero
        self.dir = Path(dir_proyecto)
        self.pdf, self.pos = pdf, posiciones or {}
        self.informar = informar or (lambda *a, **k: None)
        self.fmt = self.m.get("formato_texto", "simple")
        self.doc_cfg = self.m.get("documento") or {}
        self.tesis = self.m["clase"] == "tesis"
        self.cont = {"figura": 0, "tabla": 0, "imagenes": 0, "ecuaciones": 0, "recortes": 0, "tablas": 0}
        self.avisos: list[str] = []
        self.secciones = [0, 0, 0, 0, 0]
        self.capitulo_apendice = 0

    # ------------------------------------------------------------------ estilos
    def _estilos(self):
        from docx.enum.text import WD_LINE_SPACING
        from docx.shared import Pt, RGBColor
        m, tipo = self.m, self.m.get("tipografia") or {}
        self.fuente = self._familia(tipo.get("familia"))
        self.fuente_titulos = self._familia(tipo.get("familia_titulos")) if tipo.get("familia_titulos") else self.fuente
        self.tam = float(tipo.get("fuente") or 11)
        colores = m.get("colores") or {}
        self.color_primario = RGBColor.from_string(str(colores.get("primario") or "1F3864")[:6].upper())
        self.color_texto = RGBColor.from_string(str(colores.get("texto") or "000000")[:6].upper())
        self.color_tenue = RGBColor.from_string(str(colores.get("tenue") or "595959")[:6].upper())
        self.color_fondo_caja = str(colores.get("fondo_bloque") or "F2F2F2")[:6].upper()
        idioma = IDIOMAS.get(m.get("idioma") or "es", "es-ES")
        st = self.d.styles
        normal = st["Normal"]
        normal.font.name = self.fuente
        normal.font.size = Pt(self.tam)
        normal.font.color.rgb = self.color_texto
        self._fuente_xml(normal, self.fuente, idioma)
        pf = normal.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        pf.line_spacing = float(tipo.get("interlinea") or 1.25)
        if self.doc_cfg.get("parrafos") == "sangria":
            pf.first_line_indent = Pt(self.tam * 1.5)
            pf.space_after = Pt(0)
        else:
            pf.space_after = Pt(self.tam * 0.6)
        esc_sec = float(self.doc_cfg.get("escala_seccion") or 1.4)
        esc_cap = float(self.doc_cfg.get("escala_capitulo") or 2.2)
        tams = [esc_cap if self.tesis else esc_sec, esc_sec if self.tesis else 1.2, 1.15, 1.05, 1.0]
        for n in range(1, 6):
            h = st[f"Heading {n}"]
            h.font.name = self.fuente_titulos
            self._fuente_xml(h, self.fuente_titulos, idioma)
            h.font.size = Pt(round(self.tam * tams[n - 1], 1))
            h.font.bold = True
            h.font.italic = False
            h.font.color.rgb = self.color_primario
            h.paragraph_format.first_line_indent = Pt(0)
            h.paragraph_format.space_before = Pt(self.tam * (1.6 if n == 1 else 1.1))
            h.paragraph_format.space_after = Pt(self.tam * 0.5)
            h.paragraph_format.keep_with_next = True
        for nombre, escala, color in (("Title", 2.1, self.color_primario), ("Subtitle", 1.25, self.color_tenue)):
            s = st[nombre]
            s.font.name = self.fuente_titulos
            self._fuente_xml(s, self.fuente_titulos, idioma)
            s.font.size = Pt(round(self.tam * escala, 1))
            s.font.color.rgb = color
            s.font.bold = nombre == "Title"
            s.font.italic = False
            s.paragraph_format.first_line_indent = Pt(0)
            s.paragraph_format.alignment = 1
            self._sin_borde(s)
        cap = st["Caption"]
        cap.font.name = self.fuente
        cap.font.size = Pt(round(self.tam * 0.9, 1))
        cap.font.italic = False
        cap.font.bold = False
        cap.font.color.rgb = self.color_tenue
        cap.paragraph_format.first_line_indent = Pt(0)
        cap.paragraph_format.space_after = Pt(self.tam * 0.9)
        for nombre in ("List Bullet", "List Number", "Quote", "Intense Quote", "No Spacing"):
            st[nombre].paragraph_format.first_line_indent = None if nombre.startswith("List") else Pt(0)

    def _familia(self, clave) -> str:
        if not clave:
            return "Palatino Linotype"
        info = M.FAMILIAS_INFO.get(clave)
        if info:
            return FUENTES_WORD.get(clave, info["nombre"])
        return str(clave)                     # una tipografía propia: su nombre de familia

    @staticmethod
    def _fuente_xml(estilo, nombre: str, idioma: str):
        from docx.oxml.ns import qn
        rpr = estilo.element.get_or_add_rPr()
        fuentes = rpr.find(qn("w:rFonts"))
        if fuentes is None:
            fuentes = rpr.makeelement(qn("w:rFonts"), {})
            rpr.insert(0, fuentes)
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            fuentes.set(qn(a), nombre)
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
            if fuentes.get(qn(a)) is not None:
                del fuentes.attrib[qn(a)]
        lang = rpr.find(qn("w:lang"))
        if lang is None:
            lang = rpr.makeelement(qn("w:lang"), {})
            rpr.append(lang)
        lang.set(qn("w:val"), idioma)

    @staticmethod
    def _sin_borde(estilo):
        from docx.oxml.ns import qn
        ppr = estilo.element.find(qn("w:pPr"))
        if ppr is not None:
            for b in ppr.findall(qn("w:pBdr")):
                ppr.remove(b)

    # ------------------------------------------------------------------ página
    def _pagina(self):
        from docx.shared import Mm
        lz = self.m.get("lienzo") or {}
        s = self.d.sections[0]
        ancho, alto = _mm(lz.get("ancho"), 210), _mm(lz.get("alto"), 297)
        s.page_width, s.page_height = Mm(ancho), Mm(alto)
        margen = _mm(lz.get("margen"), 25)
        s.top_margin = Mm(_mm(lz.get("margen_superior"), margen) if lz.get("margen_superior") else margen)
        s.bottom_margin = Mm(_mm(lz.get("margen_inferior"), margen) if lz.get("margen_inferior") else margen)
        s.left_margin = Mm(_mm(lz.get("margen_izquierdo"), margen) if lz.get("margen_izquierdo") else margen)
        s.right_margin = Mm(_mm(lz.get("margen_derecho"), margen) if lz.get("margen_derecho") else margen)
        self.ancho_texto = s.page_width - s.left_margin - s.right_margin
        self.ancho_columna = self.ancho_texto
        if self.doc_cfg.get("numerar_paginas", True):
            p = s.footer.paragraphs[0]
            p.alignment = 1
            self._campo(p, "PAGE", "1")
        enc = str(self.doc_cfg.get("encabezado") or "").strip()
        if enc:
            p = s.header.paragraphs[0]
            p.alignment = 2
            self._escribir(p, [t.con(i=True) for par in parrafos(enc, self.fmt, False) for t in par])

    # ------------------------------------------------------------------ piezas de bajo nivel
    def _campo(self, p, instruccion: str, resultado: str = ""):
        """Un campo de Word (PAGE, SEQ Figura, TOC…) con su resultado ya puesto."""
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls
        from xml.sax.saxutils import escape
        instr = escape(instruccion, {'"': "&quot;"})
        p._p.append(parse_xml(f'<w:fldSimple {nsdecls("w")} w:instr=" {instr} "><w:r><w:t xml:space="preserve">'
                              f'{escape(resultado)}</w:t></w:r></w:fldSimple>'))

    def _escribir(self, p, trozos: list[Trozo], tam: float | None = None, color=None):
        from docx.shared import Pt
        for t in trozos:
            if t.salto:
                p.add_run().add_break()
                continue
            if t.mate:
                self._formula_en_linea(p, t.texto, tam)
                continue
            r = p.add_run(t.texto)
            f = r.font
            f.bold = t.b or None
            f.italic = t.i or None
            if t.sup:
                f.superscript = True
            if t.sub:
                f.subscript = True
            if t.smallcaps:
                f.small_caps = True
            if t.code:
                f.name = "Consolas"
            if tam:
                f.size = Pt(tam)
            if color is not None:
                f.color.rgb = color

    def _formula_en_linea(self, p, codigo: str, tam: float | None):
        from docx.shared import Pt
        clave = (codigo, False)
        if clave in self.formulas.omml:
            p._p.append(copy.deepcopy(self.formulas.omml[clave]))
            self.cont["ecuaciones"] += 1
        elif clave in self.formulas.png:
            datos, w, h = self.formulas.png[clave]
            esc = (tam or self.tam) / 10.0
            r = p.add_run()
            pic = r.add_picture(io.BytesIO(datos), width=Pt(w * esc), height=Pt(h * esc))
            self._alt(pic, codigo)
            self.cont["ecuaciones"] += 1
        else:
            r = p.add_run(codigo)
            r.font.italic = True

    @staticmethod
    def _alt(foto, texto: str):
        """Texto alternativo de una imagen (accesibilidad; en las fórmulas, su código LaTeX)."""
        from docx.oxml.ns import qn
        docpr = foto._inline.find(qn("wp:docPr"))
        if docpr is not None:
            docpr.set("descr", texto[:2000])

    def _parrafo(self, trozos=None, estilo: str | None = None, alinear: int | None = None, tam: float | None = None,
                 sin_sangria: bool = False, color=None):
        from docx.shared import Pt
        p = self.d.add_paragraph(style=estilo)
        if alinear is not None:
            p.alignment = alinear
        if sin_sangria:
            p.paragraph_format.first_line_indent = Pt(0)
        if trozos:
            self._escribir(p, trozos, tam, color)
        return p

    def _texto(self, valor, alinear: int | None = None, estilo: str | None = None, tam: float | None = None,
               sin_sangria=False):
        for par in parrafos(valor, self.fmt):
            self._parrafo(par, estilo, alinear, tam, sin_sangria)

    def _una_linea(self, valor) -> list[Trozo]:
        return [t for par in parrafos(valor, self.fmt, separar=False) for t in par]

    def _alineacion(self, alinear_modelo: str | None = None) -> int | None:
        a = alinear_modelo or (self.m.get("estilo") or {}).get("alinear_texto")
        return {"justificado": 3, "izquierda": 0, "centro": 1, "derecha": 2}.get(a)

    def _sombrear(self, p, fondo: str | None = None, borde: str | None = None, izquierda_solo: bool = False):
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls
        ppr = p._p.get_or_add_pPr()
        if borde:
            lados = ("left",) if izquierda_solo else ("top", "left", "bottom", "right")
            ppr.append(parse_xml(f'<w:pBdr {nsdecls("w")}>' + "".join(
                f'<w:{l} w:val="single" w:sz="{18 if izquierda_solo else 6}" w:space="6" w:color="{borde}"/>' for l in lados)
                + "</w:pBdr>"))
        if fondo:
            ppr.append(parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{fondo}"/>'))

    def _salto_pagina(self):
        from docx.enum.text import WD_BREAK
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ------------------------------------------------------------------ imágenes
    def _archivo(self, ruta) -> Path | None:
        if not ruta:
            return None
        from ..nucleo.almacen import unir
        try:
            p = unir(self.dir, str(ruta))
        except Exception:
            return None
        return p if p.is_file() else None

    def _bytes_imagen(self, ruta: Path) -> bytes | None:
        ext = ruta.suffix.lower()
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"):
            return ruta.read_bytes()
        if ext in (".pdf", ".eps", ".svg"):
            try:
                import pymupdf
                doc = pymupdf.open(str(ruta))
                return doc[0].get_pixmap(dpi=220, alpha=False).tobytes("png")
            except Exception:
                return None
        return None

    def _imagen(self, ruta, ancho_frac: float, alinear: int = 1, alt: str = ""):
        p = self._archivo(ruta)
        datos = self._bytes_imagen(p) if p else None
        if not datos:
            if ruta:
                self.avisos.append(f"No se pudo poner la imagen «{ruta}».")
            return None
        par = self.d.add_paragraph()
        par.alignment = alinear
        par.paragraph_format.first_line_indent = 0
        par.paragraph_format.keep_with_next = True
        foto = par.add_run().add_picture(io.BytesIO(datos), width=int(self.ancho_columna * max(0.05, min(1.0, ancho_frac))))
        self._alt(foto, alt or Path(str(ruta)).stem)
        self.cont["imagenes"] += 1
        return par

    def _rejilla_imagenes(self, rutas: list, columnas: int, ancho_frac: float, rotulos: list | None = None):
        """Varias imágenes en una tabla sin bordes (así quedan lado a lado y se pueden cambiar una a una)."""
        rutas = [r for r in rutas if r]
        if not rutas:
            return
        columnas = max(1, min(columnas, len(rutas)))
        filas = (len(rutas) + columnas - 1) // columnas
        tabla = self.d.add_table(rows=filas, cols=columnas)
        tabla.alignment = 1
        self._ancho_tabla(tabla, max(0.1, min(1.0, ancho_frac)))
        ancho_celda = int(self.ancho_columna * max(0.1, min(1.0, ancho_frac)) / columnas)
        for n, ruta in enumerate(rutas):
            celda = tabla.cell(n // columnas, n % columnas)
            p = celda.paragraphs[0]
            p.alignment = 1
            p.paragraph_format.first_line_indent = 0
            f = self._archivo(ruta)
            datos = self._bytes_imagen(f) if f else None
            if datos:
                foto = p.add_run().add_picture(io.BytesIO(datos), width=int(ancho_celda * 0.96))
                self._alt(foto, Path(str(ruta)).stem)
                self.cont["imagenes"] += 1
            etiqueta = (rotulos[n] if rotulos and n < len(rotulos) else None)
            if etiqueta:
                q = celda.add_paragraph()
                q.alignment = 1
                q.paragraph_format.first_line_indent = 0
                self._escribir(q, etiqueta, tam=self.tam * 0.9)

    def _recorte_pdf(self, ident: str, alt: str) -> bool:
        """La parte del PDF compilado donde está ese elemento, como imagen (lo que Word no sabe hacer)."""
        cajas = (self.pos or {}).get("cajas") or {}
        papel = (self.pos or {}).get("papel")
        c = cajas.get(ident)
        if not c or not papel or not self.pdf or not Path(self.pdf).exists():
            return False
        try:
            import pymupdf
        except ImportError:
            return False
        doc = pymupdf.open(str(self.pdf))
        n = int(c.get("pagina") or 1) - 1
        if n >= len(doc):
            return False
        pg = doc[n]
        fx, fy = pg.rect.width / papel["ancho"], pg.rect.height / papel["alto"]
        r = pymupdf.Rect(c["x0"] * fx - 2, c["y0"] * fy - 2, c["x1"] * fx + 2, c["y1"] * fy + 2) & pg.rect
        if r.is_empty or r.width < 2 or r.height < 2:
            return False
        datos = pg.get_pixmap(dpi=220, clip=r, alpha=False).tobytes("png")
        from docx.shared import Pt
        par = self.d.add_paragraph()
        par.alignment = 1
        par.paragraph_format.first_line_indent = 0
        ancho = min(Pt(r.width), self.ancho_columna)
        foto = par.add_run().add_picture(io.BytesIO(datos), width=ancho)
        self._alt(foto, alt)
        self.cont["recortes"] += 1
        return True

    def _pie(self, valor, tipo: str = "figura"):
        """Pie numerado (campo SEQ, como «Insertar título» de Word)."""
        trozos = self._una_linea(valor)
        estilo = self.m.get("estilo") or {}
        numerar = estilo.get("numerar_figuras", True) if tipo == "figura" else self.doc_cfg.get("numerar_tablas", True)
        if not trozos and not numerar:
            return
        p = self.d.add_paragraph(style="Caption")
        p.alignment = 1
        if numerar:
            self.cont[tipo] += 1
            nombre = (estilo.get("nombre_figura") or "Figura") if tipo == "figura" else (self.doc_cfg.get("nombre_tabla") or "Tabla")
            r = p.add_run(nombre + " ")
            r.font.bold = True
            self._campo(p, f"SEQ {'Figura' if tipo == 'figura' else 'Tabla'} \\* ARABIC", str(self.cont[tipo]))
            r = p.add_run(". " if trozos else "")
            r.font.bold = True
        self._escribir(p, trozos)
        if tipo == "tabla":
            p.paragraph_format.keep_with_next = True

    # ------------------------------------------------------------------ listas
    def _numeracion_nueva(self) -> int:
        """Un número de lista nuevo (para que cada lista numerada empiece en 1)."""
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls, qn
        numbering = self.d.part.numbering_part.element
        estilo = self.d.styles["List Number"].element
        num_id_estilo = estilo.find(".//" + qn("w:numId"))
        if num_id_estilo is None:
            return 0
        base = numbering.find(f"{qn('w:num')}[@{qn('w:numId')}='{num_id_estilo.get(qn('w:val'))}']")
        abstract = base.find(qn("w:abstractNumId")).get(qn("w:val"))
        nuevo = max(int(n.get(qn("w:numId"))) for n in numbering.findall(qn("w:num"))) + 1
        numbering.append(parse_xml(f'<w:num {nsdecls("w")} w:numId="{nuevo}"><w:abstractNumId w:val="{abstract}"/>'
                                   f'<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>'))
        return nuevo

    def _lista(self, items, numerada: bool = False, tam: float | None = None):
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls
        if isinstance(items, str):
            items = [x for x in items.replace("\r", "").split("\n") if x.strip()]
        num = self._numeracion_nueva() if numerada else 0
        for it in items or []:
            p = self._parrafo(self._una_linea(it), "List Number" if numerada else "List Bullet", tam=tam)
            if num:
                p._p.get_or_add_pPr().append(parse_xml(f'<w:numPr {nsdecls("w")}><w:ilvl w:val="0"/>'
                                                        f'<w:numId w:val="{num}"/></w:numPr>'))

    # ------------------------------------------------------------------ tabla
    @staticmethod
    def _antes_de_look(tbl_pr, el):
        """Los hijos de w:tblPr tienen un orden fijo: tblBorders va antes de tblLook."""
        from docx.oxml.ns import qn
        look = tbl_pr.find(qn("w:tblLook"))
        if look is not None:
            look.addprevious(el)
        else:
            tbl_pr.append(el)

    def _ancho_tabla(self, tabla, frac: float = 1.0):
        """La tabla, al ancho de la columna de texto (con dos columnas, al de una columna)."""
        from docx.oxml.ns import qn
        tbl_pr = tabla._tbl.tblPr
        w = tbl_pr.find(qn("w:tblW"))
        if w is not None:
            w.set(qn("w:type"), "pct")
            w.set(qn("w:w"), str(int(5000 * frac)))
        ancho = int(self.ancho_columna * frac)
        n = len(tabla.columns)
        for col in tabla.columns:
            col.width = ancho // n
        for fila in tabla.rows:
            for celda in fila.cells:
                celda.width = ancho // n

    def _tabla(self, t: dict, pie):
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls
        filas = [f for f in (t or {}).get("filas") or [] if isinstance(f, list)]
        if not filas:
            return
        if pie:
            self._pie(pie, "tabla")
        ncol = max(len(f) for f in filas)
        alin = [{"l": 0, "c": 1, "r": 2}.get(ch, 0) for ch in re.sub(r"[^lcrp]", "", str(t.get("columnas") or ""))]
        tabla = self.d.add_table(rows=len(filas), cols=ncol)
        tabla.alignment = 1
        # bordes al estilo científico: arriba, abajo y bajo el encabezado
        tbl_pr = tabla._tbl.tblPr
        self._ancho_tabla(tabla)
        self._antes_de_look(tbl_pr, parse_xml(f'<w:tblBorders {nsdecls("w")}><w:top w:val="single" w:sz="10" w:color="000000"/>'
                                f'<w:bottom w:val="single" w:sz="10" w:color="000000"/><w:insideH w:val="nil"/>'
                                f'<w:insideV w:val="nil"/><w:left w:val="nil"/><w:right w:val="nil"/></w:tblBorders>'))
        encabezado = t.get("encabezado", True)
        for i, fila in enumerate(filas):
            for j in range(ncol):
                celda = tabla.cell(i, j)
                p = celda.paragraphs[0]
                p.paragraph_format.first_line_indent = 0
                p.alignment = alin[j] if j < len(alin) else 0
                trozos = self._una_linea(fila[j] if j < len(fila) else "")
                if i == 0 and encabezado:
                    trozos = [x.con(b=True) for x in trozos]
                    celda._tc.get_or_add_tcPr().append(parse_xml(
                        f'<w:tcBorders {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:color="000000"/></w:tcBorders>'))
                self._escribir(p, trozos, tam=self.tam * 0.95)
        if encabezado:
            fila0 = tabla.rows[0]._tr.get_or_add_trPr()
            fila0.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
        self.d.add_paragraph().paragraph_format.space_after = 0
        self.cont["tablas"] += 1

    # ------------------------------------------------------------------ ecuación en bloque
    def _ecuacion(self, codigo: str):
        codigo = _limpiar_ecuacion(codigo)
        clave = (codigo, True)
        p = self.d.add_paragraph()
        p.alignment = 1
        p.paragraph_format.first_line_indent = 0
        if clave in self.formulas.omml:
            p._p.append(copy.deepcopy(self.formulas.omml[clave]))
        elif clave in self.formulas.png:
            from docx.shared import Pt
            datos, w, h = self.formulas.png[clave]
            esc = self.tam / 10.0
            foto = p.add_run().add_picture(io.BytesIO(datos), width=Pt(w * esc), height=Pt(h * esc))
            self._alt(foto, codigo)
        else:
            r = p.add_run(codigo)
            r.font.name = "Consolas"
        self.cont["ecuaciones"] += 1

    # ------------------------------------------------------------------ elementos
    def _elemento(self, e: dict):
        tipo = str(e.get("tipo") or "")
        v = V.POR_CLAVE.get(tipo)
        alt = T.texto_plano(e.get("pie") or e.get("titulo") or tipo, 120)
        if tipo.startswith("cmp:") or tipo == "latex" or tipo == "imgAnotada":
            if not self._recorte_pdf(e.get("id", ""), alt):
                if tipo == "imgAnotada":
                    self._imagen(e.get("archivo"), self._frac(e), alt=alt)
                else:
                    self.avisos.append("Un elemento de código LaTeX no se pudo pasar a Word (compila el documento primero).")
            if tipo == "imgAnotada":
                self._pie(e.get("pie"))
            return
        if not v:
            return
        g = v["grupo"]
        if tipo == "espacio":
            self.d.add_paragraph()
            return
        if tipo == "bibliografia":
            self._bibliografia(e)
            return
        if g == "imagen":
            self._elemento_imagen(e, v)
            return
        # --- texto y cajas
        just = self._alineacion()
        if tipo in ("txtJustificado", "txtDosColumnas", "txtTresColumnas", "txtDosColumnasFilete"):
            self._texto(e.get("texto"), just)
        elif tipo == "txtIzquierda":
            self._texto(e.get("texto"), 0)
        elif tipo == "txtDerecha":
            self._texto(e.get("texto"), 2)
        elif tipo in ("txtCentrado", "txtCirculo"):
            self._texto(e.get("texto"), 1, sin_sangria=True)
        elif tipo == "txtBanda":
            for par in parrafos(e.get("texto"), self.fmt):
                p = self._parrafo(par, alinear=1, sin_sangria=True, tam=self.tam * 1.2)
                self._sombrear(p, self.color_fondo_caja)
        elif tipo == "txtAsimetrico":
            self._texto(e.get("izquierda"), just)
            self._texto(e.get("derecha"), just)
        elif tipo == "txtCapitular":
            pars = parrafos(e.get("texto"), self.fmt)
            inicio = [Trozo(str(e.get("letra") or ""), b=True)] + [x.con(smallcaps=True) for x in self._una_linea(e.get("resto"))]
            if pars:
                pars[0] = inicio + [Trozo(" ")] + pars[0]
            else:
                pars = [inicio]
            for par in pars:
                self._parrafo(par, alinear=just)
        elif tipo == "txtEntradilla":
            self._parrafo([x.con(b=True) for x in self._una_linea(e.get("entradilla"))], tam=self.tam * 1.15, sin_sangria=True)
            self._texto(e.get("texto"), just)
        elif tipo == "txtVinetas":
            self._lista(e.get("items"))
        elif tipo == "txtNumerada":
            self._lista(e.get("items"), numerada=True)
        elif tipo == "txtReferencias":
            self._lista(e.get("items"), tam=self.tam * 0.9)
        elif tipo == "txtDefiniciones":
            for par in e.get("pares") or []:
                if isinstance(par, (list, tuple)) and par:
                    termino = [x.con(b=True) for x in self._una_linea(par[0])]
                    desc = self._una_linea(par[1] if len(par) > 1 else "")
                    p = self._parrafo(termino + ([Trozo(": ")] if desc else []) + desc, sin_sangria=True)
                    p.paragraph_format.left_indent = int(self.ancho_texto * 0.04)
        elif tipo == "txtCitaGrande":
            self._parrafo([Trozo("«")] + [x.con(i=True) for x in self._una_linea(e.get("cita"))] + [Trozo("»")],
                          "Quote", alinear=1, tam=self.tam * 1.25)
            if str(e.get("autor") or "").strip():
                self._parrafo([Trozo("— ")] + self._una_linea(e.get("autor")), alinear=2, sin_sangria=True)
        elif tipo in ("txtCifra",):
            self._parrafo([Trozo(str(e.get("cifra") or ""), b=True)], alinear=1, tam=self.tam * 2.2, sin_sangria=True,
                          color=self.color_primario)
            self._parrafo(self._una_linea(e.get("texto")), alinear=1, sin_sangria=True)
        elif tipo == "txtCifras":
            tabla = self.d.add_table(rows=2, cols=3)
            self._ancho_tabla(tabla)
            for j, n in enumerate((1, 2, 3)):
                for i, (clave, tam, b) in enumerate(((f"c{n}", self.tam * 2, True), (f"t{n}", self.tam * 0.9, False))):
                    p = tabla.cell(i, j).paragraphs[0]
                    p.alignment = 1
                    p.paragraph_format.first_line_indent = 0
                    self._escribir(p, [x.con(b=b) for x in self._una_linea(e.get(clave))], tam=tam,
                                   color=self.color_primario if b else None)
        elif tipo == "txtPasos":
            self._lista([e.get(k) for k in ("p1", "p2", "p3") if str(e.get(k) or "").strip()], numerada=True)
        elif tipo in ("txtNotaLateral",):
            for par in parrafos(e.get("nota"), self.fmt):
                p = self._parrafo([x.con(i=True) for x in par], tam=self.tam * 0.9, sin_sangria=True)
                self._sombrear(p, self.color_fondo_caja)
            self._texto(e.get("texto"), just)
        elif tipo in ("txtVertical", "txtEtiquetaMargen"):
            self._parrafo([x.con(b=True) for x in self._una_linea(e.get("rotulo"))], sin_sangria=True,
                          color=self.color_primario)
            self._texto(e.get("texto"), just)
        elif tipo == "txtSobreImagen":
            self._imagen(e.get("archivo"), self._frac(e), alt=alt)
            self._texto(e.get("texto"), 1)
        elif tipo == "txtContacto":
            self._texto(e.get("texto"), 0)
            self._imagen(e.get("archivo"), 0.2, alinear=0, alt="Código QR")
        elif tipo == "txtTabla":
            self._tabla(e.get("tabla") or {}, e.get("pie"))
        elif tipo == "txtEcuacion":
            self._titulo_caja(e)
            if str(e.get("ecuacion") or "").strip():
                self._ecuacion(e["ecuacion"])
            self._texto(e.get("texto"), just)
        elif tipo == "txtLineaTiempo":
            self._titulo_caja(e)
            for h in e.get("hitos") or []:
                if isinstance(h, (list, tuple)) and h:
                    p = self._parrafo([x.con(b=True) for x in self._una_linea(h[0])] + [Trozo(" — ")]
                                      + self._una_linea(h[1] if len(h) > 1 else ""), "List Bullet")
        elif g == "caja":                      # resaltado, recuadro, caja con título, cita con barra…
            fondo = str(e.get("fondo") or "").strip()[:6] or (None if tipo in ("txtCitaBarra", "txtRecuadro") else self.color_fondo_caja)
            borde = str(e.get("borde") or "").strip()[:6] or str((self.m.get("colores") or {}).get("primario") or "1F3864")[:6]
            pars = []
            if e.get("titulo") and e.get("mostrar_titulo", True) is not False:
                pars.append([x.con(b=True) for x in self._una_linea(e.get("titulo"))])
            pars += parrafos(e.get("texto"), self.fmt)
            for par in pars:
                p = self._parrafo([x.con(i=True) for x in par] if tipo == "txtCitaBarra" else par, sin_sangria=True)
                self._sombrear(p, fondo, borde, izquierda_solo=tipo in ("txtCitaBarra", "txtResaltado"))
        else:                                   # cualquier otra variante: sus textos, en orden
            for c in v["campos"]:
                if c["tipo"] in ("texto", "parrafo"):
                    self._texto(e.get(c["nombre"]), just)
                elif c["tipo"] == "lista":
                    self._lista(e.get(c["nombre"]))

    def _titulo_caja(self, e):
        if e.get("titulo") and e.get("mostrar_titulo", True) is not False:
            self._parrafo([x.con(b=True) for x in self._una_linea(e.get("titulo"))], sin_sangria=True,
                          color=self.color_primario)

    @staticmethod
    def _frac(e: dict, defecto: float = 0.75) -> float:
        tam = e.get("tam")
        try:
            tam = float(tam)
        except (TypeError, ValueError):
            return defecto
        return tam / 100 if tam > 1 else (tam if tam > 0 else defecto)

    def _elemento_imagen(self, e: dict, v: dict):
        tipo = e["tipo"]
        alt = T.texto_plano(e.get("pie") or e.get("titulo") or "Figura", 120)
        imagenes = [c["nombre"] for c in v["campos"] if c["tipo"] == "imagen"]
        frac = self._frac(e)
        if tipo in ("imgTextoDerecha", "imgTextoIzquierda", "imgEnvueltaIzquierda", "imgEnvueltaDerecha",
                    "imgPieLateral", "imgDetalle"):
            frac = max(0.3, min(0.9, frac if frac <= 1 else 0.45))
        if tipo == "imgInclinada":
            frac = 0.6
        if tipo in ("imgTituloSobre", "imgMiniatura"):
            self._titulo_caja(dict(e, mostrar_titulo=True))
            if str(e.get("subtitulo") or "").strip():
                self._parrafo(self._una_linea(e.get("subtitulo")), sin_sangria=True)
        if tipo == "imgPieArriba":
            self._pie(e.get("pie"))
        if len(imagenes) == 1 or tipo == "imgDetalle":
            self._imagen(e.get(imagenes[0]), frac if tipo != "imgMiniatura" else 0.35, alt=alt)
        else:
            rutas = [e.get(n) for n in imagenes]
            cols = 3 if tipo == "imgRejillaSeis" else 2 if tipo in ("imgRejilla", "imgPila") else len(rutas)
            if tipo == "imgPila":
                cols = 1
            rotulos = None
            if tipo == "imgComparar":
                rotulos = [self._una_linea(e.get("ra")), self._una_linea(e.get("rb"))]
            elif tipo in ("imgRejilla", "imgRejillaSeis", "imgPila"):
                rotulos = [[Trozo(f"({chr(97 + i)})", b=True)] for i in range(len(rutas))]
            self._rejilla_imagenes(rutas, cols, frac if frac <= 1 else 1.0, rotulos)
        for c in v["campos"]:
            if c["tipo"] == "parrafo" or (c["tipo"] == "texto" and c["nombre"] == "texto"):
                self._texto(e.get(c["nombre"]), self._alineacion())
        if tipo not in ("imgPieArriba", "imgTituloSobre", "imgMiniatura") and "pie" in {c["nombre"] for c in v["campos"]}:
            self._pie(e.get("pie"))

    def _bibliografia(self, e: dict):
        from docx.shared import Pt
        if not self.ctx:
            return
        entradas = self.ctx.entradas(e.get("incluir") or "citadas")
        for etiqueta, rico, _ in entradas:
            p = self.d.add_paragraph()
            pf = p.paragraph_format
            pf.first_line_indent = Pt(-self.tam * 1.8)
            pf.left_indent = Pt(self.tam * 1.8)
            pf.space_after = Pt(self.tam * 0.35)
            if etiqueta:
                p.add_run(etiqueta + " ")
            for texto, estilo in rico._unidos():
                r = p.add_run(texto)
                r.font.size = Pt(self.tam * 0.92)
                if "b" in estilo:
                    r.font.bold = True
                if "i" in estilo:
                    r.font.italic = True

    # ------------------------------------------------------------------ partes del documento
    def _titulo_seccion(self, texto_trozos: list[Trozo], nivel: int, numerar: bool, apendice: bool):
        nivel = max(1, min(5, nivel))
        etiqueta = ""
        if numerar:
            if apendice and nivel == 1:
                self.capitulo_apendice += 1
                nombre = self.doc_cfg.get("nombre_apendice") or "Apéndice"
                etiqueta = f"{nombre} {chr(64 + self.capitulo_apendice)}. "
                self.secciones = [0, 0, 0, 0, 0]
            else:
                self.secciones[nivel - 1] += 1
                for k in range(nivel, 5):
                    self.secciones[k] = 0
                nums = [str(n) for n in self.secciones[:nivel]]
                if self.capitulo_apendice:
                    nums[0] = chr(64 + self.capitulo_apendice)
                if self.tesis and nivel == 1 and not self.capitulo_apendice:
                    etiqueta = f"{self.doc_cfg.get('nombre_capitulo') or 'Capítulo'} {nums[0]}. "
                else:
                    etiqueta = ".".join(nums) + ("." if nivel == 1 else "") + " "
        h = self.d.add_heading(level=nivel)
        if etiqueta:
            h.add_run(etiqueta)
        self._escribir(h, texto_trozos)
        if self.tesis and nivel == 1:
            h.paragraph_format.page_break_before = True
        return h

    def _portada(self):
        from docx.shared import Pt
        cab = self.m.get("cabecera") or {}
        port = self.doc_cfg.get("portada") or {}

        def linea(valor, tam=1.0, b=False, color=None, espacio=0.6):
            trozos = self._una_linea(valor)
            if trozos:
                p = self._parrafo([x.con(b=b) for x in trozos], alinear=1, tam=self.tam * tam, sin_sangria=True, color=color)
                p.paragraph_format.space_after = Pt(self.tam * espacio)
        linea(port.get("institucion"), 1.5, True)
        linea(port.get("dependencia"), 1.15)
        for _ in range(4):
            self._parrafo(sin_sangria=True)
        p = self._parrafo([x.con(b=True) for x in self._una_linea(cab.get("titulo"))], "Title")
        if cab.get("subtitulo"):
            self._parrafo(self._una_linea(cab.get("subtitulo")), "Subtitle")
        for _ in range(3):
            self._parrafo(sin_sangria=True)
        linea(port.get("tipo"), 1.6, True)
        linea(port.get("grado"), 1.1)
        linea(port.get("presenta"), 1.0, color=self.color_tenue)
        linea(cab.get("autores"), 1.1, True)
        linea(cab.get("afiliaciones"), 0.92, color=self.color_tenue)
        for _ in range(3):
            self._parrafo(sin_sangria=True)
        linea(port.get("director"), 1.05)
        lugar = ", ".join(x for x in (str(port.get("lugar") or "").strip(), str(port.get("fecha") or "").strip()) if x)
        linea(lugar)
        del p
        self._salto_pagina()

    def _titulo_documento(self):
        cab = self.m.get("cabecera") or {}
        if cab.get("visible", True) is False:
            return
        self._parrafo(self._una_linea(cab.get("titulo")), "Title")
        if str(cab.get("subtitulo") or "").strip():
            self._parrafo(self._una_linea(cab.get("subtitulo")), "Subtitle")
        if str(cab.get("autores") or "").strip():
            self._parrafo([x.con(b=True) for x in self._una_linea(cab.get("autores"))], alinear=1, sin_sangria=True,
                          tam=self.tam * 1.1)
        if str(cab.get("afiliaciones") or "").strip():
            for par in parrafos(cab.get("afiliaciones"), self.fmt):
                self._parrafo(par, alinear=1, sin_sangria=True, tam=self.tam * 0.92, color=self.color_tenue)

    def _resumenes(self, como_seccion: bool):
        from docx.shared import Pt
        for suf in ("", "2"):
            resumen = str(self.doc_cfg.get("resumen" + suf) or "").strip()
            claves = str(self.doc_cfg.get("palabras_clave" + suf) or "").strip()
            if not resumen and not claves:
                continue
            titulo = self._una_linea(self.doc_cfg.get("titulo_resumen" + suf) or "Resumen")
            if como_seccion:
                h = self.d.add_heading(level=1)
                self._escribir(h, titulo)
                h.paragraph_format.page_break_before = True
            else:
                p = self._parrafo([x.con(b=True) for x in titulo], alinear=1, sin_sangria=True)
                p.paragraph_format.space_before = Pt(self.tam)
            for par in parrafos(resumen, self.fmt):
                p = self._parrafo(par, alinear=3)
                if not como_seccion:
                    p.paragraph_format.left_indent = p.paragraph_format.right_indent = int(self.ancho_texto * 0.06)
            if claves:
                p = self._parrafo([Trozo(self._plano(self.doc_cfg.get("titulo_palabras" + suf) or "Palabras clave") + ": ",
                                         b=True)] + self._una_linea(claves), sin_sangria=True)
                if not como_seccion:
                    p.paragraph_format.left_indent = p.paragraph_format.right_indent = int(self.ancho_texto * 0.06)

    def _plano(self, v) -> str:
        return "".join(t.texto for t in self._una_linea(v) if not t.salto)

    def _indices(self):
        for clave, titulo, instr in (("indice", "titulo_indice", 'TOC \\o "1-3" \\h \\z \\u'),
                                     ("lista_figuras", "titulo_figuras", 'TOC \\h \\z \\c "Figura"'),
                                     ("lista_tablas", "titulo_tablas", 'TOC \\h \\z \\c "Tabla"')):
            if not self.doc_cfg.get(clave):
                continue
            h = self.d.add_heading(level=1)
            self._escribir(h, self._una_linea(self.doc_cfg.get(titulo) or "Índice"))
            if self.tesis:
                h.paragraph_format.page_break_before = True
            p = self.d.add_paragraph()
            self._campo(p, instr, "Haz clic con el botón derecho y elige «Actualizar campo» para ver el índice.")
            self.hay_indices = True

    def _dos_columnas(self):
        """Del cuerpo en adelante, a dos columnas (artículo)."""
        from docx.enum.section import WD_SECTION
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls, qn
        anterior = self.d.sections[-1]
        nueva = self.d.add_section(WD_SECTION.CONTINUOUS)
        sect = nueva._sectPr
        for c in sect.findall(qn("w:cols")):
            sect.remove(c)
        sect.append(parse_xml(f'<w:cols {nsdecls("w")} w:num="2" w:space="425"/>'))
        self.ancho_columna = (self.ancho_texto - 425 * 635) // 2      # 425 twips = 0,75 cm
        del anterior

    def _actualizar_campos_al_abrir(self):
        """Word pregunta al abrir si actualiza los campos (índices): así salen con los números de página."""
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls
        ajustes = self.d.settings.element
        ajustes.append(parse_xml(f'<w:updateFields {nsdecls("w")} w:val="true"/>'))

    # ------------------------------------------------------------------ todo
    def exportar(self, destino: Path) -> dict:
        try:
            import docx
        except ImportError as exc:
            raise ErrorWord("Falta el paquete de Python «python-docx»: instálalo en el entorno de DocsLab "
                            "(python -m pip install python-docx) y reinicia DocsLab.") from exc
        self.informar("Preparando las fórmulas", 0.1)
        self.formulas = Formulas(str((self.m.get("latex") or {}).get("preambulo") or ""))
        lista = formulas_de(self.m)
        self.formulas.preparar(lista)
        if lista and len(self.formulas.omml) < len(lista):
            if self.formulas.pandoc:
                self.avisos.append("Algunas fórmulas no se pudieron convertir en ecuaciones de Word: van como imagen.")
            else:
                self.avisos.append("Sin pandoc, las fórmulas van como imagen (con su código como texto alternativo). "
                                   "Instala pandoc para que sean ecuaciones de Word editables.")
        self.informar("Escribiendo el documento", 0.3)
        self.d = docx.Document()
        self.hay_indices = False
        self._estilos()
        self._pagina()
        cab = self.m.get("cabecera") or {}
        dos_col = str(self.doc_cfg.get("columnas") or "1") == "2"
        if self.tesis:
            if (self.doc_cfg.get("portada") or {}).get("visible", True) and cab.get("visible", True):
                self._portada()
            if str(self.doc_cfg.get("dedicatoria") or "").strip():
                for _ in range(8):
                    self._parrafo(sin_sangria=True)
                for par in parrafos(self.doc_cfg.get("dedicatoria"), self.fmt):
                    self._parrafo([x.con(i=True) for x in par], alinear=2, sin_sangria=True)
                self._salto_pagina()
            if str(self.doc_cfg.get("agradecimientos") or "").strip():
                h = self.d.add_heading(level=1)
                self._escribir(h, self._una_linea(self.doc_cfg.get("titulo_agradecimientos") or "Agradecimientos"))
                self._texto(self.doc_cfg.get("agradecimientos"), 3)
            self._resumenes(como_seccion=True)
            self._indices()
        else:
            self._titulo_documento()
            self._resumenes(como_seccion=False)
            self._indices()
            if dos_col:
                self._dos_columnas()
        bloques = [b for b in M.bloques_de_flujo(self.m) if b.get("visible", True) is not False]
        for n, b in enumerate(bloques):
            self.informar(f"Sección {n + 1} de {len(bloques)}", 0.3 + 0.65 * n / max(1, len(bloques)))
            titulo = self._una_linea(b.get("titulo"))
            nivel = int(self._numero(b.get("nivel"), 1) or 1)
            if b.get("salto") and not (self.tesis and nivel == 1):
                self._salto_pagina()
            if titulo and b.get("mostrar_titulo", True) is not False:
                numerar = self.doc_cfg.get("numerar_secciones", True) and b.get("numerar") is not False
                self._titulo_seccion(titulo, nivel, numerar, bool(b.get("apendice")))
            for e in b.get("elementos") or []:
                if e.get("visible", True) is False:
                    continue
                self._elemento(e)
        if self.hay_indices:
            self._actualizar_campos_al_abrir()
        self.d.core_properties.title = self._plano(cab.get("titulo")) or "Documento"
        self.d.core_properties.author = self._plano(cab.get("autores"))[:250]
        self.d.core_properties.language = IDIOMAS.get(self.m.get("idioma") or "es", "es-ES")
        self.d.save(str(destino))
        self.informar("Word listo", 1.0)
        return {"imagenes": self.cont["imagenes"], "tablas": self.cont["tablas"], "ecuaciones": self.cont["ecuaciones"],
                "figuras": self.cont["figura"], "recortes": self.cont["recortes"],
                "ecuaciones_editables": bool(self.formulas.omml) or not lista,
                "pandoc": bool(self.formulas.pandoc), "avisos": self.avisos}


def exportar(m: dict, dir_proyecto: Path, destino: Path, pdf: Path | None = None, posiciones: dict | None = None,
             informar=None) -> dict:
    return Exportador(m, dir_proyecto, pdf, posiciones, informar).exportar(destino)
