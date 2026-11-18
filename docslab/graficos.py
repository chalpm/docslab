# SPDX-License-Identifier: AGPL-3.0-only
"""Plantillas de gráficos del LAB.

Una plantilla es código Python con huecos «{{nombre}}» y la lista de parámetros que
los rellenan desde un formulario (datos, columnas, textos, colores…). Al usarla se
genera código normal, que queda en una celda del cuaderno y se puede editar a mano.
Las incluidas usan matplotlib, seaborn o plotly; las propias se guardan en
datos/graficos/ y sirven para todos los documentos.
"""
from __future__ import annotations

import base64
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .almacen import ErrorAlmacen

TIPOS = ("datos", "columna", "columnas", "texto", "numero", "interruptor", "opcion", "color", "paleta")
BIBLIOTECAS = ("matplotlib", "seaborn", "plotly")
PALETAS = ["documento", "deep", "muted", "colorblind", "Set2", "tab10", "viridis", "magma", "Blues", "Greys"]
HUECO = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
DIR_EJEMPLOS = Path(__file__).resolve().parent / "datos_ejemplo"
EJEMPLO = DIR_EJEMPLOS / "ejemplo.csv"
COLORES_DEFECTO = ["#2F4858", "#C8553D", "#588157", "#E0A458", "#6D597A", "#33658A"]


from .graficos_comun import (  # noqa: E402,F401  (también se usan desde fuera)
    CABEZA_MPL, CABEZA_PX, CABEZA_SNS, DATOS, PIE_MPL, PIE_PX, _comunes, _p)

INCLUIDAS = [
    dict(id="barras", nombre="Barras", biblioteca="matplotlib",
         descripcion="Una barra por categoría, con la media de una columna numérica.",
         parametros=[DATOS, _p("x", "Categorías", "columna", "tratamiento"),
                     _p("y", "Valor", "columna", "valor", numerica=True),
                     _p("color", "Color", "color", "primario"),
                     _p("horizontal", "Barras horizontales", "interruptor", False)] + _comunes("barras"),
         codigo=CABEZA_MPL + '''resumen = datos.groupby({{x}}, sort=False)[{{y}}].mean()

fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
if {{horizontal}}:
    ax.barh(resumen.index.astype(str), resumen.values, color={{color}})
    ax.invert_yaxis()
    ax.set_xlabel({{etiqueta_y}} or {{y}})
    ax.set_ylabel({{etiqueta_x}} or {{x}})
else:
    ax.bar(resumen.index.astype(str), resumen.values, color={{color}})
    ax.set_xlabel({{etiqueta_x}} or {{x}})
    ax.set_ylabel({{etiqueta_y}} or {{y}})
''' + PIE_MPL),
    dict(id="barras-agrupadas", nombre="Barras agrupadas", biblioteca="matplotlib",
         descripcion="Barras lado a lado: una categoría en el eje y un color por grupo.",
         parametros=[DATOS, _p("x", "Categorías", "columna", "tratamiento"),
                     _p("grupo", "Un color por", "columna", "grupo"),
                     _p("y", "Valor", "columna", "valor", numerica=True),
                     _p("apiladas", "Apiladas", "interruptor", False),
                     _p("paleta", "Colores", "paleta", "documento")] + _comunes("barras_agrupadas"),
         codigo=CABEZA_MPL + '''tabla = datos.pivot_table(index={{x}}, columns={{grupo}}, values={{y}}, aggfunc="mean", sort=False)
colores = {{paleta}}

fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
tabla.plot.bar(ax=ax, stacked={{apiladas}}, width=0.8, rot=0,
               color=colores if isinstance(colores, list) else None,
               colormap=None if isinstance(colores, list) else colores)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
ax.legend(title={{grupo}}, frameon=False)
''' + PIE_MPL),
    dict(id="lineas", nombre="Líneas", biblioteca="matplotlib",
         descripcion="Evolución de un valor; una línea por grupo si eliges uno.",
         parametros=[DATOS, _p("x", "Eje x", "columna", "tiempo"),
                     _p("y", "Valor", "columna", "valor", numerica=True),
                     _p("grupo", "Una línea por", "columna", "tratamiento", opcional=True),
                     _p("marcadores", "Marcar los puntos", "interruptor", True),
                     _p("paleta", "Colores", "paleta", "documento")] + _comunes("lineas"),
         codigo=CABEZA_MPL + '''colores = {{paleta}}
grupos = [(None, datos)] if not {{grupo}} else list(datos.groupby({{grupo}}, sort=False))

fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
if not isinstance(colores, list):
    colores = [plt.get_cmap(colores)(i / max(1, len(grupos) - 1)) for i in range(len(grupos))]
for i, (nombre, parte) in enumerate(grupos):
    media = parte.groupby({{x}})[{{y}}].mean()
    ax.plot(media.index, media.values, marker="o" if {{marcadores}} else None, markersize=4,
            color=colores[i % len(colores)], label=None if nombre is None else str(nombre))
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
if {{grupo}}:
    ax.legend(title={{grupo}}, frameon=False)
''' + PIE_MPL),
    dict(id="dispersion", nombre="Dispersión", biblioteca="matplotlib",
         descripcion="Una nube de puntos de dos columnas numéricas, con color por grupo opcional.",
         parametros=[DATOS, _p("x", "Eje x", "columna", "peso", numerica=True),
                     _p("y", "Eje y", "columna", "altura", numerica=True),
                     _p("grupo", "Un color por", "columna", "grupo", opcional=True),
                     _p("tamano", "Tamaño de los puntos", "numero", 22, min=1, max=300),
                     _p("paleta", "Colores", "paleta", "documento")] + _comunes("dispersion"),
         codigo=CABEZA_MPL + '''colores = {{paleta}}
grupos = [(None, datos)] if not {{grupo}} else list(datos.groupby({{grupo}}, sort=False))

fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
if not isinstance(colores, list):
    colores = [plt.get_cmap(colores)(i / max(1, len(grupos) - 1)) for i in range(len(grupos))]
for i, (nombre, parte) in enumerate(grupos):
    ax.scatter(parte[{{x}}], parte[{{y}}], s={{tamano}}, alpha=0.8, linewidths=0,
               color=colores[i % len(colores)], label=None if nombre is None else str(nombre))
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
if {{grupo}}:
    ax.legend(title={{grupo}}, frameon=False)
''' + PIE_MPL),
    dict(id="histograma", nombre="Histograma", biblioteca="matplotlib",
         descripcion="Cómo se reparten los valores de una columna numérica.",
         parametros=[DATOS, _p("x", "Columna", "columna", "valor", numerica=True),
                     _p("intervalos", "Número de intervalos", "numero", 20, min=2, max=200),
                     _p("color", "Color", "color", "primario")] + _comunes("histograma", y="Frecuencia"),
         codigo=CABEZA_MPL + '''
fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
ax.hist(datos[{{x}}].dropna(), bins=int({{intervalos}}), color={{color}}, edgecolor="white", linewidth=0.6)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}})
''' + PIE_MPL),
    dict(id="cajas", nombre="Cajas (boxplot)", biblioteca="matplotlib",
         descripcion="Mediana, cuartiles y valores extremos de una columna, por grupo.",
         parametros=[DATOS, _p("x", "Grupos", "columna", "tratamiento"),
                     _p("y", "Valor", "columna", "valor", numerica=True),
                     _p("color", "Color", "color", "primario"),
                     _p("puntos", "Mostrar también los puntos", "interruptor", False)] + _comunes("cajas"),
         codigo=CABEZA_MPL + '''nombres = list(dict.fromkeys(datos[{{x}}].dropna()))
series = [datos.loc[datos[{{x}}] == n, {{y}}].dropna() for n in nombres]

fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
cajas = ax.boxplot(series, patch_artist=True, widths=0.55, medianprops={"color": "white", "linewidth": 1.5})
for caja in cajas["boxes"]:
    caja.set(facecolor={{color}}, edgecolor={{color}})
if {{puntos}}:
    for i, serie in enumerate(series, start=1):
        ax.scatter([i] * len(serie), serie, s=8, color="black", alpha=0.35, zorder=3)
ax.set_xticks(range(1, len(nombres) + 1), [str(n) for n in nombres])
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
''' + PIE_MPL),
    dict(id="violin", nombre="Violín", biblioteca="seaborn",
         descripcion="La forma de la distribución de una columna, por grupo.",
         parametros=[DATOS, _p("x", "Grupos", "columna", "tratamiento"),
                     _p("y", "Valor", "columna", "valor", numerica=True),
                     _p("paleta", "Colores", "paleta", "documento")] + _comunes("violin"),
         codigo=CABEZA_SNS + '''
fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
sns.violinplot(data=datos, x={{x}}, y={{y}}, hue={{x}}, palette={{paleta}}, legend=False, inner="quartile",
               linewidth=0.8, ax=ax)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
''' + PIE_MPL),
    dict(id="barras-error", nombre="Barras con error", biblioteca="seaborn",
         descripcion="Media de cada categoría con su intervalo de confianza del 95 %.",
         parametros=[DATOS, _p("x", "Categorías", "columna", "tratamiento"),
                     _p("y", "Valor", "columna", "valor", numerica=True),
                     _p("grupo", "Un color por", "columna", "grupo", opcional=True),
                     _p("paleta", "Colores", "paleta", "documento")] + _comunes("barras_error"),
         codigo=CABEZA_SNS + '''
fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
sns.barplot(data=datos, x={{x}}, y={{y}}, hue={{grupo}} or {{x}}, palette={{paleta}}, errorbar=("ci", 95),
            capsize=0.15, err_kws={"linewidth": 1}, legend=bool({{grupo}}), ax=ax)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
if {{grupo}}:
    ax.legend(title={{grupo}}, frameon=False)
''' + PIE_MPL),
    dict(id="regresion", nombre="Dispersión con recta", biblioteca="seaborn",
         descripcion="Puntos de dos columnas numéricas con su recta de regresión y su banda de confianza.",
         parametros=[DATOS, _p("x", "Eje x", "columna", "peso", numerica=True),
                     _p("y", "Eje y", "columna", "altura", numerica=True),
                     _p("color", "Color", "color", "primario")] + _comunes("regresion"),
         codigo=CABEZA_SNS + '''
fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
sns.regplot(data=datos, x={{x}}, y={{y}}, color={{color}}, scatter_kws={"s": 16, "alpha": 0.7}, ax=ax)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
''' + PIE_MPL),
    dict(id="correlacion", nombre="Mapa de calor de correlaciones", biblioteca="seaborn",
         descripcion="La correlación entre las columnas numéricas que elijas.",
         parametros=[DATOS, _p("columnas", "Columnas", "columnas", ["tiempo", "valor", "peso", "altura"], numerica=True),
                     _p("anotar", "Escribir el valor en cada celda", "interruptor", True),
                     _p("mapa", "Mapa de color", "opcion", "vlag",
                        opciones=["vlag", "coolwarm", "RdBu_r", "viridis", "magma", "Blues"])]
         + [p for p in _comunes("correlacion", alto=11) if p["nombre"] not in ("etiqueta_x", "etiqueta_y")],
         codigo=CABEZA_SNS + '''correlacion = datos[{{columnas}}].corr()

fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
sns.heatmap(correlacion, annot={{anotar}}, fmt=".2f", cmap={{mapa}}, vmin=-1, vmax=1, square=True,
            linewidths=0.5, cbar_kws={"shrink": 0.8}, ax=ax)
''' + PIE_MPL.replace('ax.spines[["top", "right"]].set_visible(False)\n', "")),
    dict(id="px-dispersion", nombre="Dispersión interactiva", biblioteca="plotly",
         descripcion="Puntos que muestran sus datos al pasar el cursor. Al documento entra como imagen fija.",
         parametros=[DATOS, _p("x", "Eje x", "columna", "peso", numerica=True),
                     _p("y", "Eje y", "columna", "altura", numerica=True),
                     _p("grupo", "Un color por", "columna", "grupo", opcional=True),
                     _p("paleta", "Colores", "paleta", "documento")] + _comunes("dispersion_interactiva"),
         codigo=CABEZA_PX + '''colores = {{paleta}}
fig = px.scatter(datos, x={{x}}, y={{y}}, color={{grupo}} or None,
                 color_discrete_sequence=colores if isinstance(colores, list) else None,
                 labels={ {{x}}: {{etiqueta_x}} or {{x}}, {{y}}: {{etiqueta_y}} or {{y}} })
''' + PIE_PX),
    dict(id="px-lineas", nombre="Líneas interactivas", biblioteca="plotly",
         descripcion="Evolución de un valor, con una línea por grupo. Al documento entra como imagen fija.",
         parametros=[DATOS, _p("x", "Eje x", "columna", "tiempo"),
                     _p("y", "Valor", "columna", "valor", numerica=True),
                     _p("grupo", "Una línea por", "columna", "tratamiento", opcional=True),
                     _p("paleta", "Colores", "paleta", "documento")] + _comunes("lineas_interactivas"),
         codigo=CABEZA_PX + '''colores = {{paleta}}
claves = [{{x}}] + ([{{grupo}}] if {{grupo}} else [])
media = datos.groupby(claves, sort=False, as_index=False)[{{y}}].mean()
fig = px.line(media, x={{x}}, y={{y}}, color={{grupo}} or None, markers=True,
              color_discrete_sequence=colores if isinstance(colores, list) else None,
              labels={ {{x}}: {{etiqueta_x}} or {{x}}, {{y}}: {{etiqueta_y}} or {{y}} })
''' + PIE_PX),
    dict(id="px-barras", nombre="Barras interactivas", biblioteca="plotly",
         descripcion="Media por categoría, con un color por grupo. Al documento entra como imagen fija.",
         parametros=[DATOS, _p("x", "Categorías", "columna", "tratamiento"),
                     _p("y", "Valor", "columna", "valor", numerica=True),
                     _p("grupo", "Un color por", "columna", "grupo", opcional=True),
                     _p("paleta", "Colores", "paleta", "documento")] + _comunes("barras_interactivas"),
         codigo=CABEZA_PX + '''colores = {{paleta}}
claves = [{{x}}] + ([{{grupo}}] if {{grupo}} else [])
media = datos.groupby(claves, sort=False, as_index=False)[{{y}}].mean()
fig = px.bar(media, x={{x}}, y={{y}}, color={{grupo}} or None, barmode="group",
             color_discrete_sequence=colores if isinstance(colores, list) else None,
             labels={ {{x}}: {{etiqueta_x}} or {{x}}, {{y}}: {{etiqueta_y}} or {{y}} })
''' + PIE_PX),
]
CATEGORIAS = ["Distribución", "Correlación", "Ranking", "Partes de un todo", "Evolución", "Mapas", "Flujos",
              "Multivariado", "Aprendizaje automático", "Estadística", "Biomedicina", "Señales y superficies"]
_CATEGORIA = {  # las incluidas desde el principio, en las categorías de The R Graph Gallery
    "barras": ("Ranking", "barplot.html"), "barras-agrupadas": ("Partes de un todo", "stacked-barplot.html"),
    "lineas": ("Evolución", "line-plot.html"), "dispersion": ("Correlación", "scatterplot.html"),
    "histograma": ("Distribución", "histogram.html"), "cajas": ("Distribución", "boxplot.html"),
    "violin": ("Distribución", "violin.html"), "barras-error": ("Ranking", "barplot.html"),
    "regresion": ("Correlación", "scatterplot.html"), "correlacion": ("Correlación", "correlogram.html"),
    "px-dispersion": ("Correlación", "scatterplot.html"), "px-lineas": ("Evolución", "line-plot.html"),
    "px-barras": ("Ranking", "barplot.html"),
}
for _t in INCLUIDAS:
    _t["categoria"], _ref = _CATEGORIA[_t["id"]]
    _t["referencia"] = "https://r-graph-gallery.com/" + _ref

from .graficos_ciencia import CIENCIA  # noqa: E402
from .graficos_galeria import GALERIA  # noqa: E402

INCLUIDAS += GALERIA + CIENCIA
for _t in INCLUIDAS:
    _t["incluida"] = True

NUEVA = dict(nombre="Gráfico nuevo", biblioteca="matplotlib", descripcion="",
             parametros=[DATOS, _p("x", "Eje x", "columna", "tiempo"), _p("y", "Eje y", "columna", "valor", numerica=True),
                         _p("color", "Color", "color", "primario"), _p("titulo", "Título", "texto", ""),
                         _p("salida", "Guardar como", "texto", "figuras/grafico.pdf")],
             codigo='''import os
import pandas as pd
import matplotlib.pyplot as plt

datos = {{datos}}

fig, ax = plt.subplots(figsize=(14 / 2.54, 9 / 2.54))
ax.plot(datos[{{x}}], datos[{{y}}], ".", color={{color}})
ax.set_xlabel({{x}})
ax.set_ylabel({{y}})
ax.set_title({{titulo}})
fig.tight_layout()
os.makedirs(os.path.dirname({{salida}}) or ".", exist_ok=True)
fig.savefig({{salida}}, bbox_inches="tight", dpi=300)
plt.show()
''')


# ---------------------------------------------------------------------- validar y guardar
def archivos_ejemplo(t: dict) -> list[str]:
    """Los archivos de datos_ejemplo/ que necesita una plantilla para probarse (tabla y, si tiene, mapa base)."""
    nombres = []
    for p in t.get("parametros") or []:
        d = p.get("defecto")
        valor = d.get("archivo") if p.get("tipo") == "datos" and isinstance(d, dict) else (d if p.get("nombre") == "mapa" else None)
        if isinstance(valor, str) and (DIR_EJEMPLOS / valor).is_file() and valor not in nombres:
            nombres.append(valor)
    return nombres or [EJEMPLO.name]


def normalizar(t: dict) -> dict:
    if not isinstance(t, dict):
        raise ErrorAlmacen("Plantilla de gráfico no válida")
    nombre = str(t.get("nombre") or "").strip()[:80] or "Gráfico sin nombre"
    codigo = str(t.get("codigo") or "")
    if len(codigo) > 200_000:
        raise ErrorAlmacen("El código de la plantilla es demasiado largo")
    pars, vistos = [], set()
    for p in t.get("parametros") or []:
        if not isinstance(p, dict):
            continue
        n = str(p.get("nombre") or "").strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,39}", n) or n in vistos:
            continue
        vistos.add(n)
        tipo = p.get("tipo") if p.get("tipo") in TIPOS else "texto"
        q = {"nombre": n, "etiqueta": str(p.get("etiqueta") or n)[:80], "tipo": tipo, "defecto": p.get("defecto")}
        for k in ("opcional", "numerica"):
            if p.get(k):
                q[k] = True
        if p.get("ayuda"):
            q["ayuda"] = str(p["ayuda"])[:300]
        if tipo == "opcion":
            q["opciones"] = [str(o)[:60] for o in (p.get("opciones") or []) if str(o).strip()][:40]
        if tipo == "numero":
            for k in ("min", "max"):
                if isinstance(p.get(k), (int, float)):
                    q[k] = p[k]
        pars.append(q)
    return {"id": str(t.get("id") or ""), "nombre": nombre, "descripcion": str(t.get("descripcion") or "")[:400],
            "biblioteca": t.get("biblioteca") if t.get("biblioteca") in BIBLIOTECAS else "matplotlib",
            "parametros": pars, "codigo": codigo}


class Graficos:
    def __init__(self, raiz: Path):
        self.dir = Path(raiz) / "graficos"

    def _ruta(self, id_: str) -> Path:
        if not re.fullmatch(r"g-[0-9a-f]{6,12}", id_ or ""):
            raise ErrorAlmacen("Plantilla de gráfico no encontrada")
        return self.dir / f"{id_}.json"

    def listar(self) -> list[dict]:
        propias = []
        if self.dir.exists():
            for f in sorted(self.dir.glob("g-*.json")):
                try:
                    t = normalizar(json.loads(f.read_text(encoding="utf-8")))
                    t.update(id=f.stem, incluida=False, modificado=time.strftime("%Y-%m-%dT%H:%M:%S",
                                                                              time.localtime(f.stat().st_mtime)))
                    propias.append(t)
                except Exception:  # noqa: BLE001
                    continue
        return propias + [json.loads(json.dumps(t)) for t in INCLUIDAS]

    def obtener(self, id_: str) -> dict:
        for t in INCLUIDAS:
            if t["id"] == id_:
                return json.loads(json.dumps(t))
        f = self._ruta(id_)
        if not f.exists():
            raise ErrorAlmacen("Plantilla de gráfico no encontrada")
        t = normalizar(json.loads(f.read_text(encoding="utf-8")))
        t.update(id=id_, incluida=False)
        return t

    def guardar(self, t: dict) -> dict:
        t = normalizar(t)
        if not t["id"] or any(x["id"] == t["id"] for x in INCLUIDAS):
            t["id"] = "g-" + secrets.token_hex(4)
        f = self._ruta(t["id"])
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, f)
        t["incluida"] = False
        return t

    def borrar(self, id_: str):
        f = self._ruta(id_)
        if f.exists():
            f.unlink()
        mini = f.with_suffix(".png")
        if mini.exists():
            mini.unlink()

    def miniatura(self, id_: str) -> Path | None:
        f = self._ruta(id_).with_suffix(".png")
        return f if f.exists() else None

    def guardar_miniatura(self, id_: str, png: bytes):
        self.dir.mkdir(parents=True, exist_ok=True)
        self._ruta(id_).with_suffix(".png").write_bytes(png)


# ---------------------------------------------------------------------- generar código
def _color(v, colores: dict) -> str:
    v = str(v or "")
    if re.fullmatch(r"#?[0-9A-Fa-f]{6}", v):
        return "#" + v.lstrip("#").upper()
    c = str((colores or {}).get(v) or "")
    if re.fullmatch(r"#?[0-9A-Fa-f]{6}", c):
        return "#" + c.lstrip("#").upper()
    return COLORES_DEFECTO[0]


def paleta_documento(colores: dict) -> list[str]:
    lista = []
    for k in ("primario", "acento"):
        c = str((colores or {}).get(k) or "")
        if re.fullmatch(r"#?[0-9A-Fa-f]{6}", c) and "#" + c.lstrip("#").upper() not in lista:
            lista.append("#" + c.lstrip("#").upper())
    for c in COLORES_DEFECTO:                        # hasta seis colores distintos
        if len(lista) >= 6:
            break
        if c not in lista:
            lista.append(c)
    return lista


def _datos(v) -> str:
    v = v if isinstance(v, dict) else {}
    if v.get("modo") == "variable":
        var = str(v.get("variable") or "")
        if not var.isidentifier():
            raise ErrorAlmacen("Elige la tabla (DataFrame) del cuaderno que quieres dibujar")
        return var
    archivo = str(v.get("archivo") or "")
    if not archivo:
        raise ErrorAlmacen("Elige el archivo de datos")
    ext = Path(archivo).suffix.lower()
    if ext in (".xlsx", ".xls"):
        return f"pd.read_excel({archivo!r})"
    if ext == ".parquet":
        return f"pd.read_parquet({archivo!r})"
    if ext == ".json":
        return f"pd.read_json({archivo!r})"
    if ext in (".tsv", ".tab"):
        return f"pd.read_csv({archivo!r}, sep=\"\\t\")"
    return f"pd.read_csv({archivo!r}, sep=None, engine=\"python\")"


def _texto_py(s: str) -> str:
    """Un texto como literal de Python, con comillas dobles y sin escapar los acentos."""
    return json.dumps(str(s), ensure_ascii=False)


def valor_py(p: dict, v, colores: dict) -> str:
    tipo = p["tipo"]
    if v is None:
        v = p.get("defecto")
    if tipo == "datos":
        return _datos(v)
    if tipo == "columna":
        if not v:
            if p.get("opcional"):
                return "None"
            raise ErrorAlmacen(f"Falta elegir «{p['etiqueta']}»")
        return _texto_py(v)
    if tipo == "columnas":
        lista = [str(x) for x in (v if isinstance(v, list) else [])]
        if not lista and not p.get("opcional"):
            raise ErrorAlmacen(f"Falta elegir «{p['etiqueta']}»")
        return "[" + ", ".join(_texto_py(x) for x in lista) + "]"
    if tipo == "numero":
        try:
            n = float(v)
        except (TypeError, ValueError):
            n = float(p.get("defecto") or 0)
        return str(int(n)) if n == int(n) else repr(float(f"{n:.10g}"))     # 10 cifras: 5e-08 no se vuelve 0
    if tipo == "interruptor":
        return "True" if v else "False"
    if tipo == "color":
        return _texto_py(_color(v, colores))
    if tipo == "paleta":
        if not v or v == "documento":
            return "[" + ", ".join(_texto_py(c) for c in paleta_documento(colores)) + "]"
        return _texto_py(v)
    return _texto_py("" if v is None else v)


def generar(t: dict, valores: dict | None, colores: dict | None = None) -> str:
    """El código de la plantilla con sus huecos rellenos."""
    t = normalizar(t)
    valores = valores or {}
    hechos = {p["nombre"]: valor_py(p, valores.get(p["nombre"]), colores or {}) for p in t["parametros"]}

    def poner(m):
        n = m.group(1)
        if n not in hechos:
            raise ErrorAlmacen(f"El código usa «{{{{{n}}}}}», pero no hay un parámetro con ese nombre")
        return hechos[n]

    cuerpo = HUECO.sub(poner, t["codigo"]).rstrip() + "\n"
    return f"# {t['nombre']} · plantilla de gráficos de DocsLab (este código se puede editar)\n" + cuerpo


# ---------------------------------------------------------------------- probar con los datos de ejemplo
EPILOGO = '''

# --- DocsLab: vista de prueba ---
try:
    import matplotlib.pyplot as _plt
    if _plt.get_fignums():
        _plt.figure(_plt.get_fignums()[-1]).savefig("_vista.png", dpi=110, bbox_inches="tight")
except Exception:
    pass
try:
    import plotly.graph_objects as _go
    _figs = [v for v in list(globals().values()) if isinstance(v, _go.Figure)]
    if _figs:
        open("_vista.json", "w", encoding="utf-8").write(_figs[-1].to_json())
except Exception:
    pass
'''


def probar(codigo: str, tiempo: int = 90) -> dict:
    """Ejecuta el código en una carpeta temporal con los datos de ejemplo y devuelve lo que dibuja."""
    d = Path(tempfile.mkdtemp(prefix="docslab-grafico-"))
    try:
        for f in DIR_EJEMPLOS.iterdir():          # todos los datos de ejemplo (tablas y mapa base)
            if f.is_file() and not f.name.startswith("."):
                shutil.copy2(f, d / f.name)
        prologo = ("import plotly.graph_objects as _g\n_g.Figure.show = lambda *a, **k: None\n"
                   if "plotly" in codigo else "")       # en la prueba no se abre nada: se devuelve la figura
        (d / "_prueba.py").write_text(prologo + codigo + EPILOGO, encoding="utf-8")
        entorno = dict(os.environ, MPLBACKEND="Agg", PLOTLY_RENDERER="plotly_mimetype", PYTHONIOENCODING="utf-8")
        try:
            r = subprocess.run([sys.executable, "_prueba.py"], cwd=d, env=entorno, capture_output=True, text=True,
                               timeout=tiempo, encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"El código tardó más de {tiempo} s", "salida": ""}
        res = {"ok": r.returncode == 0, "salida": (r.stdout or "")[-6000:], "error": ""}
        if r.returncode != 0:
            lineas = [ln for ln in (r.stderr or "").splitlines() if ln.strip()]
            res["error"] = "\n".join(lineas[-14:]).replace(str(d) + os.sep, "")
        vista = d / "_vista.png"
        if vista.exists():
            res["imagen"] = "data:image/png;base64," + base64.b64encode(vista.read_bytes()).decode()
        elif (d / "_vista.json").exists():
            res["plotly"] = json.loads((d / "_vista.json").read_text(encoding="utf-8"))
        return res
    finally:
        shutil.rmtree(d, ignore_errors=True)
