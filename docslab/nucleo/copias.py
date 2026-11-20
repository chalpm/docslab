# SPDX-License-Identifier: AGPL-3.0-only
"""Copias de seguridad automáticas de la carpeta de datos.

Cada ``horas`` (24 por defecto) se guarda un zip con todo lo que no se puede regenerar:
proyectos (modelo, recursos, cuadernos, historial…), plantillas propias, componentes y
plantillas de gráficos. Se excluye lo que DocsLab vuelve a crear solo: la carpeta ``build/``
de cada proyecto y los formatos precompilados de LaTeX (``formatos/``).

* Carpeta: ``DOCSLAB_COPIAS_DIR`` o, si no, ``<datos>/copias``. Conviene que esté en otro disco
  o en una carpeta sincronizada con la nube: una copia en el mismo disco no protege si el disco falla.
* Cuántas se guardan: ``DOCSLAB_COPIAS`` (7 por defecto; 0 las desactiva). Se borran las más antiguas.
* Frecuencia: ``DOCSLAB_COPIAS_HORAS`` (24 por defecto).
* Si nada cambió desde la última copia, no se hace otra igual.

Restaurar: descomprime el zip y copia lo que necesites (por ejemplo, ``proyectos/p-xxxxxxxx``)
dentro de la carpeta de datos, con DocsLab cerrado.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import zipfile
from pathlib import Path

PREFIJO = "docslab-copia-"
CARPETAS = ("proyectos", "plantillas", "componentes", "graficos")
EXCLUIR_EN_PROYECTO = {"build"}
log = logging.getLogger("docslab")


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(0, int(os.environ.get(nombre, defecto)))
    except ValueError:
        return defecto


class Copias:
    def __init__(self, datos: Path, destino: Path | None = None, conservar: int | None = None,
                 horas: float | None = None):
        self.datos = Path(datos).resolve()
        otra = os.environ.get("DOCSLAB_COPIAS_DIR")
        self.dir = Path(destino or (Path(otra).expanduser() if otra else self.datos / "copias")).resolve()
        self.conservar = _entero("DOCSLAB_COPIAS", 7) if conservar is None else max(0, conservar)
        self.horas = float(horas if horas is not None else _entero("DOCSLAB_COPIAS_HORAS", 24) or 24)
        self._cerrojo = threading.Lock()
        self._hilo: threading.Thread | None = None

    # ------------------------------------------------------------------ qué se copia
    def archivos(self):
        """(ruta en disco, nombre dentro del zip) de todo lo que entra en la copia."""
        for carpeta in CARPETAS:
            base = self.datos / carpeta
            if not base.is_dir():
                continue
            for raiz, dirs, nombres in os.walk(base):
                r = Path(raiz)
                rel = r.relative_to(self.datos)
                # dentro de proyectos/<pid>/ se salta build/; y nunca se copia la propia carpeta de copias
                if carpeta == "proyectos" and len(rel.parts) == 2:
                    dirs[:] = [d for d in dirs if d not in EXCLUIR_EN_PROYECTO]
                dirs[:] = [d for d in dirs if (r / d).resolve() != self.dir]
                for n in nombres:
                    p = r / n
                    if p.is_file() and not p.is_symlink():
                        yield p, (rel / n).as_posix()

    def ultima(self) -> Path | None:
        copias = self.lista()
        return copias[-1] if copias else None

    def lista(self) -> list[Path]:
        if not self.dir.is_dir():
            return []
        return sorted(self.dir.glob(f"{PREFIJO}*.zip"))

    def hace_falta(self, ahora: float | None = None) -> bool:
        if self.conservar == 0:
            return False
        ahora = time.time() if ahora is None else ahora
        u = self.ultima()
        if u is None:
            return any(True for _ in self.archivos())
        if ahora - u.stat().st_mtime < self.horas * 3600:
            return False
        # ¿cambió algo desde la última copia?
        limite = u.stat().st_mtime
        return any(p.stat().st_mtime > limite for p, _ in self.archivos())

    # ------------------------------------------------------------------ hacer y rotar
    def hacer(self) -> Path | None:
        """Hace una copia ahora (si las copias están activas). Devuelve su ruta."""
        if self.conservar == 0:
            return None
        with self._cerrojo:
            self.dir.mkdir(parents=True, exist_ok=True)
            nombre = f"{PREFIJO}{time.strftime('%Y%m%d-%H%M%S')}.zip"
            final = self.dir / nombre
            n = 1
            while final.exists():
                n += 1
                final = self.dir / nombre.replace(".zip", f"-{n}.zip")
            tmp = final.with_suffix(".zip.parcial")
            try:
                with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                    for p, dentro in self.archivos():
                        try:
                            z.write(p, dentro)
                        except OSError as exc:            # un archivo que se borra justo ahora
                            log.warning("Copia de seguridad: se omite %s (%s)", dentro, exc)
                tmp.replace(final)
            finally:
                tmp.unlink(missing_ok=True)
            self.rotar()
            return final

    def rotar(self) -> list[Path]:
        copias = self.lista()
        sobran = copias[:-self.conservar] if self.conservar else copias
        for p in sobran:
            p.unlink(missing_ok=True)
        return sobran

    def si_hace_falta(self) -> Path | None:
        try:
            if self.hace_falta():
                return self.hacer()
        except Exception:                              # una copia fallida no debe tumbar el servidor
            log.exception("No se pudo hacer la copia de seguridad en %s", self.dir)
        return None

    def programar(self, cada_segundos: float = 3600) -> None:
        """Comprueba ahora y luego cada hora (en un hilo aparte) si toca otra copia."""
        if self.conservar == 0 or self._hilo:
            return

        def bucle():
            while True:
                self.si_hace_falta()
                time.sleep(cada_segundos)

        self._hilo = threading.Thread(target=bucle, daemon=True, name="copias-de-seguridad")
        self._hilo.start()

    def resumen(self) -> str:
        if self.conservar == 0:
            return "Copias de seguridad automáticas desactivadas (DOCSLAB_COPIAS=0)."
        return (f"Copias de seguridad: cada {self.horas:g} h en {self.dir} (se guardan las {self.conservar} "
                f"más recientes).")
