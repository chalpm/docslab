# SPDX-License-Identifier: AGPL-3.0-only
"""LAB: cuadernos celda a celda y plantillas de gráficos."""
import time

import pytest

from conftest import hay_nucleo
from docslab import graficos as G


def _proyecto(cliente):
    pid = cliente.post("/api/proyectos", json={"nombre": "lab", "asistente": {"clase": "poster"}}).get_json()["id"]
    nb = cliente.post(f"/api/proyectos/{pid}/cuadernos", json={"nuevo": "Análisis"}).get_json()
    return pid, nb["id"]


def _esperar(cliente, pid, nb, rev=0, tiempo=90):
    fin = time.time() + tiempo
    while time.time() < fin:
        e = cliente.get(f"/api/proyectos/{pid}/lab/{nb}/estado?rev={rev}").get_json()
        if e["nucleo"]["estado"] != "ocupado":
            return e
        time.sleep(0.2)
    raise AssertionError("el núcleo no terminó")


def test_cuaderno_nuevo_y_edicion(cliente):
    pid, nb = _proyecto(cliente)
    d = cliente.get(f"/api/proyectos/{pid}/lab/{nb}").get_json()
    assert [c["tipo"] for c in d["celdas"]] == ["texto", "codigo"] and d["nucleo"]["estado"] == "apagado"
    celdas = d["celdas"] + [{"id": "nueva1", "tipo": "codigo", "fuente": "x = 1", "meta": {"plantilla": "barras"}}]
    celdas.reverse()
    assert cliente.put(f"/api/proyectos/{pid}/lab/{nb}", json={"celdas": celdas}).status_code == 200
    d2 = cliente.get(f"/api/proyectos/{pid}/lab/{nb}").get_json()
    assert [c["id"] for c in d2["celdas"]] == [c["id"] for c in celdas]
    assert d2["celdas"][0]["meta"] == {"plantilla": "barras"} and d2["celdas"][0]["fuente"] == "x = 1"


@hay_nucleo
def test_ejecutar_celda_a_celda_conserva_las_variables(cliente):
    pid, nb = _proyecto(cliente)
    base = f"/api/proyectos/{pid}/lab/{nb}"
    celdas = [{"id": "a", "tipo": "codigo", "fuente": "x = 20"},
              {"id": "b", "tipo": "codigo", "fuente": "print(x + 1)\nx * 2"},
              {"id": "c", "tipo": "codigo", "fuente": "1 / 0"},
              {"id": "d", "tipo": "codigo", "fuente": "print('no llega')"}]
    try:
        assert cliente.post(base + "/ejecutar", json={"celdas": celdas, "ids": ["a"]}).status_code == 200
        _esperar(cliente, pid, nb)
        cliente.post(base + "/ejecutar", json={"ids": ["b"]})
        e = _esperar(cliente, pid, nb)
        b = next(c for c in e["celdas"] if c["id"] == "b")
        assert [s["t"] for s in b["salidas"]] == ["texto", "texto"]
        assert b["salidas"][0]["texto"].strip() == "21" and b["salidas"][1]["texto"] == "40" and b["n"] == 2
        # todo: se detiene en el primer error
        cliente.post(base + "/ejecutar", json={"todas": True})
        e = _esperar(cliente, pid, nb)
        por = {c["id"]: c for c in e["celdas"]}
        assert por["c"]["salidas"][0]["t"] == "error" and por["c"]["salidas"][0]["nombre"] == "ZeroDivisionError"
        assert por["d"]["salidas"] == [] and e["nucleo"]["estado"] == "listo"
        # las salidas quedan en el .ipynb
        d = cliente.get(base).get_json()
        assert next(c for c in d["celdas"] if c["id"] == "b")["salidas"]
        # reiniciar borra las variables
        cliente.post(base + "/reiniciar")
        cliente.post(base + "/ejecutar", json={"ids": ["b"]})
        e = _esperar(cliente, pid, nb)
        assert next(c for c in e["celdas"] if c["id"] == "b")["salidas"][0]["nombre"] == "NameError"
    finally:
        cliente.application.config["lab"].apagar_todo()


@hay_nucleo
def test_un_grafico_de_plantilla_llega_al_documento(cliente):
    pytest.importorskip("matplotlib")
    pytest.importorskip("pandas")
    pid, nb = _proyecto(cliente)
    base = f"/api/proyectos/{pid}/lab/{nb}"
    try:
        assert cliente.post(base + "/ejemplo").get_json()["archivo"] == "ejemplo.csv"
        cols = cliente.post(base + "/columnas", json={"datos": {"modo": "archivo", "archivo": "ejemplo.csv"}}).get_json()
        assert {"nombre": "valor", "numerica": True} in cols["columnas"] and cols["filas"] == 72
        codigo = cliente.post("/api/graficos/generar", json={"id": "barras", "valores": {"color": "#112233"},
                                                             "colores": {"primario": "AA0000"}}).get_json()["codigo"]
        assert '"#112233"' in codigo and "{{" not in codigo
        cliente.post(base + "/ejecutar", json={"celdas": [{"id": "g", "tipo": "codigo", "fuente": codigo}], "ids": ["g"]})
        e = _esperar(cliente, pid, nb)
        g = e["celdas"][0]
        assert [s["t"] for s in g["salidas"]] == ["img"], g["salidas"]
        assert e["nucleo"]["figuras_nuevas"] == 1
        figs = cliente.get(f"/api/proyectos/{pid}/cuadernos/{nb}/figuras").get_json()
        assert [f["nombre"] for f in figs] == ["barras.pdf"]
        assert cliente.post(base + "/variables").get_json()["variables"][0]["nombre"] == "datos"
    finally:
        cliente.application.config["lab"].apagar_todo()


@hay_nucleo
def test_borrar_variables_conserva_el_proceso_y_reiniciar_lo_cambia(cliente):
    """«Borrar las variables» es un %reset en el mismo Python; «Reiniciar» arranca otro proceso (así se
    cargan los paquetes recién instalados)."""
    pid, nb = _proyecto(cliente)
    base = f"/api/proyectos/{pid}/lab/{nb}"
    celdas = [{"id": "a", "tipo": "codigo", "fuente": "import os\nx = 41\nprint(os.getpid())"},
              {"id": "b", "tipo": "codigo", "fuente": "import os\nprint('x' in dir(), os.getpid())"}]

    def correr(cid):
        cliente.post(base + "/ejecutar", json={"ids": [cid]})
        e = _esperar(cliente, pid, nb)
        return next(c for c in e["celdas"] if c["id"] == cid)["salidas"][0]["texto"].split()

    try:
        # con Python apagado no hay nada que borrar, y no falla
        assert cliente.post(base + "/borrar-variables").status_code == 200
        cliente.put(base, json={"celdas": celdas})
        proceso = correr("a")[0]
        assert cliente.post(base + "/borrar-variables").status_code == 200
        hay_x, mismo = correr("b")
        assert hay_x == "False" and mismo == proceso            # sin variables, mismo proceso
        assert cliente.get(base).get_json()["nucleo"]["estado"] == "listo"
        correr("a")
        cliente.post(base + "/reiniciar")
        assert cliente.get(base).get_json()["nucleo"]["estado"] == "apagado"
        hay_x, otro = correr("b")
        assert hay_x == "False" and otro != proceso              # proceso nuevo
    finally:
        cliente.application.config["lab"].apagar_todo()


def test_una_celda_no_se_queda_colgada_si_se_pierde_el_idle():
    """Si el «idle» del canal iopub no llega pero Python ya contestó en el canal shell, la celda termina
    a los pocos segundos (antes esperaba el límite entero, hasta 1 h)."""
    import queue
    import threading

    import nbformat

    from docslab import lab as L

    class Cliente:
        iopub = [{"parent_header": {"msg_id": "m"}, "msg_type": "stream", "header": {"msg_type": "stream"},
                  "content": {"name": "stdout", "text": "hola\n"}}]
        shell = [{"parent_header": {"msg_id": "m"}, "msg_type": "execute_reply", "content": {"status": "ok"}}]

        def execute(self, *a, **k):
            return "m"

        def get_iopub_msg(self, timeout=1):
            if self.iopub:
                return self.iopub.pop(0)
            raise queue.Empty

        def get_shell_msg(self, timeout=0):
            if self.shell:
                return self.shell.pop(0)
            raise queue.Empty

    class Gestor:
        def is_alive(self):
            return True

    s = L.Sesion.__new__(L.Sesion)
    s.kc, s.km, s.mutex, s.rev, s.revs, s.interrumpido = Cliente(), Gestor(), threading.RLock(), 0, {}, False
    cel = nbformat.v4.new_code_cell("print('hola')", id="c1")
    inicio = time.time()
    assert s._una(cel, 3600) is True
    assert time.time() - inicio < 10 and [o["output_type"] for o in cel.outputs] == ["stream"]


def test_generar_codigo_de_plantilla():
    t = next(x for x in G.INCLUIDAS if x["id"] == "lineas")
    codigo = G.generar(t, {"datos": {"modo": "variable", "variable": "df"}, "grupo": "", "titulo": 'Con "comillas"',
                           "paleta": "viridis"}, {})
    assert "datos = df\n" in codigo and "if not None" in codigo and r'"Con \"comillas\""' in codigo
    assert 'colores = "viridis"' in codigo
    compile(codigo, "<plantilla>", "exec")
    doc = G.generar(t, {}, {"primario": "#1f3a5f", "acento": "c8553d"})
    assert '["#1F3A5F", "#C8553D"' in doc
    with pytest.raises(Exception):
        G.generar({"nombre": "x", "codigo": "print({{falta}})", "parametros": []}, {})


@pytest.mark.parametrize("t", G.INCLUIDAS, ids=lambda t: t["id"])
def test_las_plantillas_incluidas_generan_python_valido(t):
    compile(G.generar(t, {}, {}), t["id"], "exec")


def test_plantillas_propias(cliente):
    cat = cliente.get("/api/graficos").get_json()
    assert len(cat["plantillas"]) == len(G.INCLUIDAS) and all(t["incluida"] for t in cat["plantillas"])
    mia = dict(cat["nueva"], nombre="Mi gráfico", codigo="print({{titulo}})")
    g = cliente.post("/api/graficos", json=mia).get_json()
    assert g["id"].startswith("g-")
    g["nombre"] = "Otro nombre"
    assert cliente.post("/api/graficos", json=g).get_json()["id"] == g["id"]
    lista = cliente.get("/api/graficos").get_json()["plantillas"]
    assert lista[0]["nombre"] == "Otro nombre" and len(lista) == len(G.INCLUIDAS) + 1
    # una incluida no se pisa: se guarda como copia
    copia = cliente.post("/api/graficos", json=dict(G.INCLUIDAS[0], nombre="Barras mías")).get_json()
    assert copia["id"].startswith("g-")
    cliente.delete(f"/api/graficos/{g['id']}")
    assert len(cliente.get("/api/graficos").get_json()["plantillas"]) == len(G.INCLUIDAS) + 1


def test_probar_una_plantilla_con_los_datos_de_ejemplo(cliente):
    pytest.importorskip("matplotlib")
    pytest.importorskip("pandas")
    r = cliente.post("/api/graficos/probar", json={"id": "histograma"}).get_json()
    assert r["ok"] and r["imagen"].startswith("data:image/png;base64,")
    malo = cliente.post("/api/graficos/probar", json={"plantilla": {"nombre": "x", "codigo": "1/0", "parametros": []}}).get_json()
    assert not malo["ok"] and "ZeroDivisionError" in malo["error"]
