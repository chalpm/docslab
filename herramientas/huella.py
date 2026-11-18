"""Huella digital de una versión de DocsLab.

Genera un manifiesto JSON reproducible con lo que define una versión:
números de versión, contrato público (API, variantes, estilos, esquema),
dependencias, pruebas, tamaño del código y el SHA-256 de cada archivo.
Comparando dos huellas se ve qué cambió y qué salto de SemVer corresponde.

Uso (desde la raíz del proyecto):
    python herramientas/huella.py generar                 # escribe huella/v<version>.json
    python herramientas/huella.py generar --salida x.json
    python herramientas/huella.py verificar huella/v1.0.0.json
    python herramientas/huella.py comparar huella/v1.0.0.json huella/v1.1.0.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FORMATO_HUELLA = 1
EXCLUIR_DIRS = {".git", "datos", ".venv", "venv", "__pycache__", ".pytest_cache", "dist",
                ".ipynb_checkpoints", "huella"}
EXCLUIR_EXT = {".pyc"}
RE_RUTA = re.compile(r'@app\.(get|post|put|patch|delete|route)\("([^"]+)"')


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 16), b""):
            h.update(bloque)
    return h.hexdigest()


def _archivos(raiz: Path) -> dict:
    res = {}
    for p in sorted(raiz.rglob("*")):
        rel = p.relative_to(raiz)
        if not p.is_file() or any(parte in EXCLUIR_DIRS for parte in rel.parts) or p.suffix in EXCLUIR_EXT:
            continue
        res[rel.as_posix()] = {"sha256": _sha(p), "bytes": p.stat().st_size}
    return res


def _lineas(p: Path) -> int:
    return sum(1 for _ in p.open(encoding="utf-8", errors="replace"))


def _requisitos(raiz: Path) -> list[str]:
    out = []
    for linea in (raiz / "requirements.txt").read_text(encoding="utf-8").splitlines():
        linea = linea.split("#", 1)[0].strip()
        if linea:
            out.append(linea)
    return sorted(out)


def _version_sty(raiz: Path) -> str | None:
    m = re.search(r"\\ProvidesPackage\{postercientifico\}\[\S+ v([\d.]+)", (raiz / "latex/postercientifico.sty").read_text(encoding="utf-8"))
    return m.group(1) if m else None


def generar(raiz: Path = RAIZ) -> dict:
    sys.path.insert(0, str(raiz))
    import docslab
    from docslab import bibliografia as B, modelo as M, variantes as V

    rutas = sorted({f"{m.upper()} {r}" for m, r in RE_RUTA.findall((raiz / "docslab/app.py").read_text(encoding="utf-8"))})
    plantillas = {}
    for d in sorted((raiz / "plantillas").iterdir()):
        meta = d / "plantilla.json"
        if meta.exists():
            j = json.loads(meta.read_text(encoding="utf-8"))
            plantillas[d.name] = {"tipo": j.get("tipo"), "clase": j.get("clase", "poster")}
    pruebas = {}
    for t in sorted((raiz / "tests").glob("test_*.py")):
        pruebas[t.name] = len(re.findall(r"^def test_", t.read_text(encoding="utf-8"), re.M))
    codigo = {p.relative_to(raiz).as_posix(): _lineas(p)
              for patron in ("docslab/*.py", "static/js/*.js", "static/css/*.css", "latex/*.sty", "servidor.py")
              for p in sorted(raiz.glob(patron))}
    archivos = _archivos(raiz)
    global_ = hashlib.sha256("".join(f"{k}:{v['sha256']}\n" for k, v in archivos.items()).encode()).hexdigest()

    return {
        "formato_huella": FORMATO_HUELLA,
        "producto": "DocsLab",
        "versiones": {
            "aplicacion": docslab.__version__,
            "postercientifico_sty": _version_sty(raiz),
            "esquema_modelo": M.ESQUEMA,
        },
        "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "contrato": {
            "api": rutas,
            "variantes": sorted(V.POR_CLAVE),
            "estilos_caja": list(V.ESTILOS_CAJA),
            "estilos_bibliograficos": sorted(B.ESTILOS),
            "clases_documento": sorted(M.CLASES),
            "tamanos": sorted(M.TAMANOS),
            "temas": sorted(M.TEMAS),
            "idiomas": sorted(M.IDIOMAS),
            "familias_tipograficas": sorted(M.FAMILIAS),
            "plantillas_incluidas": plantillas,
        },
        "dependencias": _requisitos(raiz),
        "pruebas": {"funciones_por_archivo": pruebas, "total_funciones": sum(pruebas.values()), "nota": "funciones def test_; pytest las expande con parametrize"},
        "codigo": {"lineas_por_archivo": codigo, "total_lineas": sum(codigo.values())},
        "archivos": {"total": len(archivos), "sha256_global": global_, "detalle": archivos},
    }


def _dif_lista(a, b):
    a, b = set(a), set(b)
    return sorted(b - a), sorted(a - b)


def comparar(a: dict, b: dict) -> tuple[str, list[str]]:
    """Devuelve (salto SemVer sugerido, líneas del informe en Markdown)."""
    rompe, agrega, lineas = False, False, []
    va, vb = a["versiones"], b["versiones"]
    lineas.append(f"# Diferencias de huella: {va['aplicacion']} → {vb['aplicacion']}\n")
    for k in va:
        if va[k] != vb.get(k):
            lineas.append(f"- Versión `{k}`: {va[k]} → {vb.get(k)}")
    if va["esquema_modelo"] != vb["esquema_modelo"]:
        rompe = True
    for k in a["contrato"]:
        x, y = a["contrato"][k], b["contrato"].get(k, [])
        nuevos, quitados = _dif_lista(x, y)
        if nuevos or quitados:
            lineas.append(f"\n## Contrato · {k}")
            lineas += [f"- ➕ `{n}`" for n in nuevos] + [f"- ➖ `{q}`" for q in quitados]
            agrega |= bool(nuevos)
            rompe |= bool(quitados)
    nuevos, quitados = _dif_lista(a["dependencias"], b["dependencias"])
    if nuevos or quitados:
        lineas.append("\n## Dependencias")
        lineas += [f"- ➕ `{n}`" for n in nuevos] + [f"- ➖ `{q}`" for q in quitados]
    fa, fb = a["archivos"]["detalle"], b["archivos"]["detalle"]
    nuevos, quitados = _dif_lista(fa, fb)
    cambiados = sorted(k for k in set(fa) & set(fb) if fa[k]["sha256"] != fb[k]["sha256"])
    lineas.append(f"\n## Archivos\n- Nuevos: {len(nuevos)} · Eliminados: {len(quitados)} · Modificados: {len(cambiados)}")
    for titulo, lista in (("Nuevos", nuevos), ("Eliminados", quitados), ("Modificados", cambiados)):
        if lista:
            lineas.append(f"\n### {titulo}")
            lineas += [f"- `{p}`" for p in lista]
    lineas.append(f"\n## Pruebas\n- {a['pruebas']['total_funciones']} → {b['pruebas']['total_funciones']} funciones")
    salto = "MAJOR" if rompe else "MINOR" if agrega else "PATCH" if (nuevos or quitados or cambiados) else "NINGUNO"
    lineas.insert(1, f"**Salto SemVer sugerido:** {salto} (orientativo: los cambios de comportamiento no se detectan solos)\n")
    return salto, lineas


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    g = sub.add_parser("generar")
    g.add_argument("--salida")
    v = sub.add_parser("verificar")
    v.add_argument("huella")
    c = sub.add_parser("comparar")
    c.add_argument("anterior")
    c.add_argument("nueva")
    a = ap.parse_args(argv)

    if a.orden == "generar":
        h = generar()
        salida = Path(a.salida) if a.salida else RAIZ / "huella" / f"v{h['versiones']['aplicacion']}.json"
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(json.dumps(h, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")
        print(f"{salida}  ·  {h['archivos']['total']} archivos  ·  sha256_global {h['archivos']['sha256_global']}")
    elif a.orden == "verificar":
        guardada = json.loads(Path(a.huella).read_text(encoding="utf-8"))
        actual = generar()
        if guardada["archivos"]["sha256_global"] == actual["archivos"]["sha256_global"]:
            print("OK: el árbol coincide con la huella.")
            return 0
        _, lineas = comparar(guardada, actual)
        print("\n".join(lineas))
        return 1
    else:
        _, lineas = comparar(*(json.loads(Path(p).read_text(encoding="utf-8")) for p in (a.anterior, a.nueva)))
        print("\n".join(lineas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
