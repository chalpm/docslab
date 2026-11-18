# SPDX-License-Identifier: AGPL-3.0-only
"""Servidor web de DocsLab (Flask)."""
from __future__ import annotations

import hashlib
import io
import json
import mimetypes
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file, send_from_directory

from . import __license__, __license_sty__, __version__, almacen as A, bibliografia as B, compilador, componentes as CP, cuadernos, generador
from . import graficos as GR, lab as LAB
from . import fuentes as F
from . import modelo as M, powerpoint as PP, revision, texto as T, variantes as V
from .trabajos import GestorTrabajos

RAIZ_APP = Path(__file__).resolve().parent.parent
ESTATICO = RAIZ_APP / "static"


def crear_app(datos: Path, raices: list[Path] | None = None, colab: bool = False) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.json.sort_keys = False          # conserva el orden (temas, tamaños…)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1 GB
    alm = A.Almacen(datos)
    compilador.DIR_FORMATOS = alm.datos / "formatos"
    trabajos = GestorTrabajos()
    raices = [Path(r).expanduser().resolve() for r in (raices or [])]
    app.config.update(ALMACEN=alm, TRABAJOS=trabajos, RAICES=raices, COLAB=colab)

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

    # ------------------------------------------------------------------ estáticos
    @app.get("/")
    def inicio():
        return sin_cache(send_from_directory(ESTATICO, "index.html"))

    @app.get("/static/<path:ruta>")
    def estatico(ruta):
        resp = send_from_directory(ESTATICO, ruta)
        if not ruta.startswith("vendor/"):
            resp.headers["Cache-Control"] = "no-cache"
        return resp

    # ------------------------------------------------------------------ estado
    def _familias_instaladas() -> dict:
        """Qué tipografías libres de TeX Live están instaladas (None si no se puede saber)."""
        libres = {k: f"{v['paquete']}.sty" for k, v in M.FAMILIAS_INFO.items() if v.get("paquete")}
        hay = compilador.existen_tex(list(libres.values()))
        return {k: hay.get(v) for k, v in libres.items()}

    @app.get("/api/estado")
    def estado():
        try:
            import nbclient  # noqa: F401
            nb_ok = True
        except ImportError:
            nb_ok = False
        try:
            import PIL  # noqa: F401
            pil_ok = True
        except ImportError:
            pil_ok = False
        return jsonify({
            "version": __version__, "licencia": __license__, "licencia_sty": __license_sty__, "pdflatex": compilador.pdflatex(), "tex": compilador.version_tex(),
            "miktex": compilador.es_miktex(),
            "pdftoppm": bool(compilador.pdftoppm()), "cuadernos": nb_ok, "pillow": pil_ok,
            "ghostscript": bool(compilador.ghostscript()), "poppler": revision.herramientas(),
            "powerpoint": PP.disponible(),
            "lualatex": bool(compilador.lualatex()), "familias": _familias_instaladas(),
            "colab": colab, "raices": [str(r) for r in raices], "datos": str(alm.datos),
            "python": sys.version.split()[0], "python_exe": sys.executable, "sistema": platform.system(),
            "idiomas": {k: compilador.existe_tex(v["babel"] + ".ldf") is not False for k, v in M.IDIOMAS.items()},
        })

    @app.get("/api/variantes")
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

    # ------------------------------------------------------------------ Componente Lab
    biblio = CP.Biblioteca(alm.datos / "componentes")
    app.config["BIBLIOTECA"] = biblio

    def _error_valor(fn):
        try:
            return fn()
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.get("/api/componentes")
    def componentes():
        return sin_cache(jsonify(biblio.listar()))

    @app.post("/api/componentes")
    def componente_nuevo():
        d = json_body()
        if isinstance(d.get("componente"), dict):
            return jsonify(biblio.crear(d["componente"], conservar_id=bool(d.get("conservar_id"))))
        return jsonify(biblio.crear(d))

    @app.get("/api/componentes/<cid>")
    def componente(cid):
        return _error_valor(lambda: sin_cache(jsonify(biblio.leer(cid))))

    @app.put("/api/componentes/<cid>")
    def componente_guardar(cid):
        return _error_valor(lambda: jsonify(biblio.guardar(cid, json_body())))

    @app.delete("/api/componentes/<cid>")
    def componente_borrar(cid):
        return _error_valor(lambda: (biblio.borrar(cid), jsonify({"ok": True}))[1])

    @app.post("/api/componentes/<cid>/duplicar")
    def componente_duplicar(cid):
        return _error_valor(lambda: jsonify(biblio.duplicar(cid)))

    @app.post("/api/componentes/recrear")
    def componente_recrear():
        """Un borrador (sin guardar, sin id) para recrear uno de los incluidos."""
        d = json_body()

        def borrador():
            c = CP.desde_variante(str(d.get("clave") or ""), "preajuste" if d.get("modo") == "preajuste" else "latex")
            for k in ("id", "version", "creado", "modificado"):
                c.pop(k, None)
            return jsonify(c)
        return _error_valor(borrador)

    @app.post("/api/componentes/codigo")
    def componente_codigo():
        """El LaTeX de un componente (para «Ver el código» y «Pasar a código»)."""
        c = CP.normalizar(json_body())
        codigo, pre = CP.codigo_de(c) if c["modo"] != CP.PREAJUSTE else ("", "")
        return jsonify({"codigo": codigo, "preambulo": pre, "campos": c["campos"], "como_latex": CP.a_codigo(c)})

    @app.post("/api/componentes/vista")
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

    @app.get("/api/componentes/vistas/<h>.pdf")
    def componente_vista_pdf(h):
        p = CP.pdf_vista(biblio.raiz, h)
        if not p:
            return jsonify({"error": "La vista previa ya no está: vuelve a generarla"}), 404
        return send_file(p, mimetype="application/pdf", max_age=3600)

    @app.get("/api/componentes/<cid>/miniatura")
    def componente_miniatura(cid):
        if not CP.es_id(cid) or not (biblio.raiz / f"{cid}.png").exists():
            return jsonify({"error": "sin miniatura"}), 404
        return sin_cache(send_file(biblio.raiz / f"{cid}.png", mimetype="image/png"))

    @app.get("/api/componentes/exportar")
    def componentes_exportar():
        ids = [x for x in request.args.get("ids", "").split(",") if CP.es_id(x)]
        texto = _error_valor(lambda: biblio.exportar(ids or None))
        if not isinstance(texto, str):
            return texto
        nombre = "componentes-docslab.json" if len(ids) != 1 else \
            A.limpiar_nombre(biblio.leer(ids[0]).get("nombre"), "componente") + ".json"
        return send_file(io.BytesIO(texto.encode("utf-8")), mimetype="application/json", as_attachment=True,
                         download_name=nombre)

    @app.post("/api/componentes/importar")
    def componentes_importar():
        f = request.files.get("archivo")
        texto = f.read().decode("utf-8-sig", "replace") if f else str(json_body().get("texto") or "")
        return _error_valor(lambda: jsonify([CP.resumen(c) for c in biblio.importar(texto)]))

    # ------------------------------------------------------------------ bibliografía
    @app.post("/api/bibliografia/formatear")
    def bib_formatear():
        d = json_body()
        estilo, idioma = d.get("estilo") or "apa", d.get("idioma") or "es"
        refs = d.get("referencias") if isinstance(d.get("referencias"), list) else []
        return jsonify({"entradas": B.formatear(refs, estilo, idioma), "ejemplo": B.ejemplo_cita(estilo, idioma)})

    @app.post("/api/bibliografia/vista")
    def bibliografia_vista():
        d = json_body()
        if not isinstance(d.get("modelo"), dict):
            return jsonify({"error": "Falta el modelo del póster"}), 400
        return jsonify(generador.vista_bibliografia(d["modelo"]))

    @app.post("/api/bibliografia/importar")
    def bib_importar():
        f = request.files.get("archivo")
        if f:
            texto = f.read().decode("utf-8-sig", "replace")
        else:
            texto = str(json_body().get("texto") or "")
        refs, errores = B.importar_texto(texto)
        return jsonify({"referencias": refs, "errores": errores})

    @app.get("/api/bibliografia/doi")
    def bib_doi():
        try:
            return jsonify({"referencia": B.buscar_doi(request.args.get("doi", ""))})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.get("/api/proyectos/<pid>/bibliografia.bib")
    def bib_exportar(pid):
        meta = alm.meta(pid)
        refs = alm.leer_modelo(pid).get("bibliografia", {}).get("referencias", []) if meta["tipo"] == "estructurado" else []
        nombre = A.limpiar_nombre(meta["nombre"], "referencias") + ".bib"
        return send_file(io.BytesIO(B.a_bibtex(refs).encode("utf-8")), mimetype="application/x-bibtex",
                         as_attachment=True, download_name=nombre)

    # ------------------------------------------------------------------ plantillas
    @app.get("/api/plantillas")
    def plantillas():
        return jsonify(alm.listar_plantillas())

    @app.post("/api/plantillas")
    def plantilla_nueva():
        d = json_body()
        return jsonify(alm.crear_plantilla(d.get("proyecto", ""), d.get("nombre", ""), d.get("descripcion", "")))

    @app.patch("/api/plantillas/<tid>")
    def plantilla_cambiar(tid):
        return jsonify(alm.actualizar_plantilla(tid, json_body()))

    @app.put("/api/plantillas/<tid>")
    def plantilla_reemplazar(tid):
        """Sustituye el contenido de una plantilla propia por el de un proyecto."""
        return jsonify(alm.reemplazar_plantilla(tid, json_body().get("proyecto", "")))

    @app.delete("/api/plantillas/<tid>")
    def plantilla_borrar(tid):
        alm.borrar_plantilla(tid)
        return jsonify({"ok": True})

    @app.get("/api/plantillas/<tid>/miniatura")
    def plantilla_miniatura(tid):
        p = alm.dir_plantilla(tid) / "miniatura.png"
        if not p.exists():
            return jsonify({"error": "sin miniatura"}), 404
        return send_file(p, mimetype="image/png", max_age=60)

    @app.get("/api/plantillas/<tid>/exportar")
    def plantilla_exportar(tid):
        datos = alm.exportar_plantilla(tid)
        return send_file(io.BytesIO(datos), mimetype="application/zip", as_attachment=True,
                         download_name=f"plantilla-{tid}.zip")

    # ------------------------------------------------------------------ proyectos
    @app.get("/api/proyectos")
    def proyectos():
        return jsonify(alm.listar_proyectos())

    @app.post("/api/proyectos")
    def proyecto_nuevo():
        d = json_body()
        return jsonify(alm.crear_proyecto(d.get("nombre", ""), d.get("plantilla") or None, d.get("asistente")))

    @app.post("/api/proyectos/importar")
    def proyecto_importar():
        f = request.files.get("archivo")
        if not f:
            return jsonify({"error": "Falta el archivo"}), 400
        return jsonify(alm.importar_zip(f.read(), request.form.get("nombre", "")))

    @app.get("/api/proyectos/<pid>")
    def proyecto(pid):
        meta = alm.meta(pid)
        salida = {"meta": meta, "plantilla_propia": alm.plantilla_propia(meta)}
        if meta["tipo"] == "estructurado":
            salida["modelo"] = alm.leer_modelo(pid)
        return sin_cache(jsonify(salida))

    @app.patch("/api/proyectos/<pid>")
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

    @app.delete("/api/proyectos/<pid>")
    def proyecto_borrar(pid):
        lab.cerrar(pid)
        alm.borrar_proyecto(pid)
        return jsonify({"ok": True})

    @app.post("/api/proyectos/<pid>/duplicar")
    def proyecto_duplicar(pid):
        return jsonify(alm.duplicar_proyecto(pid, json_body().get("nombre")))

    @app.put("/api/proyectos/<pid>/modelo")
    def modelo_guardar(pid):
        d = request.get_json(silent=True)
        if not isinstance(d, dict):
            return jsonify({"error": "Modelo no válido"}), 400
        alm.guardar_modelo(pid, d)
        return jsonify({"ok": True, "guardado": time.time()})

    @app.post("/api/proyectos/<pid>/formato")
    def formato_texto(pid):
        nuevo = json_body().get("formato")
        if nuevo not in ("simple", "latex"):
            return jsonify({"error": "Formato no válido"}), 400
        mod = M.convertir_formato(alm.leer_modelo(pid), nuevo)
        mod = alm.guardar_modelo(pid, mod)
        return jsonify({"modelo": mod})

    @app.get("/api/proyectos/<pid>/historial")
    def historial(pid):
        return jsonify(alm.historial(pid))

    @app.post("/api/proyectos/<pid>/historial/<nombre>/restaurar")
    def historial_restaurar(pid, nombre):
        return jsonify({"modelo": alm.restaurar(pid, nombre)})

    @app.post("/api/proyectos/<pid>/convertir-latex")
    def convertir_latex(pid):
        return jsonify(alm.convertir_a_latex(pid))

    @app.get("/api/proyectos/<pid>/latex")
    def ver_latex(pid):
        meta = alm.meta(pid)
        if meta["tipo"] == "estructurado":
            tex, _ = generador.generar(alm.leer_modelo(pid), marcas=request.args.get("marcas") == "1")
        else:
            tex = alm.leer_archivo(pid, meta["principal"])
        return sin_cache(Response(tex, mimetype="text/plain; charset=utf-8"))

    # ------------------------------------------------------------------ compilación
    def _ultima(pid) -> Path:
        return alm.dir_proyecto(pid) / "build" / "ultima.json"

    def _huella_compilacion(d: Path, principal: str) -> str:
        """Lo que decide el PDF: el .tex, la plantilla y las imágenes (nombre, tamaño y fecha)."""
        h = hashlib.md5()
        for p in (d / principal, compilador.STY):
            try:
                h.update(p.read_bytes())
            except OSError:
                pass
        for raiz, dirs, archivos in os.walk(d):
            dirs[:] = sorted(x for x in dirs if x not in ("build", "historial", "__pycache__", ".ipynb_checkpoints"))
            for a in sorted(archivos):
                rel = Path(raiz, a).relative_to(d).as_posix()
                if rel in (principal, "postercientifico.sty", "ajuste.tex", "imprenta.tex"):
                    continue                    # el .tex va por su contenido; la plantilla, aparte
                if Path(a).suffix.lower() in (".png", ".jpg", ".jpeg", ".pdf", ".tex", ".sty", ".bib", ".eps", ".cls",
                                              ".ttf", ".otf"):
                    st = (Path(raiz) / a).stat()
                    h.update(f"{rel}|{st.st_size}|{st.st_mtime_ns}".encode())
        return h.hexdigest()

    def _compilar(pid, t):
        meta = alm.meta(pid)
        d = alm.dir_proyecto(pid)
        mapa = {}
        formato = None
        clase, diapositivas = "poster", None
        if meta["tipo"] == "estructurado":
            t.informar("Generando el código LaTeX", 0.02)
            _, mapa = alm.escribir_tex(pid, marcas=True)
            principal = "poster.tex"
            copiar = True
            modelo = alm.leer_modelo(pid)
            clase = modelo.get("clase", "poster")
            if clase == "presentacion":
                diapositivas = [(pg["id"], T.texto_plano(pg.get("nombre"), 40)) for pg in modelo.get("paginas", [])
                                if pg.get("visible", True) is not False]
            motor = M.motor(modelo)
            formato = compilador.formato_poster() if motor == "pdflatex" else None
        else:
            principal = meta.get("principal", "poster.tex")
            copiar = not (d / "postercientifico.sty").exists()
            try:
                motor = compilador.motor_del_tex((d / principal).read_text(encoding="utf-8", errors="replace"))
            except OSError:
                motor = "pdflatex"
        huella = _huella_compilacion(d, principal)
        try:
            anterior = json.loads(_ultima(pid).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            anterior = {}
        pdf_actual = d / "build" / (Path(principal).stem + ".pdf")
        if anterior.get("huella") == huella and anterior.get("ok") and pdf_actual.exists():
            t.informar("Sin cambios: el PDF ya está al día", 1.0)
            return anterior
        res = compilador.compilar(d, principal, copiar_sty=copiar, cancelar=t.cancelar, informar=t.informar,
                                  avisar_paginas=meta["tipo"] == "estructurado" and clase == "poster",
                                  hacer_miniatura=False, formato=formato, motor=motor, diapositivas=diapositivas)
        res["huella"] = huella
        res["clase"] = clase
        if mapa:
            lineas = (d / principal).read_text(encoding="utf-8", errors="replace").splitlines()
            for e in res.get("errores", []):
                if e.get("linea") and Path(e.get("archivo") or "").name == Path(principal).name:
                    e["elemento"] = compilador.localizar_error(e, lineas, mapa)
        res["version"] = int(time.time() * 1000)
        res["principal"] = principal
        if res.get("ok"):
            info = revision.info_pdf(d / "build" / (Path(principal).stem + ".pdf"))
            if info:                        # tamaño real de la página (también en los proyectos LaTeX)
                w, h = info["tamanos"][0]
                res["pagina_mm"] = [round(w * 25.4 / 72, 1), round(h * 25.4 / 72, 1)]
        (d / "build").mkdir(exist_ok=True)
        if not res.get("ok"):
            # se sigue mostrando el último PDF correcto: sus posiciones también
            anterior = {}
            try:
                anterior = json.loads(_ultima(pid).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
            if anterior.get("posiciones", {}).get("cajas"):
                res["posiciones"] = anterior["posiciones"]
            res["pdf_anterior"] = (d / "build" / (Path(principal).stem + ".ok.pdf")).exists()
        _ultima(pid).write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        if res.get("ok"):
            # la miniatura (para la pantalla de inicio) se hace aparte: no retrasa la vista previa
            ok_pdf = d / "build" / (Path(principal).stem + ".ok.pdf")
            threading.Thread(target=compilador.miniatura, args=(ok_pdf, d / "build" / "miniatura.png"),
                             daemon=True).start()
        t.informar("Listo" if res.get("ok") else "Con errores", 1.0)
        return res

    # ------------------------------------------------------------------ ajustar a una página
    def _ajustar(pid, t):
        """Busca la letra más grande (sin pasar de la actual) con la que el póster cabe en una
        página: compila aparte (ajuste.tex) y va partiendo el intervalo por la mitad."""
        import copy
        import math
        import re
        meta = alm.meta(pid)
        if meta["tipo"] != "estructurado":
            raise ValueError("Solo los pósters del editor visual se ajustan solos")
        d = alm.dir_proyecto(pid)
        m = alm.leer_modelo(pid)
        if M.es_flujo(m):
            raise ValueError("En un documento el texto sigue en la página siguiente: no hace falta ajustarlo")
        # una presentación «cabe» si cada diapositiva ocupa una sola página
        paginas_ok = sum(1 for pg in m["paginas"] if pg.get("visible", True) is not False) \
            if m["clase"] == "presentacion" else 1
        f0 = float(generador.numero(m["tipografia"].get("fuente"), 30) or 30)
        pruebas = []

        def probar(f):
            if t.cancelar.is_set():
                raise InterruptedError
            t.informar(f"Probando con letra de {generador.fmt(round(f, 2))} pt", min(0.95, 0.1 + 0.09 * len(pruebas)))
            m2 = copy.deepcopy(m)
            m2["tipografia"]["fuente"] = round(f, 2)
            tex, _ = generador.generar(m2, marcas=False)
            (d / "ajuste.tex").write_text(tex, encoding="utf-8")
            res = compilador.compilar(d, "ajuste.tex", max_pasadas=3, cancelar=t.cancelar, avisar_paginas=False,
                                      hacer_miniatura=False, formato=compilador.formato_poster(), motor=M.motor(m2))
            if res.get("cancelado"):
                raise InterruptedError
            if not res.get("ok"):
                raise ValueError("El póster tiene errores de LaTeX: corrígelos antes de ajustarlo")
            cabe = (res.get("paginas") or 99) <= paginas_ok and not any(
                "no cabe" in str(a.get("mensaje")) for a in res.get("avisos") or [])
            pruebas.append({"fuente": round(f, 2), "cabe": cabe, "paginas": res.get("paginas")})
            return cabe, res

        def estimar(res) -> float:
            """Cuánto hay que achicar la letra. El alto de un texto en columnas de ancho fijo crece
            con el cuadrado de la letra (líneas más altas y más líneas), así que el factor es
            la raíz de disponible / necesario."""
            sobra = [float(x) for a in res.get("avisos") or []
                     for x in re.findall(r"sobra ([0-9.]+)pt", str(a.get("mensaje")))]
            mo = re.match(r"^\s*([0-9.]+)\s*(mm|cm|in|pt|bp)?\s*$", str(m["lienzo"].get("alto") or ""))
            factor = {"mm": 72.27 / 25.4, "cm": 72.27 / 2.54, "in": 72.27, "pt": 1, "bp": 72.27 / 72}
            alto_pt = float(mo.group(1)) * factor[mo.group(2) or "pt"] if mo else 3383.0
            disponible = 0.72 * alto_pt
            if sobra:
                return math.sqrt(disponible / (disponible + max(sobra)))
            return math.sqrt(1 / max(2, (res.get("paginas") or 2) - paginas_ok + 1))

        try:
            cabe, res = probar(f0)
            if cabe:
                return {"cabe": True, "ya_cabia": True, "fuente": f0, "antes": f0, "pruebas": pruebas}
            minima = max(5.0, f0 * 0.5)
            g = max(minima, min(f0 * 0.97, f0 * estimar(res) * 0.98))
            if probar(g)[0]:
                lo, hi = g, min(f0, g * 1.06)
                if hi < f0 and probar(hi)[0]:
                    lo, hi = hi, f0
            else:
                hi, lo = g, max(minima, g * 0.85)
                if not probar(lo)[0]:
                    hi, lo = lo, minima
                    if not probar(lo)[0]:
                        return {"cabe": False, "fuente": f0, "antes": f0, "minima": round(lo, 1), "pruebas": pruebas}
            tolerancia = max(0.1, f0 * 0.008)
            while hi - lo > tolerancia:
                medio = (lo + hi) / 2
                if probar(medio)[0]:
                    lo = medio
                else:
                    hi = medio
            f = math.floor(lo * 10) / 10
            t.informar(f"Cabe con letra de {generador.fmt(f)} pt", 1.0)
            return {"cabe": True, "ya_cabia": False, "fuente": f, "antes": f0, "pruebas": pruebas}
        except InterruptedError:
            t.cancelar.set()
            return None
        finally:
            for x in [d / "ajuste.tex", *(d / "build").glob("ajuste.*")]:
                try:
                    x.unlink()
                except OSError:
                    pass

    @app.post("/api/proyectos/<pid>/ajustar")
    def ajustar(pid):
        alm.meta(pid)
        for t in trabajos.activos(pid, "ajustar"):
            return jsonify(t.como_dict(False))
        t = trabajos.lanzar("ajustar", pid, lambda t: _ajustar(pid, t), "Ajustar a una página", exclusivo="ajustar")
        return jsonify(t.como_dict(False))

    # ------------------------------------------------------------------ revisión antes de imprimir
    def _pdf_actual(pid, meta, res) -> Path:
        d = alm.dir_proyecto(pid)
        stem = "poster" if meta["tipo"] == "estructurado" else Path(meta.get("principal", "poster.tex")).stem
        pdf = d / "build" / f"{stem}.pdf"
        if not res.get("ok"):
            pdf = d / "build" / f"{stem}.ok.pdf"     # el último que compiló bien
        return pdf

    def _revisar(pid, t):
        meta = alm.meta(pid)
        res = _compilar(pid, t)                      # al día (si no hay cambios, no compila)
        pdf = _pdf_actual(pid, meta, res)
        if not pdf.exists():
            raise ValueError("Todavía no hay un PDF que revisar: corrige los errores y compila")
        t.informar("Revisando imágenes, letra, contraste y tipografías", 0.6)
        modelo = alm.leer_modelo(pid) if meta["tipo"] == "estructurado" else None
        r = revision.revisar(alm.dir_proyecto(pid), pdf, modelo, res, meta["tipo"])
        r["version"] = res.get("version")
        t.informar("Revisión hecha", 1.0)
        return r

    @app.post("/api/proyectos/<pid>/revisar")
    def revisar(pid):
        alm.meta(pid)
        for t in trabajos.activos(pid, "revisar"):
            return jsonify(t.como_dict(False))
        # comparte turno con las compilaciones: nadie cambia el PDF mientras se revisa
        t = trabajos.lanzar("revisar", pid, lambda t: _revisar(pid, t), "Revisar para imprimir", exclusivo="compilar")
        return jsonify(t.como_dict(False))

    # ------------------------------------------------------------------ PDF para imprenta
    def _imprenta(pid, t, opciones: dict):
        """Sangrado y marcas de corte (en los pósters del editor visual, desde LaTeX; en los
        de código, solo las marcas, alrededor del PDF ya hecho) y, si se pide, CMYK."""
        meta = alm.meta(pid)
        d = alm.dir_proyecto(pid)
        build = d / "build"
        build.mkdir(exist_ok=True)
        try:
            sangrado = max(0.0, min(10.0, float(opciones.get("sangrado_mm") or 0)))
        except (TypeError, ValueError):
            sangrado = 0.0
        marcas, cmyk = bool(opciones.get("marcas_corte")), bool(opciones.get("cmyk"))
        if cmyk and not compilador.ghostscript():
            raise ValueError("Para pasar a CMYK hace falta Ghostscript (gs): instálalo o descarga el PDF en RGB")
        notas = []
        destino = build / "imprenta.pdf"
        if meta["tipo"] == "estructurado":
            t.informar("Preparando el póster para la imprenta", 0.05)
            modelo = alm.leer_modelo(pid)
            tex, _ = generador.generar(modelo, marcas=False,
                                       imprenta={"sangrado_mm": sangrado, "marcas_corte": marcas, "directorio": d})
            (d / "imprenta.tex").write_text(tex, encoding="utf-8")
            # las alturas de las filas no cambian: con el .aux del póster basta una pasada
            if (build / "poster.aux").exists():
                shutil.copyfile(build / "poster.aux", build / "imprenta.aux")
            try:
                res = compilador.compilar(d, "imprenta.tex", cancelar=t.cancelar, avisar_paginas=False,
                                          hacer_miniatura=False, formato=compilador.formato_poster(),
                                          motor=M.motor(modelo),
                                          informar=lambda msg, pr=None: t.informar("Compilando el PDF para imprenta",
                                                                                   0.1 + 0.6 * (pr or 0)))
            finally:
                (d / "imprenta.tex").unlink(missing_ok=True)
                for x in build.glob("imprenta.*"):
                    if x.suffix not in (".pdf", ".json"):
                        x.unlink(missing_ok=True)
                (build / "imprenta.ok.pdf").unlink(missing_ok=True)
            if res.get("cancelado"):
                t.cancelar.set()
                return None
            if not res.get("ok"):
                primero = (res.get("errores") or [{}])[0].get("mensaje") or ""
                raise ValueError("El póster tiene errores de LaTeX: corrígelos y vuelve a intentarlo"
                                 + (f" ({primero[:160]})" if primero else ""))
        else:
            res = _compilar(pid, t)
            fuente = _pdf_actual(pid, meta, res)
            if not res.get("ok") or not fuente.exists():
                raise ValueError("El documento tiene errores de LaTeX: corrígelos y vuelve a intentarlo")
            if sangrado:
                notas.append("En los proyectos de código el sangrado no se añade solo: el PDF va sin sangrado.")
                sangrado = 0.0
            if marcas:
                t.informar("Poniendo las marcas de corte", 0.5)
                info = revision.info_pdf(fuente)
                if not info or not compilador.marcas_de_corte(fuente, destino, info["tamanos"][:info["paginas"]] or info["tamanos"]):
                    raise ValueError("No se pudieron poner las marcas de corte")
            else:
                shutil.copyfile(fuente, destino)
        if cmyk:
            t.informar("Pasando los colores a CMYK", 0.8)
            ok, error = compilador.a_cmyk(destino, build / "imprenta-cmyk.pdf")
            if not ok:
                raise ValueError(error)
            destino.unlink(missing_ok=True)
            destino = build / "imprenta-cmyk.pdf"
        else:
            (build / "imprenta-cmyk.pdf").unlink(missing_ok=True)
        nombre = A.limpiar_nombre(meta["nombre"], "poster") + ("-imprenta-cmyk" if cmyk else "-imprenta") + ".pdf"
        info = revision.info_pdf(destino) or {}
        w, h = (info.get("tamanos") or [(0, 0)])[0]
        datos = {"archivo": destino.name, "nombre": nombre, "sangrado_mm": sangrado, "marcas_corte": marcas,
                 "cmyk": cmyk, "bytes": destino.stat().st_size, "paginas": info.get("paginas"),
                 "ancho_mm": round(w * 25.4 / 72, 1), "alto_mm": round(h * 25.4 / 72, 1), "notas": notas,
                 "fecha": time.time(), "url": f"api/proyectos/{pid}/imprenta.pdf"}
        (build / "imprenta.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        meta = alm.meta(pid)
        meta.setdefault("ajustes", {})["imprenta"] = {"sangrado_mm": sangrado if meta["tipo"] == "estructurado"
                                                      else float(opciones.get("sangrado_mm") or 0),
                                                      "marcas_corte": marcas, "cmyk": cmyk}
        alm.guardar_meta(pid, meta)
        t.informar("PDF para imprenta listo", 1.0)
        return datos

    def _powerpoint(pid, t, opciones: dict):
        """El póster en PowerPoint: con el texto editable sobre una imagen del póster sin
        texto, o como una imagen entera."""
        meta = alm.meta(pid)
        d = alm.dir_proyecto(pid)
        build = d / "build"
        build.mkdir(exist_ok=True)
        modo = opciones.get("modo") if opciones.get("modo") in PP.MODOS else "editable"
        hay = PP.disponible()
        if not hay["pptx"]:
            raise ValueError("Falta el paquete de Python «python-pptx»: instálalo en el entorno de DocsLab "
                             "(python -m pip install python-pptx) y reinicia DocsLab")
        notas = []
        if modo == "editable" and not hay["editable"]:
            modo = "imagen"
            notas.append("Sin Ghostscript no se puede separar el texto: el póster va como imagen.")
        res = _compilar(pid, t)                      # al día (si no hay cambios, no compila)
        if res is None:
            return None
        pdf = _pdf_actual(pid, meta, res)
        if not pdf.exists():
            raise ValueError("El póster no compila todavía: corrige los errores y vuelve a intentarlo")
        if not res.get("ok"):
            notas.append("El póster tiene errores: va la última versión que compiló bien.")
        modelo = alm.leer_modelo(pid) if meta["tipo"] == "estructurado" else None
        destino = build / "poster.pptx"
        info = PP.exportar(pdf, destino, modo, modelo, res.get("posiciones") if res.get("ok") else None,
                           ppp=220 if opciones.get("alta") else 150, titulo=meta["nombre"],
                           informar=lambda msg, pr=None: t.informar(msg, pr))
        datos = dict(info, nombre=A.limpiar_nombre(meta["nombre"], "poster") + ".pptx", bytes=destino.stat().st_size,
                     notas=notas + info.get("avisos", []), fecha=time.time(),
                     url=f"api/proyectos/{pid}/powerpoint.pptx")
        (build / "powerpoint.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        meta = alm.meta(pid)
        meta.setdefault("ajustes", {})["powerpoint"] = {"modo": opciones.get("modo") or modo,
                                                         "alta": bool(opciones.get("alta"))}
        alm.guardar_meta(pid, meta)
        t.informar("PowerPoint listo", 1.0)
        return datos

    @app.post("/api/proyectos/<pid>/powerpoint")
    def powerpoint(pid):
        alm.meta(pid)
        opciones = json_body()
        t = trabajos.lanzar("powerpoint", pid, lambda t: _powerpoint(pid, t, opciones), "PowerPoint",
                            exclusivo="compilar")
        return jsonify(t.como_dict(False))

    @app.get("/api/proyectos/<pid>/powerpoint.pptx")
    def powerpoint_pptx(pid):
        d = alm.dir_proyecto(pid) / "build"
        try:
            datos = json.loads((d / "powerpoint.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return jsonify({"error": "Todavía no hay PowerPoint"}), 404
        p = d / "poster.pptx"
        if not p.is_file():
            return jsonify({"error": "Todavía no hay PowerPoint"}), 404
        return sin_cache(send_file(p, mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                   as_attachment=request.args.get("descargar") == "1",
                                   download_name=datos.get("nombre") or "poster.pptx", max_age=0))

    @app.post("/api/proyectos/<pid>/imprenta")
    def imprenta(pid):
        alm.meta(pid)
        opciones = json_body()
        t = trabajos.lanzar("imprenta", pid, lambda t: _imprenta(pid, t, opciones), "PDF para imprenta",
                            exclusivo="compilar")
        return jsonify(t.como_dict(False))

    @app.get("/api/proyectos/<pid>/imprenta.pdf")
    def imprenta_pdf(pid):
        d = alm.dir_proyecto(pid) / "build"
        try:
            datos = json.loads((d / "imprenta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return jsonify({"error": "Todavía no hay PDF para imprenta"}), 404
        p = d / Path(str(datos.get("archivo") or "")).name
        if not p.is_file():
            return jsonify({"error": "Todavía no hay PDF para imprenta"}), 404
        return sin_cache(send_file(p, mimetype="application/pdf", as_attachment=request.args.get("descargar") == "1",
                                   download_name=datos.get("nombre") or "poster-imprenta.pdf", max_age=0))

    @app.get("/api/proyectos/<pid>/imprenta.png")
    def imprenta_png(pid):
        d = alm.dir_proyecto(pid) / "build"
        try:
            datos = json.loads((d / "imprenta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return jsonify({"error": "Todavía no hay PDF para imprenta"}), 404
        p = d / Path(str(datos.get("archivo") or "")).name
        destino = d / "imprenta-mini.png"
        if not p.is_file():
            return jsonify({"error": "Todavía no hay PDF para imprenta"}), 404
        if not destino.exists() or destino.stat().st_mtime < p.stat().st_mtime:
            hecho = (compilador.miniatura_cmyk if datos.get("cmyk") else compilador.miniatura)(p, destino, 420)
            if not hecho:
                return jsonify({"error": "sin miniatura"}), 404
        return sin_cache(send_file(destino, mimetype="image/png"))

    @app.post("/api/proyectos/<pid>/compilar")
    def compilar(pid):
        alm.meta(pid)
        # si ya hay uno esperando, se reutiliza (las ediciones rápidas no se encolan sin fin)
        for t in trabajos.activos(pid, "compilar"):
            if t.estado == "pendiente":
                return jsonify(t.como_dict(False))
        t = trabajos.lanzar("compilar", pid, lambda t: _compilar(pid, t), "Compilar el póster",
                            exclusivo="compilar")
        return jsonify(t.como_dict(False))

    @app.get("/api/proyectos/<pid>/compilacion")
    def compilacion(pid):
        p = _ultima(pid)
        if not p.exists():
            return sin_cache(jsonify(None))
        texto = p.read_text(encoding="utf-8")
        if '"pagina_mm"' not in texto:             # compilaciones de antes de guardar el tamaño
            try:
                res = json.loads(texto)
                pdf = _pdf_actual(pid, alm.meta(pid), res)
                info = revision.info_pdf(pdf) if pdf.exists() else None
                if info:
                    w, h = info["tamanos"][0]
                    res["pagina_mm"] = [round(w * 25.4 / 72, 1), round(h * 25.4 / 72, 1)]
                    return sin_cache(jsonify(res))
            except (ValueError, OSError):
                pass
        return sin_cache(Response(texto, mimetype="application/json"))

    @app.get("/api/proyectos/<pid>/pdf")
    def pdf(pid):
        meta = alm.meta(pid)
        d = alm.dir_proyecto(pid)
        p = d / "build" / (Path(meta.get("principal", "poster.tex")).stem + ".pdf")
        if not p.exists():
            p = p.with_suffix(".ok.pdf")          # la última versión que compiló bien
        if not p.exists():
            return jsonify({"error": "Todavía no hay PDF: compila el póster"}), 404
        nombre = A.limpiar_nombre(meta["nombre"], "poster") + ".pdf"
        resp = send_file(p, mimetype="application/pdf", as_attachment=request.args.get("descargar") == "1",
                         download_name=nombre, max_age=0)
        return sin_cache(resp)

    @app.get("/api/proyectos/<pid>/miniatura")
    def miniatura(pid):
        p = alm.miniatura(pid)
        if not p:
            return jsonify({"error": "sin miniatura"}), 404
        return sin_cache(send_file(p, mimetype="image/png"))

    @app.get("/api/proyectos/<pid>/exportar")
    def exportar(pid):
        meta = alm.meta(pid)
        tipo = request.args.get("tipo", "overleaf")
        base = A.limpiar_nombre(meta["nombre"], "poster")
        if tipo == "proyecto":
            datos, nombre = alm.exportar_proyecto(pid), f"{base}-docslab.zip"
        else:
            datos, nombre = alm.exportar_overleaf(pid), f"{base}-overleaf.zip"
        return send_file(io.BytesIO(datos), mimetype="application/zip", as_attachment=True, download_name=nombre)

    # ------------------------------------------------------------------ archivos (modo LaTeX)
    @app.get("/api/proyectos/<pid>/archivos")
    def archivos(pid):
        return sin_cache(jsonify(alm.listar_archivos(pid)))

    @app.get("/api/proyectos/<pid>/archivos/<path:ruta>")
    def archivo_leer(pid, ruta):
        return sin_cache(Response(alm.leer_archivo(pid, ruta), mimetype="text/plain; charset=utf-8"))

    @app.put("/api/proyectos/<pid>/archivos/<path:ruta>")
    def archivo_escribir(pid, ruta):
        alm.escribir_archivo(pid, ruta, request.get_data(as_text=True))
        return jsonify({"ok": True})

    @app.delete("/api/proyectos/<pid>/archivos/<path:ruta>")
    def archivo_borrar(pid, ruta):
        alm.borrar_archivo(pid, ruta)
        return jsonify({"ok": True})

    @app.post("/api/proyectos/<pid>/archivos")
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
    @app.get("/api/proyectos/<pid>/fuentes")
    def fuentes(pid):
        return sin_cache(jsonify({"familias": F.familias(alm.dir_proyecto(pid))}))

    @app.post("/api/proyectos/<pid>/fuentes")
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

    @app.delete("/api/proyectos/<pid>/fuentes")
    def fuentes_borrar(pid):
        d = alm.dir_proyecto(pid)
        F.borrar_familia(d, request.args.get("familia", ""))
        return jsonify({"familias": F.familias(d)})

    # ------------------------------------------------------------------ recursos
    @app.get("/api/proyectos/<pid>/recursos")
    def recursos(pid):
        return sin_cache(jsonify(alm.listar_recursos(pid)))

    @app.post("/api/proyectos/<pid>/recursos")
    def recursos_subir(pid):
        carpeta = request.form.get("carpeta", "recursos")
        guardados, errores = [], []
        for nombre, datos in archivos_subidos("archivos"):
            try:
                guardados.append(alm.guardar_recurso(pid, nombre, datos, carpeta))
            except A.ErrorAlmacen as exc:
                errores.append(f"{nombre}: {exc}")
        return jsonify({"guardados": guardados, "errores": errores})

    @app.delete("/api/proyectos/<pid>/recursos")
    def recursos_borrar(pid):
        alm.borrar_recurso(pid, request.args.get("ruta", ""))
        return jsonify({"ok": True})

    @app.get("/api/proyectos/<pid>/f/<path:ruta>")
    def fichero(pid, ruta):
        p = A.unir(alm.dir_proyecto(pid), ruta)
        if not p.is_file():
            return jsonify({"error": "no existe"}), 404
        tipo = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        return sin_cache(send_file(p, mimetype=tipo))

    @app.get("/api/proyectos/<pid>/vista")
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

    # ------------------------------------------------------------------ LAB: cuadernos celda a celda
    lab = LAB.Lab(alm)
    app.config["lab"] = lab
    graficos = GR.Graficos(alm.datos)

    @app.get("/api/proyectos/<pid>/lab/<nb>")
    def lab_cuaderno(pid, nb):
        return sin_cache(jsonify(lab.sesion(pid, nb).como_dict()))

    @app.put("/api/proyectos/<pid>/lab/<nb>")
    def lab_guardar(pid, nb):
        s = lab.sesion(pid, nb)
        s.guardar(json_body().get("celdas"))
        return jsonify({"ok": True, "rev": s.rev})

    @app.get("/api/proyectos/<pid>/lab/<nb>/estado")
    def lab_estado(pid, nb):
        try:
            desde = int(request.args.get("rev", 0))
        except ValueError:
            desde = 0
        return sin_cache(jsonify(lab.sesion(pid, nb).cambios(desde)))

    @app.post("/api/proyectos/<pid>/lab/<nb>/ejecutar")
    def lab_ejecutar(pid, nb):
        if not (estado().get_json() or {}).get("cuadernos"):
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

    @app.post("/api/proyectos/<pid>/lab/<nb>/<accion>")
    def lab_accion(pid, nb, accion):
        s = lab.sesion(pid, nb)
        if accion == "interrumpir":
            s.interrumpir()
        elif accion == "reiniciar":
            s.reiniciar()
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

    @app.get("/api/lab/plotly.min.js")
    def lab_plotly():
        import importlib.util
        spec = importlib.util.find_spec("plotly")
        p = Path(spec.origin).parent / "package_data" / "plotly.min.js" if spec and spec.origin else None
        if not p or not p.exists():
            return jsonify({"error": "plotly no está instalado"}), 404
        return send_file(p, mimetype="text/javascript", max_age=86400)

    # ------------------------------------------------------------------ LAB: plantillas de gráficos
    @app.get("/api/graficos")
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

    @app.post("/api/graficos")
    def graficos_guardar():
        return jsonify(graficos.guardar(json_body()))

    @app.delete("/api/graficos/<gid>")
    def graficos_borrar(gid):
        graficos.borrar(gid)
        return jsonify({"ok": True})

    @app.get("/api/graficos/<gid>/miniatura")
    def graficos_miniatura(gid):
        p = graficos.miniatura(gid)
        if not p:
            return jsonify({"error": "Sin miniatura"}), 404
        return send_file(p, mimetype="image/png", max_age=0)

    @app.post("/api/graficos/generar")
    def graficos_generar():
        d = json_body()
        t = d.get("plantilla") if isinstance(d.get("plantilla"), dict) else graficos.obtener(str(d.get("id") or ""))
        return jsonify({"codigo": GR.generar(t, d.get("valores") or {}, d.get("colores") or {})})

    @app.post("/api/graficos/probar")
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

    # ------------------------------------------------------------------ cuadernos
    @app.get("/api/proyectos/<pid>/cuadernos")
    def lista_cuadernos(pid):
        meta = alm.meta(pid)
        salida = []
        for c in meta.get("cuadernos", []):
            c = dict(c)
            activos = trabajos.activos(pid, "cuaderno:" + c["id"])
            c["trabajo"] = activos[0].id if activos else None
            salida.append(c)
        return sin_cache(jsonify(salida))

    @app.post("/api/proyectos/<pid>/cuadernos")
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

    @app.patch("/api/proyectos/<pid>/cuadernos/<nb>")
    def cuaderno_cambiar(pid, nb):
        return jsonify(cuadernos.configurar(alm, pid, nb, json_body()))

    @app.delete("/api/proyectos/<pid>/cuadernos/<nb>")
    def cuaderno_borrar(pid, nb):
        lab.cerrar(pid, nb)
        cuadernos.borrar(alm, pid, nb, request.args.get("figuras") == "1")
        return jsonify({"ok": True})

    @app.get("/api/proyectos/<pid>/cuadernos/<nb>/celdas")
    def cuaderno_celdas(pid, nb):
        return jsonify(cuadernos.celdas(alm, pid, nb))

    @app.get("/api/proyectos/<pid>/cuadernos/<nb>/archivos")
    def cuaderno_archivos(pid, nb):
        return sin_cache(jsonify(cuadernos.listar_archivos(alm, pid, nb)))

    @app.post("/api/proyectos/<pid>/cuadernos/<nb>/datos")
    def cuaderno_datos(pid, nb):
        return jsonify({"archivos": cuadernos.agregar_datos(alm, pid, nb, archivos_subidos("datos"))})

    @app.post("/api/proyectos/<pid>/cuadernos/<nb>/ejecutar")
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

    @app.post("/api/proyectos/<pid>/cuadernos/<nb>/importar")
    def cuaderno_importar(pid, nb):
        f = request.files.get("archivo")
        if not f:
            return jsonify({"error": "Falta el zip"}), 400
        return jsonify({"figuras": cuadernos.importar_zip(alm, pid, nb, f.read())})

    @app.get("/api/proyectos/<pid>/cuadernos/<nb>/figuras")
    def cuaderno_figuras(pid, nb):
        return sin_cache(jsonify(cuadernos.figuras(alm, pid, nb)))

    @app.get("/api/proyectos/<pid>/cuadernos/<nb>/celda-colab")
    def cuaderno_celda(pid, nb):
        return Response(cuadernos.celda_exportar(alm, pid, nb), mimetype="text/plain; charset=utf-8")

    @app.get("/api/proyectos/<pid>/cuadernos/<nb>/ejecutado")
    def cuaderno_ejecutado(pid, nb):
        p = alm.dir_proyecto(pid) / "cuadernos" / nb / "ejecutado.ipynb"
        if not p.exists():
            return jsonify({"error": "Aún no se ha ejecutado"}), 404
        return send_file(p, mimetype="application/x-ipynb+json", as_attachment=True,
                         download_name=f"{nb}-ejecutado.ipynb")

    @app.get("/api/explorar")
    def explorar():
        return jsonify(cuadernos.explorar(request.args.get("ruta", ""), raices))

    # ------------------------------------------------------------------ trabajos
    @app.get("/api/proyectos/<pid>/trabajos")
    def trabajos_proyecto(pid):
        return sin_cache(jsonify([t.como_dict(False) for t in trabajos.listar(pid)[:30]]))

    @app.get("/api/trabajos/<tid>")
    def trabajo(tid):
        t = trabajos.obtener(tid)
        if not t:
            return jsonify({"error": "Trabajo no encontrado"}), 404
        return sin_cache(jsonify(t.como_dict(request.args.get("registro", "1") == "1")))

    @app.post("/api/trabajos/<tid>/cancelar")
    def trabajo_cancelar(tid):
        return jsonify({"ok": trabajos.cancelar(tid)})

    return app
