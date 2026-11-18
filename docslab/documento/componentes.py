# SPDX-License-Identifier: AGPL-3.0-only
"""Componente Lab: elementos propios para usar dentro de las cajas del póster.

Un componente se hace de tres maneras:

* «visual» (sin código): una pila de piezas (título, texto, cifra, imagen, lista,
  etiqueta, icono, separador, espacio, columnas y, si se quiere, un trozo de LaTeX)
  dentro de una caja con el estilo y los colores que se elijan. DocsLab escribe el
  LaTeX.
* «latex» (con código): una plantilla LaTeX con huecos {{campo}} que se rellenan con
  lo que se escribe en el inspector. Admite secciones: {{#campo}}…{{/campo}} (solo
  si tiene valor; con una lista se repite por cada elemento, que es {{.}}) y
  {{^campo}}…{{/campo}} (solo si está vacío). Un preámbulo opcional define órdenes.
* «preajuste» (recrear sin código): uno de los 69 componentes incluidos con algunos
  valores fijos y solo ciertos campos editables.

Los incluidos se pueden «recrear» también con código: la plantilla es su propia
definición en postercientifico.sty, con los argumentos cambiados por {{campo}}.

Los componentes viven en datos/componentes/<id>.json. Al usarse en un póster, su
definición se copia en modelo["componentes"][id], así que el póster no depende de la
biblioteca (se exporta y compila igual en Overleaf).
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import texto as T
from . import variantes as V

STY = Path(__file__).resolve().parents[2] / "latex" / "postercientifico.sty"

MODOS = ("visual", "latex", "preajuste")
TIPOS_CAMPO = ("texto", "parrafo", "latex", "lista", "pares", "hitos", "tabla", "flechas", "imagen", "color",
               "numero", "porcentaje", "fraccion", "angulo", "dimension", "seleccion", "booleano")
NOMBRES_TIPO = {
    "texto": "Texto de una línea", "parrafo": "Párrafos", "latex": "Código LaTeX", "lista": "Lista",
    "pares": "Pares (término y descripción)", "hitos": "Hitos (fecha y texto)", "tabla": "Tabla",
    "flechas": "Flechas sobre una imagen", "imagen": "Imagen", "color": "Color", "numero": "Número",
    "porcentaje": "Porcentaje (se escribe como fracción: 45 → 0.45)", "fraccion": "Fracción (0 a 1)",
    "angulo": "Ángulo", "dimension": "Medida (12mm, 2em…)", "seleccion": "Una opción de una lista",
    "booleano": "Sí o no",
}
_NOMBRE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,39}$")
_ID = re.compile(r"^k-[a-z0-9]{6,16}$")
RESERVADOS = {"id", "tipo", "visible"}
NO_PREAJUSTE = {"latex", "espacio", "bibliografia"}
LIMITE_CODIGO = 100_000
LIMITE_CAMPOS = 40


def nuevo_id() -> str:
    return "k-" + secrets.token_hex(4)


def es_id(cid) -> bool:
    return bool(_ID.match(str(cid or "")))


# ====================================================================== campos
def _defecto_tipo(tipo: str):
    return {"lista": [], "pares": [], "hitos": [], "flechas": [], "tabla": {"columnas": "lr", "encabezado": True,
            "filas": [["", ""]]}, "booleano": False, "numero": 1, "porcentaje": 100, "fraccion": 0.5,
            "angulo": 0}.get(tipo, "")


def _limpiar_valor(tipo: str, v):
    """Un valor con la forma de su tipo (para defectos y valores fijos)."""
    if tipo == "lista":
        if isinstance(v, str):
            v = v.split("\n")
        return [str(x) for x in (v or []) if str(x).strip()] if isinstance(v, list) else []
    if tipo in ("pares", "hitos"):
        return [[str(p[0]), str(p[1])] for p in (v or []) if isinstance(p, (list, tuple)) and len(p) >= 2] \
            if isinstance(v, list) else []
    if tipo == "flechas":
        return [list(f[:5]) for f in (v or []) if isinstance(f, (list, tuple)) and len(f) >= 5] \
            if isinstance(v, list) else []
    if tipo == "tabla":
        return copy.deepcopy(v) if isinstance(v, dict) else _defecto_tipo("tabla")
    if tipo == "booleano":
        return v is True or str(v).lower() in ("true", "1", "si", "sí")
    if tipo in ("numero", "porcentaje", "fraccion", "angulo"):
        try:
            x = float(v)
            return int(x) if x.is_integer() else x
        except (TypeError, ValueError):
            return _defecto_tipo(tipo)
    return "" if v is None else str(v)


def _opciones(lista) -> list[dict]:
    salida, vistos = [], set()
    for o in lista or []:
        if isinstance(o, dict):
            valor, texto = str(o.get("valor", "")).strip(), str(o.get("texto") or o.get("valor") or "").strip()
        else:
            valor = texto = str(o).strip()
        if valor and valor not in vistos and not re.search(r"[{}\\%#]", valor):
            vistos.add(valor)
            salida.append({"valor": valor[:60], "texto": (texto or valor)[:80]})
    return salida[:40]


def normalizar_campos(lista, permitidos: dict | None = None) -> list[dict]:
    """Campos válidos y sin nombres repetidos. «permitidos» (nombre → campo) limita los
    campos a los de una variante (preajustes) y les impone su tipo."""
    salida, usados = [], set()
    for c in lista or []:
        if not isinstance(c, dict):
            continue
        nombre = str(c.get("nombre") or "").strip()
        if not _NOMBRE.match(nombre) or nombre in RESERVADOS or nombre in usados:
            continue
        if permitidos is not None:
            if nombre not in permitidos:
                continue
            base = permitidos[nombre]
            tipo, opciones = base["tipo"], base.get("opciones")
        else:
            tipo = c.get("tipo") if c.get("tipo") in TIPOS_CAMPO else "texto"
            opciones = c.get("opciones")
        d = {"nombre": nombre, "tipo": tipo, "etiqueta": str(c.get("etiqueta") or nombre).strip()[:80] or nombre}
        d["defecto"] = _limpiar_valor(tipo, c.get("defecto", _defecto_tipo(tipo)))
        if tipo == "seleccion":
            d["opciones"] = _opciones(opciones)
            if d["opciones"] and d["defecto"] not in [o["valor"] for o in d["opciones"]]:
                d["defecto"] = d["opciones"][0]["valor"]
        if c.get("ayuda"):
            d["ayuda"] = str(c["ayuda"])[:200]
        usados.add(nombre)
        salida.append(d)
        if len(salida) >= LIMITE_CAMPOS:
            break
    return salida


# ====================================================================== diseño visual
PIEZAS = {
    "titulo": "Título", "texto": "Texto", "cifra": "Cifra grande", "etiqueta": "Etiqueta",
    "imagen": "Imagen", "lista": "Lista", "icono": "Icono", "separador": "Separador",
    "espacio": "Espacio", "latex": "Código LaTeX", "columnas": "Columnas",
}
TIPO_CAMPO_PIEZA = {"titulo": "texto", "texto": "parrafo", "cifra": "texto", "etiqueta": "texto",
                    "imagen": "imagen", "lista": "lista", "icono": "seleccion"}
ICONOS = [  # (valor = número de \ding de pifont, nombre)
    ("51", "✓ Marca"), ("55", "✗ Cruz"), ("72", "★ Estrella"), ("228", "➔ Flecha"), ("108", "● Círculo"),
    ("110", "■ Cuadrado"), ("115", "▲ Triángulo"), ("117", "◆ Rombo"), ("37", "☎ Teléfono"),
    ("41", "✉ Sobre"), ("46", "✎ Lápiz"), ("40", "✈ Avión"), ("170", "♥ Corazón"), ("43", "☞ Mano"),
]
VINETAS = {
    "cuadrado": r"\rule[0.15em]{0.42em}{0.42em}", "punto": r"\textbullet", "guion": r"\textendash",
    "flecha": r"\ensuremath{\rightarrow}", "check": r"\ensuremath{\checkmark}", "numero": "",
}
ALINEACIONES = ("izquierda", "centro", "derecha", "justificado")
DEFECTOS_PIEZA = {
    "titulo": {"valor": "Título", "escala": 1.3, "color": "primario", "negrita": True, "cursiva": False},
    "texto": {"valor": "Texto de ejemplo. Una línea en blanco separa párrafos.", "escala": 1, "color": "",
              "negrita": False, "cursiva": False},
    "cifra": {"valor": "87 %", "escala": 3, "color": "acento", "negrita": True, "cursiva": False},
    "etiqueta": {"valor": "Nuevo", "escala": 0.85, "color": "contraste", "fondo": "acento"},
    "imagen": {"valor": "", "ancho": 100, "alto": 0, "redondeo": False, "circulo": False},
    "lista": {"valor": ["Primer punto", "Segundo punto"], "vineta": "cuadrado", "color": "acento"},
    "icono": {"valor": "51", "escala": 1.6, "color": "contraste", "fondo": "acento", "circulo": True},
    "separador": {"color": "acento", "grosor": "0.08em", "ancho": 100},
    "espacio": {"alto": "0.6em"},
    "latex": {"codigo": r"\textit{Código LaTeX}"},
    "columnas": {"separacion": "1em", "alinear": "arriba",
                 "columnas": [{"ancho": 50, "piezas": []}, {"ancho": 50, "piezas": []}]},
}
CAJA_DEFECTO = {"estilo": "ninguno", "fondo": "", "borde": "", "grosor": "", "radio": "", "relleno": "",
                "sombra": False}


def _pieza(p: dict, usados: set, anidada: bool = False) -> dict | None:
    if not isinstance(p, dict) or p.get("tipo") not in PIEZAS or (anidada and p.get("tipo") == "columnas"):
        return None
    tipo = p["tipo"]
    d = {"id": str(p.get("id") or "p-" + secrets.token_hex(3))[:20], "tipo": tipo}
    for k, v in DEFECTOS_PIEZA[tipo].items():
        d[k] = copy.deepcopy(p.get(k, v))
    if "alineacion" in p and p["alineacion"] in ALINEACIONES:
        d["alineacion"] = p["alineacion"]
    if tipo in TIPO_CAMPO_PIEZA:
        d["editable"] = True if tipo == "imagen" else bool(p.get("editable", True))
        nombre = str(p.get("campo") or "").strip()
        if not _NOMBRE.match(nombre) or nombre in RESERVADOS or nombre in usados:
            base = {"titulo": "titulo", "texto": "texto", "cifra": "cifra", "etiqueta": "etiqueta",
                    "imagen": "imagen", "lista": "items", "icono": "icono"}[tipo]
            nombre, n = base, 2
            while nombre in usados:
                nombre, n = f"{base}{n}", n + 1
        usados.add(nombre)
        d["campo"] = nombre
        d["etiqueta_campo"] = str(p.get("etiqueta_campo") or PIEZAS[tipo]).strip()[:80]
        d["valor"] = _limpiar_valor(TIPO_CAMPO_PIEZA[tipo], d.get("valor"))
    if tipo == "columnas":
        cols = []
        for c in (p.get("columnas") or [])[:3]:
            if isinstance(c, dict):
                cols.append({"ancho": _num(c.get("ancho"), 50, 5, 95),
                             "piezas": [x for x in (_pieza(q, usados, True) for q in (c.get("piezas") or [])) if x]})
        d["columnas"] = cols or copy.deepcopy(DEFECTOS_PIEZA["columnas"]["columnas"])
        d["alinear"] = "centro" if p.get("alinear") == "centro" else "arriba"
    return d


def _num(v, defecto, minimo=None, maximo=None):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return defecto
    if x != x:
        return defecto
    if minimo is not None:
        x = max(minimo, x)
    if maximo is not None:
        x = min(maximo, x)
    return int(x) if float(x).is_integer() else x


def normalizar_diseno(d) -> dict:
    d = d if isinstance(d, dict) else {}
    caja = dict(CAJA_DEFECTO)
    if isinstance(d.get("caja"), dict):
        for k in caja:
            if k in d["caja"]:
                caja[k] = d["caja"][k]
    if caja["estilo"] not in V.ESTILOS_CAJA and caja["estilo"] != "sin-caja":
        caja["estilo"] = "ninguno"
    caja["sombra"] = bool(caja["sombra"])
    usados: set = set()
    piezas = [x for x in (_pieza(p, usados) for p in (d.get("piezas") or [])[:40]) if x]
    return {"caja": caja, "alineacion": d.get("alineacion") if d.get("alineacion") in ALINEACIONES else "izquierda",
            "separacion": str(d.get("separacion") or "0.45em"), "piezas": piezas}


def _todas_las_piezas(piezas):
    for p in piezas:
        yield p
        if p["tipo"] == "columnas":
            for c in p["columnas"]:
                yield from c["piezas"]


def campos_de_diseno(diseno: dict) -> list[dict]:
    campos = []
    for p in _todas_las_piezas(diseno["piezas"]):
        if p.get("editable") and p.get("campo"):
            tipo = TIPO_CAMPO_PIEZA[p["tipo"]]
            c = {"nombre": p["campo"], "tipo": tipo, "etiqueta": p.get("etiqueta_campo") or PIEZAS[p["tipo"]],
                 "defecto": p.get("valor")}
            if tipo == "seleccion":
                c["opciones"] = [{"valor": v, "texto": t} for v, t in ICONOS]
            campos.append(c)
    return normalizar_campos(campos)


# ====================================================================== componentes
def normalizar(d, cid: str | None = None) -> dict:
    d = copy.deepcopy(d) if isinstance(d, dict) else {}
    ahora = time.time()
    c = {
        "id": cid or (d.get("id") if es_id(d.get("id")) else nuevo_id()),
        "nombre": (str(d.get("nombre") or "").strip() or "Componente sin nombre")[:80],
        "descripcion": str(d.get("descripcion") or "").strip()[:400],
        "modo": d.get("modo") if d.get("modo") in MODOS else "latex",
        "version": max(1, int(_num(d.get("version"), 1))),
        "creado": float(_num(d.get("creado"), ahora)),
        "modificado": float(_num(d.get("modificado"), ahora)),
        "origen": str(d.get("origen") or "")[:40],
    }
    if c["modo"] == "visual":
        c["diseno"] = normalizar_diseno(d.get("diseno"))
        c["campos"] = campos_de_diseno(c["diseno"])
    elif c["modo"] == "latex":
        c["codigo"] = str(d.get("codigo") or "")[:LIMITE_CODIGO]
        c["preambulo"] = str(d.get("preambulo") or "")[:LIMITE_CODIGO]
        c["campos"] = normalizar_campos(d.get("campos"))
    else:
        base = d.get("base") if d.get("base") in V.POR_CLAVE and d.get("base") not in NO_PREAJUSTE else "txtCifra"
        c["base"] = base
        campos_base = {x["nombre"]: x for x in V.POR_CLAVE[base]["campos"]}
        c["campos"] = normalizar_campos(d.get("campos"), campos_base)
        fijos = d.get("fijos") if isinstance(d.get("fijos"), dict) else {}
        c["fijos"] = {k: _limpiar_valor(campos_base[k]["tipo"], v) for k, v in fijos.items() if k in campos_base}
    return c


def resumen(c: dict) -> dict:
    return {k: c.get(k) for k in ("id", "nombre", "descripcion", "modo", "version", "modificado", "origen", "base")} | \
        {"campos": len(c.get("campos") or [])}


# ====================================================================== plantillas {{campo}}
@dataclass
class Valor:
    texto: str = ""
    items: list | None = None          # para {{#campo}}…{{/campo}} con listas
    verdad: bool = True
    partes: dict = field(default_factory=dict)   # {{0}}, {{1}} dentro de una lista de pares


_ETIQUETA = re.compile(r"\{\{\s*([#^/]?)\s*([A-Za-z_][A-Za-z0-9_]*|\.|[0-9])\s*\}\}")
_ORDEN_FINAL = re.compile(r"\\[A-Za-z@]+$")


def _buscar(nombre: str, pila: list[dict]):
    for ctx in reversed(pila):
        if nombre in ctx:
            return True, ctx[nombre]
    return False, None


def _cierre(t: str, desde: int, nombre: str):
    prof = 0
    for m in _ETIQUETA.finditer(t, desde):
        if m.group(2) != nombre:
            continue
        if m.group(1) in "#^" and m.group(1):
            prof += 1
        elif m.group(1) == "/":
            if prof == 0:
                return m
            prof -= 1
    return None


def renderizar(plantilla: str, pila: list[dict], conservar_lineas: bool = True) -> str:
    """Rellena una plantilla. Los nombres que no son campos se dejan tal cual (así
    no se toca el LaTeX que lleva llaves dobles). Una sección que no sale deja sus
    saltos de línea para que los números de línea de los errores sigan valiendo."""
    salida: list[str] = []
    cola = [""]                      # final de lo escrito (para no pegar una orden con letras)

    def poner(texto: str, frontera: bool):
        # \bfseries{{campo}} o \par{{^nota}}sin nota: en la frontera de un hueco se separa
        # con un espacio, o la orden y las letras se leerían como otra orden
        if frontera and texto[:1].isalpha() and _ORDEN_FINAL.search(cola[0]):
            texto = " " + texto
        if texto:
            salida.append(texto)
            cola[0] = (cola[0] + texto)[-48:]

    i, tras_hueco = 0, False
    while True:
        m = _ETIQUETA.search(plantilla, i)
        if not m:
            break
        tipo, nombre = m.group(1), m.group(2)
        conocido, valor = _buscar(nombre, pila)
        if not conocido or tipo == "/":
            poner(plantilla[i:m.end()], tras_hueco)
            tras_hueco = False
            i = m.end()
            continue
        poner(plantilla[i:m.start()], tras_hueco)
        if not tipo:
            poner(valor.texto, True)
            tras_hueco = True
            i = m.end()
            continue
        fin = _cierre(plantilla, m.end(), nombre)
        if fin is None:
            poner(m.group(0), False)
            tras_hueco = False
            i = m.end()
            continue
        dentro = plantilla[m.end():fin.start()]
        hecho = ""
        if tipo == "#":
            if valor.items is not None:
                hecho = "".join(renderizar(dentro, pila + [{".": it} | it.partes], conservar_lineas)
                                for it in valor.items)
            elif valor.verdad:
                hecho = renderizar(dentro, pila, conservar_lineas)
        elif not valor.verdad:
            hecho = renderizar(dentro, pila, conservar_lineas)
        if not hecho and conservar_lineas:
            hecho = "\n" * dentro.count("\n")
        poner(hecho, True)
        tras_hueco = True
        i = fin.end()
    poner(plantilla[i:], tras_hueco)
    return "".join(salida)


def _letras(t: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(t))


def valor_campo(campo: dict, valor, fmt_texto: str, eid: str, colores: list) -> Valor:
    """El valor de un campo convertido a LaTeX (como lo escribiría una variante)."""
    from . import generador as G
    tipo = campo["tipo"]
    if valor is None or (valor == "" and tipo not in ("texto", "parrafo", "latex", "imagen", "color")):
        valor = campo.get("defecto", _defecto_tipo(tipo))
    if tipo in ("texto", "parrafo"):
        t = T.convertir(valor, fmt_texto, parrafos=tipo == "parrafo")
        return Valor(t, verdad=bool(t.strip()))
    if tipo == "latex":
        t = str(valor or "")
        return Valor(t, verdad=bool(t.strip()))
    if tipo == "lista":
        items = T.lista(valor if isinstance(valor, (list, str)) else [], fmt_texto)
        return Valor(" ".join("\\item " + x for x in items), [Valor(x) for x in items], bool(items))
    if tipo in ("pares", "hitos"):
        pares = [p for p in (valor or []) if isinstance(p, (list, tuple)) and len(p) >= 2]
        items = []
        for p in pares:
            a, b = T.convertir(p[0], fmt_texto, False), T.convertir(p[1], fmt_texto, False)
            items.append(Valor(a + " " + b, partes={"0": Valor(a), "1": Valor(b)}))
        orden = G._arg(("defs" if tipo == "pares" else "hitos", "x"), {"x": pares}, fmt_texto)[1:-1]
        return Valor(orden, items, bool(items))
    if tipo == "flechas":
        t = G._arg(("flechas", "x"), {"x": valor}, fmt_texto)[1:-1]
        return Valor(t, verdad=bool(t.strip()))
    if tipo == "tabla":
        t = G._tabla(valor, fmt_texto)
        return Valor(t, verdad=bool(t.strip()))
    if tipo == "imagen":
        return Valor(G.ruta(valor), verdad=bool(str(valor or "").strip()))
    if tipo == "color":
        c = G.color(valor) or G.color(campo.get("defecto"))
        if not c:
            return Valor("", verdad=False)
        if re.fullmatch(r"[0-9A-F]{6}", c):
            nombre = "pck" + _letras(eid) + _letras(campo["nombre"])
            colores.append(f"\\definecolor{{{nombre}}}{{HTML}}{{{c}}}")
            c = nombre
        return Valor(c)
    if tipo in ("numero", "fraccion", "angulo"):
        x = G.numero(valor, G.numero(campo.get("defecto"), 0))
        return Valor(G.fmt(x), verdad=x != 0)
    if tipo == "porcentaje":
        x = G.numero(valor, G.numero(campo.get("defecto"), 100))
        return Valor(G.fmt(x / 100), verdad=x != 0)
    if tipo == "dimension":
        d = G.dim(valor, G.dim(campo.get("defecto"), "0pt"))
        return Valor(d, verdad=not re.match(r"^-?0+(\.0*)?[a-z]+$", d))
    if tipo == "seleccion":
        validos = [o["valor"] for o in campo.get("opciones") or []]
        v = str(valor) if str(valor) in validos else str(campo.get("defecto") or (validos[0] if validos else ""))
        return Valor(v, verdad=bool(v))
    if tipo == "booleano":
        b = valor is True or str(valor).lower() in ("true", "1", "si", "sí")
        return Valor("true" if b else "false", verdad=b)
    return Valor(T.escapar(str(valor or "")))


def contexto(c: dict, e: dict, fmt_texto: str, eid: str) -> tuple[dict, list]:
    colores: list = []
    ctx = {"id": Valor(_letras(eid) or "x")}
    for campo in c.get("campos") or []:
        ctx[campo["nombre"]] = valor_campo(campo, e.get(campo["nombre"]), fmt_texto, eid, colores)
    return ctx, colores


# ====================================================================== diseño → LaTeX
def _col(v, defecto=None):
    from . import generador as G
    return G.color(v, defecto)


def _alin(a: str) -> str:
    return {"izquierda": r"\raggedright", "centro": r"\centering", "derecha": r"\raggedleft"}.get(a, "")


def _contenido(p: dict, parrafos: bool = False) -> str:
    """{{campo}} si se edita en el póster; si no, el texto fijo ya en LaTeX."""
    if p.get("editable"):
        return "{{" + p["campo"] + "}}"
    return T.convertir(p.get("valor"), "simple", parrafos=parrafos)


def _dim_partes(d: str) -> tuple[float, str]:
    m = re.match(r"^\s*(-?\d*\.?\d+)\s*([a-z]+)\s*$", d or "")
    return (float(m.group(1)), m.group(2)) if m else (1.0, "em")


def _pieza_latex(p: dict, alin_comp: str, preambulo: set) -> list[str]:
    from . import generador as G
    tipo = p["tipo"]
    alin = _alin(p.get("alineacion") or alin_comp)
    esc = G.fmt(_num(p.get("escala"), 1, 0.2, 12))
    col = _col(p.get("color"))
    color = f"\\color{{{col}}}" if col else ""
    negrita = r"\bfseries" if p.get("negrita") else ""
    cursiva = r"\itshape" if p.get("cursiva") else ""
    if tipo == "titulo":
        return [f"% {PIEZAS[tipo]}", f"{{{alin}{color}\\tam{{{esc}}}{negrita}{cursiva}\\PC@fuentetit {_contenido(p)}\\par}}"]
    if tipo == "texto":
        if (p.get("alineacion") or alin_comp) == "justificado":
            alin = ""
        return [f"% {PIEZAS[tipo]}", f"{{{alin}{color}\\tam{{{esc}}}{negrita}{cursiva}{_contenido(p, True)}\\par}}"]
    if tipo == "cifra":
        return [f"% {PIEZAS[tipo]}", f"{{{alin}{color}\\tam{{{esc}}}{negrita}{cursiva}\\PC@fuentetit {_contenido(p)}\\par}}"]
    if tipo == "etiqueta":
        fondo = _col(p.get("fondo"), "pcAcento")
        texto = _col(p.get("color"), "pcContraste")
        return [f"% {PIEZAS[tipo]}",
                f"{{{alin}\\tikz[baseline=(pcetq.base)]\\node[fill={fondo},text={texto},rounded corners=0.25em,"
                f"inner xsep=0.55em,inner ysep=0.3em,font=\\bfseries\\tam{{{esc}}}] (pcetq) {{{_contenido(p)}}};\\par}}"]
    if tipo == "imagen":
        ancho = G.fmt(_num(p.get("ancho"), 100, 5, 100) / 100)
        ruta = _contenido(p)
        alin = _alin(p.get("alineacion") or "centro")
        if p.get("circulo"):
            return [f"% {PIEZAS[tipo]} (recorte circular)",
                    f"{{{alin}\\begingroup\\setlength{{\\PC@w}}{{{ancho}\\linewidth}}%",
                    f"\\sbox{{\\PC@box}}{{\\PCimg[width=10cm]{{{ruta}}}}}\\setlength{{\\PC@bw}}{{\\wd\\PC@box}}"
                    "\\setlength{\\PC@bh}{\\ht\\PC@box}%",
                    "\\pgfmathsetmacro{\\PC@s}{max(\\PC@w/\\PC@bw,\\PC@w/\\PC@bh)}%",
                    "\\begin{tikzpicture}\\path[use as bounding box] (-0.5\\PC@w,-0.5\\PC@w) rectangle (0.5\\PC@w,0.5\\PC@w);",
                    "\\begin{scope}\\clip (0,0) circle (0.5\\PC@w);\\node[inner sep=0pt] at (0,0) "
                    "{\\scalebox{\\PC@s}{\\usebox{\\PC@box}}};\\end{scope}\\end{tikzpicture}\\endgroup\\par}"]
        alto = _num(p.get("alto"), 0, 0, 300)
        if alto or p.get("redondeo"):
            alto = alto or 62
            h = G.fmt(_num(p.get("ancho"), 100, 5, 100) / 100 * alto / 100)
            redondeo = "[rounded corners=0.6em]" if p.get("redondeo") else ""
            return [f"% {PIEZAS[tipo]} (recortada)",
                    f"{{{alin}\\PCrecorte{redondeo}{{{ancho}\\linewidth}}{{{h}\\linewidth}}{{{ruta}}}\\par}}"]
        return [f"% {PIEZAS[tipo]}", f"{{{alin}\\PCimg[width={ancho}\\linewidth]{{{ruta}}}\\par}}"]
    if tipo == "lista":
        vineta = p.get("vineta") if p.get("vineta") in VINETAS else "cuadrado"
        colv = _col(p.get("color"), "pcAcento")
        if p.get("editable"):
            items = "{{#" + p["campo"] + "}}\\item {{.}} {{/" + p["campo"] + "}}{{^" + p["campo"] + "}}\\item[]\\relax{{/" + p["campo"] + "}}"
        else:
            lista = T.lista(p.get("valor"), "simple")
            items = " ".join("\\item " + x for x in lista) or "\\item[]\\relax"
        if vineta == "numero":
            return [f"% {PIEZAS[tipo]} numerada",
                    f"\\begin{{enumerate}}[label={{\\color{{{colv}}}\\bfseries\\arabic*.}},leftmargin=1.5em]{items}\\end{{enumerate}}"]
        return [f"% {PIEZAS[tipo]}",
                f"\\begin{{itemize}}[label={{\\color{{{colv}}}{VINETAS[vineta]}}},leftmargin=1.3em,labelsep=0.45em]{items}\\end{{itemize}}"]
    if tipo == "icono":
        preambulo.add(r"\RequirePackage{pifont}")
        simbolo = "{{" + p["campo"] + "}}" if p.get("editable") else (
            str(p.get("valor")) if str(p.get("valor")) in dict(ICONOS) else "51")
        texto = _col(p.get("color"), "pcContraste")
        if p.get("circulo"):
            fondo = _col(p.get("fondo"), "pcAcento")
            return [f"% {PIEZAS[tipo]}",
                    f"{{{alin}\\tikz[baseline=(pcico.base)]\\node[circle,fill={fondo},text={texto},inner sep=0.3em,"
                    f"font=\\tam{{{esc}}}] (pcico) {{\\ding{{{simbolo}}}}};\\par}}"]
        return [f"% {PIEZAS[tipo]}", f"{{{alin}\\color{{{texto}}}\\tam{{{esc}}}\\ding{{{simbolo}}}\\par}}"]
    if tipo == "separador":
        colsep = _col(p.get("color"), "pcAcento")
        grosor = G.dim(p.get("grosor"), "0.08em")
        ancho = G.fmt(_num(p.get("ancho"), 100, 5, 100) / 100)
        return [f"% {PIEZAS[tipo]}", f"{{{alin}\\color{{{colsep}}}\\rule{{{ancho}\\linewidth}}{{{grosor}}}\\par}}"]
    if tipo == "espacio":
        return [f"\\vspace{{{G.dim(p.get('alto'), '0.6em')}}}"]
    if tipo == "latex":
        return ["% Código LaTeX", str(p.get("codigo") or "")]
    if tipo == "columnas":
        cols = p.get("columnas") or []
        n = max(1, len(cols))
        total = sum(_num(c.get("ancho"), 50) for c in cols) or 100
        x, unidad = _dim_partes(G.dim(p.get("separacion"), "1em"))
        hueco = G.fmt(x * (n - 1) / n)
        pos = "c" if p.get("alinear") == "centro" else "t"
        lineas = [f"% {PIEZAS[tipo]}", "\\par\\noindent"]
        for k, c in enumerate(cols):
            frac = G.fmt(_num(c.get("ancho"), 50) / total)
            arriba = "\\vspace{0pt}" if pos == "t" else ""
            lineas.append(f"\\begin{{minipage}}[{pos}]{{\\dimexpr{frac}\\linewidth-{hueco}{unidad}\\relax}}{arriba}\\PC@parrafos")
            for q in c.get("piezas") or []:
                lineas += ["  " + x for x in _pieza_latex(q, alin_comp, preambulo)]
            lineas.append("\\end{minipage}" + ("\\hfill" if k < n - 1 else "\\par"))
        return lineas
    return []


def diseno_a_codigo(diseno: dict) -> tuple[str, str]:
    """El LaTeX de un diseño visual: (código con {{campos}}, preámbulo)."""
    from . import generador as G
    d = normalizar_diseno(diseno)
    preambulo: set = set()
    cuerpo: list[str] = []
    for p in d["piezas"]:
        cuerpo += _pieza_latex(p, d["alineacion"], preambulo)
    sep = G.dim(d.get("separacion"), "0.45em")
    caja = d["caja"]
    if caja["estilo"] == "sin-caja":
        lineas = ["\\PC@antesV\\begingroup\\setlength{\\parskip}{" + sep + "}%"] + cuerpo + ["\\endgroup\\PC@despues"]
    else:
        claves = [f"estilo={caja['estilo']}", "sin titulo", "antes=\\PC@sepelem", "despues=\\PC@sepelem"]
        for k, clave in (("fondo", "fondo"), ("borde", "borde")):
            c = _col(caja.get(k))
            if c:
                claves.append(f"{clave}={c}")
        for k, clave in (("grosor", "grosor borde"), ("radio", "radio"), ("relleno", "relleno")):
            v = G.dim(caja.get(k), "")
            if v:
                claves.append(f"{clave}={v}")
        if caja.get("sombra"):
            claves.append("sombra")
        lineas = ["\\begin{caja}[" + ", ".join(claves) + "]",
                  "\\setlength{\\parskip}{" + sep + "}%"] + cuerpo + ["\\end{caja}"]
    return "\n".join(lineas) + "\n", "\n".join(sorted(preambulo))


def codigo_de(c: dict) -> tuple[str, str]:
    if c.get("modo") == "visual":
        return diseno_a_codigo(c.get("diseno") or {})
    return str(c.get("codigo") or ""), str(c.get("preambulo") or "")


def a_codigo(c: dict) -> dict:
    """«Pasar a código»: el mismo componente en modo LaTeX."""
    c = normalizar(c, c.get("id"))
    if c["modo"] == "latex":
        return c
    if c["modo"] == "visual":
        codigo, pre = diseno_a_codigo(c["diseno"])
        campos = c["campos"]
    else:
        nuevo = desde_variante(c["base"], "latex")
        codigo, pre = nuevo["codigo"], nuevo["preambulo"]
        campos = []
        visibles = {x["nombre"]: x for x in c["campos"]}
        for x in nuevo["campos"]:
            if x["nombre"] in visibles:
                campos.append(visibles[x["nombre"]])
            else:                                   # los valores fijos pasan a escribirse en el código
                fijo = dict(x)
                fijo["defecto"] = c["fijos"].get(x["nombre"], x.get("defecto"))
                campos.append(fijo)
    salida = {k: v for k, v in c.items() if k not in ("diseno", "base", "fijos")}
    salida.update({"modo": "latex", "codigo": codigo, "preambulo": pre, "campos": normalizar_campos(campos)})
    return salida


# ====================================================================== recrear las incluidas
def _grupo(s: str, i: int) -> tuple[str, int]:
    if i >= len(s) or s[i] != "{":
        raise ValueError("se esperaba «{»")
    prof, j = 0, i
    while j < len(s):
        ch = s[j]
        if ch == "\\":
            j += 2
            continue
        if ch == "%":
            while j < len(s) and s[j] != "\n":
                j += 1
            continue
        if ch == "{":
            prof += 1
        elif ch == "}":
            prof -= 1
            if prof == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError("llaves sin cerrar")


def _opcional(s: str, i: int) -> tuple[str | None, int]:
    if i < len(s) and s[i] == "[":
        prof, j = 0, i
        while j < len(s):
            if s[j] == "{":
                prof += 1
            elif s[j] == "}":
                prof -= 1
            elif s[j] == "]" and prof == 0:
                return s[i + 1:j], j + 1
            j += 1
    return None, i


_STY_TEXTO: str | None = None


def definicion_en_sty(nombre: str) -> dict | None:
    """La definición de una orden de postercientifico.sty: cuerpo, número de argumentos
    y comentario que la describe."""
    global _STY_TEXTO
    if _STY_TEXTO is None:
        _STY_TEXTO = STY.read_text(encoding="utf-8")
    s = _STY_TEXTO
    m = re.search(r"\\(newcommand|NewDocumentCommand)\{?\\" + re.escape(nombre) + r"\}?(?![A-Za-z@])", s)
    if not m:
        return None
    i = m.end()
    if m.group(1) == "newcommand":
        n, i = _opcional(s, i)
        _, i = _opcional(s, i)
        cuerpo, _ = _grupo(s, i)
        n = int(n or 0)
    else:
        spec, i = _grupo(s, i)
        cuerpo, _ = _grupo(s, i)
        n = len(re.findall(r"\+?(?:O\{[^}]*\}|m|o)", spec))
    inicio_linea = s.rfind("\n", 0, m.start())
    previas = s[:inicio_linea].split("\n")[-3:]
    comentario = [x[2:].strip() for x in previas if x.startswith("%%")]
    return {"cuerpo": cuerpo, "n": n, "comentario": comentario[-1] if comentario else ""}


def _hueco_arg(espec, campos: dict) -> str:
    tipo = espec[0]
    campo = espec[1] if len(espec) > 1 else None
    if tipo == "opt_pct":
        return "{{" + campo + "}}\\linewidth"
    if tipo in ("opt_num", "opt_dim", "img", "txt", "par", "raw"):
        return "{{" + campo + "}}"
    if tipo == "items":
        return "{{#" + campo + "}}\\item {{.}} {{/" + campo + "}}{{^" + campo + "}}\\item\\relax{{/" + campo + "}}"
    if tipo == "defs":
        return "{{#" + campo + "}}\\item[{{{0}}}] {{1}} {{/" + campo + "}}{{^" + campo + "}}\\item[]\\relax{{/" + campo + "}}"
    if tipo == "hitos":
        return "{{#" + campo + "}}\\hito{{{0}}}{{{1}}} {{/" + campo + "}}"
    if tipo in ("flechas", "tabla"):
        return "{{" + campo + "}}"
    if tipo == "claves_caja":
        partes = []
        for c in espec[1]:
            if c == "estilo":
                partes.append("estilo={{estilo}}, ")
            elif c == "titulo":
                partes.append("{{#titulo}}titulo={{{titulo}}}, {{/titulo}}")
            elif c == "mostrar_titulo":
                partes.append("{{#titulo}}mostrar titulo={{mostrar_titulo}}, {{/titulo}}")
            elif c == "mostrar_titulo_forzado":
                partes.append("mostrar titulo={{mostrar_titulo}}, ")
            elif c in ("fondo", "borde"):
                partes.append("{{#" + c + "}}" + c + "={{" + c + "}}, {{/" + c + "}}")
        return "".join(partes)
    raise ValueError(tipo)


def desde_variante(clave: str, modo: str = "latex") -> dict:
    """Borrador para recrear un componente incluido: con código (su definición en el
    .sty con los argumentos cambiados por {{campos}}) o sin código (preajuste)."""
    v = V.POR_CLAVE.get(clave)
    if not v or clave in NO_PREAJUSTE:
        raise ValueError("Ese componente no se puede recrear")
    campos = copy.deepcopy(v["campos"])
    base = {"nombre": f"{v['nombre']} (propio)", "descripcion": f"Recreado a partir de {v['codigo']} · {v['nombre']}.",
            "origen": clave}
    if modo == "preajuste":
        return normalizar(base | {"modo": "preajuste", "base": clave, "campos": campos, "fijos": {}})
    d = definicion_en_sty(clave)
    if not d:
        raise ValueError("No se encontró su definición en postercientifico.sty")
    huecos = [_hueco_arg(a, {c["nombre"]: c for c in campos}) for a in v["args"]]
    cuerpo = d["cuerpo"]
    def hueco(mo):
        n = int(mo.group(2))
        if n > len(huecos):
            return mo.group(0)
        return (mo.group(1) + " " if mo.group(1) else "") + huecos[n - 1]
    cuerpo = re.sub(r"(\\[A-Za-z@]+)?#([1-9])", hueco, cuerpo).replace("##", "#")
    if v.get("despues"):
        cuerpo += "\n" + _hueco_arg(v["despues"], {})
    cabecera = [f"% Recreado a partir de {v['codigo']} · {v['nombre']} (postercientifico.sty).",
                "% Cada {{campo}} se cambia por lo que escribas en el inspector. Las órdenes",
                "% con @ (\\PC@antes, \\PC@despues…) son de la plantilla y se pueden usar aquí."]
    if d["comentario"]:
        cabecera.insert(1, "% Original: " + re.sub(r"\s{2,}", "   ", d["comentario"]))
    return normalizar(base | {"modo": "latex", "codigo": "\n".join(cabecera) + "\n" + cuerpo.strip() + "\n",
                              "preambulo": "", "campos": campos})


def catalogo_recrear() -> list[dict]:
    return [{"clave": v["clave"], "codigo": v["codigo"], "nombre": v["nombre"], "grupo": v["grupo"]}
            for v in V.VARIANTES if v["clave"] not in NO_PREAJUSTE]


# ====================================================================== LaTeX de una instancia
def llaves_equilibradas(t: str) -> str | None:
    """None si las llaves están bien; si no, un mensaje."""
    prof, i, linea = 0, 0, 1
    while i < len(t):
        ch = t[i]
        if ch == "\n":
            linea += 1
        elif ch == "\\":
            i += 2
            continue
        elif ch == "%":
            while i < len(t) and t[i] != "\n":
                i += 1
            continue
        elif ch == "{":
            prof += 1
        elif ch == "}":
            prof -= 1
            if prof < 0:
                return f"Sobra una llave «}}» en la línea {linea}"
        i += 1
    if prof > 0:
        return f"Falta cerrar {prof} {'llave' if prof == 1 else 'llaves'} «{{»"
    return None


PREAJUSTE = "preajuste"


def elemento_preajuste(c: dict, e: dict) -> dict:
    """El elemento de la variante base con los valores fijos y los del póster."""
    e2 = V.elemento_nuevo(c["base"], e.get("id") or "e-x")
    e2.update(copy.deepcopy(c.get("fijos") or {}))
    for campo in c.get("campos") or []:
        n = campo["nombre"]
        e2[n] = copy.deepcopy(e[n]) if e.get(n) is not None else copy.deepcopy(campo.get("defecto"))
    return e2


def cuerpo_instancia(c: dict, e: dict, fmt_texto: str, eid: str) -> str:
    """El LaTeX de un componente (modo visual o latex) con los valores de un elemento."""
    codigo, _ = codigo_de(c)
    ctx, colores = contexto(c, e, fmt_texto, eid)
    cuerpo = renderizar(codigo, [ctx])
    return "".join(colores) + cuerpo


# ====================================================================== biblioteca
class Biblioteca:
    """Componentes del usuario en datos/componentes (un JSON por componente)."""

    def __init__(self, raiz: Path):
        self.raiz = Path(raiz)
        self.raiz.mkdir(parents=True, exist_ok=True)

    def _ruta(self, cid: str) -> Path:
        if not es_id(cid):
            raise ValueError("Componente no válido")
        return self.raiz / f"{cid}.json"

    def listar(self) -> list[dict]:
        salida = []
        for p in self.raiz.glob("k-*.json"):
            try:
                c = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            r = resumen(c)
            r["tiene_miniatura"] = (self.raiz / f"{c.get('id')}.png").exists()
            salida.append(r)
        return sorted(salida, key=lambda r: -(r.get("modificado") or 0))

    def todos(self) -> list[dict]:
        salida = []
        for p in self.raiz.glob("k-*.json"):
            try:
                salida.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return salida

    def leer(self, cid: str) -> dict:
        p = self._ruta(cid)
        if not p.exists():
            raise ValueError("El componente no existe")
        return json.loads(p.read_text(encoding="utf-8"))

    def _escribir(self, c: dict):
        p = self._ruta(c["id"])
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, p)

    def crear(self, datos: dict, conservar_id: bool = False) -> dict:
        """Componente nuevo. Con conservar_id (copiar al Lab uno que solo estaba en un
        póster) se mantiene su id y su versión, si el id no está ocupado."""
        propio = datos.get("id") if conservar_id and es_id(datos.get("id")) else None
        if propio and self._ruta(propio).exists():
            propio = None
        c = normalizar(datos, propio or nuevo_id())
        if not propio:
            c["version"] = 1
            c["creado"] = c["modificado"] = time.time()
        self._escribir(c)
        return c

    def guardar(self, cid: str, datos: dict) -> dict:
        viejo = self.leer(cid)
        c = normalizar(datos, cid)
        c["creado"] = viejo.get("creado", c["creado"])
        cambio = {k: v for k, v in c.items() if k not in ("version", "modificado", "creado")} != \
            {k: v for k, v in normalizar(viejo, cid).items() if k not in ("version", "modificado", "creado")}
        c["version"] = int(viejo.get("version") or 1) + (1 if cambio else 0)
        c["modificado"] = time.time() if cambio else viejo.get("modificado", time.time())
        self._escribir(c)
        if cambio:
            (self.raiz / f"{cid}.png").unlink(missing_ok=True)
        return c

    def borrar(self, cid: str):
        self._ruta(cid).unlink(missing_ok=True)
        (self.raiz / f"{cid}.png").unlink(missing_ok=True)

    def duplicar(self, cid: str) -> dict:
        c = self.leer(cid)
        c["nombre"] = (c.get("nombre") or "Componente") + " (copia)"
        c.pop("id", None)
        return self.crear(c)

    def importar(self, texto: str) -> list[dict]:
        try:
            datos = json.loads(texto)
        except ValueError:
            raise ValueError("El archivo no es un componente de DocsLab (JSON)")
        if isinstance(datos, dict) and isinstance(datos.get("componentes"), list):
            datos = datos["componentes"]
        if isinstance(datos, dict):
            datos = [datos]
        if not isinstance(datos, list) or not datos:
            raise ValueError("No hay componentes en el archivo")
        nuevos = []
        for d in datos[:200]:
            if isinstance(d, dict) and (d.get("modo") in MODOS or d.get("codigo") or d.get("diseno")):
                d = dict(d)
                d.pop("id", None)
                nuevos.append(self.crear(d))
        if not nuevos:
            raise ValueError("No hay componentes en el archivo")
        return nuevos

    def exportar(self, cids: list[str] | None = None) -> str:
        lista = [self.leer(c) for c in cids] if cids else self.todos()
        return json.dumps({"docslab": "componentes", "version": 1, "componentes": lista}, ensure_ascii=False,
                          indent=1)


def huella(*partes) -> str:
    h = hashlib.sha256()
    for p in partes:
        h.update(json.dumps(p, sort_keys=True, ensure_ascii=False).encode())
    return h.hexdigest()[:20]


# ====================================================================== vista previa en el Lab
ANCHOS_VISTA = {"estrecha": 4, "media": 3, "ancha": 2}


def modelo_vista(c: dict, tema: str = "pizarra", ancho: str = "media", en_caja: bool = False,
                 valores: dict | None = None) -> dict:
    """Un póster A0 sin cabecera ni pie con el componente en la primera columna."""
    from ..nucleo import modelo as M
    m = M.normalizar({})
    m["lienzo"].update({"tamano": "A0", "orientacion": "vertical", "ancho": "841mm", "alto": "1189mm"})
    tema = tema if tema in M.TEMAS else "pizarra"
    m["colores"].update({"tema": tema, **M.TEMAS[tema]})
    m["tipografia"]["fuente"] = 30
    m["idioma"] = "es"
    m["cabecera"]["visible"] = False
    m["pie"]["visible"] = False
    m["capas"] = []
    e = {"id": "e-vista", "tipo": "cmp:" + c["id"], "visible": True}
    for campo in c.get("campos") or []:
        n = campo["nombre"]
        e[n] = copy.deepcopy((valores or {}).get(n, campo.get("defecto")))
    b = {"id": "b-vista", "visible": True, "titulo": "Sección" if en_caja else "", "mostrar_titulo": bool(en_caja),
         "estilo": "" if en_caja else "ninguno", "numero": "", "estirar": False, "opciones": {}, "elementos": [e]}
    m["filas"] = [{"id": "f-vista", "visible": True, "alto": "auto", "rejilla": ANCHOS_VISTA.get(ancho, 3),
                   "separacion": "", "despues": "", "igualar": False,
                   "columnas": [{"id": "c-vista", "abarca": 1, "distribucion": "arriba", "bloques": [b]}]}]
    m["componentes"] = {c["id"]: c}
    return M.normalizar(m)


def compilar_vista(datos: dict, raiz: Path, tema: str = "pizarra", ancho: str = "media", en_caja: bool = False,
                   valores: dict | None = None, tiempo: int = 45) -> dict:
    """Compila el componente solo y devuelve dónde está en la página (para recortarlo)."""
    from ..salidas import compilador
    from . import generador as G
    # el id, el nombre y las fechas no cambian el dibujo: la vista se guarda por lo demás
    c = normalizar(datos, "k-vista0")
    dibujo = {k: c.get(k) for k in ("modo", "campos", "codigo", "preambulo", "diseno", "base", "fijos")}
    sty = STY.read_bytes() if STY.exists() else b""
    h = huella(dibujo, tema, ancho, bool(en_caja), valores or {}, hashlib.md5(sty).hexdigest())
    base = Path(raiz) / ".vistas"
    d = base / h
    resultado = d / "resultado.json"
    if resultado.exists():
        try:
            return json.loads(resultado.read_text(encoding="utf-8"))
        except ValueError:
            pass
    d.mkdir(parents=True, exist_ok=True)
    archivos: dict[str, str] = {}
    m = modelo_vista(c, tema, ancho, en_caja, valores)
    tex, _ = G.generar(m, marcas=True, archivos=archivos)
    (d / "vista.tex").write_text(tex, encoding="utf-8")
    for nombre, texto in archivos.items():
        (d / nombre).write_text(texto, encoding="utf-8")
    res = compilador.compilar(d, "vista.tex", max_pasadas=1, tiempo=tiempo, avisar_paginas=False,
                              hacer_miniatura=False, formato=compilador.formato_poster())
    pos = res.get("posiciones") or {}
    caja = (pos.get("cajas") or {}).get("b-vista") or (pos.get("cajas") or {}).get("e-vista")
    cuerpo, pre = f"cmp-e-vista.tex", f"cmp-pre-{c['id']}.tex"
    errores = []
    for e in res.get("errores") or []:
        archivo = str(e.get("archivo") or "").replace("./", "").split("/")[-1]
        donde = "codigo" if archivo == cuerpo else "preambulo" if archivo == pre else ""
        errores.append({"mensaje": e.get("mensaje"), "linea": e.get("linea") if donde else None, "donde": donde,
                        "contexto": e.get("contexto", "")})
    salida = {"ok": bool(res.get("ok")) and bool(caja), "huella": h, "caja": caja, "papel": pos.get("papel"),
              "errores": errores, "segundos": res.get("segundos"),
              "avisos": [a for a in res.get("avisos") or [] if a.get("tipo") != "paginas"][:12]}
    if res.get("ok") and not caja:
        salida["errores"].append({"mensaje": "El componente no dibujó nada.", "linea": None, "donde": ""})
    resultado.write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")
    _limpiar_vistas(base)
    return salida


def pdf_vista(raiz: Path, h: str) -> Path | None:
    if not re.fullmatch(r"[0-9a-f]{20}", h or ""):
        return None
    p = Path(raiz) / ".vistas" / h / "build" / "vista.pdf"
    return p if p.exists() else None


def _limpiar_vistas(base: Path, conservar: int = 60):
    try:
        dirs = sorted((x for x in base.iterdir() if x.is_dir()), key=lambda x: x.stat().st_mtime, reverse=True)
    except OSError:
        return
    import shutil
    for x in dirs[conservar:]:
        shutil.rmtree(x, ignore_errors=True)


def miniatura_desde_vista(raiz: Path, h: str, destino: Path) -> bool:
    from ..salidas import compilador
    pdf = pdf_vista(raiz, h)
    if not pdf:
        return False
    try:
        r = json.loads((pdf.parent.parent / "resultado.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not r.get("ok"):
        return False
    caja = dict(r["caja"])
    margen = 6
    caja.update({"x0": max(0, caja["x0"] - margen), "y0": max(0, caja["y0"] - margen),
                 "x1": caja["x1"] + margen, "y1": caja["y1"] + margen})
    return compilador.recorte_png(pdf, destino, caja, r.get("papel"), 360)
