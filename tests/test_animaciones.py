# SPDX-License-Identifier: AGPL-3.0-only
"""Animaciones y transiciones del PowerPoint exportado (salidas/animaciones.py) y PowerPoint todo editable."""
import io
import re
import shutil
import subprocess
import zipfile

import pytest
from lxml import etree

from docslab.nucleo import modelo as M
from docslab.salidas import animaciones as AN

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _xml(s: str):
    return etree.fromstring(s.replace(">", f' xmlns:p="{P_NS}">', 1))


def test_normalizar():
    assert AN.normalizar_animacion({"efecto": "nada"}) is None
    assert AN.normalizar_animacion(None) is None
    a = AN.normalizar_animacion({"efecto": "subir", "inicio": "raro", "duracion": "99", "retraso": -3})
    assert a == {"efecto": "subir", "inicio": "clic", "duracion": 10.0, "retraso": 0.0}
    assert AN.normalizar_transicion({"efecto": "empujar"}) == {"efecto": "empujar", "velocidad": "media"}
    assert AN.normalizar_transicion({"efecto": "x"}) is None


def test_el_modelo_limpia_lo_que_no_vale():
    m = {"clase": "poster", "filas": [{"columnas": [{"bloques": [
        {"titulo": "A", "animacion": {"efecto": "desvanecer", "duracion": "2"},
         "elementos": [{"tipo": "texto", "animacion": {"efecto": "volar"}}]}]}]}]}
    m["transicion"] = {"efecto": "dividir", "velocidad": "turbo"}
    m = M.normalizar(m)
    b = m["filas"][0]["columnas"][0]["bloques"][0]
    assert b["animacion"]["duracion"] == 2.0 and b["animacion"]["inicio"] == "clic"
    assert "animacion" not in b["elementos"][0]
    assert m["transicion"] == {"efecto": "dividir", "velocidad": "media"}


def test_xml_de_transiciones():
    for efecto, etiqueta in [("desvanecer", "fade"), ("empujar", "push"), ("barrido", "wipe"), ("cubrir", "cover"),
                             ("dividir", "split")]:
        x = _xml(AN.xml_transicion({"efecto": efecto, "velocidad": "lenta"}))
        assert x.get("spd") == "slow" and x[0].tag == f"{{{P_NS}}}{etiqueta}"
    assert AN.xml_transicion(None) == ""


def test_secuencia_de_animaciones():
    a = lambda ef, ini: AN.normalizar_animacion({"efecto": ef, "inicio": ini, "duracion": 0.5})  # noqa: E731
    x = _xml(AN.xml_animaciones([(10, a("aparecer", "clic")), (11, a("desvanecer", "con")), (12, a("subir", "despues")),
                                 (13, a("barrido", "clic")), (14, a("aumentar", "despues"))]))
    ns = {"p": P_NS}
    efectos = x.findall(".//p:cTn[@presetClass='entr']", ns)
    assert [e.get("nodeType") for e in efectos] == ["clickEffect", "withEffect", "afterEffect", "clickEffect", "afterEffect"]
    assert [e.get("presetID") for e in efectos] == ["1", "10", "2", "22", "53"]
    # dos grupos de clic (esperan un clic: delay="indefinite"), y todos los id distintos
    grupos = x.findall(".//p:cTn[@nodeType='mainSeq']/p:childTnLst/p:par", ns)
    assert len(grupos) == 2
    ids = [c.get("id") for c in x.iter(f"{{{P_NS}}}cTn")]
    assert len(ids) == len(set(ids))
    assert {t.get("spid") for t in x.iter(f"{{{P_NS}}}spTgt")} == {"10", "11", "12", "13", "14"}
    # la tanda «después» empieza cuando acaba la anterior (0,5 s)
    assert x.find(".//p:cTn[@nodeType='mainSeq']/p:childTnLst/p:par/p:cTn/p:childTnLst/p:par[2]/p:cTn/p:stCondLst/p:cond",
                  ns).get("delay") == "500"


def test_la_primera_sin_clic_empieza_sola():
    x = _xml(AN.xml_animaciones([(5, AN.normalizar_animacion({"efecto": "desvanecer", "inicio": "con"}))]))
    conds = x.findall(f".//{{{P_NS}}}cTn[@nodeType='mainSeq']/{{{P_NS}}}childTnLst/{{{P_NS}}}par/{{{P_NS}}}cTn/"
                      f"{{{P_NS}}}stCondLst/{{{P_NS}}}cond")
    assert any(c.get("evt") == "onBegin" for c in conds)


def test_transicion_de_cada_pagina():
    m = {"clase": "presentacion", "paginas": [{"id": "p-1", "transicion": {"efecto": "empujar"}}, {"id": "p-2"}]}
    pos = {"paginas": {"p-1": 1, "p-2": 3}}
    assert AN.transicion_de_pagina(m, 1, pos)["efecto"] == "empujar"
    assert AN.transicion_de_pagina(m, 2, pos)["efecto"] == "empujar"       # la diapositiva 1 ocupa dos páginas
    assert AN.transicion_de_pagina(m, 3, pos) is None
    assert AN.transicion_de_pagina({"clase": "poster", "transicion": {"efecto": "barrido"}}, 1, None)["efecto"] == "barrido"


# ------------------------------------------------------------------ PowerPoint todo editable
pymupdf = pytest.importorskip("pymupdf")
pptx = pytest.importorskip("pptx")
hay_poppler = pytest.mark.skipif(shutil.which("pdftohtml") is None or shutil.which("pdftoppm") is None,
                                 reason="sin Poppler")


def _pdf_de_prueba(ruta):
    """Una página con: fondo de color, una caja con borde, una caja redondeada, una línea, una imagen
    recortada (clip) y texto."""
    from PIL import Image
    doc = pymupdf.open()
    pg = doc.new_page(width=600, height=400)
    pg.draw_rect(pymupdf.Rect(0, 0, 600, 400), color=None, fill=(0.95, 0.95, 0.9))
    pg.draw_rect(pymupdf.Rect(40, 40, 280, 200), color=(0.2, 0.3, 0.5), fill=(1, 1, 1), width=2)
    pg.draw_rect(pymupdf.Rect(320, 40, 560, 200), color=None, fill=(0.8, 0.4, 0.2), radius=0.1)
    pg.draw_line(pymupdf.Point(40, 250), pymupdf.Point(560, 250), color=(0, 0, 0), width=1.5)
    b = io.BytesIO()
    Image.new("RGB", (400, 200), (30, 120, 60)).save(b, "PNG")
    pg.insert_image(pymupdf.Rect(40, 270, 240, 370), stream=b.getvalue())
    pg.insert_text((60, 100), "Hola PowerPoint", fontsize=20, fontname="helv", color=(0.1, 0.1, 0.1))
    doc.save(str(ruta))


@hay_poppler
def test_powerpoint_todo_editable(tmp_path):
    from pptx import Presentation
    from docslab.salidas import powerpoint as P
    pdf = tmp_path / "p.pdf"
    _pdf_de_prueba(pdf)
    modelo = {"clase": "poster", "transicion": {"efecto": "desvanecer"},
              "filas": [{"id": "f-1", "columnas": [{"id": "c-1", "bloques": [
                  {"id": "b-1", "animacion": {"efecto": "desvanecer"}, "elementos": []}]}]}], "capas": []}
    # posiciones en pt de TeX (como las da la plantilla): la caja b-1 es la de la izquierda
    k = 72.27 / 72
    pos = {"papel": {"ancho": 600 * k, "alto": 400 * k},
           "cajas": {"b-1": {"pagina": 1, "x0": 38 * k, "y0": 38 * k, "x1": 282 * k, "y1": 202 * k}}}
    r = P.exportar(pdf, tmp_path / "p.pptx", "editable", modelo, pos, ppp=72)
    assert r["todo_editable"] and r["formas"] >= 3 and r["imagenes"] == 1 and r["cuadros"] >= 1 and r["animadas"] == 1
    prs = Presentation(str(tmp_path / "p.pptx"))
    d = prs.slides[0]
    tipos = [s.shape_type for s in d.shapes]
    nombres = [s.name for s in d.shapes]
    assert any(n.startswith("Rectángulo redondeado") for n in nombres)
    assert sum(1 for t in tipos if t == 13) == 1                      # una imagen (no una imagen de fondo)
    grupo = next(s for s in d.shapes if s.shape_type == 6)
    assert any(s.has_text_frame and "Hola PowerPoint" in s.text_frame.text for s in grupo.shapes)
    xml = etree.tostring(d._element).decode()
    assert "<p:transition" in xml and "<p:timing" in xml and f'spid="{grupo.shape_id}"' in xml
    assert d.background.fill.fore_color.rgb is not None               # el color de fondo, como fondo de la diapositiva


@hay_poppler
@pytest.mark.skipif(shutil.which("soffice") is None, reason="sin LibreOffice")
def test_libreoffice_lee_las_animaciones(tmp_path):
    """LibreOffice abre el .pptx y reconoce cada efecto (prueba de que el XML es válido)."""
    from pptx import Presentation
    from pptx.util import Pt
    prs = Presentation()
    d = prs.slides.add_slide(prs.slide_layouts[6])
    pasos = []
    for i, (ef, ini) in enumerate([("aparecer", "con"), ("desvanecer", "clic"), ("subir", "despues"),
                                   ("barrido", "con"), ("aumentar", "clic")]):
        s = d.shapes.add_textbox(Pt(50 + i * 100), Pt(100), Pt(90), Pt(40))
        s.text_frame.text = ef
        pasos.append((s.shape_id, AN.normalizar_animacion({"efecto": ef, "inicio": ini})))
    AN.poner_en_diapositiva(d, AN.xml_transicion({"efecto": "barrido"}), AN.xml_animaciones(pasos))
    prs.save(str(tmp_path / "a.pptx"))
    subprocess.run(["soffice", "--headless", "--convert-to", "odp", "--outdir", str(tmp_path), str(tmp_path / "a.pptx")],
                   capture_output=True, timeout=180, env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"})
    contenido = zipfile.ZipFile(tmp_path / "a.odp").read("content.xml").decode()
    efectos = re.findall(r'presentation:node-type="(on-click|with-previous|after-previous)"[^>]*'
                         r'presentation:preset-id="([^"]+)"', contenido)
    assert efectos == [("with-previous", "ooo-entrance-appear"), ("on-click", "ooo-entrance-fade-in"),
                       ("after-previous", "ooo-entrance-fly-in"), ("with-previous", "ooo-entrance-wipe"),
                       ("on-click", "ooo-entrance-fade-in-and-zoom")]
    assert "barWipe" in contenido
