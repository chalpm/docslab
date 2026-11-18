# SPDX-License-Identifier: AGPL-3.0-only
"""LAB: cuadernos celda a celda (núcleos de Python) y ejecución completa de cuadernos."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from flask import Blueprint, Response, jsonify, request, send_file
from ..lab import cuadernos
from ..lab import nucleos as LAB

RAIZ_APP = Path(__file__).resolve().parents[2]
ESTATICO = RAIZ_APP / "static"


def registrar(app, c):
    """Registra en «app» las rutas de esta área; «c» trae los objetos compartidos."""
    bp = Blueprint('lab', __name__)
    alm, trabajos, raices, json_body, sin_cache, archivos_subidos, lab = (
        c.alm, c.trabajos, c.raices, c.json_body, c.sin_cache, c.archivos_subidos, c.lab)

    # ------------------------------------------------------------------ LAB: cuadernos celda a celda

    @bp.get("/api/proyectos/<pid>/lab/<nb>")
    def lab_cuaderno(pid, nb):
        return sin_cache(jsonify(lab.sesion(pid, nb).como_dict()))

    @bp.put("/api/proyectos/<pid>/lab/<nb>")
    def lab_guardar(pid, nb):
        s = lab.sesion(pid, nb)
        s.guardar(json_body().get("celdas"))
        return jsonify({"ok": True, "rev": s.rev})

    @bp.get("/api/proyectos/<pid>/lab/<nb>/estado")
    def lab_estado(pid, nb):
        try:
            desde = int(request.args.get("rev", 0))
        except ValueError:
            desde = 0
        return sin_cache(jsonify(lab.sesion(pid, nb).cambios(desde)))

    @bp.post("/api/proyectos/<pid>/lab/<nb>/ejecutar")
    def lab_ejecutar(pid, nb):
        if importlib.util.find_spec("nbclient") is None:      # lo mismo que «cuadernos» en /api/estado
            return jsonify({"error": "Para ejecutar código hace falta nbclient e ipykernel "
                                     "(pip install nbclient ipykernel)"}), 400
        d = json_body()
        s = lab.sesion(pid, nb)
        if isinstance(d.get("celdas"), list):
            s.guardar(d["celdas"])
        if d.get("reiniciar"):
            s.reiniciar()
        ids = d.get("ids")
        s.ejecutar(None if d.get("todas") else [str(i) for i in ids] if isinstance(ids, list) else [])
        return jsonify(s.cambios(0) if d.get("reiniciar") else {"nucleo": s.estado_nucleo(), "rev": s.rev})

    @bp.post("/api/proyectos/<pid>/lab/<nb>/<accion>")
    def lab_accion(pid, nb, accion):
        s = lab.sesion(pid, nb)
        if accion == "interrumpir":
            s.interrumpir()
        elif accion == "reiniciar":
            s.reiniciar()
        elif accion == "borrar-variables":
            s.borrar_variables()
        elif accion == "limpiar":
            s.limpiar_salidas()
        elif accion == "ejemplo":
            return jsonify({"archivo": lab.copiar_ejemplo(pid, nb, json_body().get("archivos"))})
        elif accion == "variables":
            return jsonify({"variables": s.consulta(LAB.CONSULTA_VARIABLES)})
        elif accion == "columnas":
            return jsonify(s.consulta(LAB._exp_columnas(LAB.expresion_datos(json_body().get("datos") or {}))))
        else:
            return jsonify({"error": "Acción desconocida"}), 404
        return jsonify(s.cambios(0))

    @bp.get("/api/lab/plotly.min.js")
    def lab_plotly():
        import importlib.util
        spec = importlib.util.find_spec("plotly")
        p = Path(spec.origin).parent / "package_data" / "plotly.min.js" if spec and spec.origin else None
        if not p or not p.exists():
            return jsonify({"error": "plotly no está instalado"}), 404
        return send_file(p, mimetype="text/javascript", max_age=86400)

    # ------------------------------------------------------------------ cuadernos
    @bp.get("/api/proyectos/<pid>/cuadernos")
    def lista_cuadernos(pid):
        meta = alm.meta(pid)
        salida = []
        for c in meta.get("cuadernos", []):
            c = dict(c)
            activos = trabajos.activos(pid, "cuaderno:" + c["id"])
            c["trabajo"] = activos[0].id if activos else None
            salida.append(c)
        return sin_cache(jsonify(salida))

    @bp.post("/api/proyectos/<pid>/cuadernos")
    def cuaderno_nuevo(pid):
        if request.is_json:
            if "nuevo" in json_body():                       # un cuaderno vacío, para escribirlo en el LAB
                return jsonify(LAB.crear_cuaderno(alm, pid, str(json_body().get("nuevo") or "")))
            ruta = json_body().get("ruta", "")
            return jsonify(cuadernos.enlazar_ruta(alm, pid, ruta, raices))
        f = request.files.get("cuaderno")
        if not f:
            return jsonify({"error": "Falta el archivo .ipynb"}), 400
        return jsonify(cuadernos.agregar_subido(alm, pid, f.filename or "cuaderno.ipynb", f.read(),
                                                archivos_subidos("datos")))

    @bp.patch("/api/proyectos/<pid>/cuadernos/<nb>")
    def cuaderno_cambiar(pid, nb):
        return jsonify(cuadernos.configurar(alm, pid, nb, json_body()))

    @bp.delete("/api/proyectos/<pid>/cuadernos/<nb>")
    def cuaderno_borrar(pid, nb):
        lab.cerrar(pid, nb)
        cuadernos.borrar(alm, pid, nb, request.args.get("figuras") == "1")
        return jsonify({"ok": True})

    @bp.get("/api/proyectos/<pid>/cuadernos/<nb>/celdas")
    def cuaderno_celdas(pid, nb):
        return jsonify(cuadernos.celdas(alm, pid, nb))

    @bp.get("/api/proyectos/<pid>/cuadernos/<nb>/archivos")
    def cuaderno_archivos(pid, nb):
        return sin_cache(jsonify(cuadernos.listar_archivos(alm, pid, nb)))

    @bp.post("/api/proyectos/<pid>/cuadernos/<nb>/datos")
    def cuaderno_datos(pid, nb):
        return jsonify({"archivos": cuadernos.agregar_datos(alm, pid, nb, archivos_subidos("datos"))})

    @bp.post("/api/proyectos/<pid>/cuadernos/<nb>/ejecutar")
    def cuaderno_ejecutar(pid, nb):
        meta = alm.meta(pid)
        c = next((x for x in meta.get("cuadernos", []) if x.get("id") == nb), None)
        if not c:
            return jsonify({"error": "Cuaderno no encontrado"}), 404
        activos = trabajos.activos(pid, "cuaderno:" + nb)
        if activos:
            return jsonify(activos[0].como_dict(False))
        t = trabajos.lanzar("cuaderno:" + nb, pid, lambda t: cuadernos.ejecutar(alm, pid, nb, t),
                            f"Ejecutar {c.get('nombre')}", exclusivo="cuaderno")
        return jsonify(t.como_dict(False))

    @bp.post("/api/proyectos/<pid>/cuadernos/<nb>/importar")
    def cuaderno_importar(pid, nb):
        f = request.files.get("archivo")
        if not f:
            return jsonify({"error": "Falta el zip"}), 400
        return jsonify({"figuras": cuadernos.importar_zip(alm, pid, nb, f.read())})

    @bp.get("/api/proyectos/<pid>/cuadernos/<nb>/figuras")
    def cuaderno_figuras(pid, nb):
        return sin_cache(jsonify(cuadernos.figuras(alm, pid, nb)))

    @bp.get("/api/proyectos/<pid>/cuadernos/<nb>/celda-colab")
    def cuaderno_celda(pid, nb):
        return Response(cuadernos.celda_exportar(alm, pid, nb), mimetype="text/plain; charset=utf-8")

    @bp.get("/api/proyectos/<pid>/cuadernos/<nb>/ejecutado")
    def cuaderno_ejecutado(pid, nb):
        p = alm.dir_proyecto(pid) / "cuadernos" / nb / "ejecutado.ipynb"
        if not p.exists():
            return jsonify({"error": "Aún no se ha ejecutado"}), 404
        return send_file(p, mimetype="application/x-ipynb+json", as_attachment=True,
                         download_name=f"{nb}-ejecutado.ipynb")

    @bp.get("/api/explorar")
    def explorar():
        return jsonify(cuadernos.explorar(request.args.get("ruta", ""), raices))

    app.register_blueprint(bp)
