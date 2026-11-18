"""Tipografías propias de un póster (.ttf y .otf).

Se guardan en la carpeta fuentes/ del proyecto (así viajan con el zip para Overleaf y
con las plantillas) y se agrupan por familia leyendo las tablas «name», «OS/2» y «head»
del propio archivo: no hace falta ninguna biblioteca. Un póster que las usa se compila
con LuaLaTeX (ver modelo.motor).
"""
from __future__ import annotations

import re
import struct
import unicodedata
from pathlib import Path

CARPETA = "fuentes"
EXTENSIONES = (".ttf", ".otf")
MAX_BYTES = 40 * 1024 * 1024
PREFIJO = "propia-"


class ErrorFuente(ValueError):
    pass


def leer(datos: bytes) -> dict:
    """Familia, estilo, peso, cursiva y si la licencia deja incrustarla en un PDF."""
    if len(datos) < 12:
        raise ErrorFuente("El archivo está vacío o cortado")
    etiqueta = datos[:4]
    if etiqueta == b"ttcf":
        raise ErrorFuente("Las colecciones .ttc no se admiten: sube los .ttf u .otf sueltos")
    if etiqueta in (b"wOFF", b"wOF2"):
        raise ErrorFuente("Las tipografías web (.woff) no se admiten: sube el .ttf o el .otf")
    if etiqueta not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
        raise ErrorFuente("No es una tipografía TrueType u OpenType")
    try:
        n = struct.unpack(">H", datos[4:6])[0]
        tablas = {}
        for i in range(n):
            t, _, o, ln = struct.unpack(">4sIII", datos[12 + 16 * i: 28 + 16 * i])
            tablas[t] = (o, ln)
        nombres: dict[int, str] = {}
        if b"name" in tablas:
            o, _ = tablas[b"name"]
            _, cuenta, almacen = struct.unpack(">HHH", datos[o:o + 6])
            for i in range(cuenta):
                pid, eid, lid, nid, ln, off = struct.unpack(">HHHHHH", datos[o + 6 + 12 * i: o + 18 + 12 * i])
                if nid not in (1, 2, 4, 16, 17):
                    continue
                crudo = datos[o + almacen + off: o + almacen + off + ln]
                if pid == 3 and eid in (0, 1, 10):              # Windows, UTF-16
                    try:
                        texto = crudo.decode("utf-16-be")
                    except UnicodeDecodeError:
                        continue
                    if lid == 0x409 or nid not in nombres:      # mejor en inglés (EE. UU.)
                        nombres[nid] = texto
                elif pid == 1 and eid == 0 and nid not in nombres:
                    nombres[nid] = crudo.decode("mac_roman", "replace")
        peso, cursiva, fs_type = 400, False, 0
        if b"OS/2" in tablas:
            o, ln = tablas[b"OS/2"]
            peso = struct.unpack(">H", datos[o + 4:o + 6])[0]
            fs_type = struct.unpack(">H", datos[o + 8:o + 10])[0]
            if ln >= 64:
                cursiva = bool(struct.unpack(">H", datos[o + 62:o + 64])[0] & 1)
        if b"head" in tablas:
            o, _ = tablas[b"head"]
            mac = struct.unpack(">H", datos[o + 44:o + 46])[0]
            cursiva = cursiva or bool(mac & 2)
            if mac & 1 and peso < 600:
                peso = 700
    except struct.error:
        raise ErrorFuente("El archivo de la tipografía está dañado") from None
    familia = (nombres.get(16) or nombres.get(1) or "").strip()
    estilo = (nombres.get(17) or nombres.get(2) or "").strip()
    if not familia:
        raise ErrorFuente("La tipografía no dice cómo se llama su familia")
    return {"familia": familia, "estilo": estilo or "Regular", "peso": int(peso or 400), "cursiva": cursiva,
            # fsType 2 = «Restricted License embedding»: no se puede meter en un PDF
            "incrustable": (fs_type & 0x000F) != 0x0002}


def _ascii(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return t


def id_familia(familia: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _ascii(familia).lower()).strip("-") or "familia"
    return PREFIJO + slug[:40]


def nombre_archivo(original: str) -> str:
    """Un nombre seguro para LaTeX (letras, números, punto, guion y guion bajo)."""
    p = Path(_ascii(original).replace(" ", "-"))
    base = re.sub(r"[^A-Za-z0-9._-]+", "", p.stem).strip("._-") or "fuente"
    return base[:60] + p.suffix.lower()


def guardar(directorio: Path, original: str, datos: bytes) -> str:
    """Guarda una tipografía en fuentes/ y devuelve su ruta (fuentes/xxx.ttf)."""
    if Path(original).suffix.lower() not in EXTENSIONES:
        raise ErrorFuente("Solo se admiten tipografías .ttf y .otf")
    if len(datos) > MAX_BYTES:
        raise ErrorFuente("La tipografía es demasiado grande (más de 40 MB)")
    leer(datos)                                  # que sea una tipografía de verdad
    carpeta = Path(directorio) / CARPETA
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = nombre_archivo(original)
    destino = carpeta / nombre
    n = 2
    while destino.exists() and destino.read_bytes() != datos:
        destino = carpeta / f"{Path(nombre).stem}-{n}{Path(nombre).suffix}"
        n += 1
    destino.write_bytes(datos)
    return f"{CARPETA}/{destino.name}"


def _cercano(lista: list[dict], peso: int) -> dict | None:
    return min(lista, key=lambda f: (abs(f["peso"] - peso), f["peso"])) if lista else None


def familias(directorio: Path) -> list[dict]:
    """Las familias que hay en fuentes/, con el archivo de cada variante."""
    carpeta = Path(directorio) / CARPETA
    grupos: dict[str, list[dict]] = {}
    if carpeta.is_dir():
        for p in sorted(carpeta.iterdir()):
            if not p.is_file() or p.suffix.lower() not in EXTENSIONES:
                continue
            try:
                d = leer(p.read_bytes())
            except (ErrorFuente, OSError):
                continue
            d["ruta"] = f"{CARPETA}/{p.name}"
            grupos.setdefault(d["familia"], []).append(d)
    salida = []
    for familia, archivos in sorted(grupos.items(), key=lambda kv: kv[0].lower()):
        rectas = [f for f in archivos if not f["cursiva"]]
        cursivas = [f for f in archivos if f["cursiva"]]
        normal = _cercano([f for f in rectas if f["peso"] < 600], 400) or _cercano(rectas, 400) or _cercano(archivos, 400)
        negrita = _cercano([f for f in rectas if f["peso"] >= 600], 700)
        cursiva = _cercano([f for f in cursivas if f["peso"] < 600], 400)
        negrita_cursiva = _cercano([f for f in cursivas if f["peso"] >= 600], 700)
        if negrita is normal:
            negrita = None
        salida.append({
            "id": id_familia(familia), "nombre": familia,
            "archivos": {"normal": normal["ruta"], "negrita": negrita["ruta"] if negrita else "",
                         "cursiva": cursiva["ruta"] if cursiva else "",
                         "negrita_cursiva": negrita_cursiva["ruta"] if negrita_cursiva else ""},
            "estilos": sorted(f"{f['estilo']}" for f in archivos),
            "incrustable": all(f["incrustable"] for f in archivos),
        })
    return salida


def borrar_familia(directorio: Path, fid: str) -> int:
    """Borra los archivos de una familia. Devuelve cuántos borró."""
    carpeta = Path(directorio) / CARPETA
    n = 0
    if carpeta.is_dir():
        for p in list(carpeta.iterdir()):
            if p.is_file() and p.suffix.lower() in EXTENSIONES:
                try:
                    if id_familia(leer(p.read_bytes())["familia"]) == fid:
                        p.unlink()
                        n += 1
                except (ErrorFuente, OSError):
                    continue
    return n
