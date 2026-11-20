# SPDX-License-Identifier: AGPL-3.0-only
"""Higiene del repositorio: sin claves en el código, errores sin detalles internos y sin código sin usar."""
import logging
import re
import subprocess
import time
from pathlib import Path

import pytest

from docslab.nucleo.almacen import ErrorAlmacen
from docslab.nucleo.trabajos import GestorTrabajos, mensaje_para_usuario

RAIZ = Path(__file__).resolve().parent.parent

# Patrones de secretos conocidos (partidos para que este archivo no se encuentre a sí mismo)
PATRONES = {
    "clave privada": "-----BEGIN " + r"(RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY",
    "AWS": "AK" + r"IA[0-9A-Z]{16}",
    "GitHub": r"(gh[pousr]_[A-Za-z0-9]{36}|github_" + r"pat_[A-Za-z0-9_]{40,})",
    "Slack": r"xox[baprs]-[A-Za-z0-9-]{10,}",
    "Google": "AI" + r"za[0-9A-Za-z_-]{35}",
    "OpenAI/Anthropic": r"sk-(ant-)?[A-Za-z0-9_-]{32,}",
    "Stripe": r"[sr]k_live_[0-9A-Za-z]{20,}",
    "asignación de secreto": r"(?i)\b(api[_-]?key|secret[_-]?key|client[_-]?secret|access[_-]?token|passwd|password)"
                             r"\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']",
}
TEXTO = {".py", ".js", ".mjs", ".css", ".html", ".md", ".json", ".ipynb", ".txt", ".sty", ".tex", ".bat",
         ".command", ".ini", ".cfg", ".toml", ".yml", ".yaml", ".csv", ".bib", ".env", ""}


def _archivos():
    try:
        nombres = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.split()
        return [RAIZ / n for n in nombres]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in RAIZ.rglob("*") if p.is_file() and ".git" not in p.parts and ".venv" not in p.parts]


def test_ninguna_clave_en_el_repositorio():
    hallazgos = []
    for p in _archivos():
        if p.suffix.lower() not in TEXTO or not p.is_file() or p.stat().st_size > 5_000_000:
            continue
        texto = p.read_text(encoding="utf-8", errors="ignore")
        for nombre, patron in PATRONES.items():
            for m in re.finditer(patron, texto):
                hallazgos.append(f"{p.relative_to(RAIZ)}: {nombre} → {m.group(0)[:24]}…")
    assert not hallazgos, "\n".join(hallazgos)


def test_no_hay_archivos_de_secretos_en_el_repositorio():
    prohibidos = re.compile(r"(^|/)(\.env(\..*)?|.*\.(pem|key|p12|pfx)|id_(rsa|ed25519)|credentials\.json)$")
    nombres = [str(p.relative_to(RAIZ)) for p in _archivos()]
    assert [n for n in nombres if prohibidos.search(n)] == []


def test_mensajes_de_error_para_el_usuario():
    assert mensaje_para_usuario(ValueError("El DOI no es válido")) == "El DOI no es válido"
    assert mensaje_para_usuario(ErrorAlmacen("Proyecto no encontrado")) == "Proyecto no encontrado"
    m = mensaje_para_usuario(KeyError("/home/ana/.venv/lib/python3.13/site-packages/x.py"))
    assert "terminal" in m and "/home" not in m and "KeyError" not in m


def test_un_fallo_inesperado_no_muestra_la_traza(caplog):
    g = GestorTrabajos()

    def falla(t):
        raise RuntimeError("detalle interno /ruta/secreta")

    with caplog.at_level(logging.ERROR, logger="docslab"):
        t = g.lanzar("prueba", "p-1", falla)
        for _ in range(250):                    # «fin» se pone al final, después de registrar el error
            if t.fin:
                break
            time.sleep(0.02)
    d = t.como_dict()
    texto = d["mensaje"] + "\n".join(d["registro"])
    assert d["estado"] == "error" and "Traceback" not in texto and "/ruta/secreta" not in texto
    assert "Traceback" in caplog.text or "detalle interno" in caplog.text     # la traza sí va a la terminal


def test_sin_codigo_sin_usar():
    """pyflakes (si está instalado): ni importaciones ni variables sin usar en el servidor."""
    pyflakes = pytest.importorskip("pyflakes.api")
    from pyflakes import reporter as R
    import io
    salida = io.StringIO()
    total = pyflakes.checkRecursive([str(RAIZ / "docslab"), str(RAIZ / "servidor.py"), str(RAIZ / "herramientas")],
                                    R.Reporter(salida, salida))
    assert total == 0, salida.getvalue()
