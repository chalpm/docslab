# SPDX-License-Identifier: AGPL-3.0-only
"""LAB: los cuadernos del documento como cuadernos de verdad.

Cada cuaderno abierto tiene una «sesión»: el .ipynb en memoria y, cuando hace falta,
un núcleo de Jupyter que sigue vivo entre ejecuciones (las variables se conservan,
como en Jupyter o Colab). Se puede ejecutar una celda, varias o todo el cuaderno,
editar, añadir, mover y borrar celdas, y el .ipynb se guarda con sus salidas.

Las figuras que el código guarda en la carpeta de trabajo se recogen al terminar
cada tanda (igual que con «Ejecutar en limpio») y quedan listas para el documento.
"""
from __future__ import annotations

import ast
import atexit
import json
import os
import queue
import re
import secrets
import shutil
import threading
import time
import warnings
from pathlib import Path

from . import cuadernos as C
from .graficos import DIR_EJEMPLOS
from ..nucleo.almacen import Almacen, ErrorAlmacen, limpiar_nombre

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
OCIOSO_MAX = 3 * 3600                      # un núcleo sin usar se apaga a las tres horas
MAX_TEXTO = 200_000                        # tope del texto de una salida (lo demás se recorta)
EJEMPLO = DIR_EJEMPLOS / "ejemplo.csv"

NB_VACIO = {
    "cells": [], "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                              "language_info": {"name": "python"}},
    "nbformat": 4, "nbformat_minor": 5,
}


def _id_celda() -> str:
    return secrets.token_hex(4)


def crear_cuaderno(alm: Almacen, pid: str, nombre: str) -> dict:
    """Un cuaderno nuevo, vacío, dentro del proyecto."""
    nombre = (nombre or "").strip() or "Cuaderno nuevo"
    if not nombre.lower().endswith(".ipynb"):
        nombre += ".ipynb"
    nb = json.loads(json.dumps(NB_VACIO))
    nb["cells"] = [
        {"cell_type": "markdown", "id": _id_celda(), "metadata": {}, "source": "# " + nombre[:-6]},
        {"cell_type": "code", "id": _id_celda(), "metadata": {}, "execution_count": None, "outputs": [],
         "source": "import pandas as pd\nimport matplotlib.pyplot as plt"},
    ]
    return C.agregar_subido(alm, pid, limpiar_nombre(nombre), json.dumps(nb, ensure_ascii=False, indent=1).encode(), [])


class Sesion:
    def __init__(self, alm: Almacen, pid: str, nb_id: str):
        self.alm, self.pid, self.nb_id = alm, pid, nb_id
        self.mutex = threading.RLock()
        self.km = self.kc = None
        self.cola: list[str] = []
        self.en_curso: str | None = None
        self.hilo: threading.Thread | None = None
        self.rev = 1
        self.revs: dict[str, int] = {}
        self.ultimo_uso = time.time()
        self.mtime = 0.0
        self.error_nucleo = ""
        self.interrumpido = False
        self.figuras_nuevas = 0
        self.tanda = 0                      # cuántas tandas han terminado (para que la interfaz lo note)
        self.nb = None
        self._leer()

    # ------------------------------------------------------------------ archivo
    def _conf(self) -> dict:
        return C._buscar(self.alm.meta(self.pid), self.nb_id)

    def _ruta(self) -> Path:
        return C.ruta_ipynb(self.alm, self.pid, self._conf())

    def _leer(self):
        import nbformat
        ruta = self._ruta()
        if not ruta.exists():
            raise ErrorAlmacen("No encuentro el archivo del cuaderno")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            nb = nbformat.read(str(ruta), as_version=4)
        nb.nbformat_minor = max(5, int(nb.get("nbformat_minor") or 0))
        vistos = set()
        for cel in nb.cells:
            if not cel.get("id") or cel["id"] in vistos:
                cel["id"] = _id_celda()
            vistos.add(cel["id"])
        self.nb = nb
        self.mtime = ruta.stat().st_mtime
        self.rev += 1
        self.revs = {cel["id"]: self.rev for cel in nb.cells}

    def _escribir(self):
        import nbformat
        ruta = self._ruta()
        tmp = ruta.with_suffix(".ipynb.tmp")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            nbformat.write(self.nb, str(tmp))
        os.replace(tmp, ruta)
        self.mtime = ruta.stat().st_mtime

    def refrescar(self):
        """Si alguien cambió el .ipynb por fuera (Drive, Jupyter) y no estamos ejecutando, se relee."""
        with self.mutex:
            if self.ocupado():
                return
            try:
                if self._ruta().stat().st_mtime > self.mtime + 0.5:
                    self._leer()
            except OSError:
                pass

    # ------------------------------------------------------------------ vista para la interfaz
    def ocupado(self) -> bool:
        return bool(self.en_curso or self.cola)

    def estado_nucleo(self) -> dict:
        vivo = bool(self.km and self.km.is_alive())
        return {"estado": "ocupado" if self.ocupado() else ("listo" if vivo else "apagado"),
                "en_curso": self.en_curso, "cola": list(self.cola), "error": self.error_nucleo,
                "tanda": self.tanda, "figuras_nuevas": self.figuras_nuevas}

    def _celda(self, cel) -> dict:
        d = {"id": cel["id"], "tipo": "codigo" if cel.cell_type == "code" else ("texto" if cel.cell_type == "markdown" else "crudo"),
             "fuente": cel.source, "meta": dict(cel.metadata.get("docslab") or {})}
        if cel.cell_type == "code":
            d["n"] = cel.get("execution_count")
            d["salidas"] = [s for s in (_salida(o) for o in cel.get("outputs", [])) if s]
        return d

    def como_dict(self) -> dict:
        with self.mutex:
            return {"celdas": [self._celda(c) for c in self.nb.cells], "nucleo": self.estado_nucleo(), "rev": self.rev}

    def cambios(self, desde: int) -> dict:
        with self.mutex:
            return {"nucleo": self.estado_nucleo(), "rev": self.rev,
                    "celdas": [self._celda(c) for c in self.nb.cells
                               if c.cell_type == "code" and self.revs.get(c["id"], 0) > desde]}

    def _tocar(self, cid: str):
        self.rev += 1
        self.revs[cid] = self.rev

    # ------------------------------------------------------------------ edición
    def guardar(self, celdas: list[dict]):
        """Sustituye la lista de celdas (orden, tipo y texto). Las salidas se conservan por id."""
        import nbformat
        if not isinstance(celdas, list) or len(celdas) > 5000:
            raise ErrorAlmacen("Lista de celdas no válida")
        with self.mutex:
            por_id = {c["id"]: c for c in self.nb.cells}
            nuevas, vistos = [], set()
            for d in celdas:
                cid = str(d.get("id") or "")
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", cid) or cid in vistos:
                    cid = _id_celda()
                vistos.add(cid)
                tipo = {"codigo": "code", "texto": "markdown", "crudo": "raw"}.get(d.get("tipo"), "code")
                fuente = str(d.get("fuente") or "")
                cel = por_id.get(cid)
                if cel is None or cel.cell_type != tipo:
                    hacer = {"code": nbformat.v4.new_code_cell, "markdown": nbformat.v4.new_markdown_cell,
                             "raw": nbformat.v4.new_raw_cell}[tipo]
                    viejo = cel
                    cel = hacer(fuente)
                    cel["id"] = cid
                    if viejo is not None:
                        cel.metadata.update(viejo.metadata)
                    self._tocar(cid)
                else:
                    cel.source = fuente
                meta = d.get("meta")
                if isinstance(meta, dict) and meta:
                    cel.metadata["docslab"] = json.loads(json.dumps(meta))
                else:
                    cel.metadata.pop("docslab", None)
                nuevas.append(cel)
            self.nb.cells = nuevas
            self.cola = [c for c in self.cola if c in vistos]
            self._escribir()

    def limpiar_salidas(self):
        with self.mutex:
            if self.ocupado():
                raise ErrorAlmacen("Espera a que termine la ejecución")
            for cel in self.nb.cells:
                if cel.cell_type == "code":
                    cel.outputs, cel.execution_count = [], None
                    self._tocar(cel["id"])
            self._escribir()

    # ------------------------------------------------------------------ núcleo
    def _arrancar(self):
        from jupyter_client import KernelManager
        conf = self._conf()
        trabajo_dir = C.dir_trabajo(self.alm, self.pid, conf)
        trabajo_dir.mkdir(parents=True, exist_ok=True)
        entorno = dict(os.environ, DOCSLAB="1", POSTERLAB="1", PLOTLY_RENDERER="plotly_mimetype")
        entorno.pop("MPLBACKEND", None)
        km = KernelManager(kernel_name=conf.get("kernel") or C._kernel(self.nb))
        km.start_kernel(cwd=str(trabajo_dir), env=entorno)
        kc = km.client()
        kc.start_channels()
        try:
            kc.wait_for_ready(timeout=60)
        except Exception:
            kc.stop_channels()
            km.shutdown_kernel(now=True)
            raise
        self.km, self.kc = km, kc
        self.error_nucleo = ""

    def apagar(self):
        with self.mutex:
            self.cola = []
            km, kc, self.km, self.kc = self.km, self.kc, None, None
        try:
            if kc:
                kc.stop_channels()
            if km:
                km.shutdown_kernel(now=True)
        except Exception:  # noqa: BLE001
            pass

    def interrumpir(self):
        with self.mutex:
            self.cola = []
            self.interrumpido = True
            km = self.km
        if km and km.is_alive():
            try:
                km.interrupt_kernel()
            except Exception:  # noqa: BLE001
                pass

    def reiniciar(self):
        """Apaga el núcleo (se pierden las variables). El siguiente «ejecutar» arranca uno nuevo."""
        self.interrumpir()
        hilo = self.hilo
        if hilo and hilo.is_alive():
            self.apagar()                       # la celda en curso termina con «núcleo muerto»
            hilo.join(timeout=10)
        self.apagar()
        with self.mutex:
            for cel in self.nb.cells:
                if cel.cell_type == "code" and cel.get("execution_count") is not None:
                    cel.execution_count = None
                    self._tocar(cel["id"])

    def borrar_variables(self) -> bool:
        """Borra las variables del núcleo (como «%reset -f») sin reiniciarlo: es más rápido, pero los
        paquetes ya importados siguen cargados (para usar uno recién instalado hay que reiniciar).
        Devuelve False si el núcleo estaba apagado (no había nada que borrar)."""
        with self.mutex:
            if self.ocupado():
                raise ErrorAlmacen("Python está ocupado: espera a que termine la celda o interrúmpela")
            if not (self.km and self.km.is_alive()):
                return False
            self.ultimo_uso = time.time()
            kc = self.kc
            msg_id = kc.execute("get_ipython().run_line_magic('reset', '-f')", silent=True, store_history=False)
            limite = time.time() + 20
            while time.time() < limite:
                try:
                    r = kc.get_shell_msg(timeout=1)
                except queue.Empty:
                    continue
                if r["parent_header"].get("msg_id") == msg_id:
                    break
            else:
                raise ErrorAlmacen("Python no respondió a tiempo")
            for cel in self.nb.cells:                   # los números de ejecución ya no valen
                if cel.cell_type == "code" and cel.get("execution_count") is not None:
                    cel.execution_count = None
                    self._tocar(cel["id"])
            return True

    # ------------------------------------------------------------------ ejecución
    def ejecutar(self, ids: list[str] | None):
        with self.mutex:
            validos = [c["id"] for c in self.nb.cells if c.cell_type == "code" and c.source.strip()]
            pedir = validos if ids is None else [i for i in ids if i in validos]
            for cid in pedir:
                if cid not in self.cola and cid != self.en_curso:
                    self.cola.append(cid)
            self.ultimo_uso = time.time()
            if self.cola and not (self.hilo and self.hilo.is_alive()):
                self.interrumpido = False
                self.hilo = threading.Thread(target=self._trabajar, daemon=True)
                self.hilo.start()

    def _trabajar(self):
        inicio = time.time()
        try:
            if not (self.km and self.km.is_alive()):
                self.apagar_canales()
                self._arrancar()
        except Exception as exc:  # noqa: BLE001
            with self.mutex:
                self.error_nucleo = f"No se pudo iniciar el núcleo de Python: {exc}"[:600]
                self.cola = []
                self.tanda += 1
                self.rev += 1
            return
        tiempo = int(self._conf().get("tiempo_celda") or 3600)
        while True:
            with self.mutex:
                if not self.cola:
                    break
                cid = self.cola.pop(0)
                cel = next((c for c in self.nb.cells if c["id"] == cid and c.cell_type == "code"), None)
                if cel is None:
                    continue
                self.en_curso = cid
                cel.outputs, cel.execution_count = [], None
                self._tocar(cid)
            ok = False
            try:
                ok = self._una(cel, tiempo)
            except Exception as exc:  # noqa: BLE001
                with self.mutex:
                    if not self.interrumpido:
                        self.error_nucleo = f"El núcleo se detuvo: {exc}"[:600]
                    self.cola = []
            with self.mutex:
                self.en_curso = None
                self._tocar(cid)
                if not ok:
                    self.cola = []             # como «ejecutar todo» en Jupyter: se para en el primer error
                try:
                    self._escribir()
                except OSError:
                    pass
        # figuras que el código guardó en la carpeta de trabajo
        nuevas = 0
        try:
            conf = self._conf()
            figs = C.recoger(self.alm, self.pid, conf, C.dir_trabajo(self.alm, self.pid, conf), inicio - 2)
            nuevas = len(figs)
        except Exception:  # noqa: BLE001
            pass
        try:                                   # para la tarjeta del cuaderno: cuándo y cómo fue la última vez
            meta = self.alm.meta(self.pid)
            c = C._buscar(meta, self.nb_id)
            fallo = next((o for cel in self.nb.cells if cel.cell_type == "code" for o in cel.get("outputs", [])
                          if o.get("output_type") == "error"), None)
            c["ultima_ejecucion"] = {
                "ok": fallo is None and not self.error_nucleo, "segundos": round(time.time() - inicio, 1),
                "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_figuras": nuevas,
                "error": None if fallo is None else {"tipo": fallo.get("ename", "Error"),
                                                      "mensaje": str(fallo.get("evalue", ""))[:500]}}
            self.alm.guardar_meta(self.pid, meta)
        except Exception:  # noqa: BLE001
            pass
        with self.mutex:
            self.figuras_nuevas = nuevas
            self.ultimo_uso = time.time()
            self.tanda += 1
            self.rev += 1

    def apagar_canales(self):
        if self.kc or self.km:
            self.apagar()

    def _una(self, cel, tiempo: int) -> bool:
        from nbformat.v4 import output_from_msg
        kc = self.kc
        if kc is None:
            raise RuntimeError("sin núcleo")
        msg_id = kc.execute(cel.source, store_history=True, allow_stdin=False)
        limite = time.time() + tiempo
        ok = True
        respuesta, gracia = None, 0.0
        while True:
            try:
                msg = kc.get_iopub_msg(timeout=1)
            except queue.Empty:
                if self.km is None or not self.km.is_alive():
                    raise RuntimeError("el proceso de Python terminó (¿memoria agotada?)")
                # Red de seguridad: si Python ya contestó que terminó (canal shell) pero el «idle» del canal
                # iopub no llega, se da la celda por terminada a los 3 s en vez de esperar todo el límite.
                if respuesta is None:
                    respuesta = _respuesta_shell(kc, msg_id)
                    gracia = time.time() + 3
                elif time.time() > gracia:
                    if respuesta.get("status") == "error":
                        ok = False
                    break
                if time.time() > limite:
                    self.interrumpir()
                    limite = time.time() + 30
                    with self.mutex:
                        cel.outputs.append(_error_propio("Tiempo agotado", f"La celda tardó más de {tiempo} s"))
                    ok = False
                continue
            if msg["parent_header"].get("msg_id") != msg_id:
                continue
            tipo, cont = msg["msg_type"], msg["content"]
            if tipo == "status":
                if cont.get("execution_state") == "idle":
                    break
                continue
            with self.mutex:
                if tipo == "execute_input":
                    cel.execution_count = cont.get("execution_count")
                elif tipo == "clear_output":
                    cel.outputs = []
                elif tipo in ("stream", "display_data", "execute_result", "error"):
                    out = output_from_msg(msg)
                    if tipo == "error":
                        ok = False
                    ultimo = cel.outputs[-1] if cel.outputs else None
                    if tipo == "stream" and ultimo is not None and ultimo.get("output_type") == "stream" \
                            and ultimo.get("name") == out.get("name"):
                        ultimo["text"] = (ultimo["text"] + out["text"])[-MAX_TEXTO:]
                    else:
                        cel.outputs.append(out)
                else:
                    continue
                self._tocar(cel["id"])
        return ok

    # ------------------------------------------------------------------ consultas al núcleo
    def consulta(self, codigo: str, tiempo: float = 20):
        """Evalúa en silencio una expresión que devuelve un texto JSON. Arranca el núcleo si hace falta."""
        with self.mutex:
            if self.ocupado():
                raise ErrorAlmacen("El núcleo está ocupado: espera a que termine la celda")
            self.ultimo_uso = time.time()
            if not (self.km and self.km.is_alive()):
                self.apagar_canales()
                try:
                    self._arrancar()
                except Exception as exc:  # noqa: BLE001
                    raise ErrorAlmacen(f"No se pudo iniciar el núcleo de Python: {exc}")
            kc = self.kc
            msg_id = kc.execute("", silent=True, store_history=False, user_expressions={"r": codigo})
            limite = time.time() + tiempo
            while time.time() < limite:
                try:
                    r = kc.get_shell_msg(timeout=1)
                except queue.Empty:
                    continue
                if r["parent_header"].get("msg_id") != msg_id:
                    continue
                exp = (r["content"].get("user_expressions") or {}).get("r") or {}
                if exp.get("status") != "ok":
                    raise ErrorAlmacen(f"{exp.get('ename', 'Error')}: {exp.get('evalue', '')}"[:400])
                return json.loads(ast.literal_eval(exp["data"]["text/plain"]))
            raise ErrorAlmacen("El núcleo no respondió a tiempo")


def _respuesta_shell(kc, msg_id: str) -> dict | None:
    """El «execute_reply» de msg_id si ya está en el canal shell (sin esperar); None si no."""
    while True:
        try:
            r = kc.get_shell_msg(timeout=0)
        except queue.Empty:
            return None
        if r["parent_header"].get("msg_id") == msg_id and r.get("msg_type") == "execute_reply":
            return r.get("content") or {}


def _error_propio(nombre: str, valor: str):
    from nbformat.v4 import new_output
    return new_output("error", ename=nombre, evalue=valor, traceback=[])


def _salida(o) -> dict | None:
    """Una salida de nbformat, resumida para pintarla en la interfaz."""
    t = o.get("output_type")
    if t == "stream":
        return {"t": "texto", "canal": o.get("name", "stdout"), "texto": ANSI.sub("", str(o.get("text", "")))[-MAX_TEXTO:]}
    if t == "error":
        traza = ANSI.sub("", "\n".join(o.get("traceback") or []))
        return {"t": "error", "nombre": o.get("ename", "Error"), "valor": str(o.get("evalue", ""))[:2000],
                "traza": traza[-20000:]}
    if t in ("display_data", "execute_result"):
        d = o.get("data") or {}
        if "application/vnd.plotly.v1+json" in d:
            return {"t": "plotly", "figura": d["application/vnd.plotly.v1+json"]}
        for mime in ("image/png", "image/jpeg"):
            if mime in d:
                return {"t": "img", "mime": mime, "b64": "".join(d[mime]) if isinstance(d[mime], list) else d[mime]}
        if "image/svg+xml" in d:
            svg = d["image/svg+xml"]
            return {"t": "svg", "svg": "".join(svg) if isinstance(svg, list) else svg}
        if "text/html" in d:
            html = d["text/html"]
            return {"t": "html", "html": ("".join(html) if isinstance(html, list) else html)[:MAX_TEXTO * 3]}
        if "text/markdown" in d:
            md = d["text/markdown"]
            return {"t": "texto", "canal": "stdout", "texto": "".join(md) if isinstance(md, list) else md}
        if "text/plain" in d:
            tx = d["text/plain"]
            return {"t": "texto", "canal": "resultado", "texto": ("".join(tx) if isinstance(tx, list) else tx)[-MAX_TEXTO:]}
    return None


# ---------------------------------------------------------------------- consultas hechas
CONSULTA_VARIABLES = (
    "__import__('json').dumps([{'nombre': k, 'filas': int(v.shape[0]), 'columnas': int(v.shape[1])} "
    "for k, v in list(globals().items()) if not k.startswith('_') and type(v).__name__ == 'DataFrame' "
    "and type(v).__module__.startswith('pandas')])"
)


def _exp_columnas(expresion: str) -> str:
    return ("(lambda _d: __import__('json').dumps({'columnas': [{'nombre': str(c), "
            "'numerica': bool(__import__('pandas').api.types.is_numeric_dtype(_d[c]))} for c in _d.columns][:400], "
            "'filas': int(len(_d))}))(" + expresion + ")")


def expresion_datos(datos: dict) -> str:
    """La expresión de Python que carga los datos elegidos en el formulario de un gráfico."""
    if (datos or {}).get("modo") == "variable":
        var = str(datos.get("variable") or "")
        if not var.isidentifier():
            raise ErrorAlmacen("Nombre de variable no válido")
        return var
    archivo = str((datos or {}).get("archivo") or "")
    if not archivo or ".." in Path(archivo).parts or Path(archivo).is_absolute():
        raise ErrorAlmacen("Elige un archivo de datos de la carpeta del cuaderno")
    ext = Path(archivo).suffix.lower()
    if ext in (".xlsx", ".xls"):
        return f"__import__('pandas').read_excel({archivo!r})"
    if ext == ".parquet":
        return f"__import__('pandas').read_parquet({archivo!r})"
    if ext == ".json":
        return f"__import__('pandas').read_json({archivo!r})"
    return f"__import__('pandas').read_csv({archivo!r}, sep=None, engine='python')"


class Lab:
    """Las sesiones abiertas de todos los proyectos."""

    def __init__(self, alm: Almacen):
        self.alm = alm
        self._sesiones: dict[tuple[str, str], Sesion] = {}
        self._mutex = threading.Lock()
        atexit.register(self.apagar_todo)

    def sesion(self, pid: str, nb_id: str) -> Sesion:
        with self._mutex:
            ahora = time.time()
            for k, s in list(self._sesiones.items()):
                if not s.ocupado() and ahora - s.ultimo_uso > OCIOSO_MAX:
                    s.apagar()
                    del self._sesiones[k]
            s = self._sesiones.get((pid, nb_id))
            if s is None:
                s = self._sesiones[(pid, nb_id)] = Sesion(self.alm, pid, nb_id)
        s.refrescar()
        return s

    def cerrar(self, pid: str, nb_id: str | None = None):
        with self._mutex:
            claves = [k for k in self._sesiones if k[0] == pid and (nb_id is None or k[1] == nb_id)]
            sesiones = [self._sesiones.pop(k) for k in claves]
        for s in sesiones:
            s.interrumpir()
            s.apagar()

    def apagar_todo(self):
        with self._mutex:
            sesiones, self._sesiones = list(self._sesiones.values()), {}
        for s in sesiones:
            s.apagar()

    def copiar_ejemplo(self, pid: str, nb_id: str, archivos=None) -> str:
        """Copia a la carpeta del cuaderno los datos de ejemplo pedidos (por defecto, ejemplo.csv) y
        devuelve el primero. Solo valen nombres de archivos que existen en datos_ejemplo/."""
        conf = C._buscar(self.alm.meta(pid), nb_id)
        d = C.dir_trabajo(self.alm, pid, conf)
        d.mkdir(parents=True, exist_ok=True)
        pedidos = [a for a in (archivos if isinstance(archivos, list) else []) if isinstance(a, str)
                   and a == Path(a).name and (EJEMPLO.parent / a).is_file()] or [EJEMPLO.name]
        for a in pedidos:
            if not (d / a).exists():
                shutil.copy2(EJEMPLO.parent / a, d / a)
        return pedidos[0]
