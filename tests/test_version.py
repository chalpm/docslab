"""Coherencia de versiones: evita que los ejes versionados se desincronicen (ver docs/VERSIONADO.md)."""
import json
import re
import subprocess
import sys
from pathlib import Path

import docslab
from docslab import modelo as M

RAIZ = Path(__file__).resolve().parent.parent
STY = RAIZ / "latex" / "postercientifico.sty"
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")


def test_versiones_semver():
    assert SEMVER.match(docslab.__version__)
    assert SEMVER.match(docslab.__version_sty__)


def test_version_sty_coincide_con_providespackage():
    m = re.search(r"\\ProvidesPackage\{postercientifico\}\[\S+ v([\d.]+)", STY.read_text(encoding="utf-8"))
    assert m and m.group(1) == docslab.__version_sty__


def test_copias_de_la_sty_en_plantillas_son_la_actual():
    for copia in (RAIZ / "plantillas").glob("*/postercientifico.sty"):
        assert copia.read_bytes() == STY.read_bytes(), f"{copia.parent.name}: regenerar con construir_plantillas.py"


def test_plantillas_usan_el_esquema_actual():
    for p in (RAIZ / "plantillas").glob("*/modelo.json"):
        assert json.loads(p.read_text(encoding="utf-8")).get("esquema") == M.ESQUEMA, p.parent.name


def test_version_en_el_changelog():
    assert f"## [{docslab.__version__}]" in (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")


def test_referencia_de_api_al_dia():
    r = subprocess.run([sys.executable, str(RAIZ / "herramientas" / "doc_api.py"), "--comprobar"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
