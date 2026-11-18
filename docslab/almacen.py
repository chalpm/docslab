"""Proyectos, plantillas y recursos en disco."""
from __future__ import annotations

import io
import json
import os
import re
import secrets
import shutil
import time
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

from . import generador, modelo as M

RAIZ_APP = Path(__file__).resolve().parent.parent
PLANTILLAS_INCLUIDAS = RAIZ_APP / "plantillas"
STY = RAIZ_APP / "latex" / "postercientifico.sty"

EXT_IMAGEN = {".png", ".jpg", ".jpeg", ".pdf"}
EXT_CONVERTIBLE = {".gif", ".bmp", ".tif", ".tiff", ".webp"}
EXT_TEXTO = {".tex", ".sty", ".cls", ".bib", ".bst", ".txt", ".md", ".csv", ".json", ".cfg", ".def", ".py"}
IGNORAR = {"build", "historial", "__pycache__", ".ipynb_checkpoints", ".git"}


def _clase_de(directorio: Path) -> str:
    """Clase de documento (póster, presentación…) de un proyecto o plantilla estructurados."""
    clase = (_leer_json(directorio / "modelo.json", {}) or {}).get("clase")
    return clase if clase in M.CLASES else "poster"


class ErrorAlmacen(Exception):
    pass


def ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def limpiar_nombre(nombre: str, defecto: str = "archivo") -> str:
    """Nombre de archivo seguro para LaTeX: sin acentos, espacios ni símbolos."""
    nombre = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode()
    nombre = re.sub(r"[^A-Za-z0-9._-]+", "_", nombre).strip("._-")
    return (nombre or defecto)[:120]


def limpiar_ruta(ruta: str) -> str:
    """Ruta relativa segura (cada parte limpia, sin «..»)."""
    partes = [p for p in str(ruta).replace("\\", "/").split("/") if p not in ("", ".", "..")]
    return "/".join(limpiar_nombre(p) for p in partes)


def unir(base: Path, rel: str) -> Path:
    """Une una ruta relativa sin salir de «base»."""
    base = base.resolve()
    destino = (base / str(rel).replace("\\", "/").lstrip("/")).resolve()
    if destino != base and base not in destino.parents:
        raise ErrorAlmacen("Ruta no permitida")
    return destino


def _leer_json(p: Path, defecto=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def _escribir_json(p: Path, datos):
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def _copiar_arbol(origen: Path, destino: Path, ignorar=IGNORAR, excluir_archivos=()):
    destino.mkdir(parents=True, exist_ok=True)
    for item in origen.iterdir():
        if item.name in ignorar or item.name in excluir_archivos:
            continue
        if item.is_dir():
            _copiar_arbol(item, destino / item.name, ignorar)
        else:
            shutil.copy2(item, destino / item.name)


class Almacen:
    def __init__(self, datos: Path):
        self.datos = Path(datos).resolve()
        self.dir_proyectos = self.datos / "proyectos"
        self.dir_plantillas = self.datos / "plantillas"
        self.dir_proyectos.mkdir(parents=True, exist_ok=True)
        self.dir_plantillas.mkdir(parents=True, exist_ok=True)

    # ================================================================== proyectos
    def dir_proyecto(self, pid: str) -> Path:
        if not re.fullmatch(r"p-[a-z0-9]{6,12}", pid or ""):
            raise ErrorAlmacen("Proyecto no válido")
        d = self.dir_proyectos / pid
        if not d.is_dir():
            raise ErrorAlmacen("El proyecto no existe")
        return d

    def meta(self, pid: str) -> dict:
        d = self.dir_proyecto(pid)
        m = _leer_json(d / "proyecto.json")
        if not m:
            raise ErrorAlmacen("proyecto.json dañado")
        m.setdefault("ajustes", {})
        m["ajustes"].setdefault("auto_compilar", True)
        m.setdefault("cuadernos", [])
        m.setdefault("principal", "poster.tex")
        return m

    def guardar_meta(self, pid: str, meta: dict):
        meta["modificado"] = ahora()
        _escribir_json(self.dir_proyecto(pid) / "proyecto.json", meta)

    def miniatura(self, pid: str) -> Path | None:
        """La miniatura del último PDF correcto; se hace aquí si aún no está o es vieja."""
        from . import compilador
        d = self.dir_proyecto(pid)
        mini = d / "build" / "miniatura.png"
        ok_pdf = d / "build" / (Path(self.meta(pid).get("principal", "poster.tex")).stem + ".ok.pdf")
        if ok_pdf.exists() and (not mini.exists() or mini.stat().st_mtime < ok_pdf.stat().st_mtime):
            compilador.miniatura(ok_pdf, mini)
        return mini if mini.exists() else None

    def listar_proyectos(self) -> list[dict]:
        salida = []
        for d in self.dir_proyectos.iterdir():
            if not d.is_dir():
                continue
            m = _leer_json(d / "proyecto.json")
            if not m:
                continue
            m["tiene_pdf"] = (d / "build" / (Path(m.get("principal", "poster.tex")).stem + ".pdf")).exists()
            ok_pdf = d / "build" / (Path(m.get("principal", "poster.tex")).stem + ".ok.pdf")
            m["tiene_miniatura"] = (d / "build" / "miniatura.png").exists() or ok_pdf.exists()
            m["plantilla_propia"] = self.plantilla_propia(m)
            if not m.get("clase"):
                m["clase"] = _clase_de(d) if m.get("tipo", "estructurado") == "estructurado" else "latex"
            salida.append({k: m.get(k) for k in ("id", "nombre", "tipo", "clase", "creado", "modificado", "plantilla",
                                                  "plantilla_propia", "tiene_pdf", "tiene_miniatura")})
        return sorted(salida, key=lambda m: m.get("modificado") or "", reverse=True)

    def _nuevo_pid(self) -> str:
        while True:
            pid = "p-" + secrets.token_hex(4)
            if not (self.dir_proyectos / pid).exists():
                return pid

    def crear_proyecto(self, nombre: str, plantilla: str | None = None, asistente: dict | None = None) -> dict:
        pid = self._nuevo_pid()
        d = self.dir_proyectos / pid
        d.mkdir(parents=True)
        (d / "recursos").mkdir()
        meta = {"id": pid, "nombre": nombre.strip() or "Documento sin título", "tipo": "estructurado",
                "creado": ahora(), "modificado": ahora(), "plantilla": plantilla or "asistente",
                "principal": "poster.tex", "ajustes": {"auto_compilar": True}, "cuadernos": []}
        try:
            if plantilla:
                pd = self.dir_plantilla(plantilla)
                pm = _leer_json(pd / "plantilla.json", {})
                _copiar_arbol(pd, d, excluir_archivos=("plantilla.json", "miniatura.png"))
                meta["tipo"] = pm.get("tipo", "estructurado")
                meta["principal"] = pm.get("principal", "poster.tex")
                meta["cuadernos"] = pm.get("cuadernos", [])
                if meta["tipo"] == "estructurado":
                    mod = M.normalizar(_leer_json(d / "modelo.json", {}))
                    _escribir_json(d / "modelo.json", mod)
                    meta["clase"] = mod["clase"]
                elif not (d / "postercientifico.sty").exists() and STY.exists():
                    shutil.copyfile(STY, d / "postercientifico.sty")
            else:
                mod = M.desde_asistente(asistente or {})
                _escribir_json(d / "modelo.json", mod)
                meta["clase"] = mod["clase"]
            _escribir_json(d / "proyecto.json", meta)
        except Exception:
            shutil.rmtree(d, ignore_errors=True)
            raise
        return meta

    def leer_modelo(self, pid: str) -> dict:
        d = self.dir_proyecto(pid)
        return M.normalizar(_leer_json(d / "modelo.json", {}))

    def guardar_modelo(self, pid: str, modelo: dict) -> dict:
        d = self.dir_proyecto(pid)
        modelo = M.normalizar(modelo)
        actual = d / "modelo.json"
        hist = d / "historial"
        if actual.exists():
            hist.mkdir(exist_ok=True)
            copias = sorted(hist.glob("modelo-*.json"))
            if not copias or time.time() - copias[-1].stat().st_mtime > 120:
                shutil.copy2(actual, hist / f"modelo-{datetime.now():%Y%m%d-%H%M%S}.json")
                for viejo in copias[:-29]:
                    viejo.unlink(missing_ok=True)
        _escribir_json(actual, modelo)
        meta = self.meta(pid)
        meta["clase"] = modelo["clase"]
        self.guardar_meta(pid, meta)
        return modelo

    def historial(self, pid: str) -> list[dict]:
        hist = self.dir_proyecto(pid) / "historial"
        if not hist.exists():
            return []
        return [{"nombre": p.name, "fecha": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")}
                for p in sorted(hist.glob("modelo-*.json"), reverse=True)]

    def restaurar(self, pid: str, nombre: str) -> dict:
        p = unir(self.dir_proyecto(pid) / "historial", nombre)
        mod = _leer_json(p)
        if mod is None:
            raise ErrorAlmacen("Versión no encontrada")
        return self.guardar_modelo(pid, mod)

    def borrar_proyecto(self, pid: str):
        shutil.rmtree(self.dir_proyecto(pid))

    def duplicar_proyecto(self, pid: str, nombre: str | None = None) -> dict:
        origen = self.dir_proyecto(pid)
        meta = self.meta(pid)
        nuevo = self._nuevo_pid()
        d = self.dir_proyectos / nuevo
        _copiar_arbol(origen, d, ignorar=IGNORAR)
        meta.update({"id": nuevo, "nombre": nombre or (meta["nombre"] + " (copia)"),
                     "creado": ahora(), "modificado": ahora()})
        for c in meta.get("cuadernos", []):
            c.pop("ultima_ejecucion", None)
        _escribir_json(d / "proyecto.json", meta)
        return meta

    def escribir_tex(self, pid: str, marcas: bool = True) -> tuple[Path, dict]:
        """Escribe poster.tex desde el modelo (proyectos estructurados)."""
        d = self.dir_proyecto(pid)
        tex, mapa = generador.generar(self.leer_modelo(pid), marcas=marcas)
        (d / "poster.tex").write_text(tex, encoding="utf-8")
        return d / "poster.tex", mapa

    # ================================================================== archivos (modo LaTeX)
    def listar_archivos(self, pid: str) -> list[dict]:
        d = self.dir_proyecto(pid)
        salida = []
        for raiz, dirs, archivos in os.walk(d):
            dirs[:] = sorted(x for x in dirs if x not in IGNORAR and x != "cuadernos")
            for a in sorted(archivos):
                p = Path(raiz) / a
                rel = p.relative_to(d).as_posix()
                if rel in ("proyecto.json", "modelo.json"):
                    continue
                salida.append({"ruta": rel, "tamano": p.stat().st_size,
                               "texto": p.suffix.lower() in EXT_TEXTO,
                               "imagen": p.suffix.lower() in EXT_IMAGEN})
        return salida

    def leer_archivo(self, pid: str, ruta: str) -> str:
        p = unir(self.dir_proyecto(pid), ruta)
        if p.suffix.lower() not in EXT_TEXTO:
            raise ErrorAlmacen("Solo se pueden editar archivos de texto")
        return p.read_text(encoding="utf-8", errors="replace")

    def escribir_archivo(self, pid: str, ruta: str, contenido: str):
        ruta = limpiar_ruta(ruta)
        p = unir(self.dir_proyecto(pid), ruta)
        if p.suffix.lower() not in EXT_TEXTO:
            raise ErrorAlmacen("Solo se pueden editar archivos de texto")
        if p.name in ("proyecto.json", "modelo.json"):
            raise ErrorAlmacen("Archivo reservado")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenido, encoding="utf-8")
        self.guardar_meta(pid, self.meta(pid))

    def borrar_archivo(self, pid: str, ruta: str):
        p = unir(self.dir_proyecto(pid), ruta)
        if p.name in ("proyecto.json", "modelo.json") or p.is_dir():
            raise ErrorAlmacen("No se puede borrar")
        p.unlink(missing_ok=True)

    def convertir_a_latex(self, pid: str) -> dict:
        """Pasa un proyecto estructurado a modo LaTeX (se edita el código directamente)."""
        meta = self.meta(pid)
        if meta["tipo"] != "estructurado":
            return meta
        d = self.dir_proyecto(pid)
        self.escribir_tex(pid, marcas=False)
        if STY.exists():
            shutil.copyfile(STY, d / "postercientifico.sty")
        (d / "historial").mkdir(exist_ok=True)
        shutil.copy2(d / "modelo.json", d / "historial" / "modelo-antes-de-latex.json")
        meta["tipo"] = "latex"
        meta["principal"] = "poster.tex"
        self.guardar_meta(pid, meta)
        return meta

    # ================================================================== recursos (imágenes)
    def listar_recursos(self, pid: str) -> list[dict]:
        d = self.dir_proyecto(pid)
        base = d / "recursos"
        if not base.exists():
            return []
        usados = set()
        meta = self.meta(pid)
        if meta["tipo"] == "estructurado":
            usados = M.recursos_usados(self.leer_modelo(pid))
        salida = []
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.suffix.lower() in EXT_IMAGEN:
                rel = p.relative_to(d).as_posix()
                origen = "cuaderno" if rel.startswith("recursos/cuadernos/") else "subido"
                salida.append({"ruta": rel, "nombre": p.name, "tamano": p.stat().st_size,
                               "tipo": p.suffix.lower().lstrip("."), "origen": origen,
                               "usado": rel in usados,
                               "fecha": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")})
        return salida

    def guardar_recurso(self, pid: str, nombre: str, datos: bytes, carpeta: str = "recursos") -> str:
        d = self.dir_proyecto(pid)
        nombre = limpiar_nombre(nombre)
        ext = Path(nombre).suffix.lower()
        if ext in EXT_CONVERTIBLE:
            datos, nombre = _a_png(datos, nombre)
            ext = ".png"
        elif ext == ".svg":
            datos, nombre = _svg_a_pdf(datos, nombre)
            ext = ".pdf"
        if ext not in EXT_IMAGEN:
            raise ErrorAlmacen(f"Formato no admitido ({ext or 'sin extensión'}). Usa PNG, JPG o PDF.")
        destino_dir = unir(d, limpiar_ruta(carpeta) or "recursos")
        if destino_dir.relative_to(d).parts[:1] != ("recursos",):
            destino_dir = d / "recursos"
        destino_dir.mkdir(parents=True, exist_ok=True)
        destino = destino_dir / nombre
        n = 2
        while destino.exists() and destino.read_bytes() != datos:
            destino = destino_dir / f"{Path(nombre).stem}-{n}{ext}"
            n += 1
        destino.write_bytes(datos)
        return destino.relative_to(d).as_posix()

    def borrar_recurso(self, pid: str, ruta: str):
        d = self.dir_proyecto(pid)
        p = unir(d, ruta)
        if not p.relative_to(d).as_posix().startswith("recursos/"):
            raise ErrorAlmacen("Solo se pueden borrar recursos")
        p.unlink(missing_ok=True)

    # ================================================================== plantillas
    def dir_plantilla(self, tid: str) -> Path:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,60}", tid or ""):
            raise ErrorAlmacen("Plantilla no válida")
        for base in (self.dir_plantillas, PLANTILLAS_INCLUIDAS):
            d = base / tid
            if (d / "plantilla.json").exists():
                return d
        raise ErrorAlmacen("La plantilla no existe")

    def listar_plantillas(self) -> list[dict]:
        salida = []
        for base, incluida in ((PLANTILLAS_INCLUIDAS, True), (self.dir_plantillas, False)):
            if not base.exists():
                continue
            for d in sorted(base.iterdir()):
                if d.name.startswith("."):
                    continue
                pm = _leer_json(d / "plantilla.json")
                if not pm:
                    continue
                pm["id"] = d.name
                pm["incluida"] = incluida
                pm["tiene_miniatura"] = (d / "miniatura.png").exists()
                if not pm.get("clase"):
                    pm["clase"] = _clase_de(d) if pm.get("tipo", "estructurado") == "estructurado" else "latex"
                salida.append(pm)
        return sorted(salida, key=lambda p: (not p["incluida"], p.get("orden", 99), p.get("nombre", "")))

    def crear_plantilla(self, pid: str, nombre: str, descripcion: str = "") -> dict:
        self.dir_proyecto(pid)
        base = limpiar_nombre(nombre, "plantilla").lower().replace("_", "-").replace(".", "-")[:40].strip("-")
        tid = base or "plantilla"
        n = 2
        while (self.dir_plantillas / tid).exists() or (PLANTILLAS_INCLUIDAS / tid).exists():
            tid = f"{base}-{n}"
            n += 1
        d = self.dir_plantillas / tid
        pm = {"nombre": nombre.strip() or "Plantilla", "descripcion": descripcion.strip(), "creada": ahora()}
        try:
            pm = self._volcar_en_plantilla(pid, d, pm, tid)
        except Exception:
            shutil.rmtree(d, ignore_errors=True)
            raise
        self._vincular(pid, tid)
        return pm

    def _volcar_en_plantilla(self, pid: str, d: Path, pm: dict, tid: str) -> dict:
        """Copia el contenido de un proyecto en la carpeta «d» de una plantilla."""
        origen = self.dir_proyecto(pid)
        meta = self.meta(pid)
        _copiar_arbol(origen, d, ignorar=IGNORAR, excluir_archivos=("proyecto.json",))
        for ej in d.glob("cuadernos/*/ejecutado.ipynb"):
            ej.unlink(missing_ok=True)
        cuadernos = []
        for c in meta.get("cuadernos", []):
            c = dict(c)
            c.pop("ultima_ejecucion", None)
            cuadernos.append(c)
        pm.pop("id", None)
        pm.update({"tipo": meta["tipo"], "principal": meta.get("principal", "poster.tex"),
                   "cuadernos": cuadernos, "origen": meta.get("nombre")})
        _escribir_json(d / "plantilla.json", pm)
        mini = self.miniatura(pid)
        if mini:
            shutil.copyfile(mini, d / "miniatura.png")
        pm["id"] = tid
        return pm

    def _vincular(self, pid: str, tid: str):
        """Recuerda en el proyecto la plantilla propia que se guardó desde él (sin tocar su fecha)."""
        meta = self.meta(pid)
        if meta.get("plantilla_vinculada") != tid:
            meta["plantilla_vinculada"] = tid
            _escribir_json(self.dir_proyecto(pid) / "proyecto.json", meta)

    def plantilla_propia(self, meta: dict) -> dict | None:
        """La plantilla propia que un proyecto puede actualizar: la que se guardó desde él
        o, si no, la plantilla propia con la que se creó."""
        for tid in (meta.get("plantilla_vinculada"), meta.get("plantilla")):
            if not tid or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,60}", str(tid)):
                continue
            pm = _leer_json(self.dir_plantillas / tid / "plantilla.json")
            if pm:
                return {"id": tid, "nombre": pm.get("nombre") or tid}
        return None

    def reemplazar_plantilla(self, tid: str, pid: str) -> dict:
        """Cambia el contenido de una plantilla propia por el de un proyecto.
        Conserva el nombre, la descripción y la fecha de creación de la plantilla."""
        d = self.dir_plantilla(tid)
        if d.parent.resolve() != self.dir_plantillas.resolve():
            raise ErrorAlmacen("Las plantillas incluidas no se pueden modificar")
        self.dir_proyecto(pid)
        pm = _leer_json(d / "plantilla.json", {}) or {}
        pm["actualizada"] = ahora()
        # se prepara aparte y se cambia de golpe: si algo falla, la plantilla queda como estaba
        nueva = self.dir_plantillas / f".nueva-{tid}-{secrets.token_hex(3)}"
        vieja = self.dir_plantillas / f".vieja-{tid}-{secrets.token_hex(3)}"
        try:
            pm = self._volcar_en_plantilla(pid, nueva, pm, tid)
            os.replace(d, vieja)
            try:
                os.replace(nueva, d)
            except OSError:
                os.replace(vieja, d)
                raise
        finally:
            shutil.rmtree(nueva, ignore_errors=True)
        shutil.rmtree(vieja, ignore_errors=True)
        self._vincular(pid, tid)
        return pm

    def actualizar_plantilla(self, tid: str, cambios: dict) -> dict:
        d = self.dir_plantilla(tid)
        if d.parent.resolve() == PLANTILLAS_INCLUIDAS.resolve():
            raise ErrorAlmacen("Las plantillas incluidas no se pueden modificar")
        pm = _leer_json(d / "plantilla.json", {})
        for k in ("nombre", "descripcion"):
            if k in cambios:
                pm[k] = str(cambios[k]).strip()
        _escribir_json(d / "plantilla.json", pm)
        pm["id"] = tid
        return pm

    def borrar_plantilla(self, tid: str):
        d = self.dir_plantilla(tid)
        if d.parent.resolve() == PLANTILLAS_INCLUIDAS.resolve():
            raise ErrorAlmacen("Las plantillas incluidas no se pueden borrar")
        shutil.rmtree(d)

    # ================================================================== zips
    def exportar_proyecto(self, pid: str) -> bytes:
        d = self.dir_proyecto(pid)
        return _zip_dir(d, ignorar=IGNORAR | {"ejecutado.ipynb"})

    def exportar_plantilla(self, tid: str) -> bytes:
        return _zip_dir(self.dir_plantilla(tid), ignorar=IGNORAR)

    def exportar_overleaf(self, pid: str) -> bytes:
        """Zip listo para Overleaf: poster.tex, postercientifico.sty y las imágenes que se usan."""
        d = self.dir_proyecto(pid)
        meta = self.meta(pid)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            if meta["tipo"] == "estructurado":
                mod = self.leer_modelo(pid)
                tex, _ = generador.generar(mod, marcas=False)
                z.writestr("poster.tex", tex)
                z.write(STY, "postercientifico.sty")
                if M.motor(mod) == "lualatex":
                    # Overleaf compila con latexmk -pdf: así usa LuaLaTeX sin tocar el menú
                    z.writestr("latexmkrc", "# DocsLab: el póster usa tipografías propias y se compila con LuaLaTeX.\n"
                                            "# Overleaf (y latexmk -pdf) lo hacen solos con esta línea; también puedes\n"
                                            "# elegir LuaLaTeX en el menú del proyecto.\n"
                                            "$pdflatex = 'lualatex %O %S';\n")
                usadas = set(generador.familias_de(mod))
                for f in M.familias_propias(mod).values():
                    if f["id"] in usadas:
                        for rel in {v for v in f["archivos"].values() if v}:
                            try:
                                fp = unir(d, rel)
                            except ErrorAlmacen:
                                continue
                            if fp.is_file():
                                z.write(fp, rel)
                for rel in sorted(M.recursos_usados(mod)):
                    try:
                        p = unir(d, rel)
                    except ErrorAlmacen:
                        continue
                    if p.is_file():
                        z.write(p, rel)
            else:
                for raiz, dirs, archivos in os.walk(d):
                    dirs[:] = [x for x in dirs if x not in IGNORAR and x != "cuadernos"]
                    for a in archivos:
                        p = Path(raiz) / a
                        rel = p.relative_to(d).as_posix()
                        if rel in ("proyecto.json", "modelo.json"):
                            continue
                        z.write(p, rel)
                if not (d / "postercientifico.sty").exists():
                    z.write(STY, "postercientifico.sty")
                try:
                    from . import compilador
                    motor = compilador.motor_del_tex(unir(d, meta.get("principal", "poster.tex")).read_text(
                        encoding="utf-8", errors="replace"))
                except (OSError, ErrorAlmacen):
                    motor = "pdflatex"
                if motor != "pdflatex" and not (d / "latexmkrc").exists() and not (d / ".latexmkrc").exists():
                    z.writestr("latexmkrc", f"# DocsLab: el documento pide {motor} (% !TEX program).\n"
                                            f"$pdflatex = '{motor} %O %S';\n")
        return buf.getvalue()

    def importar_zip(self, datos: bytes, nombre: str = "") -> dict:
        """Importa un zip: proyecto o plantilla de DocsLab, o cualquier proyecto LaTeX (Overleaf)."""
        try:
            z = zipfile.ZipFile(io.BytesIO(datos))
        except zipfile.BadZipFile:
            raise ErrorAlmacen("El archivo no es un zip válido")
        nombres = [n for n in z.namelist() if not n.endswith("/") and "__MACOSX" not in n]
        if not nombres:
            raise ErrorAlmacen("El zip está vacío")
        tope = _carpeta_comun(nombres)
        def rel(n):
            return n[len(tope):] if tope else n
        rels = {rel(n): n for n in nombres}
        if "plantilla.json" in rels:
            pm = json.loads(z.read(rels["plantilla.json"]).decode("utf-8"))
            base = limpiar_nombre(pm.get("nombre") or nombre or "plantilla").lower().replace("_", "-")
            base = re.sub(r"[^a-z0-9-]", "-", base)[:40].strip("-") or "plantilla"
            tid, n = base, 2
            while (self.dir_plantillas / tid).exists() or (PLANTILLAS_INCLUIDAS / tid).exists():
                tid, n = f"{base}-{n}", n + 1
            destino = self.dir_plantillas / tid
            _extraer(z, rels, destino)
            pm["id"] = tid
            return {"tipo": "plantilla", "plantilla": pm}
        pid = self._nuevo_pid()
        destino = self.dir_proyectos / pid
        _extraer(z, rels, destino)
        if (destino / "proyecto.json").exists():
            meta = _leer_json(destino / "proyecto.json", {})
            meta.update({"id": pid, "creado": ahora(), "modificado": ahora()})
            meta.pop("plantilla_vinculada", None)   # era de otro equipo
            if nombre:
                meta["nombre"] = nombre
        else:
            texs = [p for p in destino.rglob("*.tex")]
            principal = None
            for preferido in ("poster.tex", "main.tex"):
                if (destino / preferido).exists():
                    principal = preferido
                    break
            if not principal:
                for p in texs:
                    if "\\documentclass" in p.read_text(encoding="utf-8", errors="replace"):
                        principal = p.relative_to(destino).as_posix()
                        break
            if not principal:
                shutil.rmtree(destino, ignore_errors=True)
                raise ErrorAlmacen("El zip no contiene ningún documento LaTeX (\\documentclass).")
            meta = {"id": pid, "nombre": nombre or Path(principal).stem, "tipo": "latex", "creado": ahora(),
                    "modificado": ahora(), "plantilla": "importado", "principal": principal,
                    "ajustes": {"auto_compilar": False}, "cuadernos": []}
            texto = (destino / principal).read_text(encoding="utf-8", errors="replace")
            if "postercientifico" in texto and not (destino / "postercientifico.sty").exists():
                shutil.copyfile(STY, destino / "postercientifico.sty")
        (destino / "recursos").mkdir(exist_ok=True)
        _escribir_json(destino / "proyecto.json", meta)
        return {"tipo": "proyecto", "proyecto": meta}


def _carpeta_comun(nombres: list[str]) -> str:
    primeras = {n.split("/", 1)[0] for n in nombres}
    if len(primeras) == 1 and all("/" in n for n in nombres):
        return primeras.pop() + "/"
    return ""


def _extraer(z: zipfile.ZipFile, rels: dict, destino: Path):
    destino.mkdir(parents=True, exist_ok=True)
    total = 0
    for rel, original in rels.items():
        partes = [p for p in rel.replace("\\", "/").split("/") if p not in ("", ".", "..")]
        if not partes or partes[0] in IGNORAR:
            continue
        p = unir(destino, "/".join(partes))
        info = z.getinfo(original)
        total += info.file_size
        if total > 2_000_000_000:
            raise ErrorAlmacen("El zip es demasiado grande")
        p.parent.mkdir(parents=True, exist_ok=True)
        with z.open(original) as fuente, open(p, "wb") as salida:
            shutil.copyfileobj(fuente, salida)


def _zip_dir(d: Path, ignorar=IGNORAR) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for raiz, dirs, archivos in os.walk(d):
            dirs[:] = [x for x in dirs if x not in ignorar]
            for a in archivos:
                if a in ignorar:
                    continue
                p = Path(raiz) / a
                z.write(p, p.relative_to(d).as_posix())
    return buf.getvalue()


def _a_png(datos: bytes, nombre: str) -> tuple[bytes, str]:
    try:
        from PIL import Image
    except ImportError:
        raise ErrorAlmacen("Para convertir esta imagen a PNG hace falta Pillow (pip install pillow).")
    im = Image.open(io.BytesIO(datos))
    if im.mode not in ("RGB", "RGBA", "L", "LA"):
        im = im.convert("RGBA")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue(), Path(nombre).stem + ".png"


def _svg_a_pdf(datos: bytes, nombre: str) -> tuple[bytes, str]:
    try:
        import cairosvg  # type: ignore
    except ImportError:
        raise ErrorAlmacen("Los SVG necesitan cairosvg (pip install cairosvg) o expórtalos como PDF.")
    return cairosvg.svg2pdf(bytestring=datos), Path(nombre).stem + ".pdf"
