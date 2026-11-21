# SPDX-License-Identifier: AGPL-3.0-only
"""Exportar a PowerPoint: texto editable sobre el póster sin texto, o una imagen."""
import io
import time

import pytest

from conftest import hay_latex
from docslab.salidas import powerpoint as P

hay_pptx = pytest.mark.skipif(not P.disponible()["pptx"], reason="sin python-pptx")
hay_todo = pytest.mark.skipif(not P.disponible()["editable"], reason="sin python-pptx, Ghostscript o Poppler")
EMU_CM = 360000


def esperar(c, tid, limite=300):
    t0 = time.time()
    while time.time() - t0 < limite:
        t = c.get(f"/api/trabajos/{tid}").get_json()
        if t["estado"] in ("terminado", "error", "cancelado"):
            return t
        time.sleep(0.2)
    raise AssertionError("el trabajo no terminó")


def textos(prs):
    return [sh.text_frame.text for d in prs.slides for sh in d.shapes if sh.has_text_frame and sh.text_frame.text]


# ---------------------------------------------------------------------- piezas sueltas
def test_tipografias_para_powerpoint():
    assert P.familia_ppt("UIRCHT+NimbusSanL-Bold") == "Arial"
    assert P.familia_ppt("NimbusRomNo9L-Regu") == "Times New Roman"
    assert P.familia_ppt("URWPalladioL-Roma") == "Palatino Linotype"
    assert P.familia_ppt("GJOKRJ+DejaVuSans") == "DejaVu Sans"
    assert P.familia_ppt("SourceSansPro-Regular") == "Source Sans Pro"


def linea(texto, x0, x1, y0=100, tam=20, **kw):
    d = {"x0": x0, "x1": x1, "y0": y0, "y1": y0 + tam, "tam": tam, "familia": "NimbusSanL-Regu",
         "color": (0, 0, 0), "trozos": [(texto, False, False)], "ancho_cero": False}
    d.update(kw)
    return d


def test_partir_donde_hay_un_hueco_grande():
    # «4 Capa propia»: pdftohtml lo da junto, pero entre el número y el título hay casi una letra
    ln = linea("4 Capa propia", 10, 120)
    palabras = [(10, 100, 20, 120, "4"), (38, 100, 70, 120, "Capa"), (75, 100, 120, 120, "propia")]
    partes = P.partir_lineas([ln], palabras)
    assert [P._texto(x) for x in partes] == ["4", "Capa propia"]
    assert partes[1]["x0"] == 38
    # si las palabras no coinciden con el texto, no se toca
    assert P.partir_lineas([ln], palabras[:2]) == [ln]


def test_unir_trozos_de_una_misma_linea():
    a = linea("Texto normal", 10, 130)
    b = linea("en negrita", 134, 230, trozos=[("en negrita", True, False)])
    sup = linea("1", 232, 238, y0=95, tam=12)
    c = linea("lejos", 300, 350)
    unidas = P.unir_lineas([a, b, sup, c])
    textos_ = sorted(P._texto(x) for x in unidas)
    assert "Texto normal en negrita" in textos_ and "1" in textos_ and "lejos" in textos_
    junto = next(x for x in unidas if P._texto(x).startswith("Texto"))
    assert junto["trozos"][-1] == (" en negrita", True, False)


def test_las_formulas_y_las_letras_de_las_figuras_quedan_en_la_imagen():
    pag = {"ancho": 1000, "alto": 1000, "lineas": [
        linea("Texto del póster", 10, 300, y0=50),
        linea("eje x", 520, 560, y0=520, familia="ABCDEF+DejaVuSans"),           # dentro de una figura
        linea("Figura 1. Un pie", 500, 700, y0=700),                               # pie, dentro de la figura
        linea("y", 10, 20, y0=900, familia="CMMI10"),
    ]}
    figuras = [{"pagina": 1, "x0": 0.45, "y0": 0.45, "x1": 0.95, "y1": 0.75}]
    c = P.clasificar(pag, 1, figuras, [], True)
    editables = {P._texto(x) for x in c["editables"]}
    assert editables == {"Texto del póster", "Figura 1. Un pie"}
    assert {P._texto(x) for x in c["imagen"]} == {"eje x", "y"}
    assert c["zonas"] == figuras


def test_lo_que_tapa_una_capa_de_delante_queda_en_la_imagen():
    pag = {"ancho": 1000, "alto": 1000, "lineas": [
        linea("Texto debajo de la nota", 10, 400, y0=100),
        linea("Una nota", 300, 380, y0=100 + 30),
    ]}
    tapan = [{"pagina": 1, "x0": 0.28, "y0": 0.09, "x1": 0.5, "y1": 0.2, "texto": P._letras("Una **nota**")}]
    c = P.clasificar(pag, 1, [], [], True, tapan)
    assert {P._texto(x) for x in c["editables"]} == {"Una nota"}
    assert {P._texto(x) for x in c["imagen"]} == {"Texto debajo de la nota"}


@hay_pptx
def test_un_poster_mas_grande_que_powerpoint_se_reduce(tmp_path):
    from PIL import Image
    from pptx import Presentation
    if not P.disponible()["imagen"]:
        pytest.skip("sin Ghostscript ni Poppler")
    pdf = tmp_path / "grande.pdf"
    Image.new("RGB", (2000, 1000), (40, 90, 150)).save(pdf, "PDF", resolution=10)   # 200 × 100 pulgadas
    r = P.exportar(pdf, tmp_path / "g.pptx", "imagen", ppp=20)
    prs = Presentation(str(tmp_path / "g.pptx"))
    assert r["escala"] < 0.3 and r["avisos"]
    assert prs.slide_width <= 56 * 914400 and abs(prs.slide_width / prs.slide_height - 2) < 0.01


# ---------------------------------------------------------------------- desde la aplicación
@hay_latex
@hay_todo
def test_exportar_a_powerpoint_editable_y_como_imagen(cliente):
    from pptx import Presentation
    c = cliente
    pid = c.post("/api/proyectos", json={"nombre": "Diapositiva", "asistente": {"tamano": "A3", "columnas": 2}}).get_json()["id"]
    m = c.get(f"/api/proyectos/{pid}").get_json()["modelo"]
    m["cabecera"]["titulo"] = "Un título para PowerPoint"
    c.put(f"/api/proyectos/{pid}/modelo", json=m)
    t = esperar(c, c.post(f"/api/proyectos/{pid}/powerpoint", json={"modo": "editable"}).get_json()["id"])
    assert t["estado"] == "terminado", t
    assert t["resultado"]["modo"] == "editable" and t["resultado"]["cuadros"] > 5
    r = c.get(f"/api/proyectos/{pid}/powerpoint.pptx?descargar=1")
    assert r.status_code == 200 and "Diapositiva.pptx" in r.headers["Content-Disposition"]
    prs = Presentation(io.BytesIO(r.data))
    assert abs(prs.slide_width / EMU_CM - 29.7) < 0.1 and abs(prs.slide_height / EMU_CM - 42.0) < 0.1
    assert any("Un título para PowerPoint" in x for x in textos(prs))
    if t["resultado"].get("todo_editable"):
        # todo editable: formas de PowerPoint y ninguna imagen que ocupe la diapositiva entera
        assert t["resultado"]["formas"] > 0
        assert not any(sh.shape_type == 13 and sh.width >= prs.slide_width * 0.98 for sh in prs.slides[0].shapes)
    else:
        assert sum(1 for sh in prs.slides[0].shapes if sh.shape_type == 13) == 1    # el fondo
    assert c.get(f"/api/proyectos/{pid}").get_json()["meta"]["ajustes"]["powerpoint"]["modo"] == "editable"
    # como imagen: sin cuadros de texto
    t = esperar(c, c.post(f"/api/proyectos/{pid}/powerpoint", json={"modo": "imagen"}).get_json()["id"])
    assert t["estado"] == "terminado", t
    prs = Presentation(io.BytesIO(c.get(f"/api/proyectos/{pid}/powerpoint.pptx").data))
    assert textos(prs) == [] and len(prs.slides) == 1


@hay_latex
@hay_todo
def test_powerpoint_de_un_proyecto_latex(cliente):
    from pptx import Presentation
    c = cliente
    pid = c.post("/api/proyectos", json={"nombre": "Código", "plantilla": "ejemplo-capas-latex"}).get_json()["id"]
    t = esperar(c, c.post(f"/api/proyectos/{pid}/powerpoint", json={"modo": "editable"}).get_json()["id"])
    assert t["estado"] == "terminado", t
    prs = Presentation(io.BytesIO(c.get(f"/api/proyectos/{pid}/powerpoint.pptx").data))
    assert any("Un póster por capas" in x for x in textos(prs))


def test_sin_powerpoint_todavia(cliente):
    pid = cliente.post("/api/proyectos", json={"nombre": "Nada", "asistente": {"tamano": "A4"}}).get_json()["id"]
    assert cliente.get(f"/api/proyectos/{pid}/powerpoint.pptx").status_code == 404
