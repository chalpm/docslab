# SPDX-License-Identifier: AGPL-3.0-only
"""Componente Lab: biblioteca de componentes propios, vista previa, importar y exportar."""
from __future__ import annotations

import io
from pathlib import Path
from flask import Blueprint, jsonify, request, send_file
from ..nucleo import almacen as A
from ..documento import componentes as CP
from ..salidas import compilador

RAIZ_APP = Path(__file__).resolve().parents[2]
ESTATICO = RAIZ_APP / "static"


def registrar(app, c):
    """Registra en «app» las rutas de esta área; «c» trae los objetos compartidos."""
    bp = Blueprint('componentes', __name__)
    json_body, sin_cache, biblio = c.json_body, c.sin_cache, c.biblio

    # ------------------------------------------------------------------ Componente Lab

    def _error_valor(fn):
        try:
            return fn()
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.get("/api/componentes")
    def componentes():
        return sin_cache(jsonify(biblio.listar()))

    @bp.post("/api/componentes")
    def componente_nuevo():
        d = json_body()
        if isinstance(d.get("componente"), dict):
            return jsonify(biblio.crear(d["componente"], conservar_id=bool(d.get("conservar_id"))))
        return jsonify(biblio.crear(d))

    @bp.get("/api/componentes/<cid>")
    def componente(cid):
        return _error_valor(lambda: sin_cache(jsonify(biblio.leer(cid))))

    @bp.put("/api/componentes/<cid>")
    def componente_guardar(cid):
        return _error_valor(lambda: jsonify(biblio.guardar(cid, json_body())))

    @bp.delete("/api/componentes/<cid>")
    def componente_borrar(cid):
        return _error_valor(lambda: (biblio.borrar(cid), jsonify({"ok": True}))[1])

    @bp.post("/api/componentes/<cid>/duplicar")
    def componente_duplicar(cid):
        return _error_valor(lambda: jsonify(biblio.duplicar(cid)))

    @bp.post("/api/componentes/recrear")
    def componente_recrear():
        """Un borrador (sin guardar, sin id) para recrear uno de los incluidos."""
        d = json_body()

        def borrador():
            c = CP.desde_variante(str(d.get("clave") or ""), "preajuste" if d.get("modo") == "preajuste" else "latex")
            for k in ("id", "version", "creado", "modificado"):
                c.pop(k, None)
            return jsonify(c)
        return _error_valor(borrador)

    @bp.post("/api/componentes/codigo")
    def componente_codigo():
        """El LaTeX de un componente (para «Ver el código» y «Pasar a código»)."""
        c = CP.normalizar(json_body())
        codigo, pre = CP.codigo_de(c) if c["modo"] != CP.PREAJUSTE else ("", "")
        return jsonify({"codigo": codigo, "preambulo": pre, "campos": c["campos"], "como_latex": CP.a_codigo(c)})

    @bp.post("/api/componentes/vista")
    def componente_vista():
        d = json_body()
        datos = d.get("componente") if isinstance(d.get("componente"), dict) else {}
        if not compilador.pdflatex():
            return jsonify({"ok": False, "errores": [{"mensaje": "No se encontró pdflatex: instala TeX Live para ver la vista previa."}]})
        r = CP.compilar_vista(datos, biblio.raiz, str(d.get("tema") or "pizarra"), str(d.get("ancho") or "media"),
                              bool(d.get("en_caja")), d.get("valores") if isinstance(d.get("valores"), dict) else None)
        cid = d.get("miniatura_de")
        if r.get("ok") and CP.es_id(cid) and (biblio.raiz / f"{cid}.json").exists():
            CP.miniatura_desde_vista(biblio.raiz, r["huella"], biblio.raiz / f"{cid}.png")
        if r.get("ok"):
            r["pdf"] = f"api/componentes/vistas/{r['huella']}.pdf"
        return jsonify(r)

    @bp.get("/api/componentes/vistas/<h>.pdf")
    def componente_vista_pdf(h):
        p = CP.pdf_vista(biblio.raiz, h)
        if not p:
            return jsonify({"error": "La vista previa ya no está: vuelve a generarla"}), 404
        return send_file(p, mimetype="application/pdf", max_age=3600)

    @bp.get("/api/componentes/<cid>/miniatura")
    def componente_miniatura(cid):
        if not CP.es_id(cid) or not (biblio.raiz / f"{cid}.png").exists():
            return jsonify({"error": "sin miniatura"}), 404
        return sin_cache(send_file(biblio.raiz / f"{cid}.png", mimetype="image/png"))

    @bp.get("/api/componentes/exportar")
    def componentes_exportar():
        ids = [x for x in request.args.get("ids", "").split(",") if CP.es_id(x)]
        texto = _error_valor(lambda: biblio.exportar(ids or None))
        if not isinstance(texto, str):
            return texto
        nombre = "componentes-docslab.json" if len(ids) != 1 else \
            A.limpiar_nombre(biblio.leer(ids[0]).get("nombre"), "componente") + ".json"
        return send_file(io.BytesIO(texto.encode("utf-8")), mimetype="application/json", as_attachment=True,
                         download_name=nombre)

    @bp.post("/api/componentes/importar")
    def componentes_importar():
        f = request.files.get("archivo")
        texto = f.read().decode("utf-8-sig", "replace") if f else str(json_body().get("texto") or "")
        return _error_valor(lambda: jsonify([CP.resumen(c) for c in biblio.importar(texto)]))

    app.register_blueprint(bp)
