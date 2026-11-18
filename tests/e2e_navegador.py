#!/usr/bin/env python3
"""Prueba de extremo a extremo en un navegador real (opcional; necesita Playwright y Chromium).

    pip install playwright && python -m playwright install chromium
    python tests/e2e_navegador.py
    DOCSLAB_PYTHON=.venv/bin/python python tests/e2e_navegador.py   # el servidor con otro Python

Arranca DocsLab en un puerto libre con una carpeta de datos temporal y recorre
lo principal: asistente, editor, títulos, elementos, capas, errores, referencias,
edición directa, tipografías, revisión para imprimir, PDF para imprenta, PowerPoint, plantillas,
descargas y el Componente Lab.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
fallos: list[str] = []


def ok(cond, msg):
    print(("  ok    " if cond else "  FALLO ") + msg, flush=True)
    if not cond:
        fallos.append(msg)


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    from playwright.sync_api import sync_playwright

    tmp = Path(tempfile.mkdtemp(prefix="docslab-e2e-"))
    puerto = puerto_libre()
    python = os.environ.get("DOCSLAB_PYTHON") or sys.executable      # p. ej. .venv/bin/python
    srv = subprocess.Popen([python, str(RAIZ / "servidor.py"), "--puerto", str(puerto), "--datos", str(tmp / "datos"),
                            "--raices", str(tmp)], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{puerto}/"
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "api/estado", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        with sync_playwright() as p:
            nav = p.chromium.launch()
            pg = nav.new_page(viewport={"width": 1440, "height": 900}, accept_downloads=True)
            errores = []
            pg.on("pageerror", lambda e: errores.append(str(e)))

            def modelo(pid):
                return pg.evaluate(f"fetch('api/proyectos/{pid}').then(r => r.json()).then(d => d.modelo)")

            def esperar_compilacion(t=60):
                t0 = time.time()
                time.sleep(1.2)          # guardado (0.7 s) + inicio de la compilación
                while time.time() - t0 < t:
                    if not pg.locator(".barra .chip.trabajando, .barra .chip.aviso-chip").count():
                        return
                    time.sleep(0.3)

            pg.goto(base, wait_until="networkidle")
            ok(pg.locator(".tarjeta-hoja").count() >= 7, "inicio con plantillas")
            # asistente
            pg.click(".cabeza .btn.primario")
            pg.fill(".dialogo input.entrada", "Prueba e2e")
            pg.click(".dialogo footer .btn.primario")
            pg.wait_for_selector(".hoja canvas", timeout=90000)
            pid = pg.evaluate("location.hash.split('/').pop()")
            ok(pid.startswith("p-"), "el asistente crea el póster y lo compila")
            # caja: título oculto desde el inspector
            m = modelo(pid)
            b = m["filas"][0]["columnas"][0]["bloques"][0]
            pg.click(f".fila-nodo[data-id='{b['id']}']")
            pg.fill(".inspector .tarjeta-titulo input.entrada", "Introducción nueva")
            pg.click(".inspector .tarjeta-titulo .interruptor")
            esperar_compilacion()
            b2 = modelo(pid)["filas"][0]["columnas"][0]["bloques"][0]
            ok(b2["titulo"] == "Introducción nueva" and b2["mostrar_titulo"] is False, "título editado y oculto")
            # añadir un elemento con el selector de variantes
            pg.click(".inspector .acciones-insp .btn.primario")
            pg.fill(".dialogo input.entrada", "cifra destacada")
            pg.click(".dialogo .variante")
            esperar_compilacion()
            tipos = [e["tipo"] for e in modelo(pid)["filas"][0]["columnas"][0]["bloques"][0]["elementos"]]
            ok("txtCifra" in tipos, "elemento añadido desde el selector de variantes")
            # capa: texto nuevo y arrastre en la vista previa
            pg.click(".fila-nodo[data-id='frente']")
            pg.click(".inspector .acciones-insp .btn:has-text('Texto')")
            esperar_compilacion()
            pg.wait_for_selector(".marco.capa.seleccionado", timeout=30000)
            caja = pg.locator(".marco.capa.seleccionado").bounding_box()
            x, y = caja["x"] + caja["width"] / 2, caja["y"] + caja["height"] / 2
            pg.mouse.move(x, y)
            pg.mouse.down()
            pg.mouse.move(x + 120, y - 80, steps=6)
            pg.mouse.up()
            esperar_compilacion()
            it = modelo(pid)["capas"][1]["elementos"][-1]
            ok(float(it["x"]) > 0.55 and float(it["y"]) < 0.45, f"arrastrar un elemento de capa ({it['x']}, {it['y']})")
            # deshacer
            pg.click(".mesa", position={"x": 15, "y": 15})
            pg.keyboard.press("Control+z")
            esperar_compilacion()
            it2 = modelo(pid)["capas"][1]["elementos"][-1]
            ok(abs(float(it2["x"]) - 0.5) < 1e-6, "deshacer el arrastre")
            # error de LaTeX localizado
            e = modelo(pid)["filas"][0]["columnas"][0]["bloques"][0]["elementos"][0]
            pg.click(f".fila-nodo[data-id='{b['id']}'] .flecha") if not pg.locator(f".fila-nodo[data-id='{e['id']}']").count() else None
            pg.click(f".fila-nodo[data-id='{e['id']}']")
            pg.fill(".inspector textarea.entrada", "Texto {{\\ordenquenoexiste}}")
            esperar_compilacion()
            pg.wait_for_selector(".registro .mensaje.error", timeout=60000)
            pg.click(".fila-nodo[data-id='poster']")
            pg.click(".registro .mensaje.error .btn")
            sel = pg.evaluate("document.querySelector('.fila-nodo.seleccionado').dataset.id")
            ok(sel == e["id"], "el error lleva al elemento que lo causa")
            pg.fill(".inspector textarea.entrada", "Texto corregido")
            esperar_compilacion()
            ok(pg.locator(".registro .mensaje.error").count() == 0, "el error desaparece")
            # referencias: importar BibTeX y citarla en el párrafo
            pg.click(".panel.izq .pestanas button[aria-label='Referencias']")
            pg.click(".acciones-refs .btn:has-text('Importar')")
            pg.fill(".fondo-dialogo textarea[aria-label^='Texto en BibTeX']",
                    "@article{garcia2020, author = {García, Ana and López, Beatriz}, title = {Un artículo de prueba},"
                    " journal = {Revista de Prueba}, year = {2020}, volume = {3}, pages = {1--9}}")
            pg.click(".fondo-dialogo .btn:has-text('Leer el texto')")
            pg.wait_for_selector(".fondo-dialogo .fila-importar", timeout=20000)
            pg.click(".fondo-dialogo footer .btn.primario")
            pg.wait_for_selector(".lista-refs .ref", timeout=20000)
            esperar_compilacion()
            refs = modelo(pid)["bibliografia"]["referencias"]
            ok(len(refs) == 1 and refs[0]["clave"] == "garcia2020", "importar una referencia en BibTeX")
            pg.click(".panel.izq .pestanas button[aria-label='Estructura']")
            pg.click(f".fila-nodo[data-id='{e['id']}']")
            pg.fill(".inspector textarea.entrada", "Como se ha descrito [@garcia2020].")
            esperar_compilacion()
            comp = pg.evaluate(f"fetch('api/proyectos/{pid}/compilacion').then(r => r.json())")
            ok(comp["ok"] and not comp.get("errores"), "citar la referencia en un texto")
            # edición directa: doble clic sobre el párrafo en la vista previa
            pg.locator(f".marco[data-id='{e['id']}']").dblclick()
            pg.wait_for_selector(".editor-en-vista textarea", timeout=10000)
            pg.locator(".editor-en-vista textarea").first.fill("Escrito sobre el póster [@garcia2020].")
            pg.keyboard.press("Escape")
            ok(pg.locator(".editor-en-vista").count() == 0, "Esc cierra el cuadro de edición directa")
            esperar_compilacion()
            e_nuevo = modelo(pid)["filas"][0]["columnas"][0]["bloques"][0]["elementos"][0]
            ok(any("sobre el póster" in str(v) for v in e_nuevo.values()), "escribir con doble clic en la vista previa")
            # tipografía libre (si está instalada) desde el diseño general
            pg.click(".fila-nodo[data-id='poster']")
            pg.wait_for_selector(".tipografias select")
            disponible = pg.evaluate("fetch('api/estado').then(r => r.json()).then(d => d.familias && d.familias.roboto)")
            if disponible:
                pg.locator(".tipografias select").nth(0).select_option("roboto")
                esperar_compilacion()
                comp = pg.evaluate(f"fetch('api/proyectos/{pid}/compilacion').then(r => r.json())")
                ok(comp["ok"] and modelo(pid)["tipografia"]["familia"] == "roboto", "cambiar a una tipografía libre")
            # revisión para imprimir
            pg.click(".barra .btn:has-text('Descargar')")
            pg.click(".menu button:has-text('Revisar para imprimir')")
            pg.wait_for_selector(".revision .seccion-revision", timeout=90000)
            secciones = pg.locator(".revision .cabeza-seccion .nombre-seccion").all_inner_texts()
            ok({"Imágenes", "Tamaño de letra", "Contenido"} <= set(secciones), f"revisión para imprimir ({len(secciones)} secciones)")
            ok(pg.locator(".revision .titulo-item:has-text('Falta una imagen')").count() >= 1,
               "la revisión avisa de la imagen que falta")
            # PDF para imprenta desde el panel de revisión
            pg.click(".revision .btn:has-text('PDF para imprenta')")
            pg.wait_for_selector(".dialogo-imprenta")
            with pg.expect_download(timeout=120000) as d:
                pg.click(".dialogo-imprenta .btn:has-text('Preparar y descargar')")
            ok(d.value.suggested_filename.endswith("-imprenta.pdf"), "PDF para imprenta")
            pg.click(".dialogo-imprenta footer .btn:has-text('Cerrar')")
            pg.click(".revision button[aria-label='Cerrar la revisión']")
            # PowerPoint con el texto editable
            pg.click(".barra .btn:has-text('Descargar')")
            pg.click(".menu button:has-text('PowerPoint')")
            pg.wait_for_selector(".dialogo-powerpoint")
            if pg.locator(".dialogo-powerpoint input[value='editable']:not([disabled])").count():
                pg.check(".dialogo-powerpoint input[value='editable']")
            with pg.expect_download(timeout=240000) as d:
                pg.click(".dialogo-powerpoint .btn.primario")
            ok(d.value.suggested_filename.endswith(".pptx"), "exportar a PowerPoint")
            pg.click(".dialogo-powerpoint footer .btn:has-text('Cerrar')")
            # descargas
            with pg.expect_download() as d:
                pg.click(".barra .btn:has-text('Descargar')")
                pg.click(".menu button:has-text('PDF del póster')")
            ok(d.value.suggested_filename.endswith(".pdf"), "descargar el PDF")
            # plantilla
            pg.click(".barra button[aria-label='Más opciones']")
            pg.click(".menu button:has-text('Guardar como plantilla')")
            pg.fill(".fondo-dialogo input.entrada", "Plantilla e2e")
            pg.click(".fondo-dialogo .btn.primario")
            time.sleep(5)
            nombres = pg.evaluate("fetch('api/plantillas').then(r => r.json()).then(d => d.map(p => p.nombre))")
            ok("Plantilla e2e" in nombres, "guardar como plantilla")
            pg.click(".barra button[aria-label='Más opciones']")
            pg.click(".menu button:has-text('Actualizar la plantilla')")
            pg.click(".fondo-dialogo .btn.primario")
            pg.wait_for_function("() => [...document.querySelectorAll('.aviso')].some(a => a.textContent.includes('actualizada'))",
                                 timeout=60000)
            act = pg.evaluate("fetch('api/plantillas').then(r => r.json()).then(d => d.filter(p => p.nombre === 'Plantilla e2e').map(p => !!p.actualizada))")
            ok(act == [True], "actualizar la plantilla desde el póster")
            # Componente Lab: uno sin código, guardado y usado en el póster
            pg.goto(base + "#/lab", wait_until="networkidle")
            pg.wait_for_selector(".bienvenida-lab .inicio-lab", timeout=30000)
            pg.locator(".bienvenida-lab .inicio-lab").first.click()
            pg.wait_for_selector(".vista-lab .recorte", timeout=90000)
            pg.fill(".lab .barra input.titulo-proyecto", "Componente e2e")
            pg.click(".lab .barra .btn.primario:has-text('Guardar')")
            pg.wait_for_function("() => location.hash.startsWith('#/lab/') && !location.hash.endsWith('/nuevo')", timeout=30000)
            lista = pg.evaluate("fetch('api/componentes').then(r => r.json())")
            cid = next((c["id"] for c in lista if c["nombre"] == "Componente e2e"), None)
            ok(cid is not None, "crear y guardar un componente en el Componente Lab")
            pg.goto(base + f"#/p/{pid}", wait_until="networkidle")
            pg.wait_for_selector(".hoja canvas", timeout=90000)
            pg.click(f".fila-nodo[data-id='{b['id']}']")
            pg.click(".inspector .acciones-insp .btn.primario")
            pg.fill(".dialogo input.entrada", "Componente e2e")
            pg.click(".dialogo .seccion-propios .variante")
            esperar_compilacion()
            m = modelo(pid)
            tipos = [x["tipo"] for x in m["filas"][0]["columnas"][0]["bloques"][0]["elementos"]]
            comp = pg.evaluate(f"fetch('api/proyectos/{pid}/compilacion').then(r => r.json())")
            ok(f"cmp:{cid}" in tipos and cid in m.get("componentes", {}) and comp["ok"],
               "usar el componente propio en el póster")
            # logos de la cabecera: elegir uno en la vista previa y estirarlo desde la esquina
            pg.evaluate(f"""async () => {{
                const c = document.createElement('canvas'); c.width = 300; c.height = 300;
                const g = c.getContext('2d'); g.fillStyle = '#2b5a8a'; g.fillRect(0, 0, 300, 300);
                const b = await new Promise((r) => c.toBlob(r, 'image/png'));
                const fd = new FormData(); fd.append('archivos', b, 'logo.png');
                await fetch('api/proyectos/{pid}/recursos', {{method: 'POST', body: fd}});
                const m = (await (await fetch('api/proyectos/{pid}')).json()).modelo;
                m.cabecera.logo_izquierdo = 'recursos/logo.png';
                await fetch('api/proyectos/{pid}/modelo', {{method: 'PUT', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(m)}});
                const t = await (await fetch('api/proyectos/{pid}/compilar', {{method: 'POST'}})).json();
                for (let i = 0; i < 300; i++) {{
                    const x = await (await fetch('api/trabajos/' + t.id)).json();
                    if (['terminado', 'error', 'cancelado'].includes(x.estado)) break;
                    await new Promise((r) => setTimeout(r, 300));
                }}
            }}""")
            pg.reload(wait_until="networkidle")
            pg.wait_for_selector(".marco[data-id='cabecera-logo-izq']", timeout=90000)
            logo = pg.locator(".marco[data-id='cabecera-logo-izq']")
            logo.click()
            pg.wait_for_selector(".inspector .seccion.resaltada")
            caja = pg.locator(".marco[data-id='cabecera-logo-izq'] .tirador").bounding_box()
            x, y = caja["x"] + caja["width"] / 2, caja["y"] + caja["height"] / 2
            pg.mouse.move(x, y)
            pg.mouse.down()
            pg.mouse.move(x + 40, y + 40, steps=6)
            pg.mouse.up()
            esperar_compilacion()
            tam = modelo(pid)["cabecera"].get("tam_logo_izquierdo")
            ok(isinstance(tam, (int, float)) and tam > 100, f"estirar un logo desde la vista previa ({tam} %)")
            ok(not errores, f"sin errores de JavaScript {errores[:3]}")
            nav.close()
    finally:
        srv.terminate()
    print("\nFALLOS:", len(fallos))
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
