# SPDX-License-Identifier: AGPL-3.0-only
"""Versión mínima de Python: requirements, servidor y lanzador de macOS/Linux (ver docslab.PYTHON_MINIMO)."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import docslab

RAIZ = Path(__file__).resolve().parent.parent
sin_sh = pytest.mark.skipif(os.name == "nt" or shutil.which("sh") is None, reason="necesita sh (macOS o Linux)")


def test_python_minimo_es_3_11():
    assert docslab.PYTHON_MINIMO == (3, 11)
    assert sys.version_info[:2] >= docslab.PYTHON_MINIMO


def test_requirements_sin_marcadores_de_python_antiguo():
    req = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
    assert "3.11 o posterior" in req.splitlines()[0]
    assert "python_version" not in req
    assert any(l.startswith("pillow>=13.0") for l in req.splitlines())


def test_el_servidor_se_niega_con_un_python_antiguo(monkeypatch, capsys):
    sys.path.insert(0, str(RAIZ))
    import servidor
    assert servidor.python_valido((3, 11, 0)) and servidor.python_valido((3, 13, 1))
    assert not servidor.python_valido((3, 10, 12)) and not servidor.python_valido((3, 9, 18))
    monkeypatch.setattr(servidor, "python_valido", lambda version=None: False)
    assert servidor.main([]) == 1
    assert "3.11 o posterior" in capsys.readouterr().err


def _falso(carpeta: Path, nombre: str, version: str) -> None:
    """Un «python» de mentira: responde a la comprobación de versión y falla al crear el entorno."""
    valido = tuple(int(x) for x in version.split(".")[:2]) >= (3, 11)
    p = carpeta / nombre
    p.write_text(f"""#!/bin/sh
case "$*" in
  *"version_info < (3, 11)"*) exit {0 if valido else 1};;
  *python_version*) echo {version}; exit 0;;
  *) exit 1;;
esac
""")
    p.chmod(0o755)


def _lanzar(tmp_path, pythons: dict, entorno=None, venv_viejo=False):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for herramienta in ("dirname", "cmp", "cp", "cat"):
        if shutil.which(herramienta):
            (bin_ / herramienta).symlink_to(shutil.which(herramienta))
    for nombre, version in pythons.items():
        _falso(bin_, nombre, version)
    app = tmp_path / "app"
    app.mkdir()
    shutil.copy(RAIZ / "iniciar.command", app)
    shutil.copy(RAIZ / "requirements.txt", app)
    if venv_viejo:                       # un .venv que se creó con Python 3.10 (antes de 1.7.0)
        (app / ".venv" / "bin").mkdir(parents=True)
        _falso(app / ".venv" / "bin", "python", "3.10.12")
    env = {"PATH": str(bin_), "HOME": str(tmp_path), **(entorno or {})}
    return subprocess.run([shutil.which("sh"), str(app / "iniciar.command")], capture_output=True, text=True,
                          env=env, timeout=30)


@sin_sh
def test_lanzador_rechaza_python_3_10(tmp_path):
    r = _lanzar(tmp_path, {"python3": "3.10.12"})
    assert r.returncode == 1
    assert "3.11 o posterior" in r.stdout and "3.10.12" in r.stdout and "python3.11-venv" in r.stdout


@sin_sh
def test_lanzador_sin_python(tmp_path):
    r = _lanzar(tmp_path, {})
    assert r.returncode == 1 and "No encuentro Python 3" in r.stdout


@sin_sh
def test_lanzador_busca_un_python_mas_nuevo(tmp_path):
    # python3 es 3.10, pero hay python3.12: debe usarlo (aquí falla después, al crear .venv, a propósito)
    r = _lanzar(tmp_path, {"python3": "3.10.12", "python3.12": "3.12.3"})
    assert "con python3.12" in r.stdout and "No se pudo crear el entorno" in r.stdout


@sin_sh
def test_lanzador_respeta_docslab_python(tmp_path):
    r = _lanzar(tmp_path, {"python3": "3.12.3", "mipython": "3.10.1"}, {"DOCSLAB_PYTHON": "mipython"})
    assert r.returncode == 1 and "3.10.1" in r.stdout


@sin_sh
def test_lanzador_rehace_un_venv_de_python_antiguo(tmp_path):
    r = _lanzar(tmp_path, {"python3": "3.12.3"}, venv_viejo=True)
    assert "Preparando DocsLab" in r.stdout and "No se pudo crear el entorno" in r.stdout
