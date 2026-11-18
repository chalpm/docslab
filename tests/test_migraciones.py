# SPDX-License-Identifier: AGPL-3.0-only
"""Migraciones del esquema del modelo (docslab/migraciones.py, docs/MIGRACIONES.md)."""
import json
from pathlib import Path

import pytest

from docslab.nucleo import almacen as A, migraciones as MG, modelo as M
from docslab.documento import generador as G

FIXTURES = Path(__file__).parent / "fixtures" / "esquemas"
TODOS = sorted(FIXTURES.glob("v*/*.json"))


def _cargar(p):
    return json.loads(p.read_text(encoding="utf-8"))


def _subconjunto(original, migrado, ruta="modelo"):
    """Todo valor del original sigue en el migrado (normalizar solo añade)."""
    if isinstance(original, dict):
        for k, v in original.items():
            if k in (MG.CLAVE, MG.CLAVE_HEREDADA):
                continue
            assert k in migrado, f"se perdió {ruta}.{k}"
            _subconjunto(v, migrado[k], f"{ruta}.{k}")
    elif isinstance(original, list):
        assert len(original) == len(migrado), f"cambió la longitud de {ruta}"
        for i, (a, b) in enumerate(zip(original, migrado)):
            _subconjunto(a, b, f"{ruta}[{i}]")
    else:
        assert original == migrado, f"cambió {ruta}: {original!r} → {migrado!r}"


# ---------------------------------------------------------------- registro real
def test_hay_una_migracion_por_cada_salto_de_esquema():
    faltan = [n for n in range(1, M.ESQUEMA) if n not in MG.MIGRACIONES]
    assert not faltan, f"faltan migraciones desde los esquemas {faltan}"
    assert all(n < M.ESQUEMA for n in MG.MIGRACIONES), "hay migraciones más allá del esquema actual"


def test_hay_fixture_de_cada_esquema_anterior():
    for n in range(1, M.ESQUEMA + 1):
        assert list((FIXTURES / f"v{n}").glob("*.json")), f"falta un fixture en tests/fixtures/esquemas/v{n}/"


@pytest.mark.parametrize("fixture", TODOS, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_cada_fixture_llega_al_esquema_actual_y_genera_latex(fixture):
    m = M.normalizar(_cargar(fixture))
    assert m[MG.CLAVE] == M.ESQUEMA
    assert MG.CLAVE_HEREDADA not in m
    tex, _ = G.generar(m)
    assert "\\begin{document}" in tex


@pytest.mark.parametrize("fixture", sorted(FIXTURES.glob(f"v{M.ESQUEMA}/*.json")), ids=lambda p: p.stem)
def test_normalizar_el_esquema_actual_no_pierde_datos(fixture):
    original = _cargar(fixture)
    _subconjunto(original, M.normalizar(original))


def test_heredados_se_tratan_como_esquema_1():
    for crudo in ({}, {"esquema": 1}, {"esquema": 2}):
        assert MG.version_de(crudo) == 1
        m, pasos = MG.migrar(crudo, destino=1)
        assert pasos == ["heredado→1"] and m == {MG.CLAVE: 1}


def test_migrar_no_modifica_la_entrada_y_es_idempotente():
    crudo = {"esquema": 2, "clase": "poster"}
    una, _ = MG.migrar(crudo)
    assert crudo == {"esquema": 2, "clase": "poster"}
    dos, pasos = MG.migrar(una)
    assert una == dos and pasos == []


@pytest.mark.parametrize("valor", [0, -1, "1", 1.0, True])
def test_version_no_valida(valor):
    with pytest.raises(MG.ErrorEsquema):
        MG.migrar({MG.CLAVE: valor})


def test_un_esquema_mas_nuevo_no_se_abre():
    with pytest.raises(MG.ErrorEsquema, match="más nueva"):
        M.normalizar({MG.CLAVE: M.ESQUEMA + 1})


# ---------------------------------------------------------------- cadena simulada
@pytest.fixture
def registro(monkeypatch):
    reg = {}
    monkeypatch.setattr(MG, "MIGRACIONES", reg)
    return reg


def test_cadena_de_migraciones_en_orden(registro):
    @MG.migracion(desde=1)
    def _(m):
        m["b"] = m.pop("a")
        return m

    @MG.migracion(desde=2)
    def _(m):
        m["c"] = m.pop("b") * 2
        return m

    m, pasos = MG.migrar({MG.CLAVE: 1, "a": 21}, destino=3)
    assert m == {MG.CLAVE: 3, "c": 42}
    assert pasos == ["1→2", "2→3"]
    m, pasos = MG.migrar({"esquema": 2, "a": 1}, destino=3)        # heredado: se trata como 1
    assert pasos == ["heredado→1", "1→2", "2→3"] and m["c"] == 2


def test_falta_un_eslabon(registro):
    MG.migracion(desde=1)(lambda m: m)
    with pytest.raises(MG.ErrorEsquema, match="del esquema 2 al 3"):
        MG.migrar({MG.CLAVE: 1}, destino=3)


def test_no_se_registra_dos_veces(registro):
    MG.migracion(desde=1)(lambda m: m)
    with pytest.raises(RuntimeError):
        MG.migracion(desde=1)(lambda m: m)


def test_una_migracion_que_no_devuelve_un_modelo(registro):
    MG.migracion(desde=1)(lambda m: None)
    with pytest.raises(MG.ErrorEsquema):
        MG.migrar({MG.CLAVE: 1}, destino=2)


# ---------------------------------------------------------------- almacén
def test_al_abrir_un_proyecto_antiguo_se_guarda_una_copia(tmp_path, monkeypatch, registro):
    alm = A.Almacen(tmp_path)
    meta = alm.crear_proyecto("p", "minima-a1")
    d = alm.dir_proyecto(meta["id"])
    original = (d / "modelo.json").read_bytes()
    MG.migracion(desde=1)(lambda m: {**m, "nuevo": True})
    monkeypatch.setattr(M, "ESQUEMA", 2)
    m = alm.leer_modelo(meta["id"])
    assert m[MG.CLAVE] == 2 and m["nuevo"] is True
    copia = d / "historial" / "modelo-antes-de-esquema-2.json"
    assert copia.read_bytes() == original
    assert (d / "modelo.json").read_bytes() == original        # leer no reescribe el proyecto


def test_un_proyecto_de_un_esquema_mas_nuevo_da_un_error_claro(tmp_path):
    alm = A.Almacen(tmp_path)
    meta = alm.crear_proyecto("p", "minima-a1")
    p = alm.dir_proyecto(meta["id"]) / "modelo.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    m[MG.CLAVE] = M.ESQUEMA + 1
    p.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(A.ErrorAlmacen, match="Actualiza DocsLab"):
        alm.leer_modelo(meta["id"])


def test_la_api_responde_400_con_un_esquema_mas_nuevo(cliente, tmp_path):
    r = cliente.post("/api/proyectos", json={"nombre": "p", "plantilla": "minima-a1"})
    pid = r.get_json()["id"]
    r = cliente.put(f"/api/proyectos/{pid}/modelo", json={MG.CLAVE: M.ESQUEMA + 1})
    assert r.status_code == 400 and "Actualiza DocsLab" in r.get_json()["error"]
