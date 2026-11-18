# SPDX-License-Identifier: AGPL-3.0-only
"""Defensas del servidor local frente a otras webs abiertas en el mismo navegador.

DocsLab no tiene contraseña: está pensado para usarse en 127.0.0.1. Aun así, una web cualquiera
puede intentar hablar con él desde el navegador del usuario. Aquí se cierran esas vías:

* **Host** (DNS rebinding): solo se atiende a nombres locales (localhost, *.localhost), a direcciones
  IP escritas tal cual (un ataque de rebinding siempre usa un nombre de dominio) y a los nombres de
  ``DOCSLAB_HOSTS`` (separados por comas). En modo Colab el proxy de Google es quien filtra.
* **Peticiones que cambian algo** (POST, PUT, PATCH, DELETE): deben llevar la cabecera
  ``X-DocsLab: 1``, que el navegador no deja añadir desde otro origen sin un permiso CORS que el
  servidor nunca concede; y, si traen ``Origin``, debe ser el propio servidor.
* **Cabeceras de respuesta**: ``X-Content-Type-Options: nosniff``, ``Referrer-Policy`` y una CSP
  mínima que impide meter DocsLab en un marco ajeno (salvo Colab, que lo muestra en un iframe).
* **Errores**: 404 y 500 en JSON, sin detalles internos.
"""
from __future__ import annotations

import ipaddress
import logging
import os
from urllib.parse import urlsplit

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

CABECERA = "X-DocsLab"
METODOS_QUE_CAMBIAN = {"POST", "PUT", "PATCH", "DELETE"}
MARCOS_COLAB = "https://colab.research.google.com https://*.googleusercontent.com"   # [no verificado en un Colab real]

log = logging.getLogger("docslab")


def _nombre(host: str) -> str:
    """«127.0.0.1:8765» → «127.0.0.1»; «[::1]:8765» → «::1»; en minúsculas."""
    host = (host or "").strip().lower()
    if host.startswith("["):
        return host[1:host.find("]")] if "]" in host else host[1:]
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def _es_ip(nombre: str) -> bool:
    try:
        ipaddress.ip_address(nombre)
        return True
    except ValueError:
        return False


def hosts_extra() -> set[str]:
    return {h.strip().lower() for h in os.environ.get("DOCSLAB_HOSTS", "").split(",") if h.strip()}


def host_permitido(host: str, extra: set[str] | None = None) -> bool:
    n = _nombre(host)
    if not n:
        return False
    return n == "localhost" or n.endswith(".localhost") or _es_ip(n) or n in (extra if extra is not None else hosts_extra())


def proteger(app: Flask, colab: bool = False) -> None:
    extra = hosts_extra()

    def _rechazo(mensaje: str):
        return jsonify({"error": mensaje}), 403

    @app.before_request
    def _comprobar():
        if not colab and not host_permitido(request.host, extra):
            return _rechazo("Petición rechazada: DocsLab solo atiende en su dirección local "
                            "(usa http://127.0.0.1:<puerto>/ o añade el nombre a DOCSLAB_HOSTS).")
        if request.method in METODOS_QUE_CAMBIAN:
            if request.headers.get(CABECERA) != "1":
                return _rechazo("Petición rechazada: no viene de la interfaz de DocsLab.")
            origen = request.headers.get("Origin")
            if origen is not None and not colab:
                partes = urlsplit(origen)
                if origen == "null" or partes.netloc.lower() != request.host.lower():
                    return _rechazo("Petición rechazada: viene de otra página.")
        return None

    @app.after_request
    def _cabeceras(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        marcos = "'self' " + MARCOS_COLAB if colab else "'self'"
        resp.headers.setdefault("Content-Security-Policy", f"frame-ancestors {marcos}; object-src 'none'; base-uri 'self'")
        return resp

    @app.errorhandler(404)
    def _no_encontrado(exc):
        return jsonify({"error": "No encontrado"}), 404

    @app.errorhandler(405)
    def _metodo(exc):
        return jsonify({"error": "Método no permitido"}), 405

    @app.errorhandler(Exception)
    def _inesperado(exc):
        if isinstance(exc, HTTPException):
            return jsonify({"error": exc.description or exc.name}), exc.code or 500
        log.exception("Error no controlado en %s %s", request.method, request.path)
        return jsonify({"error": "Error interno de DocsLab. Mira la terminal para más detalles."}), 500
