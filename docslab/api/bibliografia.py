# SPDX-License-Identifier: AGPL-3.0-only
"""Referencias: formatear, vista previa, importar (BibTeX, RIS, CSL-JSON), DOI y exportar .bib."""
from __future__ import annotations

import io
from pathlib import Path
from flask import Blueprint, jsonify, request, send_file
from ..nucleo import almacen as A
from ..documento import bibliografia as B, generador

RAIZ_APP = Path(__file__).resolve().parents[2]
ESTATICO = RAIZ_APP / "static"


def registrar(app, c):
    """Registra en «app» las rutas de esta área; «c» trae los objetos compartidos."""
    bp = Blueprint('bibliografia', __name__)
    alm, json_body = c.alm, c.json_body

    # ------------------------------------------------------------------ bibliografía
    @bp.post("/api/bibliografia/formatear")
    def bib_formatear():
        d = json_body()
        estilo, idioma = d.get("estilo") or "apa", d.get("idioma") or "es"
        refs = d.get("referencias") if isinstance(d.get("referencias"), list) else []
        return jsonify({"entradas": B.formatear(refs, estilo, idioma), "ejemplo": B.ejemplo_cita(estilo, idioma)})

    @bp.post("/api/bibliografia/vista")
    def bibliografia_vista():
        d = json_body()
        if not isinstance(d.get("modelo"), dict):
            return jsonify({"error": "Falta el modelo del póster"}), 400
        return jsonify(generador.vista_bibliografia(d["modelo"]))

    @bp.post("/api/bibliografia/importar")
    def bib_importar():
        f = request.files.get("archivo")
        if f:
            texto = f.read().decode("utf-8-sig", "replace")
        else:
            texto = str(json_body().get("texto") or "")
        refs, errores = B.importar_texto(texto)
        return jsonify({"referencias": refs, "errores": errores})

    @bp.get("/api/bibliografia/doi")
    def bib_doi():
        try:
            return jsonify({"referencia": B.buscar_doi(request.args.get("doi", ""))})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.get("/api/proyectos/<pid>/bibliografia.bib")
    def bib_exportar(pid):
        meta = alm.meta(pid)
        refs = alm.leer_modelo(pid).get("bibliografia", {}).get("referencias", []) if meta["tipo"] == "estructurado" else []
        nombre = A.limpiar_nombre(meta["nombre"], "referencias") + ".bib"
        return send_file(io.BytesIO(B.a_bibtex(refs).encode("utf-8")), mimetype="application/x-bibtex",
                         as_attachment=True, download_name=nombre)

    app.register_blueprint(bp)
