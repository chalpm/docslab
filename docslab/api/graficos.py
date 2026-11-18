# SPDX-License-Identifier: AGPL-3.0-only
"""LAB: plantillas de gráficos (catálogo, guardar, generar código y probar)."""
from __future__ import annotations

from pathlib import Path
from flask import Blueprint, jsonify, send_file
from ..nucleo import almacen as A
from ..lab import graficos as GR

RAIZ_APP = Path(__file__).resolve().parents[2]
ESTATICO = RAIZ_APP / "static"


def registrar(app, c):
    """Registra en «app» las rutas de esta área; «c» trae los objetos compartidos."""
    bp = Blueprint('graficos', __name__)
    json_body, sin_cache, graficos = c.json_body, c.sin_cache, c.graficos

    # ------------------------------------------------------------------ LAB: plantillas de gráficos
    @bp.get("/api/graficos")
    def graficos_lista():
        lista = graficos.listar()
        for t in lista:
            t["miniatura"] = (f"static/img/graficos/{t['id']}.png" if t.get("incluida")
                              else (f"api/graficos/{t['id']}/miniatura?v={t.get('modificado', '')}"
                                    if graficos.miniatura(t["id"]) else ""))
            if t.get("incluida"):
                t["ejemplo"] = GR.archivos_ejemplo(t)
        return sin_cache(jsonify({"plantillas": lista, "tipos": list(GR.TIPOS), "bibliotecas": list(GR.BIBLIOTECAS),
                                  "categorias": GR.CATEGORIAS,
                                  "paletas": GR.PALETAS, "nueva": GR.normalizar(GR.NUEVA)}))

    @bp.post("/api/graficos")
    def graficos_guardar():
        return jsonify(graficos.guardar(json_body()))

    @bp.delete("/api/graficos/<gid>")
    def graficos_borrar(gid):
        graficos.borrar(gid)
        return jsonify({"ok": True})

    @bp.get("/api/graficos/<gid>/miniatura")
    def graficos_miniatura(gid):
        p = graficos.miniatura(gid)
        if not p:
            return jsonify({"error": "Sin miniatura"}), 404
        return send_file(p, mimetype="image/png", max_age=0)

    @bp.post("/api/graficos/generar")
    def graficos_generar():
        d = json_body()
        t = d.get("plantilla") if isinstance(d.get("plantilla"), dict) else graficos.obtener(str(d.get("id") or ""))
        return jsonify({"codigo": GR.generar(t, d.get("valores") or {}, d.get("colores") or {})})

    @bp.post("/api/graficos/probar")
    def graficos_probar():
        d = json_body()
        t = d.get("plantilla") if isinstance(d.get("plantilla"), dict) else graficos.obtener(str(d.get("id") or ""))
        r = GR.probar(GR.generar(t, d.get("valores") or {}, d.get("colores") or {}))
        gid = str(t.get("id") or "")
        if r.get("imagen") and gid.startswith("g-") and d.get("guardar_miniatura"):
            import base64
            try:
                graficos.guardar_miniatura(gid, base64.b64decode(r["imagen"].split(",", 1)[1]))
            except A.ErrorAlmacen:
                pass
        return jsonify(r)

    app.register_blueprint(bp)
