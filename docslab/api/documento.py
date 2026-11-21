# SPDX-License-Identifier: AGPL-3.0-only
"""Salidas del documento: compilar, ajustar a una página, revisar, PDF para imprenta, PowerPoint, Word, PDF, miniatura y zip."""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import threading
import time
from pathlib import Path
from flask import Blueprint, Response, jsonify, request, send_file
from ..nucleo import almacen as A
from ..documento import generador
from ..salidas import compilador
from ..nucleo import modelo as M
from ..salidas import powerpoint as PP, revision, word as W
from ..documento import texto as T

RAIZ_APP = Path(__file__).resolve().parents[2]
ESTATICO = RAIZ_APP / "static"


def registrar(app, c):
    """Registra en «app» las rutas de esta área; «c» trae los objetos compartidos."""
    bp = Blueprint('documento', __name__)
    alm, trabajos, json_body, sin_cache = c.alm, c.trabajos, c.json_body, c.sin_cache

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

    @bp.post("/api/proyectos/<pid>/ajustar")
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

    @bp.post("/api/proyectos/<pid>/revisar")
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
            notas.append("Sin PyMuPDF ni Ghostscript no se puede separar el texto: el documento va como imagen.")
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

    @bp.post("/api/proyectos/<pid>/powerpoint")
    def powerpoint(pid):
        alm.meta(pid)
        opciones = json_body()
        t = trabajos.lanzar("powerpoint", pid, lambda t: _powerpoint(pid, t, opciones), "PowerPoint",
                            exclusivo="compilar")
        return jsonify(t.como_dict(False))

    @bp.get("/api/proyectos/<pid>/powerpoint.pptx")
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

    # ------------------------------------------------------------------ Word
    def _word(pid, t):
        """Documento, artículo o tesis en Word, escrito desde el modelo (todo editable). Se compila
        antes para poder poner como imagen lo que Word no sabe hacer (código LaTeX, componentes)."""
        meta = alm.meta(pid)
        if meta["tipo"] != "estructurado":
            raise ValueError("Word está disponible para los documentos del editor visual")
        modelo = alm.leer_modelo(pid)
        if modelo.get("clase") not in W.CLASES:
            raise ValueError("Word está disponible para documentos, artículos y tesis")
        if not W.disponible()["docx"]:
            raise ValueError("Falta el paquete de Python «python-docx»: instálalo en el entorno de DocsLab "
                             "(python -m pip install python-docx) y reinicia DocsLab")
        d = alm.dir_proyecto(pid)
        build = d / "build"
        build.mkdir(exist_ok=True)
        notas, pdf, posiciones = [], None, None
        try:
            res = _compilar(pid, t)
        except Exception:                                # sin LaTeX también se puede hacer el Word
            res = None
        if res:
            pdf = _pdf_actual(pid, meta, res)
            posiciones = res.get("posiciones") if res.get("ok") else None
            if not pdf.exists():
                pdf = None
        if pdf is None:
            notas.append("El documento no compiló: el código LaTeX libre y los componentes no van en el Word.")
        destino = build / "documento.docx"
        info = W.exportar(modelo, d, destino, pdf, posiciones, informar=lambda msg, pr=None: t.informar(msg, pr))
        datos = dict(info, nombre=A.limpiar_nombre(meta["nombre"], "documento") + ".docx", bytes=destino.stat().st_size,
                     notas=notas + info.get("avisos", []), fecha=time.time(), url=f"api/proyectos/{pid}/word.docx")
        (build / "word.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        t.informar("Word listo", 1.0)
        return datos

    @bp.post("/api/proyectos/<pid>/word")
    def word(pid):
        alm.meta(pid)
        t = trabajos.lanzar("word", pid, lambda t: _word(pid, t), "Word", exclusivo="compilar")
        return jsonify(t.como_dict(False))

    @bp.get("/api/proyectos/<pid>/word.docx")
    def word_docx(pid):
        d = alm.dir_proyecto(pid) / "build"
        try:
            datos = json.loads((d / "word.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return jsonify({"error": "Todavía no hay Word"}), 404
        p = d / "documento.docx"
        if not p.is_file():
            return jsonify({"error": "Todavía no hay Word"}), 404
        return sin_cache(send_file(p, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   as_attachment=request.args.get("descargar") == "1",
                                   download_name=datos.get("nombre") or "documento.docx", max_age=0))

    @bp.post("/api/proyectos/<pid>/imprenta")
    def imprenta(pid):
        alm.meta(pid)
        opciones = json_body()
        t = trabajos.lanzar("imprenta", pid, lambda t: _imprenta(pid, t, opciones), "PDF para imprenta",
                            exclusivo="compilar")
        return jsonify(t.como_dict(False))

    @bp.get("/api/proyectos/<pid>/imprenta.pdf")
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

    @bp.get("/api/proyectos/<pid>/imprenta.png")
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

    @bp.post("/api/proyectos/<pid>/compilar")
    def compilar(pid):
        alm.meta(pid)
        # si ya hay uno esperando, se reutiliza (las ediciones rápidas no se encolan sin fin)
        for t in trabajos.activos(pid, "compilar"):
            if t.estado == "pendiente":
                return jsonify(t.como_dict(False))
        t = trabajos.lanzar("compilar", pid, lambda t: _compilar(pid, t), "Compilar el póster",
                            exclusivo="compilar")
        return jsonify(t.como_dict(False))

    @bp.get("/api/proyectos/<pid>/compilacion")
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

    @bp.get("/api/proyectos/<pid>/pdf")
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

    @bp.get("/api/proyectos/<pid>/miniatura")
    def miniatura(pid):
        p = alm.miniatura(pid)
        if not p:
            return jsonify({"error": "sin miniatura"}), 404
        return sin_cache(send_file(p, mimetype="image/png"))

    @bp.get("/api/proyectos/<pid>/exportar")
    def exportar(pid):
        meta = alm.meta(pid)
        tipo = request.args.get("tipo", "overleaf")
        base = A.limpiar_nombre(meta["nombre"], "poster")
        if tipo == "proyecto":
            datos, nombre = alm.exportar_proyecto(pid), f"{base}-docslab.zip"
        else:
            datos, nombre = alm.exportar_overleaf(pid), f"{base}-overleaf.zip"
        return send_file(io.BytesIO(datos), mimetype="application/zip", as_attachment=True, download_name=nombre)

    app.register_blueprint(bp)
