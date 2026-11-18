"""Referencias bibliográficas del póster.

* Datos: cada referencia es un diccionario (clave, tipo, autores, año, título,
  revista, volumen, número, páginas, editorial, DOI, URL…). Los autores son
  {"apellido", "nombre"} o {"literal"} para organizaciones.
* Estilos: APA 7, Vancouver, IEEE, Chicago (autor-fecha), MLA 9, Harvard,
  Nature y ACS. Cada entrada se arma como «texto rico» (trozos con cursiva o
  negrita) que se escribe en LaTeX para el póster o en HTML para la aplicación.
* Citas: en cualquier texto del póster, [@clave] o [@a; @b, p. 12]. El
  generador las cambia por la cita en el estilo elegido y numera las referencias
  en orden de aparición cuando el estilo es numérico.
* Importación: BibTeX, RIS, CSL-JSON y búsqueda por DOI (doi.org).
"""
from __future__ import annotations

import json
import re
import unicodedata
from html import escape as _html

from . import texto as T

# ====================================================================== catálogos
ESTILOS = {
    "apa": {"nombre": "APA 7", "cita": "autor-año", "orden": "alfabetico", "lista": "autor"},
    "vancouver": {"nombre": "Vancouver", "cita": "numero", "orden": "cita", "lista": "numerica",
                  "marca": "parentesis", "etiqueta": "{n}."},
    "ieee": {"nombre": "IEEE", "cita": "numero", "orden": "cita", "lista": "numerica",
             "marca": "corchetes", "etiqueta": "[{n}]"},
    "chicago": {"nombre": "Chicago (autor-fecha)", "cita": "autor-año", "orden": "alfabetico", "lista": "autor"},
    "mla": {"nombre": "MLA 9", "cita": "autor-pagina", "orden": "alfabetico", "lista": "autor"},
    "harvard": {"nombre": "Harvard", "cita": "autor-año", "orden": "alfabetico", "lista": "autor"},
    "nature": {"nombre": "Nature", "cita": "numero", "orden": "cita", "lista": "numerica",
               "marca": "superindice", "etiqueta": "{n}."},
    "acs": {"nombre": "ACS", "cita": "numero", "orden": "cita", "lista": "numerica",
            "marca": "superindice", "etiqueta": "({n})"},
}

TIPOS = {
    "articulo": "Artículo de revista", "libro": "Libro", "capitulo": "Capítulo de libro",
    "congreso": "Congreso (actas o ponencia)", "tesis": "Tesis", "informe": "Informe técnico",
    "web": "Página web", "datos": "Conjunto de datos", "software": "Software", "preprint": "Preprint",
    "otro": "Otro",
}

# Campos que muestra el formulario de cada tipo (además de clave, tipo, autores, año y título)
CAMPOS_TIPO = {
    "articulo": ["revista", "revista_abrev", "volumen", "numero", "paginas", "doi", "url"],
    "libro": ["edicion", "editorial", "lugar", "editores", "doi", "url"],
    "capitulo": ["revista", "editores", "edicion", "paginas", "editorial", "lugar", "doi", "url"],
    "congreso": ["revista", "lugar", "editorial", "paginas", "doi", "url"],
    "tesis": ["grado", "institucion", "lugar", "url"],
    "informe": ["institucion", "numero", "lugar", "doi", "url"],
    "web": ["revista", "fecha", "url", "fecha_acceso"],
    "datos": ["version", "editorial", "doi", "url"],
    "software": ["version", "editorial", "doi", "url"],
    "preprint": ["revista", "doi", "url"],
    "otro": ["revista", "editorial", "lugar", "doi", "url", "nota"],
}

ETIQUETAS_CAMPO = {
    "revista": "Revista, libro, sitio o congreso", "revista_abrev": "Abreviatura de la revista (Vancouver, ACS)",
    "volumen": "Volumen", "numero": "Número", "paginas": "Páginas", "editorial": "Editorial",
    "lugar": "Lugar", "edicion": "Edición", "editores": "Editores", "doi": "DOI", "url": "URL",
    "fecha_acceso": "Fecha de consulta (AAAA-MM-DD)", "fecha": "Fecha (AAAA-MM-DD)",
    "institucion": "Institución", "grado": "Grado (doctorado, maestría…)", "version": "Versión", "nota": "Nota",
}

CAMPOS_TEXTO = ["clave", "tipo", "anio", "titulo", "revista", "revista_abrev", "volumen", "numero", "paginas",
                "editorial", "lugar", "edicion", "doi", "url", "fecha_acceso", "fecha", "institucion", "grado",
                "version", "nota"]

# ====================================================================== idioma
L = {
    "es": dict(y="y", et_al="et al.", en="En", ed="Ed.", eds="Eds.", ed_num="{n}.ª ed.", pp="pp.", p="p.",
               sf="s. f.", doctoral="Tesis doctoral", maestria="Tesis de maestría", tesis="Tesis",
               consultado="Consultado el {f}", citado="citado {f}", internet="Internet",
               disponible="Disponible en", version="Versión", datos="Conjunto de datos", software="Software",
               preprint="Preprint", editado="editado por", informe="Informe", n_informe="Informe n.º",
               meses=["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                      "octubre", "noviembre", "diciembre"],
               meses_cortos=["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]),
    "en": dict(y="and", et_al="et al.", en="In", ed="Ed.", eds="Eds.", ed_num="{n}{ord} ed.", pp="pp.", p="p.",
               sf="n.d.", doctoral="Doctoral dissertation", maestria="Master's thesis", tesis="Thesis",
               consultado="Accessed {f}", citado="cited {f}", internet="Internet",
               disponible="Available from", version="Version", datos="Data set", software="Computer software",
               preprint="Preprint", editado="edited by", informe="Report", n_informe="Report No.",
               meses=["January", "February", "March", "April", "May", "June", "July", "August", "September",
                      "October", "November", "December"],
               meses_cortos=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]),
    "pt": dict(y="e", et_al="et al.", en="In", ed="Ed.", eds="Eds.", ed_num="{n}.ª ed.", pp="pp.", p="p.",
               sf="s. d.", doctoral="Tese de doutorado", maestria="Dissertação de mestrado", tesis="Tese",
               consultado="Acesso em {f}", citado="citado {f}", internet="Internet",
               disponible="Disponível em", version="Versão", datos="Conjunto de dados", software="Software",
               preprint="Preprint", editado="editado por", informe="Relatório", n_informe="Relatório n.º",
               meses=["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
                      "outubro", "novembro", "dezembro"],
               meses_cortos=["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]),
    "fr": dict(y="et", et_al="et al.", en="Dans", ed="Éd.", eds="Éds", ed_num="{n}e éd.", pp="p.", p="p.",
               sf="s. d.", doctoral="Thèse de doctorat", maestria="Mémoire de master", tesis="Thèse",
               consultado="Consulté le {f}", citado="cité le {f}", internet="Internet",
               disponible="Disponible sur", version="Version", datos="Jeu de données", software="Logiciel",
               preprint="Prépublication", editado="sous la direction de", informe="Rapport", n_informe="Rapport n°",
               meses=["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
                      "octobre", "novembre", "décembre"],
               meses_cortos=["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.",
                             "nov.", "déc."]),
    "de": dict(y="und", et_al="et al.", en="In", ed="Hrsg.", eds="Hrsg.", ed_num="{n}. Aufl.", pp="S.", p="S.",
               sf="o. J.", doctoral="Dissertation", maestria="Masterarbeit", tesis="Abschlussarbeit",
               consultado="Zugriff am {f}", citado="zitiert am {f}", internet="Internet",
               disponible="Verfügbar unter", version="Version", datos="Datensatz", software="Software",
               preprint="Preprint", editado="herausgegeben von", informe="Bericht", n_informe="Bericht Nr.",
               meses=["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September",
                      "Oktober", "November", "Dezember"],
               meses_cortos=["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sep.", "Okt.", "Nov.",
                             "Dez."]),
    "it": dict(y="e", et_al="et al.", en="In", ed="A cura di", eds="A cura di", ed_num="{n}ª ed.", pp="pp.",
               p="p.", sf="s. d.", doctoral="Tesi di dottorato", maestria="Tesi di laurea magistrale",
               tesis="Tesi", consultado="Consultato il {f}", citado="citato il {f}", internet="Internet",
               disponible="Disponibile su", version="Versione", datos="Set di dati", software="Software",
               preprint="Preprint", editado="a cura di", informe="Rapporto", n_informe="Rapporto n.",
               meses=["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
                      "ottobre", "novembre", "dicembre"],
               meses_cortos=["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]),
}


def _l(idioma: str) -> dict:
    return L.get(idioma or "en", L["en"]) if idioma in L else L["en"]


def _ordinal_en(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


# ====================================================================== texto rico
class Rico:
    """Lista de trozos (texto, estilo); estilo es '', 'i', 'b', 'bi' o 'url'."""

    def __init__(self):
        self.trozos: list[tuple[str, str]] = []

    def __call__(self, texto, estilo: str = "") -> "Rico":
        if texto:
            self.trozos.append((str(texto), estilo))
        return self

    def i(self, texto) -> "Rico":
        return self(texto, "i")

    def b(self, texto) -> "Rico":
        return self(texto, "b")

    def url(self, texto) -> "Rico":
        return self(texto, "url")

    def vacio(self) -> bool:
        return not any(t.strip() for t, _ in self.trozos)

    def plano(self) -> str:
        return "".join(t for t, _ in self.trozos)

    # -- terminar con un signo (sin duplicar el punto si ya lo hay)
    def punto(self, signo: str = ".") -> "Rico":
        if not self.trozos:
            return self
        t, e = self.trozos[-1]
        if e != "url" and t.rstrip().endswith((".", "?", "!")) and signo == ".":
            return self
        if e == "url" and signo == ".":
            return self
        self.trozos.append((signo, ""))
        return self

    def latex(self) -> str:
        salida = []
        for t, e in self._unidos():
            if e == "url":
                salida.append(_url_latex(t))
                continue
            x = T.escapar(t).replace("--", "-{}-")
            if "b" in e:
                x = r"\textbf{" + x + "}"
            if "i" in e:
                x = r"\textit{" + x + "}"
            salida.append(x)
        return "".join(salida)

    def html(self) -> str:
        salida = []
        for t, e in self._unidos():
            x = _html(t)
            if e == "url":
                x = f'<span class="url">{x}</span>'
            if "b" in e:
                x = f"<b>{x}</b>"
            if "i" in e:
                x = f"<i>{x}</i>"
            salida.append(x)
        return "".join(salida)

    def _unidos(self):
        res: list[list] = []
        for t, e in self.trozos:
            if res and res[-1][1] == e:
                res[-1][0] += t
            else:
                res.append([t, e])
        return [(t, e) for t, e in res]


def _url_latex(u: str) -> str:
    """URL como texto que puede partirse al final de línea (sin el paquete url)."""
    x = T.escapar(u)
    return r"\PCurl{" + re.sub(r"(/(?!/)|[.\-_?=&](?!/))", r"\1\\allowbreak{}", x).replace(
        "https:/\\allowbreak{}/", "https://").replace("http:/\\allowbreak{}/", "http://") + "}"


# ====================================================================== nombres
def _texto(v) -> str:
    return str(v or "").strip()


def autor(apellido: str = "", nombre: str = "", literal: str = "") -> dict:
    return {"literal": literal} if literal else {"apellido": apellido, "nombre": nombre}


def iniciales(nombre: str, punto: bool = True, espacio: bool = True, guion: bool = True) -> str:
    """«Ana María» → «A. M.»; «Jean-Paul» → «J.-P.»."""
    res = []
    for parte in re.split(r"\s+", _texto(nombre)):
        if not parte:
            continue
        subpartes = []
        for s in parte.split("-"):
            s = s.strip(".,")
            if not s:
                continue
            subpartes.append(s[0].upper() + ("." if punto else ""))
        if subpartes:
            res.append(("-" if guion else "").join(subpartes))
    return (" " if espacio else "").join(res)


def _es_literal(a: dict) -> bool:
    return bool(a.get("literal")) or not (_texto(a.get("apellido")) or _texto(a.get("nombre")))


def _apellido(a: dict) -> str:
    return _texto(a.get("literal")) if _es_literal(a) else _texto(a.get("apellido")) or _texto(a.get("nombre"))


def _lista(nombres: list[str], y: str, coma_final: bool = False, sep: str = ", ") -> str:
    nombres = [n for n in nombres if n]
    if len(nombres) <= 1:
        return "".join(nombres)
    if len(nombres) == 2:
        return f"{nombres[0]}{',' if coma_final else ''} {y} {nombres[1]}"
    return sep.join(nombres[:-1]) + f"{',' if coma_final else ''} {y} {nombres[-1]}"


def _fecha(iso: str):
    m = re.match(r"^\s*(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?", str(iso or ""))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)) if m.group(2) else None, int(m.group(3)) if m.group(3) else None


def _fecha_larga(iso: str, idioma: str, britanico: bool = False) -> str:
    f = _fecha(iso)
    if not f:
        return _texto(iso)
    a, mes, d = f
    lx = _l(idioma)
    if not mes:
        return str(a)
    nombre_mes = lx["meses"][mes - 1]
    if idioma == "en" and not britanico:
        return f"{nombre_mes} {d}, {a}" if d else f"{nombre_mes} {a}"
    if idioma == "de":
        return f"{d}. {nombre_mes} {a}" if d else f"{nombre_mes} {a}"
    if idioma in ("es", "pt"):
        return f"{d} de {nombre_mes} de {a}" if d else f"{nombre_mes} de {a}"
    return f"{d} {nombre_mes} {a}" if d else f"{nombre_mes} {a}"


def _anio(ref: dict, idioma: str) -> str:
    a = _texto(ref.get("anio"))
    return a or _l(idioma)["sf"]


def _paginas(p: str) -> str:
    return re.sub(r"\s*-{1,2}\s*", "–", _texto(p))


def _doi_url(ref: dict) -> str:
    doi = _texto(ref.get("doi"))
    if doi:
        doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
        return "https://doi.org/" + doi
    return _texto(ref.get("url"))


def _doi(ref: dict) -> str:
    return re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", _texto(ref.get("doi")), flags=re.I)


def _edicion(ref: dict, idioma: str) -> str:
    e = _texto(ref.get("edicion"))
    if not e:
        return ""
    if e.isdigit():
        n = int(e)
        if n <= 1:
            return ""
        plantilla = _l(idioma)["ed_num"]
        return plantilla.format(n=n, ord=_ordinal_en(n))
    return e


def _es_maestria(ref: dict) -> bool:
    return bool(re.search(r"maest|mast|mestr|msc|m\.s", _texto(ref.get("grado")), re.I))


def _tipo_tesis(ref: dict, idioma: str, estilo: str = "") -> str:
    """Nombre del tipo de tesis según el estilo y el idioma."""
    grado = _texto(ref.get("grado"))
    maestria = _es_maestria(ref)
    conocido = not grado or maestria or re.search(r"doct|ph\.?d|dissert", grado, re.I)
    if not conocido:
        return grado
    if idioma == "en":
        if estilo == "ieee":
            return "M.S. thesis" if maestria else "Ph.D. dissertation"
        if estilo == "vancouver":
            return "master's thesis" if maestria else "dissertation"
        if estilo == "harvard":
            return "MSc thesis" if maestria else "PhD thesis"
        if estilo == "chicago":
            return "Master's thesis" if maestria else "PhD diss."
    lx = _l(idioma)
    t = lx["maestria"] if maestria else lx["doctoral"]
    return t.lower() if estilo == "vancouver" else t


def _sentence(t: str) -> str:
    return _texto(t).rstrip(". ")


# ====================================================================== estilos
class Estilo:
    clave = "apa"

    def __init__(self, idioma: str = "es"):
        self.idioma = idioma if idioma in L else "en"
        self.lx = _l(self.idioma)

    # ---- nombres en la lista
    def autores_lista(self, autores: list[dict]) -> str:
        raise NotImplementedError

    # ---- nombre corto para las citas autor-año
    def corto(self, autores: list[dict], ref: dict, max_antes_etal: int = 2) -> str:
        if not autores:
            return _sentence(ref.get("titulo"))[:40]
        aps = [_apellido(a) for a in autores]
        if len(aps) == 1:
            return aps[0]
        if len(aps) <= max_antes_etal:
            return _lista(aps, self.y_cita())
        return f"{aps[0]} {self.lx['et_al']}"

    def y_cita(self) -> str:
        return self.lx["y"]

    def entrada(self, ref: dict) -> Rico:
        raise NotImplementedError


class APA(Estilo):
    clave = "apa"

    def y_cita(self):
        return "&" if self.idioma == "en" else self.lx["y"]

    def _nombre(self, a: dict) -> str:
        if _es_literal(a):
            return _apellido(a)
        ini = iniciales(a.get("nombre", ""))
        return f"{_texto(a.get('apellido'))}, {ini}" if ini else _texto(a.get("apellido"))

    def autores_lista(self, autores):
        n = [self._nombre(a) for a in autores]
        y = "&" if self.idioma == "en" else self.lx["y"]
        serial = self.idioma == "en"          # en español: «A, B y C» (sin coma antes de «y»)
        if len(n) > 20:
            return ", ".join(n[:19]) + ", … " + n[-1]
        if len(n) == 2:
            return f"{n[0]}, {y} {n[1]}" if serial else f"{n[0]} {y} {n[1]}"
        return _lista(n, y, coma_final=serial)

    def _editores(self, editores):
        n = []
        for a in editores:
            if _es_literal(a):
                n.append(_apellido(a))
            else:
                ini = iniciales(a.get("nombre", ""))
                n.append(f"{ini} {_texto(a.get('apellido'))}".strip())
        y = "&" if self.idioma == "en" else self.lx["y"]
        return _lista(n, y, coma_final=len(n) > 2 and self.idioma == "en")

    def entrada(self, ref):
        r = Rico()
        lx = self.lx
        tipo = ref.get("tipo", "articulo")
        autores = ref.get("autores") or []
        titulo = _sentence(ref.get("titulo"))
        anio = _anio(ref, self.idioma)
        if tipo == "web" and _fecha(ref.get("fecha")):
            anio = _fecha_larga(ref.get("fecha"), self.idioma)
            if self.idioma == "en":
                f = _fecha(ref.get("fecha"))
                anio = f"{f[0]}, {lx['meses'][f[1] - 1]} {f[2]}" if f[1] and f[2] else anio
        italico_titulo = tipo in ("libro", "informe", "tesis", "web", "datos", "software")
        if autores:
            r(self.autores_lista(autores)).punto()
            r(f" ({anio}). ")
            if italico_titulo:
                r.i(titulo)
            else:
                r(titulo)
        else:          # sin autores: el título va delante
            if italico_titulo:
                r.i(titulo)
            else:
                r(titulo)
            r(f" ({anio})")
        cont = _texto(ref.get("revista"))
        if tipo == "articulo":
            r.punto()
            if cont:
                r(" ").i(cont)
                vol, num, pag = _texto(ref.get("volumen")), _texto(ref.get("numero")), _paginas(ref.get("paginas"))
                if vol:
                    r(", ").i(vol)
                if num:
                    r(f"({num})")
                if pag:
                    r(", " + pag)
                r.punto()
        elif tipo == "libro":
            ed = _edicion(ref, self.idioma)
            if ed:
                r(f" ({ed})")
            r.punto()
            if ref.get("editorial"):
                r(" " + _texto(ref["editorial"])).punto()
        elif tipo == "capitulo":
            r.punto()
            r(f" {lx['en']} ")
            eds = ref.get("editores") or []
            if eds:
                r(self._editores(eds) + f" ({lx['eds'] if len(eds) > 1 else lx['ed']}), ")
            r.i(cont)
            extra = [x for x in (_edicion(ref, self.idioma),
                                 (lx["pp"] + " " + _paginas(ref.get("paginas"))) if ref.get("paginas") else "") if x]
            if extra:
                r(" (" + ", ".join(extra) + ")")
            r.punto()
            if ref.get("editorial"):
                r(" " + _texto(ref["editorial"])).punto()
        elif tipo == "tesis":
            tipo_tesis = _tipo_tesis(ref, self.idioma, "apa")
            inst = _texto(ref.get("institucion"))
            r(f" [{tipo_tesis}{', ' + inst if inst else ''}]").punto()
        elif tipo == "informe":
            num = _texto(ref.get("numero"))
            if num:
                r(f" ({lx['n_informe']} {num})")
            r.punto()
            if ref.get("institucion") or ref.get("editorial"):
                r(" " + _texto(ref.get("institucion") or ref.get("editorial"))).punto()
        elif tipo in ("datos", "software"):
            ver = _texto(ref.get("version"))
            if ver:
                r(f" ({lx['version']} {ver})")
            r(f" [{lx['datos'] if tipo == 'datos' else lx['software']}]").punto()
            if ref.get("editorial"):
                r(" " + _texto(ref["editorial"])).punto()
        elif tipo == "congreso":
            r.punto()
            if cont:
                r(f" {lx['en']} ").i(cont)
                if ref.get("paginas"):
                    r(f" ({lx['pp']} {_paginas(ref['paginas'])})")
                r.punto()
            if ref.get("editorial"):
                r(" " + _texto(ref["editorial"])).punto()
        elif tipo == "web":
            r.punto()
            if cont:
                r(" " + cont).punto()
        elif tipo == "preprint":
            r(f" [{lx['preprint']}]").punto()
            if cont:
                r(" ").i(cont).punto()
        else:
            r.punto()
            if cont:
                r(" ").i(cont).punto()
            if ref.get("editorial"):
                r(" " + _texto(ref["editorial"])).punto()
        enlace = _doi_url(ref)
        if enlace:
            if tipo == "web" and ref.get("fecha_acceso") and self.idioma in ("es", "en"):
                f = _fecha_larga(ref["fecha_acceso"], self.idioma)
                r(f" Recuperado el {f}, de " if self.idioma == "es" else f" Retrieved {f}, from ")
            else:
                r(" ")
            r.url(enlace)
        return r


class Vancouver(Estilo):
    clave = "vancouver"

    def _nombre(self, a):
        if _es_literal(a):
            return _apellido(a)
        return f"{_texto(a.get('apellido'))} {iniciales(a.get('nombre', ''), punto=False, espacio=False, guion=False)}".strip()

    def autores_lista(self, autores):
        n = [self._nombre(a) for a in autores]
        if len(n) > 6:
            return ", ".join(n[:6]) + ", " + self.lx["et_al"].rstrip(".")
        return ", ".join(n)

    def entrada(self, ref):
        r = Rico()
        lx = self.lx
        tipo = ref.get("tipo", "articulo")
        autores = ref.get("autores") or []
        if autores:
            r(self.autores_lista(autores)).punto()
            r(" ")
        r(_sentence(ref.get("titulo")))
        anio = _texto(ref.get("anio"))
        cont = _texto(ref.get("revista_abrev") or ref.get("revista"))
        if tipo == "articulo":
            r.punto()
            if cont:
                r(" " + cont).punto()
            r(" " + anio if anio else "")
            vol, num, pag = _texto(ref.get("volumen")), _texto(ref.get("numero")), _paginas(ref.get("paginas"))
            if vol or num:
                r(";" + vol + (f"({num})" if num else ""))
            if pag:
                r(":" + pag.replace("–", "-"))
            r.punto()
        elif tipo == "libro":
            r.punto()
            ed = _edicion(ref, self.idioma)
            if ed:
                r(" " + ed)
            lugar, edit = _texto(ref.get("lugar")), _texto(ref.get("editorial"))
            if lugar or edit:
                r(" " + ": ".join(x for x in (lugar, edit) if x))
            if anio:
                r("; " + anio)
            r.punto()
        elif tipo == "capitulo":
            r.punto()
            eds = ref.get("editores") or []
            r(f" {lx['en']}: ")
            if eds:
                plural = len(eds) > 1
                palabra = ("editors" if plural else "editor") if self.idioma == "en" else ("editores" if plural else "editor")
                r(", ".join(self._nombre(a) for a in eds) + f", {palabra}. ")
            r(cont).punto()
            lugar, edit = _texto(ref.get("lugar")), _texto(ref.get("editorial"))
            if lugar or edit:
                r(" " + ": ".join(x for x in (lugar, edit) if x))
            if anio:
                r("; " + anio)
            r.punto()
            if ref.get("paginas"):
                r(" p. " + _paginas(ref["paginas"]).replace("–", "-")).punto()
        elif tipo == "web":
            r(f" [{lx['internet']}]").punto()
            if cont:
                r(" " + cont)
            if anio:
                r(("; " if cont else " ") + anio)
            if ref.get("fecha_acceso"):
                f = _fecha(ref["fecha_acceso"])
                fecha = f"{f[0]} {lx['meses_cortos'][f[1] - 1]} {f[2]}" if f and f[1] and f[2] else _texto(ref["fecha_acceso"])
                if self.idioma == "es" and f and f[1] and f[2]:
                    fecha = f"{f[2]} {lx['meses_cortos'][f[1] - 1]} {f[0]}"
                r(" [" + lx["citado"].format(f=fecha) + "]")
            r.punto()
            if ref.get("url"):
                r(f" {lx['disponible']}: ").url(_texto(ref["url"]))
            return r
        elif tipo == "tesis":
            r(" [" + _tipo_tesis(ref, self.idioma, "vancouver") + "]").punto()
            lugar, inst = _texto(ref.get("lugar")), _texto(ref.get("institucion"))
            if lugar or inst:
                r(" " + ": ".join(x for x in (lugar, inst) if x))
            if anio:
                r("; " + anio)
            r.punto()
        else:
            r.punto()
            if cont:
                r(" " + cont).punto()
            edit = _texto(ref.get("editorial") or ref.get("institucion"))
            if edit:
                r(" " + edit)
            if anio:
                r(("; " if edit else " ") + anio)
            r.punto()
        doi = _doi(ref)
        if doi:
            r(" doi:").url(doi)
        elif ref.get("url"):
            r(f" {lx['disponible']}: ").url(_texto(ref["url"]))
        return r


class IEEE(Estilo):
    clave = "ieee"

    def _nombre(self, a):
        if _es_literal(a):
            return _apellido(a)
        return f"{iniciales(a.get('nombre', ''))} {_texto(a.get('apellido'))}".strip()

    def autores_lista(self, autores):
        n = [self._nombre(a) for a in autores]
        if len(n) > 6:
            return f"{n[0]} {self.lx['et_al']}"
        return _lista(n, self.lx["y"], coma_final=len(n) > 2 and self.idioma == "en")

    def entrada(self, ref):
        r = Rico()
        lx = self.lx
        tipo = ref.get("tipo", "articulo")
        autores = ref.get("autores") or []
        if autores:
            r(self.autores_lista(autores) + ", ")
        titulo = _sentence(ref.get("titulo"))
        anio = _texto(ref.get("anio"))
        cont = _texto(ref.get("revista"))
        if tipo in ("libro", "informe", "software", "datos"):
            r.i(titulo)
            partes = []
            if tipo == "libro":
                ed = _edicion(ref, "en" if self.idioma == "en" else self.idioma)
                if ed:
                    r(", " + ed)
                r.punto()
                r(" ")
                lugar, edit = _texto(ref.get("lugar")), _texto(ref.get("editorial"))
                if lugar or edit:
                    r(": ".join(x for x in (lugar, edit) if x) + (", " if anio else ""))
                r(anio).punto()
            else:
                if tipo == "informe" and ref.get("numero"):
                    partes.append(f"{lx['informe']} {ref['numero']}")
                if ref.get("version"):
                    partes.append(f"{lx['version']} {ref['version']}")
                for x in (_texto(ref.get("institucion") or ref.get("editorial")), anio):
                    if x:
                        partes.append(x)
                if partes:
                    r(", " + ", ".join(partes))
                r.punto()
        else:
            r(f"“{titulo},” ")
            if tipo == "articulo":
                r.i(cont)
                for etiqueta, campo in (("vol.", "volumen"), ("no.", "numero")):
                    if ref.get(campo):
                        r(f", {etiqueta} {_texto(ref[campo])}")
                if ref.get("paginas"):
                    p = _paginas(ref["paginas"])
                    r(f", {'pp.' if '–' in p else 'p.'} {p}")
                if anio:
                    r(", " + anio)
                r.punto()
            elif tipo in ("capitulo", "congreso"):
                r((lx["en"].lower() if self.idioma == "en" else lx["en"].lower()) + " ").i(cont)
                eds = ref.get("editores") or []
                if eds:
                    r(", " + _lista([self._nombre(a) for a in eds], lx["y"]) + f", {lx['eds'] if len(eds) > 1 else lx['ed']}")
                lugar, edit = _texto(ref.get("lugar")), _texto(ref.get("editorial"))
                if lugar or edit:
                    r.punto()
                    r(" " + ": ".join(x for x in (lugar, edit) if x))
                if anio:
                    r(", " + anio)
                if ref.get("paginas"):
                    r(", pp. " + _paginas(ref["paginas"]))
                r.punto()
            elif tipo == "tesis":
                r(_tipo_tesis(ref, self.idioma, "ieee"))
                for x in (_texto(ref.get("institucion")), _texto(ref.get("lugar")), anio):
                    if x:
                        r(", " + x)
                r.punto()
            elif tipo == "web":
                if cont:
                    r(cont + ". ")
                if ref.get("url"):
                    r.url(_texto(ref["url"]))
                if ref.get("fecha_acceso"):
                    f = _fecha(ref["fecha_acceso"])
                    fecha = (f"{lx['meses_cortos'][f[1] - 1]}. {f[2]}, {f[0]}" if self.idioma == "en" else
                             _fecha_larga(ref["fecha_acceso"], self.idioma)) if f and f[1] and f[2] else _texto(ref["fecha_acceso"])
                    r(" (" + (f"accessed {fecha}" if self.idioma == "en" else lx["consultado"].format(f=fecha).lower()) + ")")
                return r
            else:
                if cont:
                    r.i(cont)
                    r(", ")
                r(anio).punto()
        doi = _doi(ref)
        if doi:
            r(" doi: ").url(doi)
            r.punto()
        elif ref.get("url"):
            r(" [Online]. " if self.idioma == "en" else f" [{lx['internet']}]. ")
            r.url(_texto(ref["url"]))
        return r


class Chicago(Estilo):
    clave = "chicago"

    def _nombre(self, a, primero):
        if _es_literal(a):
            return _apellido(a)
        ap, no = _texto(a.get("apellido")), _texto(a.get("nombre"))
        if primero:
            return f"{ap}, {no}" if no else ap
        return f"{no} {ap}".strip()

    def autores_lista(self, autores):
        n = [self._nombre(a, i == 0) for i, a in enumerate(autores)]
        if len(n) > 10:
            n = n[:7] + [self.lx["et_al"]]
            return ", ".join(n)
        serial = self.idioma == "en"
        if len(n) == 2:
            return f"{n[0]}, {self.lx['y']} {n[1]}" if serial else f"{n[0]} {self.lx['y']} {n[1]}"
        return _lista(n, self.lx["y"], coma_final=serial)

    def corto(self, autores, ref, max_antes_etal=3):
        return super().corto(autores, ref, max_antes_etal=3)

    def entrada(self, ref):
        r = Rico()
        lx = self.lx
        tipo = ref.get("tipo", "articulo")
        autores = ref.get("autores") or []
        anio = _anio(ref, self.idioma)
        titulo = _sentence(ref.get("titulo"))
        if autores:
            r(self.autores_lista(autores)).punto()
            r(f" {anio}. ")
        cursiva = tipo in ("libro", "informe", "datos", "software")
        if cursiva:
            r.i(titulo)
        else:
            r(f"“{titulo}.”")
        if not autores:
            r(f" {anio}")
        cont = _texto(ref.get("revista"))
        if tipo == "articulo":
            if cont:
                r(" ").i(cont)
            if ref.get("volumen"):
                r(" " + _texto(ref["volumen"]))
            if ref.get("numero"):
                r(f" ({_texto(ref['numero'])})")
            if ref.get("paginas"):
                r(": " + _paginas(ref["paginas"]))
            r.punto()
        elif tipo == "capitulo":
            r(f" {lx['en']} ").i(cont)
            eds = ref.get("editores") or []
            if eds:
                r(f", {lx['editado']} " + _lista([self._nombre(a, False) for a in eds], lx["y"]))
            if ref.get("paginas"):
                r(", " + _paginas(ref["paginas"]))
            r.punto()
            lugar, edit = _texto(ref.get("lugar")), _texto(ref.get("editorial"))
            if lugar or edit:
                r(" " + ": ".join(x for x in (lugar, edit) if x)).punto()
        elif tipo == "libro":
            if not cursiva:
                pass
            r.punto()
            lugar, edit = _texto(ref.get("lugar")), _texto(ref.get("editorial"))
            if lugar or edit:
                r(" " + ": ".join(x for x in (lugar, edit) if x)).punto()
        elif tipo == "tesis":
            r(f" {_tipo_tesis(ref, self.idioma, 'chicago')}, {_texto(ref.get('institucion'))}".rstrip(", ")).punto()
        elif tipo == "web":
            if cont:
                r(" " + cont).punto()
            if ref.get("fecha_acceso"):
                r(" " + lx["consultado"].format(f=_fecha_larga(ref["fecha_acceso"], self.idioma))).punto()
        else:
            if cont:
                r(" ").i(cont)
            r.punto()
            edit = _texto(ref.get("editorial") or ref.get("institucion"))
            if edit:
                r(" " + edit).punto()
        enlace = _doi_url(ref)
        if enlace:
            r(" ").url(enlace)
            r.punto()
        return r


class MLA(Estilo):
    clave = "mla"

    def autores_lista(self, autores):
        if not autores:
            return ""
        a0 = autores[0]
        primero = _apellido(a0) if _es_literal(a0) else (
            f"{_texto(a0.get('apellido'))}, {_texto(a0.get('nombre'))}".rstrip(", "))
        if len(autores) == 1:
            return primero
        if len(autores) == 2:
            a1 = autores[1]
            seg = _apellido(a1) if _es_literal(a1) else f"{_texto(a1.get('nombre'))} {_texto(a1.get('apellido'))}".strip()
            return f"{primero}, {self.lx['y']} {seg}" if self.idioma == "en" else f"{primero} {self.lx['y']} {seg}"
        return f"{primero}, {self.lx['et_al']}"

    def corto(self, autores, ref, max_antes_etal=2):
        return super().corto(autores, ref, max_antes_etal=2)

    def entrada(self, ref):
        r = Rico()
        lx = self.lx
        tipo = ref.get("tipo", "articulo")
        autores = ref.get("autores") or []
        if autores:
            r(self.autores_lista(autores)).punto()
            r(" ")
        titulo = _sentence(ref.get("titulo"))
        cont = _texto(ref.get("revista"))
        anio = _texto(ref.get("anio"))
        if tipo in ("libro", "informe", "datos", "software", "tesis"):
            r.i(titulo).punto()
        else:
            r(f"“{titulo}.”")
        partes: list[Rico] = []

        def parte(*trozos):
            x = Rico()
            for t, e in trozos:
                x(t, e)
            if not x.vacio():
                partes.append(x)
        if tipo in ("articulo", "capitulo", "congreso", "web", "preprint") and cont:
            parte((cont, "i"))
        if tipo == "capitulo" and ref.get("editores"):
            eds = ref["editores"]
            parte((f"{lx['editado']} " + _lista([f"{_texto(a.get('nombre'))} {_texto(a.get('apellido'))}".strip()
                                               if not _es_literal(a) else _apellido(a) for a in eds], lx["y"]), ""))
        if ref.get("volumen"):
            parte((f"vol. {_texto(ref['volumen'])}", ""))
        if ref.get("numero") and tipo == "articulo":
            parte((f"no. {_texto(ref['numero'])}", ""))
        if ref.get("editorial") and tipo not in ("articulo",):
            parte((_texto(ref["editorial"]), ""))
        if tipo == "tesis" and ref.get("institucion"):
            parte((_texto(ref["institucion"]), ""))
        if anio:
            parte((anio, ""))
        if ref.get("paginas"):
            p = _paginas(ref["paginas"])
            parte((("pp. " if "–" in p else "p. ") + p, ""))
        enlace = _doi_url(ref)
        if enlace:
            parte((enlace, "url"))
        for k, x in enumerate(partes):
            r(" " if k == 0 else ", ")
            r.trozos.extend(x.trozos)
        if partes:
            r.punto()
        return r


class Harvard(Estilo):
    clave = "harvard"

    def _nombre(self, a):
        if _es_literal(a):
            return _apellido(a)
        ini = iniciales(a.get("nombre", ""), espacio=False)
        return f"{_texto(a.get('apellido'))}, {ini}" if ini else _texto(a.get("apellido"))

    def autores_lista(self, autores):
        n = [self._nombre(a) for a in autores]
        if len(n) >= 4:
            return f"{n[0]} {self.lx['et_al']}"
        return _lista(n, self.lx["y"])

    def corto(self, autores, ref, max_antes_etal=3):
        return super().corto(autores, ref, max_antes_etal=3)

    def entrada(self, ref):
        r = Rico()
        lx = self.lx
        tipo = ref.get("tipo", "articulo")
        autores = ref.get("autores") or []
        anio = _anio(ref, self.idioma)
        titulo = _sentence(ref.get("titulo"))
        if autores:
            r(self.autores_lista(autores) + f" ({anio}) ")
        cont = _texto(ref.get("revista"))
        if tipo in ("articulo", "capitulo", "congreso", "preprint"):
            r(f"‘{titulo}’")
            if not autores:
                r(f" ({anio})")
            if tipo == "articulo":
                if cont:
                    r(", ").i(cont)
                vol, num = _texto(ref.get("volumen")), _texto(ref.get("numero"))
                if vol:
                    r(", " + vol + (f"({num})" if num else ""))
                if ref.get("paginas"):
                    r(", pp. " + _paginas(ref["paginas"]))
                r.punto()
            else:
                r(f", {lx['en'].lower()} ")
                eds = ref.get("editores") or []
                if eds:
                    r(_lista([self._nombre(a) for a in eds], lx["y"]) + f" ({'eds.' if len(eds) > 1 else 'ed.'}) ")
                r.i(cont)
                r.punto()
                lugar, edit = _texto(ref.get("lugar")), _texto(ref.get("editorial"))
                if lugar or edit:
                    r(" " + ": ".join(x for x in (lugar, edit) if x))
                if ref.get("paginas"):
                    r(", pp. " + _paginas(ref["paginas"]))
                r.punto()
        else:
            r.i(titulo)
            if not autores:
                r(f" ({anio})")
            r.punto()
            ed = _edicion(ref, self.idioma)
            if ed:
                r(" " + ed)
            if tipo == "tesis":
                r(" " + _tipo_tesis(ref, self.idioma, "harvard") + ". " + _texto(ref.get("institucion")))
                r.punto()
            elif tipo != "web":
                lugar, edit = _texto(ref.get("lugar")), _texto(ref.get("editorial") or ref.get("institucion"))
                if lugar or edit:
                    r(" " + ": ".join(x for x in (lugar, edit) if x)).punto()
        enlace = _doi_url(ref)
        if enlace:
            r(" " + ("Available at: " if self.idioma == "en" else lx["disponible"] + ": ")).url(enlace)
            if ref.get("fecha_acceso"):
                f = _fecha_larga(ref["fecha_acceso"], self.idioma, britanico=True)
                r(f" ({'Accessed: ' + f if self.idioma == 'en' else lx['consultado'].format(f=f)})")
            r.punto()
        return r


class Nature(Estilo):
    clave = "nature"

    def _nombre(self, a):
        if _es_literal(a):
            return _apellido(a)
        ini = iniciales(a.get("nombre", ""))
        return f"{_texto(a.get('apellido'))}, {ini}" if ini else _texto(a.get("apellido"))

    def autores_lista(self, autores):
        n = [self._nombre(a) for a in autores]
        if len(n) > 5:
            return f"{n[0]} {self.lx['et_al']}"
        if len(n) == 2:
            return f"{n[0]} & {n[1]}"
        return _lista(n, "&")

    def entrada(self, ref):
        r = Rico()
        tipo = ref.get("tipo", "articulo")
        autores = ref.get("autores") or []
        if autores:
            r(self.autores_lista(autores)).punto()
            r(" ")
        titulo = _sentence(ref.get("titulo"))
        anio = _texto(ref.get("anio"))
        cont = _texto(ref.get("revista_abrev") or ref.get("revista"))
        if tipo == "articulo" or tipo == "preprint":
            r(titulo).punto()
            if cont:
                r(" ").i(cont)
            if ref.get("volumen"):
                r(" ").b(_texto(ref["volumen"]))
            if ref.get("paginas"):
                r(", " + _paginas(ref["paginas"]))
            if anio:
                r(f" ({anio})")
            r.punto()
        elif tipo == "capitulo":
            r(titulo + ". " + ("in " if self.idioma == "en" else self.lx["en"].lower() + " ")).i(_texto(ref.get("revista")))
            eds = ref.get("editores") or []
            interior = []
            if eds:
                interior.append(("eds " if self.idioma == "en" else self.lx["eds"] + " ") +
                                _lista([self._nombre(a) for a in eds], "&"))
            if interior:
                r(" (" + "; ".join(interior) + ")")
            if ref.get("paginas"):
                r(" " + _paginas(ref["paginas"]))
            dentro = ", ".join(x for x in (_texto(ref.get("editorial")), anio) if x)
            if dentro:
                r(f" ({dentro})")
            r.punto()
        else:
            r.i(titulo)
            dentro = ", ".join(x for x in (_texto(ref.get("editorial") or ref.get("institucion") or ref.get("revista")), anio) if x)
            if dentro:
                r(f" ({dentro})")
            r.punto()
        enlace = _doi_url(ref)
        if enlace:
            r(" ").url(enlace)
        return r


class ACS(Estilo):
    clave = "acs"

    def _nombre(self, a):
        if _es_literal(a):
            return _apellido(a)
        ini = iniciales(a.get("nombre", ""))
        return f"{_texto(a.get('apellido'))}, {ini}" if ini else _texto(a.get("apellido"))

    def autores_lista(self, autores):
        n = [self._nombre(a) for a in autores]
        if len(n) > 10:
            return "; ".join(n[:10]) + f"; {self.lx['et_al']}"
        return "; ".join(n)

    def entrada(self, ref):
        r = Rico()
        tipo = ref.get("tipo", "articulo")
        autores = ref.get("autores") or []
        if autores:
            r(self.autores_lista(autores)).punto()
            r(" ")
        titulo = _sentence(ref.get("titulo"))
        anio = _texto(ref.get("anio"))
        cont = _texto(ref.get("revista_abrev") or ref.get("revista"))
        if tipo in ("articulo", "preprint"):
            r(titulo).punto()
            if cont:
                r(" ").i(cont)
            if anio:
                r(" ").b(anio)
            if ref.get("volumen"):
                r(", ").i(_texto(ref["volumen"]))
            if ref.get("numero"):
                r(f" ({_texto(ref['numero'])})")
            if ref.get("paginas"):
                r(", " + _paginas(ref["paginas"]))
            r.punto()
        elif tipo == "capitulo":
            r(titulo + ". " + ("In " if self.idioma == "en" else self.lx["en"] + " ")).i(_texto(ref.get("revista")))
            eds = ref.get("editores") or []
            if eds:
                r("; " + "; ".join(self._nombre(a) for a in eds) + (", Eds." if len(eds) > 1 else ", Ed."))
            edit, lugar = _texto(ref.get("editorial")), _texto(ref.get("lugar"))
            if edit or lugar:
                r("; " + ": ".join(x for x in (edit, lugar) if x))
            if anio:
                r(", " + anio)
            if ref.get("paginas"):
                r("; pp " + _paginas(ref["paginas"]))
            r.punto()
        else:
            r.i(titulo)
            ed = _edicion(ref, self.idioma)
            if ed:
                r(", " + ed)
            edit, lugar = _texto(ref.get("editorial") or ref.get("institucion")), _texto(ref.get("lugar"))
            if edit or lugar:
                r("; " + ": ".join(x for x in (edit, lugar) if x))
            if anio:
                r(", " + anio)
            r.punto()
        enlace = _doi_url(ref)
        if enlace:
            r(" ").url(enlace)
            if tipo == "web" and ref.get("fecha_acceso"):
                r(f" ({'accessed' if self.idioma == 'en' else self.lx['consultado'].split()[0].lower()} {ref['fecha_acceso']})")
            r.punto()
        return r


CLASES = {"apa": APA, "vancouver": Vancouver, "ieee": IEEE, "chicago": Chicago, "mla": MLA,
          "harvard": Harvard, "nature": Nature, "acs": ACS}


def estilo(clave: str, idioma: str = "es") -> Estilo:
    return CLASES.get(clave, APA)(idioma or "en")


# ====================================================================== referencias y claves
_CLAVE_OK = re.compile(r"^[A-Za-z0-9_:.\-]+$")


def _ascii(t: str) -> str:
    return unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode()


def clave_sugerida(ref: dict, usadas=()) -> str:
    autores = ref.get("autores") or []
    base = _apellido(autores[0]) if autores else (_texto(ref.get("titulo")).split() or ["ref"])[0]
    base = re.sub(r"[^a-z]", "", _ascii(base).lower())[:20] or "ref"
    anio = re.sub(r"\D", "", _texto(ref.get("anio")))[:4]
    clave = base + anio
    usadas = set(usadas)
    if clave not in usadas:
        return clave
    for letra in "abcdefghijklmnopqrstuvwxyz":
        if clave + letra not in usadas:
            return clave + letra
    n = 2
    while f"{clave}-{n}" in usadas:
        n += 1
    return f"{clave}-{n}"


def normalizar_ref(ref: dict) -> dict:
    r = {k: v for k, v in (ref or {}).items() if v not in (None, "")}
    r["tipo"] = r.get("tipo") if r.get("tipo") in TIPOS else "articulo"
    for k in CAMPOS_TEXTO:
        if k in r and not isinstance(r[k], str):
            r[k] = str(r[k])
    if r.get("doi"):
        r["doi"] = limpiar_doi(r["doi"])
    for k in ("autores", "editores"):
        lista = []
        for a in r.get(k) or []:
            if isinstance(a, str):
                lista.append(_autor_desde_texto(a))
            elif isinstance(a, dict):
                if _texto(a.get("literal")):
                    lista.append({"literal": _texto(a["literal"])})
                elif _texto(a.get("apellido")) or _texto(a.get("nombre")):
                    lista.append({"apellido": _texto(a.get("apellido")), "nombre": _texto(a.get("nombre"))})
        r[k] = lista
    return r


def normalizar_lista(refs) -> list[dict]:
    salida, usadas = [], set()
    for ref in refs or []:
        if not isinstance(ref, dict):
            continue
        r = normalizar_ref(ref)
        clave = _texto(r.get("clave"))
        if not clave or not _CLAVE_OK.match(clave) or clave in usadas:
            clave = clave_sugerida(r, usadas)
        r["clave"] = clave
        usadas.add(clave)
        salida.append(r)
    return salida


def _autor_desde_texto(t: str) -> dict:
    t = _texto(t)
    if t.startswith("{") and t.endswith("}"):
        return {"literal": t[1:-1].strip()}
    if "," in t:
        ap, _, no = t.partition(",")
        return {"apellido": ap.strip(), "nombre": no.strip()}
    partes = t.split()
    if len(partes) == 1:
        return {"apellido": partes[0], "nombre": ""}
    # partículas (van, de, von, del, da, di, le) pasan al apellido
    i = len(partes) - 1
    while i > 1 and partes[i - 1].lower() in ("van", "von", "de", "del", "der", "da", "di", "le", "la", "dos", "das"):
        i -= 1
    return {"apellido": " ".join(partes[i:]), "nombre": " ".join(partes[:i])}


# ====================================================================== citas
_CITA = re.compile(r"\[(@[^\]\n]+)\]")


def _partes_cita(contenido: str) -> list[tuple[str, str]]:
    """«@a; @b, p. 12» → [("a", ""), ("b", "p. 12")]."""
    salida = []
    for trozo in contenido.split(";"):
        trozo = trozo.strip()
        if not trozo.startswith("@"):
            continue
        clave, _, loc = trozo[1:].partition(",")
        salida.append((clave.strip(), loc.strip()))
    return salida


def claves_citadas(texto: str) -> list[str]:
    salida = []
    for m in _CITA.finditer(str(texto or "")):
        for clave, _ in _partes_cita(m.group(1)):
            salida.append(clave)
    return salida


def _rangos(numeros: list[int]) -> str:
    numeros = sorted(set(numeros))
    partes, i = [], 0
    while i < len(numeros):
        j = i
        while j + 1 < len(numeros) and numeros[j + 1] == numeros[j] + 1:
            j += 1
        if j - i >= 2:
            partes.append(f"{numeros[i]}–{numeros[j]}")
        else:
            partes.extend(str(n) for n in numeros[i:j + 1])
        i = j + 1
    return ",".join(partes)


class Contexto:
    """Lo que el generador necesita: estilo, referencias, números y sufijos (2020a)."""

    def __init__(self, bib: dict, idioma: str):
        self.idioma = idioma if idioma in L else "en"
        self.clave_estilo = bib.get("estilo") if bib.get("estilo") in ESTILOS else "apa"
        self.info = ESTILOS[self.clave_estilo]
        self.est = estilo(self.clave_estilo, self.idioma)
        self.refs = normalizar_lista(bib.get("referencias") or [])
        self.por_clave = {r["clave"]: r for r in self.refs}
        self.orden: list[str] = []          # claves en orden de primera cita
        self.desconocidas: list[str] = []
        self._sufijos = self._calcular_sufijos()

    # --- autor-año: García 2020a, García 2020b
    def _calcular_sufijos(self) -> dict:
        if self.info["cita"] != "autor-año":
            return {}
        grupos: dict[tuple, list] = {}
        for r in self.refs:
            k = (self.est.corto(r.get("autores") or [], r), _texto(r.get("anio")))
            grupos.setdefault(k, []).append(r)
        sufijos = {}
        for k, lista in grupos.items():
            if len(lista) > 1 and k[1]:
                for i, r in enumerate(sorted(lista, key=lambda x: _ascii(_texto(x.get("titulo"))).lower())):
                    sufijos[r["clave"]] = "abcdefghijklmnopqrstuvwxyz"[i % 26]
        return sufijos

    def registrar(self, texto: str):
        for clave in claves_citadas(texto):
            if clave in self.por_clave and clave not in self.orden:
                self.orden.append(clave)

    def numero(self, clave: str) -> int | None:
        if clave in self.orden:
            return self.orden.index(clave) + 1
        return None

    def anio(self, ref: dict) -> str:
        return _anio(ref, self.idioma) + self._sufijos.get(ref["clave"], "")

    # --- la cita en LaTeX
    def cita(self, partes: list[tuple[str, str]]) -> str:
        conocidas = [(c, loc) for c, loc in partes if c in self.por_clave]
        for c, _ in partes:
            if c not in self.por_clave and c not in self.desconocidas:
                self.desconocidas.append(c)
        malas = "".join(r"\PCcitadesconocida{" + T.escapar(c) + "}" for c, _ in partes if c not in self.por_clave)
        if not conocidas:
            return malas
        tipo = self.info["cita"]
        lx = self.est.lx
        if tipo == "numero":
            nums = [self.numero(c) or 0 for c, _ in conocidas]
            locs = [loc for _, loc in conocidas if loc]
            cuerpo = _rangos([n for n in nums if n])
            if locs and len(conocidas) == 1:
                cuerpo += ", " + locs[0]
            marca = self.info.get("marca")
            if marca == "superindice":
                return r"\PCcitasup{" + T.escapar(cuerpo) + "}" + malas
            if marca == "parentesis":
                return r"\PCcita{(" + T.escapar(cuerpo) + ")}" + malas
            return r"\PCcita{[" + T.escapar(cuerpo).replace(",", ", ") + "]}" + malas
        trozos = []
        lista = conocidas
        if self.clave_estilo == "apa":
            lista = sorted(conocidas, key=lambda x: _ascii(self.est.corto(self.por_clave[x[0]].get("autores") or [],
                                                                           self.por_clave[x[0]])).lower())
        for c, loc in lista:
            r = self.por_clave[c]
            quien = self.est.corto(r.get("autores") or [], r)
            if tipo == "autor-pagina":                 # MLA
                trozos.append(" ".join(x for x in (quien, loc.replace("p. ", "").replace("pp. ", "")) if x))
                continue
            separador = " " if self.clave_estilo == "chicago" else ", "
            t = f"{quien}{separador}{self.anio(r)}"
            if loc:
                t += f", {loc}"
            trozos.append(t)
        return r"\PCcita{(" + T.escapar("; ".join(trozos)) + ")}" + malas

    # --- la lista de referencias
    def entradas(self, incluir: str = "citadas") -> list[tuple[str, Rico, dict]]:
        """[(etiqueta, texto rico, referencia)] en el orden del estilo."""
        if incluir == "todas":
            elegidas = [self.por_clave[c] for c in self.orden] + [r for r in self.refs if r["clave"] not in self.orden]
        else:
            elegidas = [self.por_clave[c] for c in self.orden]
        if self.info["orden"] == "alfabetico":
            elegidas = sorted(elegidas, key=lambda r: (
                _ascii(self.est.corto(r.get("autores") or [], r, 99) if r.get("autores") else _texto(r.get("titulo"))).lower(),
                _texto(r.get("anio")), self._sufijos.get(r["clave"], "")))
        salida = []
        for i, r in enumerate(elegidas, start=1):
            rico = self.est.entrada(self._con_sufijo(r))
            etiqueta = ""
            if self.info["lista"] == "numerica":
                n = self.numero(r["clave"]) or i
                etiqueta = self.info["etiqueta"].format(n=n)
            salida.append((etiqueta, rico, r))
        if self.info["lista"] == "numerica":
            salida.sort(key=lambda x: int(re.sub(r"\D", "", x[0]) or 0))
        return salida

    def _con_sufijo(self, r: dict) -> dict:
        s = self._sufijos.get(r["clave"])
        if s and _texto(r.get("anio")):
            r = dict(r)
            r["anio"] = _texto(r["anio"]) + s
        return r


def reemplazar_citas(texto: str, ctx: Contexto, formato: str) -> str:
    """Cambia [@clave] por la cita. En formato sencillo va dentro de {{ }} (LaTeX sin tocar),
    salvo si la cita ya está dentro de un trozo {{...}}: ahí se escribe tal cual."""
    if not texto or "[@" not in str(texto):
        return texto

    def citas(t: str, crudo: bool) -> str:
        if ctx.info.get("marca") == "superindice":     # la cita en superíndice va pegada a la palabra
            t = re.sub(r"[ \t]+(?=\[@)", "", t)
        return _CITA.sub(lambda m: (lambda x: x if crudo else "{{" + x + "}}")(ctx.cita(_partes_cita(m.group(1)))), t)
    texto = str(texto)
    if formato == "latex":
        return citas(texto, True)
    return "".join("{{" + citas(t, True) + "}}" if crudo else citas(t, False) for crudo, t in T._trozos_crudos(texto))


def formatear(refs: list[dict], estilo_clave: str = "apa", idioma: str = "es") -> list[dict]:
    """Para la aplicación: cada referencia formateada en HTML con su etiqueta."""
    ctx = Contexto({"estilo": estilo_clave, "referencias": refs}, idioma)
    for r in ctx.refs:
        ctx.orden.append(r["clave"])
    salida = []
    for etiqueta, rico, r in ctx.entradas("todas"):
        salida.append({"clave": r["clave"], "etiqueta": etiqueta, "html": rico.html(), "texto": rico.plano()})
    return salida


def ejemplo_cita(estilo_clave: str = "apa", idioma: str = "es") -> str:
    ej = [{"clave": "a", "tipo": "articulo", "anio": "2020", "titulo": "x",
           "autores": [{"apellido": "García", "nombre": "Ana"}, {"apellido": "López", "nombre": "Beatriz"}]}]
    ctx = Contexto({"estilo": estilo_clave, "referencias": ej}, idioma)
    ctx.orden = ["a"]
    latex = ctx.cita([("a", "")])
    m = re.search(r"\{(.*)\}", latex)
    t = m.group(1) if m else latex
    if "PCcitasup" in latex:
        return "texto¹"
    return t.replace(r"\&", "&")


# ====================================================================== importar: BibTeX
_ACENTOS = {"'": "\u0301", "`": "\u0300", "^": "\u0302", '"': "\u0308", "~": "\u0303", "=": "\u0304",
            ".": "\u0307", "u": "\u0306", "v": "\u030C", "H": "\u030B", "c": "\u0327", "k": "\u0328", "r": "\u030A"}
_ESPECIALES = {r"\ss": "ß", r"\o": "ø", r"\O": "Ø", r"\aa": "å", r"\AA": "Å", r"\ae": "æ", r"\AE": "Æ",
               r"\oe": "œ", r"\OE": "Œ", r"\l": "ł", r"\L": "Ł", r"\i": "ı", r"\j": "ȷ", r"\&": "&", r"\%": "%",
               r"\$": "$", r"\#": "#", r"\_": "_", r"\textendash": "–", r"\textemdash": "—"}


def latex_a_texto(t: str) -> str:
    """Convierte acentos y símbolos de LaTeX a Unicode y quita las llaves de protección."""
    t = str(t or "")

    def acento(m):
        cmd, letra = m.group(1), m.group(2) or m.group(3)
        letra = {"\\i": "i", "\\j": "j"}.get(letra, letra)
        return unicodedata.normalize("NFC", letra + _ACENTOS.get(cmd, ""))
    # \'a, \'{a}, {\'a}; las órdenes con letra (\c, \u, \v…) solo con llaves o espacio: \c{c}, \v s
    t = re.sub(r"\\([\'`^\"~=.])\s*(?:\{(\\?[A-Za-z])\}|(\\?[A-Za-z]))", acento, t)
    t = re.sub(r"\\([uvHckr])(?:\s*\{(\\?[A-Za-z])\}|\s+([A-Za-z])(?![A-Za-z]))", acento, t)
    for k in sorted(_ESPECIALES, key=len, reverse=True):
        # tras una orden con letras (\ss, \o) el espacio solo separa; tras \& o \% es un espacio de verdad
        cola = r"(?![A-Za-z])\s?(\{\})?" if k[1:].isalpha() else ""
        t = re.sub(re.escape(k) + cola, _ESPECIALES[k], t)
    t = re.sub(r"\\(textit|emph|textbf|textrm|textsf|texttt|mathrm|textsc|textsuperscript|textsubscript)\s*\{([^{}]*)\}", r"\2", t)
    t = re.sub(r"\\(it|bf|em|sc|rm|tt|sl|sf|small|large|normalfont|upshape|itshape|bfseries)(?![A-Za-z])\s*", "", t)
    t = re.sub(r"\\(LaTeX|TeX|BibTeX)(?![A-Za-z])\s?(\{\})?", lambda m: m.group(1) + (" " if m.group(0).endswith(" ") else ""), t)
    t = re.sub(r"\\([A-Za-z]+)(?![A-Za-z])", r"\1", t)
    t = t.replace("---", "—").replace("--", "–").replace("~", " ")
    t = re.sub(r"(?<!\\)[{}]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _bib_valor(s: str, i: int, macros: dict) -> tuple[str, int]:
    """Lee el valor de un campo desde s[i] (llaves, comillas, número o macro, con #)."""
    partes = []
    n = len(s)
    while i < n:
        while i < n and s[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        c = s[i]
        if c == "{":
            prof, j = 0, i
            while j < n:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == "{":
                    prof += 1
                elif s[j] == "}":
                    prof -= 1
                    if prof == 0:
                        break
                j += 1
            partes.append(s[i + 1:j])
            i = j + 1
        elif c == '"':
            prof, j = 0, i + 1
            while j < n:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == "{":
                    prof += 1
                elif s[j] == "}":
                    prof -= 1
                elif s[j] == '"' and prof == 0:
                    break
                j += 1
            partes.append(s[i + 1:j])
            i = j + 1
        else:
            m = re.match(r"[A-Za-z0-9_:.\-+/]+", s[i:])
            if not m:
                break
            palabra = m.group(0)
            partes.append(macros.get(palabra.lower(), palabra))
            i += len(palabra)
        while i < n and s[i] in " \t\r\n":
            i += 1
        if i < n and s[i] == "#":
            i += 1
            continue
        break
    return "".join(partes), i


TIPOS_BIB = {"article": "articulo", "book": "libro", "inbook": "capitulo", "incollection": "capitulo",
             "inproceedings": "congreso", "conference": "congreso", "proceedings": "congreso",
             "phdthesis": "tesis", "mastersthesis": "tesis", "thesis": "tesis", "techreport": "informe",
             "report": "informe", "online": "web", "electronic": "web", "www": "web", "dataset": "datos",
             "data": "datos", "software": "software", "unpublished": "otro", "misc": "otro", "manual": "otro",
             "booklet": "otro"}


def leer_bibtex(texto: str) -> tuple[list[dict], list[str]]:
    refs, errores, macros = [], [], {}
    s = str(texto)
    pos = 0
    while True:
        m = re.compile(r"@\s*([A-Za-z]+)\s*[{(]").search(s, pos)
        if not m:
            break
        tipo = m.group(1).lower()
        inicio = m.end()
        # final de la entrada (llaves equilibradas)
        prof, j = 1, inicio
        while j < len(s) and prof:
            if s[j] == "\\":
                j += 2
                continue
            if s[j] in "{(":
                prof += 1
            elif s[j] in "})":
                prof -= 1
            j += 1
        if prof:
            errores.append(f"La entrada «{s[m.start():m.start() + 40].strip()}…» no se cierra: falta una llave")
            break
        cuerpo = s[inicio:j - 1]
        pos = j
        if tipo == "comment" or tipo == "preamble":
            continue
        if tipo == "string":
            mm = re.match(r"\s*([A-Za-z][\w-]*)\s*=\s*", cuerpo)
            if mm:
                valor, _ = _bib_valor(cuerpo, mm.end(), macros)
                macros[mm.group(1).lower()] = valor
            continue
        mm = re.match(r"\s*([^,\s]+)\s*,", cuerpo)
        if not mm:
            errores.append(f"Entrada @{tipo} sin clave")
            continue
        clave = mm.group(1).strip()
        campos, i = {}, mm.end()
        while i < len(cuerpo):
            mc = re.match(r"\s*([A-Za-z][\w\-:]*)\s*=\s*", cuerpo[i:])
            if not mc:
                break
            nombre = mc.group(1).lower()
            valor, k = _bib_valor(cuerpo, i + mc.end(), macros)
            campos[nombre] = valor
            i = k
            while i < len(cuerpo) and cuerpo[i] in " \t\r\n,":
                i += 1
        refs.append(_desde_bib(tipo, clave, campos))
    return refs, errores


def _personas_bib(valor: str) -> list[dict]:
    if not valor.strip():
        return []
    nombres, prof, actual, i = [], 0, "", 0
    while i < len(valor):
        c = valor[i]
        if c == "{":
            prof += 1
        elif c == "}":
            prof -= 1
        if prof == 0 and valor[i:i + 5].lower() == " and " :
            nombres.append(actual)
            actual = ""
            i += 5
            continue
        actual += c
        i += 1
    nombres.append(actual)
    salida = []
    for n in nombres:
        n = n.strip()
        if not n or n.lower() == "others":
            continue
        if n.startswith("{") and n.endswith("}") and n.count("{") == 1:
            salida.append({"literal": latex_a_texto(n)})
            continue
        n = latex_a_texto(n) if "," not in n else n
        if "," in n:
            partes = [p.strip() for p in n.split(",")]
            ap = latex_a_texto(partes[0])
            no = latex_a_texto(partes[-1]) if len(partes) > 1 else ""
            salida.append({"apellido": ap, "nombre": no})
        else:
            salida.append(_autor_desde_texto(n))
    return salida


def _desde_bib(tipo: str, clave: str, c: dict) -> dict:
    t = TIPOS_BIB.get(tipo, "otro")
    if t == "otro" and (c.get("url") or c.get("howpublished", "").startswith("\\url")) and not c.get("journal"):
        t = "web"
    ref = {"clave": clave, "tipo": t}
    ref["autores"] = _personas_bib(c.get("author", ""))
    if c.get("editor"):
        ref["editores"] = _personas_bib(c["editor"])
    anio = c.get("year") or (c.get("date", "")[:4])
    mapa = {"titulo": c.get("title"), "anio": anio,
            "revista": c.get("journal") or c.get("journaltitle") or c.get("booktitle") or c.get("eventtitle")
            or c.get("organization") if t not in ("libro", "tesis", "informe") else None,
            "volumen": c.get("volume"), "numero": c.get("number") or c.get("issue"),
            "paginas": c.get("pages"), "editorial": c.get("publisher"),
            "lugar": c.get("address") or c.get("location"), "edicion": c.get("edition"),
            "doi": c.get("doi"), "url": c.get("url"), "fecha_acceso": c.get("urldate"),
            "institucion": c.get("school") or c.get("institution"), "version": c.get("version"),
            "nota": c.get("note")}
    if tipo == "phdthesis":
        mapa["grado"] = "doctoral"
    elif tipo == "mastersthesis":
        mapa["grado"] = "maestría"
    for k, v in mapa.items():
        if v:
            ref[k] = latex_a_texto(v) if k not in ("url", "doi") else re.sub(r"\\url\{(.*)\}", r"\1", v).strip()
    if ref.get("paginas"):
        ref["paginas"] = _paginas(ref["paginas"])
    return normalizar_ref(ref)


# ====================================================================== importar: RIS
TIPOS_RIS = {"JOUR": "articulo", "JFULL": "articulo", "MGZN": "articulo", "NEWS": "articulo", "EJOUR": "articulo",
             "BOOK": "libro", "EBOOK": "libro", "EDBOOK": "libro", "CHAP": "capitulo", "ECHAP": "capitulo",
             "CONF": "congreso", "CPAPER": "congreso", "THES": "tesis", "RPRT": "informe", "ELEC": "web",
             "WEB": "web", "BLOG": "web", "DATA": "datos", "COMP": "software", "UNPB": "preprint", "GEN": "otro"}


def leer_ris(texto: str) -> tuple[list[dict], list[str]]:
    refs, actual = [], None
    for linea in str(texto).splitlines():
        m = re.match(r"^([A-Z][A-Z0-9])\s{2}-\s?(.*)$", linea.strip("\ufeff"))
        if not m:
            continue
        tag, valor = m.group(1), m.group(2).strip()
        if tag == "TY":
            actual = {"tipo": TIPOS_RIS.get(valor, "otro"), "autores": [], "editores": []}
            continue
        if actual is None:
            continue
        if tag == "ER":
            refs.append(normalizar_ref(actual))
            actual = None
        elif tag in ("AU", "A1"):
            actual["autores"].append(_autor_desde_texto(valor))
        elif tag in ("ED", "A2", "A3") and actual["tipo"] in ("capitulo", "libro"):
            actual["editores"].append(_autor_desde_texto(valor))
        elif tag in ("PY", "Y1", "DA") and not actual.get("anio"):
            mm = re.search(r"\d{4}", valor)
            if mm:
                actual["anio"] = mm.group(0)
        elif tag in ("TI", "T1") and not actual.get("titulo"):
            actual["titulo"] = valor
        elif tag in ("JO", "JF", "T2", "BT", "SE") and not actual.get("revista"):
            actual["revista"] = valor
        elif tag in ("JA", "J2"):
            actual["revista_abrev"] = valor
        elif tag == "VL":
            actual["volumen"] = valor
        elif tag in ("IS", "M1") and not actual.get("numero"):
            actual["numero"] = valor
        elif tag == "SP":
            actual["paginas"] = valor
        elif tag == "EP" and actual.get("paginas"):
            actual["paginas"] = f"{actual['paginas']}–{valor}"
        elif tag == "PB":
            actual["editorial"] = valor
        elif tag == "CY":
            actual["lugar"] = valor
        elif tag == "ET":
            actual["edicion"] = valor
        elif tag == "DO":
            actual["doi"] = valor
        elif tag in ("UR", "L2") and not actual.get("url"):
            actual["url"] = valor
        elif tag == "Y2":
            actual["fecha_acceso"] = valor.replace("/", "-").strip("-")
        elif tag == "N1" and not actual.get("nota"):
            actual["nota"] = valor
    if actual:
        refs.append(normalizar_ref(actual))
    return refs, []


# ====================================================================== importar: CSL-JSON y DOI
TIPOS_CSL = {"article-journal": "articulo", "article-magazine": "articulo", "article-newspaper": "articulo",
             "review": "articulo", "book": "libro", "chapter": "capitulo", "paper-conference": "congreso",
             "thesis": "tesis", "report": "informe", "webpage": "web", "post-weblog": "web", "post": "web",
             "dataset": "datos", "software": "software", "article": "preprint", "posted-content": "preprint",
             "manuscript": "otro"}


def _personas_csl(lista) -> list[dict]:
    salida = []
    for a in lista or []:
        if not isinstance(a, dict):
            continue
        if a.get("literal") or a.get("name"):
            salida.append({"literal": a.get("literal") or a.get("name")})
        else:
            apellido = " ".join(x for x in (a.get("non-dropping-particle"), a.get("family")) if x)
            salida.append({"apellido": apellido or "", "nombre": a.get("given") or ""})
    return salida


def _fecha_csl(f) -> str:
    try:
        partes = (f or {}).get("date-parts", [[]])[0]
    except (AttributeError, IndexError, TypeError):
        return ""
    return "-".join(f"{int(x):02d}" if k else str(int(x)) for k, x in enumerate(partes) if x)


def desde_csl(d: dict) -> dict:
    def primero(v):
        if isinstance(v, list):
            return v[0] if v else ""
        return v or ""
    tipo = TIPOS_CSL.get(d.get("type"), "otro")
    fecha = _fecha_csl(d.get("issued")) or _fecha_csl(d.get("published-print")) or _fecha_csl(d.get("published-online"))
    ref = {"tipo": tipo, "titulo": re.sub(r"<[^>]+>", "", str(primero(d.get("title")) or "")),
           "autores": _personas_csl(d.get("author")), "editores": _personas_csl(d.get("editor")),
           "anio": fecha[:4] if fecha else "", "revista": primero(d.get("container-title")),
           "revista_abrev": primero(d.get("container-title-short") or d.get("journalAbbreviation")),
           "volumen": d.get("volume"), "numero": d.get("issue") or (d.get("number") if tipo == "informe" else None),
           "paginas": d.get("page"), "editorial": d.get("publisher"), "lugar": d.get("publisher-place"),
           "edicion": d.get("edition"), "doi": d.get("DOI"), "url": d.get("URL"),
           "fecha_acceso": _fecha_csl(d.get("accessed")), "version": d.get("version"), "grado": d.get("genre"),
           "institucion": d.get("publisher") if tipo == "tesis" else None}
    if tipo == "web" and fecha and len(fecha) > 4:
        ref["fecha"] = fecha
    if d.get("id") and isinstance(d.get("id"), str) and _CLAVE_OK.match(d["id"]):
        ref["clave"] = d["id"]
    if ref.get("paginas"):
        ref["paginas"] = _paginas(ref["paginas"])
    return normalizar_ref(ref)


def leer_csl(texto: str) -> tuple[list[dict], list[str]]:
    datos = json.loads(texto)
    if isinstance(datos, dict):
        datos = datos.get("items") or [datos]
    return [desde_csl(d) for d in datos if isinstance(d, dict)], []


def importar_texto(texto: str) -> tuple[list[dict], list[str]]:
    """Detecta el formato (CSL-JSON, RIS o BibTeX) y lee las referencias."""
    t = str(texto or "").strip().lstrip("\ufeff")
    if not t:
        return [], ["No hay nada que importar"]
    try:
        if t[0] in "[{":
            return leer_csl(t)
    except ValueError as exc:
        return [], [f"El JSON no es válido: {exc}"]
    if re.search(r"^TY\s{2}-", t, re.M):
        return leer_ris(t)
    if "@" in t:
        refs, errores = leer_bibtex(t)
        if refs:
            return refs, errores
    return [], ["No reconozco el formato: usa BibTeX (.bib), RIS (.ris) o CSL-JSON (.json)"]


def limpiar_doi(doi: str) -> str:
    d = _texto(doi)
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", d, flags=re.I).strip()
    return d.strip("<>").rstrip(".,;")


def buscar_doi(doi: str, tiempo: float = 12.0) -> dict:
    """Pide a doi.org los datos de la referencia (CSL-JSON). Necesita conexión a internet."""
    import urllib.error
    import urllib.request
    d = limpiar_doi(doi)
    if not re.match(r"^10\.\d{4,9}/\S+$", d):
        raise ValueError("No parece un DOI (empieza por 10. y lleva una barra, por ejemplo 10.1038/nature12373)")
    from urllib.parse import quote
    req = urllib.request.Request("https://doi.org/" + quote(d, safe="/:;()._-"),
                                 headers={"Accept": "application/vnd.citationstyles.csl+json",
                                          "User-Agent": "DocsLab (gestor de referencias)"})
    try:
        with urllib.request.urlopen(req, timeout=tiempo) as r:
            datos = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ValueError(f"doi.org no conoce el DOI {d}") from exc
        raise ValueError(f"doi.org respondió con el código {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValueError("No hay conexión con doi.org. Comprueba tu conexión a internet o escribe la referencia a mano.") from exc
    ref = desde_csl(datos)
    ref.setdefault("doi", d)
    return ref


# ====================================================================== exportar a BibTeX
_TIPOS_A_BIB = {"articulo": "article", "libro": "book", "capitulo": "incollection", "congreso": "inproceedings",
                "tesis": "phdthesis", "informe": "techreport", "web": "online", "datos": "dataset",
                "software": "software", "preprint": "misc", "otro": "misc"}


def _bib_personas(lista) -> str:
    salida = []
    for a in lista or []:
        if _es_literal(a):
            salida.append("{" + _apellido(a) + "}")
        else:
            salida.append(f"{_texto(a.get('apellido'))}, {_texto(a.get('nombre'))}".rstrip(", "))
    return " and ".join(salida)


def a_bibtex(refs: list[dict]) -> str:
    bloques = []
    for r in normalizar_lista(refs):
        tipo = _TIPOS_A_BIB.get(r["tipo"], "misc")
        if r["tipo"] == "tesis" and re.search(r"maest|mast|mestr", r.get("grado", ""), re.I):
            tipo = "mastersthesis"
        campos = []

        def campo(nombre, valor):
            if valor:
                campos.append(f"  {nombre} = {{{valor}}}")
        campo("author", _bib_personas(r.get("autores")))
        campo("editor", _bib_personas(r.get("editores")))
        campo("title", r.get("titulo"))
        contenedor = {"articulo": "journal", "capitulo": "booktitle", "congreso": "booktitle"}.get(r["tipo"], "howpublished")
        campo(contenedor, r.get("revista"))
        campo("year", r.get("anio"))
        campo("volume", r.get("volumen"))
        campo("number", r.get("numero"))
        campo("pages", _texto(r.get("paginas")).replace("–", "--"))
        campo("publisher", r.get("editorial"))
        campo("address", r.get("lugar"))
        campo("edition", r.get("edicion"))
        campo("school" if r["tipo"] == "tesis" else "institution", r.get("institucion"))
        campo("doi", _doi(r))
        campo("url", r.get("url"))
        campo("urldate", r.get("fecha_acceso"))
        campo("version", r.get("version"))
        campo("note", r.get("nota"))
        bloques.append(f"@{tipo}{{{r['clave']},\n" + ",\n".join(campos) + "\n}")
    return "\n\n".join(bloques) + ("\n" if bloques else "")
