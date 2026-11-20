# SPDX-License-Identifier: AGPL-3.0-only
import json

import pytest

from conftest import RAIZ, hay_latex
from docslab.salidas import compilador
from docslab.documento import generador as G, variantes as V
from docslab.nucleo import modelo as M

PLANTILLAS = sorted(p.parent.name for p in (RAIZ / "plantillas").glob("*/modelo.json"))


def _modelo_con(elementos):
    m = M.normalizar({})
    m["filas"] = [{"id": "f-1", "columnas": [{"id": "c-1", "bloques": [
        {"id": "b-1", "titulo": "Caja", "elementos": elementos}]}]}]
    return M.normalizar(m)


def test_normalizar_completa_y_asegura_ids():
    m = M.normalizar({"filas": [{"columnas": [{"bloques": [{"titulo": "x", "elementos": [{"tipo": "txtJustificado"}]}]}]}]})
    b = m["filas"][0]["columnas"][0]["bloques"][0]
    assert b["id"].startswith("b-") and b["mostrar_titulo"] is True
    assert b["elementos"][0]["texto"]                    # valor por defecto de la variante
    assert [c["id"] for c in m["capas"]] == ["fondo", "frente"]


@pytest.mark.parametrize("clave", [v["clave"] for v in V.VARIANTES])
def test_cada_variante_genera_su_orden(clave):
    e = V.elemento_nuevo(clave, "e-x")
    tex, mapa = G.generar(_modelo_con([e]))
    if clave == "latex":
        assert e["codigo"] in tex
    elif clave == "espacio":
        assert "\\vspace{1em}" in tex
    elif clave == "bibliografia":
        assert "\\PCbibliografia" in tex
    else:
        assert "\\" + clave in tex
    assert "e-x" in mapa.values()


def test_titulo_oculto_en_cajas_y_cajas_de_texto():
    e = V.elemento_nuevo("txtResaltado", "e-r")
    e.update({"titulo": "Nota", "mostrar_titulo": False})
    m = _modelo_con([e])
    m["filas"][0]["columnas"][0]["bloques"][0]["mostrar_titulo"] = False
    tex, _ = G.generar(m)
    assert "titulo={Caja}, mostrar titulo=false" in tex
    assert "\\txtResaltado[titulo={Nota}, mostrar titulo=false]" in tex


def test_capas_y_elementos_de_capa():
    m = M.normalizar({})
    m["capas"].append({"id": "notas", "nombre": "Notas", "z": 5, "elementos": [
        {"id": "a-1", "tipo": "texto", "texto": "Hola **mundo**", "x": 0.2, "y": "30mm", "rotacion": 10, "fondo": "FFF1A8"},
        {"id": "a-2", "tipo": "forma", "forma": "flecha", "x": 0.1, "y": 0.1, "x2": 0.3, "y2": 0.2},
        {"id": "a-3", "tipo": "imagen", "archivo": "recursos/a.png", "ancho": 0.3, "ajuste": "cubrir", "alto": 0.2}]})
    tex, _ = G.generar(M.normalizar(m))
    assert "\\configcapa{notas}{z=5, opacidad=1, visible=true}" in tex
    assert "\\colocartexto[capa=notas, id=a-1, x=0.2, y=30mm, rotacion=10, fondo=FFF1A8]{Hola \\textbf{mundo}}" in tex
    assert "forma=flecha" in tex and "x2=0.3" in tex
    assert "\\colocarimagen[capa=notas, id=a-3, x=0.5, y=0.5, ancho=0.3, alto=0.2, ajuste=cubrir]{recursos/a.png}" in tex


def test_rutas_y_colores_peligrosos_se_neutralizan():
    e = V.elemento_nuevo("imgAncho", "e-i")
    e["archivo"] = "../../etc/passwd"
    m = _modelo_con([e])
    m["filas"][0]["columnas"][0]["bloques"][0]["opciones"] = {"fondo": "red}\\evil", "borde": "acento!20"}
    tex, _ = G.generar(m)
    assert "{imagen-pendiente}" in tex and "passwd" not in tex
    assert "evil" not in tex and "borde=pcAcento!20" in tex


@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_convertir_formato_no_cambia_el_poster(plantilla):
    m = M.normalizar(json.loads((RAIZ / "plantillas" / plantilla / "modelo.json").read_text(encoding="utf-8")))
    t0, _ = G.generar(m)
    ml = M.convertir_formato(m, "latex")
    assert ml["formato_texto"] == "latex"
    assert G.generar(ml)[0] == t0
    assert G.generar(M.convertir_formato(ml, "simple"))[0] == t0


def test_asistente():
    m = M.desde_asistente({"tamano": "A1", "orientacion": "horizontal", "columnas": 4, "tema": "verde"})
    assert (m["lienzo"]["ancho"], m["lienzo"]["alto"]) == ("841mm", "594mm")
    assert len(m["filas"][0]["columnas"]) == 4 and m["colores"]["primario"] == "14532D"


def test_idioma_del_poster():
    m = M.desde_asistente({"idioma": "en"})
    assert m["idioma"] == "en" and m["estilo"]["nombre_figura"] == "Figure"
    assert "idioma=english" in G.generar(m)[0]
    assert M.desde_asistente({})["idioma"] == "es"
    viejo = M.normalizar({})                      # proyectos anteriores: sin idioma, como antes
    assert viejo["idioma"] == "" and "idioma=" not in G.generar(viejo)[0]


def test_asistente_ajusta_imagen_y_letra():
    def imagen(m):
        return [e for c in m["filas"][0]["columnas"] for b in c["bloques"] for e in b["elementos"]
                if e["tipo"] == "imgAncho"][0]
    # una sola columna en horizontal: la imagen a todo el ancho no cabría en el alto
    assert imagen(M.desde_asistente({"tamano": "A0", "orientacion": "horizontal", "columnas": 1}))["tam"] < 60
    assert imagen(M.desde_asistente({"tamano": "A0", "columnas": 3}))["tam"] == 100
    # 9 pt como mínimo, salvo que los títulos no quepan en columnas muy estrechas
    assert M.desde_asistente({"tamano": "A4", "columnas": 3})["tipografia"]["fuente"] == 9
    assert M.desde_asistente({"tamano": "A4", "columnas": 6})["tipografia"]["fuente"] < 9
    assert M.desde_asistente({"tamano": "A0", "columnas": 3})["tipografia"]["fuente"] == 30


@hay_latex
def test_imagen_de_reserva_mide_lo_pedido(tmp_path):
    """Sin el archivo se dibuja un recuadro con el tamaño exacto (escalarlo dejaba medio punto de más)."""
    import shutil
    import subprocess
    shutil.copy(RAIZ / "latex" / "postercientifico.sty", tmp_path)
    (tmp_path / "t.tex").write_text(
        "\\documentclass{article}\\usepackage{postercientifico}\\posterconfig{tamano=A0}\\begin{document}\n"
        "\\sbox0{\\PCimg[width=1087.3pt]{no-existe}}\\typeout{MIDE \\the\\wd0}\n"
        "\\sbox0{\\PCimg[width=400pt,height=100pt,keepaspectratio]{no-existe}}\\typeout{MIDE \\the\\wd0 x\\the\\ht0}\n"
        "\\sbox0{\\PCimg[height=300pt]{imagen-pendiente}}\\typeout{MIDE \\the\\wd0}\n"
        "\\noindent\\PCimg[width=\\linewidth]{imagen-pendiente}\n\\end{document}\n", encoding="utf-8")
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "t.tex"], cwd=tmp_path, capture_output=True,
                       text=True, errors="replace")
    log = (tmp_path / "t.log").read_text(encoding="utf-8", errors="replace")
    assert r.returncode == 0, log[-2000:]
    assert [l.split("MIDE ")[1].strip() for l in log.splitlines() if l.startswith("MIDE ")] == \
        ["1087.3pt", "133.33333ptx100.0pt", "400.0pt"]
    assert "Overfull" not in log


def test_localizar_error_en_filas():
    lineas = ["\\begin{fila}[id=f-1]", "  \\begin{columna}[id=c-1]", "    \\begin{caja}[id=b-1]",
              "      \\txtJustificado{Hola \\ordenmala}", "    \\end{caja}", "  \\end{columna}", "\\end{fila}"]
    mapa = {1: "f-1", 2: "c-1", 3: "b-1", 4: "e-1", 5: "b-1", 6: "c-1", 7: "f-1"}
    error = {"linea": 7, "contexto": "<argument> Hola \\ordenmala\n   {}\nl.7 \\end{fila}"}
    assert compilador.localizar_error(error, lineas, mapa) == "e-1"


def test_leer_registro():
    log = ("./poster.tex:12: Undefined control sequence.\n<argument> \\malo\n\nl.12 \\end{fila}\n\n"
           "Package postercientifico Warning: La fila f-1 no cabe: sobra 3.0pt de contenido on input line 5.\n"
           "Overfull \\hbox (2.0pt too wide) in paragraph at lines 3--4\n"
           "Output written on build/poster.pdf (1 page, 1234 bytes).\n")
    r = compilador.leer_registro(log)
    assert r["errores"][0]["linea"] == 12 and r["paginas"] == 1
    assert {a["tipo"] for a in r["avisos"]} == {"plantilla", "desborde"}


@hay_latex
@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_las_plantillas_compilan_en_una_pagina(plantilla, tmp_path):
    from docslab.nucleo import almacen as A
    alm = A.Almacen(tmp_path)
    meta = alm.crear_proyecto("p", plantilla)
    alm.escribir_tex(meta["id"], marcas=True)
    res = compilador.compilar(alm.dir_proyecto(meta["id"]), "poster.tex")
    assert res["ok"], res.get("errores")
    if meta.get("clase", "poster") == "poster":            # un póster es una sola hoja
        assert res["paginas"] == 1
    assert res["posiciones"]["cajas"], "faltan las marcas de posición"
    assert not [a for a in res["avisos"] if a["tipo"] == "plantilla"], res["avisos"]


def test_tamano_de_cada_logo():
    from docslab.documento import generador as G
    from docslab.nucleo import modelo as M
    m = M.desde_asistente({"tamano": "A2"})
    assert m["cabecera"]["tam_logo_izquierdo"] == 100
    m["cabecera"].update({"tam_logo_izquierdo": 160, "tam_logo_derecho": 900})
    tex, _ = G.generar(M.normalizar(m))
    assert "escala logo izquierdo=1.6" in tex
    assert "escala logo derecho=3" in tex          # como mucho 300 %
    assert G.tam_logo("x") == 1 and G.tam_logo(10) == 0.3
