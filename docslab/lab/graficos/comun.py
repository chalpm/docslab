# SPDX-License-Identifier: AGPL-3.0-only
"""Piezas comunes de las plantillas de gráficos: parámetros, cabeceras y pies de código.

Las usan graficos.py (las plantillas de siempre) y graficos_galeria.py (las de la galería).
"""
from __future__ import annotations


def _p(nombre, etiqueta, tipo, defecto=None, **mas):
    return dict(nombre=nombre, etiqueta=etiqueta, tipo=tipo, defecto=defecto, **mas)


DATOS = _p("datos", "Datos", "datos", {"modo": "archivo", "archivo": "ejemplo.csv"})


def _comunes(nombre, x="", y="", alto=9):
    return [
        _p("titulo", "Título", "texto", ""),
        _p("etiqueta_x", "Rótulo del eje x", "texto", x, ayuda="Vacío = el nombre de la columna."),
        _p("etiqueta_y", "Rótulo del eje y", "texto", y),
        _p("ancho", "Ancho (cm)", "numero", 14, min=3, max=60),
        _p("alto", "Alto (cm)", "numero", alto, min=3, max=60),
        _p("letra", "Tamaño de letra (pt)", "numero", 10, min=5, max=30),
        _p("salida", "Guardar como", "texto", f"figuras/{nombre}.pdf",
           ayuda="Dentro de la carpeta del cuaderno. Con .pdf queda vectorial; también vale .png."),
    ]


CABEZA_MPL = '''import os
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": {{letra}}})
datos = {{datos}}
'''
PIE_MPL = '''
ax.set_title({{titulo}})
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
os.makedirs(os.path.dirname({{salida}}) or ".", exist_ok=True)
fig.savefig({{salida}}, bbox_inches="tight", dpi=300)
plt.show()
'''
CABEZA_SNS = CABEZA_MPL.replace("import matplotlib.pyplot as plt", "import matplotlib.pyplot as plt\nimport seaborn as sns")
CABEZA_PX = '''import os
import pandas as pd
import plotly.express as px

datos = {{datos}}
'''
PIE_PX = '''
fig.update_layout(template="simple_white", font_size={{letra}}, width={{ancho}} * 38, height={{alto}} * 38,
                  title={{titulo}} or None)
os.makedirs(os.path.dirname({{salida}}) or ".", exist_ok=True)
try:
    fig.write_image({{salida}})          # imagen fija para el documento
except Exception as error:               # hace falta kaleido (pip install kaleido) y Chrome
    print("No se pudo guardar la imagen:", error)
fig.show()
'''
