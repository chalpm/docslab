"""Conversión del texto que se escribe en la aplicación a LaTeX.

Hay dos formatos por proyecto:

* «simple» (por defecto): el texto se escribe tal cual y la aplicación escapa
  los caracteres especiales de LaTeX. Admite un marcado ligero:
      **negrita**   *cursiva*   `código`   $matemáticas$   ^superíndice^
      ~subíndice~   {{\\orden LaTeX sin tocar}}
  Una línea en blanco separa párrafos y un salto de línea simple corta la línea.
* «latex»: el texto se copia sin cambios (para quien prefiere escribir LaTeX).
"""
from __future__ import annotations

import re

ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "%": r"\%",
    "&": r"\&",
    "#": r"\#",
    "_": r"\_",
    "^": r"\textasciicircum{}",
    "~": r"\textasciitilde{}",
}
_ESC_RE = re.compile(r"[\\{}$%&#_^~]")

# Orden de prioridad: matemáticas, código, negrita, cursiva, sup, sub.
# (El LaTeX crudo {{...}} se separa antes, contando llaves.)
_MARCADO = re.compile(
    r"(?<!\\)\$(?P<mate>[^$\n]+?)\$"
    r"|`(?P<codigo>[^`\n]+?)`"
    r"|\*\*(?P<negrita>.+?)\*\*"
    r"|(?<![\w*])\*(?P<cursiva>[^*\s](?:[^*\n]*?[^*\s])?)\*(?![\w*])"
    r"|\^(?P<sup>[^^\s](?:[^^\n]*?))\^"
    r"|~(?P<sub>[^~\s](?:[^~\n]*?))~",
    re.DOTALL,
)


def _trozos_crudos(texto: str):
    """Separa los fragmentos {{...}} (LaTeX sin tocar) contando llaves.
    Devuelve una lista de (es_crudo, texto)."""
    trozos, i, n = [], 0, len(texto)
    inicio = 0
    while i < n - 1:
        if texto[i] == "{" and texto[i + 1] == "{":
            j, prof = i + 2, 0
            while j < n:
                ch = texto[j]
                if ch == "\\":
                    j += 2
                    continue
                if ch == "{":
                    prof += 1
                elif ch == "}":
                    if prof == 0 and j + 1 < n and texto[j + 1] == "}":
                        break
                    prof -= 1
                j += 1
            if j < n:
                if inicio < i:
                    trozos.append((False, texto[inicio:i]))
                trozos.append((True, texto[i + 2:j]))
                i = inicio = j + 2
                continue
        i += 1
    if inicio < n:
        trozos.append((False, texto[inicio:]))
    return trozos


def escapar(texto: str) -> str:
    """Escapa los caracteres especiales de LaTeX."""
    return _ESC_RE.sub(lambda m: ESCAPES[m.group(0)], texto)


def _en_linea(texto: str) -> str:
    """Convierte un fragmento sin párrafos (el marcado puede anidarse)."""
    return "".join(c if crudo else _marcado(c) for crudo, c in _trozos_crudos(texto))


def _marcado(texto: str) -> str:
    salida = []
    pos = 0
    for m in _MARCADO.finditer(texto):
        salida.append(escapar(texto[pos:m.start()]))
        tipo = m.lastgroup
        valor = m.group(tipo)
        if tipo == "mate":
            salida.append("$" + valor + "$")
        elif tipo == "codigo":
            salida.append(r"\codigo{" + escapar(valor) + "}")
        elif tipo == "negrita":
            salida.append(r"\textbf{" + _en_linea(valor) + "}")
        elif tipo == "cursiva":
            salida.append(r"\textit{" + _en_linea(valor) + "}")
        elif tipo == "sup":
            salida.append(r"\textsuperscript{" + _en_linea(valor) + "}")
        elif tipo == "sub":
            salida.append(r"\textsubscript{" + _en_linea(valor) + "}")
        pos = m.end()
    salida.append(escapar(texto[pos:]))
    return "".join(salida)


def _lineas(texto: str) -> str:
    partes = [p.strip() for p in texto.split("\n")]
    partes = [p for p in partes if p]
    return r"\newline ".join(_en_linea(p) for p in partes)


def convertir(texto, formato: str = "simple", parrafos: bool = True) -> str:
    """Convierte un campo de texto a LaTeX.

    parrafos=True: las líneas en blanco separan párrafos (\\par).
    parrafos=False: todo queda en un solo párrafo (títulos, pies, rótulos).
    """
    if texto is None:
        return ""
    texto = str(texto).replace("\r\n", "\n").replace("\r", "\n")
    if formato == "latex":
        return texto.strip()
    texto = texto.strip()
    if not texto:
        return ""
    if not parrafos:
        return _lineas(texto)
    bloques = [b for b in re.split(r"\n\s*\n", texto) if b.strip()]
    return r"\par ".join(_lineas(b) for b in bloques)


def lista(elementos, formato: str = "simple") -> list[str]:
    """Convierte una lista (o un texto con un elemento por línea)."""
    if isinstance(elementos, str):
        elementos = [e for e in elementos.replace("\r", "").split("\n") if e.strip()]
    return [convertir(e, formato, parrafos=False) for e in (elementos or [])]


def texto_plano(texto, limite: int = 60) -> str:
    """Resumen de un texto para mostrarlo en el árbol de la aplicación."""
    if not texto:
        return ""
    t = re.sub(r"\s+", " ", str(texto)).strip()
    t = re.sub(r"[*`^~{}$]", "", t)
    return t if len(t) <= limite else t[: limite - 1].rstrip() + "…"
