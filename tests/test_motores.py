"""La distribución de TeX: MiKTeX (instala solo lo que falte), formatos que hay que
rehacer y compilaciones que fallan sin dejar registro."""
import os
import stat
import sys
from pathlib import Path

import pytest

from conftest import hay_latex
from docslab import compilador as C, generador as G, modelo as M

MIKTEX = "MiKTeX-pdfTeX 4.20 (MiKTeX 25.4)"


@pytest.fixture
def miktex(monkeypatch):
    monkeypatch.setattr(C, "version_tex", lambda: MIKTEX)
    monkeypatch.setattr(C, "_KPSE_CACHE", {})


def guion(tmp_path: Path, nombre: str, cuerpo: str) -> str:
    """Un «pdflatex» de mentira (un guion de Python) para probar lo que hace DocsLab."""
    p = tmp_path / nombre
    p.write_text(f"#!{sys.executable}\nimport os, sys\n{cuerpo}\n", encoding="utf-8")
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return str(p)


def test_los_posters_no_cargan_epstopdf():
    tex, _ = G.generar(M.normalizar(M.desde_asistente({"tamano": "A3"})))
    lineas = tex.splitlines()
    i_eps = next(i for i, x in enumerate(lineas) if x.startswith(C.SIN_EPSTOPDF))
    i_doc = lineas.index("\\documentclass{article}")
    assert i_eps < i_doc
    assert C._FORMATO_TEX.index(C.SIN_EPSTOPDF) < C._FORMATO_TEX.index("\\documentclass")


def test_con_miktex_se_instala_lo_que_falta(miktex):
    assert C.es_miktex()
    assert C.opciones_motor() == ["--enable-installer"]
    assert C.tiempo_motor(45) == 600 and C.tiempo_motor(900) == 900
    if C.shutil.which("kpsewhich"):
        # lo que kpsewhich no encuentra todavía no se da por perdido: MiKTeX lo instalará
        assert C.existe_tex("paquete-que-no-existe-xyz.sty") is None
        assert C.existen_tex(["paquete-que-no-existe-xyz.sty"])["paquete-que-no-existe-xyz.sty"] is None


def test_sin_miktex_no_cambia_nada(monkeypatch):
    monkeypatch.setattr(C, "version_tex", lambda: "pdfTeX 3.141592653-2.6-1.40.25 (TeX Live 2023/Debian)")
    assert not C.es_miktex() and C.opciones_motor() == [] and C.tiempo_motor(45) == 45


def test_un_formato_que_falla_se_rehace_una_vez(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "_FORMATOS_MALOS", set())
    monkeypatch.setattr(C, "_FALLOS_FORMATO", {})
    fmt = tmp_path / "pcposter-abc123"
    fmt.with_suffix(".fmt").write_bytes(b"x")
    C.olvidar_formato(str(fmt))
    assert not fmt.with_suffix(".fmt").exists() and "abc123" not in C._FORMATOS_MALOS
    C.olvidar_formato(str(fmt))
    assert "abc123" in C._FORMATOS_MALOS


@pytest.mark.skipif(os.name == "nt", reason="guion de shell")
def test_un_fallo_sin_registro_se_explica(tmp_path, monkeypatch):
    exe = guion(tmp_path, "pdflatex-roto", "sys.stderr.write('pdflatex: algo salió mal\\n'); sys.exit(1)")
    monkeypatch.setenv("DOCSLAB_PDFLATEX", exe)
    d = tmp_path / "p"
    d.mkdir()
    (d / "poster.tex").write_text("\\documentclass{article}\\begin{document}x\\end{document}\n", encoding="utf-8")
    (d / "build").mkdir()
    (d / "build" / "poster.log").write_text("registro viejo sin errores\n", encoding="utf-8")
    r = C.compilar(d, "poster.tex", copiar_sty=False, hacer_miniatura=False)
    assert not r["ok"]
    assert r["errores"] and "algo salió mal" in r["errores"][0]["mensaje"]
    assert not (d / "build" / "poster.log").exists()      # no se lee el registro de la vez anterior


@hay_latex
@pytest.mark.skipif(os.name == "nt", reason="guion de shell")
def test_miktex_rechaza_un_formato_viejo(tmp_path, monkeypatch):
    """MiKTeX no carga un formato anterior a su última actualización («The memory dump
    file could not be found»): se compila sin él y se rehace la próxima vez."""
    real = C.shutil.which("pdflatex")
    exe = guion(tmp_path, "pdflatex-miktex", (
        "if any(a.startswith('-fmt=') for a in sys.argv[1:]):\n"
        "    sys.stderr.write('pdflatex: The memory dump file could not be found.\\n'); sys.exit(1)\n"
        f"os.execv({real!r}, [{real!r}] + sys.argv[1:])"))
    monkeypatch.setenv("DOCSLAB_PDFLATEX", exe)
    monkeypatch.setattr(C, "_FORMATOS_MALOS", set())
    monkeypatch.setattr(C, "_FALLOS_FORMATO", {})
    d = tmp_path / "p"
    d.mkdir()
    tex, _ = G.generar(M.normalizar(M.desde_asistente({"tamano": "A4", "columnas": 1})))
    (d / "poster.tex").write_text(tex, encoding="utf-8")
    fmt = tmp_path / "pcposter-viejo"
    fmt.with_suffix(".fmt").write_bytes(b"formato")
    r = C.compilar(d, "poster.tex", hacer_miniatura=False, formato=str(fmt), max_pasadas=2)
    assert r["ok"], r.get("errores")
    assert r["formato"] is False and not fmt.with_suffix(".fmt").exists()
    assert C._FALLOS_FORMATO == {"viejo": 1} and "viejo" not in C._FORMATOS_MALOS
