# SPDX-License-Identifier: AGPL-3.0-only
"""Copias de seguridad automáticas (docslab/nucleo/copias.py)."""
import os
import time
import zipfile

import pytest

from docslab.nucleo import almacen as A
from docslab.nucleo.copias import Copias


@pytest.fixture
def datos(tmp_path):
    alm = A.Almacen(tmp_path / "datos")
    pid = alm.crear_proyecto("Copia")["id"]
    d = alm.dir_proyecto(pid)
    (d / "build").mkdir(exist_ok=True)
    (d / "build" / "poster.pdf").write_bytes(b"%PDF regenerable")
    (tmp_path / "datos" / "formatos").mkdir()
    (tmp_path / "datos" / "formatos" / "x.fmt").write_bytes(b"cache")
    (tmp_path / "datos" / "componentes").mkdir()
    (tmp_path / "datos" / "componentes" / "c-1.json").write_text("{}")
    return tmp_path / "datos", pid


def test_copia_con_lo_importante_y_sin_lo_regenerable(datos):
    raiz, pid = datos
    c = Copias(raiz, conservar=3, horas=24)
    zipf = c.hacer()
    assert zipf and zipf.parent == raiz / "copias" and zipf.name.startswith("docslab-copia-")
    nombres = zipfile.ZipFile(zipf).namelist()
    assert f"proyectos/{pid}/modelo.json" in nombres and "componentes/c-1.json" in nombres
    assert not any("/build/" in n or n.startswith(("formatos/", "copias/")) for n in nombres)
    assert not list((raiz / "copias").glob("*.parcial"))


def test_rota_y_conserva_las_mas_recientes(datos):
    raiz, _ = datos
    c = Copias(raiz, conservar=2, horas=24)
    hechas = [c.hacer() for _ in range(4)]
    assert c.lista() == sorted(hechas)[-2:]


def test_solo_cuando_toca_y_si_algo_cambio(datos):
    raiz, pid = datos
    c = Copias(raiz, conservar=5, horas=24)
    assert c.hace_falta()                       # no hay ninguna
    u = c.hacer()
    assert not c.hace_falta()                   # recién hecha
    viejo = time.time() - 25 * 3600
    os.utime(u, (viejo, viejo))
    for p, _ in c.archivos():                   # nada cambió desde entonces
        os.utime(p, (viejo - 10, viejo - 10))
    assert not c.hace_falta()
    (raiz / "proyectos" / pid / "modelo.json").touch()
    assert c.hace_falta()


def test_desactivadas_y_carpeta_propia(datos, tmp_path, monkeypatch):
    raiz, _ = datos
    monkeypatch.setenv("DOCSLAB_COPIAS", "0")
    c = Copias(raiz)
    assert c.hacer() is None and not c.hace_falta() and "desactivadas" in c.resumen()
    monkeypatch.setenv("DOCSLAB_COPIAS", "4")
    monkeypatch.setenv("DOCSLAB_COPIAS_DIR", str(tmp_path / "otro-disco"))
    c = Copias(raiz)
    assert c.conservar == 4 and c.hacer().parent == (tmp_path / "otro-disco").resolve()


def test_un_fallo_no_tumba_el_servidor(datos, monkeypatch):
    raiz, _ = datos
    c = Copias(raiz, conservar=2)
    monkeypatch.setattr(c, "hacer", lambda: (_ for _ in ()).throw(OSError("disco lleno")))
    assert c.si_hace_falta() is None
