# SPDX-License-Identifier: AGPL-3.0-only
"""DocsLab · editor web de documentos científicos con LaTeX (postercientifico.sty).

Versionado: SemVer 2.0.0. Ver CHANGELOG.md y docs/VERSIONADO.md.
"""
__version__ = "1.9.0"
__version_sty__ = "1.1.0"   # latex/postercientifico.sty

# Python mínimo para el servidor (lo comprueban servidor.py y los lanzadores). El código que generan las
# plantillas de gráficos sigue valiendo en Python 3.9, porque puede correr en otro núcleo o en Colab.
PYTHON_MINIMO = (3, 11)

__license__ = "AGPL-3.0-only"   # aplicación; ver LICENSE
__license_sty__ = "LPPL-1.3c"   # postercientifico.sty; ver latex/LICENSE-LPPL-1.3c.txt
