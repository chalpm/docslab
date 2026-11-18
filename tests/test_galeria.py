# SPDX-License-Identifier: AGPL-3.0-only
"""Plantillas de gráficos de la galería y de análisis científico (graficos_galeria.py, graficos_ciencia.py)."""
import ast
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

import pytest

from docslab.lab import graficos as G
from docslab.lab.graficos.ciencia import CATEGORIAS_CIENCIA, CIENCIA
from docslab.lab.graficos.galeria import GALERIA

# Los 41 tipos de gráfico de https://r-graph-gallery.com/ (página de cada uno)
PAGINAS_GALERIA = {
    "violin.html", "density-plot.html", "histogram.html", "boxplot.html", "ridgeline-plot.html", "beeswarm.html",
    "scatterplot.html", "heatmap.html", "correlogram.html", "bubble-chart.html", "connected-scatterplot.html",
    "2d-density-chart.html", "barplot.html", "spider-or-radar-chart.html", "wordcloud.html", "parallel-plot.html",
    "lollipop-plot.html", "circular-barplot.html", "table.html", "stacked-barplot.html", "treemap.html",
    "doughnut-plot.html", "pie-plot.html", "dendrogram.html", "circle-packing.html", "waffle.html", "line-plot.html",
    "area-chart.html", "stacked-area-graph.html", "streamgraph.html", "time-series.html", "map.html",
    "choropleth-map.html", "hexbin-map.html", "cartogram.html", "connection-map.html", "bubble-map.html",
    "chord-diagram.html", "network.html", "sankey-diagram.html", "arc-diagram.html",
    "hierarchical-edge-bundling.html",
}
COLORES = {"primario": "2F4858", "acento": "C8553D"}


def test_cada_tipo_de_la_galeria_tiene_plantilla():
    cubiertas = {t["referencia"].rsplit("/", 1)[-1] for t in G.INCLUIDAS if t.get("referencia")}
    assert PAGINAS_GALERIA <= cubiertas, sorted(PAGINAS_GALERIA - cubiertas)


def test_ids_unicos_y_metadatos():
    ids = [t["id"] for t in G.INCLUIDAS]
    assert len(ids) == len(set(ids))
    for t in G.INCLUIDAS:
        assert t["categoria"] in G.CATEGORIAS, t["id"]
        if t["categoria"] not in CATEGORIAS_CIENCIA:           # las de la galería enlazan a su página
            assert t["referencia"].startswith("https://r-graph-gallery.com/"), t["id"]
        assert t["biblioteca"] in G.BIBLIOTECAS
        for a in G.archivos_ejemplo(t):
            assert (G.DIR_EJEMPLOS / a).is_file(), (t["id"], a)


@pytest.mark.parametrize("t", G.INCLUIDAS, ids=lambda t: t["id"])
def test_el_codigo_es_python_valido(t):
    ast.parse(G.generar(t, {}, COLORES), feature_version=(3, 9))


def test_el_codigo_compila_en_un_python_antiguo(tmp_path):
    """ast.parse(feature_version=…) no detecta todo (p. ej., comillas anidadas en f-strings, válidas
    solo desde 3.12): se compila de verdad con el Python más antiguo que haya instalado."""
    antiguo = next((p for p in ("python3.9", "python3.10", "python3.11") if shutil.which(p)), None)
    if not antiguo:
        pytest.skip("no hay un Python 3.9–3.11 instalado")
    for t in G.INCLUIDAS:
        (tmp_path / (t["id"].replace("-", "_") + ".py")).write_text(G.generar(t, {}, COLORES), encoding="utf-8")
    r = subprocess.run([antiguo, "-c", "import sys, glob\nmalos = []\nfor f in glob.glob(sys.argv[1] + '/*.py'):\n"
                        "    try:\n        compile(open(f, encoding='utf-8').read(), f, 'exec')\n"
                        "    except SyntaxError as e:\n        malos.append(f'{f}: {e}')\nprint(chr(10).join(malos))",
                        str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0 and not r.stdout.strip(), r.stdout + r.stderr


def test_los_numeros_pequenos_no_se_redondean_a_cero():
    assert G.valor_py({"tipo": "numero", "defecto": 5e-8}, None, {}) == "5e-08"
    assert G.valor_py({"tipo": "numero", "defecto": 0.05}, None, {}) == "0.05"
    assert G.valor_py({"tipo": "numero", "defecto": 3}, None, {}) == "3"


def test_las_plantillas_de_la_galeria_dibujan_con_sus_datos_de_ejemplo():
    pytest.importorskip("matplotlib")
    pytest.importorskip("seaborn")
    pytest.importorskip("scipy")

    def probar(t):
        r = G.probar(G.generar(t, {}, COLORES), tiempo=180)
        return t["id"], r["ok"] and bool(r.get("imagen")), r["error"][-400:]

    with ThreadPoolExecutor(max(1, min(4, os.cpu_count() or 1))) as ex:
        fallos = [(i, e) for i, ok, e in ex.map(probar, GALERIA) if not ok]
    assert not fallos, fallos


def test_las_plantillas_cientificas_dibujan_con_sus_datos_de_ejemplo():
    pytest.importorskip("sklearn")
    pytest.importorskip("scipy")

    def probar(t):
        r = G.probar(G.generar(t, {}, COLORES), tiempo=240)
        return t["id"], r["ok"] and bool(r.get("imagen")), r["error"][-400:]

    with ThreadPoolExecutor(max(1, min(4, os.cpu_count() or 1))) as ex:
        fallos = [(i, e) for i, ok, e in ex.map(probar, CIENCIA) if not ok]
    assert not fallos, fallos


def test_pedidos_de_las_plantillas_cientificas():
    ids = {t["id"] for t in CIENCIA}
    assert {"pca", "pca-3d", "tsne", "tsne-3d"} <= ids
    assert all(t["categoria"] in CATEGORIAS_CIENCIA for t in CIENCIA)
    km = next(t for t in CIENCIA if t["id"] == "kaplan-meier")
    assert G.archivos_ejemplo(km) == ["ejemplo_supervivencia.csv"]


def test_usar_datos_de_ejemplo_copia_los_de_la_plantilla(cliente):
    pid = cliente.post("/api/proyectos", json={"nombre": "lab", "asistente": {"clase": "poster"}}).get_json()["id"]
    nb_id = cliente.post(f"/api/proyectos/{pid}/cuadernos", json={"nuevo": "Análisis"}).get_json()["id"]
    t = next(x for x in cliente.get("/api/graficos").get_json()["plantillas"] if x["id"] == "coropletas")
    assert t["ejemplo"] == ["ejemplo_paises.csv", "mundo.geojson"]
    r = cliente.post(f"/api/proyectos/{pid}/lab/{nb_id}/ejemplo", json={"archivos": t["ejemplo"]}).get_json()
    assert r["archivo"] == "ejemplo_paises.csv"
    rutas = {a["ruta"] for a in cliente.get(f"/api/proyectos/{pid}/cuadernos/{nb_id}/archivos").get_json()}
    assert {"ejemplo_paises.csv", "mundo.geojson"} <= rutas
    # solo nombres de datos_ejemplo/: nada de rutas
    malo = cliente.post(f"/api/proyectos/{pid}/lab/{nb_id}/ejemplo", json={"archivos": ["../../app.py"]}).get_json()
    assert malo["archivo"] == "ejemplo.csv"
    cliente.application.config["lab"].apagar_todo()
