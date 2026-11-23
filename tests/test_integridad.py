# SPDX-License-Identifier: AGPL-3.0-only
"""Integridad de los datos (auditoría de entrega, 2026-11-22).

H-01: un zip con un proyecto.json raro no debe dejar carpetas a medias ni romper la lista de proyectos.
H-02: guardar a la vez no debe dar errores ni dañar modelo.json o proyecto.json; un modelo dañado
      no se abre en blanco (el siguiente guardado borraría el documento).
"""
import io
import json
import threading
import zipfile

import pytest

from docslab.nucleo import almacen as A


def _zip(entradas: dict) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for n, d in entradas.items():
            z.writestr(n, d)
    return b.getvalue()


def _importar(c, datos):
    return c.post("/api/proyectos/importar", data={"archivo": (io.BytesIO(datos), "x.zip")},
                  content_type="multipart/form-data")


@pytest.fixture
def c(cliente, tmp_path):
    cliente.dir_proyectos = tmp_path / "datos" / "proyectos"
    return cliente


# ---------------------------------------------------------------------- H-01
@pytest.mark.parametrize("proyecto_json", ["[1, 2]", '"texto"', "42", '{"principal": 5}', '{"ajustes": []}',
                                           '{"cuadernos": "no"}'])
def test_h01_zip_con_proyecto_json_raro(c, proyecto_json):
    antes = sorted(p.name for p in c.dir_proyectos.iterdir()) if c.dir_proyectos.exists() else []
    r = _importar(c, _zip({"proyecto.json": proyecto_json, "modelo.json": "{}"}))
    assert r.status_code == 400 and "dañado" in r.get_json()["error"]
    despues = sorted(p.name for p in c.dir_proyectos.iterdir()) if c.dir_proyectos.exists() else []
    assert despues == antes                                    # sin carpeta a medias
    assert c.get("/api/proyectos").status_code == 200


def test_h01_plantilla_json_rota_es_400(c):
    r = _importar(c, _zip({"plantilla.json": "{no es json", "modelo.json": "{}"}))
    assert r.status_code == 400
    r = _importar(c, _zip({"plantilla.json": "[1]", "modelo.json": "{}"}))
    assert r.status_code == 400


def test_h01_un_proyecto_danado_en_disco_no_oculta_los_demas(c):
    bueno = c.post("/api/proyectos", json={"nombre": "Bueno"}).get_json()["id"]
    malo = c.post("/api/proyectos", json={"nombre": "Malo"}).get_json()["id"]
    (c.dir_proyectos / malo / "proyecto.json").write_text('{"principal": 5}', encoding="utf-8")
    r = c.get("/api/proyectos")
    assert r.status_code == 200
    assert [p["id"] for p in r.get_json()] == [bueno]
    assert c.get(f"/api/proyectos/{malo}").status_code in (400, 404)


# ---------------------------------------------------------------------- H-02
def test_h02_guardados_a_la_vez_no_fallan_ni_danan_archivos(c):
    pid = c.post("/api/proyectos", json={"nombre": "Concurrente"}).get_json()["id"]
    base = c.get(f"/api/proyectos/{pid}").get_json()["modelo"]
    codigos = []

    def guardar(i):
        m = dict(base, cabecera=dict(base["cabecera"], titulo=("T%d" % i) * (50 + 37 * i)))
        codigos.append(c.put(f"/api/proyectos/{pid}/modelo", json=m).status_code)

    for _ in range(6):
        hilos = [threading.Thread(target=guardar, args=(i,)) for i in range(20)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        for nombre in ("modelo.json", "proyecto.json"):
            json.loads((c.dir_proyectos / pid / nombre).read_text(encoding="utf-8"))   # se lee entero
    assert set(codigos) == {200}
    assert not list((c.dir_proyectos / pid).glob("*.tmp"))                             # sin temporales sueltos


def test_h02_escribir_json_no_deja_temporales(tmp_path):
    p = tmp_path / "a.json"
    A._escribir_json(p, {"x": 1})
    A._escribir_json(p, {"x": 2})
    assert json.loads(p.read_text()) == {"x": 2}
    assert [q.name for q in tmp_path.iterdir()] == ["a.json"]


def test_h02_un_modelo_danado_no_se_abre_en_blanco(c):
    pid = c.post("/api/proyectos", json={"nombre": "Dañado"}).get_json()["id"]
    m = c.get(f"/api/proyectos/{pid}").get_json()["modelo"]
    m["cabecera"]["titulo"] = "Mi documento"
    assert c.put(f"/api/proyectos/{pid}/modelo", json=m).status_code == 200
    # una copia buena en el historial y un modelo.json roto
    hist = c.dir_proyectos / pid / "historial"
    hist.mkdir(exist_ok=True)
    (hist / "modelo-20260101-000000.json").write_text(json.dumps(m), encoding="utf-8")
    (c.dir_proyectos / pid / "modelo.json").write_text('{"filas": [', encoding="utf-8")
    r = c.get(f"/api/proyectos/{pid}")
    assert r.status_code == 400 and "dañado" in r.get_json()["error"]
    # se recupera desde el historial
    r = c.post(f"/api/proyectos/{pid}/historial/modelo-20260101-000000.json/restaurar")
    assert r.status_code == 200
    assert c.get(f"/api/proyectos/{pid}").get_json()["modelo"]["cabecera"]["titulo"] == "Mi documento"
