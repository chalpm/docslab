"""Extensión de cuadernos: ejecutar .ipynb (los de Colab) y recoger sus figuras.

Un cuaderno puede estar:
  * «subido»: el .ipynb y sus datos se copian a proyectos/<p>/cuadernos/<id>/ y se
    ejecuta ahí;
  * «ruta»: se ejecuta en su propia carpeta del servidor (por ejemplo, tu Google
    Drive montado cuando la aplicación corre dentro de Colab).

Al terminar, las figuras nuevas (PNG, JPG, PDF) se copian a
recursos/cuadernos/<id>/ conservando su ruta relativa, así que el póster que
ya las usa se actualiza solo.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import secrets
import shutil
import signal
import threading
import time
import zipfile
from pathlib import Path

from .almacen import Almacen, ErrorAlmacen, limpiar_nombre, limpiar_ruta, unir

EXT_FIGURA = ("png", "jpg", "jpeg", "pdf")
SALTAR_DIRS = {".ipynb_checkpoints", "__pycache__", ".git", "node_modules", ".venv", "venv", "build"}
PATRON_COLAB = re.compile(r"(^|\n)\s*(from\s+google\.colab\s+import|import\s+google\.colab|"
                          r"drive\.mount\(|files\.upload\(|files\.download\()")

CELDA_COLAB = '''# DocsLab · exportar las figuras de este cuaderno
# Ejecuta esta celda al final del cuaderno en Google Colab y sube el zip
# en DocsLab › Cuadernos › «Importar zip de Colab».
import shutil
from google.colab import files

CARPETA = "{carpeta}"   # carpeta donde el cuaderno guarda sus figuras
zip_ = shutil.make_archive("figuras_docslab", "zip", root_dir=".", base_dir=CARPETA)
files.download(zip_)
'''

DEFECTO = {"patrones_ext": ["pdf", "png", "jpg"], "carpeta_figuras": "", "preferir_pdf": True,
           "recoger_mostradas": False, "omitir_colab": False, "parametros": {"despues_de": -1, "codigo": ""},
           "tiempo_celda": 3600, "recompilar": True, "kernel": ""}


def nuevo_id() -> str:
    return "nb-" + secrets.token_hex(3)


def _buscar(meta: dict, nb_id: str) -> dict:
    for c in meta.get("cuadernos", []):
        if c.get("id") == nb_id:
            for k, v in DEFECTO.items():
                c.setdefault(k, json.loads(json.dumps(v)))
            return c
    raise ErrorAlmacen("Cuaderno no encontrado")


def dir_trabajo(alm: Almacen, pid: str, c: dict) -> Path:
    if c.get("origen") == "ruta":
        return Path(c["ruta"]).resolve().parent
    return alm.dir_proyecto(pid) / "cuadernos" / c["id"]


def ruta_ipynb(alm: Almacen, pid: str, c: dict) -> Path:
    if c.get("origen") == "ruta":
        return Path(c["ruta"]).resolve()
    return dir_trabajo(alm, pid, c) / c["archivo"]


# --------------------------------------------------------------------- alta y datos
def agregar_subido(alm: Almacen, pid: str, nombre: str, datos: bytes, extras: list[tuple[str, bytes]]) -> dict:
    if not nombre.lower().endswith(".ipynb"):
        raise ErrorAlmacen("El cuaderno debe ser un archivo .ipynb")
    try:
        nb = json.loads(datos.decode("utf-8"))
        assert isinstance(nb.get("cells"), list)
    except Exception:
        raise ErrorAlmacen("El archivo no parece un cuaderno de Jupyter/Colab válido")
    meta = alm.meta(pid)
    c = dict(json.loads(json.dumps(DEFECTO)), id=nuevo_id(), nombre=nombre, archivo=limpiar_nombre(nombre),
             origen="subido")
    d = alm.dir_proyecto(pid) / "cuadernos" / c["id"]
    d.mkdir(parents=True)
    (d / c["archivo"]).write_bytes(datos)
    for n, b in extras:
        _guardar_dato(d, n, b)
    c["carpeta_figuras"] = adivinar_carpeta(nb)
    meta.setdefault("cuadernos", []).append(c)
    alm.guardar_meta(pid, meta)
    return c


def enlazar_ruta(alm: Almacen, pid: str, ruta: str, raices: list[Path]) -> dict:
    p = Path(ruta).expanduser().resolve()
    if not p.is_file() or p.suffix.lower() != ".ipynb":
        raise ErrorAlmacen("No encuentro ese .ipynb en el servidor")
    if raices and not any(r == p or r in p.parents for r in raices):
        raise ErrorAlmacen("Esa carpeta no está permitida (ver --raices)")
    nb = json.loads(p.read_text(encoding="utf-8"))
    meta = alm.meta(pid)
    c = dict(json.loads(json.dumps(DEFECTO)), id=nuevo_id(), nombre=p.name, archivo=p.name, origen="ruta",
             ruta=str(p))
    c["carpeta_figuras"] = adivinar_carpeta(nb)
    meta.setdefault("cuadernos", []).append(c)
    alm.guardar_meta(pid, meta)
    return c


def _guardar_dato(d: Path, nombre: str, datos: bytes):
    rel = limpiar_ruta(nombre)
    if not rel:
        return
    destino = unir(d, rel)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos)


def agregar_datos(alm: Almacen, pid: str, nb_id: str, archivos: list[tuple[str, bytes]]) -> list[str]:
    meta = alm.meta(pid)
    c = _buscar(meta, nb_id)
    if c.get("origen") == "ruta":
        raise ErrorAlmacen("Este cuaderno usa su propia carpeta: copia ahí los datos")
    d = dir_trabajo(alm, pid, c)
    for n, b in archivos:
        if n.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                for info in z.infolist():
                    if not info.is_dir() and "__MACOSX" not in info.filename:
                        _guardar_dato(d, info.filename, z.read(info))
        else:
            _guardar_dato(d, n, b)
    return [p["ruta"] for p in listar_archivos(alm, pid, nb_id)]


def listar_archivos(alm: Almacen, pid: str, nb_id: str, limite: int = 300) -> list[dict]:
    c = _buscar(alm.meta(pid), nb_id)
    d = dir_trabajo(alm, pid, c)
    salida = []
    if not d.exists():
        return salida
    for raiz, dirs, archivos in os.walk(d):
        dirs[:] = sorted(x for x in dirs if x not in SALTAR_DIRS)
        for a in sorted(archivos):
            p = Path(raiz) / a
            salida.append({"ruta": p.relative_to(d).as_posix(), "tamano": p.stat().st_size})
            if len(salida) >= limite:
                return salida
    return salida


def configurar(alm: Almacen, pid: str, nb_id: str, cambios: dict) -> dict:
    meta = alm.meta(pid)
    c = _buscar(meta, nb_id)
    for k in DEFECTO:
        if k in cambios:
            c[k] = cambios[k]
    if "nombre" in cambios:
        c["nombre"] = str(cambios["nombre"])[:120]
    alm.guardar_meta(pid, meta)
    return c


def borrar(alm: Almacen, pid: str, nb_id: str, borrar_figuras: bool = False):
    meta = alm.meta(pid)
    c = _buscar(meta, nb_id)
    if c.get("origen") != "ruta":
        shutil.rmtree(alm.dir_proyecto(pid) / "cuadernos" / nb_id, ignore_errors=True)
    if borrar_figuras:
        shutil.rmtree(alm.dir_proyecto(pid) / "recursos" / "cuadernos" / nb_id, ignore_errors=True)
    meta["cuadernos"] = [x for x in meta["cuadernos"] if x.get("id") != nb_id]
    alm.guardar_meta(pid, meta)


def celdas(alm: Almacen, pid: str, nb_id: str) -> list[dict]:
    c = _buscar(alm.meta(pid), nb_id)
    nb = json.loads(ruta_ipynb(alm, pid, c).read_text(encoding="utf-8"))
    salida = []
    for i, cel in enumerate(nb.get("cells", [])):
        src = cel.get("source", "")
        src = "".join(src) if isinstance(src, list) else src
        primera = next((ln for ln in src.splitlines() if ln.strip()), "")
        salida.append({"indice": i, "tipo": cel.get("cell_type"), "primera": primera[:110],
                       "colab": bool(PATRON_COLAB.search(src)) if cel.get("cell_type") == "code" else False})
    return salida


def adivinar_carpeta(nb: dict) -> str:
    """Carpeta de figuras que declara el cuaderno (output_dir, resultados…), si se ve."""
    for cel in nb.get("cells", []):
        if cel.get("cell_type") != "code":
            continue
        src = cel.get("source", "")
        src = "".join(src) if isinstance(src, list) else src
        m = re.search(r"""["'](?:output_dir|carpeta_resultados|results_dir|out_dir)["']\s*:\s*["']([^"']+)["']""", src)
        if m:
            return m.group(1).strip("/")
    return ""


def celda_exportar(alm: Almacen, pid: str, nb_id: str) -> str:
    c = _buscar(alm.meta(pid), nb_id)
    return CELDA_COLAB.format(carpeta=c.get("carpeta_figuras") or "resultados")


# --------------------------------------------------------------------- ejecución
def ejecutar(alm: Almacen, pid: str, nb_id: str, trabajo) -> dict:
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError, CellTimeoutError, DeadKernelError

    meta = alm.meta(pid)
    c = _buscar(meta, nb_id)
    ruta = ruta_ipynb(alm, pid, c)
    trabajo_dir = dir_trabajo(alm, pid, c)
    if not ruta.exists():
        raise ErrorAlmacen("No encuentro el archivo del cuaderno")
    import warnings
    with warnings.catch_warnings():                    # cuadernos antiguos sin ids de celda
        warnings.simplefilter("ignore")
        nb = nbformat.read(str(ruta), as_version=4)
    if any("id" not in cel for cel in nb.cells):      # ids de celda (nbformat ≥ 4.5)
        nb.nbformat_minor = max(5, int(nb.get("nbformat_minor") or 0))
        for cel in nb.cells:
            cel.setdefault("id", secrets.token_hex(4))
    # celdas de Colab que no tienen sentido aquí (montar Drive, subir archivos…)
    omitidas = 0
    if c.get("omitir_colab"):
        for cel in nb.cells:
            if cel.cell_type == "code" and PATRON_COLAB.search(cel.source):
                cel.source = "# (DocsLab omitió esta celda de Colab)\n" + "\n".join(
                    "# " + ln for ln in cel.source.splitlines())
                omitidas += 1
    # parámetros: una celda nueva después de la elegida
    par = c.get("parametros") or {}
    codigo = str(par.get("codigo") or "").strip()
    if codigo:
        idx = int(par.get("despues_de", -1))
        nueva = nbformat.v4.new_code_cell("# Parámetros inyectados por DocsLab\n" + codigo)
        nueva.metadata["tags"] = ["injected-parameters"]
        pos = min(max(idx + 1, 0), len(nb.cells))
        nb.cells.insert(pos, nueva)
    codigos = [i for i, cel in enumerate(nb.cells) if cel.cell_type == "code" and cel.source.strip()]
    total = max(1, len(codigos))
    kernel = c.get("kernel") or _kernel(nb)
    trabajo.informar(f"Iniciando el núcleo «{kernel}» en {trabajo_dir}", 0.01)
    if omitidas:
        trabajo.informar(f"Se omitieron {omitidas} celdas propias de Colab")
    inicio = time.time()
    hechas = {"n": 0}

    def al_empezar(cell=None, cell_index=None, **_):
        linea = next((ln for ln in (cell.source or "").splitlines() if ln.strip()), "")[:80]
        if cell.cell_type != "code":
            if linea.startswith("#"):                     # títulos de sección, como referencia
                trabajo.anotar("  " + linea.lstrip("# ").strip())
            return
        if not (cell.source or "").strip():
            return
        hechas["n"] += 1
        trabajo.informar(f"Celda de código {hechas['n']} de {total} · {linea}",
                         0.02 + 0.9 * (hechas["n"] - 1) / total)

    def al_terminar(cell=None, cell_index=None, **_):
        # on_cell_executed: la celda ya tiene sus salidas
        for out in cell.get("outputs", []):
            if out.get("output_type") == "stream":
                for ln in str(out.get("text", "")).splitlines()[-6:]:
                    trabajo.anotar("    " + ln[:200])

    cliente = NotebookClient(nb, timeout=int(c.get("tiempo_celda") or 3600), kernel_name=kernel,
                             resources={"metadata": {"path": str(trabajo_dir)}}, allow_errors=False,
                             record_timing=True, on_cell_start=al_empezar, on_cell_executed=al_terminar)
    vigilante_para = threading.Event()

    def vigilar():
        avisado = False
        while not vigilante_para.is_set():
            if trabajo.cancelar.is_set():
                if not avisado:
                    trabajo.informar("Cancelando: deteniendo el núcleo")
                    avisado = True
                if _detener_nucleo(cliente):      # si el núcleo aún no existe, se reintenta
                    return
            time.sleep(0.5)

    threading.Thread(target=vigilar, daemon=True).start()
    error = None
    os.environ["DOCSLAB"] = "1"
    os.environ["POSTERLAB"] = "1"          # los cuadernos hechos para PosterLab siguen funcionando
    try:
        cliente.execute()
    except CellExecutionError as exc:
        error = _resumen_error(exc)
    except (CellTimeoutError, DeadKernelError) as exc:
        error = {"tipo": type(exc).__name__, "mensaje": str(exc)[:500]}
    except Exception as exc:  # noqa: BLE001
        if trabajo.cancelar.is_set():
            error = {"tipo": "cancelado", "mensaje": "Ejecución cancelada"}
        else:
            error = {"tipo": type(exc).__name__, "mensaje": str(exc)[:800]}
    finally:
        vigilante_para.set()
    if trabajo.cancelar.is_set():
        error = {"tipo": "cancelado", "mensaje": "Ejecución cancelada"}
    destino_nb = alm.dir_proyecto(pid) / "cuadernos" / nb_id
    destino_nb.mkdir(parents=True, exist_ok=True)
    try:
        nbformat.write(nb, str(destino_nb / "ejecutado.ipynb"))
    except Exception:
        pass
    trabajo.informar("Recogiendo figuras", 0.94)
    figuras = recoger(alm, pid, c, trabajo_dir, inicio - 2)
    if c.get("recoger_mostradas"):
        figuras += recoger_mostradas(alm, pid, nb_id, nb)
    resumen = {"ok": error is None, "error": error, "segundos": round(time.time() - inicio, 1),
               "celdas": total, "figuras": figuras, "fecha": time.strftime("%Y-%m-%dT%H:%M:%S")}
    meta = alm.meta(pid)
    c2 = _buscar(meta, nb_id)
    c2["ultima_ejecucion"] = {k: v for k, v in resumen.items() if k != "figuras"}
    c2["ultima_ejecucion"]["n_figuras"] = len(figuras)
    alm.guardar_meta(pid, meta)
    trabajo.informar(("Terminado" if error is None else "Terminó con errores") +
                     f" · {len(figuras)} figuras recogidas", 1.0)
    return resumen


def _detener_nucleo(cliente) -> bool:
    """Interrumpe y, si hace falta, mata el proceso del núcleo (nbclient lo verá muerto)."""
    km = getattr(cliente, "km", None)
    proc = getattr(getattr(km, "provisioner", None), "process", None)
    if proc is None:
        return False
    try:
        if os.name != "nt":
            proc.send_signal(signal.SIGINT)
    except Exception:  # noqa: BLE001
        pass
    for _ in range(10):
        if proc.poll() is not None:
            return True
        time.sleep(0.15)
    try:
        proc.kill()
    except Exception:  # noqa: BLE001
        pass
    return True


def _kernel(nb) -> str:
    nombre = (nb.metadata.get("kernelspec") or {}).get("name") or "python3"
    try:
        from jupyter_client.kernelspec import find_kernel_specs
        disponibles = find_kernel_specs()
        if nombre not in disponibles:
            return "python3" if "python3" in disponibles else next(iter(disponibles), "python3")
    except Exception:
        pass
    return nombre


def _resumen_error(exc) -> dict:
    texto = str(exc)
    texto = re.sub(r"\x1b\[[0-9;]*m", "", texto)
    lineas = [ln for ln in texto.splitlines() if ln.strip()]
    return {"tipo": getattr(exc, "ename", "Error"), "mensaje": getattr(exc, "evalue", "")[:500],
            "detalle": "\n".join(lineas[-25:])}


def recoger(alm: Almacen, pid: str, c: dict, trabajo_dir: Path, desde: float) -> list[dict]:
    """Copia a recursos/cuadernos/<id>/ las figuras creadas o cambiadas desde «desde»."""
    exts = {("." + e.lower().lstrip(".")) for e in (c.get("patrones_ext") or EXT_FIGURA)}
    exts &= {".png", ".jpg", ".jpeg", ".pdf"}
    base = trabajo_dir
    if c.get("carpeta_figuras"):
        cand = (trabajo_dir / c["carpeta_figuras"]).resolve()
        if cand.exists() and (cand == trabajo_dir.resolve() or trabajo_dir.resolve() in cand.parents):
            base = cand
    encontrados = []
    vistos = 0
    for raiz, dirs, archivos in os.walk(base):
        dirs[:] = [x for x in dirs if x not in SALTAR_DIRS and not x.startswith(".")]
        for a in archivos:
            vistos += 1
            if vistos > 50000:
                break
            p = Path(raiz) / a
            if p.suffix.lower() in exts:
                try:
                    if p.stat().st_mtime >= desde:
                        encontrados.append(p)
                except OSError:
                    pass
    if c.get("preferir_pdf", True):
        pdfs = {p.with_suffix("") for p in encontrados if p.suffix.lower() == ".pdf"}
        encontrados = [p for p in encontrados if p.suffix.lower() == ".pdf" or p.with_suffix("") not in pdfs]
    proyecto = alm.dir_proyecto(pid)
    destino_base = proyecto / "recursos" / "cuadernos" / c["id"]
    salida = []
    for p in sorted(encontrados):
        rel = p.relative_to(trabajo_dir).as_posix()
        destino = unir(destino_base, limpiar_ruta(rel))
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, destino)
        salida.append({"ruta": destino.relative_to(proyecto).as_posix(), "origen": rel,
                       "tamano": destino.stat().st_size})
    return salida


def recoger_mostradas(alm: Almacen, pid: str, nb_id: str, nb) -> list[dict]:
    """Guarda las imágenes que el cuaderno mostró (salidas image/png)."""
    proyecto = alm.dir_proyecto(pid)
    destino = proyecto / "recursos" / "cuadernos" / nb_id / "salidas"
    salida = []
    for i, cel in enumerate(nb.cells):
        k = 0
        for out in cel.get("outputs", []) if cel.cell_type == "code" else []:
            datos = (out.get("data") or {}).get("image/png")
            if not datos:
                continue
            k += 1
            destino.mkdir(parents=True, exist_ok=True)
            p = destino / f"celda-{i + 1:03d}-{k}.png"
            p.write_bytes(base64.b64decode(datos))
            salida.append({"ruta": p.relative_to(proyecto).as_posix(), "origen": f"salida de la celda {i + 1}",
                           "tamano": p.stat().st_size})
    return salida


def importar_zip(alm: Almacen, pid: str, nb_id: str, datos: bytes) -> list[dict]:
    """Figuras exportadas desde Colab con la celda de DocsLab (o cualquier zip de imágenes)."""
    meta = alm.meta(pid)
    c = _buscar(meta, nb_id)
    proyecto = alm.dir_proyecto(pid)
    destino_base = proyecto / "recursos" / "cuadernos" / c["id"]
    salida = []
    try:
        z = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile:
        raise ErrorAlmacen("El archivo no es un zip válido")
    nombres = [i for i in z.infolist() if not i.is_dir() and "__MACOSX" not in i.filename]
    pdfs = {Path(i.filename).with_suffix("").as_posix() for i in nombres if i.filename.lower().endswith(".pdf")}
    for info in nombres:
        ext = Path(info.filename).suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".pdf"):
            continue
        if c.get("preferir_pdf", True) and ext != ".pdf" and Path(info.filename).with_suffix("").as_posix() in pdfs:
            continue
        rel = limpiar_ruta(info.filename)
        destino = unir(destino_base, rel)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(z.read(info))
        salida.append({"ruta": destino.relative_to(proyecto).as_posix(), "origen": info.filename,
                       "tamano": info.file_size})
    meta = alm.meta(pid)
    c2 = _buscar(meta, nb_id)
    c2["ultima_ejecucion"] = {"ok": True, "error": None, "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
                              "importado": True, "n_figuras": len(salida)}
    alm.guardar_meta(pid, meta)
    return salida


def figuras(alm: Almacen, pid: str, nb_id: str) -> list[dict]:
    proyecto = alm.dir_proyecto(pid)
    base = proyecto / "recursos" / "cuadernos" / nb_id
    if not base.exists():
        return []
    return [{"ruta": p.relative_to(proyecto).as_posix(), "nombre": p.name, "tamano": p.stat().st_size,
             "fecha": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(p.stat().st_mtime))}
            for p in sorted(base.rglob("*")) if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".pdf")]


def explorar(ruta: str, raices: list[Path]) -> dict:
    """Lista carpetas y cuadernos de una ruta del servidor (solo dentro de las raíces)."""
    if not raices:
        raise ErrorAlmacen("Explorar el servidor está desactivado (inicia con --raices)")
    if not ruta:
        return {"ruta": "", "padre": None,
                "entradas": [{"nombre": str(r), "ruta": str(r), "carpeta": True} for r in raices if r.exists()]}
    p = Path(ruta).expanduser().resolve()
    if not any(r == p or r in p.parents for r in raices):
        raise ErrorAlmacen("Esa carpeta no está permitida")
    if not p.is_dir():
        raise ErrorAlmacen("No es una carpeta")
    entradas = []
    try:
        for hijo in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if hijo.name.startswith("."):
                continue
            if hijo.is_dir() or hijo.suffix.lower() == ".ipynb":
                entradas.append({"nombre": hijo.name, "ruta": str(hijo), "carpeta": hijo.is_dir()})
            if len(entradas) > 500:
                break
    except PermissionError:
        pass
    padre = str(p.parent) if any(r == p.parent or r in p.parent.parents for r in raices) and p not in raices else ""
    return {"ruta": str(p), "padre": padre, "entradas": entradas}
