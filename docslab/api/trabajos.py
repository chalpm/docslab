# SPDX-License-Identifier: AGPL-3.0-only
"""Trabajos en segundo plano: estado, registro y cancelación."""
from __future__ import annotations

from pathlib import Path
from flask import Blueprint, jsonify, request

RAIZ_APP = Path(__file__).resolve().parents[2]
ESTATICO = RAIZ_APP / "static"


def registrar(app, c):
    """Registra en «app» las rutas de esta área; «c» trae los objetos compartidos."""
    bp = Blueprint('trabajos', __name__)
    trabajos, sin_cache = c.trabajos, c.sin_cache

    # ------------------------------------------------------------------ trabajos
    @bp.get("/api/proyectos/<pid>/trabajos")
    def trabajos_proyecto(pid):
        return sin_cache(jsonify([t.como_dict(False) for t in trabajos.listar(pid)[:30]]))

    @bp.get("/api/trabajos/<tid>")
    def trabajo(tid):
        t = trabajos.obtener(tid)
        if not t:
            return jsonify({"error": "Trabajo no encontrado"}), 404
        return sin_cache(jsonify(t.como_dict(request.args.get("registro", "1") == "1")))

    @bp.post("/api/trabajos/<tid>/cancelar")
    def trabajo_cancelar(tid):
        return jsonify({"ok": trabajos.cancelar(tid)})

    app.register_blueprint(bp)
