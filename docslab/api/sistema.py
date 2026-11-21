# SPDX-License-Identifier: AGPL-3.0-only
"""Página de la aplicación, archivos estáticos, estado del servidor y catálogo de variantes."""
from __future__ import annotations

import importlib.util
import platform
import sys
from pathlib import Path
from flask import Blueprint, jsonify, send_from_directory
from .. import __license__, __license_sty__, __version__
from ..documento import bibliografia as B, componentes as CP
from ..salidas import compilador
from ..nucleo import modelo as M
from ..salidas import powerpoint as PP, revision, word as W
from ..documento import variantes as V

RAIZ_APP = Path(__file__).resolve().parents[2]
ESTATICO = RAIZ_APP / "static"


def registrar(app, c):
    """Registra en «app» las rutas de esta área; «c» trae los objetos compartidos."""
    bp = Blueprint('sistema', __name__)
    alm, raices, colab, sin_cache = c.alm, c.raices, c.colab, c.sin_cache

    # ------------------------------------------------------------------ estáticos
    @bp.get("/")
    def inicio():
        return sin_cache(send_from_directory(ESTATICO, "index.html"))

    @bp.get("/static/<path:ruta>")
    def estatico(ruta):
        # El tipo MIME se fija aquí: con «nosniff», un .js o .mjs servido como text/plain (pasa en Windows
        # cuando el registro tiene mal la extensión) no se ejecutaría.
        tipo = {".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css"}.get(Path(ruta).suffix.lower())
        resp = send_from_directory(ESTATICO, ruta, mimetype=tipo) if tipo else send_from_directory(ESTATICO, ruta)
        if not ruta.startswith("vendor/"):
            resp.headers["Cache-Control"] = "no-cache"
        return resp

    # ------------------------------------------------------------------ estado
    def _familias_instaladas() -> dict:
        """Qué tipografías libres de TeX Live están instaladas (None si no se puede saber)."""
        libres = {k: f"{v['paquete']}.sty" for k, v in M.FAMILIAS_INFO.items() if v.get("paquete")}
        hay = compilador.existen_tex(list(libres.values()))
        return {k: hay.get(v) for k, v in libres.items()}

    @bp.get("/api/estado")
    def estado():
        nb_ok = importlib.util.find_spec("nbclient") is not None
        pil_ok = importlib.util.find_spec("PIL") is not None
        return jsonify({
            "version": __version__, "licencia": __license__, "licencia_sty": __license_sty__, "pdflatex": compilador.pdflatex(), "tex": compilador.version_tex(),
            "miktex": compilador.es_miktex(),
            "pdftoppm": bool(compilador.pdftoppm()), "cuadernos": nb_ok, "pillow": pil_ok,
            "ghostscript": bool(compilador.ghostscript()), "poppler": revision.herramientas(),
            "powerpoint": PP.disponible(),
            "word": W.disponible(),
            "lualatex": bool(compilador.lualatex()), "familias": _familias_instaladas(),
            "colab": colab, "raices": [str(r) for r in raices], "datos": str(alm.datos),
            "python": sys.version.split()[0], "python_exe": sys.executable, "sistema": platform.system(),
            "idiomas": {k: compilador.existe_tex(v["babel"] + ".ldf") is not False for k, v in M.IDIOMAS.items()},
        })

    @bp.get("/api/variantes")
    def lista_variantes():
        return jsonify({"variantes": V.VARIANTES, "grupos": V.GRUPOS, "estilos_caja": V.ESTILOS_CAJA,
                        "temas": M.TEMAS, "grupos_temas": M.GRUPOS_TEMAS, "familias": M.FAMILIAS,
                        "familias_info": M.FAMILIAS_INFO, "tamanos": M.TAMANOS,
                        "idiomas": M.IDIOMAS, "clases": M.CLASES, "disenos_pagina": M.DISENOS_PAGINA,
                        "estilos_titulo_pagina": M.ESTILOS_TITULO_PAGINA, "niveles": M.NIVELES,
                        "pagina_defecto": M.PAGINA_DEFECTO, "libre_defecto": M.LIBRE_DEFECTO,
                        "bibliografia": {"estilos": B.ESTILOS, "tipos": B.TIPOS, "campos": B.CAMPOS_TIPO,
                                         "etiquetas": B.ETIQUETAS_CAMPO},
                        "estilos_cabecera": M.ESTILOS_CABECERA, "estilos_pie": M.ESTILOS_PIE,
                        "formas": M.FORMAS, "anclas": M.ANCLAS, "item_tipos": M.ITEM_TIPOS,
                        "componentes": {"tipos": CP.NOMBRES_TIPO, "piezas": CP.PIEZAS, "iconos": CP.ICONOS,
                                        "vinetas": list(CP.VINETAS), "defectos_pieza": CP.DEFECTOS_PIEZA,
                                        "tipo_campo_pieza": CP.TIPO_CAMPO_PIEZA, "caja": CP.CAJA_DEFECTO,
                                        "recrear": CP.catalogo_recrear(), "anchos_vista": list(CP.ANCHOS_VISTA)}})

    app.register_blueprint(bp)
