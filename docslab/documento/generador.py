# SPDX-License-Identifier: AGPL-3.0-only
"""Generador: modelo JSON del póster → documento LaTeX (postercientifico.sty).

generar(modelo, marcas=True) devuelve el texto .tex y un mapa
{número de línea: id del elemento} para señalar en la aplicación de qué
elemento viene un error de compilación.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import bibliografia as B
from ..salidas import compilador
from . import componentes as C
from ..nucleo import modelo as M
from . import texto as T
from . import variantes as V

_DIM = re.compile(r"^\s*-?(\d+(\.\d*)?|\.\d+)\s*(mm|cm|in|pt|em|ex|bp|pc|sp|dd|cc)\s*$")
_HEX = re.compile(r"^#?[0-9A-Fa-f]{6}$")
_XCOLOR = re.compile(r"^[A-Za-z][A-Za-z0-9]*(![0-9]{1,3}(![A-Za-z][A-Za-z0-9]*)?)*$")
_ID = re.compile(r"[^A-Za-z0-9-]")
_NUM = re.compile(r"^\s*-?(\d+(\.\d*)?|\.\d+)\s*$")
_RUTA_MALA = re.compile(r"[%#{}\\$&^~]")


def dim(valor, defecto: str) -> str:
    """Una longitud válida de LaTeX o el valor por defecto."""
    if valor is None:
        return defecto
    v = str(valor).strip()
    if _NUM.match(v):            # sin unidad: se entiende en pt
        return v + "pt"
    return v.replace(" ", "") if _DIM.match(v) else defecto


def numero(valor, defecto):
    try:
        x = float(valor)
    except (TypeError, ValueError):
        return defecto
    if x != x or x in (float("inf"), float("-inf")):
        return defecto
    return x


def fmt(x) -> str:
    """Número con pocos decimales y sin ceros sobrantes."""
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int):
        return str(x)
    s = f"{float(x):.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


NOMBRES_COLOR = {"primario": "pcPrimario", "secundario": "pcSecundario", "acento": "pcAcento",
                 "fondo": "pcFondo", "bloque": "pcBloque", "fondo_bloque": "pcBloque", "texto": "pcTexto",
                 "tenue": "pcTenue", "contraste": "pcContraste", "blanco": "white", "negro": "black"}


def color(valor, defecto: str | None = None) -> str | None:
    """Color en hexadecimal (sin #), un nombre del tema (primario, acento…) o una expresión
    de xcolor (pcAcento!20). Si no es válido, el defecto."""
    if valor is None:
        return defecto
    v = str(valor).strip()
    if not v:
        return defecto
    if _HEX.match(v):
        return v.lstrip("#").upper()
    base, _, resto = v.partition("!")
    if base in NOMBRES_COLOR:
        v = NOMBRES_COLOR[base] + ("!" + resto if resto else "")
    if _XCOLOR.match(v):
        return v
    return defecto


def ident(valor: str) -> str:
    return _ID.sub("-", str(valor or ""))[:60]


def ruta(valor: str) -> str:
    """Ruta de un recurso para \\includegraphics (sin caracteres que rompan LaTeX)."""
    v = str(valor or "").strip().replace("\\", "/")
    if not v or _RUTA_MALA.search(v) or ".." in v.split("/"):
        return "imagen-pendiente"
    return v


def coord(valor, defecto="0.5") -> str:
    """Coordenada o tamaño de capa: fracción (0.25) o longitud (12cm)."""
    if valor is None or str(valor).strip() == "":
        return defecto
    v = str(valor).strip()
    if _NUM.match(v):
        return fmt(float(v))
    return dim(v, defecto)


@dataclass
class Escritor:
    lineas: list = field(default_factory=list)
    mapa: dict = field(default_factory=dict)
    actual: list = field(default_factory=list)   # pila de ids

    def w(self, texto: str = ""):
        for linea in str(texto).split("\n"):
            self.lineas.append(linea)
            if self.actual:
                self.mapa[len(self.lineas)] = self.actual[-1]

    def dentro(self, id_):
        escritor = self

        class _Ctx:
            def __enter__(self):
                escritor.actual.append(id_)

            def __exit__(self, *a):
                escritor.actual.pop()
        return _Ctx()

    def texto(self) -> str:
        return "\n".join(self.lineas) + "\n"


# --------------------------------------------------------------------- configuración
_ARCHIVO_FUENTE = re.compile(r"^[A-Za-z0-9._-]+\.(ttf|otf)$", re.I)


def familias_de(m: dict) -> tuple[str, str]:
    """(familia del texto, familia de los títulos) que puede usar el póster con su motor.
    Con LuaLaTeX (tipografías propias) las libres de TeX Live se cambian por una clásica."""
    tp = m.get("tipografia") or {}
    propias = M.familias_propias(m)
    lua = M.motor(m) == "lualatex"

    def valida(f, defecto):
        if f in propias:
            return f
        info = M.FAMILIAS_INFO.get(f)
        if not info:
            return defecto
        if lua and info["grupo"] == "libre":
            return "helvetica" if info["tipo"] == "sans" else "palatino"
        return f
    return valida(tp.get("familia"), "helvetica"), valida(tp.get("familia_titulos"), "")


def _familias_propias_tex(m: dict) -> list[str]:
    """\\posterfamilia{...} de las tipografías propias que usa el póster."""
    propias = M.familias_propias(m)
    lineas = []
    for fid in dict.fromkeys(f for f in familias_de(m) if f in propias):
        arch = propias[fid]["archivos"]
        normal = str(arch.get("normal") or "").replace("\\", "/")
        carpeta, _, nombre = normal.rpartition("/")
        if not _ARCHIVO_FUENTE.match(nombre) or ".." in carpeta.split("/"):
            continue
        otros = []
        for k in ("negrita", "cursiva", "negrita_cursiva"):
            v = str(arch.get(k) or "").replace("\\", "/")
            c, _, n = v.rpartition("/")
            otros.append(n if v and c == carpeta and _ARCHIVO_FUENTE.match(n) else "")
        nombre_visible = T.texto_plano(propias[fid].get("nombre"), 60)
        lineas.append(f"\\posterfamilia{{{fid}}}{{{carpeta + '/' if carpeta else ''}}}{{{nombre}}}"
                      f"{{{otros[0]}}}{{{otros[1]}}}{{{otros[2]}}}   % {nombre_visible}")
    return lineas


def _posterconfig(m: dict, marcas: bool, imprenta: dict | None = None) -> str:
    lz, tp, co, es = m["lienzo"], m["tipografia"], m["colores"], m["estilo"]
    cab, pie = m["cabecera"], m["pie"]
    esc = tp.get("escalas", {})
    fmt_texto = m.get("formato_texto", "simple")
    clase = m.get("clase", "poster")
    claves = []
    if clase == "presentacion":
        claves.append(("modo", "presentacion"))
    elif M.es_flujo(m):
        claves.append(("modo", "documento"))
    claves += [
        ("ancho", dim(lz.get("ancho"), "841mm")), ("alto", dim(lz.get("alto"), "1189mm")),
        ("margen", dim(lz.get("margen"), "28mm")),
    ]
    margenes = {k: dim(lz.get("margen_" + k), "") if str(lz.get("margen_" + k) or "").strip() else ""
                for k in ("superior", "inferior", "izquierdo", "derecho")}
    if clase == "presentacion" and not margenes["inferior"] and _pie_presentacion(m):
        # sitio para el pie de las diapositivas (se pinta dentro del margen inferior)
        mg = _mm(dim(lz.get("margen"), "14mm"), 0) or 14.0
        letra = numero(tp.get("fuente"), 20) * 0.62 * 25.4 / 72.27
        margenes["inferior"] = fmt(round(max(mg, 0.5 * mg + 1.6 * letra + 1.5), 2)) + "mm"
    for k, v in margenes.items():
        if v:
            claves.append((f"margen {k}", v))
    claves += [
        ("separacion", dim(es.get("separacion_columnas"), "20mm")),
        ("separacion bloques", dim(es.get("separacion_bloques"), "0.9em")),
        ("separacion imagenes", dim(es.get("separacion_imagenes"), "0.45em")),
        ("separacion elementos", dim(es.get("separacion_elementos"), "0.35em")),
    ]
    if str(es.get("separacion_filas") or "").strip():
        claves.append(("separacion filas", dim(es.get("separacion_filas"), "0.9em")))
    claves += [
        ("fuente", fmt(numero(tp.get("fuente"), 30)) + "pt"),
        ("interlinea", fmt(numero(tp.get("interlinea"), 1.28))),
        ("familia", familias_de(m)[0]),
    ]
    if m.get("idioma") in M.IDIOMAS:
        claves.append(("idioma", M.IDIOMAS[m["idioma"]]["babel"]))
    if familias_de(m)[1]:
        claves.append(("familia titulos", familias_de(m)[1]))
    for k, defecto in [("titulo", 3.3), ("subtitulo", 1.75), ("autores", 1.4), ("afiliaciones", 1.0),
                       ("bloque", 1.35), ("pie", 0.8), ("cita", 1.5), ("cifra", 3.2),
                       ("referencias", 0.75), ("piedeposter", 0.8)]:
        claves.append((f"escala {k}", fmt(numero(esc.get(k), defecto))))
    claves += [
        ("cabecera", cab.get("estilo") if cab.get("estilo") in M.ESTILOS_CABECERA else "banda"),
        ("alineacion cabecera", "izquierda" if cab.get("alineacion") == "izquierda" else "centro"),
        ("ancho logos", fmt(numero(cab.get("ancho_logos"), 0.15))),
        ("alto logos", dim(cab.get("alto_logos"), "5.5em")),
        ("escala logo izquierdo", fmt(tam_logo(cab.get("tam_logo_izquierdo")))),
        ("escala logo derecho", fmt(tam_logo(cab.get("tam_logo_derecho")))),
        ("pie", pie.get("estilo") if pie.get("estilo") in M.ESTILOS_PIE else "banda"),
        ("estilo bloque", es.get("bloque") if es.get("bloque") in V.ESTILOS_CAJA else "barra"),
        ("radio", dim(es.get("radio"), "0.3em")), ("relleno", dim(es.get("relleno"), "0.75em")),
        ("mostrar titulos", fmt(bool(es.get("mostrar_titulos", True)))),
        ("numerar bloques", fmt(bool(es.get("numerar_bloques", False)))),
        ("alineacion titulos", es.get("alineacion_titulos") if es.get("alineacion_titulos") in
         ("izquierda", "centro", "derecha") else "izquierda"),
        ("alinear texto", es.get("alinear_texto") if es.get("alinear_texto") in
         ("izquierda", "centro", "derecha", "justificado") else "justificado"),
        ("sombra", fmt(bool(es.get("sombra", False)))),
        ("numerar figuras", fmt(bool(es.get("numerar_figuras", True)))),
        ("nombre figura", "{" + T.convertir(es.get("nombre_figura") or "Figura", fmt_texto, False) + "}"),
    ]
    tema = M.TEMAS.get(co.get("tema"), M.TEMAS["azul"])
    for k, nombre in [("primario", "primario"), ("secundario", "secundario"), ("acento", "acento"),
                      ("fondo", "fondo"), ("fondo_bloque", "fondo bloque"), ("texto", "texto"),
                      ("tenue", "tenue"), ("contraste", "contraste")]:
        claves.append((nombre, color(co.get(k), tema[k])))
    if clase == "presentacion":
        pr = m.get("presentacion") or {}
        if str(pr.get("pie") or "").strip():
            claves.append(("pie diapositiva", "{" + T.convertir(pr.get("pie"), fmt_texto, False) + "}"))
        claves.append(("numerar diapositivas", fmt(bool(pr.get("numerar", True)))))
        claves.append(("titulo diapositiva", pr.get("titulo") if pr.get("titulo") in M.ESTILOS_TITULO_PAGINA else "banda"))
        claves.append(("escala diapositiva", fmt(numero(pr.get("escala_titulo"), 1.5))))
        if pr.get("progreso"):
            claves.append(("progreso", "true"))
    elif M.es_flujo(m):
        doc = m.get("documento") or {}
        claves.append(("columnas texto", "2" if int(numero(doc.get("columnas"), 1)) == 2 else "1"))
        claves.append(("parrafos", "sangria" if doc.get("parrafos") != "separados" else "separados"))
        claves.append(("numerar paginas", fmt(bool(doc.get("numerar_paginas", True)))))
        claves.append(("numerar secciones", fmt(bool(doc.get("numerar_secciones", True)))))
        if clase == "tesis":
            claves.append(("capitulos", "true"))
        if str(doc.get("encabezado") or "").strip():
            claves.append(("encabezado", "{" + T.convertir(doc.get("encabezado"), fmt_texto, False) + "}"))
        claves.append(("numerar tablas", fmt(bool(doc.get("numerar_tablas", True)))))
        for k, clave, defecto in (("nombre_tabla", "nombre tabla", "Tabla"), ("nombre_capitulo", "nombre capitulo", "Capítulo"),
                                  ("nombre_apendice", "nombre apendice", "Apéndice")):
            claves.append((clave, "{" + T.convertir(doc.get(k) or defecto, "simple", False) + "}"))
        if doc.get("lista_figuras"):
            claves.append(("lista figuras", "true"))
        if doc.get("lista_tablas"):
            claves.append(("lista tablas", "true"))
        claves.append(("escala seccion", fmt(numero(doc.get("escala_seccion"), 1.45))))
        claves.append(("escala capitulo", fmt(numero(doc.get("escala_capitulo"), 2.2))))
    claves.append(("contenido visible", fmt(bool(m.get("contenido_visible", True)))))
    claves.append(("marcas", fmt(bool(marcas))))
    if imprenta:
        sangrado = max(0.0, min(10.0, numero(imprenta.get("sangrado_mm"), 0)))
        if sangrado:
            claves.append(("sangrado", fmt(sangrado) + "mm"))
        if imprenta.get("marcas_corte"):
            claves.append(("marcas corte", "true"))
    filas = []
    linea = "  "
    for k, v in claves:
        trozo = f"{k}={v}, "
        if len(linea) + len(trozo) > 100:
            filas.append(linea.rstrip())
            linea = "  "
        linea += trozo
    filas.append(linea.rstrip().rstrip(","))
    return "\\posterconfig{\n" + "\n".join(filas) + "\n}"


def _pie_presentacion(m: dict) -> bool:
    """¿Alguna diapositiva pinta el pie (texto, número o barra de avance)?"""
    pr = m.get("presentacion") or {}
    if not (str(pr.get("pie") or "").strip() or pr.get("numerar", True) or pr.get("progreso")):
        return False
    return any(pg.get("pie", True) and pg.get("visible", True) for pg in m.get("paginas") or [])


# --------------------------------------------------------------------- argumentos
def _arg(espec, e: dict, fmt_texto: str) -> str:
    tipo = espec[0]
    campo = espec[1] if len(espec) > 1 else None
    valor = e.get(campo) if isinstance(campo, str) else None
    if tipo == "opt_pct":
        x = numero(valor, espec[2])
        return "" if abs(x - espec[2]) < 1e-9 else f"[{fmt(x / 100)}\\linewidth]"
    if tipo == "opt_num":
        x = numero(valor, espec[2])
        return "" if abs(x - espec[2]) < 1e-9 else f"[{fmt(x)}]"
    if tipo == "opt_dim":
        d = dim(valor, espec[2])
        return "" if d == espec[2] else f"[{d}]"
    if tipo == "img":
        return "{" + ruta(valor) + "}"
    if tipo == "txt":
        return "{" + T.convertir(valor, fmt_texto, parrafos=False) + "}"
    if tipo == "par":
        return "{" + T.convertir(valor, fmt_texto, parrafos=True) + "}"
    if tipo == "raw":
        return "{" + str(valor or "") + "}"
    if tipo == "items":
        items = T.lista(valor, fmt_texto)
        return "{" + " ".join("\\item " + i for i in items) + "}" if items else "{\\item\\relax}"
    if tipo == "defs":
        partes = []
        for par in valor or []:
            if isinstance(par, (list, tuple)) and len(par) >= 2:
                partes.append("\\item[{" + T.convertir(par[0], fmt_texto, False) + "}] " +
                              T.convertir(par[1], fmt_texto, False))
        return "{" + " ".join(partes) + "}" if partes else "{\\item[]\\relax}"
    if tipo == "hitos":
        partes = []
        for par in valor or []:
            if isinstance(par, (list, tuple)) and len(par) >= 2:
                partes.append("\\hito{" + T.convertir(par[0], fmt_texto, False) + "}{" +
                              T.convertir(par[1], fmt_texto, False) + "}")
        return "{" + " ".join(partes) + "}"
    if tipo == "flechas":
        partes = []
        for f in valor or []:
            if isinstance(f, (list, tuple)) and len(f) >= 5:
                x0, y0, x1, y1 = (fmt(min(1.0, max(0.0, numero(c, 0.5)))) for c in f[:4])
                partes.append(f"\\PCflecha{{{x0},{y0}}}{{{x1},{y1}}}{{" +
                              T.convertir(f[4], fmt_texto, False) + "}")
        return "{" + " ".join(partes) + "}"
    if tipo == "tabla":
        return "{" + _tabla(valor, fmt_texto) + "}"
    if tipo == "claves_caja":
        return _claves_caja(espec[1], e, fmt_texto)
    raise ValueError(f"tipo de argumento desconocido: {tipo}")


def _tabla(t, fmt_texto) -> str:
    t = t or {}
    filas = [f for f in (t.get("filas") or []) if isinstance(f, (list, tuple))]
    if not filas:
        return ""
    n = max(len(f) for f in filas)
    cols = re.sub(r"[^lcr]", "", str(t.get("columnas") or ""))
    cols = (cols + "l" * n)[:n] if cols else "l" + "r" * (n - 1)
    out = ["\\begin{tabular}{" + cols + "}\\toprule"]
    for i, f in enumerate(filas):
        celdas = [T.convertir(c, fmt_texto, False) for c in list(f) + [""] * (n - len(f))]
        out.append(" & ".join(celdas) + "\\\\")
        if i == 0 and t.get("encabezado", True) and len(filas) > 1:
            out.append("\\midrule")
    out.append("\\bottomrule\\end{tabular}")
    return "\n".join(out)


def _claves_caja(campos, e: dict, fmt_texto: str) -> str:
    partes = []
    titulo = T.convertir(e.get("titulo"), fmt_texto, False)
    for c in campos:
        if c == "estilo":
            if e.get("estilo") in V.ESTILOS_CAJA:
                partes.append(f"estilo={e['estilo']}")
        elif c == "titulo":
            if titulo:
                partes.append("titulo={" + titulo + "}")
        elif c == "mostrar_titulo":
            if titulo:
                partes.append("mostrar titulo=" + fmt(bool(e.get("mostrar_titulo"))))
        elif c == "mostrar_titulo_forzado":
            partes.append("mostrar titulo=" + fmt(bool(e.get("mostrar_titulo", True))))
        elif c in ("fondo", "borde"):
            col = color(e.get(c))
            if col:
                partes.append(f"{c}={col}")
    return "[" + ", ".join(partes) + "]" if partes else ""


def _bibliografia(e: dict, ctx) -> list[str]:
    """La lista de referencias en el estilo del proyecto (T36)."""
    if ctx is None:
        return ["\\PCbibliografiavacia"]
    entradas = ctx.entradas("todas" if e.get("incluir") == "todas" else "citadas")
    if not entradas:
        return ["\\PCbibliografiavacia"]
    cols = max(1, min(3, int(numero(e.get("columnas"), 1) or 1)))
    tipo_lista = "autor" if ctx.info["lista"] == "autor" else "numerica"
    lineas = [f"\\PCbibliografia[{tipo_lista}][{cols}]{{%"]
    for etiqueta, rico, _ in entradas:
        lineas.append("  \\PCref{" + T.escapar(etiqueta) + "}{" + rico.latex() + "}")
    lineas.append("}")
    return lineas


def llamada(e: dict, fmt_texto: str, ctx=None) -> list[str]:
    """Líneas LaTeX de un elemento de caja."""
    tipo = e.get("tipo")
    if tipo == "latex":
        return [str(e.get("codigo") or "")]
    if tipo == "bibliografia":
        return _bibliografia(e, ctx)
    if tipo == "espacio":
        alto = str(e.get("alto") or "").strip()
        return ["\\vfill"] if not alto else ["\\vspace{" + dim(alto, "1em") + "}"]
    v = V.POR_CLAVE.get(tipo)
    if not v:
        return [f"% elemento desconocido: {tipo}"]
    cuerpo = "\\" + tipo + "".join(_arg(a, e, fmt_texto) for a in v["args"])
    lineas = cuerpo.split("\n")
    if v.get("despues"):
        lineas.append(_arg(v["despues"], e, fmt_texto)[1:-1])
    return lineas


# --------------------------------------------------------------------- partes
_OPC_BLOQUE = {"fondo": ("fondo", "color"), "borde": ("borde", "color"),
               "fondo_titulo": ("fondo titulo", "color"), "color_titulo": ("color titulo", "color"),
               "color_texto": ("color texto", "color"), "grosor_borde": ("grosor borde", "dim"),
               "radio": ("radio", "dim"), "relleno": ("relleno", "dim"),
               "escala_titulo": ("escala titulo", "num"), "escala_texto": ("escala texto", "num"),
               "alineacion_titulo": ("alineacion titulo", "alin"),
               "alinear_texto": ("alinear texto", "alin2"), "columnas": ("columnas", "int"),
               "alto": ("alto", "dim"), "opacidad": ("opacidad", "num"), "sombra": ("sombra", "bool")}


def _claves_bloque(b: dict, fmt_texto: str, marcas: bool) -> str:
    partes = []
    if marcas:
        partes.append("id=" + ident(b["id"]))
    titulo = T.convertir(b.get("titulo"), fmt_texto, False)
    if titulo:
        partes.append("titulo={" + titulo + "}")
    if not b.get("mostrar_titulo", True):
        partes.append("mostrar titulo=false")
    if b.get("estilo") in V.ESTILOS_CAJA:
        partes.append("estilo=" + b["estilo"])
    if str(b.get("numero") or "").strip():
        partes.append("numero={" + T.convertir(b["numero"], fmt_texto, False) + "}")
    if b.get("estirar"):
        partes.append("estirar")
    if not b.get("visible", True):
        partes.append("visible=false")
    op = b.get("opciones") or {}
    for k, (clave, tipo) in _OPC_BLOQUE.items():
        val = op.get(k)
        if val is None or val == "":
            continue
        if tipo == "color":
            c = color(val)
            if c:
                partes.append(f"{clave}={c}")
        elif tipo == "dim":
            d = dim(val, "")
            if d:
                partes.append(f"{clave}={d}")
        elif tipo == "num":
            x = numero(val, None)
            if x is not None:
                partes.append(f"{clave}={fmt(x)}")
        elif tipo == "int":
            x = numero(val, None)
            if x is not None and int(x) >= 2:
                partes.append(f"{clave}={int(x)}")
        elif tipo == "alin" and val in ("izquierda", "centro", "derecha"):
            partes.append(f"{clave}={val}")
        elif tipo == "alin2" and val in ("izquierda", "centro", "derecha", "justificado"):
            if val != "justificado":
                partes.append(f"{clave}={val}")
        elif tipo == "bool":
            if val is True or str(val).lower() in ("true", "1", "si", "sí"):
                partes.append(clave)
    tcb = str(op.get("tcb") or "").strip()
    if tcb:
        partes.append("tcb={" + tcb + "}")
    return ", ".join(partes)


def _cabecera(w: Escritor, m: dict, fmt_texto: str):
    cab = m["cabecera"]
    w.w("\\titulo{" + T.convertir(cab.get("titulo"), fmt_texto, False) + "}")
    for k, orden in [("subtitulo", "subtitulo"), ("autores", "autores"), ("afiliaciones", "afiliaciones")]:
        t = T.convertir(cab.get(k), fmt_texto, False)
        if t:
            w.w(f"\\{orden}{{{t}}}")
    if cab.get("logo_izquierdo"):
        w.w("\\logoizquierdo{" + ruta(cab["logo_izquierdo"]) + "}")
    if cab.get("logo_derecho"):
        w.w("\\logoderecho{" + ruta(cab["logo_derecho"]) + "}")


def _opciones_cabecera(m: dict) -> str:
    cab = m["cabecera"]
    partes = []
    c = color(cab.get("fondo"))
    if c:
        partes.append("fondo=" + c)
    c = color(cab.get("color_texto"))
    if c:
        partes.append("color texto=" + c)
    if cab.get("estilo") == "imagen" and cab.get("imagen"):
        partes.append("imagen={" + ruta(cab["imagen"]) + "}")
        partes.append("oscurecer=" + fmt(min(1.0, max(0.0, numero(cab.get("oscurecer"), 0.45)))))
    return "[" + ", ".join(partes) + "]" if partes else ""


def _capas(w: Escritor, m: dict, fmt_texto: str, marcas: bool, imprenta: dict | None = None):
    w.w("%% ---- Capas (z < 0: detrás del contenido; z > 0: delante) ----")
    num_pag = {}                    # presentaciones: id de la diapositiva → número de página
    if m.get("clase") == "presentacion":
        n = 0
        for pg in m.get("paginas") or []:
            if pg.get("visible", True) is not False:
                n += 1
                num_pag[pg.get("id")] = n
    for capa in m.get("capas", []):
        nombre = ident(capa.get("id"))
        z = fmt(numero(capa.get("z"), 1))
        if z == "0":
            z = "1"
        op = fmt(min(1.0, max(0.0, numero(capa.get("opacidad"), 1))))
        vis = fmt(bool(capa.get("visible", True)))
        w.w(f"\\configcapa{{{nombre}}}{{z={z}, opacidad={op}, visible={vis}}}"
            f"   % {T.texto_plano(capa.get('nombre'), 40)}")
        for it in capa.get("elementos", []):
            if imprenta and numero(imprenta.get("sangrado_mm"), 0) > 0:
                it = a_sangre(it, m, numero(imprenta.get("sangrado_mm"), 0), imprenta.get("directorio"))
            if it.get("pag"):             # solo en una diapositiva
                if it["pag"] not in num_pag:
                    continue              # su diapositiva está oculta o ya no existe
                it = dict(it, pagina=num_pag[it["pag"]])
            with w.dentro(it.get("id")):
                w.w(_item(it, nombre, fmt_texto, marcas))


def _mm(valor, ref_mm: float) -> float | None:
    """Coordenada de capa en mm: una fracción del papel o una longitud."""
    if valor is None or str(valor).strip() == "":
        return None
    v = str(valor).strip()
    if _NUM.match(v):
        return float(v) * ref_mm
    mo = re.match(r"^\s*(-?[0-9.]+)\s*(mm|cm|in|pt|bp)\s*$", v)
    if not mo:
        return None
    return float(mo.group(1)) * {"mm": 1, "cm": 10, "in": 25.4, "pt": 25.4 / 72.27, "bp": 25.4 / 72}[mo.group(2)]


def _aspecto(ruta) -> float | None:
    """Ancho / alto de una imagen (PNG, JPG o la primera página de un PDF)."""
    try:
        p = Path(ruta)
        if p.suffix.lower() == ".pdf":
            from ..salidas import revision
            info = revision.info_pdf(p)
            w, h = info["tamanos"][0] if info else (0, 0)
        else:
            from PIL import Image
            with Image.open(p) as im:
                w, h = im.size
        return w / h if w and h else None
    except Exception:          # noqa: BLE001
        return None


def a_sangre(it: dict, m: dict, sangrado_mm: float, directorio=None) -> dict:
    """Si una imagen o un rectángulo de una capa llega al borde del papel, lo alarga
    «sangrado_mm» por ese lado para que al cortar no quede un filo blanco. Devuelve una
    copia con la posición en mm (o el mismo elemento si no toca el borde)."""
    tipo = it.get("tipo")
    if it.get("visible") is False or numero(it.get("rotacion"), 0) or tipo not in ("imagen", "forma"):
        return it
    if tipo == "forma" and (it.get("forma") or "rectangulo") != "rectangulo":
        return it
    lz = m.get("lienzo") or {}
    W, H = _mm(lz.get("ancho"), 0) or 841.0, _mm(lz.get("alto"), 0) or 1189.0
    if (lz.get("orientacion") == "horizontal") != (W > H):
        W, H = H, W
    w, h = _mm(it.get("ancho"), W), _mm(it.get("alto"), H)
    if tipo == "forma":
        w = w if w is not None else 0.1 * W
        h = h if h is not None else w
    else:
        ajuste = it.get("ajuste") or "ajustar"
        asp = None
        if (w is None or h is None or ajuste == "ajustar") and directorio and it.get("archivo"):
            asp = _aspecto(Path(directorio) / str(it["archivo"]))
        if w is None and h is None:
            return it
        if w is None or h is None:
            if not asp or ajuste == "cubrir":
                return it
            w, h = (w, w / asp) if h is None else (h * asp, h)
        elif ajuste == "ajustar":
            if not asp:
                return it
            w, h = (w, w / asp) if w / h < asp else (h * asp, h)
    x, y = _mm(it.get("x"), W), _mm(it.get("y"), H)
    x = 0.5 * W if x is None else x
    y = 0.5 * H if y is None else y
    ancla = it.get("ancla") or "center"
    x0 = x if "west" in ancla else x - w if "east" in ancla else x - w / 2
    y0 = y if "north" in ancla else y - h if "south" in ancla else y - h / 2
    x1, y1 = x0 + w, y0 + h
    tol = 0.6
    izq, arr, der, aba = x0 <= tol, y0 <= tol, x1 >= W - tol, y1 >= H - tol
    if not (izq or arr or der or aba):
        return it
    s = sangrado_mm
    x0, y0 = (min(x0, 0) - s if izq else x0), (min(y0, 0) - s if arr else y0)
    x1, y1 = (max(x1, W) + s if der else x1), (max(y1, H) + s if aba else y1)
    nuevo = dict(it)
    nuevo.update({"x": f"{fmt(round(x0, 3))}mm", "y": f"{fmt(round(y0, 3))}mm", "ancla": "north west",
                  "ancho": f"{fmt(round(x1 - x0, 3))}mm", "alto": f"{fmt(round(y1 - y0, 3))}mm"})
    if tipo == "imagen" and (it.get("ajuste") or "ajustar") == "ajustar":
        nuevo["ajuste"] = "cubrir"
    return nuevo


def _item(it: dict, capa: str, fmt_texto: str, marcas: bool) -> str:
    tipo = it.get("tipo", "texto")
    claves = [f"capa={capa}"]
    if marcas and it.get("id"):
        claves.append("id=" + ident(it["id"]))
    claves.append("x=" + coord(it.get("x"), "0.5"))
    claves.append("y=" + coord(it.get("y"), "0.5"))
    if it.get("ancla") in M.ANCLAS and it.get("ancla") != "center":
        claves.append("ancla={" + it["ancla"] + "}")
    for k in ("ancho", "alto"):
        if it.get(k) not in (None, ""):
            claves.append(f"{k}=" + coord(it.get(k), "0.2"))
    rot = numero(it.get("rotacion"), 0)
    if rot:
        claves.append("rotacion=" + fmt(rot))
    op = min(1.0, max(0.0, numero(it.get("opacidad"), 1)))
    if op < 1:
        claves.append("opacidad=" + fmt(op))
    pag = numero(it.get("pagina"), None)
    if pag:
        claves.append("pagina=" + str(int(pag)))
    if not it.get("visible", True):
        claves.append("visible=false")
    if tipo == "imagen":
        if it.get("ajuste") in ("ajustar", "cubrir", "estirar") and it.get("ajuste") != "ajustar":
            claves.append("ajuste=" + it["ajuste"])
        return "\\colocarimagen[" + ", ".join(claves) + "]{" + ruta(it.get("archivo")) + "}"
    if tipo == "texto":
        esc = numero(it.get("escala"), 1)
        if esc != 1:
            claves.append("escala=" + fmt(esc))
        for k in ("color", "fondo", "borde"):
            c = color(it.get(k))
            if c:
                claves.append(f"{k}={c}")
        for k, d in (("grosor", "0.08em"), ("radio", "0pt"), ("relleno", "0.4em")):
            v = dim(it.get(k), d)
            if v != d:
                claves.append(f"{k}={v}")
        if it.get("alineacion") in ("izquierda", "derecha", "justificado"):
            claves.append("alineacion=" + it["alineacion"])
        if it.get("negrita"):
            claves.append("negrita")
        if it.get("cursiva"):
            claves.append("cursiva")
        return "\\colocartexto[" + ", ".join(claves) + "]{" + T.convertir(it.get("texto"), fmt_texto) + "}"
    if tipo == "forma":
        if it.get("forma") in M.FORMAS:
            claves.append("forma=" + it["forma"])
        for k in ("fondo", "borde", "color"):
            c = color(it.get(k))
            if c:
                claves.append(f"{k}={c}")
        for k, d in (("grosor", "0.08em"), ("radio", "0pt")):
            v = dim(it.get(k), d)
            if v != d:
                claves.append(f"{k}={v}")
        for k in ("x2", "y2"):
            if it.get(k) not in (None, ""):
                claves.append(f"{k}=" + coord(it.get(k)))
        return "\\colocarforma[" + ", ".join(claves) + "]"
    return "\\colocar[" + ", ".join(claves) + "]{" + str(it.get("codigo") or "") + "}"


# --------------------------------------------------------------------- documento
def preparar_citas(m: dict):
    """Numera las citas en orden de lectura y las escribe en el estilo del proyecto.
    Devuelve el contexto de la bibliografía (o None si el póster no tiene referencias ni citas)."""
    refs = (m.get("bibliografia") or {}).get("referencias") or []
    hay_citas = []
    M.transformar_textos(m, lambda t, p: (hay_citas.append(1) if "[@" in t else None, t)[1])
    if not refs and not hay_citas:
        return None
    ctx = B.Contexto(m.get("bibliografia") or {}, m.get("idioma") or "es")
    # se numera por orden de lectura y solo con lo que se ve (un texto oculto no cuenta)
    M.transformar_textos(m, lambda t, p: (ctx.registrar(t), t)[1], solo_visibles=True)
    fmt_texto = m.get("formato_texto", "simple")
    M.transformar_textos(m, lambda t, p: B.reemplazar_citas(t, ctx, fmt_texto))
    return ctx


def _componentes(m: dict, fmt_texto: str, archivos: dict | None) -> tuple[list[str], dict]:
    """Componentes propios (Componente Lab): líneas para el preámbulo y, por elemento,
    las líneas que lo dibujan. Cada uso queda definido en el preámbulo como una orden
    (\\PCk@<id>) para que dentro del código se puedan usar las órdenes con @. Con
    «archivos» (vista previa del Lab) va en archivos aparte, así los errores traen la
    línea exacta del código del componente."""
    comps = m.get("componentes") or {}
    preambulo: list[str] = []
    llamadas: dict[str, list[str]] = {}
    usados: list[str] = []
    for fila in m["filas"]:
        if not fila.get("visible", True):
            continue
        for col in fila.get("columnas", []):
            for b in col.get("bloques", []):
                for e in b.get("elementos", []):
                    tipo = str(e.get("tipo") or "")
                    if not tipo.startswith("cmp:") or not e.get("visible", True):
                        continue
                    c = comps.get(tipo[4:])
                    eid = ident(e.get("id"))
                    if not isinstance(c, dict):
                        llamadas[e["id"]] = ["\\PCcomponenteroto{Falta la definición de este componente}"]
                        continue
                    nombre = T.escapar(str(c.get("nombre") or "componente"))
                    if c.get("modo") == C.PREAJUSTE:
                        try:
                            llamadas[e["id"]] = llamada(C.elemento_preajuste(c, e), fmt_texto)
                        except Exception as err:          # un preajuste mal guardado no rompe el póster
                            llamadas[e["id"]] = ["\\PCcomponenteroto{" + nombre + ": " + T.escapar(str(err)) + "}"]
                        continue
                    if tipo[4:] not in usados:
                        usados.append(tipo[4:])
                    cuerpo = C.cuerpo_instancia(c, e, fmt_texto, eid)
                    problema = C.llaves_equilibradas(cuerpo)
                    if problema:
                        llamadas[e["id"]] = ["\\PCcomponenteroto{" + nombre + ": " + T.escapar(problema) + "}"]
                        continue
                    if archivos is not None:
                        archivos[f"cmp-{eid}.tex"] = cuerpo
                        llamadas[e["id"]] = ["\\makeatletter\\input{cmp-" + eid + "}\\makeatother"]
                    else:
                        lineas = cuerpo.replace("#", "##").rstrip("\n").split("\n")
                        lineas[-1] += "%"
                        preambulo.append("\\expandafter\\def\\csname PCk@" + eid + "\\endcsname{%   "
                                         + T.texto_plano(c.get("nombre"), 50))
                        preambulo += lineas
                        preambulo.append("}")
                        llamadas[e["id"]] = ["\\csname PCk@" + eid + "\\endcsname"]
    propios: list[str] = []
    for cid in usados:
        c = comps[cid]
        _, pre = C.codigo_de(c)
        if not pre.strip():
            continue
        problema = C.llaves_equilibradas(pre)
        propios.append(f"% Preámbulo de «{T.texto_plano(c.get('nombre'), 60)}» (versión {c.get('version', 1)})")
        if problema:
            propios.append(f"% (se omite: {problema})")
        elif archivos is not None:
            archivos[f"cmp-pre-{cid}.tex"] = pre
            propios.append("\\input{cmp-pre-" + cid + "}")
        else:
            propios += pre.rstrip("\n").split("\n")
    todo = propios + preambulo
    if not todo:
        return [], llamadas
    return ["%% ---- Componentes propios (Componente Lab) ----", "\\makeatletter"] + todo + ["\\makeatother"], llamadas


def _elementos_de_caja(m: dict):
    for fila in m["filas"]:
        for col in fila["columnas"]:
            for b in col["bloques"]:
                for e in b["elementos"]:
                    yield fila, b, e


def vista_bibliografia(m: dict) -> dict:
    """Para el panel Referencias: cada referencia con la etiqueta y en el orden del póster,
    cuántas veces se cita y qué citas no tienen referencia."""
    m = M.normalizar(m)
    citas: dict[str, int] = {}

    def contar(t, p):
        for c in B.claves_citadas(t):
            citas[c] = citas.get(c, 0) + 1
        return t
    M.transformar_textos(m, contar, solo_visibles=True)
    ctx = preparar_citas(m) or B.Contexto(m["bibliografia"], m.get("idioma") or "es")
    listas = [e for f, b, e in _elementos_de_caja(m) if e.get("tipo") == "bibliografia"
              and f.get("visible") is not False and b.get("visible") is not False and e.get("visible") is not False]
    incluir = "todas" if listas and listas[0].get("incluir") == "todas" else "citadas"
    entradas = []
    for etiqueta, rico, r in ctx.entradas(incluir):
        entradas.append({"clave": r["clave"], "etiqueta": etiqueta, "html": rico.html(), "texto": rico.plano(),
                         "en_lista": True})
    dentro = {e["clave"] for e in entradas}
    for r in ctx.refs:
        if r["clave"] not in dentro:
            rico = ctx.est.entrada(ctx._con_sufijo(r))
            entradas.append({"clave": r["clave"], "etiqueta": "", "html": rico.html(), "texto": rico.plano(),
                             "en_lista": False})
    return {"entradas": entradas, "citas": citas, "incluir": incluir, "hay_lista": bool(listas),
            "desconocidas": [c for c in citas if c not in ctx.por_clave],
            "ejemplo": B.ejemplo_cita(ctx.clave_estilo, ctx.idioma)}


TAM_LOGO = (30, 300)          # % del tamaño base de los logos


def tam_logo(v) -> float:
    """Tamaño de un logo (en %) como escala para la plantilla."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        x = 100.0
    return round(min(TAM_LOGO[1], max(TAM_LOGO[0], x)) / 100, 3)


def _elementos(w: Escritor, b: dict, fmt_texto: str, ctx, llamadas_comp: dict, marcas: bool, sangria: str):
    """Los elementos visibles de una caja o sección."""
    for e in b.get("elementos", []):
        if not e.get("visible", True):
            continue
        with w.dentro(e["id"]):
            if marcas:
                w.w(sangria + "\\PCinicio{" + ident(e["id"]) + "}")
            lineas = llamadas_comp.get(e["id"]) if str(e.get("tipo", "")).startswith("cmp:") \
                else llamada(e, fmt_texto, ctx)
            for linea in lineas or ["\\PCcomponenteroto{Componente sin dibujar}"]:
                w.w(sangria + linea)
            if marcas:
                w.w(sangria + "\\PCfin{" + ident(e["id"]) + "}")


def es_libre(b: dict, m: dict) -> bool:
    """¿La caja está suelta de la cuadrícula? (solo en pósters y presentaciones)"""
    return bool(b.get("libre")) and not M.es_flujo(m)


def _caja_libre(w: Escritor, b: dict, m: dict, fmt_texto: str, ctx, llamadas_comp: dict, marcas: bool, aqui: bool):
    """Una caja suelta: se coloca en cualquier punto de la página (capa «libre»)."""
    lz = m.get("lienzo") or {}
    claves = ["capa=libre"]
    if marcas:
        claves.append("id=" + ident(b["id"]))
    if aqui:
        claves.append("aqui")
    claves.append("x=" + coord(b.get("x"), "0.1"))
    claves.append("y=" + coord(b.get("y"), "0.15"))
    ancla = b.get("ancla") if b.get("ancla") in M.ANCLAS else "north west"
    claves.append("ancla={" + ancla + "}")
    claves.append("ancho=" + coord(b.get("ancho"), "0.3"))
    rot = numero(b.get("rotacion"), 0)
    if rot:
        claves.append("rotacion=" + fmt(rot))
    if not b.get("visible", True):
        claves.append("visible=false")
    caja = dict(b, estirar=False)
    alto = _mm(b.get("alto"), _mm(lz.get("alto"), 0) or 1189.0)
    if alto:
        caja["opciones"] = dict(b.get("opciones") or {}, alto=f"{fmt(round(alto, 2))}mm")
    with w.dentro(b["id"]):
        w.w("\\colocar[" + ", ".join(claves) + "]{%")
        w.w("  \\begin{caja}[" + _claves_bloque(caja, fmt_texto, False) + "]")
        _elementos(w, b, fmt_texto, ctx, llamadas_comp, marcas, "    ")
        w.w("  \\end{caja}}")


def _fila(w: Escritor, fila: dict, m: dict, fmt_texto: str, ctx, llamadas_comp: dict, marcas: bool) -> list:
    """Escribe una fila con sus columnas y cajas. Devuelve las cajas sueltas que contiene."""
    libres = []
    if not fila.get("visible", True):
        w.w(f"% fila oculta: {fila.get('id')}")
        return libres
    cols = [c for c in fila.get("columnas", [])]
    for col in cols:
        libres += [b for b in col.get("bloques", []) if es_libre(b, m)]
    if not cols or not any(not es_libre(b, m) for col in cols for b in col.get("bloques", [])):
        if not libres and cols:
            pass                    # fila vacía: conserva su hueco en la cuadrícula
        else:
            return libres           # solo cajas sueltas: no ocupa sitio
    if not cols:
        return libres
    rejilla = int(numero(fila.get("rejilla"), 0)) or sum(max(1, int(numero(c.get("abarca"), 1))) for c in cols)
    opc = [f"columnas={rejilla}"]
    if marcas:
        opc.insert(0, "id=" + ident(fila["id"]))
    alto = str(fila.get("alto") or "auto").strip()
    if alto == "llenar":
        opc.append("alto=llenar")
    elif alto not in ("", "auto"):
        d = dim(alto, "")
        if d:
            opc.append("alto=" + d)
    if str(fila.get("separacion") or "").strip():
        opc.append("separacion=" + dim(fila["separacion"], "20mm"))
    if str(fila.get("despues") or "").strip():
        opc.append("despues=" + dim(fila["despues"], "0.9em"))
    if fila.get("igualar") is False:
        opc.append("igualar=false")
    w.w("")
    with w.dentro(fila["id"]):
        w.w("\\begin{fila}[" + ", ".join(opc) + "]")
        for col in cols:
            copc = [f"abarca={max(1, int(numero(col.get('abarca'), 1)))}"]
            if marcas:
                copc.insert(0, "id=" + ident(col["id"]))
            if col.get("distribucion") in ("arriba", "abajo", "centro"):
                copc.append("distribucion=" + col["distribucion"])
            with w.dentro(col["id"]):
                w.w("  \\begin{columna}[" + ", ".join(copc) + "]")
                for b in col.get("bloques", []):
                    if es_libre(b, m):
                        continue
                    with w.dentro(b["id"]):
                        w.w("    \\begin{caja}[" + _claves_bloque(b, fmt_texto, marcas) + "]")
                        _elementos(w, b, fmt_texto, ctx, llamadas_comp, marcas, "      ")
                        w.w("    \\end{caja}")
                w.w("  \\end{columna}")
        w.w("\\end{fila}")
    return libres


def _cuerpo_poster(w, m, fmt_texto, ctx, llamadas_comp, marcas):
    cab = m["cabecera"]
    if cab.get("visible", True):
        with w.dentro("cabecera"):
            w.w("\\cabecera" + _opciones_cabecera(m))
    libres = []
    for fila in m["filas"]:
        libres += _fila(w, fila, m, fmt_texto, ctx, llamadas_comp, marcas)
    pie = m["pie"]
    if pie.get("visible", True):
        partes = []
        c = color(pie.get("fondo"))
        if c:
            partes.append("fondo=" + c)
        c = color(pie.get("color_texto"))
        if c:
            partes.append("color texto=" + c)
        opc = "[" + ", ".join(partes) + "]" if partes else ""
        w.w("")
        with w.dentro("pie"):
            w.w("\\piedeposter" + opc + "{" + T.convertir(pie.get("izquierda"), fmt_texto, False) + "}{" +
                T.convertir(pie.get("centro"), fmt_texto, False) + "}{" +
                T.convertir(pie.get("derecha"), fmt_texto, False) + "}")
    if libres:
        w.w("")
        w.w("%% ---- Cajas sueltas (posición libre) ----")
        for b in libres:
            _caja_libre(w, b, m, fmt_texto, ctx, llamadas_comp, marcas, aqui=False)


def _cuerpo_presentacion(w, m, fmt_texto, ctx, llamadas_comp, marcas):
    for pg, filas in M.paginas_con_filas(m):
        if pg.get("visible", True) is False:
            w.w(f"% diapositiva oculta: {pg.get('id')}")
            continue
        claves = []
        if marcas:
            claves.append("id=" + ident(pg["id"]))
        diseno = pg.get("diseno") if pg.get("diseno") in M.DISENOS_PAGINA else "contenido"
        if diseno != "contenido":
            claves.append("diseno=" + diseno)
        if diseno in ("contenido", "seccion"):
            titulo = T.convertir(pg.get("nombre"), fmt_texto, False)
            if titulo:
                claves.append("titulo={" + titulo + "}")
            sub = T.convertir(pg.get("subtitulo"), fmt_texto, False)
            if sub:
                claves.append("subtitulo={" + sub + "}")
        if pg.get("estilo") in M.ESTILOS_TITULO_PAGINA:
            claves.append("estilo=" + pg["estilo"])
        if pg.get("pie", True) is False:
            claves.append("pie=false")
        c = color(pg.get("fondo"))
        if c:
            claves.append("fondo=" + c)
        w.w("")
        w.w("%% ---- " + T.texto_plano(pg.get("nombre"), 60) + " ----")
        with w.dentro(pg["id"]):
            w.w("\\diapositiva[" + ", ".join(claves) + "]")
        libres = []
        for fila in filas:
            libres += _fila(w, fila, m, fmt_texto, ctx, llamadas_comp, marcas)
        for b in libres:
            _caja_libre(w, b, m, fmt_texto, ctx, llamadas_comp, marcas, aqui=True)


def _nivel_tex(b: dict, clase: str) -> int:
    """Nivel de la plantilla (0 capítulo, 1 sección…) de una sección del modelo."""
    n = int(numero(b.get("nivel"), 1) or 1)
    n = max(1, min(4 if clase == "tesis" else 3, n))
    return n - 1 if clase == "tesis" else n


def _cuerpo_flujo(w, m, fmt_texto, ctx, llamadas_comp, marcas):
    clase = m.get("clase")
    doc = m.get("documento") or {}
    cab = m["cabecera"]
    port = doc.get("portada") or {}
    tesis = clase == "tesis"
    cols2 = int(numero(doc.get("columnas"), 1)) == 2
    nivel_frente = "0" if tesis else "1"

    def txt(v, parrafos=False):
        return T.convertir(v, fmt_texto, parrafos)

    def resumenes() -> list[str]:
        lineas = []
        for suf in ("", "2"):
            if str(doc.get("resumen" + suf) or "").strip():
                marca = "[doc-resumen" + suf + "]" if marcas else ""
                lineas.append("\\PCresumen" + marca + "{" + txt(doc.get("titulo_resumen" + suf) or "Resumen") + "}{" +
                              txt(doc.get("resumen" + suf), True) + "}")
            if str(doc.get("palabras_clave" + suf) or "").strip():
                lineas.append("\\PCpalabrasclave{" + txt(doc.get("titulo_palabras" + suf) or "Palabras clave") + "}{" +
                              txt(doc.get("palabras_clave" + suf)) + "}")
        return lineas

    def indices():
        for clave, titulo, orden in (("indice", "titulo_indice", "\\PCindice"),
                                     ("lista_figuras", "titulo_figuras", "\\PClistafiguras"),
                                     ("lista_tablas", "titulo_tablas", "\\PClistatablas")):
            if doc.get(clave):
                with w.dentro("documento"):
                    w.w("\\PCseccion[nivel=" + nivel_frente + ", numerar=false, indice=false]{" +
                        txt(doc.get(titulo) or "Índice") + "}")
                    w.w(orden)

    if tesis:
        if port.get("visible", True) and cab.get("visible", True):
            claves = []
            for k in ("institucion", "dependencia", "tipo", "grado", "presenta", "director", "lugar", "fecha"):
                v = txt(port.get(k))
                if v:
                    claves.append(k + "={" + v + "}")
            with w.dentro("cabecera"):
                w.w("\\PCportada[" + ", ".join(claves) + "]")
        w.w("\\PCnumeracion{roman}")
        with w.dentro("documento"):
            if str(doc.get("dedicatoria") or "").strip():
                w.w("\\clearpage\\thispagestyle{pcvacia}\\vspace*{0.25\\textheight}")
                w.w("{\\raggedleft\\itshape " + txt(doc.get("dedicatoria"), True) + "\\par}")
            if str(doc.get("agradecimientos") or "").strip():
                w.w("\\PCseccion[nivel=0, numerar=false, indice=false]{" +
                    txt(doc.get("titulo_agradecimientos") or "Agradecimientos") + "}")
                w.w(txt(doc.get("agradecimientos"), True))
            for suf in ("", "2"):
                if str(doc.get("resumen" + suf) or "").strip():
                    w.w("\\PCseccion[nivel=0, numerar=false, indice=false" + (", id=doc-resumen" + suf if marcas else "") +
                        "]{" + txt(doc.get("titulo_resumen" + suf) or "Resumen") + "}")
                    w.w(txt(doc.get("resumen" + suf), True))
                    if str(doc.get("palabras_clave" + suf) or "").strip():
                        w.w("\\par\\vspace{1em}\\noindent\\textbf{" + txt(doc.get("titulo_palabras" + suf) or "Palabras clave") +
                            ":} " + txt(doc.get("palabras_clave" + suf)))
                    if marcas:
                        w.w("\\PCfinseccion{doc-resumen" + suf + "}")
        indices()
        w.w("\\PCnumeracion{arabic}")
    else:
        frente = []
        if cab.get("visible", True):
            frente.append("\\PCtitulodoc")
        frente += resumenes()
        with w.dentro("cabecera"):
            if cols2:
                w.w("\\PCdoscolumnas{%")
                for linea in frente:
                    w.w("  " + linea)
                w.w("}")
            else:
                for linea in frente:
                    w.w(linea)
        indices()
    for b in M.bloques_de_flujo(m):
        if not b.get("visible", True):
            continue
        titulo = T.convertir(b.get("titulo"), fmt_texto, False)
        w.w("")
        with w.dentro(b["id"]):
            if titulo and b.get("mostrar_titulo", True):
                claves = ["nivel=" + str(_nivel_tex(b, clase))]
                if marcas:
                    claves.append("id=" + ident(b["id"]))
                if b.get("numerar") is False:
                    claves.append("numerar=false")
                if b.get("salto"):
                    claves.append("salto")
                if b.get("apendice"):
                    claves.append("apendice")
                w.w("\\PCseccion[" + ", ".join(claves) + "]{" + titulo + "}")
            else:
                if b.get("salto"):
                    w.w("\\clearpage")
                if marcas:
                    w.w("\\PCinicio{" + ident(b["id"]) + "}")
            _elementos(w, b, fmt_texto, ctx, llamadas_comp, marcas, "  ")
            if marcas:
                w.w("\\PCfinseccion{" + ident(b["id"]) + "}")


def generar(m: dict, marcas: bool = True, archivos: dict | None = None,
            imprenta: dict | None = None) -> tuple[str, dict]:
    """El .tex del documento. Si se pasa «archivos» (un diccionario), el código de los
    componentes propios va en archivos aparte (nombre → texto), como en la vista previa del Lab.
    «imprenta» ({sangrado_mm, marcas_corte, directorio}) prepara el PDF para la imprenta."""
    m = M.normalizar(m)
    ctx = preparar_citas(m)
    fmt_texto = m.get("formato_texto", "simple")
    clase = m.get("clase", "poster")
    nombre_clase = M.CLASES[clase]["nombre"]
    pre_comp, llamadas_comp = _componentes(m, fmt_texto, archivos)
    w = Escritor()
    lua = M.motor(m) == "lualatex"
    if lua:
        w.w("% !TEX program = lualatex")
    w.w("%% ============================================================================")
    w.w(f"%%  {nombre_clase} generado por DocsLab con la plantilla postercientifico.sty (v3).")
    if lua:
        w.w("%%  Compila con LuaLaTeX (usa tipografías propias, en la carpeta fuentes/);")
        w.w("%%  repite mientras salga «Rerun» (Overleaf lo hace solo).")
    else:
        w.w("%%  Compila con pdfLaTeX; repite mientras salga «Rerun» (Overleaf lo hace solo).")
    w.w("%% ============================================================================")
    w.w(compilador.SIN_EPSTOPDF + "   % sin conversión de .eps (no hace falta)")
    w.w("\\documentclass{article}")
    w.w("\\usepackage{postercientifico}")
    w.w("%% (la línea siguiente acelera la compilación en DocsLab; en Overleaf no hace nada)")
    w.w("\\csname endofdump\\endcsname")
    for linea in _familias_propias_tex(m):
        w.w(linea)
    w.w(_posterconfig(m, marcas, imprenta))
    if m["latex"].get("preambulo", "").strip():
        w.w("%% ---- Preámbulo propio ----")
        w.w(m["latex"]["preambulo"].rstrip())
    for linea in pre_comp:
        w.w(linea)
    _cabecera(w, m, fmt_texto)
    if not M.es_flujo(m) and any(es_libre(b, m) for b, _ in _cajas(m)):
        w.w("\\nuevacapa[z=5]{libre}   % cajas sueltas: delante del contenido, detrás de la capa «frente»")
    _capas(w, m, fmt_texto, marcas, imprenta)
    w.w("")
    w.w("\\begin{document}")
    if m["latex"].get("antes", "").strip():
        w.w(m["latex"]["antes"].rstrip())
    if clase == "presentacion":
        _cuerpo_presentacion(w, m, fmt_texto, ctx, llamadas_comp, marcas)
    elif M.es_flujo(m):
        _cuerpo_flujo(w, m, fmt_texto, ctx, llamadas_comp, marcas)
    else:
        _cuerpo_poster(w, m, fmt_texto, ctx, llamadas_comp, marcas)
    if m["latex"].get("despues", "").strip():
        w.w(m["latex"]["despues"].rstrip())
    w.w("\\end{document}")
    return w.texto(), w.mapa


def _cajas(m: dict):
    """(caja, fila) de todo el contenido."""
    for fila in m.get("filas", []):
        for col in fila.get("columnas", []):
            for b in col.get("bloques", []):
                yield b, fila
