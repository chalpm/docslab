# SPDX-License-Identifier: AGPL-3.0-only
"""Defensas frente a otras webs abiertas en el mismo navegador (docslab/seguridad.py)."""
import io
import re
import zipfile
from pathlib import Path

import pytest

from docslab import seguridad as S

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def crudo(tmp_path):
    """Cliente sin la cabecera X-DocsLab (como una web ajena)."""
    from docslab.app import crear_app
    return crear_app(tmp_path / "datos").test_client()


def _zip_latex():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("main.tex", "\\documentclass{article}\\begin{document}x\\end{document}")
    return buf.getvalue()


@pytest.mark.parametrize("host,ok", [
    ("127.0.0.1:8765", True), ("localhost:8765", True), ("[::1]:8765", True), ("docslab.localhost", True),
    ("192.168.1.20:8765", True), ("atacante.example:8765", False), ("127.0.0.1.nip.io:8765", False), ("", False),
])
def test_host_permitido(host, ok):
    assert S.host_permitido(host, set()) is ok


def test_hosts_extra_por_variable(monkeypatch):
    monkeypatch.setenv("DOCSLAB_HOSTS", "mi-equipo.lan, Otro.Local")
    assert S.host_permitido("mi-equipo.lan:8765") and S.host_permitido("otro.local")
    assert not S.host_permitido("tercero.lan")


def test_rebinding_un_host_ajeno_se_rechaza(cliente):
    r = cliente.get("/api/proyectos", headers={"Host": "atacante.example:8765"})
    assert r.status_code == 403 and "dirección local" in r.get_json()["error"]
    assert cliente.get("/api/proyectos", headers={"Host": "127.0.0.1:8765"}).status_code == 200


def test_sin_cabecera_no_se_cambia_nada(crudo):
    # Lo que una web ajena puede mandar sin preflight: text/plain y multipart.
    assert crudo.post("/api/proyectos", data="x", content_type="text/plain").status_code == 403
    r = crudo.post("/api/proyectos/importar", data={"archivo": (io.BytesIO(_zip_latex()), "x.zip")},
                   content_type="multipart/form-data")
    assert r.status_code == 403
    assert crudo.get("/api/proyectos").get_json() == []          # no se creó nada
    assert crudo.get("/api/proyectos").status_code == 200        # leer sí (el navegador no deja leerlo desde fuera)


@pytest.mark.parametrize("origen", ["http://atacante.example", "null", "http://127.0.0.1:9999"])
def test_origen_ajeno_se_rechaza_aunque_lleve_cabecera(cliente, origen):
    r = cliente.post("/api/proyectos", json={"nombre": "x"}, headers={"Origin": origen, "Host": "127.0.0.1:8765"})
    assert r.status_code == 403


def test_mismo_origen_funciona(cliente):
    r = cliente.post("/api/proyectos", json={"nombre": "x"},
                     headers={"Origin": "http://127.0.0.1:8765", "Host": "127.0.0.1:8765"})
    assert r.status_code == 200 and r.get_json()["id"].startswith("p-")


def test_modo_colab_deja_pasar_el_proxy_pero_pide_la_cabecera(tmp_path):
    from docslab.app import crear_app
    c = crear_app(tmp_path / "datos", colab=True).test_client()
    h = {"Host": "abc-8765-colab.googleusercontent.com", "Origin": "https://abc-8765-colab.googleusercontent.com"}
    assert c.get("/api/estado", headers=h).status_code == 200
    assert c.post("/api/proyectos", json={}, headers=h).status_code == 403
    assert c.post("/api/proyectos", json={}, headers={**h, "X-DocsLab": "1"}).status_code == 200
    assert "googleusercontent" in c.get("/", headers=h).headers["Content-Security-Policy"]


def test_cabeceras_de_seguridad(cliente):
    h = cliente.get("/").headers
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["Referrer-Policy"] == "same-origin"
    assert "frame-ancestors 'self'" in h["Content-Security-Policy"]
    assert "googleusercontent" not in h["Content-Security-Policy"]


def test_errores_en_json(tmp_path):
    from docslab.app import crear_app
    app = crear_app(tmp_path / "datos")

    @app.get("/api/_fallo")
    def _fallo():
        raise RuntimeError("detalle interno secreto")
    cliente = app.test_client()
    cliente.environ_base["HTTP_X_DOCSLAB"] = "1"
    r = cliente.get("/no-existe")
    assert r.status_code == 404 and r.is_json
    r = cliente.delete("/api/estado")
    assert r.status_code == 405 and r.is_json
    r = cliente.get("/api/_fallo")
    assert r.status_code == 500 and r.is_json and "secreto" not in r.get_data(as_text=True)


def test_la_interfaz_manda_la_cabecera():
    api = (RAIZ / "static" / "js" / "api.js").read_text(encoding="utf-8")
    assert "'X-DocsLab': '1'" in api and "setRequestHeader('X-DocsLab', '1')" in api
    # Ningún otro módulo hace peticiones por su cuenta (todas pasan por api.js)
    otros = [p.name for p in (RAIZ / "static" / "js").glob("*.js")
             if p.name != "api.js" and re.search(r"\bfetch\(|XMLHttpRequest|sendBeacon", p.read_text(encoding="utf-8"))]
    assert otros == []


def test_salidas_html_de_cuadernos_en_marco_aislado():
    js = (RAIZ / "static" / "js" / "cuaderno.js").read_text(encoding="utf-8")
    assert 'v-html="s.html"' not in js
    marcos = re.findall(r'<iframe[^>]*sandbox="([^"]*)"', js)
    assert marcos and all("allow-same-origin" not in s for s in marcos)
    assert re.search(r"<iframe v-else-if=\"s\.t === 'html'\"[^>]*sandbox=\"allow-scripts\"", js)


def test_los_scripts_se_sirven_como_javascript(cliente, monkeypatch):
    """Con «nosniff» el navegador no ejecuta un script con otro tipo MIME (Windows puede tener mal el registro)."""
    import mimetypes
    monkeypatch.setattr(mimetypes, "guess_type", lambda *a, **k: ("text/plain", None))
    for ruta in ("static/js/app.js", "static/vendor/pdf.min.mjs", "static/vendor/pdf.worker.min.mjs"):
        r = cliente.get("/" + ruta)
        assert r.status_code == 200 and r.mimetype == "text/javascript", ruta
    assert cliente.get("/static/css/app.css").mimetype == "text/css"
