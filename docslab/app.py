# SPDX-License-Identifier: AGPL-3.0-only
"""Servidor web de DocsLab (Flask): crea la aplicación y registra las rutas de docslab/api/."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from flask import Flask, jsonify, request

from .nucleo import almacen as A
from .documento import componentes as CP
from .salidas import compilador
from .lab import graficos as GR, nucleos as LAB
from .nucleo.trabajos import GestorTrabajos
from . import seguridad
from .api import bibliografia, componentes, documento, plantillas, proyectos, sistema
from .api import graficos as api_graficos, lab as api_lab, trabajos as api_trabajos

# Una blueprint por área, en el orden en que se registran. Los alias evitan que choquen con los
# objetos compartidos que crear_app llama «lab», «graficos» y «trabajos».
AREAS = (sistema, componentes, bibliografia, plantillas, proyectos, documento, api_lab, api_graficos, api_trabajos)


def crear_app(datos: Path, raices: list[Path] | None = None, colab: bool = False) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.json.sort_keys = False          # conserva el orden (temas, tamaños…)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1 GB
    alm = A.Almacen(datos)
    compilador.DIR_FORMATOS = alm.datos / "formatos"
    trabajos = GestorTrabajos()
    raices = [Path(r).expanduser().resolve() for r in (raices or [])]
    app.config.update(ALMACEN=alm, TRABAJOS=trabajos, RAICES=raices, COLAB=colab)
    seguridad.proteger(app, colab)   # Host, cabecera X-DocsLab, Origin, cabeceras y errores en JSON

    # ------------------------------------------------------------------ utilidades
    @app.errorhandler(A.ErrorAlmacen)
    def _error_almacen(exc):
        return jsonify({"error": str(exc)}), 400

    @app.errorhandler(413)
    def _demasiado(exc):
        return jsonify({"error": "El archivo es demasiado grande"}), 413

    def json_body() -> dict:
        d = request.get_json(silent=True)
        return d if isinstance(d, dict) else {}

    def sin_cache(resp):
        resp.headers["Cache-Control"] = "no-store"
        return resp

    def archivos_subidos(campo: str) -> list[tuple[str, bytes]]:
        return [(f.filename or "archivo", f.read()) for f in request.files.getlist(campo) if f]

    # ------------------------------------------------------------------ objetos compartidos
    biblio = CP.Biblioteca(alm.datos / "componentes")
    app.config["BIBLIOTECA"] = biblio
    lab = LAB.Lab(alm)
    app.config["lab"] = lab
    graficos = GR.Graficos(alm.datos)

    # ------------------------------------------------------------------ rutas (docslab/api/)
    c = SimpleNamespace(alm=alm, trabajos=trabajos, raices=raices, colab=colab, json_body=json_body,
                        sin_cache=sin_cache, archivos_subidos=archivos_subidos, lab=lab, graficos=graficos,
                        biblio=biblio)
    for area in AREAS:
        area.registrar(app, c)
    return app
