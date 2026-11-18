# SPDX-License-Identifier: AGPL-3.0-only
"""Genera docs/API.md a partir de las rutas declaradas en docslab/app.py.

Uso (desde la raíz del proyecto):
    python herramientas/doc_api.py            # escribe docs/API.md
    python herramientas/doc_api.py --comprobar  # sale con 1 si docs/API.md está desactualizado
"""
from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
APP = RAIZ / "docslab" / "app.py"
DESTINO = RAIZ / "docs" / "API.md"
METODOS = {"get", "post", "put", "patch", "delete", "route"}

GRUPOS = [
    ("/api/estado", "Estado del servidor"),
    ("/api/variantes", "Catálogo de variantes"),
    ("/api/proyectos/<pid>/cuadernos", "Cuadernos (ejecución completa)"),
    ("/api/proyectos/<pid>/lab", "LAB (núcleo interactivo, celda a celda)"),
    ("/api/proyectos", "Proyectos"),
    ("/api/plantillas", "Plantillas"),
    ("/api/componentes", "Componente Lab"),
    ("/api/graficos", "Plantillas de gráficos"),
    ("/api/lab", "LAB (recursos)"),
    ("/api/bibliografia", "Bibliografía"),
    ("/api/trabajos", "Trabajos en segundo plano"),
    ("/api/explorar", "Explorador de carpetas"),
    ("/", "Aplicación web"),
]


def rutas() -> list[dict]:
    arbol = ast.parse(APP.read_text(encoding="utf-8"))
    out = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.FunctionDef):
            continue
        doc = (ast.get_docstring(nodo) or "").strip().split("\n")[0]
        for dec in nodo.decorator_list:
            if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                    and dec.func.attr in METODOS and dec.args and isinstance(dec.args[0], ast.Constant)):
                metodo = dec.func.attr.upper()
                if metodo == "ROUTE":
                    ms = next((k.value for k in dec.keywords if k.arg == "methods"), None)
                    metodo = "/".join(e.value for e in ms.elts) if isinstance(ms, ast.List) else "GET"
                out.append({"metodo": metodo, "ruta": dec.args[0].value, "funcion": nodo.name,
                            "linea": nodo.lineno, "doc": doc})
    return sorted(out, key=lambda r: (r["ruta"], r["metodo"]))


def grupo(ruta: str) -> str:
    for prefijo, nombre in GRUPOS:
        if ruta == prefijo or ruta.startswith(prefijo.rstrip("/") + "/") or prefijo == "/":
            return nombre
    return "Otros"


def markdown() -> str:
    por_grupo = defaultdict(list)
    lista = rutas()
    for r in lista:
        por_grupo[grupo(r["ruta"])].append(r)
    lineas = [
        "# Referencia de la API HTTP",
        "",
        "> Archivo generado por `herramientas/doc_api.py` a partir de `docslab/app.py`. No editar a mano.",
        "",
        f"Total: **{len(lista)}** combinaciones método + ruta. Base: `http://127.0.0.1:8765`. "
        "Formato: JSON salvo descargas (PDF, PNG, ZIP, PPTX, BIB). Sin autenticación (ver `SECURITY.md`).",
        "",
        "Parámetros de ruta: `<pid>` proyecto · `<tid>` plantilla o trabajo · `<cid>` componente · "
        "`<gid>` plantilla de gráfico · `<nb>` cuaderno · `<path:ruta>` ruta relativa dentro del proyecto.",
        "",
    ]
    for _, nombre in GRUPOS + [("", "Otros")]:
        if nombre not in por_grupo:
            continue
        lineas += [f"## {nombre}", "", "| Método | Ruta | Función (app.py) | Descripción |", "|---|---|---|---|"]
        for r in por_grupo.pop(nombre):
            lineas.append(f"| `{r['metodo']}` | `{r['ruta']}` | `{r['funcion']}` (L{r['linea']}) | {r['doc'] or '—'} |")
        lineas.append("")
    return "\n".join(lineas)


def main(argv=None) -> int:
    texto = markdown()
    if argv and "--comprobar" in argv:
        actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if actual != texto:
            print("docs/API.md está desactualizado: ejecuta python herramientas/doc_api.py")
            return 1
        print("docs/API.md al día.")
        return 0
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text(texto, encoding="utf-8")
    print(f"{DESTINO.relative_to(RAIZ)} · {texto.count(chr(10) + '| `')} rutas")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
