# SPDX-License-Identifier: AGPL-3.0-only
"""Revisión antes de imprimir y PDF para imprenta."""
import io
import re
import shutil
import subprocess
import time

import pytest

from conftest import hay_latex
from docslab import generador as G, modelo as M, revision as R

hay_poppler = pytest.mark.skipif(not all(R.herramientas().values()), reason="sin las herramientas de Poppler")
hay_gs = pytest.mark.skipif(not (shutil.which("gs") or shutil.which("gswin64c")), reason="sin Ghostscript")


def esperar(c, tid, limite=300):
    t0 = time.time()
    while time.time() - t0 < limite:
        t = c.get(f"/api/trabajos/{tid}").get_json()
        if t["estado"] in ("terminado", "error", "cancelado"):
            return t
        time.sleep(0.2)
    raise AssertionError("el trabajo no terminó")


def png(ancho, alto, color=(40, 120, 200)):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (ancho, alto), color).save(b, "PNG")
    return b.getvalue()


def items(res, seccion=None):
    return [i for s in res["secciones"] if seccion in (None, s["id"]) for i in s["items"]]


# ---------------------------------------------------------------------- piezas sueltas
def test_contraste_y_color():
    assert round(R.contraste((0, 0, 0), (255, 255, 255)), 1) == 21.0
    assert R.contraste((119, 119, 119), (255, 255, 255)) == pytest.approx(4.48, abs=0.05)
    assert R.delta_e((10, 20, 30), (10, 20, 30)) == 0
    assert R.delta_e((0, 0, 255), (59, 83, 164)) > 25


def test_letra_de_mapa_de_bits():
    assert R.de_mapa_de_bits({"nombre": "F37", "tipo": "Type 3"})
    assert R.de_mapa_de_bits({"nombre": "ecrm1000", "tipo": "Type 3"})
    assert not R.de_mapa_de_bits({"nombre": "GJOKRJ+DejaVuSans", "tipo": "Type 3"})    # matplotlib: vectorial
    assert not R.de_mapa_de_bits({"nombre": "F37", "tipo": "Type 1"})


def test_relleno_y_ejemplos():
    assert R.es_relleno("Lorem ipsum dolor sit amet")
    assert R.es_relleno("Donec vehicula augue eu neque. Pellentesque habitant morbi.")
    # palabras del español que también salen en el lorem ipsum no bastan
    assert not R.es_relleno("El dolor de cabeza y la sed aparecen en la fase aguda.")
    assert R.es_ejemplo("Nombre Apellido^1^, Nombre Apellido^2^")
    assert R.es_ejemplo("Texto de la sección «Métodos».")
    assert not R.es_ejemplo("Material de relleno para carreteras")


def test_donde_en_palabras():
    assert R._donde({"pagina": 1, "x0": 0.0, "y0": 0.0, "x1": 0.1, "y1": 0.1}) == "la parte superior izquierda"
    assert R._donde({"pagina": 2, "x0": 0.45, "y0": 0.45, "x1": 0.55, "y1": 0.55}, True) == "la parte central de la página 2"


def test_textos_e_imagenes_del_modelo():
    m = M.desde_asistente({"tamano": "A1", "columnas": 2})
    textos = R.textos_modelo(m)
    assert ("cabecera", "titulo", "Título del póster") in textos
    huecos = [x for x in R.imagenes_modelo(m) if not x[2]]
    assert huecos, "el asistente deja figuras sin imagen"
    nodos = R.nodos_modelo(m)
    e = huecos[0][0]
    assert nodos[e]["tipo"] == "elemento" and nodos[e]["grupo"] == "imagen" and nodos[e]["nombre"].startswith("«")


def test_a_sangre_alarga_lo_que_toca_el_borde():
    m = M.desde_asistente({"tamano": "A3"})                        # 297 × 420 mm
    banda = {"id": "a-1", "tipo": "forma", "forma": "rectangulo", "x": 0, "y": 1, "ancla": "south west",
             "ancho": 1, "alto": 0.1}
    b = G.a_sangre(banda, m, 3)
    assert (b["x"], b["y"], b["ancho"], b["alto"], b["ancla"]) == ("-3mm", "378mm", "303mm", "45mm", "north west")
    centro = {"id": "a-2", "tipo": "forma", "forma": "rectangulo", "x": 0.5, "y": 0.5, "ancho": 0.2, "alto": 0.2}
    assert G.a_sangre(centro, m, 3) is centro                       # no toca el borde: igual
    girada = dict(banda, rotacion=10)
    assert G.a_sangre(girada, m, 3) is girada                       # girada: no se toca
    tex, _ = G.generar(M.normalizar(m), marcas=False, imprenta={"sangrado_mm": 3, "marcas_corte": True})
    assert "sangrado=3mm" in tex and "marcas corte=true" in tex
    assert "sangrado" not in G.generar(M.normalizar(m), marcas=False)[0]


# ---------------------------------------------------------------------- con el PDF
@hay_latex
@hay_poppler
def test_revision_encuentra_los_problemas(cliente):
    c = cliente
    pid = c.post("/api/proyectos", json={"nombre": "Rev", "asistente": {"tamano": "A1", "columnas": 2}}).get_json()["id"]
    c.post(f"/api/proyectos/{pid}/recursos", data={"archivos": [(io.BytesIO(png(80, 60)), "chica.png")]},
           content_type="multipart/form-data")
    m = c.get(f"/api/proyectos/{pid}").get_json()["modelo"]
    m["colores"]["texto"] = "C4C4C4"                                 # gris claro sobre blanco
    m["colores"]["acento"] = "7C3AED"                                # violeta que la tinta no alcanza
    bloques = [b for f in m["filas"] for col in f["columnas"] for b in col["bloques"]]
    figura = next(e for b in bloques for e in b["elementos"] if e["tipo"] == "imgAncho")
    figura["archivo"] = "recursos/chica.png"
    texto = next(e for b in bloques for e in b["elementos"] if e["tipo"] == "txtJustificado")
    texto["texto"] = "Lorem ipsum dolor sit amet, consectetuer adipiscing elit [@nadie2020]."
    c.put(f"/api/proyectos/{pid}/modelo", json=m)
    t = esperar(c, c.post(f"/api/proyectos/{pid}/revisar").get_json()["id"])
    assert t["estado"] == "terminado", t
    res = t["resultado"]
    assert res["papel"]["nombre"] == "A1" and res["papel"]["paginas"] == 1
    assert res["resumen"]["problemas"] >= 3
    ppi = [i for i in items(res, "imagenes") if i.get("ppi")]
    assert ppi and ppi[0]["nivel"] == "problema" and ppi[0]["elemento"] == figura["id"]
    assert ppi[0]["ppi"] < 30
    assert any(i["nivel"] == "problema" and i.get("contraste", 9) < 3 for i in items(res, "contraste"))
    contenido = items(res, "contenido")
    assert any(i.get("elemento") == texto["id"] and i["titulo"].startswith("Texto de ejemplo") for i in contenido)
    assert any("@nadie2020" in i["titulo"] and i["nivel"] == "problema" for i in contenido)
    assert any(i["titulo"].startswith("Texto de ejemplo en la cabecera") for i in contenido)
    for i in items(res):
        z = i.get("zona")
        if z:
            assert 0 <= z["x0"] <= z["x1"] <= 1.001 and 0 <= z["y0"] <= z["y1"] <= 1.001
    if R.colores_en_cmyk(["7C3AED"]):
        assert any(i.get("color_antes") == "#7C3AED" for i in items(res, "color"))
    # las secciones llevan el peor estado de lo que contienen
    for s in res["secciones"]:
        niveles = {i["nivel"] for i in s["items"]}
        esperado = next((n for n in ("problema", "aviso", "bien") if n in niveles), "info")
        assert s["estado"] == esperado


@hay_latex
@hay_poppler
def test_revision_de_un_poster_correcto(cliente):
    pid = cliente.post("/api/proyectos", json={"nombre": "Bien", "asistente": {"tamano": "A1", "columnas": 2}}).get_json()["id"]
    t = esperar(cliente, cliente.post(f"/api/proyectos/{pid}/revisar").get_json()["id"])
    res = t["resultado"]
    tip = items(res, "tipografias")
    assert tip and tip[0]["nivel"] == "bien"
    letra = items(res, "letra")
    assert any(i["nivel"] == "bien" and i["titulo"].startswith("Texto principal") for i in letra)


@hay_latex
@hay_poppler
def test_pdf_para_imprenta_con_sangrado_y_marcas(cliente):
    c = cliente
    pid = c.post("/api/proyectos", json={"nombre": "Imp", "asistente": {"tamano": "A3", "columnas": 2, "tema": "oscuro"}}).get_json()["id"]
    t = esperar(c, c.post(f"/api/proyectos/{pid}/imprenta", json={"sangrado_mm": 3, "marcas_corte": True}).get_json()["id"])
    assert t["estado"] == "terminado", t
    r = t["resultado"]
    assert (r["ancho_mm"], r["alto_mm"]) == (323.0, 446.0)           # 297 × 420 + 2 × (3 + 10)
    pdf = c.get(f"/api/proyectos/{pid}/imprenta.pdf?descargar=1")
    assert pdf.status_code == 200 and "Imp-imprenta.pdf" in pdf.headers["Content-Disposition"]
    destino = c.raiz / "imp.pdf"
    destino.write_bytes(pdf.data)
    cajas = subprocess.run(["pdfinfo", "-box", str(destino)], capture_output=True, text=True).stdout
    trim = [float(x) for x in re.search(r"TrimBox:\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", cajas).groups()]
    assert trim[0] == pytest.approx(36.85, abs=0.05) and trim[2] - trim[0] == pytest.approx(841.89, abs=0.1)
    assert c.get(f"/api/proyectos/{pid}").get_json()["meta"]["ajustes"]["imprenta"]["sangrado_mm"] == 3
    assert c.get(f"/api/proyectos/{pid}/imprenta.png").status_code == 200
    # el póster de siempre no cambia ni se recompila por esto
    t = esperar(c, c.post(f"/api/proyectos/{pid}/compilar").get_json()["id"])
    t = esperar(c, c.post(f"/api/proyectos/{pid}/compilar").get_json()["id"])
    assert t["mensaje"].startswith("Sin cambios")
    info = R.info_pdf(c.raiz.parent / "datos" / "proyectos" / pid / "build" / "poster.pdf")
    assert info["tamanos"][0][0] == pytest.approx(841.89, abs=0.1)


@hay_latex
@hay_poppler
@hay_gs
def test_pdf_para_imprenta_en_cmyk(cliente):
    pid = cliente.post("/api/proyectos", json={"nombre": "Cmyk", "asistente": {"tamano": "A4", "columnas": 1}}).get_json()["id"]
    t = esperar(cliente, cliente.post(f"/api/proyectos/{pid}/imprenta", json={"cmyk": True}).get_json()["id"])
    assert t["estado"] == "terminado", t
    assert t["resultado"]["archivo"] == "imprenta-cmyk.pdf" and t["resultado"]["cmyk"]
    r = cliente.get(f"/api/proyectos/{pid}/imprenta.pdf?descargar=1")
    assert "Cmyk-imprenta-cmyk.pdf" in r.headers["Content-Disposition"] and r.data[:5] == b"%PDF-"


@hay_latex
@hay_poppler
def test_imprenta_y_revision_de_un_proyecto_latex(cliente):
    c = cliente
    pid = c.post("/api/proyectos", json={"nombre": "Código", "plantilla": "ejemplo-capas-latex"}).get_json()["id"]
    t = esperar(c, c.post(f"/api/proyectos/{pid}/imprenta", json={"sangrado_mm": 3, "marcas_corte": True}).get_json()["id"])
    assert t["estado"] == "terminado", t
    assert t["resultado"]["notas"] and t["resultado"]["sangrado_mm"] == 0
    t = esperar(c, c.post(f"/api/proyectos/{pid}/revisar").get_json()["id"])
    assert t["estado"] == "terminado", t
    ids = {s["id"] for s in t["resultado"]["secciones"]}
    assert {"pagina", "letra", "tipografias"} <= ids and "color" not in ids
