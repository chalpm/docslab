# SPDX-License-Identifier: AGPL-3.0-only
"""Exportar a Word: documento, artículo y tesis, todo editable, desde el modelo."""
import io
import shutil
import subprocess
import time
import zipfile

import pytest

from conftest import hay_latex
from docslab.documento import variantes as V
from docslab.nucleo import modelo as M
from docslab.salidas import word as W

hay_docx = pytest.mark.skipif(not W.disponible()["docx"], reason="sin python-docx")
hay_pandoc = pytest.mark.skipif(not W.disponible()["pandoc"], reason="sin pandoc")


def esperar(c, tid, limite=300):
    t0 = time.time()
    while time.time() - t0 < limite:
        t = c.get(f"/api/trabajos/{tid}").get_json()
        if t["estado"] in ("terminado", "error", "cancelado"):
            return t
        time.sleep(0.2)
    raise AssertionError("el trabajo no terminó")


# ---------------------------------------------------------------------- el marcado
def test_marcado_sencillo():
    t = W.trozos_simple("Hola **negrita** y *cursiva*, H~2~O, x^2^, `f()` y $a+b$")
    assert [(x.texto, x.b, x.i, x.sub, x.sup, x.code, x.mate) for x in t if x.texto.strip()] == [
        ("Hola ", False, False, False, False, False, False), ("negrita", True, False, False, False, False, False),
        (" y ", False, False, False, False, False, False), ("cursiva", False, True, False, False, False, False),
        (", H", False, False, False, False, False, False), ("2", False, False, True, False, False, False),
        ("O, x", False, False, False, False, False, False), ("2", False, False, False, True, False, False),
        (", ", False, False, False, False, False, False), ("f()", False, False, False, False, True, False),
        (" y ", False, False, False, False, False, False), ("a+b", False, False, False, False, False, True)]


def test_marcado_latex_y_citas():
    t = W.trozos_latex(r"Ver \textbf{esto \emph{aquí}} \PCcita{(Pérez, 2020)} y \PCcitasup{3}; $x^2$ \\ fin")
    assert any(x.texto == "esto " and x.b for x in t)
    assert any(x.texto == "aquí" and x.b and x.i for x in t)
    assert any(x.texto == "(Pérez, 2020)" for x in t)
    assert any(x.texto == "3" and x.sup for x in t)
    assert any(x.mate and x.texto == "x^2" for x in t)
    assert any(x.salto for x in t)
    # el LaTeX crudo dentro del marcado sencillo
    t = W.trozos_simple(r"Antes {{\textit{dentro}}} después")
    assert any(x.texto == "dentro" and x.i for x in t)


def test_parrafos_y_saltos():
    p = W.parrafos("Uno\ndos\n\nTres", "simple")
    assert len(p) == 2 and any(x.salto for x in p[0])
    assert len(W.parrafos("Uno\ndos", "latex")) == 1
    assert W.parrafos("", "simple") == []


def test_limpiar_ecuacion():
    assert W._limpiar_ecuacion(r"\[ a=b \]") == "a=b"
    assert W._limpiar_ecuacion("$$x$$") == "x"
    assert W._limpiar_ecuacion(r"\begin{equation}y\end{equation}") == "y"
    assert W._limpiar_ecuacion("E=mc^2") == "E=mc^2"


def test_solo_documentos(tmp_path):
    m = M.desde_asistente({"clase": "poster"})
    with pytest.raises(W.ErrorWord):
        W.exportar(m, tmp_path, tmp_path / "x.docx")


# ---------------------------------------------------------------------- un documento entero
def _modelo_completo(clase="paper"):
    m = M.desde_asistente({"clase": clase, "columnas": 2})
    m["cabecera"]["titulo"] = "Un **artículo** de prueba"
    m["bibliografia"] = {"estilo": "apa", "referencias": [
        {"clave": "perez2020", "tipo": "articulo", "autores": ["Pérez, Ana"], "titulo": "Un estudio", "anio": "2020",
         "revista": "Revista de Pruebas"}]}
    b = M.bloques_de_flujo(m).__next__()
    lista = V.elemento_nuevo("txtVinetas", "e-lista")
    lista["items"] = ["primero", "segundo con *cursiva*"]
    num = V.elemento_nuevo("txtNumerada", "e-num")
    num["items"] = ["a", "b"]
    tabla = V.elemento_nuevo("txtTabla", "e-tabla")
    tabla["tabla"] = {"columnas": "lr", "encabezado": True, "filas": [["Grupo", "Media"], ["A", "1.5"], ["B", "2.0"]]}
    tabla["pie"] = "Resultados"
    ecu = V.elemento_nuevo("txtEcuacion", "e-ecu")
    ecu["ecuacion"] = r"\int_0^1 x^2\,dx = \frac{1}{3}"
    texto = V.elemento_nuevo("txtJustificado", "e-txt")
    texto["texto"] = "Según [@perez2020], el agua es H~2~O y $E=mc^2$."
    b["elementos"] = [texto, lista, num, tabla, ecu]
    return m


@hay_docx
def test_exportar_documento_completo(tmp_path):
    import docx
    m = _modelo_completo()
    r = W.exportar(m, tmp_path, tmp_path / "a.docx")
    assert r["tablas"] == 1 and r["ecuaciones"] >= 2
    d = docx.Document(str(tmp_path / "a.docx"))
    texto = "\n".join(p.text for p in d.paragraphs)
    assert "artículo" in texto and "de prueba" in texto
    assert "Pérez" in texto and "2020" in texto                    # la cita, en el estilo del proyecto
    assert "Un estudio" in texto                                    # la bibliografía
    estilos = {p.style.name for p in d.paragraphs}
    assert {"Title", "Heading 1", "List Bullet", "List Number", "Caption"} <= estilos
    assert any(r_.bold and r_.text == "artículo" for p in d.paragraphs for r_ in p.runs)
    assert any(r_.font.subscript and r_.text == "2" for p in d.paragraphs for r_ in p.runs)
    assert len(d.tables) >= 1 and d.tables[0].cell(1, 0).text == "A"
    xml = zipfile.ZipFile(tmp_path / "a.docx").read("word/document.xml").decode()
    assert "SEQ Tabla" in xml and 'w:num="2"' in xml                # pie numerado y dos columnas
    assert abs(d.sections[0].page_width.mm - 210) < 1


@hay_docx
@hay_pandoc
def test_ecuaciones_editables_con_pandoc(tmp_path):
    r = W.exportar(_modelo_completo(), tmp_path, tmp_path / "a.docx")
    assert r["ecuaciones_editables"] and r["pandoc"]
    xml = zipfile.ZipFile(tmp_path / "a.docx").read("word/document.xml").decode()
    assert "<m:oMathPara" in xml and "<m:oMath>" in xml             # en bloque y en línea


@hay_docx
@hay_latex
def test_sin_pandoc_las_formulas_van_como_imagen(tmp_path, monkeypatch):
    pytest.importorskip("pymupdf")
    original = shutil.which
    monkeypatch.setattr(W.shutil, "which", lambda n, *a, **k: None if n == "pandoc" else original(n, *a, **k))
    r = W.exportar(_modelo_completo(), tmp_path, tmp_path / "a.docx")
    assert not r["pandoc"] and any("pandoc" in a for a in r["avisos"])
    z = zipfile.ZipFile(tmp_path / "a.docx")
    xml = z.read("word/document.xml").decode()
    assert "<m:oMath" not in xml and r"\frac{1}{3}" in xml          # imagen con su código como texto alternativo
    assert sum(1 for n in z.namelist() if n.startswith("word/media/")) >= 2


@hay_docx
def test_tesis_con_portada_indices_y_capitulos(tmp_path):
    import docx
    m = M.desde_asistente({"clase": "tesis"})
    m["documento"]["lista_figuras"] = True
    W.exportar(m, tmp_path, tmp_path / "t.docx")
    d = docx.Document(str(tmp_path / "t.docx"))
    textos = [p.text for p in d.paragraphs]
    assert "Nombre de la institución" in textos and "TESIS" in textos
    assert "Capítulo 1. Introducción" in textos and "1.1 Planteamiento del problema" in textos
    assert "Apéndice A. Datos complementarios" in textos
    xml = zipfile.ZipFile(tmp_path / "t.docx").read("word/document.xml").decode()
    assert "TOC \\o" in xml and 'TOC \\h \\z \\c &quot;Figura&quot;' in xml
    ajustes = zipfile.ZipFile(tmp_path / "t.docx").read("word/settings.xml").decode()
    assert "updateFields" in ajustes


@hay_docx
@pytest.mark.skipif(shutil.which("soffice") is None, reason="sin LibreOffice")
def test_libreoffice_abre_el_word(tmp_path):
    W.exportar(_modelo_completo(), tmp_path, tmp_path / "a.docx")
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp_path), str(tmp_path / "a.docx")],
                   capture_output=True, timeout=180)
    assert (tmp_path / "a.pdf").exists() and (tmp_path / "a.pdf").stat().st_size > 2000


# ---------------------------------------------------------------------- desde la aplicación
@hay_docx
def test_word_desde_la_aplicacion(cliente):
    import docx
    c = cliente
    pid = c.post("/api/proyectos", json={"nombre": "Informe", "asistente": {"clase": "documento"}}).get_json()["id"]
    m = c.get(f"/api/proyectos/{pid}").get_json()["modelo"]
    m["cabecera"]["titulo"] = "Un informe en Word"
    c.put(f"/api/proyectos/{pid}/modelo", json=m)
    assert c.get(f"/api/proyectos/{pid}/word.docx").status_code == 404
    t = esperar(c, c.post(f"/api/proyectos/{pid}/word", json={}).get_json()["id"])
    assert t["estado"] == "terminado", t
    r = c.get(f"/api/proyectos/{pid}/word.docx?descargar=1")
    assert r.status_code == 200 and "Informe.docx" in r.headers["Content-Disposition"]
    d = docx.Document(io.BytesIO(r.data))
    assert any(p.text == "Un informe en Word" for p in d.paragraphs)
    assert "word" in c.get("/api/estado").get_json()


def test_word_no_para_posteres(cliente):
    c = cliente
    pid = c.post("/api/proyectos", json={"nombre": "Póster", "asistente": {"tamano": "A3"}}).get_json()["id"]
    t = esperar(c, c.post(f"/api/proyectos/{pid}/word", json={}).get_json()["id"])
    assert t["estado"] == "error" and "documentos" in t["mensaje"]


@hay_pandoc
def test_una_formula_no_puede_salir_de_las_matematicas():
    f = W.Formulas()
    f.preparar([("x^2", False), (r"a$ \input{/etc/hostname} $b", False)])
    assert ("x^2", False) in f.omml
    assert (r"a$ \input{/etc/hostname} $b", False) not in f.omml       # no pasa por pandoc
