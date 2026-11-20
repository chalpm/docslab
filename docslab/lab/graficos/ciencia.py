# SPDX-License-Identifier: AGPL-3.0-only
"""Plantillas de gráficos para análisis científico y de datos.

Reducción de dimensión (PCA, t-SNE, NMDS), agrupamiento, evaluación de modelos,
estadística (comparaciones con valor p, Q-Q, Bland-Altman, ajustes, metaanálisis),
biomedicina y ómicas (volcán, Manhattan, Kaplan-Meier, dosis-respuesta, Venn) y
señales (espectros, superficies). Usan matplotlib, seaborn, scipy y scikit-learn.
"""
from __future__ import annotations

from .comun import CABEZA_MPL, CABEZA_SNS, PIE_MPL, _comunes, _p
from .galeria import COLORES_N, FIG, PALETA, PIE_SIN_EJES, _datos, _sin_ejes


def _t(id_, nombre, categoria, biblioteca, descripcion, parametros, codigo):
    return dict(id=id_, nombre=nombre, categoria=categoria, biblioteca=biblioteca, descripcion=descripcion,
                parametros=parametros, codigo=codigo)


PIE_LIBRE = r'''
if {{titulo}}:
    fig.suptitle({{titulo}})
fig.tight_layout()
os.makedirs(os.path.dirname({{salida}}) or ".", exist_ok=True)
fig.savefig({{salida}}, bbox_inches="tight", dpi=300)
plt.show()
'''
FIG_3D = r'''
fig = plt.figure(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
ax = fig.add_subplot(projection="3d")
'''
VISTA_3D = [_p("elevacion", "Ángulo de elevación (°)", "numero", 22, min=-90, max=90),
            _p("giro", "Ángulo de giro (°)", "numero", -60, min=-180, max=180)]

# ------------------------------------------------------------------------- matriz numérica y grupos
P_COLUMNAS = _p("columnas", "Variables (vacío = todas las numéricas)", "columnas", [], opcional=True, numerica=True)
P_GRUPO = _p("grupo", "Un color por", "columna", "grupo", opcional=True)
P_ESCALAR = _p("escalar", "Estandarizar las variables (media 0, desviación 1)", "interruptor", True)

MATRIZ = r'''import numpy as np

cols = {{columnas}} or [c for c in datos.select_dtypes("number").columns if c != {{grupo}}]
X = datos[cols].dropna()
etiquetas = datos.loc[X.index, {{grupo}}].astype(str).to_numpy() if {{grupo}} else None
if {{escalar}}:
    X = (X - X.mean()) / X.std(ddof=0).replace(0, 1)
'''
DISPERSAR = r'''
from matplotlib.patches import Ellipse


def dispersar(ax, S, i, j, elipses=False, tamano=18):
    """Puntos de las columnas i, j de S con un color por grupo y, si se pide, la elipse del 95 %."""
    if etiquetas is None:
        grupos = [(None, np.arange(len(S)))]
    else:
        grupos = [(g, np.where(etiquetas == g)[0]) for g in dict.fromkeys(etiquetas)]
    for (g, idx), color in zip(grupos, colores_n(len(grupos))):
        ax.scatter(S[idx, i], S[idx, j], s=tamano, color=color, alpha=0.8, linewidths=0,
                   label=None if g is None else g)
        if elipses and len(idx) > 2:
            valores, vectores = np.linalg.eigh(np.cov(S[idx][:, [i, j]].T))
            angulo = np.degrees(np.arctan2(vectores[1, 1], vectores[0, 1]))
            ancho_e, alto_e = 2 * np.sqrt(5.991 * np.clip(valores[::-1], 0, None))     # chi² (2 gl) al 95 %
            ax.add_patch(Ellipse(S[idx][:, [i, j]].mean(axis=0), ancho_e, alto_e, angle=angulo, facecolor=color,
                                 edgecolor=color, alpha=0.12, linewidth=1))
    if etiquetas is not None:
        ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0), title={{grupo}})

'''
DISPERSAR_3D = r'''

def dispersar_3d(ax, S):
    grupos = [(None, np.arange(len(S)))] if etiquetas is None else \
        [(g, np.where(etiquetas == g)[0]) for g in dict.fromkeys(etiquetas)]
    for (g, idx), color in zip(grupos, colores_n(len(grupos))):
        ax.scatter(S[idx, 0], S[idx, 1], S[idx, 2], s=14, color=color, alpha=0.8, linewidths=0,
                   depthshade=True, label=None if g is None else g)
    if etiquetas is not None:
        ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.02, 1.0), title={{grupo}})
    ax.view_init(elev={{elevacion}}, azim={{giro}})

'''
PIE_3D = r'''
ax.set_title({{titulo}})
fig.tight_layout()
os.makedirs(os.path.dirname({{salida}}) or ".", exist_ok=True)
fig.savefig({{salida}}, bbox_inches="tight", dpi=300)
plt.show()
'''
TSNE_CODIGO = r'''from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

datos_tsne = X.to_numpy()
if {{pca_previo}} and datos_tsne.shape[1] > 50:      # habitual con miles de variables: primero 50 componentes
    datos_tsne = PCA(n_components=50, random_state=int({{semilla}})).fit_transform(datos_tsne)
perplejidad = min(float({{perplejidad}}), (len(datos_tsne) - 1) / 3)
metodo = "exact" if len(datos_tsne) <= 1500 else "barnes_hut"   # exacto: más fiel y sin puntos sueltos
S = TSNE(n_components=DIMENSIONES, perplexity=perplejidad, init="pca", learning_rate="auto", method=metodo,
         random_state=int({{semilla}})).fit_transform(datos_tsne)
print(f"t-SNE ({metodo}) con perplejidad {perplejidad:g} sobre {datos_tsne.shape[0]} filas y {datos_tsne.shape[1]} variables.")
print("Las distancias entre grupos alejados y el tamaño de los grupos no tienen un significado directo.")
'''
P_TSNE = [_p("perplejidad", "Perplejidad (vecinos efectivos)", "numero", 30, min=2, max=200,
             ayuda="Entre 5 y 50 es lo habitual; con pocas filas se reduce sola."),
          _p("semilla", "Semilla (para repetir el resultado)", "numero", 42, min=0, max=99999),
          _p("pca_previo", "Reducir antes con PCA si hay más de 50 variables", "interruptor", True)]

MULTIVARIADO = [
    _t("pca", "PCA (componentes principales)", "Multivariado", "matplotlib",
       "Las muestras proyectadas en dos componentes principales, con el % de varianza de cada eje y elipses del 95 %.",
       [_datos("ejemplo_multivariado.csv"), P_COLUMNAS, P_GRUPO, P_ESCALAR,
        _p("eje_x", "Componente del eje x", "numero", 1, min=1, max=50),
        _p("eje_y", "Componente del eje y", "numero", 2, min=1, max=50),
        _p("elipses", "Elipse del 95 % de cada grupo", "interruptor", True), PALETA]
       + _sin_ejes("pca", alto=11, ancho=15),
       CABEZA_MPL + COLORES_N + MATRIZ + r'''from sklearn.decomposition import PCA

pca = PCA(n_components=min(X.shape)).fit(X)
S = pca.transform(X)
var = pca.explained_variance_ratio_ * 100
i, j = int({{eje_x}}) - 1, int({{eje_y}}) - 1
print("Varianza explicada por componente (%):", np.round(var[:8], 1))
''' + DISPERSAR + FIG + r'''dispersar(ax, S, i, j, elipses={{elipses}})
ax.axhline(0, color="#BBBBBB", linewidth=0.6, zorder=0)
ax.axvline(0, color="#BBBBBB", linewidth=0.6, zorder=0)
ax.set_xlabel(f"PC{i + 1} ({var[i]:.1f} %)")
ax.set_ylabel(f"PC{j + 1} ({var[j]:.1f} %)")
''' + PIE_MPL),
    _t("pca-3d", "PCA 3D", "Multivariado", "matplotlib",
       "Las muestras en las tres primeras componentes principales, en una vista 3D que se puede girar.",
       [_datos("ejemplo_multivariado.csv"), P_COLUMNAS, P_GRUPO, P_ESCALAR, *VISTA_3D, PALETA]
       + _sin_ejes("pca_3d", alto=12, ancho=15),
       CABEZA_MPL + COLORES_N + MATRIZ + r'''from sklearn.decomposition import PCA

pca = PCA(n_components=3).fit(X)
S = pca.transform(X)
var = pca.explained_variance_ratio_ * 100
print("Varianza explicada (%):", np.round(var, 1), "· total:", round(var.sum(), 1))
''' + DISPERSAR_3D + FIG_3D + r'''dispersar_3d(ax, S)
ax.set_xlabel(f"PC1 ({var[0]:.1f} %)")
ax.set_ylabel(f"PC2 ({var[1]:.1f} %)")
ax.set_zlabel(f"PC3 ({var[2]:.1f} %)")
''' + PIE_3D),
    _t("pca-biplot", "Biplot de PCA", "Multivariado", "matplotlib",
       "Muestras y variables a la vez: las flechas muestran cuánto pesa cada variable en las dos componentes.",
       [_datos("ejemplo_multivariado.csv"), P_COLUMNAS, P_GRUPO, P_ESCALAR,
        _p("flechas", "Variables con flecha (las de más peso)", "numero", 8, min=1, max=100), PALETA]
       + _sin_ejes("pca_biplot", alto=12, ancho=15),
       CABEZA_MPL + COLORES_N + MATRIZ + r'''from sklearn.decomposition import PCA

pca = PCA(n_components=2).fit(X)
S = pca.transform(X)
var = pca.explained_variance_ratio_ * 100
S = S / np.abs(S).max(axis=0)                        # muestras escaladas a [-1, 1]
cargas = pca.components_.T * np.sqrt(pca.explained_variance_)
cargas = cargas / np.abs(cargas).max()               # la flecha mayor llega a 1
orden = np.argsort(-np.hypot(cargas[:, 0], cargas[:, 1]))[: int({{flechas}})]
''' + DISPERSAR + FIG + r'''dispersar(ax, S, 0, 1, tamano=14)
for k in orden:
    ax.annotate("", xy=(cargas[k, 0], cargas[k, 1]), xytext=(0, 0),
                arrowprops={"arrowstyle": "->", "color": "#333333", "linewidth": 1})
    ax.text(cargas[k, 0] * 1.1, cargas[k, 1] * 1.1, cols[k], fontsize="x-small", ha="center", va="center",
            color="#333333")
ax.axhline(0, color="#BBBBBB", linewidth=0.6, zorder=0)
ax.axvline(0, color="#BBBBBB", linewidth=0.6, zorder=0)
ax.set_xlim(-1.25, 1.25)
ax.set_ylim(-1.25, 1.25)
ax.set_aspect("equal")
ax.set_xlabel(f"PC1 ({var[0]:.1f} %)")
ax.set_ylabel(f"PC2 ({var[1]:.1f} %)")
''' + PIE_MPL),
    _t("pca-varianza", "Varianza explicada (sedimentación)", "Multivariado", "matplotlib",
       "Cuánta varianza recoge cada componente y la acumulada: ayuda a decidir cuántas conservar.",
       [_datos("ejemplo_multivariado.csv"), P_COLUMNAS,
        _p("grupo", "Columna que no es una variable (se excluye)", "columna", "grupo", opcional=True), P_ESCALAR,
        _p("maximo", "Componentes a mostrar", "numero", 10, min=2, max=100),
        _p("umbral", "Marcar el % acumulado de", "numero", 80, min=1, max=100),
        _p("color", "Color", "color", "primario")] + _comunes("pca_varianza", x="Componente", y="% de varianza"),
       CABEZA_MPL + MATRIZ + r'''from sklearn.decomposition import PCA

pca = PCA().fit(X)
var = pca.explained_variance_ratio_[: int({{maximo}})] * 100
acumulada = np.cumsum(pca.explained_variance_ratio_ * 100)[: len(var)]
necesarias = int(np.searchsorted(acumulada, {{umbral}}) + 1)
print(f"Hacen falta {necesarias} componentes para llegar al " + str({{umbral}}) + " % de la varianza.")
x = np.arange(1, len(var) + 1)
''' + FIG + r'''ax.bar(x, var, color={{color}}, alpha=0.85, label="Componente")
ax.plot(x, acumulada, "-o", color="#333333", markersize=4, linewidth=1.2, label="Acumulada")
ax.axhline({{umbral}}, color="#999999", linestyle="--", linewidth=0.8)
ax.text(x[-1], {{umbral}} + 1.5, str({{umbral}}) + " %", ha="right", fontsize="small", color="#666666")
ax.set_xticks(x, [f"PC{k}" for k in x])
ax.set_ylim(0, 105)
ax.set_xlabel({{etiqueta_x}})
ax.set_ylabel({{etiqueta_y}})
ax.legend(frameon=False, loc="center right")
''' + PIE_MPL),
    _t("tsne", "t-SNE", "Multivariado", "matplotlib",
       "Mapa 2D que conserva qué muestras se parecen entre sí: muy usado para ver grupos (por ejemplo, en células).",
       [_datos("ejemplo_multivariado.csv"), P_COLUMNAS, P_GRUPO, P_ESCALAR, *P_TSNE, PALETA]
       + _sin_ejes("tsne", alto=11, ancho=15),
       CABEZA_MPL + COLORES_N + MATRIZ + "DIMENSIONES = 2\n" + TSNE_CODIGO + DISPERSAR + FIG + r'''dispersar(ax, S, 0, 1)
ax.set_xlabel("t-SNE 1")
ax.set_ylabel("t-SNE 2")
ax.set_xticks([])
ax.set_yticks([])
''' + PIE_MPL),
    _t("tsne-3d", "t-SNE 3D", "Multivariado", "matplotlib",
       "La misma idea que el t-SNE, en tres dimensiones.",
       [_datos("ejemplo_multivariado.csv"), P_COLUMNAS, P_GRUPO, P_ESCALAR, *P_TSNE, *VISTA_3D, PALETA]
       + _sin_ejes("tsne_3d", alto=12, ancho=15),
       CABEZA_MPL + COLORES_N + MATRIZ + "DIMENSIONES = 3\n" + TSNE_CODIGO + DISPERSAR_3D + FIG_3D + r'''dispersar_3d(ax, S)
ax.set_xlabel("t-SNE 1")
ax.set_ylabel("t-SNE 2")
ax.set_zlabel("t-SNE 3")
for eje in (ax.xaxis, ax.yaxis, ax.zaxis):
    eje.set_ticklabels([])
''' + PIE_3D),
    _t("nmds", "NMDS / MDS (ordenación)", "Multivariado", "matplotlib",
       "Ordenación a partir de distancias (Bray-Curtis, Jaccard…), típica en ecología. Muestra el estrés del ajuste.",
       [_datos("ejemplo_multivariado.csv"), P_COLUMNAS, P_GRUPO,
        _p("escalar", "Estandarizar las variables (no con Bray-Curtis)", "interruptor", False),
        _p("distancia", "Distancia", "opcion", "Bray-Curtis",
           opciones=["Bray-Curtis", "Euclídea", "Jaccard (presencia)", "Manhattan", "Correlación"]),
        _p("metrico", "MDS métrico (si no, NMDS)", "interruptor", False),
        _p("elipses", "Elipse del 95 % de cada grupo", "interruptor", True),
        _p("semilla", "Semilla", "numero", 42, min=0, max=99999), PALETA] + _sin_ejes("nmds", alto=11, ancho=15),
       CABEZA_MPL + COLORES_N + MATRIZ + r'''from scipy.spatial.distance import pdist, squareform
from sklearn.manifold import MDS

metrica = {"Bray-Curtis": "braycurtis", "Euclídea": "euclidean", "Jaccard (presencia)": "jaccard",
           "Manhattan": "cityblock", "Correlación": "correlation"}[{{distancia}}]
valores = X.to_numpy() > 0 if metrica == "jaccard" else X.to_numpy()
D = squareform(pdist(valores, metric=metrica))
try:                                                    # scikit-learn 1.8 o posterior
    modelo = MDS(n_components=2, metric_mds={{metrico}}, metric="precomputed", n_init=4, init="random",
                 random_state=int({{semilla}}), normalized_stress="auto")
except TypeError:                                       # versiones anteriores
    modelo = MDS(n_components=2, metric={{metrico}}, dissimilarity="precomputed", n_init=4,
                 random_state=int({{semilla}}), normalized_stress="auto")
S = modelo.fit_transform(D)
print(f"Estrés: {modelo.stress_:.3f}  (en NMDS, < 0,1 es bueno y > 0,2, dudoso)")
''' + DISPERSAR + FIG + r'''dispersar(ax, S, 0, 1, elipses={{elipses}})
nombre = "MDS" if {{metrico}} else "NMDS"
ax.set_xlabel(nombre + " 1")
ax.set_ylabel(nombre + " 2")
ax.text(0.98, 0.02, f"Estrés = {modelo.stress_:.3f}", transform=ax.transAxes, ha="right", va="bottom",
        fontsize="small", color="#555555")
''' + PIE_MPL),
    _t("mapa-calor-agrupado", "Mapa de calor con agrupamiento", "Multivariado", "seaborn",
       "Matriz de muestras × variables con dendrogramas en filas y columnas: el clásico de la expresión génica.",
       [_datos("ejemplo_multivariado.csv"), P_COLUMNAS, P_GRUPO,
        _p("escalado", "Escalar", "opcion", "Por columna (z)", opciones=["Por columna (z)", "Por fila (z)", "Sin escalar"]),
        _p("metodo", "Método de agrupamiento", "opcion", "average", opciones=["average", "complete", "ward", "single"]),
        _p("mapa_color", "Mapa de color", "opcion", "vlag", opciones=["vlag", "RdBu_r", "coolwarm", "viridis", "magma", "mako"]),
        _p("rotulos_filas", "Escribir el nombre de cada fila", "interruptor", False), PALETA]
       + _sin_ejes("mapa_calor_agrupado", alto=16, ancho=15),
       CABEZA_SNS + COLORES_N + r'''cols = {{columnas}} or [c for c in datos.select_dtypes("number").columns if c != {{grupo}}]
X = datos[cols].dropna()
z = {"Por columna (z)": 1, "Por fila (z)": 0}.get({{escalado}})
colores_filas = None
if {{grupo}}:
    g_filas = datos.loc[X.index, {{grupo}}].astype(str)
    tono = dict(zip(dict.fromkeys(g_filas), colores_n(g_filas.nunique())))
    colores_filas = g_filas.map(tono).rename({{grupo}})
g = sns.clustermap(X, method={{metodo}}, metric="euclidean", z_score=z, cmap={{mapa_color}}, center=0 if z is not None else None,
                   row_colors=colores_filas, yticklabels={{rotulos_filas}}, figsize=({{ancho}} / 2.54, {{alto}} / 2.54),
                   dendrogram_ratio=0.15, cbar_kws={"label": "z" if z is not None else "valor"})
if {{grupo}}:
    g.ax_col_dendrogram.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c, label=k) for k, c in tono.items()],
                               ncol=min(4, len(tono)), loc="center", frameon=False, fontsize="small",
                               bbox_to_anchor=(0.5, 1.15))
fig = g.figure
if {{titulo}}:
    fig.suptitle({{titulo}}, y=1.04)
os.makedirs(os.path.dirname({{salida}}) or ".", exist_ok=True)
fig.savefig({{salida}}, bbox_inches="tight", dpi=300)
plt.show()
'''),
]

# ----------------------------------------------------------------------------- aprendizaje automático
APRENDIZAJE = [
    _t("kmeans", "Agrupamiento k-means", "Aprendizaje automático", "matplotlib",
       "Divide las muestras en k grupos y los muestra sobre el PCA, con sus centros. Añade la columna «cluster».",
       [_datos("ejemplo_multivariado.csv"), P_COLUMNAS,
        _p("grupo", "Grupo conocido, para comparar (opcional)", "columna", "grupo", opcional=True), P_ESCALAR,
        _p("k", "Número de grupos (k)", "numero", 4, min=2, max=30),
        _p("semilla", "Semilla", "numero", 42, min=0, max=99999), PALETA] + _sin_ejes("kmeans", alto=11, ancho=15),
       CABEZA_MPL + COLORES_N + MATRIZ + r'''from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score

modelo = KMeans(n_clusters=int({{k}}), n_init=10, random_state=int({{semilla}})).fit(X)
cluster = modelo.labels_ + 1
datos.loc[X.index, "cluster"] = cluster               # queda en la tabla para las celdas siguientes
print(f"Silueta media: {silhouette_score(X, modelo.labels_):.3f}")
if etiquetas is not None:
    print("Índice de Rand ajustado frente a «" + str({{grupo}}) + f"»: {adjusted_rand_score(etiquetas, cluster):.3f}")
    print(pd.crosstab(pd.Series(cluster, name="cluster"), pd.Series(etiquetas, name={{grupo}})))
pca = PCA(n_components=2).fit(X)
S = pca.transform(X)
centros = pca.transform(modelo.cluster_centers_)
var = pca.explained_variance_ratio_ * 100
''' + FIG + r'''for c, color in zip(range(1, int({{k}}) + 1), colores_n(int({{k}}))):
    idx = cluster == c
    ax.scatter(S[idx, 0], S[idx, 1], s=18, color=color, alpha=0.8, linewidths=0, label=f"Grupo {c} (n = {idx.sum()})")
    ax.scatter(*centros[c - 1], marker="X", s=140, color=color, edgecolor="black", linewidth=0.8, zorder=3)
ax.set_xlabel(f"PC1 ({var[0]:.1f} %)")
ax.set_ylabel(f"PC2 ({var[1]:.1f} %)")
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0), title="k-means")
''' + PIE_MPL),
    _t("kmeans-k", "Elegir k (codo y silueta)", "Aprendizaje automático", "matplotlib",
       "Inercia (método del codo) y silueta media para cada k: ayuda a elegir el número de grupos.",
       [_datos("ejemplo_multivariado.csv"), P_COLUMNAS,
        _p("grupo", "Columna que no es una variable (se excluye)", "columna", "grupo", opcional=True), P_ESCALAR,
        _p("k_max", "k máximo", "numero", 10, min=3, max=40),
        _p("semilla", "Semilla", "numero", 42, min=0, max=99999),
        _p("color", "Color", "color", "primario")] + _sin_ejes("kmeans_k", alto=8, ancho=16),
       CABEZA_MPL + MATRIZ + r'''from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

ks = list(range(2, min(int({{k_max}}), len(X) - 1) + 1))
inercia, silueta = [], []
for k in ks:
    m = KMeans(n_clusters=k, n_init=10, random_state=int({{semilla}})).fit(X)
    inercia.append(m.inertia_)
    silueta.append(silhouette_score(X, m.labels_))
mejor = ks[int(np.argmax(silueta))]
print("k con mayor silueta:", mejor)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
ax1.plot(ks, inercia, "-o", color={{color}}, markersize=4)
ax1.set_xlabel("k")
ax1.set_ylabel("Inercia (suma de distancias²)")
ax1.set_title("Método del codo", fontsize="medium")
ax2.plot(ks, silueta, "-o", color={{color}}, markersize=4)
ax2.axvline(mejor, color="#999999", linestyle="--", linewidth=0.8)
ax2.set_xlabel("k")
ax2.set_ylabel("Silueta media")
ax2.set_title(f"Silueta (mejor k = {mejor})", fontsize="medium")
for a in (ax1, ax2):
    a.spines[["top", "right"]].set_visible(False)
    a.set_xticks(ks)
''' + PIE_LIBRE),
    _t("roc", "Curva ROC", "Aprendizaje automático", "matplotlib",
       "Sensibilidad frente a 1 − especificidad de uno o varios modelos o pruebas, con su área bajo la curva (AUC).",
       [_datos("ejemplo_clasificacion.csv"), _p("real", "Clase real (0/1 o texto)", "columna", "real"),
        _p("positiva", "Valor de la clase positiva", "texto", "1"),
        _p("columnas", "Puntuación de cada modelo", "columnas", ["modelo_a", "modelo_b"], numerica=True),
        _p("youden", "Marcar el punto de corte óptimo (Youden)", "interruptor", True), PALETA]
       + _comunes("roc", x="1 − especificidad", y="Sensibilidad", alto=12),
       CABEZA_MPL + COLORES_N + r'''import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve

y = (datos[{{real}}].astype(str) == str({{positiva}})).astype(int)
''' + FIG + r'''ax.plot([0, 1], [0, 1], linestyle="--", color="#AAAAAA", linewidth=0.8)
for columna, color in zip({{columnas}}, colores_n(len({{columnas}}))):
    fpr, tpr, cortes = roc_curve(y, datos[columna])
    auc = roc_auc_score(y, datos[columna])
    ax.plot(fpr, tpr, color=color, linewidth=1.6, label=f"{columna} (AUC = {auc:.3f})")
    if {{youden}}:
        k = int(np.argmax(tpr - fpr))
        ax.scatter(fpr[k], tpr[k], color=color, s=30, zorder=3)
        print(f"{columna}: AUC {auc:.3f}; corte de Youden {cortes[k]:.3g} (sens. {tpr[k]:.2f}, espec. {1 - fpr[k]:.2f})")
ax.set_xlim(0, 1)
ax.set_ylim(0, 1.01)
ax.set_aspect("equal")
ax.set_xlabel({{etiqueta_x}})
ax.set_ylabel({{etiqueta_y}})
ax.legend(frameon=False, loc="lower right")
''' + PIE_MPL),
    _t("matriz-confusion", "Matriz de confusión", "Aprendizaje automático", "seaborn",
       "Clases reales frente a predichas; en la consola, precisión, sensibilidad y F1 de cada clase.",
       [_datos("ejemplo_clasificacion.csv"), _p("real", "Clase real", "columna", "clase_real"),
        _p("predicho", "Clase predicha", "columna", "clase_predicha"),
        _p("orden", "Orden de las clases (separadas por comas; vacío = alfabético)", "texto", "Sano, Leve, Grave"),
        _p("normalizar", "Mostrar", "opcion", "Recuentos",
           opciones=["Recuentos", "Proporción por fila (sensibilidad)", "Proporción por columna (precisión)"]),
        _p("mapa_color", "Mapa de color", "opcion", "Blues", opciones=["Blues", "Greens", "Purples", "viridis", "mako_r"])]
       + _comunes("matriz_confusion", x="Clase predicha", y="Clase real", alto=11),
       CABEZA_SNS + r'''from sklearn.metrics import classification_report, confusion_matrix

real, pred = datos[{{real}}].astype(str), datos[{{predicho}}].astype(str)
clases = [c.strip() for c in {{orden}}.split(",") if c.strip()] or sorted(set(real) | set(pred))
m = confusion_matrix(real, pred, labels=clases)
modo = {{normalizar}}
if modo.startswith("Proporción por fila"):
    valores, formato = m / m.sum(axis=1, keepdims=True).clip(min=1), ".0%"
elif modo.startswith("Proporción por columna"):
    valores, formato = m / m.sum(axis=0, keepdims=True).clip(min=1), ".0%"
else:
    valores, formato = m, "d"
print(classification_report(real, pred, labels=clases, zero_division=0))
''' + FIG + r'''sns.heatmap(valores, annot=True, fmt=formato, cmap={{mapa_color}}, cbar=False, square=True, linewidths=0.5,
            xticklabels=clases, yticklabels=clases, ax=ax)
ax.set_xlabel({{etiqueta_x}})
ax.set_ylabel({{etiqueta_y}})
ax.text(0.5, -0.22, f"Exactitud = {m.trace() / max(m.sum(), 1):.1%}", transform=ax.transAxes, ha="center",
        fontsize="small", color="#555555")
''' + PIE_MPL.replace('ax.spines[["top", "right"]].set_visible(False)\n', "")),
]

# -------------------------------------------------------------------------------------- estadística
ESTADISTICA = [
    _t("comparacion-grupos", "Comparación de grupos con valor p", "Estadística", "matplotlib",
       "Cajas con todos los puntos y las comparaciones entre grupos (t de Welch, Mann-Whitney…) con su corrección.",
       [_datos("ejemplo.csv"), _p("x", "Grupos", "columna", "tratamiento"),
        _p("y", "Valor", "columna", "valor", numerica=True),
        _p("prueba", "Prueba", "opcion", "t de Welch",
           opciones=["t de Welch", "t de Student (varianzas iguales)", "Mann-Whitney"]),
        _p("comparaciones", "Comparar", "opcion", "Todas las parejas", opciones=["Todas las parejas", "Contra el primer grupo"]),
        _p("correccion", "Corrección por comparaciones múltiples", "opcion", "Holm", opciones=["Holm", "Bonferroni", "Ninguna"]),
        _p("mostrar", "Mostrar", "opcion", "Asteriscos", opciones=["Asteriscos", "Valor p"]), PALETA]
       + _comunes("comparacion_grupos", alto=11),
       CABEZA_MPL + COLORES_N + r'''import itertools
import numpy as np
from scipy import stats

nombres = list(dict.fromkeys(datos[{{x}}].dropna()))
series = [datos.loc[datos[{{x}}] == n, {{y}}].dropna().to_numpy() for n in nombres]
if {{comparaciones}} == "Todas las parejas":
    parejas = list(itertools.combinations(range(len(nombres)), 2))
else:
    parejas = [(0, k) for k in range(1, len(nombres))]
p = []
for a, b in parejas:
    if {{prueba}} == "Mann-Whitney":
        p.append(stats.mannwhitneyu(series[a], series[b], alternative="two-sided").pvalue)
    else:
        p.append(stats.ttest_ind(series[a], series[b], equal_var={{prueba}}.startswith("t de Student")).pvalue)
p = np.array(p)
if {{correccion}} == "Bonferroni":
    p = np.minimum(p * len(p), 1)
elif {{correccion}} == "Holm":                       # Holm-Bonferroni, con monotonía
    orden = np.argsort(p)
    ajust = np.maximum.accumulate(p[orden] * (len(p) - np.arange(len(p))))
    p[orden] = np.minimum(ajust, 1)
global_ = stats.kruskal(*series) if {{prueba}} == "Mann-Whitney" else stats.f_oneway(*series)
print(("Kruskal-Wallis" if {{prueba}} == "Mann-Whitney" else "ANOVA") + f" global: p = {global_.pvalue:.3g}")
for (a, b), v in zip(parejas, p):
    print(f"{nombres[a]} vs {nombres[b]}: p = {v:.3g}")


def rotulo(v):
    if {{mostrar}} == "Valor p":
        return "p < 0,001" if v < 0.001 else f"p = {v:.3f}".replace(".", ",")
    return "***" if v < 0.001 else "**" if v < 0.01 else "*" if v < 0.05 else "ns"

''' + FIG + r'''colores = colores_n(len(nombres))
rng = np.random.default_rng(1)
ax.boxplot(series, positions=range(len(series)), widths=0.5, showfliers=False,
           medianprops={"color": "black"}, boxprops={"color": "#555555"}, whiskerprops={"color": "#555555"},
           capprops={"color": "#555555"})
for i, (s, color) in enumerate(zip(series, colores)):
    ax.scatter(i + rng.uniform(-0.12, 0.12, len(s)), s, s=14, color=color, alpha=0.75, zorder=3, linewidths=0)
alto_max = max(s.max() for s in series)
rango = alto_max - min(s.min() for s in series)
paso = rango * 0.09
for n, ((a, b), v) in enumerate(sorted(zip(parejas, p), key=lambda t: abs(t[0][1] - t[0][0]))):
    h = alto_max + paso * (n + 1)
    ax.plot([a, a, b, b], [h - paso * 0.3, h, h, h - paso * 0.3], color="black", linewidth=0.8)
    ax.text((a + b) / 2, h, rotulo(v), ha="center", va="bottom", fontsize="small")
ax.set_ylim(top=alto_max + paso * (len(parejas) + 1.5))
ax.set_xticks(range(len(nombres)), [str(n) for n in nombres])
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
''' + PIE_MPL),
    _t("raincloud", "Nube de lluvia (raincloud)", "Estadística", "matplotlib",
       "Densidad, caja y todos los puntos de cada grupo en una sola figura: la distribución completa.",
       [_datos("ejemplo.csv"), _p("x", "Grupos", "columna", "tratamiento"),
        _p("y", "Valor", "columna", "valor", numerica=True), PALETA] + _comunes("raincloud", x="", alto=10),
       CABEZA_MPL + COLORES_N + r'''import numpy as np

nombres = list(dict.fromkeys(datos[{{x}}].dropna()))
series = [datos.loc[datos[{{x}}] == n, {{y}}].dropna().to_numpy() for n in nombres]
todo = np.concatenate(series)
malla = np.linspace(todo.min() - 0.1 * np.ptp(todo), todo.max() + 0.1 * np.ptp(todo), 300)
rng = np.random.default_rng(1)
''' + FIG + r'''for i, (s, color) in enumerate(zip(series, colores_n(len(series)))):
    h = 1.06 * s.std() * len(s) ** (-1 / 5) or 1.0
    dens = np.exp(-((malla[:, None] - s[None, :]) ** 2) / (2 * h * h)).sum(axis=1)
    dens = dens / dens.max() * 0.4
    ax.fill_between(malla, i + 0.05, i + 0.05 + dens, color=color, alpha=0.6, linewidth=0)       # nube
    ax.boxplot(s, positions=[i - 0.08], vert=False, widths=0.1, showfliers=False, patch_artist=True,
               boxprops={"facecolor": "white", "edgecolor": "#333333"}, medianprops={"color": "black"},
               whiskerprops={"color": "#333333"}, capprops={"color": "#333333"})
    ax.scatter(s, i - 0.25 + rng.uniform(-0.06, 0.06, len(s)), s=10, color=color, alpha=0.8, linewidths=0)  # lluvia
ax.set_yticks(range(len(nombres)), [str(n) for n in nombres])
ax.set_ylim(-0.5, len(nombres) - 0.4)
ax.set_xlabel({{etiqueta_y}} or {{y}})
ax.set_ylabel({{etiqueta_x}})
''' + PIE_MPL),
    _t("qq", "Gráfico Q-Q (normalidad)", "Estadística", "matplotlib",
       "Cuantiles de los datos frente a los de una normal: si los puntos siguen la recta, los datos son normales.",
       [_datos("ejemplo.csv"), _p("x", "Columna", "columna", "valor", numerica=True),
        _p("grupo", "Un color por", "columna", "tratamiento", opcional=True), PALETA]
       + _comunes("qq", x="Cuantiles teóricos (normal)", y="Cuantiles de la muestra", alto=11),
       CABEZA_MPL + COLORES_N + r'''from scipy import stats

grupos = [(None, datos)] if not {{grupo}} else list(datos.groupby({{grupo}}, sort=False))
''' + FIG + r'''for (nombre, parte), color in zip(grupos, colores_n(len(grupos))):
    v = parte[{{x}}].dropna()
    (teoricos, ordenados), (pendiente, corte, r) = stats.probplot(v, dist="norm")
    w = stats.shapiro(v).pvalue if 3 <= len(v) <= 5000 else float("nan")
    etiqueta = ("" if nombre is None else f"{nombre} · ") + f"Shapiro-Wilk p = {w:.3f}"
    ax.scatter(teoricos, ordenados, s=14, color=color, alpha=0.8, linewidths=0, label=etiqueta)
    ax.plot(teoricos, pendiente * teoricos + corte, color=color, linewidth=1)
ax.set_xlabel({{etiqueta_x}})
ax.set_ylabel({{etiqueta_y}} or {{x}})
ax.legend(frameon=False, fontsize="small")
''' + PIE_MPL),
    _t("bland-altman", "Bland-Altman (concordancia)", "Estadística", "matplotlib",
       "Concordancia entre dos métodos de medida: diferencia frente a media, con el sesgo y los límites de acuerdo.",
       [_datos("ejemplo_metodos.csv"), _p("a", "Método A", "columna", "metodo_a", numerica=True),
        _p("b", "Método B", "columna", "metodo_b", numerica=True),
        _p("porcentaje", "Diferencia en % de la media", "interruptor", False),
        _p("color", "Color", "color", "primario")] + _comunes("bland_altman", x="Media de los dos métodos", y=""),
       CABEZA_MPL + r'''import numpy as np

d = datos[[{{a}}, {{b}}]].dropna()
media = d.mean(axis=1)
dif = d[{{a}}] - d[{{b}}]
if {{porcentaje}}:
    dif = dif / media * 100
sesgo, de = dif.mean(), dif.std(ddof=1)
li, ls = sesgo - 1.96 * de, sesgo + 1.96 * de
unidad = " %" if {{porcentaje}} else ""
print(f"Sesgo: {sesgo:.3g}{unidad} · límites de acuerdo del 95 %: {li:.3g} a {ls:.3g}{unidad}")
''' + FIG + r'''ax.scatter(media, dif, s=18, color={{color}}, alpha=0.8, linewidths=0)
for v, texto, estilo in [(sesgo, "Sesgo", "-"), (ls, "+1,96 DE", "--"), (li, "−1,96 DE", "--")]:
    ax.axhline(v, color="#555555", linestyle=estilo, linewidth=1)
    ax.text(1.01, v, f"{texto}\n{v:.2f}".replace(".", ","), transform=ax.get_yaxis_transform(), va="center",
            fontsize="x-small", color="#555555")
ax.axhline(0, color="#CCCCCC", linewidth=0.6, zorder=0)
ax.set_xlabel({{etiqueta_x}})
ax.set_ylabel({{etiqueta_y}} or (str({{a}}) + " − " + str({{b}}) + (" (% de la media)" if {{porcentaje}} else "")))
''' + PIE_MPL),
    _t("ajuste-curva", "Ajuste de curva (modelo)", "Estadística", "matplotlib",
       "Ajusta un modelo (lineal, polinomio, exponencial, logístico, Michaelis-Menten…) con su banda de confianza y R².",
       [_datos("ejemplo.csv"), _p("x", "Eje x", "columna", "tiempo", numerica=True),
        _p("y", "Eje y", "columna", "valor", numerica=True),
        _p("modelo", "Modelo", "opcion", "Lineal",
           opciones=["Lineal", "Polinomio de grado 2", "Polinomio de grado 3", "Exponencial", "Logarítmico", "Potencia",
                     "Logístico", "Michaelis-Menten"]),
        _p("banda", "Banda de confianza del 95 %", "interruptor", True),
        _p("ecuacion", "Escribir la ecuación y R²", "interruptor", True),
        _p("color", "Color", "color", "primario")] + _comunes("ajuste_curva"),
       CABEZA_MPL + r'''import numpy as np
from scipy.optimize import curve_fit

d = datos[[{{x}}, {{y}}]].dropna().sort_values({{x}})
x, y = d[{{x}}].to_numpy(float), d[{{y}}].to_numpy(float)
MODELOS = {   # función, forma de la ecuación, valores iniciales
    "Lineal": (lambda x, a, b: a + b * x, "y = {0:.4g} + {1:.4g}·x", lambda: [y.mean(), 0]),
    "Polinomio de grado 2": (lambda x, a, b, c: a + b * x + c * x**2, "y = {0:.4g} + {1:.4g}·x + {2:.4g}·x²",
                             lambda: [y.mean(), 0, 0]),
    "Polinomio de grado 3": (lambda x, a, b, c, e: a + b * x + c * x**2 + e * x**3,
                             "y = {0:.4g} + {1:.4g}·x + {2:.4g}·x² + {3:.4g}·x³", lambda: [y.mean(), 0, 0, 0]),
    "Exponencial": (lambda x, a, b: a * np.exp(b * x), "y = {0:.4g}·e^({1:.4g}·x)",
                    lambda: [max(y[0], 1e-9), np.polyfit(x, np.log(np.clip(y, 1e-9, None)), 1)[0]]),
    "Logarítmico": (lambda x, a, b: a + b * np.log(x), "y = {0:.4g} + {1:.4g}·ln x", lambda: [y.mean(), 1]),
    "Potencia": (lambda x, a, b: a * x**b, "y = {0:.4g}·x^{1:.4g}", lambda: [max(y.mean(), 1e-9), 1]),
    "Logístico": (lambda x, L, k, x0: L / (1 + np.exp(-k * (x - x0))), "y = {0:.4g} / (1 + e^(−{1:.4g}·(x − {2:.4g})))",
                  lambda: [y.max(), 1, np.median(x)]),
    "Michaelis-Menten": (lambda x, v, k: v * x / (k + x), "y = {0:.4g}·x / ({1:.4g} + x)", lambda: [y.max(), np.median(x)]),
}
f, forma, inicio = MODELOS[{{modelo}}]
par, cov = curve_fit(f, x, y, p0=inicio(), maxfev=20000)
r2 = 1 - np.sum((y - f(x, *par)) ** 2) / np.sum((y - y.mean()) ** 2)
ecuacion = forma.format(*par)
print(ecuacion, f"· R² = {r2:.4f}")
print("Errores estándar de los parámetros:", np.round(np.sqrt(np.diag(cov)), 4))
xs = np.linspace(x.min(), x.max(), 300)
ys = f(xs, *par)
''' + FIG + r'''ax.scatter(x, y, s=16, color={{color}}, alpha=0.6, linewidths=0)
ax.plot(xs, ys, color={{color}}, linewidth=1.8)
if {{banda}} and np.all(np.isfinite(cov)):
    h = 1e-6 * np.maximum(np.abs(par), 1)            # método delta con derivadas numéricas
    J = np.column_stack([(f(xs, *(par + np.eye(len(par))[k] * h[k])) - ys) / h[k] for k in range(len(par))])
    se = np.sqrt(np.einsum("ij,jk,ik->i", J, cov, J))
    ax.fill_between(xs, ys - 1.96 * se, ys + 1.96 * se, color={{color}}, alpha=0.18, linewidth=0)
if {{ecuacion}}:
    ax.text(0.02, 0.98, ecuacion + f"\nR² = {r2:.4f}", transform=ax.transAxes, va="top", fontsize="small",
            bbox={"facecolor": "white", "edgecolor": "#DDDDDD", "boxstyle": "round,pad=0.4"})
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
''' + PIE_MPL),
    _t("forest", "Forest plot (metaanálisis)", "Estadística", "matplotlib",
       "Estimación e intervalo de confianza de cada estudio y el efecto combinado (inverso de la varianza), con I².",
       [_datos("ejemplo_metaanalisis.csv"), _p("estudio", "Estudio", "columna", "estudio"),
        _p("efecto", "Estimación", "columna", "or", numerica=True),
        _p("li", "Límite inferior del IC 95 %", "columna", "li", numerica=True),
        _p("ls", "Límite superior del IC 95 %", "columna", "ls", numerica=True),
        _p("logaritmica", "Medida de razón (OR, RR, HR): escala logarítmica", "interruptor", True),
        _p("combinado", "Calcular el efecto combinado", "interruptor", True),
        _p("color", "Color", "color", "primario")] + _comunes("forest", x="Odds ratio (IC 95 %)", y="", alto=11),
       CABEZA_MPL + r'''import numpy as np
from matplotlib.transforms import blended_transform_factory

d = datos.dropna(subset=[{{efecto}}, {{li}}, {{ls}}]).reset_index(drop=True)
t = np.log if {{logaritmica}} else (lambda v: np.asarray(v, float))
t_inv = np.exp if {{logaritmica}} else (lambda v: v)
est, se = t(d[{{efecto}}]), (t(d[{{ls}}]) - t(d[{{li}}])) / (2 * 1.96)
w = 1 / se**2
nulo = 1 if {{logaritmica}} else 0
filas = len(d) + (2 if {{combinado}} else 0)
''' + FIG + r'''y = np.arange(len(d))[::-1] + (2 if {{combinado}} else 0)
ax.hlines(y, d[{{li}}], d[{{ls}}], color="#333333", linewidth=1)
ax.scatter(d[{{efecto}}], y, s=30 + 220 * w / w.max(), marker="s", color={{color}}, zorder=3)
texto = blended_transform_factory(ax.transAxes, ax.transData)
for yi, (_, f) in zip(y, d.iterrows()):
    e_, l_, u_ = f[{{efecto}}], f[{{li}}], f[{{ls}}]
    ax.text(1.02, yi, f"{e_:.2f} [{l_:.2f}, {u_:.2f}]".replace(".", ","), transform=texto,
            va="center", fontsize="x-small")
etiquetas = list(d[{{estudio}}].astype(str))
if {{combinado}}:
    comb = np.sum(w * est) / np.sum(w)
    se_c = np.sqrt(1 / np.sum(w))
    q = np.sum(w * (est - comb) ** 2)
    i2 = max(0, (q - (len(d) - 1)) / q) * 100 if q > 0 else 0
    c, cl, cu = t_inv(comb), t_inv(comb - 1.96 * se_c), t_inv(comb + 1.96 * se_c)
    ax.fill([cl, c, cu, c], [0, 0.3, 0, -0.3], color="#333333")
    ax.text(1.02, 0, f"{c:.2f} [{cl:.2f}, {cu:.2f}]".replace(".", ","), transform=texto, va="center",
            fontsize="x-small", fontweight="bold")
    print(f"Efecto combinado: {c:.3f} (IC 95 % {cl:.3f}–{cu:.3f}); I² = {i2:.0f} %")
    etiquetas = etiquetas + ["", f"Combinado (I² = {i2:.0f} %)"]
    y = np.concatenate([y, [1, 0]])
ax.axvline(nulo, color="#999999", linestyle="--", linewidth=0.8)
if {{logaritmica}}:
    ax.set_xscale("log")
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
    x0, x1 = ax.get_xlim()
    ax.xaxis.set_major_locator(FixedLocator([v for v in (0.1, 0.2, 0.25, 0.5, 1, 2, 4, 5, 10, 20) if x0 <= v <= x1]))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
ax.set_yticks(list(y), etiquetas[: len(y)])
ax.set_ylim(-0.8, y.max() + 0.8)
ax.spines[["left"]].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.set_xlabel({{etiqueta_x}})
ax.set_ylabel({{etiqueta_y}})
''' + PIE_MPL),
]

# ---------------------------------------------------------------------------------- biomedicina
BIOMEDICINA = [
    _t("volcan", "Volcán (expresión diferencial)", "Biomedicina", "matplotlib",
       "Cambio (log2 FC) frente a significación (−log10 p) de cada gen, con umbrales y los más destacados rotulados.",
       [_datos("ejemplo_expresion.csv"), _p("x", "log2 del cambio (log2FC)", "columna", "log2fc", numerica=True),
        _p("p", "Valor p (mejor ajustado)", "columna", "padj", numerica=True),
        _p("etiqueta", "Nombre del gen", "columna", "gen", opcional=True),
        _p("umbral_fc", "Umbral de |log2FC|", "numero", 1, min=0, max=20),
        _p("umbral_p", "Umbral de p", "numero", 0.05, min=0, max=1),
        _p("rotular", "Rotular los más significativos", "numero", 10, min=0, max=100),
        _p("color_sube", "Color de los que suben", "color", "acento"),
        _p("color_baja", "Color de los que bajan", "color", "primario")]
       + _comunes("volcan", x="log2(cambio)", y="−log10(p ajustado)", alto=11),
       CABEZA_MPL + r'''import numpy as np

d = datos.dropna(subset=[{{x}}, {{p}}]).copy()
d["_menoslog"] = -np.log10(d[{{p}}].clip(lower=1e-300))
sig = d[{{p}}] < {{umbral_p}}
sube = sig & (d[{{x}}] >= {{umbral_fc}})
baja = sig & (d[{{x}}] <= -{{umbral_fc}})
print(f"Suben: {sube.sum()} · bajan: {baja.sum()} · sin cambio: {(~(sube | baja)).sum()}")
''' + FIG + r'''ax.scatter(d.loc[~(sube | baja), {{x}}], d.loc[~(sube | baja), "_menoslog"], s=6, color="#BBBBBB", linewidths=0,
           label=f"Sin cambio ({(~(sube | baja)).sum()})")
ax.scatter(d.loc[sube, {{x}}], d.loc[sube, "_menoslog"], s=10, color={{color_sube}}, linewidths=0, label=f"Suben ({sube.sum()})")
ax.scatter(d.loc[baja, {{x}}], d.loc[baja, "_menoslog"], s=10, color={{color_baja}}, linewidths=0, label=f"Bajan ({baja.sum()})")
ax.axhline(-np.log10({{umbral_p}}), color="#999999", linestyle="--", linewidth=0.8)
for v in (-{{umbral_fc}}, {{umbral_fc}}):
    ax.axvline(v, color="#999999", linestyle="--", linewidth=0.8)
if {{etiqueta}} and int({{rotular}}) > 0:
    for _, f in d[sube | baja].nsmallest(int({{rotular}}), {{p}}).iterrows():
        ax.annotate(str(f[{{etiqueta}}]), (f[{{x}}], f["_menoslog"]), xytext=(3, 3), textcoords="offset points",
                    fontsize="xx-small")
ax.set_xlabel({{etiqueta_x}})
ax.set_ylabel({{etiqueta_y}})
ax.legend(frameon=False, fontsize="small", loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
''' + PIE_MPL),
    _t("manhattan", "Manhattan (GWAS)", "Biomedicina", "matplotlib",
       "Significación (−log10 p) de cada variante a lo largo del genoma, por cromosoma, con los umbrales habituales.",
       [_datos("ejemplo_gwas.csv"), _p("cromosoma", "Cromosoma", "columna", "cromosoma"),
        _p("posicion", "Posición", "columna", "posicion", numerica=True),
        _p("p", "Valor p", "columna", "pvalor", numerica=True),
        _p("etiqueta", "Nombre de la variante", "columna", "snp", opcional=True),
        _p("umbral", "Umbral de significación genómica", "numero", 5e-8, min=0, max=1),
        _p("sugerente", "Umbral sugerente (0 = no)", "numero", 1e-5, min=0, max=1), PALETA]
       + _comunes("manhattan", x="Cromosoma", y="−log10(p)", alto=9, ),
       CABEZA_MPL + COLORES_N + r'''import numpy as np

d = datos.dropna(subset=[{{cromosoma}}, {{posicion}}, {{p}}]).copy()


def clave(c):                                         # 1, 2, …, 22, X, Y, MT
    c = str(c).replace("chr", "")
    return (0, int(c)) if c.isdigit() else (1, {"X": 23, "Y": 24, "MT": 25, "M": 25}.get(c.upper(), 99))


cromosomas = sorted(d[{{cromosoma}}].unique(), key=clave)
desplazamiento, centros, inicio = {}, [], 0
for c in cromosomas:
    largo = d.loc[d[{{cromosoma}}] == c, {{posicion}}].max()
    desplazamiento[c] = inicio
    centros.append(inicio + largo / 2)
    inicio += largo * 1.02
d["_x"] = d[{{posicion}}] + d[{{cromosoma}}].map(desplazamiento)
d["_y"] = -np.log10(d[{{p}}].clip(lower=1e-300))
dos = colores_n(2)
''' + FIG + r'''for k, c in enumerate(cromosomas):
    parte = d[d[{{cromosoma}}] == c]
    ax.scatter(parte["_x"], parte["_y"], s=3, color=dos[k % 2], linewidths=0, rasterized=True)
ax.axhline(-np.log10({{umbral}}), color="#C0392B", linestyle="--", linewidth=0.8)
if {{sugerente}}:
    ax.axhline(-np.log10({{sugerente}}), color="#999999", linestyle=":", linewidth=0.8)
signif = d[d[{{p}}] < {{umbral}}]
print("Variantes con p < " + str({{umbral}}) + f": {len(signif)}")
if {{etiqueta}} and len(signif):
    for _, f in signif.loc[signif.groupby({{cromosoma}})[{{p}}].idxmin()].iterrows():
        ax.annotate(str(f[{{etiqueta}}]), (f["_x"], f["_y"]), xytext=(3, 3), textcoords="offset points", fontsize="xx-small")
ax.set_xticks(centros, [str(c) for c in cromosomas], fontsize="x-small")
ax.set_xlim(0, inicio)
ax.set_ylim(0, d["_y"].max() * 1.08)
ax.set_xlabel({{etiqueta_x}})
ax.set_ylabel({{etiqueta_y}})
''' + PIE_MPL),
    _t("kaplan-meier", "Supervivencia (Kaplan-Meier)", "Biomedicina", "matplotlib",
       "Curvas de supervivencia con censuras, intervalo de confianza, prueba log-rank y pacientes en riesgo.",
       [_datos("ejemplo_supervivencia.csv"), _p("tiempo", "Tiempo", "columna", "tiempo_meses", numerica=True),
        _p("evento", "Evento (1 = ocurrió, 0 = censurado)", "columna", "evento", numerica=True),
        _p("grupo", "Una curva por", "columna", "grupo", opcional=True),
        _p("ic", "Intervalo de confianza del 95 %", "interruptor", True),
        _p("riesgo", "Tabla de pacientes en riesgo", "interruptor", True), PALETA]
       + _comunes("kaplan_meier", x="Tiempo (meses)", y="Probabilidad de supervivencia", alto=11),
       CABEZA_MPL + COLORES_N + r'''import numpy as np
from scipy import stats

d = datos.dropna(subset=[{{tiempo}}, {{evento}}])
grupos = [(None, d)] if not {{grupo}} else list(d.groupby({{grupo}}, sort=False))


def kaplan_meier(t, e):
    """Tiempos, supervivencia y su varianza de Greenwood (acumulada)."""
    tiempos, s, suma = [0.0], [1.0], [0.0]
    for u in np.unique(t[e == 1]):
        n, k = (t >= u).sum(), ((t == u) & (e == 1)).sum()
        s.append(s[-1] * (1 - k / n))
        suma.append(suma[-1] + (k / (n * (n - k)) if n > k else 0))
        tiempos.append(u)
    return np.array(tiempos), np.array(s), np.array(suma)


if {{riesgo}}:
    fig, (ax, ax_r) = plt.subplots(2, 1, figsize=({{ancho}} / 2.54, {{alto}} / 2.54), sharex=True,
                                   gridspec_kw={"height_ratios": [4, 1]})
else:
    fig, ax = plt.subplots(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
colores = colores_n(len(grupos))
for (nombre, parte), color in zip(grupos, colores):
    t, e = parte[{{tiempo}}].to_numpy(float), parte[{{evento}}].to_numpy(int)
    tt, s, g = kaplan_meier(t, e)
    if t.max() > tt[-1]:                               # la curva sigue hasta el último seguimiento
        tt, s, g = np.append(tt, t.max()), np.append(s, s[-1]), np.append(g, g[-1])
    etiqueta = ("Todos" if nombre is None else str(nombre)) + f" (n = {len(t)})"
    ax.step(tt, s, where="post", color=color, linewidth=1.6, label=etiqueta)
    if {{ic}}:
        se = np.sqrt(g)
        ax.fill_between(tt, np.clip(s * np.exp(-1.96 * se), 0, 1), np.clip(s * np.exp(1.96 * se), 0, 1),
                        step="post", color=color, alpha=0.15, linewidth=0)
    censuras = t[e == 0]
    ax.scatter(censuras, s[np.searchsorted(tt, censuras, side="right") - 1], marker="|", s=40, color=color)
    mediana = tt[np.argmax(s <= 0.5)] if (s <= 0.5).any() else float("nan")
    print(f"{etiqueta}: mediana de supervivencia = {mediana:.3g}")
if len(grupos) > 1:                                    # prueba log-rank
    t_all, e_all = d[{{tiempo}}].to_numpy(float), d[{{evento}}].to_numpy(int)
    g_all = d[{{grupo}}].to_numpy()
    nombres = [n for n, _ in grupos]
    O, E, V = np.zeros(len(nombres)), np.zeros(len(nombres)), np.zeros((len(nombres), len(nombres)))
    for u in np.unique(t_all[e_all == 1]):
        n_g = np.array([((t_all >= u) & (g_all == n)).sum() for n in nombres], float)
        d_g = np.array([((t_all == u) & (e_all == 1) & (g_all == n)).sum() for n in nombres], float)
        n_t, d_t = n_g.sum(), d_g.sum()
        O += d_g
        E += d_t * n_g / n_t
        if n_t > 1:
            V += d_t * (n_t - d_t) / (n_t - 1) * (np.diag(n_g / n_t) - np.outer(n_g, n_g) / n_t**2)
    dif = (O - E)[:-1]
    chi = float(dif @ np.linalg.solve(V[:-1, :-1], dif))
    p = stats.chi2.sf(chi, len(nombres) - 1)
    print(f"Log-rank: χ² = {chi:.2f}, p = {p:.3g}")
    ax.text(0.98, 0.95, ("Log-rank p < 0,001" if p < 0.001 else f"Log-rank p = {p:.3f}".replace(".", ",")),
            transform=ax.transAxes, ha="right", va="top", fontsize="small")
ax.set_ylim(0, 1.03)
ax.set_xlim(left=0)
ax.set_ylabel({{etiqueta_y}})
ax.legend(frameon=False, loc="lower left", fontsize="small")
if {{riesgo}}:
    marcas = [m for m in ax.get_xticks() if 0 <= m <= d[{{tiempo}}].max()]
    for fila, ((nombre, parte), color) in enumerate(zip(grupos, colores)):
        for m in marcas:
            ax_r.text(m, -fila, str(int((parte[{{tiempo}}] >= m).sum())), ha="center", va="center",
                      fontsize="x-small", color=color)
    ax_r.set_ylim(-len(grupos) + 0.5, 0.5)
    ax_r.set_yticks([-k for k in range(len(grupos))], ["Todos" if n is None else str(n) for n, _ in grupos],
                    fontsize="x-small")
    ax_r.tick_params(axis="y", length=0, pad=14)
    ax_r.spines[["top", "right", "left"]].set_visible(False)
    ax_r.set_title("En riesgo", fontsize="x-small", loc="left")
    ax_r.set_xlabel({{etiqueta_x}})
else:
    ax.set_xlabel({{etiqueta_x}})
''' + PIE_MPL),
    _t("dosis-respuesta", "Dosis-respuesta (CI50)", "Biomedicina", "matplotlib",
       "Ajuste logístico de 4 parámetros por compuesto, en escala logarítmica, con su CI50 (o CE50).",
       [_datos("ejemplo_dosis.csv"), _p("x", "Dosis", "columna", "dosis_um", numerica=True),
        _p("y", "Respuesta", "columna", "viabilidad", numerica=True),
        _p("grupo", "Una curva por", "columna", "compuesto", opcional=True),
        _p("medida", "Nombre de la medida", "opcion", "CI50", opciones=["CI50", "CE50", "DL50", "IC50", "EC50"]),
        _p("unidad", "Unidad de la dosis", "texto", "µM"), PALETA]
       + _comunes("dosis_respuesta", x="Dosis (µM)", y="Viabilidad (%)"),
       CABEZA_MPL + COLORES_N + r'''import numpy as np
from scipy.optimize import curve_fit


def logistica4(x, abajo, arriba, log_c50, hill):
    return abajo + (arriba - abajo) / (1 + 10 ** ((np.log10(x) - log_c50) * hill))


d = datos[datos[{{x}}] > 0]
grupos = [(None, d)] if not {{grupo}} else list(d.groupby({{grupo}}, sort=False))
xs = np.logspace(np.log10(d[{{x}}].min()) - 0.3, np.log10(d[{{x}}].max()) + 0.3, 300)
''' + FIG + r'''for (nombre, parte), color in zip(grupos, colores_n(len(grupos))):
    x, y = parte[{{x}}].to_numpy(float), parte[{{y}}].to_numpy(float)
    resumen = parte.groupby({{x}})[{{y}}].agg(["mean", "std"])
    ax.errorbar(resumen.index, resumen["mean"], yerr=resumen["std"], fmt="o", color=color, markersize=4,
                capsize=2, linewidth=0.8)
    try:
        par, _ = curve_fit(logistica4, x, y, p0=[y.min(), y.max(), np.log10(np.median(x)), 1], maxfev=20000)
        c50 = 10 ** par[2]
        texto = " · " + str({{medida}}) + f" = {c50:.3g} " + str({{unidad}})
        ax.plot(xs, logistica4(xs, *par), color=color, linewidth=1.6, label=("" if nombre is None else str(nombre)) + texto)
        print(f"{nombre}: abajo {par[0]:.3g}, arriba {par[1]:.3g}, " + {{medida}} + f" {c50:.3g}, Hill {par[3]:.3g}")
    except RuntimeError:
        print(f"{nombre}: el ajuste no convergió")
ax.set_xscale("log")
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
ax.legend(frameon=False, fontsize="small")
''' + PIE_MPL),
    _t("venn", "Diagrama de Venn", "Biomedicina", "matplotlib",
       "Cuántos elementos (genes, especies…) comparten dos o tres conjuntos. Los datos van en formato largo.",
       [_datos("ejemplo_conjuntos.csv"), _p("elemento", "Elemento", "columna", "elemento"),
        _p("conjunto", "Conjunto", "columna", "conjunto"), PALETA] + _sin_ejes("venn", alto=11, ancho=13),
       CABEZA_MPL + COLORES_N + r'''from matplotlib.patches import Circle

conjuntos = {str(k): set(v) for k, v in datos.groupby({{conjunto}}, sort=False)[{{elemento}}]}
if len(conjuntos) > 3:
    print("Hay más de tres conjuntos: se usan los tres mayores.")
nombres = sorted(conjuntos, key=lambda k: -len(conjuntos[k]))[:3]
s = [conjuntos[n] for n in nombres]
''' + FIG + r'''colores = colores_n(len(s))
if len(s) == 2:
    centros = [(-0.55, 0), (0.55, 0)]
    regiones = {(-1.0, 0): s[0] - s[1], (1.0, 0): s[1] - s[0], (0, 0): s[0] & s[1]}
    rotulos = [(-1.0, 1.2), (1.0, 1.2)]
else:
    centros = [(-0.6, 0.35), (0.6, 0.35), (0, -0.65)]
    a, b, c = s
    regiones = {(-1.05, 0.65): a - b - c, (1.05, 0.65): b - a - c, (0, -1.25): c - a - b,
                (0, 0.75): (a & b) - c, (-0.65, -0.35): (a & c) - b, (0.65, -0.35): (b & c) - a, (0, 0.05): a & b & c}
    rotulos = [(-1.3, 1.5), (1.3, 1.5), (0, -1.95)]
for (cx, cy), color in zip(centros, colores):
    ax.add_patch(Circle((cx, cy), 1.0, facecolor=color, alpha=0.3, edgecolor=color, linewidth=1.5))
for (x, y), elementos in regiones.items():
    ax.text(x, y, str(len(elementos)), ha="center", va="center", fontsize="medium")
for (x, y), n, color, conjunto in zip(rotulos, nombres, colores, s):
    ax.text(x, y, f"{n}\n(n = {len(conjunto)})", ha="center", va="center", fontsize="small", color=color,
            fontweight="bold")
ax.set_xlim(-2.2, 2.2)
ax.set_ylim(-2.3, 1.9)
ax.set_aspect("equal")
''' + PIE_SIN_EJES),
]

# ------------------------------------------------------------------------------ señales y superficies
SENALES = [
    _t("espectro-picos", "Espectro con picos", "Señales y superficies", "matplotlib",
       "Una señal (espectro, cromatograma, difractograma…) con sus picos detectados y rotulados.",
       [_datos("ejemplo_espectro.csv"), _p("x", "Eje x", "columna", "longitud_onda_nm", numerica=True),
        _p("y", "Intensidad", "columna", "intensidad", numerica=True),
        _p("suavizado", "Suavizado Savitzky-Golay (puntos; 1 = sin)", "numero", 15, min=1, max=501),
        _p("prominencia", "Prominencia mínima de un pico (fracción del rango)", "numero", 0.08, min=0.001, max=1),
        _p("rotular", "Rotular los picos", "interruptor", True),
        _p("color", "Color", "color", "primario")] + _comunes("espectro", x="Longitud de onda (nm)", y="Intensidad"),
       CABEZA_MPL + r'''import numpy as np
from scipy.signal import find_peaks, savgol_filter

d = datos[[{{x}}, {{y}}]].dropna().sort_values({{x}})
x, y = d[{{x}}].to_numpy(float), d[{{y}}].to_numpy(float)
ventana = int({{suavizado}})
if ventana > 3:
    ventana += ventana % 2 == 0                        # tiene que ser impar
    y = savgol_filter(y, min(ventana, len(y) - 1 - (len(y) % 2 == 0)), 3)
picos, props = find_peaks(y, prominence={{prominencia}} * (y.max() - y.min()))
print("Picos en:", ", ".join(f"{x[k]:.4g}" for k in picos))
''' + FIG + r'''ax.plot(x, y, color={{color}}, linewidth=1.1)
ax.scatter(x[picos], y[picos], color="#C0392B", s=14, zorder=3)
if {{rotular}}:
    for k in picos:
        ax.annotate(f"{x[k]:.4g}", (x[k], y[k]), xytext=(0, 6), textcoords="offset points", ha="center",
                    fontsize="x-small", rotation=90)
ax.set_ylim(top=y.max() * 1.18)
ax.margins(x=0)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
''' + PIE_MPL),
    _t("superficie-3d", "Superficie 3D y contornos", "Señales y superficies", "matplotlib",
       "Una variable z sobre una malla x, y: superficie 3D, mapa de contornos o ambos.",
       [_datos("ejemplo_superficie.csv"), _p("x", "x", "columna", "x", numerica=True),
        _p("y", "y", "columna", "y", numerica=True), _p("z", "z", "columna", "z", numerica=True),
        _p("estilo", "Estilo", "opcion", "Superficie 3D con contornos",
           opciones=["Superficie 3D con contornos", "Superficie 3D", "Contornos rellenos (2D)"]),
        _p("mapa_color", "Mapa de color", "opcion", "viridis", opciones=["viridis", "magma", "cividis", "coolwarm", "terrain", "RdBu_r"]),
        *VISTA_3D] + _comunes("superficie", alto=12),
       CABEZA_MPL + r'''import numpy as np

malla = datos.pivot_table(index={{y}}, columns={{x}}, values={{z}}, aggfunc="mean").sort_index().sort_index(axis=1)
X, Y = np.meshgrid(malla.columns.to_numpy(float), malla.index.to_numpy(float))
Z = malla.to_numpy(float)
fig = plt.figure(figsize=({{ancho}} / 2.54, {{alto}} / 2.54))
if {{estilo}} == "Contornos rellenos (2D)":
    ax = fig.add_subplot()
    relleno = ax.contourf(X, Y, Z, levels=20, cmap={{mapa_color}})
    lineas = ax.contour(X, Y, Z, levels=10, colors="black", linewidths=0.4)
    ax.clabel(lineas, fontsize="xx-small")
    fig.colorbar(relleno, ax=ax, label={{z}}).outline.set_visible(False)
    ax.set_aspect("equal")
else:
    ax = fig.add_subplot(projection="3d")
    sup = ax.plot_surface(X, Y, Z, cmap={{mapa_color}}, linewidth=0, antialiased=True, rstride=1, cstride=1)
    if {{estilo}} == "Superficie 3D con contornos":
        ax.contourf(X, Y, Z, zdir="z", offset=np.nanmin(Z) - 0.1 * np.ptp(Z[np.isfinite(Z)]), levels=15,
                    cmap={{mapa_color}}, alpha=0.7)
        ax.set_zlim(np.nanmin(Z) - 0.1 * np.ptp(Z[np.isfinite(Z)]), np.nanmax(Z))
    ax.set_zlabel({{z}})
    ax.view_init(elev={{elevacion}}, azim={{giro}})
    fig.colorbar(sup, ax=ax, shrink=0.6, pad=0.1, label={{z}}).outline.set_visible(False)
ax.set_xlabel({{etiqueta_x}} or {{x}})
ax.set_ylabel({{etiqueta_y}} or {{y}})
''' + PIE_3D),
]

CATEGORIAS_CIENCIA = ["Multivariado", "Aprendizaje automático", "Estadística", "Biomedicina", "Señales y superficies"]
CIENCIA = MULTIVARIADO + APRENDIZAJE + ESTADISTICA + BIOMEDICINA + SENALES
