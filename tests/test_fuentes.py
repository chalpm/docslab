# SPDX-License-Identifier: AGPL-3.0-only
"""Tipografías: las libres de TeX Live y las propias (.ttf, .otf) con LuaLaTeX."""
import io
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

import pytest

from conftest import hay_latex
from docslab import compilador, fuentes as F, generador as G, modelo as M


def kpse(nombre):
    if not shutil.which("kpsewhich"):
        return None
    r = subprocess.run(["kpsewhich", nombre], capture_output=True, text=True)
    p = r.stdout.strip()
    return Path(p) if p else None


HEROS = kpse("texgyreheros-regular.otf")
HEROS_N = kpse("texgyreheros-bold.otf")
hay_heros = pytest.mark.skipif(not (HEROS and HEROS_N), reason="sin TeX Gyre Heros")
hay_lualatex = pytest.mark.skipif(shutil.which("lualatex") is None, reason="sin lualatex")


def esperar(c, tid, limite=300):
    t0 = time.time()
    while time.time() - t0 < limite:
        t = c.get(f"/api/trabajos/{tid}").get_json()
        if t["estado"] in ("terminado", "error", "cancelado"):
            return t
        time.sleep(0.2)
    raise AssertionError("el trabajo no terminó")


# ---------------------------------------------------------------------- lectura de archivos
def test_rechaza_lo_que_no_es_una_tipografia():
    for datos, texto in ((b"", "vacío"), (b"ttcf" + b"\0" * 20, ".ttc"), (b"wOFF" + b"\0" * 20, ".woff"),
                         (b"%PDF-1.4" + b"\0" * 20, "TrueType")):
        with pytest.raises(F.ErrorFuente, match=texto):
            F.leer(datos)


@hay_heros
def test_lee_familia_peso_y_estilo():
    d = F.leer(HEROS.read_bytes())
    assert d["familia"] == "TeX Gyre Heros" and d["peso"] == 400 and not d["cursiva"] and d["incrustable"]
    assert F.leer(HEROS_N.read_bytes())["peso"] >= 700


@hay_heros
def test_guardar_y_agrupar_en_familias(tmp_path):
    rel = F.guardar(tmp_path, "Mi Fuente Ñ (normal).otf", HEROS.read_bytes())
    assert rel == "fuentes/Mi-Fuente-N-normal.otf"
    F.guardar(tmp_path, "negrita.otf", HEROS_N.read_bytes())
    assert F.guardar(tmp_path, "negrita.otf", HEROS_N.read_bytes()) == "fuentes/negrita.otf"   # igual: no se duplica
    with pytest.raises(F.ErrorFuente):
        F.guardar(tmp_path, "texto.txt", b"hola")
    fams = F.familias(tmp_path)
    assert len(fams) == 1
    f = fams[0]
    assert f["id"] == "propia-tex-gyre-heros" and f["nombre"] == "TeX Gyre Heros"
    assert f["archivos"]["normal"] == rel and f["archivos"]["negrita"] == "fuentes/negrita.otf"
    assert f["archivos"]["cursiva"] == ""
    assert F.borrar_familia(tmp_path, f["id"]) == 2 and F.familias(tmp_path) == []


# ---------------------------------------------------------------------- generador y motor
def test_motor_y_familias_de():
    m = M.desde_asistente({"tamano": "A4"})
    assert M.motor(m) == "pdflatex" and G.familias_de(m) == ("helvetica", "")
    m["tipografia"].update({"familia": "sourcesans", "familia_titulos": "merriweather"})
    assert M.motor(m) == "pdflatex" and G.familias_de(m) == ("sourcesans", "merriweather")
    m["tipografia"]["propias"] = [{"id": "propia-x", "nombre": "X", "archivos": {"normal": "fuentes/X-Regular.ttf"}}]
    m["tipografia"]["familia"] = "propia-x"
    assert M.motor(m) == "lualatex"
    # con LuaLaTeX, las libres se cambian por una clásica del mismo tipo
    assert G.familias_de(m) == ("propia-x", "palatino")
    tex, _ = G.generar(M.normalizar(m))
    assert tex.startswith("% !TEX program = lualatex")
    assert "\\posterfamilia{propia-x}{fuentes/}{X-Regular.ttf}{}{}{}" in tex
    assert "familia=propia-x" in tex and "familia titulos=palatino" in tex
    # una propia que no existe en la lista no cuenta
    m["tipografia"]["familia"] = "propia-otra"
    assert M.motor(m) == "pdflatex" and G.familias_de(m)[0] == "helvetica"


def test_motor_de_un_proyecto_latex():
    assert compilador.motor_del_tex("% !TEX program = lualatex\n\\documentclass{article}") == "lualatex"
    assert compilador.motor_del_tex("%!TEX TS-program = xelatex\n") == "xelatex"
    assert compilador.motor_del_tex("\\documentclass{article}") == "pdflatex"


# ---------------------------------------------------------------------- compilando
@hay_latex
def test_familia_libre_con_pdflatex(cliente):
    if compilador.existe_tex("sourcesanspro.sty") is False:
        pytest.skip("sin el paquete sourcesanspro")
    pid = cliente.post("/api/proyectos", json={"nombre": "Libre", "asistente": {"tamano": "A4", "columnas": 1}}).get_json()["id"]
    m = cliente.get(f"/api/proyectos/{pid}").get_json()["modelo"]
    m["tipografia"].update({"familia": "sourcesans", "familia_titulos": "palatino"})
    cliente.put(f"/api/proyectos/{pid}/modelo", json=m)
    t = esperar(cliente, cliente.post(f"/api/proyectos/{pid}/compilar").get_json()["id"])
    assert t["resultado"]["ok"] and t["resultado"]["motor"] == "pdflatex"
    pdf = cliente.raiz.parent / "datos" / "proyectos" / pid / "build" / "poster.pdf"
    nombres = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True).stdout if shutil.which("pdffonts") else ""
    if nombres:
        assert "SourceSansPro" in nombres and ("Palladio" in nombres or "Palatino" in nombres)


@hay_latex
@hay_lualatex
@hay_heros
def test_tipografia_propia_con_lualatex(cliente):
    c = cliente
    pid = c.post("/api/proyectos", json={"nombre": "Propia", "asistente": {"tamano": "A4", "columnas": 1}}).get_json()["id"]
    r = c.post(f"/api/proyectos/{pid}/fuentes", data={"archivos": [(io.BytesIO(HEROS.read_bytes()), "Marca-Regular.otf"),
                                                                   (io.BytesIO(b"no"), "mala.otf")]},
               content_type="multipart/form-data").get_json()
    assert r["guardados"] == ["fuentes/Marca-Regular.otf"] and len(r["errores"]) == 1
    assert r["nuevas"] == ["propia-tex-gyre-heros"]
    m = c.get(f"/api/proyectos/{pid}").get_json()["modelo"]
    m["tipografia"]["propias"] = r["familias"]
    m["tipografia"]["familia"] = "propia-tex-gyre-heros"
    c.put(f"/api/proyectos/{pid}/modelo", json=m)
    t = esperar(c, c.post(f"/api/proyectos/{pid}/compilar").get_json()["id"])
    assert t["resultado"]["ok"], t["resultado"].get("errores")
    assert t["resultado"]["motor"] == "lualatex" and t["resultado"]["posiciones"]["cajas"]
    # el zip para Overleaf lleva la tipografía y el latexmkrc que pide LuaLaTeX
    z = zipfile.ZipFile(io.BytesIO(c.get(f"/api/proyectos/{pid}/exportar?tipo=overleaf").data))
    assert "fuentes/Marca-Regular.otf" in z.namelist() and "latexmkrc" in z.namelist()
    assert "lualatex" in z.read("latexmkrc").decode()
    # quitar la familia
    r = c.delete(f"/api/proyectos/{pid}/fuentes?familia=propia-tex-gyre-heros").get_json()
    assert r["familias"] == []
