# SPDX-License-Identifier: AGPL-3.0-only
import shutil
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

hay_latex = pytest.mark.skipif(shutil.which("pdflatex") is None, reason="sin pdflatex")


def _hay_nucleo():
    try:
        import importlib.util
        if importlib.util.find_spec("nbclient") is None:
            return False
        from jupyter_client.kernelspec import find_kernel_specs
        return bool(find_kernel_specs())
    except Exception:
        return False


hay_nucleo = pytest.mark.skipif(not _hay_nucleo(), reason="sin nbclient o sin núcleo de Jupyter")


@pytest.fixture
def cliente(tmp_path):
    from docslab.app import crear_app
    raiz = tmp_path / "raiz"
    raiz.mkdir()
    app = crear_app(tmp_path / "datos", [raiz])
    app.config["TESTING"] = True
    c = app.test_client()
    c.environ_base["HTTP_X_DOCSLAB"] = "1"     # la cabecera que pone la interfaz (ver docslab/seguridad.py)
    c.raiz = raiz
    c.app = app
    return c
