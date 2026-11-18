#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Auditoría en un navegador real: accesibilidad y defensas del servidor local (opcional).

    pip install playwright axe-playwright-python && python -m playwright install chromium
    python tests/auditoria_navegador.py

Comprueba:
  1. axe-core (WCAG 2.0/2.1/2.2 A y AA) sin infracciones en el inicio, el editor, el LAB y el Componente Lab.
  2. Foco en los diálogos: entra al abrir, Tab no sale y vuelve al botón que lo abrió al cerrar.
  3. Una salida HTML maliciosa guardada en un cuaderno no ejecuta código en la página de DocsLab.
  4. Otra web (otro origen) no puede crear proyectos (CSRF) y un nombre ajeno que apunta a 127.0.0.1
     (DNS rebinding, simulado con --host-resolver-rules) recibe 403.
  5. En el editor, el LAB y el Componente Lab, desplazar los paneles con la rueda no desplaza la página
     entera (en 1.6.0 las casillas de los interruptores la alargaban y dejaba un hueco abajo).
"""
from __future__ import annotations

import http.server
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REGLAS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
fallos: list[str] = []


def ok(cond, msg):
    print(("  ok    " if cond else "  FALLO ") + msg, flush=True)
    if not cond:
        fallos.append(msg)


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def peticion(base, ruta, datos=None, metodo="GET", tipo="application/json"):
    cab = {"X-DocsLab": "1"}
    if datos is not None:
        cab["Content-Type"] = tipo
    r = urllib.request.Request(base + ruta, data=datos, headers=cab, method=metodo)
    return json.loads(urllib.request.urlopen(r).read() or b"null")


def cuaderno_malicioso() -> bytes:
    """Un .ipynb con una salida HTML que intenta tocar la página de DocsLab y llamar a su API."""
    ataque = ('<p id="tabla">tabla</p><img src="x" onerror="'
              "try{top.document.title='XSS'}catch(e){};"
              "fetch('/api/proyectos',{method:'POST',headers:{'X-DocsLab':'1','Content-Type':'application/json'},"
              "body:JSON.stringify({nombre:'creado-por-xss'})}).catch(function(){})\">")
    nb = {"nbformat": 4, "nbformat_minor": 5, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}},
          "cells": [{"cell_type": "code", "id": "c1", "metadata": {}, "execution_count": 1, "source": "df",
                     "outputs": [{"output_type": "execute_result", "execution_count": 1, "metadata": {},
                                  "data": {"text/html": ataque, "text/plain": "df"}}]}]}
    return json.dumps(nb).encode()


def subir(base, ruta, campo, nombre, datos: bytes):
    limite = "----docslab"
    cuerpo = (f"--{limite}\r\nContent-Disposition: form-data; name=\"{campo}\"; filename=\"{nombre}\"\r\n"
              f"Content-Type: application/octet-stream\r\n\r\n").encode() + datos + f"\r\n--{limite}--\r\n".encode()
    return peticion(base, ruta, cuerpo, "POST", f"multipart/form-data; boundary={limite}")


def main():
    from playwright.sync_api import sync_playwright
    from axe_playwright_python.sync_playwright import Axe

    tmp = Path(tempfile.mkdtemp(prefix="docslab-auditoria-"))
    puerto, puerto_ajeno = puerto_libre(), puerto_libre()
    python = os.environ.get("DOCSLAB_PYTHON") or sys.executable
    srv = subprocess.Popen([python, str(RAIZ / "servidor.py"), "--puerto", str(puerto), "--datos", str(tmp / "datos")],
                           stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{puerto}/"
    # Una «web ajena» en otro puerto (otro origen) que intenta crear un proyecto en DocsLab
    (tmp / "ajena").mkdir()
    (tmp / "ajena" / "index.html").write_text(f"""<!doctype html><script>
      fetch('{base}api/proyectos', {{method: 'POST', mode: 'no-cors', headers: {{'Content-Type': 'text/plain'}}, body: 'x'}});
      const fd = new FormData(); fd.append('archivo', new Blob(['x']), 'x.zip');
      fetch('{base}api/proyectos/importar', {{method: 'POST', mode: 'no-cors', body: fd}});
    </script>""", encoding="utf-8")
    manejador = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(tmp / "ajena"), **k)  # noqa: E731
    ajena = http.server.ThreadingHTTPServer(("127.0.0.1", puerto_ajeno), manejador)
    threading.Thread(target=ajena.serve_forever, daemon=True).start()
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "api/estado", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        pid = peticion(base, "api/proyectos", json.dumps({"nombre": "Auditoría"}).encode(), "POST")["id"]
        subir(base, f"api/proyectos/{pid}/cuadernos", "cuaderno", "ataque.ipynb", cuaderno_malicioso())

        with sync_playwright() as p:
            nav = p.chromium.launch(args=["--host-resolver-rules=MAP atacante.test 127.0.0.1"])
            pg = nav.new_page(viewport={"width": 1440, "height": 900})
            errores = []
            pg.on("pageerror", lambda e: errores.append(str(e)))
            axe = Axe()

            def revisar_pagina_fija(nombre):
                """Rueda sobre cada panel desplazable: la página no debe moverse ni ser más alta que la ventana."""
                for caja in pg.evaluate("""() => [...document.querySelectorAll('*')].filter(e => {
                        const c = getComputedStyle(e); return /(auto|scroll)/.test(c.overflowY) && e.scrollHeight > e.clientHeight + 4; })
                    .map(e => { const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + Math.min(r.height / 2, 200)]; })"""):
                    pg.mouse.move(*caja)
                    for _ in range(8):
                        pg.mouse.wheel(0, 900)
                    pg.wait_for_timeout(150)
                d = pg.evaluate("() => [scrollY, document.documentElement.scrollHeight, innerHeight]")
                ok(d[0] == 0 and d[1] <= d[2], f"la página no se desplaza al usar la rueda: {nombre} (scrollY {d[0]}, alto {d[1]} de {d[2]})")
                pg.evaluate("() => window.scrollTo(0, 0)")

            def revisar_axe(nombre):
                r = axe.run(pg, options={"runOnly": {"type": "tag", "values": REGLAS}})
                v = r.response["violations"]
                det = "; ".join(f"{x['id']} ({x['impact']}, {len(x['nodes'])}): {x['nodes'][0]['target']}" for x in v)
                ok(not v, f"axe sin infracciones: {nombre}" + (f" → {det}" if v else ""))

            # 1 y 2: inicio, asistente (diálogo) y foco
            pg.goto(base, wait_until="networkidle")
            revisar_axe("inicio")
            boton = pg.locator(".tarjeta-nueva")
            boton.focus()
            pg.keyboard.press("Enter")
            pg.wait_for_selector('[role="dialog"]')
            pg.wait_for_timeout(300)
            dentro = pg.evaluate("() => !!document.activeElement.closest('[role=dialog]')")
            ok(dentro, "el foco entra en el diálogo al abrirlo")
            revisar_axe("asistente (diálogo abierto)")
            fuera = 0
            for _ in range(60):
                pg.keyboard.press("Tab")
                fuera += pg.evaluate("() => !document.activeElement.closest('[role=dialog]')")
            for _ in range(10):
                pg.keyboard.press("Shift+Tab")
                fuera += pg.evaluate("() => !document.activeElement.closest('[role=dialog]')")
            ok(fuera == 0, f"Tab y Mayús+Tab no salen del diálogo ({fuera} veces fuera)")
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(300)
            ok(pg.evaluate("() => document.activeElement.classList.contains('tarjeta-nueva')"),
               "al cerrar, el foco vuelve al botón que abrió el diálogo")
            nombre = pg.locator(".tarjeta-hoja .boton-nombre").first
            ok(nombre.count() == 1 and nombre.evaluate("e => e.tagName") == "BUTTON", "el nombre de cada tarjeta es un botón")

            # 3: editor, LAB y la salida maliciosa
            pg.goto(base + f"#/p/{pid}", wait_until="networkidle")
            pg.wait_for_timeout(2500)
            revisar_axe("editor")
            revisar_pagina_fija("editor")
            pg.click('button[role="tab"]:has-text("LAB")')
            pg.wait_for_timeout(1500)
            if pg.locator("text=ataque").count():
                pg.locator("text=ataque").first.click()
            marco = pg.wait_for_selector("iframe.salida.html", timeout=15000)
            ok(marco.get_attribute("sandbox") == "allow-scripts", "la salida HTML va en un marco aislado")
            pg.wait_for_timeout(1500)
            ok(pg.title() != "XSS", "la salida HTML no puede cambiar la página de DocsLab")
            hay_tabla = marco.content_frame().locator("#tabla").count() == 1
            ok(hay_tabla, "la salida HTML se sigue viendo")
            revisar_axe("LAB con un cuaderno")
            revisar_pagina_fija("LAB")
            pg.goto(base + "#/lab", wait_until="networkidle")
            pg.wait_for_timeout(1500)
            revisar_axe("Componente Lab")
            revisar_pagina_fija("Componente Lab")

            # 4: otra web y DNS rebinding
            otra = nav.new_page()
            otra.goto(f"http://localhost:{puerto_ajeno}/index.html", wait_until="networkidle")
            otra.wait_for_timeout(1500)
            r = otra.goto(f"http://atacante.test:{puerto}/api/proyectos")
            ok(r is not None and r.status == 403, f"un nombre ajeno que apunta a 127.0.0.1 recibe 403 ({r.status if r else '-'})")
            otra.close()
            nav.close()
        nombres = [x["nombre"] for x in json.loads(urllib.request.urlopen(base + "api/proyectos").read())]
        ok(nombres == ["Auditoría"], f"ni la web ajena ni la salida maliciosa crearon proyectos ({nombres})")
        ok(not errores, f"sin errores de JavaScript {errores}")
    finally:
        ajena.shutdown()
        srv.terminate()
    print(f"FALLOS: {len(fallos)}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
