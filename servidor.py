#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""DocsLab · editor web de pósters científicos con LaTeX.

Uso (con el entorno de Python activado; o, más fácil, sh iniciar.command):
    python servidor.py                      # abre http://127.0.0.1:8765
    python servidor.py --puerto 9000 --abrir
    python servidor.py --datos ~/DocsLab --raices ~/Documentos
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import ipaddress
import shutil
import ssl
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
YA_ABIERTO = 3          # código de salida si ya había un DocsLab abierto (lo usa iniciar.bat)


def _ultima(base: Path, patron: str) -> list[Path]:
    try:
        return sorted(base.glob(patron), reverse=True)[:1]
    except OSError:
        return []


def completar_path() -> None:
    """Añade al PATH las carpetas habituales de LaTeX, Poppler y Ghostscript que
    existen y faltan; por ejemplo, si MacTeX o MiKTeX se instalaron después de abrir
    la terminal."""
    extra = [Path("/Library/TeX/texbin"), Path("/opt/homebrew/bin"), Path("/usr/local/bin")]
    extra += _ultima(Path("/usr/local/texlive"), "20*/bin/*")
    if os.name == "nt":
        local = [Path(os.environ["LOCALAPPDATA"])] if os.environ.get("LOCALAPPDATA") else []
        programas = [Path(os.environ[v]) for v in ("ProgramFiles", "ProgramFiles(x86)") if os.environ.get(v)]
        for b in local:
            extra.append(b / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64")       # MiKTeX solo para ti
            extra += _ultima(b, "Microsoft/WinGet/Packages/oschwartz10612.Poppler*/poppler-*/Library/bin")
        for b in programas:
            extra.append(b / "MiKTeX" / "miktex" / "bin" / "x64")                    # MiKTeX para todos
            extra += _ultima(b, "gs/gs*/bin") + _ultima(b, "poppler*/Library/bin")
        extra += _ultima(Path("C:/texlive"), "20*/bin/win*") + _ultima(Path("C:/"), "poppler*/Library/bin")
    actual = [x for x in os.environ.get("PATH", "").split(os.pathsep) if x]
    nuevas = [str(p) for p in extra if p.is_dir() and str(p) not in actual]
    if nuevas:
        os.environ["PATH"] = os.pathsep.join(actual + nuevas)


def ya_abierto(url: str) -> bool:
    """¿Hay ya un DocsLab respondiendo en esa dirección?"""
    # Con HTTPS y un certificado propio (mkcert, autofirmado) la verificación fallaría; esta consulta solo
    # mira si el propio DocsLab ya está escuchando en este equipo, no envía ni recibe datos del usuario.
    contexto = ssl._create_unverified_context() if url.startswith("https:") else None  # noqa: S323
    try:
        with urllib.request.urlopen(url + "api/estado", timeout=1.5, context=contexto) as r:
            return "version" in json.loads(r.read() or b"{}")
    except Exception:
        return False


def silenciar_registro() -> None:
    """La terminal solo muestra lo importante: ni cada petición del navegador ni el
    aviso de «servidor de desarrollo» (es un servidor local para una persona)."""
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    try:
        from flask import cli
        cli.show_server_banner = lambda *a, **k: None
    except Exception:
        pass


def solo_este_equipo(host: str) -> bool:
    """¿El servidor escucha solo en este equipo (loopback)? Si no, la red ve el tráfico."""
    if host in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def contexto_tls(certificado: str | None, clave: str | None):
    """(certificado, clave) para HTTPS, comprobados; None si no se pidió HTTPS."""
    if not certificado and not clave:
        return None
    if not (certificado and clave):
        raise SystemExit("Para HTTPS hacen falta los dos: --certificado y --clave.")
    cert, key = Path(certificado).expanduser(), Path(clave).expanduser()
    for f in (cert, key):
        if not f.is_file():
            raise SystemExit(f"No encuentro el archivo {f}.")
    try:
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(cert, key)
    except (ssl.SSLError, OSError) as exc:
        raise SystemExit(f"El certificado o la clave no sirven: {exc}") from exc
    return ctx


def python_valido(version=None) -> bool:
    from docslab import PYTHON_MINIMO
    return tuple((version or sys.version_info)[:2]) >= PYTHON_MINIMO


def main(argv=None):
    if not python_valido():
        from docslab import PYTHON_MINIMO
        minimo = ".".join(map(str, PYTHON_MINIMO))
        print(f"DocsLab necesita Python {minimo} o posterior y este es {sys.version.split()[0]}.\n"
              f"Instala uno más nuevo (python.org, brew install python o el de tu distribución), borra la "
              f"carpeta .venv si existe y vuelve a abrir el lanzador.", file=sys.stderr, flush=True)
        return 1
    ap = argparse.ArgumentParser(description="DocsLab · editor web de pósters científicos con LaTeX")
    ap.add_argument("--puerto", type=int, default=int(os.environ.get("DOCSLAB_PUERTO", 8765)))
    ap.add_argument("--host", default=os.environ.get("DOCSLAB_HOST", "127.0.0.1"),
                    help="127.0.0.1 = solo este equipo (recomendado)")
    ap.add_argument("--datos", default=os.environ.get("DOCSLAB_DATOS", str(RAIZ / "datos")),
                    help="carpeta donde se guardan proyectos y plantillas")
    ap.add_argument("--raices", nargs="*", default=None,
                    help="carpetas del servidor donde se pueden buscar cuadernos (.ipynb)")
    ap.add_argument("--colab", action="store_true", help="modo Google Colab (lo usa el cuaderno lanzador)")
    ap.add_argument("--abrir", action="store_true", help="abrir el navegador al arrancar")
    ap.add_argument("--detalle", action="store_true", help="mostrar cada petición en la terminal (para depurar)")
    ap.add_argument("--certificado", default=os.environ.get("DOCSLAB_CERTIFICADO"),
                    help="certificado TLS (.pem) para servir por HTTPS, p. ej. hecho con mkcert")
    ap.add_argument("--clave", default=os.environ.get("DOCSLAB_CLAVE"), help="clave privada (.pem) del certificado")
    a = ap.parse_args(argv)

    completar_path()
    tls = contexto_tls(a.certificado, a.clave)
    esquema = "https" if tls else "http"
    url = f"{esquema}://{'127.0.0.1' if a.host in ('0.0.0.0', '::', '') else a.host}:{a.puerto}/"
    if not a.colab and ya_abierto(url):
        print(f"DocsLab ya está abierto en {url}", flush=True)
        if a.abrir:
            webbrowser.open(url)
        return YA_ABIERTO
    raices = a.raices
    if raices is None:
        raices = ["/content"] if a.colab else [str(Path.home())]
    from docslab.app import crear_app
    app = crear_app(Path(a.datos).expanduser(), raices, colab=a.colab)
    if not a.detalle:
        silenciar_registro()
    print(f"DocsLab en {url}  (datos: {Path(a.datos).expanduser().resolve()})", flush=True)
    if not a.colab and not tls and not solo_este_equipo(a.host):
        print("Aviso: DocsLab está abierto a la red sin cifrar (HTTP) y sin contraseña. Úsalo solo en una red de "
              "confianza o sírvelo por HTTPS con --certificado y --clave (ver «Seguridad» en README.md).", flush=True)
    if not a.colab:
        from docslab.nucleo.copias import Copias
        copias = Copias(Path(a.datos).expanduser())
        print(copias.resumen(), flush=True)
        copias.programar()
        if not shutil.which("pdflatex") and not os.environ.get("DOCSLAB_PDFLATEX"):
            print("Aviso: no encuentro LaTeX (pdflatex); sin él no hay vista previa. Mira «Instalación» en README.md.",
                  flush=True)
        print("Deja esta ventana abierta mientras usas DocsLab; Ctrl + C lo cierra.", flush=True)
    if a.abrir:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host=a.host, port=a.puerto, threaded=True, use_reloader=False, debug=False, ssl_context=tls)


if __name__ == "__main__":
    sys.exit(main())
