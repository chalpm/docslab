"""Trabajos en segundo plano (compilar, ejecutar cuadernos) con progreso y cancelación."""
from __future__ import annotations

import secrets
import threading
import time
import traceback
from collections import deque


class Trabajo:
    def __init__(self, tipo: str, proyecto: str, descripcion: str = ""):
        self.id = "t-" + secrets.token_hex(5)
        self.tipo = tipo
        self.proyecto = proyecto
        self.descripcion = descripcion
        self.estado = "pendiente"          # pendiente | ejecutando | terminado | error | cancelado
        self.progreso = 0.0
        self.mensaje = ""
        self.registro: deque[str] = deque(maxlen=400)
        self.resultado = None
        self.creado = time.time()
        self.inicio = None
        self.fin = None
        self.cancelar = threading.Event()

    def informar(self, mensaje: str, progreso: float | None = None):
        self.mensaje = mensaje
        if progreso is not None:
            self.progreso = max(0.0, min(1.0, float(progreso)))
        self.registro.append(time.strftime("%H:%M:%S ") + mensaje)

    def anotar(self, linea: str):
        self.registro.append(linea)

    def como_dict(self, con_registro: bool = True) -> dict:
        d = {"id": self.id, "tipo": self.tipo, "proyecto": self.proyecto, "descripcion": self.descripcion,
             "estado": self.estado, "progreso": round(self.progreso, 3), "mensaje": self.mensaje,
             "creado": self.creado, "inicio": self.inicio, "fin": self.fin,
             "segundos": round((self.fin or time.time()) - (self.inicio or self.creado), 1),
             "resultado": self.resultado}
        if con_registro:
            d["registro"] = list(self.registro)[-200:]
        return d


class GestorTrabajos:
    """Un hilo por trabajo; los de un mismo proyecto y tipo «exclusivo» se ejecutan de uno en uno."""

    def __init__(self):
        self._trabajos: dict[str, Trabajo] = {}
        self._cerrojos: dict[tuple, threading.Lock] = {}
        self._mutex = threading.Lock()

    def _cerrojo(self, clave) -> threading.Lock:
        with self._mutex:
            if clave not in self._cerrojos:
                self._cerrojos[clave] = threading.Lock()
            return self._cerrojos[clave]

    def lanzar(self, tipo: str, proyecto: str, funcion, descripcion: str = "", exclusivo: str | None = None) -> Trabajo:
        t = Trabajo(tipo, proyecto, descripcion)
        with self._mutex:
            self._trabajos[t.id] = t
            self._limpiar()
        cerrojo = self._cerrojo((proyecto, exclusivo)) if exclusivo else None

        def correr():
            if cerrojo:
                cerrojo.acquire()
            try:
                if t.cancelar.is_set():
                    t.estado = "cancelado"
                    return
                t.estado = "ejecutando"
                t.inicio = time.time()
                t.resultado = funcion(t)
                t.estado = "cancelado" if t.cancelar.is_set() else "terminado"
                t.progreso = 1.0 if t.estado == "terminado" else t.progreso
            except Exception as exc:  # noqa: BLE001
                t.estado = "error"
                t.mensaje = str(exc) if isinstance(exc, ValueError) else f"{type(exc).__name__}: {exc}"
                t.registro.append(traceback.format_exc())
            finally:
                t.fin = time.time()
                if cerrojo:
                    cerrojo.release()

        threading.Thread(target=correr, daemon=True, name=f"trabajo-{t.id}").start()
        return t

    def obtener(self, id_: str) -> Trabajo | None:
        return self._trabajos.get(id_)

    def listar(self, proyecto: str | None = None, tipo: str | None = None) -> list[Trabajo]:
        ts = [t for t in self._trabajos.values()
              if (proyecto is None or t.proyecto == proyecto) and (tipo is None or t.tipo == tipo)]
        return sorted(ts, key=lambda t: t.creado, reverse=True)

    def activos(self, proyecto: str, tipo: str | None = None) -> list[Trabajo]:
        return [t for t in self.listar(proyecto, tipo) if t.estado in ("pendiente", "ejecutando")]

    def cancelar(self, id_: str) -> bool:
        t = self._trabajos.get(id_)
        if not t:
            return False
        t.cancelar.set()
        return True

    def _limpiar(self):
        # conserva los 200 trabajos más recientes
        if len(self._trabajos) > 200:
            viejos = sorted(self._trabajos.values(), key=lambda t: t.creado)[:-200]
            for t in viejos:
                if t.estado not in ("pendiente", "ejecutando"):
                    self._trabajos.pop(t.id, None)
