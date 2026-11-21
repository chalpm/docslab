# SPDX-License-Identifier: AGPL-3.0-only
"""Modelo de un documento estructurado (lo que edita la aplicación): póster,
presentación, documento, artículo o tesis.

El modelo es un diccionario JSON. normalizar() completa los valores que falten,
así un proyecto guardado con una versión anterior sigue abriéndose.
"""
from __future__ import annotations

import copy
import secrets
import string

from ..documento import variantes

ESQUEMA = 1   # versión del esquema del modelo JSON (entero; clave "version_esquema"; ver docs/MIGRACIONES.md)

TAMANOS = {
    "A0": ("841mm", "1189mm"), "A1": ("594mm", "841mm"), "A2": ("420mm", "594mm"),
    "A3": ("297mm", "420mm"), "A4": ("210mm", "297mm"), "B0": ("1000mm", "1414mm"),
    "B1": ("707mm", "1000mm"), "24x36in": ("24in", "36in"), "36x48in": ("36in", "48in"),
    "42x56in": ("42in", "56in"), "48x72in": ("48in", "72in"), "70x100cm": ("70cm", "100cm"),
    "90x120cm": ("90cm", "120cm"), "100x140cm": ("100cm", "140cm"),
    # documentos
    "Carta": ("215.9mm", "279.4mm"), "Oficio": ("215.9mm", "340mm"), "A5": ("148mm", "210mm"),
    "B5": ("176mm", "250mm"),
    # diapositivas (lado corto, lado largo; se usan en horizontal)
    "16:9": ("190.5mm", "338.67mm"), "16:10": ("190.5mm", "304.8mm"), "4:3": ("190.5mm", "254mm"),
}

# Clases de documento. «flujo»: el texto corre de una página a la siguiente (secciones);
# si no, cada página es un lienzo con su cuadrícula de filas, columnas y cajas.
CLASES = {
    "poster": {"nombre": "Póster", "flujo": False, "tamanos": ["A0", "A1", "A2", "A3", "A4", "B0", "B1", "24x36in",
               "36x48in", "42x56in", "48x72in", "70x100cm", "90x120cm", "100x140cm"]},
    "presentacion": {"nombre": "Presentación", "flujo": False, "tamanos": ["16:9", "16:10", "4:3"]},
    "documento": {"nombre": "Documento", "flujo": True, "tamanos": ["A4", "Carta", "Oficio", "A5", "B5"]},
    "paper": {"nombre": "Artículo", "flujo": True, "tamanos": ["A4", "Carta"]},
    "tesis": {"nombre": "Tesis", "flujo": True, "tamanos": ["A4", "Carta", "B5"]},
}
DISENOS_PAGINA = ["contenido", "portada", "seccion", "vacia"]
ESTILOS_TITULO_PAGINA = ["banda", "linea", "simple"]
NIVELES = {"tesis": ["Capítulo", "Sección", "Subsección", "Apartado"],
           "paper": ["Sección", "Subsección", "Apartado"], "documento": ["Sección", "Subsección", "Apartado"]}

TEMAS = {
    # sobrios (los primeros que se ofrecen)
    "pizarra": dict(primario="3E5468", secundario="6A8196", acento="A9803A", fondo="FFFFFF",
                    fondo_bloque="F2F4F6", texto="22272C", tenue="5D666E", contraste="FFFFFF"),
    "salvia": dict(primario="4A6352", secundario="7A9483", acento="A5634A", fondo="FCFCFA",
                   fondo_bloque="EFF2EE", texto="232823", tenue="5B635D", contraste="FFFFFF"),
    "niebla": dict(primario="4B5A6B", secundario="7D8C9E", acento="4F7F7C", fondo="FFFFFF",
                   fondo_bloque="F1F3F5", texto="24282D", tenue="5F6770", contraste="FFFFFF"),
    "ciruela": dict(primario="5A4660", secundario="8C7891", acento="967639", fondo="FFFEFC",
                    fondo_bloque="F4F1F3", texto="2A242B", tenue="655D66", contraste="FFFFFF"),
    "grafito": dict(primario="33393E", secundario="6B747C", acento="5C7F99", fondo="FFFFFF",
                    fondo_bloque="F3F4F4", texto="1F2326", tenue="5C646B", contraste="FFFFFF"),
    # vivos
    "azul": dict(primario="1F4E79", secundario="2A78D6", acento="E8743B", fondo="FFFFFF",
                 fondo_bloque="F3F5F8", texto="1E2329", tenue="59636E", contraste="FFFFFF"),
    "verde": dict(primario="14532D", secundario="2F855A", acento="C2410C", fondo="FBFAF6",
                  fondo_bloque="EEF3EC", texto="1F2421", tenue="5B6660", contraste="FFFFFF"),
    "burdeos": dict(primario="7A1F2B", secundario="B23A48", acento="C98A1B", fondo="FFFDF9",
                    fondo_bloque="F6EEEA", texto="2A1F1F", tenue="6B5B5B", contraste="FFFFFF"),
    "morado": dict(primario="4C1D95", secundario="7C3AED", acento="0E7490", fondo="FFFFFF",
                   fondo_bloque="F4F1FB", texto="1E1B2E", tenue="5E5873", contraste="FFFFFF"),
    "gris": dict(primario="222222", secundario="4B5563", acento="0E7490", fondo="FFFFFF",
                 fondo_bloque="F4F4F5", texto="18181B", tenue="52525B", contraste="FFFFFF"),
    "arena": dict(primario="7C4A1E", secundario="B7791F", acento="2B6CB0", fondo="FFFBF2",
                  fondo_bloque="F5EBDA", texto="2D2418", tenue="6E5E4B", contraste="FFFFFF"),
    "oscuro": dict(primario="38BDF8", secundario="7DD3FC", acento="FBBF24", fondo="0F172A",
                   fondo_bloque="1E293B", texto="E2E8F0", tenue="94A3B8", contraste="0F172A"),
}

GRUPOS_TEMAS = [
    {"nombre": "Sobrios", "temas": ["pizarra", "salvia", "niebla", "ciruela", "grafito"]},
    {"nombre": "Vivos", "temas": ["azul", "verde", "burdeos", "morado", "gris", "arena", "oscuro"]},
]

# Idioma del póster: separación de palabras (babel), comillas y palabras de las referencias
IDIOMAS = {
    "es": {"nombre": "Español", "babel": "spanish", "figura": "Figura", "tabla": "Tabla", "capitulo": "Capítulo",
           "apendice": "Apéndice", "resumen": "Resumen", "palabras": "Palabras clave", "indice": "Índice",
           "figuras": "Índice de figuras", "tablas": "Índice de tablas", "referencias": "Referencias"},
    "en": {"nombre": "English", "babel": "english", "figura": "Figure", "tabla": "Table", "capitulo": "Chapter",
           "apendice": "Appendix", "resumen": "Abstract", "palabras": "Keywords", "indice": "Contents",
           "figuras": "List of figures", "tablas": "List of tables", "referencias": "References"},
    "pt": {"nombre": "Português", "babel": "portuguese", "figura": "Figura", "tabla": "Tabela", "capitulo": "Capítulo",
           "apendice": "Apêndice", "resumen": "Resumo", "palabras": "Palavras-chave", "indice": "Sumário",
           "figuras": "Lista de figuras", "tablas": "Lista de tabelas", "referencias": "Referências"},
    "fr": {"nombre": "Français", "babel": "french", "figura": "Figure", "tabla": "Tableau", "capitulo": "Chapitre",
           "apendice": "Annexe", "resumen": "Résumé", "palabras": "Mots-clés", "indice": "Table des matières",
           "figuras": "Liste des figures", "tablas": "Liste des tableaux", "referencias": "Références"},
    "de": {"nombre": "Deutsch", "babel": "ngerman", "figura": "Abbildung", "tabla": "Tabelle", "capitulo": "Kapitel",
           "apendice": "Anhang", "resumen": "Zusammenfassung", "palabras": "Schlüsselwörter",
           "indice": "Inhaltsverzeichnis", "figuras": "Abbildungsverzeichnis", "tablas": "Tabellenverzeichnis",
           "referencias": "Literatur"},
    "it": {"nombre": "Italiano", "babel": "italian", "figura": "Figura", "tabla": "Tabella", "capitulo": "Capitolo",
           "apendice": "Appendice", "resumen": "Sommario", "palabras": "Parole chiave", "indice": "Indice",
           "figuras": "Elenco delle figure", "tablas": "Elenco delle tabelle", "referencias": "Riferimenti"},
}

# Familias tipográficas. «clasica»: las PostScript que trae cualquier LaTeX (con LuaLaTeX,
# sus gemelas TeX Gyre); «libre»: paquetes de TeX Live, solo con pdfLaTeX. Las propias
# (archivos .ttf u .otf del proyecto) van en tipografia.propias y obligan a usar LuaLaTeX.
FAMILIAS_INFO = {
    "helvetica": {"nombre": "Helvetica", "tipo": "sans", "grupo": "clasica"},
    "avantgarde": {"nombre": "Avant Garde", "tipo": "sans", "grupo": "clasica"},
    "palatino": {"nombre": "Palatino", "tipo": "serif", "grupo": "clasica"},
    "times": {"nombre": "Times", "tipo": "serif", "grupo": "clasica"},
    "bookman": {"nombre": "Bookman", "tipo": "serif", "grupo": "clasica"},
    "charter": {"nombre": "Charter", "tipo": "serif", "grupo": "clasica"},
    "sourcesans": {"nombre": "Source Sans", "tipo": "sans", "grupo": "libre", "paquete": "sourcesanspro"},
    "fira": {"nombre": "Fira Sans", "tipo": "sans", "grupo": "libre", "paquete": "FiraSans"},
    "roboto": {"nombre": "Roboto", "tipo": "sans", "grupo": "libre", "paquete": "roboto"},
    "lato": {"nombre": "Lato", "tipo": "sans", "grupo": "libre", "paquete": "lato"},
    "opensans": {"nombre": "Open Sans", "tipo": "sans", "grupo": "libre", "paquete": "opensans"},
    "notosans": {"nombre": "Noto Sans", "tipo": "sans", "grupo": "libre", "paquete": "noto-sans"},
    "plexsans": {"nombre": "IBM Plex Sans", "tipo": "sans", "grupo": "libre", "paquete": "plex-sans"},
    "atkinson": {"nombre": "Atkinson Hyperlegible", "tipo": "sans", "grupo": "libre", "paquete": "atkinson"},
    "montserrat": {"nombre": "Montserrat", "tipo": "sans", "grupo": "libre", "paquete": "montserrat"},
    "raleway": {"nombre": "Raleway", "tipo": "sans", "grupo": "libre", "paquete": "raleway"},
    "cabin": {"nombre": "Cabin", "tipo": "sans", "grupo": "libre", "paquete": "cabin"},
    "inter": {"nombre": "Inter", "tipo": "sans", "grupo": "libre", "paquete": "inter"},
    "libertinus": {"nombre": "Libertinus Serif", "tipo": "serif", "grupo": "libre", "paquete": "libertinus"},
    "ebgaramond": {"nombre": "EB Garamond", "tipo": "serif", "grupo": "libre", "paquete": "ebgaramond"},
    "merriweather": {"nombre": "Merriweather", "tipo": "serif", "grupo": "libre", "paquete": "merriweather"},
    "sourceserif": {"nombre": "Source Serif", "tipo": "serif", "grupo": "libre", "paquete": "sourceserifpro"},
    "crimson": {"nombre": "Crimson", "tipo": "serif", "grupo": "libre", "paquete": "crimson"},
    "notoserif": {"nombre": "Noto Serif", "tipo": "serif", "grupo": "libre", "paquete": "noto-serif"},
    "plexserif": {"nombre": "IBM Plex Serif", "tipo": "serif", "grupo": "libre", "paquete": "plex-serif"},
}
FAMILIAS = list(FAMILIAS_INFO)
PREFIJO_PROPIA = "propia-"
ESTILOS_CABECERA = ["banda", "clara", "minima", "degradado", "imagen"]
ESTILOS_PIE = ["banda", "clara", "ninguno"]
FORMAS = ["rectangulo", "circulo", "elipse", "linea", "flecha"]
ANCLAS = ["center", "north west", "north", "north east", "west", "east", "south west", "south", "south east"]


def nuevo_id(prefijo: str = "x") -> str:
    alfabeto = string.ascii_lowercase + string.digits
    return prefijo + "-" + "".join(secrets.choice(alfabeto) for _ in range(6))


DEFECTO = {
    "version_esquema": ESQUEMA,
    "clase": "poster",       # poster | presentacion | documento | paper | tesis
    "formato_texto": "simple",
    "idioma": "",            # "" = sin definir (reglas del inglés, como siempre en LaTeX)
    "lienzo": {"tamano": "A0", "orientacion": "vertical", "ancho": "841mm", "alto": "1189mm",
               "margen": "28mm", "margen_superior": "", "margen_inferior": "", "margen_izquierdo": "",
               "margen_derecho": "", "libre": False},
    "tipografia": {"fuente": 30, "interlinea": 1.28, "familia": "helvetica", "familia_titulos": "", "propias": [],
                   "escalas": {"titulo": 3.3, "subtitulo": 1.75, "autores": 1.4, "afiliaciones": 1.0,
                               "bloque": 1.35, "pie": 0.8, "cita": 1.5, "cifra": 3.2,
                               "referencias": 0.75, "piedeposter": 0.8}},
    "colores": dict(tema="pizarra", **TEMAS["pizarra"]),
    "estilo": {"bloque": "barra", "radio": "0.3em", "relleno": "0.75em",
               "separacion_columnas": "20mm", "separacion_filas": "", "separacion_bloques": "0.9em",
               "separacion_imagenes": "0.45em", "separacion_elementos": "0.35em",
               "mostrar_titulos": True, "numerar_bloques": False, "alineacion_titulos": "izquierda",
               "alinear_texto": "justificado", "sombra": False, "numerar_figuras": True, "nombre_figura": "Figura"},
    "cabecera": {"visible": True, "estilo": "banda", "alineacion": "centro", "titulo": "Título del póster",
                 "subtitulo": "", "autores": "", "afiliaciones": "", "logo_izquierdo": "",
                 "logo_derecho": "", "ancho_logos": 0.15, "alto_logos": "5.5em",
                 "tam_logo_izquierdo": 100, "tam_logo_derecho": 100, "fondo": "",
                 "color_texto": "", "imagen": "", "oscurecer": 0.45},
    "filas": [],
    "pie": {"visible": True, "estilo": "banda", "izquierda": "", "centro": "", "derecha": "",
            "fondo": "", "color_texto": ""},
    "contenido_visible": True,
    "capas": [],
    "latex": {"preambulo": "", "antes": "", "despues": ""},
    "bibliografia": {"estilo": "apa", "referencias": []},
    "componentes": {},
    # presentaciones: una entrada por diapositiva; cada fila dice a cuál pertenece (fila["pag"])
    "paginas": [],
    "presentacion": {"pie": "", "numerar": True, "titulo": "banda", "progreso": False, "escala_titulo": 1.5},
    # documentos, artículos y tesis
    "documento": {"columnas": 1, "parrafos": "sangria", "numerar_paginas": True, "numerar_secciones": True,
                  "encabezado": "", "resumen": "", "titulo_resumen": "Resumen", "palabras_clave": "",
                  "titulo_palabras": "Palabras clave", "resumen2": "", "titulo_resumen2": "Abstract",
                  "palabras_clave2": "", "titulo_palabras2": "Keywords",
                  "indice": False, "titulo_indice": "Índice", "lista_figuras": False,
                  "titulo_figuras": "Índice de figuras", "lista_tablas": False, "titulo_tablas": "Índice de tablas",
                  "numerar_tablas": True, "nombre_tabla": "Tabla", "nombre_capitulo": "Capítulo",
                  "nombre_apendice": "Apéndice", "escala_seccion": 1.45, "escala_capitulo": 2.2,
                  "dedicatoria": "", "agradecimientos": "", "titulo_agradecimientos": "Agradecimientos",
                  "portada": {"visible": False, "institucion": "", "dependencia": "", "tipo": "TESIS", "grado": "",
                              "presenta": "", "director": "", "lugar": "", "fecha": ""}},
}

PAGINA_DEFECTO = {"visible": True, "nombre": "", "subtitulo": "", "diseno": "contenido", "estilo": "",
                  "pie": True, "fondo": "", "libre": False, "notas": ""}
# Posición de una caja «libre» (suelta de la cuadrícula): fracciones del lienzo desde arriba a la izquierda
LIBRE_DEFECTO = {"x": 0.1, "y": 0.15, "ancho": 0.3, "rotacion": 0}

CAPAS_DEFECTO = [
    {"id": "fondo", "nombre": "Fondo", "z": -10, "visible": True, "opacidad": 1, "elementos": []},
    {"id": "frente", "nombre": "Frente", "z": 10, "visible": True, "opacidad": 1, "elementos": []},
]

FILA_DEFECTO = {"visible": True, "alto": "auto", "rejilla": 0, "separacion": "", "despues": "",
                "igualar": True, "columnas": []}
# Formatos de imagen de un proyecto que Pillow puede abrir (lo demás se convierte a PNG al subirlo)
FORMATOS_IMAGEN = ("PNG", "JPEG")
COLUMNA_DEFECTO = {"abarca": 1, "distribucion": "repartir", "bloques": []}
BLOQUE_DEFECTO = {"visible": True, "titulo": "", "mostrar_titulo": True, "estilo": "", "numero": "",
                  "estirar": False, "opciones": {}, "elementos": []}
ITEM_DEFECTO = {"visible": True, "tipo": "texto", "x": 0.5, "y": 0.5, "ancla": "center", "ancho": "",
                "alto": "", "rotacion": 0, "opacidad": 1, "pagina": ""}
ITEM_TIPOS = {
    "imagen": {"archivo": "", "ajuste": "ajustar", "ancho": 0.2},
    "texto": {"texto": "Texto", "escala": 1, "color": "", "fondo": "", "borde": "", "grosor": "0.08em",
              "radio": "0pt", "relleno": "0.4em", "alineacion": "centro", "negrita": False, "cursiva": False},
    "forma": {"forma": "rectangulo", "fondo": "", "borde": "", "grosor": "0.08em", "radio": "0pt",
              "x2": "", "y2": "", "color": "", "ancho": 0.2, "alto": ""},
    "latex": {"codigo": ""},
}


def _completar(destino: dict, defecto: dict) -> dict:
    for k, v in defecto.items():
        if k not in destino or destino[k] is None:
            destino[k] = copy.deepcopy(v)
        elif isinstance(v, dict) and isinstance(destino[k], dict) and k not in ("opciones",):
            _completar(destino[k], v)
    return destino


def normalizar(m: dict | None) -> dict:
    """Lleva un modelo al esquema actual (migraciones), completa los valores por
    defecto y asegura los identificadores. Lanza migraciones.ErrorEsquema si el
    modelo es de un esquema más nuevo o no se puede migrar."""
    from .migraciones import migrar
    m, _ = migrar(m if isinstance(m, dict) else {})
    _completar(m, DEFECTO)
    m["version_esquema"] = ESQUEMA
    from ..documento import bibliografia as B
    bib = m.get("bibliografia")
    if not isinstance(bib, dict):
        bib = m["bibliografia"] = {"estilo": "apa", "referencias": []}
    if bib.get("estilo") not in B.ESTILOS:
        bib["estilo"] = "apa"
    bib["referencias"] = B.normalizar_lista(bib.get("referencias"))
    if not isinstance(m.get("componentes"), dict):
        m["componentes"] = {}
    if m.get("clase") not in CLASES:
        m["clase"] = "poster"
    if not isinstance(m.get("paginas"), list):
        m["paginas"] = []
    if not m.get("capas"):
        m["capas"] = copy.deepcopy(CAPAS_DEFECTO)
    ids = set()

    def asegurar(obj, prefijo):
        i = obj.get("id")
        if not i or i in ids:
            i = nuevo_id(prefijo)
            obj["id"] = i
        ids.add(i)

    for capa in m["capas"]:
        _completar(capa, {"nombre": capa.get("id", "capa"), "z": 1, "visible": True, "opacidad": 1,
                          "elementos": []})
        if not capa.get("id"):
            capa["id"] = nuevo_id("capa")
        ids.add(capa["id"])
        for it in capa["elementos"]:
            _completar(it, ITEM_DEFECTO)
            _completar(it, ITEM_TIPOS.get(it.get("tipo"), {}))
            asegurar(it, "a")
    if m["clase"] == "presentacion":
        m["paginas"] = [pg for pg in m["paginas"] if isinstance(pg, dict)]
        if not m["paginas"]:
            m["paginas"] = [{"nombre": "Diapositiva 1"}]
        for pg in m["paginas"]:
            _completar(pg, PAGINA_DEFECTO)
            if pg.get("diseno") not in DISENOS_PAGINA:
                pg["diseno"] = "contenido"
            asegurar(pg, "p")
        ids_pag = [pg["id"] for pg in m["paginas"]]
        anterior = ids_pag[0]
        for fila in m["filas"]:                  # cada fila pertenece a una diapositiva
            if fila.get("pag") not in ids_pag:
                fila["pag"] = anterior
            anterior = fila["pag"]
        orden = {i: n for n, i in enumerate(ids_pag)}
        m["filas"].sort(key=lambda f: orden[f["pag"]])       # estable: conserva el orden dentro de cada una
    for fila in m["filas"]:
        _completar(fila, FILA_DEFECTO)
        asegurar(fila, "f")
        for col in fila["columnas"]:
            _completar(col, COLUMNA_DEFECTO)
            asegurar(col, "c")
            for b in col["bloques"]:
                _completar(b, BLOQUE_DEFECTO)
                asegurar(b, "b")
                if b.get("libre"):
                    for k, v in LIBRE_DEFECTO.items():
                        if b.get(k) in (None, ""):
                            b[k] = v
                for e in b["elementos"]:
                    if e.get("tipo") in variantes.POR_CLAVE:
                        base = variantes.elemento_nuevo(e["tipo"], e.get("id") or "")
                        for k, v in base.items():
                            if k not in e:
                                e[k] = v
                    elif str(e.get("tipo") or "").startswith("cmp:"):      # componente propio (Componente Lab)
                        comp = m["componentes"].get(e["tipo"][4:])
                        for campo in (comp.get("campos") or []) if isinstance(comp, dict) else []:
                            if isinstance(campo, dict) and campo.get("nombre") and campo["nombre"] not in e:
                                e[campo["nombre"]] = copy.deepcopy(campo.get("defecto", ""))
                    e.setdefault("visible", True)
                    asegurar(e, "e")
    _limpiar_animaciones(m)
    return m


def _limpiar_animaciones(m: dict) -> None:
    """Animaciones y transiciones para PowerPoint (opcionales): se dejan solo si son válidas."""
    from ..salidas.animaciones import normalizar_animacion, normalizar_transicion

    def anim(obj):
        if "animacion" in obj:
            a = normalizar_animacion(obj["animacion"])
            if a:
                obj["animacion"] = a
            else:
                del obj["animacion"]

    def trans(obj):
        if "transicion" in obj:
            tr = normalizar_transicion(obj["transicion"])
            if tr:
                obj["transicion"] = tr
            else:
                del obj["transicion"]
    trans(m)
    for pg in m.get("paginas") or []:
        trans(pg)
    for fila in m.get("filas") or []:
        for col in fila.get("columnas") or []:
            for b in col.get("bloques") or []:
                anim(b)
                for e in b.get("elementos") or []:
                    anim(e)
    for capa in m.get("capas") or []:
        for it in capa.get("elementos") or []:
            anim(it)


def familias_propias(m: dict) -> dict:
    """Las tipografías propias del póster: id → {nombre, archivos, ...} (solo las bien formadas)."""
    salida = {}
    for f in (m.get("tipografia") or {}).get("propias") or []:
        if isinstance(f, dict) and str(f.get("id") or "").startswith(PREFIJO_PROPIA) \
                and isinstance(f.get("archivos"), dict) and f["archivos"].get("normal"):
            salida[f["id"]] = f
    return salida


def motor(m: dict) -> str:
    """El programa que compila el póster: LuaLaTeX si usa una tipografía propia."""
    tp = m.get("tipografia") or {}
    propias = familias_propias(m)
    return "lualatex" if tp.get("familia") in propias or tp.get("familia_titulos") in propias else "pdflatex"


def es_flujo(m: dict) -> bool:
    """¿El texto corre de una página a otra (documento, artículo, tesis)?"""
    return bool(CLASES.get(m.get("clase"), CLASES["poster"])["flujo"])


def paginas_con_filas(m: dict) -> list[tuple[dict, list]]:
    """Presentaciones: [(diapositiva, sus filas)] en orden."""
    por_pag: dict[str, list] = {}
    for f in m.get("filas", []):
        por_pag.setdefault(f.get("pag"), []).append(f)
    return [(pg, por_pag.get(pg.get("id"), [])) for pg in m.get("paginas", [])]



def bloques_de_flujo(m: dict):
    """Documentos: las secciones (bloques) en orden, sin importar filas ni columnas."""
    for fila in m.get("filas", []):
        if fila.get("visible", True) is False:
            continue
        for col in fila.get("columnas", []):
            for b in col.get("bloques", []):
                yield b


def recorrer_elementos(m: dict):
    """Itera (bloque, elemento) por todo el contenido."""
    for fila in m.get("filas", []):
        for col in fila.get("columnas", []):
            for b in col.get("bloques", []):
                for e in b.get("elementos", []):
                    yield b, e


def recursos_usados(m: dict) -> set[str]:
    """Rutas de imágenes que usa el póster."""
    usados = set()
    cab = m.get("cabecera", {})
    for k in ("logo_izquierdo", "logo_derecho", "imagen"):
        if cab.get(k):
            usados.add(cab[k])
    for _, e in recorrer_elementos(m):
        for campo in campos_imagen_de(e, m):
            if e.get(campo):
                usados.add(e[campo])
    for capa in m.get("capas", []):
        for it in capa.get("elementos", []):
            if it.get("tipo") == "imagen" and it.get("archivo"):
                usados.add(it["archivo"])
    return usados



# ------------------------------------------------------------------ formato del texto
def campos_de(e: dict, m: dict | None = None) -> list[dict]:
    """Campos de un elemento: los de su variante o los de su componente propio."""
    tipo = str(e.get("tipo") or "")
    v = variantes.POR_CLAVE.get(tipo)
    if v:
        return v["campos"]
    if tipo.startswith("cmp:") and m is not None:
        comp = (m.get("componentes") or {}).get(tipo[4:])
        if isinstance(comp, dict):
            return [c for c in comp.get("campos") or [] if isinstance(c, dict) and c.get("nombre")]
    return []


def campos_imagen_de(e: dict, m: dict | None = None) -> list[str]:
    """Campos de imagen de un elemento (de una variante o de un componente del Lab)."""
    return [c["nombre"] for c in campos_de(e, m) if c.get("tipo") == "imagen"]


def transformar_textos(m: dict, fn, solo_visibles: bool = False) -> dict:
    """Aplica fn(texto, parrafos) a todos los textos del póster, en orden de lectura:
    cabecera, filas (columnas, cajas, elementos), pie y capas. Cambia m y lo devuelve.
    Con solo_visibles=True se salta lo que está oculto (para numerar las citas)."""
    def conv(t, parrafos=False):
        return fn(t, parrafos) if isinstance(t, str) and t.strip() else t

    def oculto(x):
        return solo_visibles and isinstance(x, dict) and x.get("visible") is False

    cab = m["cabecera"]
    if not oculto(cab):
        for k in ("titulo", "subtitulo", "autores", "afiliaciones"):
            cab[k] = conv(cab.get(k))
    flujo = es_flujo(m)
    doc = m.get("documento") if flujo and isinstance(m.get("documento"), dict) else None
    if doc:
        port = doc.get("portada") if isinstance(doc.get("portada"), dict) else {}
        for k in ("institucion", "dependencia", "tipo", "grado", "presenta", "director", "lugar", "fecha"):
            port[k] = conv(port.get(k))
        for k in ("dedicatoria", "agradecimientos", "resumen", "resumen2"):
            doc[k] = conv(doc.get(k), True)
        for k in ("encabezado", "titulo_resumen", "palabras_clave", "titulo_palabras", "titulo_resumen2",
                  "palabras_clave2", "titulo_palabras2", "titulo_indice", "titulo_figuras", "titulo_tablas",
                  "titulo_agradecimientos"):
            doc[k] = conv(doc.get(k))
    paginas = {pg.get("id"): pg for pg in m.get("paginas") or []} if m.get("clase") == "presentacion" else {}
    vistas = set()
    if paginas and isinstance(m.get("presentacion"), dict):
        m["presentacion"]["pie"] = conv(m["presentacion"].get("pie"))

    def textos_pagina(pg):
        if pg["id"] in vistas:
            return
        vistas.add(pg["id"])
        if not oculto(pg):
            pg["nombre"] = conv(pg.get("nombre"))
            pg["subtitulo"] = conv(pg.get("subtitulo"))
    for fila in m["filas"]:
        if paginas:
            # los títulos de las diapositivas, en orden de lectura (también las que no tienen filas)
            for pid, pg in paginas.items():
                if pid not in vistas:
                    textos_pagina(pg)
                if pid == fila.get("pag"):
                    break
            if oculto(paginas.get(fila.get("pag"))):
                continue
        if oculto(fila):
            continue
        for col in fila["columnas"]:
            for b in col["bloques"]:
                if oculto(b):
                    continue
                b["titulo"] = conv(b.get("titulo"))
                b["numero"] = conv(b.get("numero"))
                for e in b["elementos"]:
                    if oculto(e):
                        continue
                    for c in campos_de(e, m):
                        k, tipo = c["nombre"], c["tipo"]
                        if k not in e:
                            continue
                        val = e.get(k)
                        if tipo == "texto":
                            e[k] = conv(val)
                        elif tipo == "parrafo":
                            e[k] = conv(val, True)
                        elif tipo == "lista" and isinstance(val, list):
                            e[k] = [conv(x) for x in val]
                        elif tipo in ("pares", "hitos") and isinstance(val, list):
                            e[k] = [[conv(x) for x in par] if isinstance(par, list) else par for par in val]
                        elif tipo == "flechas" and isinstance(val, list):
                            e[k] = [list(f[:4]) + [conv(f[4])] + list(f[5:]) if isinstance(f, list) and len(f) >= 5 else f
                                    for f in val]
                        elif tipo == "tabla" and isinstance(val, dict) and isinstance(val.get("filas"), list):
                            val["filas"] = [[conv(x) for x in fila_t] if isinstance(fila_t, list) else fila_t
                                            for fila_t in val["filas"]]
    for pg in paginas.values():
        textos_pagina(pg)
    if not oculto(m["pie"]) and not flujo and not paginas:
        for k in ("izquierda", "centro", "derecha"):
            m["pie"][k] = conv(m["pie"].get(k))
    for capa in m["capas"]:
        if oculto(capa):
            continue
        for it in capa["elementos"]:
            if it.get("tipo") == "texto" and not oculto(it):
                it["texto"] = conv(it.get("texto"), True)
    return m


def convertir_formato(m: dict, nuevo: str) -> dict:
    """Cambia el formato de todos los textos del póster sin perder nada.

    simple → latex: cada texto se convierte a su código LaTeX.
    latex → simple: los textos con símbolos de LaTeX se envuelven en {{...}}
    (LaTeX sin tocar), párrafo a párrafo."""
    import re
    from ..documento import texto as T

    m = normalizar(m)
    viejo = m.get("formato_texto", "simple")
    if nuevo not in ("simple", "latex") or nuevo == viejo:
        return m
    especiales = re.compile(r"[\\{}$%&#_^~]")

    def conv(t, parrafos=False):
        if nuevo == "latex":
            # las citas [@clave] se dejan tal cual: el generador las escribe en los dos formatos
            citas = []

            def guardar(mo):
                citas.append(mo.group(0))
                return f"\ue000{len(citas) - 1}\ue001"
            x = T.convertir(re.sub(r"\[@[^\]\n]+\]", guardar, t), "simple", parrafos)
            return re.sub("\ue000(\\d+)\ue001", lambda mo: citas[int(mo.group(1))], x)
        if not especiales.search(t):
            return t
        if parrafos:
            bloques = [b.strip() for b in re.split(r"\n\s*\n", t) if b.strip()]
            return "\n\n".join("{{" + b + "}}" for b in bloques)
        return "{{" + t.strip() + "}}"

    transformar_textos(m, conv)
    nf = m["estilo"].get("nombre_figura")
    if isinstance(nf, str) and nf.strip():
        m["estilo"]["nombre_figura"] = conv(nf)
    m["formato_texto"] = nuevo
    return m


# ------------------------------------------------------------------ asistente
NOMBRES_BLOQUES = ["Introducción", "Objetivos", "Métodos", "Resultados", "Discusión", "Conclusiones",
                   "Referencias", "Agradecimientos"]


def desde_asistente(opciones: dict) -> dict:
    """Documento en blanco de la clase pedida (póster por defecto)."""
    clase = opciones.get("clase", "poster")
    if clase == "presentacion":
        return _presentacion_nueva(opciones)
    if clase in ("documento", "paper", "tesis"):
        return _documento_nuevo(opciones, clase)
    return _poster_nuevo(opciones)


def _aspecto_comun(m: dict, opciones: dict):
    idioma = opciones.get("idioma", "es")
    if idioma in IDIOMAS:
        m["idioma"] = idioma
        d = IDIOMAS[idioma]
        m["estilo"]["nombre_figura"] = d["figura"]
        m["documento"].update({"nombre_tabla": d["tabla"], "nombre_capitulo": d["capitulo"],
                               "nombre_apendice": d["apendice"], "titulo_resumen": d["resumen"],
                               "titulo_palabras": d["palabras"], "titulo_indice": d["indice"],
                               "titulo_figuras": d["figuras"], "titulo_tablas": d["tablas"]})
    tema = opciones.get("tema", "pizarra")
    if tema in TEMAS:
        m["colores"] = dict(tema=tema, **TEMAS[tema])
    if opciones.get("familia") in FAMILIAS:
        m["tipografia"]["familia"] = opciones["familia"]
    if opciones.get("estilo_bloque") in variantes.ESTILOS_CAJA:
        m["estilo"]["bloque"] = opciones["estilo_bloque"]


def _texto(texto: str) -> dict:
    e = variantes.elemento_nuevo("txtJustificado", nuevo_id("e"))
    e["texto"] = texto
    return e


def _bloque(titulo: str, elementos: list, **extra) -> dict:
    b = copy.deepcopy(BLOQUE_DEFECTO)
    b.update({"id": nuevo_id("b"), "titulo": titulo, "elementos": elementos})
    b.update(extra)
    return b


def _fila(columnas: list[list], **extra) -> dict:
    cols = []
    for bloques in columnas:
        col = copy.deepcopy(COLUMNA_DEFECTO)
        col.update({"id": nuevo_id("c"), "bloques": bloques, "distribucion": "arriba"})
        cols.append(col)
    fila = copy.deepcopy(FILA_DEFECTO)
    fila.update({"id": nuevo_id("f"), "rejilla": len(cols), "columnas": cols})
    fila.update(extra)
    return fila


def _presentacion_nueva(opciones: dict) -> dict:
    """Presentación en blanco: portada, dos diapositivas de contenido, una de sección y el cierre."""
    tam = opciones.get("tamano") if opciones.get("tamano") in CLASES["presentacion"]["tamanos"] else "16:9"
    corto, largo = TAMANOS[tam]
    m = normalizar({"clase": "presentacion"})
    m["lienzo"].update({"tamano": tam, "orientacion": "horizontal", "ancho": largo, "alto": corto, "margen": "14mm"})
    m["tipografia"]["fuente"] = 20 if tam != "4:3" else 18
    m["tipografia"]["interlinea"] = 1.22
    m["tipografia"]["escalas"].update({"titulo": 2.6, "subtitulo": 1.3, "autores": 1.1, "afiliaciones": 0.9,
                                       "bloque": 1.1, "pie": 0.75, "cita": 1.4, "cifra": 2.8,
                                       "referencias": 0.7, "piedeposter": 0.62})
    m["estilo"].update({"separacion_columnas": "10mm", "bloque": "ninguno", "alinear_texto": "izquierda",
                        "separacion_bloques": "0.7em"})
    _aspecto_comun(m, opciones)
    if opciones.get("estilo_bloque") not in variantes.ESTILOS_CAJA:
        m["estilo"]["bloque"] = "ninguno"
    if opciones.get("titulo_diapositiva") in ESTILOS_TITULO_PAGINA:
        m["presentacion"]["titulo"] = opciones["titulo_diapositiva"]
    m["cabecera"].update({"titulo": "Título de la presentación", "subtitulo": "Subtítulo o mensaje principal",
                          "autores": "Nombre Apellido", "afiliaciones": "Institución · fecha",
                          "alineacion": "izquierda"})
    m["presentacion"]["pie"] = "Título corto · Nombre Apellido"

    def pagina(nombre, diseno="contenido", **extra):
        pg = copy.deepcopy(PAGINA_DEFECTO)
        pg.update({"id": nuevo_id("p"), "nombre": nombre, "diseno": diseno})
        pg.update(extra)
        return pg

    def vinetas(items):
        e = variantes.elemento_nuevo("txtVinetas", nuevo_id("e"))
        e["items"] = items
        return e
    p1 = pagina("Portada", "portada", pie=False)
    p2 = pagina("Introducción")
    p3 = pagina("Resultados", "seccion")
    p4 = pagina("Un resultado con su figura")
    p5 = pagina("Conclusiones")
    filas = []
    filas.append(_fila([[_bloque("", [vinetas(["Primera idea", "Segunda idea", "Tercera idea"])],
                                 mostrar_titulo=False)]], pag=p2["id"]))
    img = variantes.elemento_nuevo("imgAncho", nuevo_id("e"))
    img["tam"] = 80
    filas.append(_fila([[_bloque("", [_texto("Explica aquí lo que muestra la figura.")], mostrar_titulo=False)],
                        [_bloque("", [img], mostrar_titulo=False)]], pag=p4["id"]))
    filas.append(_fila([[_bloque("", [vinetas(["Lo más importante", "Lo que sigue"])], mostrar_titulo=False)]],
                       pag=p5["id"]))
    m["paginas"] = [p1, p2, p3, p4, p5]
    m["filas"] = filas
    return normalizar(m)


def _documento_nuevo(opciones: dict, clase: str) -> dict:
    """Documento, artículo o tesis en blanco, con las secciones habituales."""
    tam = opciones.get("tamano") if opciones.get("tamano") in CLASES[clase]["tamanos"] else "A4"
    ancho, alto = TAMANOS[tam]
    m = normalizar({"clase": clase})
    doc = m["documento"]
    cols = 2 if clase == "paper" and int(opciones.get("columnas") or 1) == 2 else 1
    fuente = {"documento": 11, "paper": 10 if cols == 2 else 11, "tesis": 12}[clase]
    margen = {"documento": "25mm", "paper": "20mm" if cols == 2 else "25mm", "tesis": "25mm"}[clase]
    m["lienzo"].update({"tamano": tam, "orientacion": "vertical", "ancho": ancho, "alto": alto, "margen": margen})
    if clase == "tesis":
        m["lienzo"]["margen_izquierdo"] = "30mm"            # sitio para encuadernar
    m["tipografia"].update({"fuente": fuente, "interlinea": 1.5 if clase == "tesis" else 1.25,
                            "familia": "palatino" if clase != "paper" else "times"})
    m["tipografia"]["escalas"].update({"titulo": 1.9 if clase == "paper" else 2.1, "subtitulo": 1.25, "autores": 1.1,
                                       "afiliaciones": 0.92, "bloque": 1.05, "pie": 0.9, "cita": 1.25, "cifra": 2.2,
                                       "referencias": 0.92, "piedeposter": 0.8})
    m["estilo"].update({"separacion_columnas": "7mm", "bloque": "borde", "radio": "0.2em", "relleno": "0.6em",
                        "separacion_elementos": "0.55em"})
    doc.update({"columnas": cols, "parrafos": "sangria", "escala_seccion": 1.2 if clase == "paper" else 1.4})
    _aspecto_comun(m, opciones)
    if opciones.get("familia") not in FAMILIAS:
        m["tipografia"]["familia"] = "palatino" if clase != "paper" else "times"
    d = IDIOMAS.get(m.get("idioma") or "es", IDIOMAS["es"])
    m["cabecera"].update({"alineacion": "centro", "subtitulo": "", "autores": "Nombre Apellido^1^, Nombre Apellido^2^",
                          "afiliaciones": "^1^Institución · ^2^Institución"})
    ref = variantes.elemento_nuevo("bibliografia", nuevo_id("e"))

    def sec(titulo, texto=None, **extra):
        return _bloque(titulo, [_texto(texto or f"Texto de «{titulo}».")], **extra)
    if clase == "paper":
        m["cabecera"]["titulo"] = "Título del artículo"
        doc["resumen"] = ("Resume en un párrafo el problema, el método, los resultados principales y la "
                          "conclusión del trabajo.")
        doc["palabras_clave"] = "primera, segunda, tercera"
        bloques = [sec("Introducción"), sec("Métodos"), sec("Resultados"), sec("Discusión"), sec("Conclusiones"),
                   _bloque(d["referencias"], [ref], numerar=False)]
    elif clase == "tesis":
        m["cabecera"].update({"titulo": "Título de la tesis", "autores": "Nombre Apellido Apellido",
                              "afiliaciones": ""})
        doc["portada"].update({"visible": True, "institucion": "Nombre de la institución",
                               "dependencia": "Departamento o facultad", "tipo": "TESIS",
                               "grado": "que para obtener el título de …", "presenta": "presenta",
                               "director": "Director: Nombre Apellido", "lugar": "Ciudad", "fecha": "mes de año"})
        doc.update({"indice": True, "lista_figuras": False, "lista_tablas": False,
                    "resumen": "Resume aquí la tesis en uno o dos párrafos.",
                    "agradecimientos": "", "encabezado": ""})
        bloques = [sec("Introducción", nivel=1),
                   sec("Planteamiento del problema", nivel=2), sec("Objetivos", nivel=2),
                   sec("Marco teórico", nivel=1), sec("Metodología", nivel=1), sec("Resultados", nivel=1),
                   sec("Conclusiones", nivel=1),
                   _bloque(d["referencias"], [ref], nivel=1, numerar=False),
                   sec("Datos complementarios", nivel=1, apendice=True)]
    else:
        m["cabecera"].update({"titulo": "Título del documento", "autores": "Nombre Apellido",
                              "afiliaciones": "Institución · fecha"})
        bloques = [sec("Introducción"), sec("Desarrollo"), sec("Conclusiones")]
    m["filas"] = [_fila([bloques])]
    return normalizar(m)


def _poster_nuevo(opciones: dict) -> dict:
    """Póster en blanco: tamaño, orientación, columnas, tema, familia y estilos."""
    tam = opciones.get("tamano", "A0")
    orient = opciones.get("orientacion", "vertical")
    ncol = max(1, min(6, int(opciones.get("columnas", 3))))
    ancho, alto = TAMANOS.get(tam, TAMANOS["A0"])
    if orient == "horizontal":
        ancho, alto = alto, ancho
    m = normalizar({})
    m["lienzo"].update({"tamano": tam, "orientacion": orient, "ancho": ancho, "alto": alto})
    # letra proporcional al ancho del lienzo (30 pt en A0 vertical, 841 mm)
    mm = _a_mm(ancho)
    escala = mm / 841.0
    margen, separacion = round(28 * escala), round(20 * escala)
    ancho_col = (mm - 2 * margen - (ncol - 1) * separacion) / ncol          # mm
    nombres = list(NOMBRES_BLOQUES)
    usados = nombres[:2 * ncol] + ([f"Sección {ncol}.2"] if 2 * ncol > len(nombres) else [])
    # al menos 9 pt, salvo que entonces el título más largo no quepa en su columna (A4 con 5 o 6 columnas)
    tope = ancho_col * 72.27 / 25.4 / (0.75 * max(len(n) for n in usados) + 2.5)
    base = 30 * escala * (3.0 / max(ncol, 3)) ** 0.25
    m["tipografia"]["fuente"] = round(max(base, min(9.0, tope)), 1)
    m["lienzo"]["margen"] = f"{margen}mm"
    m["estilo"]["separacion_columnas"] = f"{separacion}mm"
    idioma = opciones.get("idioma", "es")
    if idioma in IDIOMAS:
        m["idioma"] = idioma
        m["estilo"]["nombre_figura"] = IDIOMAS[idioma]["figura"]
    tema = opciones.get("tema", "pizarra")
    if tema in TEMAS:
        m["colores"] = dict(tema=tema, **TEMAS[tema])
    if opciones.get("familia") in FAMILIAS:
        m["tipografia"]["familia"] = opciones["familia"]
    if opciones.get("estilo_bloque") in variantes.ESTILOS_CAJA:
        m["estilo"]["bloque"] = opciones["estilo_bloque"]
    if opciones.get("cabecera") in ESTILOS_CABECERA:
        m["cabecera"]["estilo"] = opciones["cabecera"]
    m["cabecera"].update({"titulo": "Título del póster", "subtitulo": "Mensaje principal en una línea",
                          "autores": "Nombre Apellido^1^, Nombre Apellido^2^",
                          "afiliaciones": "^1^Institución · ^2^Institución"})
    m["pie"].update({"izquierda": "Nombre del congreso · Ciudad, año", "centro": "",
                     "derecha": "correo@institución"})
    # la imagen de ejemplo (4:3) no debe pasar del 45 % del alto del lienzo:
    # con una sola columna en horizontal, a todo el ancho no cabría
    pct_img = max(30, min(100, int(0.45 * _a_mm(alto) * 4 / 3 / max(ancho_col, 1.0) * 100)))
    columnas = []
    for i in range(ncol):
        bloques = []
        for j in range(2):
            nombre = nombres.pop(0) if nombres else f"Sección {i + 1}.{j + 1}"
            b = copy.deepcopy(BLOQUE_DEFECTO)
            b.update({"id": nuevo_id("b"), "titulo": nombre})
            e = variantes.elemento_nuevo("txtJustificado", nuevo_id("e"))
            e["texto"] = f"Texto de la sección «{nombre}»."
            b["elementos"].append(e)
            if j == 0 and i == ncol // 2:
                img = variantes.elemento_nuevo("imgAncho", nuevo_id("e"))
                img["tam"] = pct_img
                b["elementos"].append(img)
            bloques.append(b)
        bloques[-1]["estirar"] = True
        col = copy.deepcopy(COLUMNA_DEFECTO)
        col.update({"id": nuevo_id("c"), "bloques": bloques, "distribucion": "arriba"})
        columnas.append(col)
    fila = copy.deepcopy(FILA_DEFECTO)
    fila.update({"id": nuevo_id("f"), "alto": "llenar", "rejilla": ncol, "columnas": columnas})
    m["filas"] = [fila]
    return normalizar(m)


def _a_mm(dim: str) -> float:
    import re
    mo = re.match(r"\s*([0-9.]+)\s*(mm|cm|in|pt)\s*$", str(dim))
    if not mo:
        return 841.0
    v, u = float(mo.group(1)), mo.group(2)
    return {"mm": v, "cm": v * 10, "in": v * 25.4, "pt": v * 25.4 / 72.27}[u]
