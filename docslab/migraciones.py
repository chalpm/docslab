# SPDX-License-Identifier: AGPL-3.0-only
"""Migraciones del esquema del modelo JSON (modelo.json).

Cada proyecto guarda la versión de su estructura en la clave ``version_esquema``
(un entero). Cuando la estructura cambia de un modo que ``modelo.normalizar()``
no resuelve completando valores por defecto (renombrar, mover o cambiar el tipo
de un campo), se sube ``modelo.ESQUEMA`` en 1 y se registra aquí una función
que lleva un modelo de la versión N a la N+1. Al abrir un proyecto antiguo se
aplican en cadena: 1 → 2 → 3 …

Reglas para escribir una migración (ver docs/MIGRACIONES.md):
  * función pura: recibe un dict y devuelve un dict, sin E/S ni efectos;
  * determinista e idempotente respecto a su entrada;
  * no pierde datos del usuario en silencio: lo que no tenga destino se
    conserva en ``modelo["_migrado"]["<n>"]``;
  * llega con un fixture ``tests/fixtures/esquemas/v<N>/…json`` de la versión
    de origen y una prueba de la transformación.

Modelos heredados: los ``modelo.json`` anteriores a DocsLab 1.1.0 (PosterLab,
DocsLab 2.1.0 original y DocsLab 1.0.x) no tienen ``version_esquema``; algunos
llevan la clave antigua ``esquema`` con 1 o 2. Todos tienen la estructura del
esquema 1, así que se tratan como versión 1 y se retira la clave antigua.
"""
from __future__ import annotations

import copy
from typing import Callable

CLAVE = "version_esquema"
CLAVE_HEREDADA = "esquema"

Migracion = Callable[[dict], dict]
MIGRACIONES: dict[int, Migracion] = {}


class ErrorEsquema(ValueError):
    """El modelo no se puede llevar al esquema actual."""


def migracion(desde: int):
    """Registra la función que lleva un modelo del esquema ``desde`` al ``desde + 1``."""
    def registrar(f: Migracion) -> Migracion:
        if desde in MIGRACIONES:
            raise RuntimeError(f"Ya hay una migración registrada desde el esquema {desde}")
        MIGRACIONES[desde] = f
        return f
    return registrar


def version_de(m: dict) -> int:
    """Versión de esquema de un modelo (1 para los heredados sin ``version_esquema``)."""
    v = m.get(CLAVE)
    if v is None:
        return 1
    if isinstance(v, bool) or not isinstance(v, int) or v < 1:
        raise ErrorEsquema(f"Versión de esquema no válida en el modelo: {v!r}")
    return v


def migrar(m: dict, destino: int | None = None) -> tuple[dict, list[str]]:
    """Lleva ``m`` al esquema ``destino`` (por defecto, el actual).

    Devuelve una copia migrada y la lista de pasos aplicados, por ejemplo
    ``["heredado→1", "1→2"]``. No modifica ``m``.
    """
    if destino is None:
        from .modelo import ESQUEMA
        destino = ESQUEMA
    v = version_de(m)
    if v > destino:
        raise ErrorEsquema(
            f"Este proyecto se guardó con una versión más nueva de DocsLab (esquema {v}; "
            f"esta versión entiende hasta el {destino}). Actualiza DocsLab para abrirlo.")
    m = copy.deepcopy(m)
    pasos = []
    if CLAVE not in m:
        if CLAVE_HEREDADA in m:
            m.pop(CLAVE_HEREDADA)
        pasos.append("heredado→1")
    while v < destino:
        f = MIGRACIONES.get(v)
        if f is None:
            raise ErrorEsquema(f"Falta la migración del esquema {v} al {v + 1}")
        m = f(m)
        if not isinstance(m, dict):
            raise ErrorEsquema(f"La migración {v}→{v + 1} no devolvió un modelo")
        v += 1
        pasos.append(f"{v - 1}→{v}")
    m[CLAVE] = destino
    return m, pasos


def necesita_copia(m: dict) -> bool:
    """True si abrir el modelo aplicará migraciones estructurales (conviene guardar una copia antes)."""
    from .modelo import ESQUEMA
    return version_de(m) < ESQUEMA


# --------------------------------------------------------------------------- registro
# Todavía no hay migraciones: el esquema actual es el 1. Ejemplo de la primera:
#
# @migracion(desde=1)
# def _1_a_2(m: dict) -> dict:
#     cab = m.get("cabecera", {})
#     if "tam_logo_izquierdo" in cab:
#         cab.setdefault("logos", {}).setdefault("izquierdo", {})["tam"] = cab.pop("tam_logo_izquierdo")
#     return m
