# SPDX-License-Identifier: AGPL-3.0-only
"""HTTPS opcional, aviso al abrirse a la red y copias al arrancar (servidor.py)."""
import json
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import servidor  # noqa: E402

sin_openssl = pytest.mark.skipif(shutil.which("openssl") is None, reason="necesita openssl")


@pytest.mark.parametrize("host,ok", [("127.0.0.1", True), ("localhost", True), ("::1", True), ("[::1]", True),
                                     ("127.0.0.2", True), ("0.0.0.0", False), ("192.168.1.20", False),
                                     ("mi-pc.lan", False)])
def test_solo_este_equipo(host, ok):
    assert servidor.solo_este_equipo(host) is ok


def test_tls_pide_los_dos_archivos(tmp_path):
    assert servidor.contexto_tls(None, None) is None
    with pytest.raises(SystemExit, match="los dos"):
        servidor.contexto_tls(str(tmp_path / "c.pem"), None)
    with pytest.raises(SystemExit, match="No encuentro"):
        servidor.contexto_tls(str(tmp_path / "c.pem"), str(tmp_path / "k.pem"))
    (tmp_path / "c.pem").write_text("no es un certificado")
    (tmp_path / "k.pem").write_text("tampoco")
    with pytest.raises(SystemExit, match="no sirven"):
        servidor.contexto_tls(str(tmp_path / "c.pem"), str(tmp_path / "k.pem"))


def _puerto():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _arrancar(args, tmp_path):
    p = subprocess.Popen([sys.executable, str(RAIZ / "servidor.py"), "--datos", str(tmp_path / "datos"), *args],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "DOCSLAB_COPIAS": "3"})
    return p


def _leer_hasta(p, texto, segundos=20):
    lineas, fin = [], time.time() + segundos
    while time.time() < fin:
        linea = p.stdout.readline()
        if not linea:
            break
        lineas.append(linea)
        if texto in linea:
            break
    return "".join(lineas)


@sin_openssl
def test_https_con_certificado_propio(tmp_path):
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=127.0.0.1",
                    "-keyout", str(key), "-out", str(cert)], check=True, capture_output=True)
    puerto = _puerto()
    p = _arrancar(["--puerto", str(puerto), "--certificado", str(cert), "--clave", str(key)], tmp_path)
    try:
        salida = _leer_hasta(p, "Copias de seguridad")
        assert f"https://127.0.0.1:{puerto}/" in salida and "sin cifrar" not in salida
        ctx = ssl.create_default_context(cafile=str(cert))
        ctx.check_hostname = False
        for _ in range(40):
            try:
                r = urllib.request.urlopen(f"https://127.0.0.1:{puerto}/api/estado", context=ctx, timeout=2)
                break
            except OSError:
                time.sleep(0.25)
        assert "version" in json.loads(r.read())
        # Un segundo arranque detecta que ya está abierto (aunque el certificado sea propio)
        assert servidor.ya_abierto(f"https://127.0.0.1:{puerto}/")
    finally:
        p.terminate()
        p.wait(10)


def test_aviso_al_abrirse_a_la_red_sin_https(tmp_path):
    puerto = _puerto()
    p = _arrancar(["--puerto", str(puerto), "--host", "0.0.0.0"], tmp_path)
    try:
        salida = _leer_hasta(p, "Copias de seguridad")
        assert "sin cifrar" in salida and "Copias de seguridad: cada 24 h" in salida
    finally:
        p.terminate()
        p.wait(10)
