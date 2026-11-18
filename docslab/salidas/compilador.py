# SPDX-License-Identifier: AGPL-3.0-only
"""Compilación con pdfLaTeX, lectura del registro y de las marcas de posición."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

RAIZ_APP = Path(__file__).resolve().parents[2]      # docslab/<área>/<módulo>.py → raíz
STY = RAIZ_APP / "latex" / "postercientifico.sty"
SP = 65536.0


def pdflatex() -> str | None:
    return os.environ.get("DOCSLAB_PDFLATEX") or shutil.which("pdflatex")


def lualatex() -> str | None:
    return os.environ.get("DOCSLAB_LUALATEX") or shutil.which("lualatex")


def xelatex() -> str | None:
    return shutil.which("xelatex")


MOTORES = {"pdflatex": pdflatex, "lualatex": lualatex, "xelatex": xelatex}


def motor_del_tex(texto: str) -> str:
    """El programa que pide un .tex con «% !TEX program = lualatex» (o xelatex) al principio."""
    mo = re.search(r"^\s*%\s*!\s*TEX\s+(?:TS-)?program\s*=\s*(pdflatex|lualatex|xelatex)\b",
                   texto[:3000], re.I | re.M)
    return mo.group(1).lower() if mo else "pdflatex"


def pdftoppm() -> str | None:
    return shutil.which("pdftoppm")


# ---------------------------------------------------------------- formato precompilado
# Cargar tikz, tcolorbox y el resto de paquetes es casi la mitad de cada pasada. Se
# guarda un «formato» de pdfLaTeX con la plantilla ya cargada (mylatexformat) y los
# pósters lo usan: el .tex lleva \csname endofdump\endcsname justo después de
# \usepackage{postercientifico} (sin el formato no hace nada).
DIR_FORMATOS: Path | None = None
_FORMATO_MUTEX = threading.Lock()
_FORMATOS_MALOS: set[str] = set()
MARCA_FORMATO = "\\csname endofdump\\endcsname"
# Antes de \documentclass en los pósters generados: graphicx (pdftex.def de 2025 en
# adelante) carga epstopdf-base, y con él grfext, aunque no haya imágenes .eps.
# DocsLab no las usa, así que se ahorra (y no hace falta tener esos paquetes).
SIN_EPSTOPDF = "\\providecommand\\DoNotLoadEpstopdf{}"
_FORMATO_TEX = (SIN_EPSTOPDF + "\n\\documentclass{article}\n\\usepackage{postercientifico}\n"
                + MARCA_FORMATO + "\n\\begin{document}\n\\end{document}\n")


def formato_poster() -> str | None:
    """Ruta (sin .fmt) del formato para la plantilla actual, creándolo si hace falta.
    None si no se puede (sin pdflatex, sin mylatexformat o si falló antes)."""
    exe = pdflatex()
    if not exe or not STY.exists() or os.environ.get("DOCSLAB_SIN_FORMATO"):
        return None
    if existe_tex("mylatexformat.ltx") is False:
        return None
    clave = hashlib.md5(STY.read_bytes() + (version_tex() or "").encode() + _FORMATO_TEX.encode()).hexdigest()[:12]
    if clave in _FORMATOS_MALOS:
        return None
    base = Path(DIR_FORMATOS or Path(tempfile.gettempdir()) / "docslab-formatos")
    nombre = base / f"pcposter-{clave}"
    if nombre.with_suffix(".fmt").exists():
        return str(nombre)
    with _FORMATO_MUTEX:
        if nombre.with_suffix(".fmt").exists():
            return str(nombre)
        try:
            base.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=base) as tmp:
                t = Path(tmp)
                shutil.copyfile(STY, t / "postercientifico.sty")
                (t / "pcformato.tex").write_text(_FORMATO_TEX, encoding="utf-8")
                r = subprocess.run([exe, "-ini", "-interaction=nonstopmode", *opciones_motor(), f"-jobname={nombre.name}",
                                    "&pdflatex", "mylatexformat.ltx", "pcformato.tex"], cwd=t, capture_output=True,
                                   timeout=tiempo_motor(120), stdin=subprocess.DEVNULL)
                fmt = t / f"{nombre.name}.fmt"
                if r.returncode != 0 or not fmt.exists():
                    _FORMATOS_MALOS.add(clave)
                    return None
                os.replace(fmt, nombre.with_suffix(".fmt"))
            return str(nombre)
        except Exception:
            _FORMATOS_MALOS.add(clave)
            return None


_FALLOS_FORMATO: dict[str, int] = {}


def olvidar_formato(formato: str):
    """Si un formato da problemas se borra. Se rehace una vez (MiKTeX, por ejemplo,
    no acepta los formatos hechos antes de su última actualización) y, si vuelve a
    fallar, se deja de usar."""
    try:
        Path(formato).with_suffix(".fmt").unlink()
    except OSError:
        pass
    clave = Path(formato).name.replace("pcposter-", "")
    _FALLOS_FORMATO[clave] = _FALLOS_FORMATO.get(clave, 0) + 1
    if _FALLOS_FORMATO[clave] >= 2:
        _FORMATOS_MALOS.add(clave)


_KPSE_CACHE: dict[str, bool] = {}


def existe_tex(archivo: str) -> bool | None:
    """¿Encuentra LaTeX este archivo (.sty, .ldf…)? None si no hay kpsewhich para saberlo."""
    if archivo in _KPSE_CACHE:
        return _KPSE_CACHE[archivo]
    exe = shutil.which("kpsewhich")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, archivo], capture_output=True, text=True, timeout=20, stdin=subprocess.DEVNULL)
        ok = bool(r.stdout.strip())
    except Exception:
        return None
    if not ok and es_miktex():
        return None                # MiKTeX lo instala al compilar: no se sabe hasta entonces
    _KPSE_CACHE[archivo] = ok
    return ok


def existen_tex(archivos: list[str]) -> dict[str, bool | None]:
    """Como existe_tex, pero de una vez (una sola llamada a kpsewhich)."""
    faltan = [a for a in archivos if a not in _KPSE_CACHE]
    exe = shutil.which("kpsewhich")
    if faltan and exe:
        try:
            r = subprocess.run([exe, *faltan], capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
            hallados = {Path(x.strip()).name for x in r.stdout.splitlines() if x.strip()}
            miktex = es_miktex()
            for a in faltan:
                if a in hallados or not miktex:          # con MiKTeX, lo que falta se instala al compilar
                    _KPSE_CACHE[a] = a in hallados
        except Exception:
            pass
    return {a: _KPSE_CACHE.get(a) for a in archivos}


_VERSION_TEX: dict[str, str] = {}


def version_tex() -> str | None:
    """Primera línea de «pdflatex --version» (se pregunta una vez por ejecutable)."""
    exe = pdflatex()
    if not exe:
        return None
    if exe in _VERSION_TEX:
        return _VERSION_TEX[exe]
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20,
                           stdin=subprocess.DEVNULL)
        v = (r.stdout or "").splitlines()[0].strip() if r.stdout else None
    except Exception:
        return None
    if v:
        _VERSION_TEX[exe] = v
    return v


def es_miktex() -> bool:
    return "miktex" in (version_tex() or "").lower()


def opciones_motor() -> list[str]:
    """Opciones para pdflatex y lualatex según la distribución. Con MiKTeX, los
    paquetes que falten se instalan solos, sin preguntar (DocsLab compila en
    segundo plano y nadie vería la pregunta)."""
    return ["--enable-installer"] if es_miktex() else []


def tiempo_motor(tiempo: int) -> int:
    """Con MiKTeX, la primera compilación puede tener que descargar paquetes."""
    return max(tiempo, 600) if es_miktex() else tiempo


def _hash(p: Path) -> str | None:
    try:
        return hashlib.md5(p.read_bytes()).hexdigest()
    except OSError:
        return None


_ERR_LINEA = re.compile(r"^(?P<archivo>[^:\s][^:]*\.(?:tex|sty|cls|cfg|def|clo|fd|aux)):(?P<linea>\d+): (?P<msg>.*)$")


def leer_registro(texto: str) -> dict:
    """Errores, avisos y número de páginas a partir del .log."""
    lineas = texto.splitlines()
    errores, avisos = [], []
    i = 0
    while i < len(lineas):
        ln = lineas[i]
        m = _ERR_LINEA.match(ln)
        if m or ln.startswith("! "):
            msg = m.group("msg") if m else ln[2:]
            # el mensaje puede seguir en las líneas siguientes hasta una línea en blanco
            contexto = []
            j = i + 1
            while j < len(lineas) and j < i + 12 and lineas[j].strip() != "":
                if lineas[j].startswith(("Here is how much", "==>", "!  ==>")):
                    break
                contexto.append(lineas[j])
                j += 1
            linea_tex = int(m.group("linea")) if m else None
            if linea_tex is None:
                for c in contexto:
                    mm = re.match(r"^l\.(\d+)", c)
                    if mm:
                        linea_tex = int(mm.group(1))
                        break
            if "Emergency stop" not in msg and "==> Fatal error" not in msg:
                errores.append({"archivo": m.group("archivo") if m else None, "linea": linea_tex,
                                "mensaje": msg.strip(), "contexto": "\n".join(contexto[:8])})
            i = j
            continue
        if "Package postercientifico Warning:" in ln:
            msg = ln.split("Warning:", 1)[1].strip()
            j = i + 1
            while j < len(lineas) and lineas[j].startswith("(postercientifico)"):
                msg += " " + lineas[j].replace("(postercientifico)", "").strip()
                j += 1
            if "Rerun" not in msg:
                avisos.append({"tipo": "plantilla", "mensaje": re.sub(r"\s+on input line \d+\.?$", "", msg)})
            i = j
            continue
        if ln.startswith("Overfull \\hbox") or ln.startswith("Overfull \\vbox"):
            avisos.append({"tipo": "desborde", "mensaje": ln.strip()})
        elif ln.startswith("LaTeX Warning: File") or "not found" in ln and ln.startswith("LaTeX Warning"):
            avisos.append({"tipo": "archivo", "mensaje": ln.replace("LaTeX Warning:", "").strip()})
        elif "Missing character" in ln:
            avisos.append({"tipo": "caracter", "mensaje": ln.strip()})
        i += 1
    paginas = None
    m = re.search(r"Output written on .*?\((\d+) pages?", texto.replace("\n", ""))
    if m:
        paginas = int(m.group(1))
    # agrupar avisos repetidos
    vistos, unicos = {}, []
    for a in avisos:
        clave = (a["tipo"], a["mensaje"])
        if clave in vistos:
            vistos[clave]["veces"] += 1
        else:
            a["veces"] = 1
            vistos[clave] = a
            unicos.append(a)
    return {"errores": errores[:20], "avisos": unicos[:60], "paginas": paginas,
            "repetir": ("Rerun to get" in texto or "Label(s) may have changed" in texto)}


_CS_FINAL = re.compile(r"(\\[A-Za-z@]+)\s*$")


def localizar_error(error: dict, lineas: list[str], mapa: dict) -> str | None:
    """Elemento del póster donde está el error.

    Las filas toman su contenido como argumento, así que TeX informa del error en
    la línea de \\end{fila}. El contexto del error sí trae el texto que lo causó:
    se busca en las líneas generadas y se devuelve el elemento que las contiene."""
    linea = error.get("linea") or 0
    # error dentro de un componente propio: su orden \PCk@<id> sale en el contexto
    m = re.search(r"PCk@([A-Za-z0-9-]+)", str(error.get("contexto") or ""))
    if m and m.group(1) in set(mapa.values()):
        return m.group(1)
    por_linea = mapa.get(linea)
    if por_linea is None:          # una línea en blanco: TeX avisa al leer la siguiente
        for k in range(linea - 1, max(0, linea - 4), -1):
            if mapa.get(k):
                por_linea = mapa[k]
                break
    contexto = [c for c in str(error.get("contexto") or "").splitlines() if c.strip()]
    if contexto and not contexto[0].startswith("l."):
        frag = re.sub(r"^<[^>]*>\s*", "", contexto[0]).lstrip(".").rstrip()
        candidatos = []
        m = _CS_FINAL.search(frag)
        if m:
            candidatos.append(m.group(1))
        cola = frag[-24:].strip()
        if len(cola) >= 6:
            candidatos.append(cola)
        for cand in candidatos:
            ids = {mapa.get(i + 1) for i, ln in enumerate(lineas) if cand in ln} - {None}
            mas_internos = [i for i in ids if i and not str(i).startswith(("f-", "c-"))]
            if len(mas_internos) == 1:
                return mas_internos[0]
            if len(ids) == 1:
                return ids.pop()
    return por_linea


def leer_posiciones(ruta: Path) -> dict:
    """Convierte el .pos de la plantilla en cajas (pt, desde la esquina superior izquierda)."""
    res = {"papel": None, "cajas": {}, "paginas": {}}
    if not ruta.exists():
        return res
    alto = None
    parciales: dict[str, dict] = {}
    for ln in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        p = ln.split()
        if not p:
            continue
        try:
            if p[0] == "papel" and len(p) >= 3:
                ancho = float(p[1].rstrip("pt"))
                alto = float(p[2].rstrip("pt"))
                res["papel"] = {"ancho": ancho, "alto": alto}
            elif len(p) == 3 and p[1] == "pag":          # diapositiva → página en la que empieza
                res["paginas"][p[0]] = int(p[2])
            elif len(p) >= 7 and p[1] == "capa":
                xmin, ytop, xmax, ybot = (float(v) for v in p[2:6])
                res["cajas"][p[0]] = {"pagina": int(p[6]), "x0": xmin, "y0": -ytop, "x1": xmax, "y1": -ybot,
                                      "capa": p[7] if len(p) > 7 else ""}
            elif len(p) >= 5 and p[1] in ("a", "b") and alto is not None:
                x = float(p[2]) / SP
                y = alto - float(p[3]) / SP
                d = parciales.setdefault(p[0], {})
                d[p[1]] = (x, y, int(p[4]), float(p[5].rstrip("pt")) if len(p) > 5 else None)
        except (ValueError, IndexError):
            continue
    for ident, d in parciales.items():
        if "a" not in d or "b" not in d:
            continue
        (xa, ya, pa, wa), (xb, yb, pb, wb) = d["a"], d["b"]
        if wa is not None:   # marca de flujo: x de la esquina, ancho de línea
            caja = {"pagina": pa, "x0": xa, "y0": ya, "x1": xa + wa, "y1": yb}
            if pb != pa or yb < ya - 0.5:
                # sigue en otra página u otra columna (documentos): se marca hasta el final de la suya
                caja["y1"] = max(ya + 14, alto - 56) if alto else ya + 14
                caja["sigue"] = True
        else:                # esquinas de un recuadro
            caja = {"pagina": pa, "x0": min(xa, xb), "y0": min(ya, yb), "x1": max(xa, xb), "y1": max(ya, yb)}
        if caja["y1"] - caja["y0"] < 0.5 and wa is not None:
            caja["y1"] = caja["y0"] + 2
        res["cajas"][ident] = caja
    return res


def aviso_diapositivas(resultado: dict, diapositivas: list):
    """Presentaciones: una diapositiva que no cabe sigue en otra página. Se avisa cuál es."""
    pags = (resultado.get("posiciones") or {}).get("paginas") or {}
    total = resultado.get("paginas") or 0
    orden = [(i, n, pags[i]) for i, n in diapositivas if i in pags]
    largas = []
    for k, (i, n, pg) in enumerate(orden):
        fin = orden[k + 1][2] if k + 1 < len(orden) else total + 1
        if fin - pg > 1:
            largas.append((i, n, k + 1))
    for i, n, num in reversed(largas):
        resultado.setdefault("avisos", []).insert(0, {
            "tipo": "paginas", "veces": 1, "elemento": i,
            "mensaje": f"La diapositiva {num}" + (f" («{n}»)" if n else "") +
                       " no cabe en una página: quita contenido o reduce las imágenes."})
    resultado["diapositivas_largas"] = [i for i, _, _ in largas]


def compilar(directorio: Path, principal: str = "poster.tex", copiar_sty: bool = True,
             max_pasadas: int = 5, tiempo: int = 240, cancelar=None, informar=None,
             avisar_paginas: bool = True, hacer_miniatura: bool = True, formato: str | None = None,
             motor: str = "pdflatex", diapositivas: list | None = None) -> dict:
    """Compila hasta que las alturas y referencias se estabilizan (máximo max_pasadas).
    «diapositivas»: [(id, nombre)] de una presentación, para avisar de las que no caben.
    Con «formato» (ver formato_poster) cada pasada es más rápida. «motor»: pdflatex,
    lualatex (tipografías propias) o xelatex."""
    motor = motor if motor in MOTORES else "pdflatex"
    if motor != "pdflatex":
        formato = None                       # el formato precompilado es de pdfLaTeX
    if formato:
        try:
            if MARCA_FORMATO not in (Path(directorio) / principal).read_text(encoding="utf-8", errors="replace")[:6000]:
                formato = None
        except OSError:
            formato = None
    exe = MOTORES[motor]()
    tiempo = tiempo_motor(tiempo)
    inicio = time.time()
    directorio = Path(directorio)
    build = directorio / "build"
    build.mkdir(exist_ok=True)
    if not exe:
        if motor == "pdflatex":
            mensaje = "No se encontró pdflatex. Instala TeX Live o MiKTeX (ver LEEME) o abre la aplicación en Colab."
        else:
            mensaje = (f"No se encontró {motor}, que hace falta para las tipografías propias. "
                       "Viene con TeX Live (paquete texlive-luatex) y con MiKTeX.")
        return {"ok": False, "errores": [{"mensaje": mensaje}],
                "avisos": [], "pasadas": 0, "segundos": 0, "paginas": None, "motor": motor}
    if copiar_sty and STY.exists():
        destino = directorio / "postercientifico.sty"
        if not destino.exists() or _hash(destino) != _hash(STY):
            shutil.copyfile(STY, destino)
    nombre = Path(principal).stem
    aux = build / (nombre + ".aux")
    env = dict(os.environ)
    env["TEXINPUTS"] = os.pathsep.join([".", str(STY.parent), ""])
    env.setdefault("max_print_line", "100000")      # el .log sin cortes de línea (mejor para leer errores)
    env.setdefault("error_line", "254")             # y con más contexto alrededor de cada error
    env.setdefault("half_error_line", "238")
    resultado = {}
    salida = ""
    pasadas = 0
    for pasada in range(1, max_pasadas + 1):
        if cancelar is not None and cancelar.is_set():
            resultado["cancelado"] = True
            break
        if informar:
            informar(f"{motor} · pasada {pasada}", pasada / (max_pasadas + 1))
        antes = _hash(aux)
        orden = [exe, "-interaction=nonstopmode", "-file-line-error", "-halt-on-error", "-no-shell-escape",
                 *opciones_motor(), f"-output-directory={build}", principal]
        if formato:
            orden.insert(1, f"-fmt={formato}")
        log = build / (nombre + ".log")

        def correr():
            log.unlink(missing_ok=True)          # sin el registro de la vez anterior si esta no llega a escribirlo
            pr = subprocess.run(orden, cwd=directorio, capture_output=True, timeout=tiempo, env=env,
                                stdin=subprocess.DEVNULL)
            sal = pr.stdout.decode("utf-8", "replace") + (pr.stderr or b"").decode("utf-8", "replace")
            return pr, sal, (log.read_text(encoding="utf-8", errors="replace") if log.exists() else sal)
        try:
            proc, salida, texto = correr()
            if formato and proc.returncode != 0 and re.search(r"format file|Fatal format|makes no sense|not a format|"
                                                              r"memory dump file", salida + texto[-3000:]):
                # un formato de otra versión de TeX (o que MiKTeX quiere rehacer): se borra y se sigue sin él
                olvidar_formato(formato)
                formato = None
                orden.remove(next(o for o in orden if o.startswith("-fmt=")))
                proc, salida, texto = correr()
        except subprocess.TimeoutExpired:
            return {"ok": False, "errores": [{"mensaje": f"{motor} tardó más de {tiempo} s y se detuvo."}],
                    "avisos": [], "pasadas": pasada, "segundos": round(time.time() - inicio, 1), "paginas": None}
        pasadas = pasada
        resultado = leer_registro(texto)
        resultado["codigo"] = proc.returncode
        if resultado["errores"] or proc.returncode != 0:
            break
        if not resultado["repetir"] and _hash(aux) == antes:
            break
    pdf = build / (nombre + ".pdf")
    if not resultado.get("errores") and resultado.get("codigo", 0) != 0:
        # se detuvo sin dejar un error de LaTeX en el registro (p. ej. el propio programa falló)
        ultimas = [x.strip() for x in salida.splitlines() if x.strip()][-3:]
        resultado["errores"] = [{"mensaje": f"{motor} se detuvo sin dejar un error en el registro"
                                 + (f": {' '.join(ultimas)[:300]}" if ultimas else ".")}]
    resultado.update({
        "ok": not resultado.get("errores") and resultado.get("codigo", 1) == 0 and pdf.exists(),
        "pasadas": pasadas, "segundos": round(time.time() - inicio, 1),
        "pdf": str(pdf.relative_to(directorio)) if pdf.exists() else None,
    })
    if avisar_paginas and resultado["ok"] and (resultado.get("paginas") or 1) > 1:
        resultado.setdefault("avisos", []).insert(0, {
            "tipo": "paginas", "veces": 1,
            "mensaje": f"El póster ocupa {resultado['paginas']} páginas: hay contenido que no cabe en el lienzo."})
    resultado["posiciones"] = leer_posiciones(build / (nombre + ".pos"))
    if diapositivas and resultado["ok"]:
        aviso_diapositivas(resultado, diapositivas)
    if resultado["ok"]:
        try:                                   # copia de la última versión correcta (sin dejarla a medias)
            tmp = build / (nombre + ".ok.pdf.tmp")
            shutil.copyfile(pdf, tmp)
            os.replace(tmp, build / (nombre + ".ok.pdf"))
        except OSError:
            pass
        if hacer_miniatura:
            miniatura(pdf, build / "miniatura.png")
    resultado["formato"] = bool(formato)
    resultado["motor"] = motor
    return resultado


def recorte_png(pdf: Path, destino: Path, caja: dict, papel: dict, ancho: int = 360) -> bool:
    """PNG de un trozo de la primera página (caja en pt de TeX desde arriba a la izquierda)."""
    exe = pdftoppm()
    if not exe or not pdf.exists() or not caja or not papel:
        return False
    w_pt = max(1.0, caja["x1"] - caja["x0"])
    ppp = max(20.0, min(600.0, ancho / (w_pt / 72.27)))
    px = lambda v: int(round(v / 72.27 * ppp))
    try:
        base = destino.with_suffix("")
        subprocess.run([exe, "-png", "-f", "1", "-l", "1", "-r", f"{ppp:.2f}", "-x", str(px(caja["x0"])),
                        "-y", str(px(caja["y0"])), "-W", str(max(1, px(w_pt))),
                        "-H", str(max(1, px(caja["y1"] - caja["y0"]))), "-singlefile", str(pdf), str(base)],
                       capture_output=True, timeout=60)
        return destino.exists()
    except Exception:
        return False


def miniatura(pdf: Path, destino: Path, ancho: int = 480) -> bool:
    """Imagen pequeña de la primera página (si hay pdftoppm)."""
    exe = pdftoppm()
    if not exe or not pdf.exists():
        return False
    try:
        # se escribe con otro nombre y se cambia de golpe (puede haber otra miniatura en marcha)
        base = destino.with_name(f"{destino.stem}-{os.getpid()}-{threading.get_ident()}")
        subprocess.run([exe, "-png", "-f", "1", "-l", "1", "-scale-to", str(ancho), "-singlefile",
                        str(pdf), str(base)], capture_output=True, timeout=60)
        hecho = base.with_suffix(".png")
        if not hecho.exists():
            return False
        os.replace(hecho, destino)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- PDF para imprenta
MM_BP = 72 / 25.4


def ghostscript() -> str | None:
    return os.environ.get("DOCSLAB_GS") or shutil.which("gs") or shutil.which("gswin64c") or shutil.which("gswin32c")


def marcas_de_corte(fuente: Path, destino: Path, tamanos: list[tuple[float, float]], margen_mm: float = 10,
                    tiempo: int = 180) -> bool:
    """Pone cada página de «fuente» (un PDF ya hecho, sin sangrado) en una página
    «margen_mm» más grande por cada lado, con marcas de corte y la caja TrimBox.
    tamanos: ancho y alto de cada página en pt del PDF."""
    exe = pdflatex()
    if not exe or not fuente.exists() or not tamanos:
        return False
    e = margen_mm * MM_BP
    paginas = []
    for n, (w, h) in enumerate(tamanos, start=1):
        marcas = []
        for cx, cy, sx, sy in ((e, -e, -1, 1), (e + w, -e, 1, 1), (e, -e - h, -1, -1), (e + w, -e - h, 1, -1)):
            marcas.append(f"\\draw ({cx + sx * 2 * MM_BP:.3f}bp,{cy:.3f}bp) -- ({cx + sx * e:.3f}bp,{cy:.3f}bp);")
            marcas.append(f"\\draw ({cx:.3f}bp,{cy + sy * 2 * MM_BP:.3f}bp) -- ({cx:.3f}bp,{cy + sy * e:.3f}bp);")
        paginas.append(
            f"\\pdfpagewidth={w + 2 * e:.3f}bp \\pdfpageheight={h + 2 * e:.3f}bp\n"
            f"\\pdfpageattr{{/TrimBox [{e:.3f} {e:.3f} {e + w:.3f} {e + h:.3f}] /BleedBox [{e:.3f} {e:.3f} {e + w:.3f} {e + h:.3f}]}}\n"
            "\\noindent\\begin{picture}(0,0)\n"
            f"\\put({e:.3f},{-(e + h):.3f}){{\\includegraphics[page={n}]{{origen.pdf}}}}\n"
            "\\put(0,0){\\begin{tikzpicture}[overlay, line width=0.3pt, black]\n" + "\n".join(marcas) + "\n"
            "\\end{tikzpicture}}\n\\end{picture}\n\\newpage\n")
    tex = (SIN_EPSTOPDF + "\n\\documentclass{article}\n\\usepackage{graphicx,tikz}\n\\pagestyle{empty}\n"
           "\\setlength\\hoffset{-1in}\\setlength\\voffset{-1in}\\setlength\\topmargin{0pt}\\setlength\\headheight{0pt}\n"
           "\\setlength\\headsep{0pt}\\setlength\\oddsidemargin{0pt}\\setlength\\topskip{0pt}\\setlength\\parindent{0pt}\n"
           "\\setlength\\unitlength{1bp}\\setlength\\textheight{100cm}\\setlength\\textwidth{100cm}\n"
           "\\begin{document}\n" + "".join(paginas) + "\\end{document}\n")
    with tempfile.TemporaryDirectory(prefix="pl-marcas-") as tmp:
        tmp = Path(tmp)
        shutil.copyfile(fuente, tmp / "origen.pdf")
        (tmp / "marcas.tex").write_text(tex, encoding="utf-8")
        try:
            subprocess.run([exe, "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", *opciones_motor(),
                            "marcas.tex"], cwd=tmp, capture_output=True, timeout=tiempo_motor(tiempo),
                           stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            return False
        hecho = tmp / "marcas.pdf"
        if not hecho.exists():
            return False
        shutil.copyfile(hecho, destino)
    return True


def a_cmyk(fuente: Path, destino: Path, tiempo: int = 600) -> tuple[bool, str]:
    """Convierte los colores a CMYK con Ghostscript (perfil CMYK genérico de Ghostscript).
    Conserva TrimBox y BleedBox, las tipografías incrustadas y la resolución de las imágenes."""
    gs = ghostscript()
    if not gs:
        return False, "Para pasar a CMYK hace falta Ghostscript (gs)."
    tmp = destino.with_name(destino.stem + f"-{os.getpid()}-{threading.get_ident()}.tmp.pdf")
    orden = [gs, "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite", "-dPDFSETTINGS=/prepress",
             "-dCompatibilityLevel=1.6", "-sColorConversionStrategy=CMYK", "-sProcessColorModel=DeviceCMYK",
             "-dAutoRotatePages=/None", "-dDownsampleColorImages=false", "-dDownsampleGrayImages=false",
             "-dDownsampleMonoImages=false", "-dEmbedAllFonts=true", "-dSubsetFonts=true",
             f"-sOutputFile={tmp}", str(fuente)]
    try:
        p = subprocess.run(orden, capture_output=True, timeout=tiempo, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return False, f"Ghostscript tardó más de {tiempo} s."
    except OSError as exc:
        return False, f"No se pudo ejecutar Ghostscript: {exc}"
    if p.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        err = (p.stderr or p.stdout or b"").decode("utf-8", "replace").strip().splitlines()
        return False, "Ghostscript no pudo convertir el PDF" + (f": {err[-1][:200]}" if err else ".")
    os.replace(tmp, destino)
    return True, ""


def miniatura_cmyk(pdf: Path, destino: Path, ancho: int = 480) -> bool:
    """Como miniatura(), pero con Ghostscript, que pinta bien los colores CMYK."""
    gs = ghostscript()
    if not gs or not pdf.exists():
        return miniatura(pdf, destino, ancho)
    try:
        sal = subprocess.run(["pdfinfo", "-f", "1", "-l", "1", str(pdf)], capture_output=True, timeout=30) \
            if shutil.which("pdfinfo") else None
        mo = re.search(rb"Page\s+1\s+size:\s+([\d.]+) x", sal.stdout) if sal else None
        w_pt = float(mo.group(1)) if mo else 2384.0
        ppp = max(4.0, ancho / (w_pt / 72))
        tmp = destino.with_name(f"{destino.stem}-{os.getpid()}-{threading.get_ident()}.png")
        subprocess.run([gs, "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m", "-dFirstPage=1", "-dLastPage=1",
                        f"-r{ppp:.2f}", "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4", f"-sOutputFile={tmp}", str(pdf)],
                       capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
        if not tmp.exists():
            return False
        os.replace(tmp, destino)
        return True
    except Exception:          # noqa: BLE001
        return False
