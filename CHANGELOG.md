# Registro de cambios

Todos los cambios relevantes de DocsLab se registran en este archivo.

El formato sigue [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[Versionado Semántico 2.0.0](https://semver.org/lang/es/). La política completa está en
[`docs/VERSIONADO.md`](docs/VERSIONADO.md).

Tipos de entrada: **Añadido**, **Cambiado**, **Obsoleto**, **Eliminado**, **Corregido** y **Seguridad**.

## [Sin publicar]

_Nada todavía._

## [1.1.0] - 2026-11-18

Huella: [`huella/v1.1.0.json`](huella/v1.1.0.json). Versiones: aplicación 1.1.0 · `.sty` 1.0.1 · esquema 1 · licencia AGPL-3.0-only.

### Añadido
- **Licencia GNU AGPL-3.0-only** (`LICENSE`, texto canónico). Cabecera `SPDX-License-Identifier` en los 70 archivos de código propio, `docslab.__license__`, campo `licencia` en `GET /api/estado` y sección «Licencia» en el LEEME.
- **Migraciones del esquema del modelo** (F-25): `docslab/migraciones.py`, con registro `@migracion(desde=N)` y aplicación en cadena desde `modelo.normalizar()`. Al abrir un proyecto que necesita migrar se guarda una copia en `historial/modelo-antes-de-esquema-<N>.json`. Los proyectos de un esquema más nuevo no se abren (HTTP 400, «Actualiza DocsLab para abrirlo»).
- `tests/test_migraciones.py` y fixtures del esquema 1 en `tests/fixtures/esquemas/v1/`: un modelo actual, uno heredado de DocsLab 2.1.0 (`"esquema": 2`) y uno sin clave.
- `docs/MIGRACIONES.md`: funcionamiento y procedimiento para añadir una migración.
- `herramientas/huella.py` registra la licencia y compara sus cambios.

### Cambiado
- La versión del esquema se guarda en la clave **`version_esquema`** en lugar de `esquema`. Los `modelo.json` con la clave antigua (1 o 2) o sin clave se reconocen como esquema 1 y se actualizan al guardarse; no hace falta ninguna acción. Así el futuro esquema 2 no se confunde con los archivos de DocsLab 2.1.0, que guardaban `"esquema": 2`.
- Plantillas incluidas: `modelo.json` con `version_esquema`.
- `postercientifico.sty` 1.0.1: solo se añade la cabecera de licencia. Las copias de las plantillas LaTeX se sincronizan.
- `ejemplo_capas.tex`: el pie ya no fija la versión de la `.sty`.


## [1.0.1] - 2026-11-18

Huella: [`huella/v1.0.1.json`](huella/v1.0.1.json). Versiones: aplicación 1.0.1 · `.sty` 1.0.0 (sin cambios) · esquema 1.

### Corregido
- `plantillas/catalogo-latex` y `plantillas/ejemplo-capas-latex` usan ahora la `postercientifico.sty` vigente (v1.0.0) en lugar de la copia antigua «v2.0». Ambas compilan; el catálogo mantiene las mismas 7 páginas que con la copia antigua.
- `ejemplo_capas.tex` (plantilla y fuente en `herramientas/fuentes/`): la cabecera y el pie dicen «v1.0.0» en lugar de «v2».

### Añadido
- `tests/test_version.py`: comprueba que las versiones siguen SemVer, que `__version_sty__` coincide con `\ProvidesPackage`, que las copias de la `.sty` en las plantillas son idénticas a la vigente, que las plantillas usan el esquema actual, que la versión figura en el CHANGELOG y que `docs/API.md` está al día.

### Problemas conocidos
- Las miniaturas (`miniatura.png`) de las dos plantillas LaTeX no se regeneraron; el único cambio visible es el texto del pie de `ejemplo-capas-latex`.
- El LEEME describe el catálogo como «de 6 páginas», pero en este entorno compila en 7, igual con la `.sty` antigua que con la vigente. [NO VERIFICADO] Puede deberse a la falta de separación de palabras en español en este TeX Live.

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
- ~~`plantillas/catalogo-latex` y `plantillas/ejemplo-capas-latex` llevan una copia antigua de `postercientifico.sty`.~~ Corregido en 1.0.1.
- ~~No hay migraciones del esquema del modelo.~~ Resuelto en 1.1.0.
- ~~El proyecto no tiene archivo de licencia propio.~~ Resuelto en 1.1.0 (AGPL-3.0-only).
- En un TeX Live sin `texlive-lang-spanish` ni `luatex85.sty` fallan 11 pruebas (las 9 de compilación de plantillas, una de la API y una de LuaLaTeX).
- La API no tiene autenticación y los cuadernos ejecutan código arbitrario (ver `SECURITY.md`).

[Sin publicar]: ../../compare/v1.1.0...HEAD
[1.1.0]: ../../compare/v1.0.1...v1.1.0
[1.0.1]: ../../compare/v1.0.0...v1.0.1
[1.0.0]: ../../releases/tag/v1.0.0
