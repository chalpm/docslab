# SPDX-License-Identifier: AGPL-3.0-only
"""Animaciones de entrada y transiciones para el PowerPoint exportado.

En el modelo (todas las clases de documento):

* un elemento, una caja (bloque) o un elemento de una capa puede llevar
  ``"animacion": {"efecto", "inicio", "duracion", "retraso"}``;
* una diapositiva de una presentación puede llevar ``"transicion": {"efecto", "velocidad"}``;
  en las demás clases, ``modelo["transicion"]`` vale para todas las páginas.

Aquí solo se normalizan esos valores y se escribe el XML de PresentationML
(``<p:timing>`` y ``<p:transition>``), que python-pptx no sabe hacer.
"""
from __future__ import annotations

from xml.sax.saxutils import quoteattr

# efecto → (presetID, presetSubtype) de PowerPoint (el que muestra su panel de animación)
EFECTOS = {
    "aparecer": (1, 0),
    "desvanecer": (10, 0),
    "subir": (2, 4),          # «Desplazar hacia dentro» desde abajo
    "barrido": (22, 8),       # «Barrido» desde la izquierda
    "aumentar": (53, 16),     # «Zoom» (aumentar y desvanecer)
}
INICIOS = ("clic", "con", "despues")          # al hacer clic · con la anterior · después de la anterior
TRANSICIONES = ("desvanecer", "empujar", "barrido", "cubrir", "dividir")
VELOCIDADES = {"rapida": "fast", "media": "med", "lenta": "slow"}
NOMBRES_EFECTO = {"": "Ninguna", "aparecer": "Aparecer", "desvanecer": "Desvanecer", "subir": "Subir desde abajo",
                  "barrido": "Barrido", "aumentar": "Aumentar"}
NOMBRES_TRANSICION = {"": "Ninguna", "desvanecer": "Desvanecer", "empujar": "Empujar", "barrido": "Barrido",
                      "cubrir": "Cubrir", "dividir": "Dividir"}


def _num(v, defecto: float, minimo: float, maximo: float) -> float:
    try:
        return max(minimo, min(maximo, float(v)))
    except (TypeError, ValueError):
        return defecto


def normalizar_animacion(a) -> dict | None:
    """{"efecto", "inicio", "duracion" (s), "retraso" (s)} válido, o None si no hay animación."""
    if not isinstance(a, dict) or a.get("efecto") not in EFECTOS:
        return None
    return {"efecto": a["efecto"], "inicio": a.get("inicio") if a.get("inicio") in INICIOS else "clic",
            "duracion": _num(a.get("duracion"), 0.5, 0.1, 10.0), "retraso": _num(a.get("retraso"), 0.0, 0.0, 30.0)}


def normalizar_transicion(t) -> dict | None:
    if not isinstance(t, dict) or t.get("efecto") not in TRANSICIONES:
        return None
    return {"efecto": t["efecto"], "velocidad": t.get("velocidad") if t.get("velocidad") in VELOCIDADES else "media"}


# ------------------------------------------------------------------------- transición
def xml_transicion(t: dict | None) -> str:
    t = normalizar_transicion(t)
    if not t:
        return ""
    cuerpo = {"desvanecer": "<p:fade/>", "empujar": '<p:push dir="u"/>', "barrido": '<p:wipe dir="r"/>',
              "cubrir": '<p:cover dir="l"/>', "dividir": '<p:split orient="vert" dir="out"/>'}[t["efecto"]]
    return f'<p:transition spd="{VELOCIDADES[t["velocidad"]]}">{cuerpo}</p:transition>'


# ------------------------------------------------------------------------- animaciones
class _Ids:
    def __init__(self):
        self.n = 0

    def __call__(self) -> int:
        self.n += 1
        return self.n


def _tgt(spid: int) -> str:
    return f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'


def _visible(ids, spid: int, retraso_ms: int = 0) -> str:
    return (f'<p:set><p:cBhvr><p:cTn id="{ids()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="{retraso_ms}"/>'
            f'</p:stCondLst></p:cTn>{_tgt(spid)}<p:attrNameLst><p:attrName>style.visibility</p:attrName>'
            f'</p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>')


def _filtro(ids, spid: int, filtro: str, dur: int) -> str:
    return (f'<p:animEffect transition="in" filter={quoteattr(filtro)}><p:cBhvr><p:cTn id="{ids()}" dur="{dur}"/>'
            f'{_tgt(spid)}</p:cBhvr></p:animEffect>')


def _anim(ids, spid: int, atributo: str, desde: str, hasta: str, dur: int) -> str:
    return (f'<p:anim calcmode="lin" valueType="num"><p:cBhvr additive="base"><p:cTn id="{ids()}" dur="{dur}" '
            f'fill="hold"/>{_tgt(spid)}<p:attrNameLst><p:attrName>{atributo}</p:attrName></p:attrNameLst></p:cBhvr>'
            f'<p:tavLst><p:tav tm="0"><p:val><p:strVal val={quoteattr(desde)}/></p:val></p:tav>'
            f'<p:tav tm="100000"><p:val><p:strVal val={quoteattr(hasta)}/></p:val></p:tav></p:tavLst></p:anim>')


def _comportamiento(ids, spid: int, efecto: str, dur: int) -> str:
    if efecto == "aparecer":
        return _visible(ids, spid)
    if efecto == "desvanecer":
        return _visible(ids, spid) + _filtro(ids, spid, "fade", dur)
    if efecto == "barrido":
        return _visible(ids, spid) + _filtro(ids, spid, "wipe(left)", dur)
    if efecto == "subir":
        return (_visible(ids, spid) + _anim(ids, spid, "ppt_x", "#ppt_x", "#ppt_x", dur)
                + _anim(ids, spid, "ppt_y", "1+#ppt_h/2", "#ppt_y", dur))
    if efecto == "aumentar":
        return (_visible(ids, spid) + _anim(ids, spid, "ppt_w", "0", "#ppt_w", dur)
                + _anim(ids, spid, "ppt_h", "0", "#ppt_h", dur) + _filtro(ids, spid, "fade", dur))
    raise ValueError(efecto)


def xml_animaciones(pasos: list[tuple[int, dict]]) -> str:
    """``<p:timing>`` para una diapositiva. ``pasos``: [(id de la forma, animación normalizada)] en orden.

    Como en PowerPoint: «clic» abre un grupo nuevo que espera un clic; «con» arranca a la vez que
    la anterior; «después» arranca cuando termina la anterior. Si la primera no es «clic», el primer
    grupo empieza solo al mostrarse la diapositiva."""
    pasos = [(spid, a) for spid, a in pasos if a]
    if not pasos:
        return ""
    ids = _Ids()
    ids(), ids()                                  # 1: raíz, 2: secuencia principal
    grupos: list[list[list[tuple[int, dict]]]] = []   # grupo de clic → tandas (se encadenan) → efectos a la vez
    for spid, a in pasos:
        if a["inicio"] == "clic" or not grupos:
            grupos.append([[(spid, a)]])
        elif a["inicio"] == "con":
            grupos[-1][-1].append((spid, a))
        else:
            grupos[-1].append([(spid, a)])
    xml_grupos = []
    for g, tandas in enumerate(grupos):
        id_grupo = ids()
        automatico = g == 0 and pasos[0][1]["inicio"] != "clic"
        cond = ('<p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond>'
                if automatico else '<p:cond delay="indefinite"/>')
        inicio_tanda, xml_tandas = 0, []
        for t, tanda in enumerate(tandas):
            id_tanda = ids()
            efectos, fin = [], 0
            for e, (spid, a) in enumerate(tanda):
                dur = int(a["duracion"] * 1000) if a["efecto"] != "aparecer" else 1
                retraso = int(a["retraso"] * 1000)
                fin = max(fin, retraso + dur)
                preset, sub = EFECTOS[a["efecto"]]
                if t == 0 and e == 0:
                    tipo = "afterEffect" if automatico and a["inicio"] == "despues" else (
                        "withEffect" if automatico else "clickEffect")
                else:
                    tipo = "withEffect" if e else "afterEffect"
                id_efecto = ids()
                efectos.append(
                    f'<p:par><p:cTn id="{id_efecto}" presetID="{preset}" presetClass="entr" presetSubtype="{sub}" '
                    f'fill="hold" nodeType="{tipo}"><p:stCondLst><p:cond delay="{retraso}"/></p:stCondLst>'
                    f'<p:childTnLst>{_comportamiento(ids, spid, a["efecto"], dur)}</p:childTnLst></p:cTn></p:par>')
            xml_tandas.append(f'<p:par><p:cTn id="{id_tanda}" fill="hold"><p:stCondLst><p:cond delay="{inicio_tanda}"/>'
                              f'</p:stCondLst><p:childTnLst>{"".join(efectos)}</p:childTnLst></p:cTn></p:par>')
            inicio_tanda += fin
        xml_grupos.append(f'<p:par><p:cTn id="{id_grupo}" fill="hold"><p:stCondLst>{cond}</p:stCondLst>'
                          f'<p:childTnLst>{"".join(xml_tandas)}</p:childTnLst></p:cTn></p:par>')
    return ('<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
            '<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
            + "".join(xml_grupos) +
            '</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl>'
            '</p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl>'
            '</p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>')


def poner_en_diapositiva(diapo, transicion: str, timing: str) -> None:
    """Mete <p:transition> y <p:timing> en el XML de la diapositiva, en el orden del esquema."""
    if not transicion and not timing:
        return
    from lxml import etree
    from pptx.oxml.ns import nsdecls, qn
    sld = diapo._element
    for viejo in sld.findall(qn("p:transition")) + sld.findall(qn("p:timing")):
        sld.remove(viejo)
    despues = sld.find(qn("p:clrMapOvr"))
    if despues is None:
        despues = sld.find(qn("p:cSld"))
    pos = list(sld).index(despues) + 1
    for xml in (transicion, timing):
        if xml:
            el = etree.fromstring(xml.replace(">", f" {nsdecls('p')}>", 1))   # declara p: en la raíz
            sld.insert(pos, el)
            pos += 1


def nodos_animados(modelo: dict) -> list[tuple[str, dict, int]]:
    """(id, animación, profundidad) en el orden del documento. Profundidad: 0 caja/elemento de capa, 1 elemento."""
    out = []
    for fila in modelo.get("filas") or []:
        if fila.get("visible") is False:
            continue
        for col in fila.get("columnas") or []:
            for b in col.get("bloques") or []:
                if b.get("visible") is False:
                    continue
                a = normalizar_animacion(b.get("animacion"))
                if a:
                    out.append((b["id"], a, 0))
                for e in b.get("elementos") or []:
                    if e.get("visible") is False:
                        continue
                    a = normalizar_animacion(e.get("animacion"))
                    if a:
                        out.append((e["id"], a, 1))
    for capa in modelo.get("capas") or []:
        if capa.get("visible") is False:
            continue
        for it in capa.get("elementos") or []:
            if it.get("visible") is False:
                continue
            a = normalizar_animacion(it.get("animacion"))
            if a:
                out.append((it["id"], a, 0))
    return out


def transicion_de_pagina(modelo: dict | None, n_pagina: int, posiciones: dict | None) -> dict | None:
    """La transición de la página n (1, 2…): la de su diapositiva o, si no es una presentación, la del documento."""
    if not modelo:
        return None
    if modelo.get("clase") == "presentacion":
        pags = (posiciones or {}).get("paginas") or {}
        ids = sorted(pags, key=lambda i: pags[i])
        actual = None
        for i in ids:                             # la diapositiva que empieza en esta página o antes
            if pags[i] <= n_pagina:
                actual = i
        pg = next((p for p in modelo.get("paginas") or [] if p.get("id") == actual), None)
        return normalizar_transicion((pg or {}).get("transicion"))
    return normalizar_transicion(modelo.get("transicion"))
