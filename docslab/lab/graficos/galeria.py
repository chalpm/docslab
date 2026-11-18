# SPDX-License-Identifier: AGPL-3.0-only
"""Plantillas de gráficos inspiradas en el catálogo de The R Graph Gallery
(https://r-graph-gallery.com/), adaptadas a Python con matplotlib y seaborn.

Cada plantilla tiene una categoría (las de la galería: Distribución, Correlación,
Ranking, Partes de un todo, Evolución, Mapas y Flujos), un archivo de datos de
ejemplo en docslab/datos_ejemplo/ y la página de la galería que le sirve de
referencia. El código es propio; de la galería solo se toma la lista de tipos.
Todo funciona sin conexión: los mapas usan mundo.geojson (Natural Earth, dominio
público) y no hacen falta geopandas, networkx, squarify ni wordcloud.
"""
from __future__ import annotations

from .comun import CABEZA_MPL, CABEZA_SNS, PIE_MPL, _comunes, _p

GALERIA_URL = "https://r-graph-gallery.com/"


def _datos(archivo):
    return _p("datos", "Datos", "datos", {"modo": "archivo", "archivo": archivo})


def _sin_ejes(nombre, alto=9, ancho=14):
    out = [p for p in _comunes(nombre, alto=alto) if p["nombre"] not in ("etiqueta_x", "etiqueta_y")]
    for p in out:
        if p["nombre"] == "ancho":
            p["defecto"] = ancho
    return out


PALETA = _p("paleta", "Colores", "paleta", "documento")

# Convierte {{paleta}} (lista de colores o nombre de mapa de color) en n colores
COLORES_N = r'''
def colores_n(n):
    paleta = {{paleta}}
    if not isinstance(paleta, list):
        paleta = [plt.get_cmap(paleta)(i / max(1, n - 1)) for i in range(n)]
    return [paleta[i % len(paleta)] for i in range(n)]

'''

FIG = "\nfig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))\n"
PIE_SIN_EJES = PIE_MPL.replace('ax.spines[["top", "right"]].set_visible(False)\n', "ax.axis(\"off\")\n")
PIE_FIGURA = r'''
fig.set_size_inches({{ancho}} / 2.54, {{alto}} / 2.54)
if {{titulo}}:
    fig.suptitle({{titulo}})
fig.tight_layout()
os.makedirs(os.path.dirname({{salida}}) or ".", exist_ok=True)
fig.savefig({{salida}}, bbox_inches="tight", dpi=300)
plt.show()
'''


def _t(id_, nombre, categoria, ref, biblioteca, descripcion, parametros, codigo):
    return dict(id=id_, nombre=nombre, categoria=categoria, biblioteca=biblioteca, descripcion=descripcion,
                referencia=GALERIA_URL + ref, parametros=parametros, codigo=codigo)


# =============================================================================================== mapas
MAPA_PARAMS = [
    _p("mapa", "Mapa base (GeoJSON)", "texto", "mundo.geojson",
       ayuda="Países de Natural Earth incluidos con los datos de ejemplo. Vale cualquier GeoJSON de polígonos."),
    _p("zona", "Zona", "opcion", "Mundo",
       opciones=["Mundo", "América", "América Latina", "México", "Europa", "África", "Asia", "Oceanía"]),
    _p("proyeccion", "Proyección", "opcion", "Equal Earth (igual área)",
       opciones=["Equal Earth (igual área)", "Longitud/latitud"]),
    _p("color_tierra", "Color de la tierra", "color", "#E4E4E4"),
]

MAPA_BASE = r'''import json
import numpy as np
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon

IGUAL_AREA = {{proyeccion}}.startswith("Equal")
ZONAS = {"Mundo": (-180, 180, -58, 84), "América": (-170, -30, -58, 75), "América Latina": (-118, -33, -56, 33),
         "México": (-118.5, -86, 14, 33.5), "Europa": (-25, 45, 34, 72), "África": (-20, 55, -36, 38),
         "Asia": (25, 150, -11, 56), "Oceanía": (110, 180, -48, 0)}


def proyectar(lon, lat):
    """Longitud y latitud (grados) → x, y. Equal Earth conserva las áreas."""
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    if not IGUAL_AREA:
        return lon, lat
    a1, a2, a3, a4, m = 1.340264, -0.081106, 0.000893, 0.003796, np.sqrt(3) / 2
    t = np.arcsin(m * np.sin(np.radians(lat)))
    x = 2 * np.sqrt(3) * np.radians(lon) * np.cos(t) / (3 * (9 * a4 * t**8 + 7 * a3 * t**6 + 3 * a2 * t**2 + a1))
    y = a4 * t**9 + a3 * t**7 + a2 * t**3 + a1 * t
    return np.degrees(x), np.degrees(y)


with open({{mapa}}, encoding="utf-8") as f:
    mundo = json.load(f)["features"]


def formas(rasgo):
    g = rasgo["geometry"]
    partes = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    return [Polygon(np.column_stack(proyectar(*np.array(p[0]).T)), closed=True) for p in partes]


def dibujar_tierra(ax, colores=None, defecto={{color_tierra}}, borde="white"):
    """Dibuja los países; «colores» es un diccionario iso3 → color (los demás, «defecto»)."""
    piezas, tonos = [], []
    for r in mundo:
        if r["properties"].get("continente") == "Antártida":
            continue
        c = (colores or {}).get(r["properties"].get("iso3"), defecto)
        for p in formas(r):
            piezas.append(p)
            tonos.append(c)
    ax.add_collection(PatchCollection(piezas, facecolor=tonos, edgecolor=borde, linewidth=0.3))


def encuadrar(ax):
    lon0, lon1, lat0, lat1 = ZONAS.get({{zona}}, ZONAS["Mundo"])
    lons = np.concatenate([np.linspace(lon0, lon1, 50), np.full(50, lon1), np.linspace(lon1, lon0, 50), np.full(50, lon0)])
    lats = np.concatenate([np.full(50, lat0), np.linspace(lat0, lat1, 50), np.full(50, lat1), np.linspace(lat1, lat0, 50)])
    x, y = proyectar(lons, lats)
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(y.min(), y.max())
    ax.set_aspect("equal")
    ax.axis("off")
'''

MAPAS = [
    _t("mapa-puntos", "Mapa con puntos", "Mapas", "map.html", "matplotlib",
       "Un mapa del mundo (o de una zona) con un punto por fila, en las coordenadas de la tabla.",
       [_datos("ejemplo_puntos.csv"), _p("lat", "Latitud", "columna", "lat", numerica=True),
        _p("lon", "Longitud", "columna", "lon", numerica=True),
        _p("grupo", "Un color por", "columna", "ciudad", opcional=True),
        _p("tamano", "Tamaño de los puntos", "numero", 6, min=1, max=200), PALETA, *MAPA_PARAMS,
        _p("leyenda", "Mostrar la leyenda", "interruptor", False)] + _sin_ejes("mapa_puntos", alto=8, ancho=16),
       CABEZA_MPL + MAPA_BASE + COLORES_N + FIG + r'''dibujar_tierra(ax)
grupos = [(None, datos)] if not {{grupo}} else list(datos.groupby({{grupo}}, sort=False))
for (nombre, parte), color in zip(grupos, colores_n(len(grupos))):
    x, y = proyectar(parte[{{lon}}], parte[{{lat}}])
    ax.scatter(x, y, s={{tamano}}, color=color, alpha=0.75, linewidths=0, zorder=3,
               label=None if nombre is None else str(nombre))
encuadrar(ax)
if {{grupo}} and {{leyenda}}:
    ax.legend(frameon=False, fontsize="small", loc="lower left", ncol=2)
''' + PIE_SIN_EJES),
    _t("coropletas", "Mapa de coropletas", "Mapas", "choropleth-map.html", "matplotlib",
       "Cada país coloreado según un valor. Los datos de ejemplo son estimaciones de Natural Earth.",
       [_datos("ejemplo_paises.csv"), _p("clave", "Código ISO3 del país", "columna", "iso3"),
        _p("valor", "Valor", "columna", "pib_per_capita", numerica=True),
        _p("logaritmica", "Escala logarítmica", "interruptor", True),
        _p("mapa_color", "Mapa de color", "opcion", "viridis",
           opciones=["viridis", "magma", "cividis", "Blues", "Greens", "OrRd", "YlGnBu", "RdBu_r"]),
        _p("rotulo", "Rótulo de la escala", "texto", "PIB por habitante (USD)"), *MAPA_PARAMS]
       + _sin_ejes("coropletas", alto=8, ancho=16),
       CABEZA_MPL + MAPA_BASE + r'''from matplotlib.colors import LogNorm, Normalize

valores = datos.dropna(subset=[{{valor}}]).set_index({{clave}})[{{valor}}]
if {{logaritmica}}:
    valores = valores[valores > 0]
    norma = LogNorm(valores.min(), valores.max())
else:
    norma = Normalize(valores.min(), valores.max())
cmap = plt.get_cmap({{mapa_color}})
''' + FIG + r'''dibujar_tierra(ax, {k: cmap(norma(v)) for k, v in valores.items()})
encuadrar(ax)
barra = fig.colorbar(plt.cm.ScalarMappable(norm=norma, cmap=cmap), ax=ax, orientation="horizontal",
                     fraction=0.04, pad=0.02, aspect=40)
barra.set_label({{rotulo}} or {{valor}})
barra.outline.set_visible(False)
''' + PIE_SIN_EJES),
    _t("mapa-hexagonos", "Mapa de hexágonos (densidad)", "Mapas", "hexbin-map.html", "matplotlib",
       "Cuántos puntos caen en cada hexágono del mapa: muestra dónde se concentran los datos.",
       [_datos("ejemplo_puntos.csv"), _p("lat", "Latitud", "columna", "lat", numerica=True),
        _p("lon", "Longitud", "columna", "lon", numerica=True),
        _p("hexagonos", "Hexágonos a lo ancho", "numero", 60, min=5, max=300),
        _p("mapa_color", "Mapa de color", "opcion", "magma_r",
           opciones=["magma_r", "viridis", "YlOrRd", "Blues", "Greens", "inferno_r"]), *MAPA_PARAMS]
       + _sin_ejes("mapa_hexagonos", alto=8, ancho=16),
       CABEZA_MPL + MAPA_BASE + FIG + r'''dibujar_tierra(ax)
x, y = proyectar(datos[{{lon}}], datos[{{lat}}])
lon0, lon1, lat0, lat1 = ZONAS.get({{zona}}, ZONAS["Mundo"])
ex, ey = proyectar([lon0, lon1, lon0, lon1], [lat0, lat0, lat1, lat1])
hb = ax.hexbin(x, y, gridsize=int({{hexagonos}}), mincnt=1, cmap={{mapa_color}}, linewidths=0.2, zorder=3,
               extent=(ex.min(), ex.max(), ey.min(), ey.max()))
encuadrar(ax)
barra = fig.colorbar(hb, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02, aspect=40)
barra.set_label("Puntos por hexágono")
barra.outline.set_visible(False)
''' + PIE_SIN_EJES),
    _t("cartograma", "Cartograma de círculos (Dorling)", "Mapas", "cartogram.html", "matplotlib",
       "Cada país es un círculo de área proporcional a su valor, cerca de su posición real.",
       [_datos("ejemplo_paises.csv"), _p("lat", "Latitud", "columna", "lat", numerica=True),
        _p("lon", "Longitud", "columna", "lon", numerica=True),
        _p("valor", "Valor (área del círculo)", "columna", "poblacion", numerica=True),
        _p("grupo", "Un color por", "columna", "continente", opcional=True),
        _p("etiqueta", "Rótulo", "columna", "iso3", opcional=True),
        _p("escala", "Tamaño de los círculos", "numero", 1.0, min=0.1, max=5),
        _p("fondo", "Dibujar el mapa debajo", "interruptor", True), PALETA, *MAPA_PARAMS]
       + _sin_ejes("cartograma", alto=8, ancho=16),
       CABEZA_MPL + MAPA_BASE + COLORES_N + r'''from matplotlib.patches import Circle

d = datos.dropna(subset=[{{valor}}, {{lat}}, {{lon}}])
d = d[d[{{valor}}] > 0].sort_values({{valor}}, ascending=False).reset_index(drop=True)
x, y = proyectar(d[{{lon}}], d[{{lat}}])
inicio = np.column_stack([x, y])
pos = inicio.copy()
radio = np.sqrt(d[{{valor}}].to_numpy() / d[{{valor}}].max()) * 15 * {{escala}}
for _ in range(300):                       # separa los círculos que se solapan y los atrae a su sitio
    dif = pos[:, None, :] - pos[None, :, :]
    dist = np.hypot(dif[..., 0], dif[..., 1]) + 1e-9
    solape = np.clip(radio[:, None] + radio[None, :] - dist, 0, None)
    np.fill_diagonal(solape, 0)
    pos += 0.5 * (dif / dist[..., None] * solape[..., None]).sum(axis=1) / (1 + (solape > 0).sum(axis=1))[:, None]
    pos += 0.05 * (inicio - pos)
grupos = list(dict.fromkeys(d[{{grupo}}])) if {{grupo}} else [None]
tono = dict(zip(grupos, colores_n(len(grupos))))
''' + FIG + r'''if {{fondo}}:
    dibujar_tierra(ax, defecto="#F0F0F0")
for i, fila in d.iterrows():
    color = tono[fila[{{grupo}}] if {{grupo}} else None]
    ax.add_patch(Circle(pos[i], radio[i], facecolor=color, edgecolor="white", linewidth=0.4, alpha=0.9, zorder=3))
    if {{etiqueta}} and radio[i] > 3:
        ax.text(*pos[i], str(fila[{{etiqueta}}]), ha="center", va="center", fontsize="x-small", color="white", zorder=4)
encuadrar(ax)
if {{grupo}}:
    ax.legend(handles=[Circle((0, 0), 1, color=c, label=str(g)) for g, c in tono.items()], frameon=False,
              fontsize="small", loc="lower left", ncol=2)
''' + PIE_SIN_EJES),
    _t("mapa-conexiones", "Mapa de conexiones", "Mapas", "connection-map.html", "matplotlib",
       "Líneas por el camino más corto sobre la Tierra (círculo máximo) entre pares de lugares.",
       [_datos("ejemplo_conexiones.csv"), _p("lat0", "Latitud de origen", "columna", "lat_origen", numerica=True),
        _p("lon0", "Longitud de origen", "columna", "lon_origen", numerica=True),
        _p("lat1", "Latitud de destino", "columna", "lat_destino", numerica=True),
        _p("lon1", "Longitud de destino", "columna", "lon_destino", numerica=True),
        _p("peso", "Grosor según", "columna", "valor", opcional=True, numerica=True),
        _p("color", "Color de las líneas", "color", "acento"), *MAPA_PARAMS]
       + _sin_ejes("mapa_conexiones", alto=8, ancho=16),
       CABEZA_MPL + MAPA_BASE + r'''

def circulo_maximo(lat0, lon0, lat1, lon1, n=80):
    """Puntos del camino más corto sobre la esfera; se corta al cruzar el meridiano 180."""
    a, b = np.radians([lat0, lon0]), np.radians([lat1, lon1])
    p = np.array([np.cos(a[0]) * np.cos(a[1]), np.cos(a[0]) * np.sin(a[1]), np.sin(a[0])])
    q = np.array([np.cos(b[0]) * np.cos(b[1]), np.cos(b[0]) * np.sin(b[1]), np.sin(b[0])])
    w = np.arccos(np.clip(p @ q, -1, 1))
    t = np.linspace(0, 1, n)[:, None]
    v = p if w < 1e-9 else (np.sin((1 - t) * w) * p + np.sin(t * w) * q) / np.sin(w)
    lat, lon = np.degrees(np.arcsin(v[:, 2])), np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    cortes = np.where(np.abs(np.diff(lon)) > 180)[0] + 1
    return [(la, lo) for la, lo in zip(np.split(lat, cortes), np.split(lon, cortes))]


pesos = datos[{{peso}}] if {{peso}} else pd.Series(1.0, index=datos.index)
grosor = 0.6 + 2.4 * (pesos - pesos.min()) / max(pesos.max() - pesos.min(), 1e-9)
''' + FIG + r'''dibujar_tierra(ax)
for i, fila in datos.iterrows():
    for la, lo in circulo_maximo(fila[{{lat0}}], fila[{{lon0}}], fila[{{lat1}}], fila[{{lon1}}]):
        ax.plot(*proyectar(lo, la), color={{color}}, linewidth=grosor[i], alpha=0.75, solid_capstyle="round", zorder=3)
for la, lo in [({{lat0}}, {{lon0}}), ({{lat1}}, {{lon1}})]:
    ax.scatter(*proyectar(datos[lo], datos[la]), s=10, color="black", zorder=4)
encuadrar(ax)
''' + PIE_SIN_EJES),
    _t("mapa-burbujas", "Mapa de burbujas", "Mapas", "bubble-map.html", "matplotlib",
       "Un círculo en cada lugar, con un área proporcional a su valor.",
       [_datos("ejemplo_paises.csv"), _p("lat", "Latitud", "columna", "lat", numerica=True),
        _p("lon", "Longitud", "columna", "lon", numerica=True),
        _p("valor", "Valor (área)", "columna", "poblacion", numerica=True),
        _p("grupo", "Un color por", "columna", "continente", opcional=True),
        _p("tamano", "Tamaño de la mayor burbuja", "numero", 600, min=10, max=5000), PALETA, *MAPA_PARAMS]
       + _sin_ejes("mapa_burbujas", alto=8, ancho=16),
       CABEZA_MPL + MAPA_BASE + COLORES_N + r'''d = datos.dropna(subset=[{{valor}}]).sort_values({{valor}}, ascending=False)
escala = {{tamano}} / d[{{valor}}].max()
grupos = list(dict.fromkeys(d[{{grupo}}])) if {{grupo}} else [None]
''' + FIG + r'''dibujar_tierra(ax)
for g, color in zip(grupos, colores_n(len(grupos))):
    parte = d if g is None else d[d[{{grupo}}] == g]
    x, y = proyectar(parte[{{lon}}], parte[{{lat}}])
    ax.scatter(x, y, s=parte[{{valor}}] * escala, color=color, alpha=0.6, edgecolor="white", linewidth=0.4,
               zorder=3, label=None if g is None else str(g))
encuadrar(ax)
leyenda = [ax.scatter([], [], s=v * escala, color="grey", alpha=0.5, label=f"{v:,.0f}".replace(",", " "))
           for v in d[{{valor}}].quantile([0.5, 0.9, 1.0]).round(-3)]
ax.legend(handles=leyenda, title={{valor}}, frameon=False, fontsize="small", loc="lower left", labelspacing=1.5)
''' + PIE_SIN_EJES),
]

# =============================================================================================== flujos
FLUJOS = [
    _t("cuerdas", "Diagrama de cuerdas", "Flujos", "chord-diagram.html", "matplotlib",
       "Los flujos entre elementos dispuestos en círculo: el grosor de cada cuerda es la cantidad.",
       [_datos("ejemplo_flujos.csv"), _p("origen", "Origen", "columna", "origen"),
        _p("destino", "Destino", "columna", "destino"),
        _p("valor", "Cantidad", "columna", "valor", opcional=True, numerica=True), PALETA]
       + _sin_ejes("cuerdas", alto=14, ancho=14),
       CABEZA_MPL + COLORES_N + r'''import numpy as np
from matplotlib.patches import PathPatch, Wedge
from matplotlib.path import Path

d = datos.assign(_v=datos[{{valor}}] if {{valor}} else 1.0)
d = d[d[{{origen}}] != d[{{destino}}]]
nodos = list(dict.fromkeys(list(d[{{origen}}]) + list(d[{{destino}}])))
idx = {n: i for i, n in enumerate(nodos)}
m = np.zeros((len(nodos), len(nodos)))
for a, b, v in zip(d[{{origen}}], d[{{destino}}], d["_v"]):
    m[idx[a], idx[b]] += v
m = m + m.T                                        # cuerdas sin dirección
total, hueco = m.sum(), np.radians(2.5)
escala = (2 * np.pi - hueco * len(nodos)) / total
inicio, a = [], 0.0
for i in range(len(nodos)):
    inicio.append(a)
    a += m[i].sum() * escala + hueco
cursor = list(inicio)
tramo = {}
for i in range(len(nodos)):                        # el trozo de arco que usa cada cuerda en cada extremo
    for j in sorted(range(len(nodos)), key=lambda j: (j - i) % len(nodos)):
        if m[i, j] > 0:
            tramo[(i, j)] = (cursor[i], cursor[i] + m[i, j] * escala)
            cursor[i] += m[i, j] * escala
colores = colores_n(len(nodos))


def arco(t0, t1, r=1.0, n=30):
    t = np.linspace(t0, t1, n)
    return list(zip(r * np.cos(t), r * np.sin(t)))

''' + FIG + r'''for i in range(len(nodos)):
    t0, t1 = inicio[i], inicio[i] + m[i].sum() * escala
    ax.add_patch(Wedge((0, 0), 1.08, np.degrees(t0), np.degrees(t1), width=0.07, color=colores[i]))
    medio = (t0 + t1) / 2
    giro = np.degrees(medio) - (180 if np.pi / 2 < medio % (2 * np.pi) < 3 * np.pi / 2 else 0)
    ax.text(1.14 * np.cos(medio), 1.14 * np.sin(medio), str(nodos[i]), rotation=giro, rotation_mode="anchor",
            ha="left" if giro == np.degrees(medio) else "right", va="center", fontsize="small")
for (i, j), (a0, a1) in tramo.items():
    if i > j:
        continue
    b0, b1 = tramo[(j, i)]
    puntos = arco(a0, a1) + [(0, 0)] + arco(b0, b1)[:1] + arco(b0, b1) + [(0, 0)] + arco(a0, a1)[:1]
    codigos = ([Path.MOVETO] + [Path.LINETO] * 29 + [Path.CURVE3, Path.CURVE3] + [Path.LINETO] * 30
               + [Path.CURVE3, Path.CURVE3])
    ax.add_patch(PathPatch(Path(puntos, codigos), facecolor=colores[i], edgecolor="none", alpha=0.55))
ax.set_xlim(-1.45, 1.45)
ax.set_ylim(-1.45, 1.45)
ax.set_aspect("equal")
''' + PIE_SIN_EJES),
    _t("red", "Red (grafo)", "Flujos", "network.html", "matplotlib",
       "Nodos y enlaces colocados con un algoritmo de fuerzas; el tamaño de cada nodo, según sus enlaces.",
       [_datos("ejemplo_red.csv"), _p("origen", "Origen", "columna", "origen"),
        _p("destino", "Destino", "columna", "destino"),
        _p("valor", "Peso del enlace", "columna", "valor", opcional=True, numerica=True),
        _p("grupo_origen", "Grupo del origen", "columna", "grupo_origen", opcional=True),
        _p("grupo_destino", "Grupo del destino", "columna", "grupo_destino", opcional=True),
        _p("rotulos", "Escribir el nombre de los nodos", "interruptor", True),
        _p("semilla", "Semilla de la disposición", "numero", 3, min=0, max=9999), PALETA]
       + _sin_ejes("red", alto=13, ancho=14),
       CABEZA_MPL + COLORES_N + r'''import numpy as np

nodos = list(dict.fromkeys(list(datos[{{origen}}]) + list(datos[{{destino}}])))
idx = {n: i for i, n in enumerate(nodos)}
n = len(nodos)
pesos = datos[{{valor}}] if {{valor}} else pd.Series(1.0, index=datos.index)
adj = np.zeros((n, n))
for a, b, w in zip(datos[{{origen}}], datos[{{destino}}], pesos):
    adj[idx[a], idx[b]] = adj[idx[b], idx[a]] = 1.0
grupo = {}
if {{grupo_origen}}:
    grupo.update(zip(datos[{{origen}}], datos[{{grupo_origen}}]))
if {{grupo_destino}}:
    grupo.update(zip(datos[{{destino}}], datos[{{grupo_destino}}]))
grupos = list(dict.fromkeys(grupo.get(x) for x in nodos))
tono = dict(zip(grupos, colores_n(len(grupos))))

# disposición por fuerzas (Fruchterman-Reingold): los enlaces atraen y todos los nodos se repelen
rng = np.random.default_rng(int({{semilla}}))
pos = rng.random((n, 2))
k = 1 / np.sqrt(n)
temperatura = 0.1
for _ in range(300):
    dif = pos[:, None, :] - pos[None, :, :]
    dist = np.hypot(dif[..., 0], dif[..., 1]) + 1e-9
    fuerza = (k * k / dist**2 - adj * dist / k)[..., None] * dif
    paso = fuerza.sum(axis=1)
    largo = np.hypot(paso[:, 0], paso[:, 1])[:, None] + 1e-9
    pos += paso / largo * np.minimum(largo, temperatura)
    temperatura *= 0.985
grado = adj.sum(axis=1)
''' + FIG + r'''anchos = 0.4 + 2.0 * (pesos - pesos.min()) / max(pesos.max() - pesos.min(), 1e-9)
for (a, b), w in zip(zip(datos[{{origen}}], datos[{{destino}}]), anchos):
    ax.plot(*zip(pos[idx[a]], pos[idx[b]]), color="#9A9A9A", linewidth=w, alpha=0.6, zorder=1)
ax.scatter(pos[:, 0], pos[:, 1], s=40 + 40 * grado, c=[tono[grupo.get(x)] for x in nodos],
           edgecolor="white", linewidth=0.8, zorder=2)
if {{rotulos}}:
    for x, (px_, py_) in zip(nodos, pos):
        ax.text(px_, py_, str(x), ha="center", va="center", fontsize="x-small", color="white", zorder=3,
                fontweight="bold")
if len(grupos) > 1:
    ax.legend(handles=[plt.Line2D([], [], marker="o", linestyle="", color=c, label=str(g)) for g, c in tono.items()],
              frameon=False, fontsize="small", loc="lower left")
ax.margins(0.12)
ax.set_aspect("equal")
''' + PIE_SIN_EJES),
    _t("sankey", "Sankey", "Flujos", "sankey-diagram.html", "matplotlib",
       "Cantidades que pasan de una etapa a la siguiente; el grosor de cada banda es la cantidad.",
       [_datos("ejemplo_flujos.csv"), _p("origen", "Origen", "columna", "origen"),
        _p("destino", "Destino", "columna", "destino"),
        _p("valor", "Cantidad", "columna", "valor", numerica=True), PALETA]
       + _sin_ejes("sankey", alto=10, ancho=16),
       CABEZA_MPL + COLORES_N + r'''import numpy as np
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path

d = datos.groupby([{{origen}}, {{destino}}], sort=False, as_index=False)[{{valor}}].sum()
nodos = list(dict.fromkeys(list(d[{{origen}}]) + list(d[{{destino}}])))
etapa = {x: 0 for x in nodos}                       # etapa = camino más largo desde una fuente
for _ in range(len(nodos)):
    for a, b in zip(d[{{origen}}], d[{{destino}}]):
        etapa[b] = max(etapa[b], etapa[a] + 1)
entra = d.groupby({{destino}})[{{valor}}].sum()
sale = d.groupby({{origen}})[{{valor}}].sum()
alto_nodo = {x: max(entra.get(x, 0), sale.get(x, 0)) for x in nodos}
n_etapas = max(etapa.values()) + 1
total = max(sum(alto_nodo[x] for x in nodos if etapa[x] == e) for e in range(n_etapas))
hueco = total * 0.04
y0 = {}
for e in range(n_etapas):
    y = 0.0
    for x in [x for x in nodos if etapa[x] == e]:
        y0[x] = y
        y += alto_nodo[x] + hueco
tono = dict(zip(nodos, colores_n(len(nodos))))
ancho_nodo = 0.04 * (n_etapas - 1 or 1)
''' + FIG + r'''sal_y, ent_y = dict(y0), dict(y0)
for _, f in d.iterrows():
    a, b, v = f[{{origen}}], f[{{destino}}], f[{{valor}}]
    xa, xb = etapa[a] + ancho_nodo / 2, etapa[b] - ancho_nodo / 2
    ya, yb = sal_y[a], ent_y[b]
    medio = (xa + xb) / 2
    camino = Path([(xa, ya), (medio, ya), (medio, yb), (xb, yb), (xb, yb + v), (medio, yb + v), (medio, ya + v),
                   (xa, ya + v), (xa, ya)],
                  [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO, Path.CURVE4, Path.CURVE4,
                   Path.CURVE4, Path.CLOSEPOLY])
    ax.add_patch(PathPatch(camino, facecolor=tono[a], edgecolor="none", alpha=0.45))
    sal_y[a] += v
    ent_y[b] += v
for x in nodos:
    ax.add_patch(Rectangle((etapa[x] - ancho_nodo / 2, y0[x]), ancho_nodo, alto_nodo[x], color=tono[x]))
    ultima = etapa[x] == n_etapas - 1
    ax.text(etapa[x] + (-1 if ultima else 1) * ancho_nodo * 0.8, y0[x] + alto_nodo[x] / 2,
            f"{x}  {alto_nodo[x]:g}" if not ultima else f"{alto_nodo[x]:g}  {x}",
            ha="right" if ultima else "left", va="center", fontsize="small")
ax.set_xlim(-0.05, n_etapas - 1 + 0.05)
ax.set_ylim(total + hueco * len(nodos), -hueco)
''' + PIE_SIN_EJES),
    _t("arcos", "Diagrama de arcos", "Flujos", "arc-diagram.html", "matplotlib",
       "Los nodos en una línea y cada enlace como un arco; ordenados por grupo, se ven las comunidades.",
       [_datos("ejemplo_red.csv"), _p("origen", "Origen", "columna", "origen"),
        _p("destino", "Destino", "columna", "destino"),
        _p("valor", "Peso del enlace", "columna", "valor", opcional=True, numerica=True),
        _p("grupo_origen", "Grupo del origen", "columna", "grupo_origen", opcional=True),
        _p("grupo_destino", "Grupo del destino", "columna", "grupo_destino", opcional=True), PALETA]
       + _sin_ejes("arcos", alto=8, ancho=16),
       CABEZA_MPL + COLORES_N + r'''import numpy as np
from matplotlib.patches import Arc

grupo = {}
if {{grupo_origen}}:
    grupo.update(zip(datos[{{origen}}], datos[{{grupo_origen}}]))
if {{grupo_destino}}:
    grupo.update(zip(datos[{{destino}}], datos[{{grupo_destino}}]))
nodos = sorted(dict.fromkeys(list(datos[{{origen}}]) + list(datos[{{destino}}])), key=lambda x: (str(grupo.get(x, "")), str(x)))
x = {n: i for i, n in enumerate(nodos)}
grupos = list(dict.fromkeys(grupo.get(n) for n in nodos))
tono = dict(zip(grupos, colores_n(len(grupos))))
pesos = datos[{{valor}}] if {{valor}} else pd.Series(1.0, index=datos.index)
anchos = 0.5 + 2.5 * (pesos - pesos.min()) / max(pesos.max() - pesos.min(), 1e-9)
grado = pd.concat([datos[{{origen}}], datos[{{destino}}]]).value_counts()
''' + FIG + r'''alto_max = 0
for (a, b), w in zip(zip(datos[{{origen}}], datos[{{destino}}]), anchos):
    xa, xb = sorted((x[a], x[b]))
    ax.add_patch(Arc(((xa + xb) / 2, 0), xb - xa, xb - xa, theta1=0, theta2=180, linewidth=w,
                     color=tono[grupo.get(a)], alpha=0.55))
    alto_max = max(alto_max, (xb - xa) / 2)
ax.scatter(list(x.values()), [0] * len(x), s=[20 + 12 * grado.get(n, 0) for n in nodos],
           c=[tono[grupo.get(n)] for n in nodos], zorder=3)
for n, xi in x.items():
    ax.text(xi, -0.4, str(n), rotation=90, ha="center", va="top", fontsize="x-small")
ax.set_xlim(-1, len(nodos))
ax.set_ylim(-0.25 * alto_max - 2, alto_max + 0.5)
''' + PIE_SIN_EJES),
    _t("haces", "Agrupamiento de aristas (edge bundling)", "Flujos", "hierarchical-edge-bundling.html", "matplotlib",
       "Nodos en círculo ordenados por grupo; las conexiones se curvan siguiendo la jerarquía y forman haces.",
       [_datos("ejemplo_red.csv"), _p("origen", "Origen", "columna", "origen"),
        _p("destino", "Destino", "columna", "destino"),
        _p("grupo_origen", "Grupo del origen", "columna", "grupo_origen"),
        _p("grupo_destino", "Grupo del destino", "columna", "grupo_destino"),
        _p("tension", "Fuerza del agrupamiento (0–1)", "numero", 0.85, min=0, max=1), PALETA]
       + _sin_ejes("haces", alto=14, ancho=14),
       CABEZA_MPL + COLORES_N + r'''import numpy as np

grupo = dict(zip(datos[{{origen}}], datos[{{grupo_origen}}]))
grupo.update(zip(datos[{{destino}}], datos[{{grupo_destino}}]))
grupos = list(dict.fromkeys(sorted(map(str, grupo.values()))))
hojas = sorted(grupo, key=lambda n: (str(grupo[n]), str(n)))
hueco = 1.5                                         # espacio entre grupos, en «hojas»
paso = 2 * np.pi / (len(hojas) + hueco * len(grupos))
angulo, a, previo = {}, 0.0, None
for h in hojas:
    if str(grupo[h]) != previo:
        a += hueco * paso
        previo = str(grupo[h])
    angulo[h] = a
    a += paso
punto = {h: np.array([np.cos(t), np.sin(t)]) for h, t in angulo.items()}
for g in grupos:                                    # el centro de cada grupo, a media altura
    t = np.mean([angulo[h] for h in hojas if str(grupo[h]) == g])
    punto[("g", g)] = 0.5 * np.array([np.cos(t), np.sin(t)])
tono = dict(zip(grupos, colores_n(len(grupos))))


def suavizar(p, veces=5):
    """Curva suave por cortes de esquinas (Chaikin)."""
    for _ in range(veces):
        q = [p[0]]
        for a_, b_ in zip(p[:-1], p[1:]):
            q += [0.75 * a_ + 0.25 * b_, 0.25 * a_ + 0.75 * b_]
        p = np.array(q + [p[-1]])
    return p

''' + FIG + r'''beta = float({{tension}})
for a_, b_ in zip(datos[{{origen}}], datos[{{destino}}]):
    ga, gb = str(grupo[a_]), str(grupo[b_])
    ctrl = [punto[a_], punto[("g", ga)]] + ([np.zeros(2), punto[("g", gb)]] if ga != gb else []) + [punto[b_]]
    ctrl = np.array(ctrl)
    recta = ctrl[0] + np.linspace(0, 1, len(ctrl))[:, None] * (ctrl[-1] - ctrl[0])
    curva = suavizar(beta * ctrl + (1 - beta) * recta)
    ax.plot(curva[:, 0], curva[:, 1], color=tono[ga], alpha=0.45, linewidth=0.9)
for h in hojas:
    t = angulo[h]
    ax.scatter(*punto[h], s=14, color=tono[str(grupo[h])], zorder=3)
    giro = np.degrees(t) - (180 if np.pi / 2 < t < 3 * np.pi / 2 else 0)
    ax.text(1.06 * np.cos(t), 1.06 * np.sin(t), str(h), rotation=giro, rotation_mode="anchor",
            ha="left" if giro == np.degrees(t) else "right", va="center", fontsize="x-small")
ax.legend(handles=[plt.Line2D([], [], color=c, label=g) for g, c in tono.items()], frameon=False,
          fontsize="small", loc="upper left", bbox_to_anchor=(1.0, 1.0))
ax.set_xlim(-1.3, 1.3)
ax.set_ylim(-1.3, 1.3)
ax.set_aspect("equal")
''' + PIE_SIN_EJES),
]

# ======================================================================================== distribución
DISTRIBUCION = [
    _t("densidad", "Densidad", "Distribución", "density-plot.html", "seaborn",
       "La forma de la distribución de una columna, suavizada; una curva por grupo si eliges uno.",
       [_datos("ejemplo.csv"), _p("x", "Columna", "columna", "valor", numerica=True),
        _p("grupo", "Una curva por", "columna", "tratamiento", opcional=True),
        _p("rellenar", "Rellenar bajo la curva", "interruptor", True),
        _p("suavizado", "Suavizado (1 = automático)", "numero", 1, min=0.1, max=5), PALETA]
       + _comunes("densidad", y="Densidad"),
       CABEZA_SNS + COLORES_N + FIG + r'''sns.kdeplot(data=datos, x={{x}}, hue={{grupo}}, fill={{rellenar}}, common_norm=False, alpha=0.35,
            bw_adjust={{suavizado}}, palette={{paleta}} if {{grupo}} else None,
            color=None if {{grupo}} else colores_n(1)[0], linewidth=1.2, ax=ax)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}})
''' + PIE_MPL),
    _t("crestas", "Crestas (ridgeline)", "Distribución", "ridgeline-plot.html", "matplotlib",
       "Una curva de densidad por grupo, apiladas y un poco solapadas: compara muchas distribuciones.",
       [_datos("ejemplo_series.csv"), _p("x", "Valor", "columna", "valor", numerica=True),
        _p("grupo", "Una cresta por", "columna", "serie"),
        _p("solape", "Solapamiento", "numero", 1.6, min=0.5, max=5),
        _p("suavizado", "Suavizado (1 = automático)", "numero", 1, min=0.1, max=5),
        _p("ordenar", "Ordenar por la mediana", "interruptor", True), PALETA]
       + _comunes("crestas", y="", alto=11),
       CABEZA_MPL + COLORES_N + r'''import numpy as np

partes = [(g, p[{{x}}].dropna().to_numpy()) for g, p in datos.groupby({{grupo}}, sort=False)]
if {{ordenar}}:
    partes.sort(key=lambda gp: np.median(gp[1]))
xs = np.linspace(datos[{{x}}].min(), datos[{{x}}].max(), 400)
xs = np.linspace(xs[0] - 0.05 * np.ptp(xs), xs[-1] + 0.05 * np.ptp(xs), 400)
''' + FIG + r'''for i, ((nombre, v), color) in enumerate(zip(partes, colores_n(len(partes)))):
    h = 1.06 * v.std() * len(v) ** (-1 / 5) * {{suavizado}} or 1.0      # regla de Silverman
    dens = np.exp(-((xs[:, None] - v[None, :]) ** 2) / (2 * h * h)).sum(axis=1)
    dens = dens / dens.max() * {{solape}}
    ax.fill_between(xs, i, i + dens, color=color, alpha=0.75, zorder=len(partes) - i, linewidth=0)
    ax.plot(xs, i + dens, color="white", linewidth=1, zorder=len(partes) - i)
ax.set_yticks(range(len(partes)), [str(g) for g, _ in partes])
ax.spines[["left"]].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}})
''' + PIE_MPL),
    _t("enjambre", "Enjambre (beeswarm)", "Distribución", "beeswarm.html", "seaborn",
       "Todos los puntos de cada grupo, apartados para que no se tapen: se ve la forma y cada dato.",
       [_datos("ejemplo.csv"), _p("x", "Grupos", "columna", "tratamiento"),
        _p("y", "Valor", "columna", "valor", numerica=True),
        _p("color_por", "Un color por", "columna", "grupo", opcional=True),
        _p("tamano", "Tamaño de los puntos", "numero", 4, min=1, max=15), PALETA] + _comunes("enjambre"),
       CABEZA_SNS + FIG + r'''sns.swarmplot(data=datos, x={{x}}, y={{y}}, hue={{color_por}} or {{x}}, palette={{paleta}}, size={{tamano}},
              legend=bool({{color_por}}), ax=ax)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
if {{color_por}}:
    ax.legend(title={{color_por}}, frameon=False)
''' + PIE_MPL),
]

# ========================================================================================= correlación
CORRELACION = [
    _t("mapa-calor", "Mapa de calor", "Correlación", "heatmap.html", "seaborn",
       "Una tabla de colores: filas × columnas, con el valor medio de cada cruce.",
       [_datos("ejemplo.csv"), _p("x", "Columnas del mapa", "columna", "tiempo"),
        _p("y", "Filas del mapa", "columna", "grupo"),
        _p("valor", "Valor", "columna", "valor", numerica=True),
        _p("anotar", "Escribir el valor en cada celda", "interruptor", True),
        _p("mapa_color", "Mapa de color", "opcion", "viridis",
           opciones=["viridis", "magma", "cividis", "Blues", "YlOrRd", "RdBu_r", "vlag"])] + _comunes("mapa_calor"),
       CABEZA_SNS + r'''tabla = datos.pivot_table(index={{y}}, columns={{x}}, values={{valor}}, aggfunc="mean")
''' + FIG + r'''sns.heatmap(tabla, annot={{anotar}}, fmt=".1f", cmap={{mapa_color}}, linewidths=0.5,
            cbar_kws={"label": {{valor}}, "shrink": 0.8}, annot_kws={"fontsize": "x-small"}, ax=ax)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
''' + PIE_MPL.replace('ax.spines[["top", "right"]].set_visible(False)\n', "")),
    _t("correlograma", "Correlograma (matriz de dispersión)", "Correlación", "correlogram.html", "seaborn",
       "Todas las parejas de columnas numéricas: dispersión fuera de la diagonal y densidad en ella.",
       [_datos("ejemplo.csv"), _p("columnas", "Columnas", "columnas", ["valor", "peso", "altura"], numerica=True),
        _p("grupo", "Un color por", "columna", "grupo", opcional=True),
        _p("triangulo", "Solo el triángulo inferior", "interruptor", True), PALETA]
       + _sin_ejes("correlograma", alto=14, ancho=14),
       CABEZA_SNS + r'''g = sns.pairplot(datos[{{columnas}} + ([{{grupo}}] if {{grupo}} else [])], hue={{grupo}},
                 palette={{paleta}} if {{grupo}} else None, corner={{triangulo}}, diag_kind="kde",
                 plot_kws={"s": 14, "alpha": 0.7, "linewidth": 0})
fig = g.figure
''' + PIE_FIGURA),
    _t("burbujas", "Burbujas", "Correlación", "bubble-chart.html", "matplotlib",
       "Dispersión de dos columnas en la que el área de cada punto representa una tercera.",
       [_datos("ejemplo.csv"), _p("x", "Eje x", "columna", "peso", numerica=True),
        _p("y", "Eje y", "columna", "altura", numerica=True),
        _p("tamano_por", "Tamaño según", "columna", "valor", numerica=True),
        _p("grupo", "Un color por", "columna", "grupo", opcional=True),
        _p("tamano", "Tamaño de la mayor burbuja", "numero", 400, min=10, max=3000), PALETA] + _comunes("burbujas"),
       CABEZA_MPL + COLORES_N + r'''t = datos[{{tamano_por}}]
area = 10 + ({{tamano}} - 10) * (t - t.min()) / max(t.max() - t.min(), 1e-9)
grupos = [(None, datos)] if not {{grupo}} else list(datos.groupby({{grupo}}, sort=False))
''' + FIG + r'''for (nombre, parte), color in zip(grupos, colores_n(len(grupos))):
    ax.scatter(parte[{{x}}], parte[{{y}}], s=area[parte.index], color=color, alpha=0.55, edgecolor="white",
               linewidth=0.6, label=None if nombre is None else str(nombre))
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
leyenda = ax.legend(title={{grupo}}, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0)) if {{grupo}} else None
refs = t.quantile([0.1, 0.5, 1.0]).round(1)
tam = [ax.scatter([], [], s=10 + ({{tamano}} - 10) * (v - t.min()) / max(t.max() - t.min(), 1e-9), color="grey",
                  alpha=0.4, label=f"{v:g}") for v in refs]
ax.legend(handles=tam, title={{tamano_por}}, frameon=False, loc="lower left", bbox_to_anchor=(1.0, 0.0),
          labelspacing=1.2)
if leyenda:
    ax.add_artist(leyenda)
''' + PIE_MPL),
    _t("dispersion-conectada", "Dispersión conectada", "Correlación", "connected-scatterplot.html", "matplotlib",
       "Cómo cambian dos variables a la vez a lo largo del tiempo: puntos unidos en orden.",
       [_datos("ejemplo.csv"), _p("x", "Eje x", "columna", "valor", numerica=True),
        _p("y", "Eje y", "columna", "peso", numerica=True),
        _p("orden", "Orden (tiempo)", "columna", "tiempo"),
        _p("grupo", "Una línea por", "columna", "grupo", opcional=True),
        _p("rotular", "Rotular el primer y el último punto", "interruptor", True), PALETA]
       + _comunes("dispersion_conectada"),
       CABEZA_MPL + COLORES_N + r'''claves = ([{{grupo}}] if {{grupo}} else []) + [{{orden}}]
media = datos.groupby(claves, sort=True)[[{{x}}, {{y}}]].mean().reset_index()
grupos = [(None, media)] if not {{grupo}} else list(media.groupby({{grupo}}, sort=False))
''' + FIG + r'''for (nombre, parte), color in zip(grupos, colores_n(len(grupos))):
    parte = parte.sort_values({{orden}})
    ax.plot(parte[{{x}}], parte[{{y}}], "-o", color=color, markersize=4, linewidth=1.2,
            label=None if nombre is None else str(nombre))
    if {{rotular}} and len(parte):
        for fila in (parte.iloc[0], parte.iloc[-1]):
            ax.annotate(str(fila[{{orden}}]), (fila[{{x}}], fila[{{y}}]), xytext=(4, 4), textcoords="offset points",
                        fontsize="x-small", color=color)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
if {{grupo}}:
    ax.legend(title={{grupo}}, frameon=False)
''' + PIE_MPL),
    _t("densidad-2d", "Densidad 2D", "Correlación", "2d-density-chart.html", "seaborn",
       "Dónde se concentran los puntos de dos columnas numéricas: contornos o hexágonos.",
       [_datos("ejemplo_puntos.csv"), _p("x", "Eje x", "columna", "lon", numerica=True),
        _p("y", "Eje y", "columna", "lat", numerica=True),
        _p("estilo", "Estilo", "opcion", "Contornos rellenos", opciones=["Contornos rellenos", "Contornos", "Hexágonos"]),
        _p("puntos", "Mostrar también los puntos", "interruptor", False),
        _p("mapa_color", "Mapa de color", "opcion", "mako_r",
           opciones=["mako_r", "rocket_r", "viridis", "magma", "Blues", "Greens"])] + _comunes("densidad_2d"),
       CABEZA_SNS + FIG + r'''if {{estilo}} == "Hexágonos":
    hb = ax.hexbin(datos[{{x}}], datos[{{y}}], gridsize=30, mincnt=1, cmap={{mapa_color}}, linewidths=0.2)
    fig.colorbar(hb, ax=ax, label="Puntos").outline.set_visible(False)
else:
    sns.kdeplot(data=datos, x={{x}}, y={{y}}, fill={{estilo}} == "Contornos rellenos", cmap={{mapa_color}},
                levels=12, thresh=0.03, ax=ax)
if {{puntos}}:
    ax.scatter(datos[{{x}}], datos[{{y}}], s=3, color="black", alpha=0.3)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
''' + PIE_MPL),
]

# ============================================================================================= ranking
RANKING = [
    _t("radar", "Radar (araña)", "Ranking", "spider-or-radar-chart.html", "matplotlib",
       "Varias variables en ejes que salen del centro; un polígono por grupo o por fila.",
       [_datos("ejemplo_puntuaciones.csv"),
        _p("columnas", "Variables", "columnas", ["Proteína", "Lípidos", "Carbohidratos", "Fibra", "Humedad", "Cenizas"],
           numerica=True),
        _p("grupo", "Un polígono por", "columna", "grupo", ayuda="Se dibuja la media de cada grupo."),
        _p("normalizar", "Escalar cada variable de 0 a 1", "interruptor", True), PALETA]
       + _sin_ejes("radar", alto=12, ancho=14),
       CABEZA_MPL + COLORES_N + r'''import numpy as np

media = datos.groupby({{grupo}}, sort=False)[{{columnas}}].mean()
if {{normalizar}}:
    media = media / datos[{{columnas}}].max()
angulos = np.linspace(0, 2 * np.pi, len({{columnas}}), endpoint=False).tolist()
fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54), subplot_kw={"projection": "polar"})
for (nombre, fila), color in zip(media.iterrows(), colores_n(len(media))):
    valores = fila.tolist()
    ax.plot(angulos + angulos[:1], valores + valores[:1], color=color, linewidth=1.5, label=str(nombre))
    ax.fill(angulos + angulos[:1], valores + valores[:1], color=color, alpha=0.2)
ax.set_xticks(angulos, {{columnas}})
ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)
ax.tick_params(axis="y", labelsize="x-small", colors="grey")
ax.spines["polar"].set_visible(False)
ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.25, 1.1))
ax.set_title({{titulo}})
fig.tight_layout()
os.makedirs(os.path.dirname({{salida}}) or ".", exist_ok=True)
fig.savefig({{salida}}, bbox_inches="tight", dpi=300)
plt.show()
'''),
    _t("nube-palabras", "Nube de palabras", "Ranking", "wordcloud.html", "matplotlib",
       "Palabras con un tamaño según su frecuencia, colocadas en espiral sin solaparse.",
       [_datos("ejemplo_palabras.csv"), _p("palabra", "Palabra", "columna", "palabra"),
        _p("frecuencia", "Frecuencia", "columna", "frecuencia", numerica=True),
        _p("maximo", "Máximo de palabras", "numero", 60, min=5, max=400),
        _p("verticales", "Proporción de palabras en vertical (0–1)", "numero", 0.2, min=0, max=1),
        _p("letra_max", "Letra de la palabra mayor (pt)", "numero", 40, min=8, max=150),
        _p("semilla", "Semilla", "numero", 7, min=0, max=9999), PALETA] + _sin_ejes("nube_palabras", alto=10, ancho=16),
       CABEZA_MPL + COLORES_N + r'''import numpy as np
from matplotlib.transforms import Bbox

d = datos.groupby({{palabra}})[{{frecuencia}}].sum().sort_values(ascending=False).head(int({{maximo}}))
rng = np.random.default_rng(int({{semilla}}))
''' + FIG + r'''ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
fig.canvas.draw()
caja_ejes = ax.get_window_extent()
cx, cy = caja_ejes.x0 + caja_ejes.width / 2, caja_ejes.y0 + caja_ejes.height / 2
ocupadas = []
fmin, fmax = d.min(), d.max()
colores = colores_n(max(2, min(6, len(d))))
for i, (palabra, f) in enumerate(d.items()):
    tam = 6 + ({{letra_max}} - 6) * np.sqrt((f - fmin) / max(fmax - fmin, 1e-9))
    giro = 90 if rng.random() < {{verticales}} else 0
    t = ax.text(0.5, 0.5, str(palabra), fontsize=tam, rotation=giro, ha="center", va="center",
                color=colores[i % len(colores)], fontweight="bold")
    caja = t.get_window_extent().expanded(1.04, 1.08)
    w, h = caja.width, caja.height
    puesto = False
    for paso in range(4000):                       # espiral de Arquímedes desde el centro
        a = 0.25 * paso
        r = 0.6 * a
        x, y = cx + r * np.cos(a) * caja_ejes.width / caja_ejes.height, cy + r * np.sin(a)
        c = Bbox.from_bounds(x - w / 2, y - h / 2, w, h)
        if (c.x0 < caja_ejes.x0 or c.x1 > caja_ejes.x1 or c.y0 < caja_ejes.y0 or c.y1 > caja_ejes.y1):
            if r > max(caja_ejes.width, caja_ejes.height):
                break
            continue
        if not any(c.overlaps(o) for o in ocupadas):
            ocupadas.append(c)
            t.set_position(ax.transAxes.inverted().transform((x, y)))
            t.set_transform(ax.transAxes)
            puesto = True
            break
    if not puesto:
        t.remove()
''' + PIE_SIN_EJES),
    _t("paralelas", "Coordenadas paralelas", "Ranking", "parallel-plot.html", "matplotlib",
       "Cada fila es una línea que cruza un eje por variable: muestra perfiles y grupos.",
       [_datos("ejemplo_puntuaciones.csv"),
        _p("columnas", "Variables", "columnas", ["Proteína", "Lípidos", "Carbohidratos", "Fibra", "Humedad", "Cenizas"],
           numerica=True),
        _p("grupo", "Un color por", "columna", "grupo", opcional=True),
        _p("normalizar", "Escalar cada eje de su mínimo a su máximo", "interruptor", True), PALETA]
       + _sin_ejes("paralelas", alto=9, ancho=16),
       CABEZA_MPL + COLORES_N + r'''import numpy as np

valores = datos[{{columnas}}].astype(float)
minimo, maximo = valores.min(), valores.max()
if {{normalizar}}:
    valores = (valores - minimo) / (maximo - minimo).replace(0, 1)
grupos = list(dict.fromkeys(datos[{{grupo}}])) if {{grupo}} else [None]
tono = dict(zip(grupos, colores_n(len(grupos))))
xs = np.arange(len({{columnas}}))
''' + FIG + r'''for i, fila in valores.iterrows():
    g = datos.at[i, {{grupo}}] if {{grupo}} else None
    ax.plot(xs, fila.to_numpy(), color=tono[g], alpha=0.7, linewidth=1.3)
for x in xs:
    ax.axvline(x, color="#666666", linewidth=0.8, zorder=0)
    if {{normalizar}}:
        c = {{columnas}}[x]
        ax.text(x, -0.04, f"{minimo[c]:g}", ha="center", va="top", fontsize="x-small", color="grey")
        ax.text(x, 1.04, f"{maximo[c]:g}", ha="center", va="bottom", fontsize="x-small", color="grey")
ax.set_xticks(xs, {{columnas}})
ax.set_yticks([])
ax.spines[["left", "bottom"]].set_visible(False)
ax.tick_params(axis="x", length=0, pad=14)
if {{grupo}}:
    ax.legend(handles=[plt.Line2D([], [], color=c, label=str(g)) for g, c in tono.items()], frameon=False,
              loc="upper left", bbox_to_anchor=(1.0, 1.0), title={{grupo}})
''' + PIE_MPL),
    _t("piruleta", "Piruleta (lollipop)", "Ranking", "lollipop-plot.html", "matplotlib",
       "Un palito con un punto por categoría, ordenados: un ranking más ligero que las barras.",
       [_datos("ejemplo_paises.csv"), _p("x", "Categorías", "columna", "pais"),
        _p("y", "Valor", "columna", "poblacion", numerica=True),
        _p("maximo", "Mostrar las primeras", "numero", 15, min=2, max=200),
        _p("color", "Color", "color", "primario")] + _comunes("piruleta", alto=10),
       CABEZA_MPL + r'''serie = datos.groupby({{x}})[{{y}}].sum().sort_values(ascending=False).head(int({{maximo}}))[::-1]
divisor, unidad = next(((d, u) for d, u in [(1e9, "miles de millones"), (1e6, "millones"), (1e3, "miles")]
                        if serie.abs().max() >= 10 * d), (1, ""))
serie = serie / divisor
''' + FIG + r'''ax.hlines(range(len(serie)), 0, serie.values, color={{color}}, linewidth=1.5, alpha=0.6)
ax.scatter(serie.values, range(len(serie)), color={{color}}, s=40, zorder=3)
ax.set_yticks(range(len(serie)), [str(i) for i in serie.index])
ax.set_xlim(0, serie.max() * 1.08)
ax.set_xlabel({{etiqueta_y}} or ({{y}} + (f" ({unidad})" if unidad else "")))
ax.set_ylabel({{etiqueta_x}})
''' + PIE_MPL),
    _t("barras-circulares", "Barras circulares", "Ranking", "circular-barplot.html", "matplotlib",
       "Barras dispuestas en círculo, con un color por grupo: muchas categorías en poco espacio.",
       [_datos("ejemplo_jerarquia.csv"), _p("x", "Categorías", "columna", "subarea"),
        _p("y", "Valor", "columna", "publicaciones", numerica=True),
        _p("grupo", "Un color por", "columna", "area", opcional=True),
        _p("ordenar", "Ordenar de mayor a menor dentro de cada grupo", "interruptor", True), PALETA]
       + _sin_ejes("barras_circulares", alto=14, ancho=14),
       CABEZA_MPL + COLORES_N + r'''import numpy as np

d = datos.groupby(([{{grupo}}] if {{grupo}} else []) + [{{x}}], sort=False)[{{y}}].sum().reset_index()
if {{ordenar}}:
    d = d.sort_values(([{{grupo}}] if {{grupo}} else []) + [{{y}}], ascending=[True] * bool({{grupo}}) + [False])
grupos = list(dict.fromkeys(d[{{grupo}}])) if {{grupo}} else [None]
tono = dict(zip(grupos, colores_n(len(grupos))))
filas, previo = [], object()                       # deja un hueco entre grupos
for _, f in d.iterrows():
    g = f[{{grupo}}] if {{grupo}} else None
    if g != previo and filas:
        filas.append(None)
    previo = g
    filas.append(f)
angulos = np.linspace(0, 2 * np.pi, len(filas), endpoint=False)
ancho = 2 * np.pi / len(filas) * 0.9
fondo = d[{{y}}].max() * 0.6
fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54), subplot_kw={"projection": "polar"})
for a, f in zip(angulos, filas):
    if f is None:
        continue
    g = f[{{grupo}}] if {{grupo}} else None
    ax.bar(a, f[{{y}}], width=ancho, bottom=fondo, color=tono[g], edgecolor="white", linewidth=0.5)
    giro = np.degrees(a)
    alinea = "left"
    if 90 < giro < 270:
        giro, alinea = giro + 180, "right"
    ax.text(a, fondo + f[{{y}}] + d[{{y}}].max() * 0.04, str(f[{{x}}]), rotation=giro,
            rotation_mode="anchor", ha=alinea, va="center", fontsize="x-small")
ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)
ax.set_ylim(0, fondo + d[{{y}}].max() * 1.5)
ax.axis("off")
if {{grupo}}:
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c, label=str(g)) for g, c in tono.items()],
              frameon=False, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=min(len(tono), 4), fontsize="small")
ax.set_title({{titulo}})
fig.tight_layout()
os.makedirs(os.path.dirname({{salida}}) or ".", exist_ok=True)
fig.savefig({{salida}}, bbox_inches="tight", dpi=300)
plt.show()
'''),
    _t("tabla", "Tabla", "Ranking", "table.html", "matplotlib",
       "Una tabla con formato, lista para el documento: encabezado de color y filas alternas.",
       [_datos("ejemplo_puntuaciones.csv"),
        _p("columnas", "Columnas (vacío = todas)", "columnas", [], opcional=True),
        _p("ordenar_por", "Ordenar por", "columna", "", opcional=True),
        _p("descendente", "De mayor a menor", "interruptor", True),
        _p("maximo", "Máximo de filas", "numero", 15, min=1, max=200),
        _p("decimales", "Decimales", "numero", 1, min=0, max=6),
        _p("color", "Color del encabezado", "color", "primario")] + _sin_ejes("tabla", alto=9, ancho=16),
       CABEZA_MPL + r'''d = datos[{{columnas}}] if {{columnas}} else datos
if {{ordenar_por}}:
    d = d.sort_values({{ordenar_por}}, ascending=not {{descendente}})
d = d.head(int({{maximo}}))
texto = d.apply(lambda c: c.map(lambda v: f"{v:,.{int({{decimales}})}f}" if isinstance(v, float) else str(v)))
''' + FIG + r'''tabla = ax.table(cellText=texto.values, colLabels=list(d.columns), loc="center", cellLoc="center")
tabla.auto_set_font_size(False)
tabla.set_fontsize({{letra}})
tabla.scale(1, 1.35)
tabla.auto_set_column_width(list(range(len(d.columns))))
for (fila, col), celda in tabla.get_celld().items():
    celda.set_edgecolor("white")
    if fila == 0:
        celda.set_facecolor({{color}})
        celda.set_text_props(color="white", fontweight="bold")
    else:
        celda.set_facecolor("#F2F2F2" if fila % 2 else "white")
''' + PIE_SIN_EJES),
]

# ================================================================================== partes de un todo
PARTES = [
    _t("mapa-arbol", "Mapa de árbol (treemap)", "Partes de un todo", "treemap.html", "matplotlib",
       "Rectángulos de área proporcional al valor, anidados por grupo.",
       [_datos("ejemplo_jerarquia.csv"), _p("grupo", "Grupo", "columna", "area", opcional=True),
        _p("x", "Elemento", "columna", "subarea"),
        _p("y", "Valor", "columna", "publicaciones", numerica=True), PALETA]
       + _sin_ejes("mapa_arbol", alto=10, ancho=16),
       CABEZA_MPL + COLORES_N + r'''from matplotlib.patches import Rectangle


def squarify(valores, x, y, w, h):
    """Rectángulos casi cuadrados (algoritmo «squarified» de Bruls, Huizing y van Wijk)."""
    total = sum(valores)
    areas = [v * w * h / total for v in valores]
    rects = []
    while areas:
        lado = min(w, h)
        fila = [areas[0]]
        def peor(f):
            s = sum(f)
            return max(max(lado * lado * a / (s * s), s * s / (lado * lado * a)) for a in f)
        while len(fila) < len(areas) and peor(fila + [areas[len(fila)]]) <= peor(fila):
            fila.append(areas[len(fila)])
        s = sum(fila)
        if w >= h:                                   # columna a la izquierda
            ancho_f, yy = s / h, y
            for a in fila:
                rects.append((x, yy, ancho_f, a / ancho_f))
                yy += a / ancho_f
            x, w = x + ancho_f, w - ancho_f
        else:                                        # fila abajo
            alto_f, xx = s / w, x
            for a in fila:
                rects.append((xx, y, a / alto_f, alto_f))
                xx += a / alto_f
            y, h = y + alto_f, h - alto_f
        areas = areas[len(fila):]
    return rects


d = datos.groupby(([{{grupo}}] if {{grupo}} else []) + [{{x}}], sort=False)[{{y}}].sum().reset_index()
d = d[d[{{y}}] > 0]
if {{grupo}}:
    tot = d.groupby({{grupo}}, sort=False)[{{y}}].sum().sort_values(ascending=False)
else:
    tot = pd.Series({None: d[{{y}}].sum()})
tono = dict(zip(tot.index, colores_n(len(tot))))
''' + FIG + r'''for (gx, gy, gw, gh), g in zip(squarify(list(tot.values), 0, 0, 100, 100), tot.index):
    parte = (d if g is None else d[d[{{grupo}}] == g]).sort_values({{y}}, ascending=False)
    for (x, y, w, h), (_, f) in zip(squarify(list(parte[{{y}}]), gx, gy, gw, gh), parte.iterrows()):
        caja = ax.add_patch(Rectangle((x, y), w, h, facecolor=tono[g], edgecolor="white", linewidth=1.2, alpha=0.9))
        if w > 6 and h > 4:
            ax.text(x + 1, y + h - 1, str(f[{{x}}]) + "\n" + format(f[{{y}}], "g"), ha="left", va="top", fontsize="x-small",
                    color="white", clip_path=caja, clip_on=True)
    ax.add_patch(Rectangle((gx, gy), gw, gh, fill=False, edgecolor="white", linewidth=3))
    if g is not None:
        ax.text(gx + gw - 1, gy + 1, str(g), ha="right", va="bottom", fontsize="small", color="white",
                fontweight="bold")
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
''' + PIE_SIN_EJES),
    _t("dona", "Dona", "Partes de un todo", "doughnut-plot.html", "matplotlib",
       "Proporciones de un total en un anillo, con el total en el centro.",
       [_datos("ejemplo_jerarquia.csv"), _p("x", "Categorías", "columna", "area"),
        _p("y", "Valor", "columna", "publicaciones", numerica=True),
        _p("maximo", "Categorías como máximo (el resto, «Otros»)", "numero", 6, min=2, max=30),
        _p("grosor", "Grosor del anillo (0–1)", "numero", 0.35, min=0.05, max=1), PALETA]
       + _sin_ejes("dona", alto=11, ancho=14),
       CABEZA_MPL + COLORES_N + r'''serie = datos.groupby({{x}})[{{y}}].sum().sort_values(ascending=False)
n = int({{maximo}})
if len(serie) > n:
    serie = pd.concat([serie.iloc[:n - 1], pd.Series({"Otros": serie.iloc[n - 1:].sum()})])
''' + FIG + r'''ax.pie(serie.values, labels=[str(i) for i in serie.index], colors=colores_n(len(serie)), startangle=90,
       counterclock=False, autopct="%1.0f %%", pctdistance=1 - {{grosor}} / 2,
       wedgeprops={"width": {{grosor}}, "edgecolor": "white", "linewidth": 1.5},
       textprops={"fontsize": "small"})
ax.text(0, 0, format(serie.sum(), ",.0f") + "\n" + str({{y}}), ha="center", va="center",
        fontsize="medium", fontweight="bold")
ax.set_aspect("equal")
''' + PIE_SIN_EJES),
    _t("pastel", "Pastel (sectores)", "Partes de un todo", "pie-plot.html", "matplotlib",
       "Proporciones de un total; mejor con pocas categorías (el resto se agrupa en «Otros»).",
       [_datos("ejemplo_jerarquia.csv"), _p("x", "Categorías", "columna", "area"),
        _p("y", "Valor", "columna", "publicaciones", numerica=True),
        _p("maximo", "Categorías como máximo (el resto, «Otros»)", "numero", 6, min=2, max=30), PALETA]
       + _sin_ejes("pastel", alto=11, ancho=14),
       CABEZA_MPL + COLORES_N + r'''serie = datos.groupby({{x}})[{{y}}].sum().sort_values(ascending=False)
n = int({{maximo}})
if len(serie) > n:
    serie = pd.concat([serie.iloc[:n - 1], pd.Series({"Otros": serie.iloc[n - 1:].sum()})])
''' + FIG + r'''ax.pie(serie.values, labels=[str(i) for i in serie.index], colors=colores_n(len(serie)), startangle=90,
       counterclock=False, autopct="%1.0f %%", wedgeprops={"edgecolor": "white", "linewidth": 1.5},
       textprops={"fontsize": "small"})
ax.set_aspect("equal")
''' + PIE_SIN_EJES),
    _t("dendrograma", "Dendrograma", "Partes de un todo", "dendrogram.html", "matplotlib",
       "Agrupamiento jerárquico de las filas según sus columnas numéricas (necesita scipy).",
       [_datos("ejemplo_puntuaciones.csv"), _p("etiqueta", "Nombre de cada fila", "columna", "muestra"),
        _p("columnas", "Variables", "columnas", ["Proteína", "Lípidos", "Carbohidratos", "Fibra", "Humedad", "Cenizas"],
           numerica=True),
        _p("metodo", "Método", "opcion", "ward", opciones=["ward", "average", "complete", "single"]),
        _p("estandarizar", "Estandarizar las variables", "interruptor", True),
        _p("grupos", "Colorear este número de grupos", "numero", 3, min=1, max=20),
        _p("horizontal", "Horizontal", "interruptor", True), PALETA] + _comunes("dendrograma", x="", y="Distancia"),
       CABEZA_MPL + COLORES_N + r'''from scipy.cluster import hierarchy

x = datos[{{columnas}}].astype(float)
if {{estandarizar}}:
    x = (x - x.mean()) / x.std(ddof=0).replace(0, 1)
enlace = hierarchy.linkage(x.to_numpy(), method={{metodo}})
k = int({{grupos}})
corte = enlace[-(k - 1), 2] if 1 < k <= len(x) else 0
hierarchy.set_link_color_palette([c if isinstance(c, str) else "#%02x%02x%02x" % tuple(int(255 * v) for v in c[:3])
                                  for c in colores_n(max(k, 1))])
''' + FIG + r'''hierarchy.dendrogram(enlace, labels=datos[{{etiqueta}}].astype(str).tolist(), ax=ax,
                     orientation="left" if {{horizontal}} else "top", color_threshold=corte,
                     above_threshold_color="#888888", leaf_font_size={{letra}})
hierarchy.set_link_color_palette(None)
if {{horizontal}}:
    ax.set_xlabel({{etiqueta_y}})
    ax.spines[["left"]].set_visible(False)
else:
    ax.set_ylabel({{etiqueta_y}})
''' + PIE_MPL),
    _t("empaquetado-circular", "Empaquetado circular", "Partes de un todo", "circle-packing.html", "matplotlib",
       "Círculos de área proporcional al valor, agrupados dentro de otros círculos.",
       [_datos("ejemplo_jerarquia.csv"), _p("grupo", "Grupo", "columna", "area", opcional=True),
        _p("x", "Elemento", "columna", "subarea"),
        _p("y", "Valor", "columna", "publicaciones", numerica=True), PALETA]
       + _sin_ejes("empaquetado_circular", alto=14, ancho=14),
       CABEZA_MPL + COLORES_N + r'''import numpy as np
from matplotlib.patches import Circle


def empaquetar(radios):
    """Coloca círculos tangentes sin solaparse, lo más cerca posible del centro."""
    pos = []
    for r in radios:
        if not pos:
            pos.append((0.0, 0.0, r))
            continue
        candidatos = [(pos[0][2] + r, 0.0)] if len(pos) == 1 else []
        for i, (x1, y1, r1) in enumerate(pos):
            for x2, y2, r2 in pos[i + 1:]:
                a, b = r1 + r, r2 + r                       # tangente a los dos
                dx, dy = x2 - x1, y2 - y1
                dist = np.hypot(dx, dy)
                if dist == 0 or dist > a + b:
                    continue
                m = (a * a - b * b + dist * dist) / (2 * dist)
                h = np.sqrt(max(a * a - m * m, 0))
                bx, by = x1 + m * dx / dist, y1 + m * dy / dist
                candidatos += [(bx + h * dy / dist, by - h * dx / dist), (bx - h * dy / dist, by + h * dx / dist)]
        validos = [c for c in candidatos if all(np.hypot(c[0] - px, c[1] - py) >= pr + r - 1e-9 for px, py, pr in pos)]
        pos.append((*min(validos, key=lambda c: np.hypot(*c)), r))
    cx = sum(x * r * r for x, _, r in pos) / sum(r * r for *_, r in pos)
    cy = sum(y * r * r for _, y, r in pos) / sum(r * r for *_, r in pos)
    pos = [(x - cx, y - cy, r) for x, y, r in pos]
    return pos, max(np.hypot(x, y) + r for x, y, r in pos)


d = datos.groupby(([{{grupo}}] if {{grupo}} else []) + [{{x}}], sort=False)[{{y}}].sum().reset_index()
d = d[d[{{y}}] > 0]
grupos = list(d.groupby({{grupo}}, sort=False)) if {{grupo}} else [(None, d)]
internos = []
for g, parte in grupos:
    parte = parte.sort_values({{y}}, ascending=False)
    pos, radio = empaquetar(list(np.sqrt(parte[{{y}}].to_numpy())))
    internos.append((g, parte, pos, radio * 1.06))
orden = sorted(range(len(internos)), key=lambda i: -internos[i][3])
externos, total = empaquetar([internos[i][3] for i in orden])
tono = dict(zip([g for g, *_ in internos], colores_n(len(internos))))
''' + FIG + r'''for i, (ox, oy, orad) in zip(orden, externos):
    g, parte, pos, _ = internos[i]
    ax.add_patch(Circle((ox, oy), orad, facecolor=tono[g], alpha=0.15, edgecolor=tono[g]))
    for (x, y, r), (_, f) in zip(pos, parte.iterrows()):
        hoja = ax.add_patch(Circle((ox + x, oy + y), r, facecolor=tono[g], alpha=0.85, edgecolor="white"))
        if r > total * 0.07:
            ax.text(ox + x, oy + y, str(f[{{x}}]) + "\n" + format(f[{{y}}], "g"), ha="center", va="center", fontsize="x-small",
                    color="white", clip_path=hoja, clip_on=True)
    if g is not None:
        ax.text(ox, oy + orad, str(g), ha="center", va="bottom", fontsize="small", fontweight="bold", color=tono[g],
                zorder=5, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1})
ax.set_xlim(-total * 1.05, total * 1.05)
ax.set_ylim(-total * 1.05, total * 1.12)
ax.set_aspect("equal")
''' + PIE_SIN_EJES),
    _t("gofre", "Gofre (waffle)", "Partes de un todo", "waffle.html", "matplotlib",
       "Una cuadrícula de 100 casillas coloreadas según el porcentaje de cada categoría.",
       [_datos("ejemplo_jerarquia.csv"), _p("x", "Categorías", "columna", "area"),
        _p("y", "Valor", "columna", "publicaciones", numerica=True),
        _p("filas", "Filas de la cuadrícula", "numero", 10, min=2, max=50),
        _p("columnas_n", "Columnas de la cuadrícula", "numero", 10, min=2, max=50), PALETA]
       + _sin_ejes("gofre", alto=10, ancho=14),
       CABEZA_MPL + COLORES_N + r'''import numpy as np
from matplotlib.patches import FancyBboxPatch

serie = datos.groupby({{x}})[{{y}}].sum().sort_values(ascending=False)
casillas = int({{filas}}) * int({{columnas_n}})
exacto = serie / serie.sum() * casillas
cuenta = np.floor(exacto).astype(int)
for i in (exacto - cuenta).sort_values(ascending=False).index[: casillas - cuenta.sum()]:
    cuenta[i] += 1                                   # resto mayor: la suma da exactamente las casillas
colores = colores_n(len(serie))
''' + FIG + r'''k = 0
for (nombre, n), color in zip(cuenta.items(), colores):
    for _ in range(n):
        fila, col = divmod(k, int({{columnas_n}}))
        ax.add_patch(FancyBboxPatch((col + 0.08, int({{filas}}) - fila - 1 + 0.08), 0.84, 0.84,
                                    boxstyle="round,pad=0,rounding_size=0.12", color=color))
        k += 1
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c, label=f"{i} ({n / casillas:.0%})")
                   for (i, n), c in zip(cuenta.items(), colores)],
          frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize="small")
ax.set_xlim(0, int({{columnas_n}}))
ax.set_ylim(0, int({{filas}}))
ax.set_aspect("equal")
''' + PIE_SIN_EJES),
]

# ============================================================================================ evolución
FECHAS = r'''import matplotlib.dates as mdates

if not pd.api.types.is_numeric_dtype(datos[{{x}}]):
    try:
        datos[{{x}}] = pd.to_datetime(datos[{{x}}])
    except (ValueError, TypeError):
        pass
'''
EJE_FECHAS = r'''if pd.api.types.is_datetime64_any_dtype(datos[{{x}}]):
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
'''
EVOLUCION = [
    _t("area", "Área", "Evolución", "area-chart.html", "matplotlib",
       "Evolución de un total, con el área bajo la línea coloreada.",
       [_datos("ejemplo_series.csv"), _p("x", "Eje x (tiempo)", "columna", "fecha"),
        _p("y", "Valor", "columna", "valor", numerica=True),
        _p("agregar", "Si se repite el tiempo", "opcion", "sumar", opciones=["sumar", "promediar"]),
        _p("color", "Color", "color", "primario")] + _comunes("area"),
       CABEZA_MPL + FECHAS + r'''agrupado = datos.groupby({{x}})[{{y}}]
serie = agrupado.sum() if {{agregar}} == "sumar" else agrupado.mean()
''' + FIG + r'''ax.fill_between(serie.index, serie.values, color={{color}}, alpha=0.35, linewidth=0)
ax.plot(serie.index, serie.values, color={{color}}, linewidth=1.5)
ax.set_ylim(bottom=0)
ax.margins(x=0)
''' + EJE_FECHAS + r'''ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
''' + PIE_MPL),
    _t("areas-apiladas", "Áreas apiladas", "Evolución", "stacked-area-graph.html", "matplotlib",
       "Evolución de varias partes de un total, una encima de otra; también en porcentaje.",
       [_datos("ejemplo_series.csv"), _p("x", "Eje x (tiempo)", "columna", "fecha"),
        _p("grupo", "Una capa por", "columna", "serie"),
        _p("y", "Valor", "columna", "valor", numerica=True),
        _p("porcentaje", "En porcentaje del total", "interruptor", False), PALETA] + _comunes("areas_apiladas"),
       CABEZA_MPL + COLORES_N + FECHAS + r'''tabla = datos.pivot_table(index={{x}}, columns={{grupo}}, values={{y}}, aggfunc="sum", fill_value=0, sort=False)
tabla = tabla.sort_index()
if {{porcentaje}}:
    tabla = tabla.div(tabla.sum(axis=1).replace(0, 1), axis=0) * 100
''' + FIG + r'''ax.stackplot(tabla.index, tabla.T.values, labels=[str(c) for c in tabla.columns],
             colors=colores_n(len(tabla.columns)), alpha=0.9, linewidth=0)
ax.margins(x=0)
''' + EJE_FECHAS + r'''ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or ("% del total" if {{porcentaje}} else {{y}}))
ax.legend(title={{grupo}}, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
''' + PIE_MPL),
    _t("flujo", "Flujo (streamgraph)", "Evolución", "streamgraph.html", "matplotlib",
       "Áreas apiladas alrededor de un eje central y suavizadas: muestra cómo cambian muchas series.",
       [_datos("ejemplo_series.csv"), _p("x", "Eje x (tiempo)", "columna", "fecha"),
        _p("grupo", "Una capa por", "columna", "serie"),
        _p("y", "Valor", "columna", "valor", numerica=True),
        _p("suavizado", "Media móvil de (puntos)", "numero", 4, min=1, max=100), PALETA] + _comunes("flujo"),
       CABEZA_MPL + COLORES_N + FECHAS + r'''tabla = datos.pivot_table(index={{x}}, columns={{grupo}}, values={{y}}, aggfunc="sum", fill_value=0, sort=False)
tabla = tabla.sort_index().rolling(int({{suavizado}}), min_periods=1, center=True).mean()
''' + FIG + r'''ax.stackplot(tabla.index, tabla.T.values, labels=[str(c) for c in tabla.columns], baseline="wiggle",
             colors=colores_n(len(tabla.columns)), alpha=0.9, linewidth=0)
ax.margins(x=0)
ax.set_yticks([])
ax.spines[["left"]].set_visible(False)
''' + EJE_FECHAS + r'''ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}})
ax.legend(title={{grupo}}, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
''' + PIE_MPL),
    _t("serie-temporal", "Serie temporal", "Evolución", "time-series.html", "matplotlib",
       "Valores a lo largo de fechas, con una línea por serie y una media móvil opcional.",
       [_datos("ejemplo_series.csv"), _p("x", "Fecha", "columna", "fecha"),
        _p("y", "Valor", "columna", "valor", numerica=True),
        _p("grupo", "Una línea por", "columna", "serie", opcional=True),
        _p("media_movil", "Media móvil de (puntos; 1 = sin media)", "numero", 1, min=1, max=365),
        _p("puntos", "Mostrar también los datos originales", "interruptor", False), PALETA]
       + _comunes("serie_temporal"),
       CABEZA_MPL + COLORES_N + FECHAS + r'''grupos = [(None, datos)] if not {{grupo}} else list(datos.groupby({{grupo}}, sort=False))
''' + FIG + r'''for (nombre, parte), color in zip(grupos, colores_n(len(grupos))):
    serie = parte.groupby({{x}})[{{y}}].mean().sort_index()
    suave = serie.rolling(int({{media_movil}}), min_periods=1, center=True).mean()
    if {{puntos}} and int({{media_movil}}) > 1:
        ax.plot(serie.index, serie.values, color=color, alpha=0.3, linewidth=0.8)
    ax.plot(suave.index, suave.values, color=color, linewidth=1.5, label=None if nombre is None else str(nombre))
''' + EJE_FECHAS + r'''ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
if {{grupo}}:
    ax.legend(title={{grupo}}, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
''' + PIE_MPL),
]

GALERIA = DISTRIBUCION + CORRELACION + RANKING + PARTES + EVOLUCION + MAPAS + FLUJOS
