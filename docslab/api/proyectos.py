# SPDX-License-Identifier: AGPL-3.0-only
"""Proyectos: crear, importar, modelo, historial, modo LaTeX, archivos, tipografías y recursos."""
from __future__ import annotations

import hashlib
import mimetypes
import time
from pathlib import Path
from flask import Blueprint, Response, jsonify, request, send_file
from ..nucleo import almacen as A
from ..documento import generador
from ..salidas import compilador
from ..documento import fuentes as F
from ..nucleo import modelo as M

RAIZ_APP = Path(__file__).resolve().parents[2]
ESTATICO = RAIZ_APP / "static"


def registrar(app, c):
    """Registra en «app» las rutas de esta área; «c» trae los objetos compartidos."""
    bp = Blueprint('proyectos', __name__)
    alm, json_body, sin_cache, archivos_subidos, lab = c.alm, c.json_body, c.sin_cache, c.archivos_subidos, c.lab

    # ------------------------------------------------------------------ proyectos
    @bp.get("/api/proyectos")
    def proyectos():
        return jsonify(alm.listar_proyectos())

    @bp.post("/api/proyectos")
    def proyecto_nuevo():
        d = json_body()
        return jsonify(alm.crear_proyecto(d.get("nombre", ""), d.get("plantilla") or None, d.get("asistente")))

    @bp.post("/api/proyectos/importar")
    def proyecto_importar():
        f = request.files.get("archivo")
        if not f:
            return jsonify({"error": "Falta el archivo"}), 400
        return jsonify(alm.importar_zip(f.read(), request.form.get("nombre", "")))

    @bp.get("/api/proyectos/<pid>")
    def proyecto(pid):
        meta = alm.meta(pid)
        salida = {"meta": meta, "plantilla_propia": alm.plantilla_propia(meta)}
        if meta["tipo"] == "estructurado":
            salida["modelo"] = alm.leer_modelo(pid)
        return sin_cache(jsonify(salida))

    @bp.patch("/api/proyectos/<pid>")
    def proyecto_cambiar(pid):
        d = json_body()
        meta = alm.meta(pid)
        if "nombre" in d:
            meta["nombre"] = str(d["nombre"]).strip()[:150] or meta["nombre"]
        if isinstance(d.get("ajustes"), dict):
            meta["ajustes"].update(d["ajustes"])
        if "principal" in d and meta["tipo"] == "latex":
            meta["principal"] = A.limpiar_ruta(d["principal"]) or meta["principal"]
        alm.guardar_meta(pid, meta)
        return jsonify(meta)

    @bp.delete("/api/proyectos/<pid>")
    def proyecto_borrar(pid):
        lab.cerrar(pid)
        alm.borrar_proyecto(pid)
        return jsonify({"ok": True})

    @bp.post("/api/proyectos/<pid>/duplicar")
    def proyecto_duplicar(pid):
        return jsonify(alm.duplicar_proyecto(pid, json_body().get("nombre")))

    @bp.put("/api/proyectos/<pid>/modelo")
    def modelo_guardar(pid):
        d = request.get_json(silent=True)
        if not isinstance(d, dict):
            return jsonify({"error": "Modelo no válido"}), 400
        alm.guardar_modelo(pid, d)
        return jsonify({"ok": True, "guardado": time.time()})

    @bp.post("/api/proyectos/<pid>/formato")
    def formato_texto(pid):
        nuevo = json_body().get("formato")
        if nuevo not in ("simple", "latex"):
            return jsonify({"error": "Formato no válido"}), 400
        mod = M.convertir_formato(alm.leer_modelo(pid), nuevo)
        mod = alm.guardar_modelo(pid, mod)
        return jsonify({"modelo": mod})

    @bp.get("/api/proyectos/<pid>/historial")
    def historial(pid):
        return jsonify(alm.historial(pid))

    @bp.post("/api/proyectos/<pid>/historial/<nombre>/restaurar")
    def historial_restaurar(pid, nombre):
        return jsonify({"modelo": alm.restaurar(pid, nombre)})

    @bp.post("/api/proyectos/<pid>/convertir-latex")
    def convertir_latex(pid):
        return jsonify(alm.convertir_a_latex(pid))

    @bp.get("/api/proyectos/<pid>/latex")
    def ver_latex(pid):
        meta = alm.meta(pid)
        if meta["tipo"] == "estructurado":
            tex, _ = generador.generar(alm.leer_modelo(pid), marcas=request.args.get("marcas") == "1")
        else:
            tex = alm.leer_archivo(pid, meta["principal"])
        return sin_cache(Response(tex, mimetype="text/plain; charset=utf-8"))

    # ------------------------------------------------------------------ archivos (modo LaTeX)
    @bp.get("/api/proyectos/<pid>/archivos")
    def archivos(pid):
        return sin_cache(jsonify(alm.listar_archivos(pid)))

    @bp.get("/api/proyectos/<pid>/archivos/<path:ruta>")
    def archivo_leer(pid, ruta):
        return sin_cache(Response(alm.leer_archivo(pid, ruta), mimetype="text/plain; charset=utf-8"))

    @bp.put("/api/proyectos/<pid>/archivos/<path:ruta>")
    def archivo_escribir(pid, ruta):
        alm.escribir_archivo(pid, ruta, request.get_data(as_text=True))
        return jsonify({"ok": True})

    @bp.delete("/api/proyectos/<pid>/archivos/<path:ruta>")
    def archivo_borrar(pid, ruta):
        alm.borrar_archivo(pid, ruta)
        return jsonify({"ok": True})

    @bp.post("/api/proyectos/<pid>/archivos")
    def archivo_subir(pid):
        d = alm.dir_proyecto(pid)
        carpeta = A.limpiar_ruta(request.form.get("carpeta", ""))
        guardados = []
        for nombre, datos in archivos_subidos("archivos"):
            rel = "/".join(x for x in (carpeta, A.limpiar_nombre(nombre)) if x)
            p = A.unir(d, rel)
            if p.name in ("proyecto.json", "modelo.json"):
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(datos)
            guardados.append(rel)
        return jsonify({"guardados": guardados})

    # ------------------------------------------------------------------ tipografías propias
    @bp.get("/api/proyectos/<pid>/fuentes")
    def fuentes(pid):
        return sin_cache(jsonify({"familias": F.familias(alm.dir_proyecto(pid))}))

    @bp.post("/api/proyectos/<pid>/fuentes")
    def fuentes_subir(pid):
        d = alm.dir_proyecto(pid)
        guardados, errores = [], []
        for nombre, datos in archivos_subidos("archivos"):
            try:
                guardados.append(F.guardar(d, nombre, datos))
            except F.ErrorFuente as exc:
                errores.append(f"{nombre}: {exc}")
        familias = F.familias(d)
        nuevas = sorted({f["id"] for f in familias if set(f["archivos"].values()) & set(guardados)})
        return jsonify({"familias": familias, "guardados": guardados, "nuevas": nuevas, "errores": errores})

    @bp.delete("/api/proyectos/<pid>/fuentes")
    def fuentes_borrar(pid):
        d = alm.dir_proyecto(pid)
        F.borrar_familia(d, request.args.get("familia", ""))
        return jsonify({"familias": F.familias(d)})

    # ------------------------------------------------------------------ recursos
    @bp.get("/api/proyectos/<pid>/recursos")
    def recursos(pid):
        return sin_cache(jsonify(alm.listar_recursos(pid)))

    @bp.post("/api/proyectos/<pid>/recursos")
    def recursos_subir(pid):
        carpeta = request.form.get("carpeta", "recursos")
        guardados, errores = [], []
        for nombre, datos in archivos_subidos("archivos"):
            try:
                guardados.append(alm.guardar_recurso(pid, nombre, datos, carpeta))
            except A.ErrorAlmacen as exc:
                errores.append(f"{nombre}: {exc}")
        return jsonify({"guardados": guardados, "errores": errores})

    @bp.delete("/api/proyectos/<pid>/recursos")
    def recursos_borrar(pid):
        alm.borrar_recurso(pid, request.args.get("ruta", ""))
        return jsonify({"ok": True})

    @bp.get("/api/proyectos/<pid>/f/<path:ruta>")
    def fichero(pid, ruta):
        p = A.unir(alm.dir_proyecto(pid), ruta)
        if not p.is_file():
            return jsonify({"error": "no existe"}), 404
        tipo = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        return sin_cache(send_file(p, mimetype=tipo))

    @bp.get("/api/proyectos/<pid>/vista")
    def vista_recurso(pid):
        """Miniatura de un recurso (PNG/JPG reducidos con Pillow, PDF con pdftoppm)."""
        d = alm.dir_proyecto(pid)
        p = A.unir(d, request.args.get("ruta", ""))
        if not p.is_file():
            return jsonify({"error": "no existe"}), 404
        lado = 360
        clave = hashlib.md5(f"{p}:{p.stat().st_mtime}:{lado}".encode()).hexdigest()
        cache = d / "build" / "miniaturas"
        cache.mkdir(parents=True, exist_ok=True)
        destino = cache / f"{clave}.png"
        if not destino.exists():
            ok = False
            if p.suffix.lower() == ".pdf":
                ok = compilador.miniatura(p, destino, lado)
            else:
                try:
                    from PIL import Image
                    im = Image.open(p)
                    im.thumbnail((lado, lado))
                    if im.mode not in ("RGB", "RGBA"):
                        im = im.convert("RGBA")
                    im.save(destino, "PNG")
                    ok = True
                except Exception:
                    ok = False
            if not ok:
                if p.suffix.lower() == ".pdf":
                    return jsonify({"error": "sin miniatura"}), 404
                return send_file(p, mimetype=mimetypes.guess_type(p.name)[0] or "image/png", max_age=60)
        return send_file(destino, mimetype="image/png", max_age=3600)

    app.register_blueprint(bp)
