# SPDX-License-Identifier: AGPL-3.0-only
import io
import json
import time
import zipfile

from conftest import hay_latex, hay_nucleo


def esperar(c, tid, limite=300):
    t0 = time.time()
    while time.time() - t0 < limite:
        t = c.get(f"/api/trabajos/{tid}").get_json()
        if t["estado"] in ("terminado", "error", "cancelado"):
            return t
        time.sleep(0.2)
    raise AssertionError("el trabajo no terminó")


def png(color=(40, 120, 200)):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (64, 40), color).save(b, "PNG")
    return b.getvalue()


def test_estado_y_catalogo(cliente):
    assert cliente.get("/api/estado").status_code == 200
    v = cliente.get("/api/variantes").get_json()
    assert len(v["variantes"]) == 69 and len(v["estilos_caja"]) == 12
    assert list(v["temas"])[0] == "pizarra"                  # se conserva el orden


def test_plantillas_incluidas(cliente):
    pls = cliente.get("/api/plantillas").get_json()
    ids = {p["id"] for p in pls}
    assert {"academico-a0", "capas-a1", "bgc-en", "bgc-es", "catalogo-latex"} <= ids
    assert cliente.patch("/api/plantillas/academico-a0", json={"nombre": "x"}).status_code == 400
    assert cliente.delete("/api/plantillas/academico-a0").status_code == 400


def test_proyecto_modelo_y_formato(cliente):
    p = cliente.post("/api/proyectos", json={"nombre": "Prueba", "asistente": {"columnas": 2}}).get_json()
    pid = p["id"]
    m = cliente.get(f"/api/proyectos/{pid}").get_json()["modelo"]
    m["cabecera"]["autores"] = "Ana^1^"
    assert cliente.put(f"/api/proyectos/{pid}/modelo", json=m).status_code == 200
    tex = cliente.get(f"/api/proyectos/{pid}/latex").get_data(as_text=True)
    assert "\\autores{Ana\\textsuperscript{1}}" in tex
    r = cliente.post(f"/api/proyectos/{pid}/formato", json={"formato": "latex"}).get_json()
    assert r["modelo"]["formato_texto"] == "latex"
    assert r["modelo"]["cabecera"]["autores"] == "Ana\\textsuperscript{1}"
    assert cliente.get(f"/api/proyectos/{pid}/latex").get_data(as_text=True) == tex


def test_recursos(cliente):
    pid = cliente.post("/api/proyectos", json={"nombre": "R"}).get_json()["id"]
    r = cliente.post(f"/api/proyectos/{pid}/recursos", data={"archivos": [(io.BytesIO(png()), "Figura ñ 1.png")]},
                     content_type="multipart/form-data").get_json()
    assert r["guardados"] == ["recursos/Figura_n_1.png"]
    r = cliente.post(f"/api/proyectos/{pid}/recursos", data={"archivos": [(io.BytesIO(b"x"), "datos.csv")]},
                     content_type="multipart/form-data").get_json()
    assert r["errores"] and not r["guardados"]
    assert cliente.get(f"/api/proyectos/{pid}/vista?ruta=recursos/Figura_n_1.png").status_code == 200
    assert cliente.get(f"/api/proyectos/{pid}/f/../proyecto.json").status_code in (400, 404)
    assert cliente.delete(f"/api/proyectos/{pid}/recursos?ruta=proyecto.json").status_code == 400


def test_plantilla_propia_y_zips(cliente):
    pid = cliente.post("/api/proyectos", json={"nombre": "Base"}).get_json()["id"]
    pl = cliente.post("/api/plantillas", json={"proyecto": pid, "nombre": "Mi plantilla"}).get_json()
    assert pl["id"] == "mi-plantilla"
    z = cliente.get(f"/api/plantillas/{pl['id']}/exportar").data
    assert "plantilla.json" in zipfile.ZipFile(io.BytesIO(z)).namelist()
    cliente.delete(f"/api/plantillas/{pl['id']}")
    r = cliente.post("/api/proyectos/importar", data={"archivo": (io.BytesIO(z), "p.zip")},
                     content_type="multipart/form-data").get_json()
    assert r["tipo"] == "plantilla"
    zo = cliente.get(f"/api/proyectos/{pid}/exportar?tipo=overleaf").data
    nombres = zipfile.ZipFile(io.BytesIO(zo)).namelist()
    assert "poster.tex" in nombres and "postercientifico.sty" in nombres
    r = cliente.post("/api/proyectos/importar", data={"archivo": (io.BytesIO(zo), "o.zip")},
                     content_type="multipart/form-data").get_json()
    assert r["tipo"] == "proyecto" and r["proyecto"]["tipo"] == "latex"


def test_actualizar_plantilla_desde_un_poster(cliente):
    pid = cliente.post("/api/proyectos", json={"nombre": "Base"}).get_json()["id"]
    assert cliente.get(f"/api/proyectos/{pid}").get_json()["plantilla_propia"] is None
    pl = cliente.post("/api/plantillas", json={"proyecto": pid, "nombre": "Congreso"}).get_json()
    tid = pl["id"]
    cliente.patch(f"/api/plantillas/{tid}", json={"descripcion": "Para el congreso"})
    # el póster queda ligado a la plantilla que se guardó desde él
    assert cliente.get(f"/api/proyectos/{pid}").get_json()["plantilla_propia"] == {"id": tid, "nombre": "Congreso"}
    lista = {p["id"]: p for p in cliente.get("/api/proyectos").get_json()}
    assert lista[pid]["plantilla_propia"]["id"] == tid
    # un póster creado con la plantilla también puede actualizarla
    hijo = cliente.post("/api/proyectos", json={"nombre": "Hijo", "plantilla": tid}).get_json()["id"]
    assert cliente.get(f"/api/proyectos/{hijo}").get_json()["plantilla_propia"]["id"] == tid
    m = cliente.get(f"/api/proyectos/{hijo}").get_json()["modelo"]
    m["cabecera"]["titulo"] = "Título nuevo de la plantilla"
    cliente.put(f"/api/proyectos/{hijo}/modelo", json=m)
    cliente.post(f"/api/proyectos/{hijo}/recursos", data={"archivos": [(io.BytesIO(png()), "logo.png")]},
                 content_type="multipart/form-data")
    r = cliente.put(f"/api/plantillas/{tid}", json={"proyecto": hijo})
    assert r.status_code == 200
    r = r.get_json()
    assert r["id"] == tid and r["nombre"] == "Congreso" and r["descripcion"] == "Para el congreso"
    assert r.get("actualizada")
    pls = [p for p in cliente.get("/api/plantillas").get_json() if not p["incluida"]]
    assert [p["id"] for p in pls] == [tid]                    # sin carpetas temporales a la vista
    nuevo = cliente.post("/api/proyectos", json={"nombre": "Nieto", "plantilla": tid}).get_json()["id"]
    assert cliente.get(f"/api/proyectos/{nuevo}").get_json()["modelo"]["cabecera"]["titulo"] == "Título nuevo de la plantilla"
    assert any(x["nombre"] == "logo.png" for x in cliente.get(f"/api/proyectos/{nuevo}/recursos").get_json())
    # el póster original no cambia
    assert cliente.get(f"/api/proyectos/{pid}").get_json()["modelo"]["cabecera"]["titulo"] != "Título nuevo de la plantilla"
    # las incluidas no se tocan; una plantilla borrada deja de ofrecerse
    assert cliente.put("/api/plantillas/academico-a0", json={"proyecto": hijo}).status_code == 400
    assert cliente.put(f"/api/plantillas/{tid}", json={"proyecto": "p-noexiste"}).status_code == 400
    cliente.delete(f"/api/plantillas/{tid}")
    assert cliente.get(f"/api/proyectos/{hijo}").get_json()["plantilla_propia"] is None


def test_zip_malicioso_no_sale_de_su_carpeta(cliente, tmp_path):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("main.tex", "\\documentclass{article}\\begin{document}x\\end{document}")
        z.writestr("../../fuera.txt", "malo")
    r = cliente.post("/api/proyectos/importar", data={"archivo": (io.BytesIO(b.getvalue()), "m.zip")},
                     content_type="multipart/form-data").get_json()
    assert r["tipo"] == "proyecto"
    assert not (tmp_path / "fuera.txt").exists() and not (tmp_path / "datos" / "fuera.txt").exists()


def test_explorar_solo_dentro_de_las_raices(cliente):
    (cliente.raiz / "nb.ipynb").write_text("{}", encoding="utf-8")
    assert cliente.get("/api/explorar").get_json()["entradas"]
    assert cliente.get(f"/api/explorar?ruta={cliente.raiz}").get_json()["entradas"][0]["nombre"] == "nb.ipynb"
    assert cliente.get("/api/explorar?ruta=/etc").status_code == 400


@hay_latex
def test_compilar_errores_y_ultimo_pdf_correcto(cliente):
    pid = cliente.post("/api/proyectos", json={"nombre": "C", "asistente": {"columnas": 2}}).get_json()["id"]
    t = esperar(cliente, cliente.post(f"/api/proyectos/{pid}/compilar").get_json()["id"])
    assert t["resultado"]["ok"] and t["resultado"]["paginas"] == 1
    assert t["resultado"]["avisos"] == []                 # un póster recién creado compila limpio
    m = cliente.get(f"/api/proyectos/{pid}").get_json()["modelo"]
    e = m["filas"][0]["columnas"][0]["bloques"][0]["elementos"][0]
    e["texto"] = "Hola {{\\ordenquenoexiste}}"
    cliente.put(f"/api/proyectos/{pid}/modelo", json=m)
    t = esperar(cliente, cliente.post(f"/api/proyectos/{pid}/compilar").get_json()["id"])
    res = t["resultado"]
    assert not res["ok"] and res["errores"][0]["elemento"] == e["id"]
    assert cliente.get(f"/api/proyectos/{pid}/compilacion").get_json()["pdf_anterior"] is True
    assert cliente.get(f"/api/proyectos/{pid}/pdf").status_code == 200        # se sigue viendo el último PDF bueno


@hay_latex
def test_compilar_sin_cambios_no_repite_y_miniatura_aparte(cliente):
    pid = cliente.post("/api/proyectos", json={"nombre": "Rápido"}).get_json()["id"]
    t = esperar(cliente, cliente.post(f"/api/proyectos/{pid}/compilar").get_json()["id"])
    assert t["resultado"]["ok"]
    # la miniatura se hace aparte (o al pedirla), no dentro de la compilación
    assert cliente.get(f"/api/proyectos/{pid}/miniatura").status_code == 200
    t = esperar(cliente, cliente.post(f"/api/proyectos/{pid}/compilar").get_json()["id"])
    assert t["resultado"]["ok"] and t["mensaje"].startswith("Sin cambios")
    # un recurso nuevo sí obliga a compilar otra vez
    cliente.post(f"/api/proyectos/{pid}/recursos", data={"archivos": [(io.BytesIO(png()), "nueva.png")]},
                 content_type="multipart/form-data")
    t = esperar(cliente, cliente.post(f"/api/proyectos/{pid}/compilar").get_json()["id"])
    assert t["resultado"]["ok"] and not t["mensaje"].startswith("Sin cambios")


@hay_nucleo
def test_cuaderno_genera_figuras(cliente):
    pid = cliente.post("/api/proyectos", json={"nombre": "N"}).get_json()["id"]
    nb = {"cells": [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                     "source": ["import os\n", "os.makedirs('res', exist_ok=True)\n",
                                "open('res/fig.pdf', 'wb').write(b'%PDF-1.4\\n')\n", "print('N =', N)\n"]}],
          "metadata": {"kernelspec": {"name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}
    c = cliente.post(f"/api/proyectos/{pid}/cuadernos",
                     data={"cuaderno": (io.BytesIO(json.dumps(nb).encode()), "a.ipynb")},
                     content_type="multipart/form-data").get_json()
    cliente.patch(f"/api/proyectos/{pid}/cuadernos/{c['id']}", json={"parametros": {"despues_de": -1, "codigo": "N = 7"}})
    t = esperar(cliente, cliente.post(f"/api/proyectos/{pid}/cuadernos/{c['id']}/ejecutar").get_json()["id"])
    assert t["resultado"]["ok"], t["resultado"]
    assert [f["ruta"] for f in t["resultado"]["figuras"]] == [f"recursos/cuadernos/{c['id']}/res/fig.pdf"]
    assert any("N = 7" in ln for ln in t["registro"])
