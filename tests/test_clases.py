"""Clases de documento de DocsLab: presentación, documento, artículo y tesis; cajas sueltas."""
import copy

import pytest

from conftest import hay_latex
from docslab import compilador, generador as G, modelo as M

CLASES = ["poster", "presentacion", "documento", "paper", "tesis"]


def _compilar(m, tmp_path):
    from docslab import almacen as A
    alm = A.Almacen(tmp_path)
    meta = alm.crear_proyecto("p", None, None)
    alm.guardar_modelo(meta["id"], m)
    alm.escribir_tex(meta["id"], marcas=True)
    diapos = [(pg["id"], pg.get("nombre", "")) for pg in m.get("paginas", []) if pg.get("visible", True)]
    return compilador.compilar(alm.dir_proyecto(meta["id"]), "poster.tex", avisar_paginas=m["clase"] == "poster",
                               diapositivas=diapos if m["clase"] == "presentacion" else None)


def _bloques(m):
    return [b for f in m["filas"] for c in f["columnas"] for b in c["bloques"]]


@pytest.mark.parametrize("clase", CLASES)
def test_el_asistente_crea_cada_clase(clase):
    m = M.desde_asistente({"clase": clase})
    assert m["clase"] == clase
    assert M.es_flujo(m) == (clase in ("documento", "paper", "tesis"))
    assert M.normalizar(copy.deepcopy(m)) == m, "normalizar debe dejar igual un modelo ya normalizado"
    tex, _ = G.generar(m)
    modo = {"poster": None, "presentacion": "modo=presentacion"}.get(clase, "modo=documento")
    assert (modo in tex) if modo else ("modo=" not in tex)


def test_un_poster_antiguo_sigue_siendo_poster():
    m = M.desde_asistente({"tamano": "A1"})
    for k in ("clase", "paginas", "documento", "presentacion"):
        m.pop(k)
    m = M.normalizar(m)
    assert m["clase"] == "poster" and m["paginas"] == [] and not M.es_flujo(m)


def test_cada_fila_pertenece_a_una_diapositiva():
    m = M.desde_asistente({"clase": "presentacion"})
    ids = [pg["id"] for pg in m["paginas"]]
    assert len(ids) == 5 and all(f["pag"] in ids for f in m["filas"])
    m["filas"][0]["pag"] = "no-existe"
    m["paginas"].reverse()
    m = M.normalizar(m)
    orden = [[pg["id"] for pg in m["paginas"]].index(f["pag"]) for f in m["filas"]]
    assert orden == sorted(orden), "las filas van en el orden de sus diapositivas"
    tex, _ = G.generar(m)
    assert tex.count("\\diapositiva[") == 5
    m["paginas"][1]["visible"] = False
    assert G.generar(m)[0].count("\\diapositiva[") == 4


def test_una_caja_suelta_sale_de_la_cuadricula():
    m = M.desde_asistente({"tamano": "A1", "columnas": 2})
    b = _bloques(m)[0]
    b.update({"libre": True, "x": 0.25, "y": 0.4, "ancho": 0.3})
    m = M.normalizar(m)
    tex, _ = G.generar(m)
    assert "\\nuevacapa[z=5]{libre}" in tex
    assert "\\colocar[capa=libre" in tex and "x=0.25" in tex and "y=0.4" in tex and "ancho=0.3" in tex
    # en un documento el texto corre: no hay cajas sueltas
    d = M.desde_asistente({"clase": "documento"})
    _bloques(d)[0].update({"libre": True, "x": 0.2, "y": 0.2, "ancho": 0.3})
    assert "capa=libre" not in G.generar(M.normalizar(d))[0]


def test_secciones_de_una_tesis():
    m = M.desde_asistente({"clase": "tesis"})
    tex, _ = G.generar(m)
    assert "\\PCportada[" in tex and "\\PCindice" in tex
    assert "\\PCseccion[nivel=0" in tex and "\\PCseccion[nivel=1" in tex and "apendice" in tex
    paper = G.generar(M.desde_asistente({"clase": "paper", "columnas": 2}))[0]
    assert "\\PCdoscolumnas{" in paper and "\\PCresumen" in paper and "columnas texto=2" in paper


@hay_latex
@pytest.mark.parametrize("clase", ["presentacion", "documento", "paper", "tesis"])
def test_cada_clase_compila(clase, tmp_path):
    m = M.desde_asistente({"clase": clase, "columnas": 2})
    res = _compilar(m, tmp_path)
    assert res["ok"], res.get("errores")
    assert res["posiciones"]["cajas"], "faltan las marcas de posición"
    if clase == "presentacion":
        assert res["paginas"] == 5 and len(res["posiciones"]["paginas"]) == 5
        assert res["diapositivas_largas"] == []
    if clase == "tesis":
        assert res["paginas"] >= 8


@hay_latex
def test_la_caja_suelta_queda_donde_se_pone(tmp_path):
    m = M.desde_asistente({"clase": "presentacion"})
    pg = m["paginas"][1]
    b = next(b for f in m["filas"] if f["pag"] == pg["id"] for c in f["columnas"] for b in c["bloques"])
    b.update({"libre": True, "x": 0.5, "y": 0.5, "ancho": 0.25})
    res = _compilar(M.normalizar(m), tmp_path)
    assert res["ok"], res.get("errores")
    pos = res["posiciones"]
    caja, papel = pos["cajas"][b["id"]], pos["papel"]
    assert caja["pagina"] == pos["paginas"][pg["id"]], "solo se pinta en su diapositiva"
    assert abs(caja["x0"] / papel["ancho"] - 0.5) < 0.01 and abs(caja["y0"] / papel["alto"] - 0.5) < 0.01
    assert abs((caja["x1"] - caja["x0"]) / papel["ancho"] - 0.25) < 0.01


@hay_latex
def test_se_avisa_de_la_diapositiva_que_no_cabe(tmp_path):
    m = M.desde_asistente({"clase": "presentacion"})
    pg = m["paginas"][1]
    b = next(b for f in m["filas"] if f["pag"] == pg["id"] for c in f["columnas"] for b in c["bloques"])
    b["elementos"][0]["items"] = [f"Idea número {i}" for i in range(40)]
    res = _compilar(M.normalizar(m), tmp_path)
    assert res["ok"] and res["diapositivas_largas"] == [pg["id"]]


def test_api_crea_y_lista_por_clase(cliente):
    for clase in CLASES:
        r = cliente.post("/api/proyectos", json={"nombre": clase, "asistente": {"clase": clase}})
        assert r.status_code == 200 and r.get_json()["clase"] == clase
    assert sorted(p["clase"] for p in cliente.get("/api/proyectos").get_json()) == sorted(CLASES)
    cat = cliente.get("/api/variantes").get_json()
    assert set(cat["clases"]) == set(CLASES) and "x" in cat["libre_defecto"]
