# SPDX-License-Identifier: AGPL-3.0-only
"""Plantillas de documento: listar, guardar, actualizar, borrar, miniatura y exportar."""
from __future__ import annotations

import io
from pathlib import Path
from flask import Blueprint, jsonify, send_file

RAIZ_APP = Path(__file__).resolve().parents[2]
ESTATICO = RAIZ_APP / "static"


def registrar(app, c):
    """Registra en «app» las rutas de esta área; «c» trae los objetos compartidos."""
    bp = Blueprint('plantillas', __name__)
    alm, json_body = c.alm, c.json_body

    # ------------------------------------------------------------------ plantillas
    @bp.get("/api/plantillas")
    def plantillas():
        return jsonify(alm.listar_plantillas())

    @bp.post("/api/plantillas")
    def plantilla_nueva():
        d = json_body()
        return jsonify(alm.crear_plantilla(d.get("proyecto", ""), d.get("nombre", ""), d.get("descripcion", "")))

    @bp.patch("/api/plantillas/<tid>")
    def plantilla_cambiar(tid):
        return jsonify(alm.actualizar_plantilla(tid, json_body()))

    @bp.put("/api/plantillas/<tid>")
    def plantilla_reemplazar(tid):
        """Sustituye el contenido de una plantilla propia por el de un proyecto."""
        return jsonify(alm.reemplazar_plantilla(tid, json_body().get("proyecto", "")))

    @bp.delete("/api/plantillas/<tid>")
    def plantilla_borrar(tid):
        alm.borrar_plantilla(tid)
        return jsonify({"ok": True})

    @bp.get("/api/plantillas/<tid>/miniatura")
    def plantilla_miniatura(tid):
        p = alm.dir_plantilla(tid) / "miniatura.png"
        if not p.exists():
            return jsonify({"error": "sin miniatura"}), 404
        return send_file(p, mimetype="image/png", max_age=60)

    @bp.get("/api/plantillas/<tid>/exportar")
    def plantilla_exportar(tid):
        datos = alm.exportar_plantilla(tid)
        return send_file(io.BytesIO(datos), mimetype="application/zip", as_attachment=True,
                         download_name=f"plantilla-{tid}.zip")

    app.register_blueprint(bp)
