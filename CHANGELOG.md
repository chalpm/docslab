# Registro de cambios

Todos los cambios relevantes de DocsLab se registran en este archivo.

El formato sigue [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[Versionado Semántico 2.0.0](https://semver.org/lang/es/). La política completa está en
[`docs/VERSIONADO.md`](docs/VERSIONADO.md).

Tipos de entrada: **Añadido**, **Cambiado**, **Obsoleto**, **Eliminado**, **Corregido** y **Seguridad**.

## [Sin publicar]

_Nada todavía._

## [1.0.0] - 2026-11-18

Línea base. Es la primera versión con versionado formal. Huella: [`huella/v1.0.0.json`](huella/v1.0.0.json).

| Eje | Versión |
|---|---|
| Aplicación (`docslab.__version__`) | 1.0.0 |
| Plantilla LaTeX (`postercientifico.sty`) | 1.0.0 |
| Esquema del modelo JSON (`modelo.ESQUEMA`) | 1 |
| Formato de exportación de componentes | 1 |

### Añadido
- Cinco clases de documento: póster, presentación, documento, artículo y tesis (ver `docs/FUNCIONAL.md`, F-01).
- Editor visual por capas (detrás, contenido y delante), edición directa sobre la vista previa y posición libre en pósters y presentaciones.
- 69 variantes de elemento (I01–I34, T01–T36, LaTeX libre y espacio) y 12 estilos de caja.
- Gestor de referencias con 8 estilos (APA 7, Vancouver, IEEE, Chicago, MLA 9, Harvard, Nature y ACS), búsqueda por DOI e importación de BibTeX, RIS y CSL-JSON.
- Componente Lab: componentes propios hechos con piezas o con código LaTeX.
- Revisión para imprimir: resolución, tamaño de letra, contraste WCAG, gama CMYK, tipografías y contenido.
- PDF para imprenta con sangrado, marcas de corte, TrimBox/BleedBox y CMYK opcional.
- Exportación a PowerPoint, editable o como imagen.
- Tipografías: 6 clásicas, 19 libres de TeX Live y tipografías propias (.ttf/.otf) con LuaLaTeX.
- LAB: cuadernos Python celda a celda y plantillas de gráficos (matplotlib, seaborn y plotly).
- Ejecución de cuadernos `.ipynb` con recogida automática de figuras.
- Modo LaTeX (conversión de un proyecto a código editable).
- 12 plantillas incluidas, plantillas propias e importación y exportación en zip (también para Overleaf).
- Historial de versiones por proyecto (una copia cada 120 s como máximo; se conservan 30).
- Lanzadores para macOS/Linux, Windows y Google Colab.
- Herramientas de versionado: `herramientas/huella.py` (huella digital) y `herramientas/doc_api.py` (referencia de la API).
- Documentación: `CHANGELOG.md`, `SECURITY.md` y `docs/` (arquitectura, funcional, API y versionado).

### Cambiado
- Los números de versión se reinician a la línea base: la aplicación pasa de 2.1.0 a 1.0.0, la plantilla `.sty` de v3.0 a v1.0.0 y el esquema del modelo de 2 a 1. Los proyectos guardados con esquema 2 se siguen abriendo, porque `normalizar()` no comprueba el número.
- En `LEEME.md`, la cifra de pruebas pasa a 288 y se quita la referencia a la «v2» de la plantilla.

### Problemas conocidos
- `plantillas/catalogo-latex` y `plantillas/ejemplo-capas-latex` llevan una copia antigua de `postercientifico.sty` (cabecera «v2.0», 2026/10/17) que difiere de `latex/postercientifico.sty`. `herramientas/construir_plantillas.py` las regenera.
- No hay migraciones del esquema del modelo: `modelo.normalizar()` solo completa los valores por defecto.
- El proyecto no tiene archivo de licencia propio; solo están las licencias de las librerías incluidas en `static/vendor/`.
- En un TeX Live sin `texlive-lang-spanish` ni `luatex85.sty` fallan 11 pruebas (las 9 de compilación de plantillas, una de la API y una de LuaLaTeX).
- La API no tiene autenticación y los cuadernos ejecutan código arbitrario (ver `SECURITY.md`).

[Sin publicar]: ../../compare/v1.0.0...HEAD
[1.0.0]: ../../releases/tag/v1.0.0
