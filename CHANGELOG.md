# Registro de cambios

Todos los cambios relevantes de DocsLab se registran en este archivo.

El formato sigue [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[Versionado Semántico 2.0.0](https://semver.org/lang/es/). La política completa está en
[`docs/VERSIONADO.md`](docs/VERSIONADO.md).

Tipos de entrada: **Añadido**, **Cambiado**, **Obsoleto**, **Eliminado**, **Corregido** y **Seguridad**.

## [Sin publicar]

_Nada todavía._

## [1.4.0] - 2026-11-18

Huella: [`huella/v1.4.0.json`](huella/v1.4.0.json). Versiones: aplicación 1.4.0 · `.sty` 1.1.0 (sin cambios) · esquema 1.

### Añadido
- **25 plantillas de análisis científico y de datos (F-27)**, en 5 categorías nuevas del LAB. Ahora hay 73 plantillas.
  - Multivariado: PCA, PCA 3D, biplot, varianza explicada, t-SNE, t-SNE 3D, NMDS/MDS y mapa de calor con agrupamiento.
  - Aprendizaje automático: k-means, elegir k (codo y silueta), curva ROC y matriz de confusión.
  - Estadística: comparación de grupos con valor p, raincloud, Q-Q, Bland-Altman, ajuste de curva y forest plot.
  - Biomedicina: volcán, Manhattan, Kaplan-Meier, dosis-respuesta (CI50) y Venn.
  - Señales y superficies: espectro con picos y superficie 3D.
- Cada una escribe sus estadísticos en la salida de la celda (varianza explicada, estrés, AUC, valores p corregidos, CI50, medianas, log-rank…).
- 11 archivos de datos de ejemplo simulados para estas plantillas (`datos_ejemplo/`, documentados en su LEEME).
- Pruebas:
  - `test_el_codigo_compila_en_un_python_antiguo` compila el código de las 73 plantillas con Python 3.9–3.11 si hay uno instalado.
  - `test_los_numeros_pequenos_no_se_redondean_a_cero` comprueba la corrección del redondeo.
  - Además, las 25 plantillas nuevas se ejecutan con sus datos de ejemplo.

### Cambiado
- **Nueva dependencia obligatoria:** `scikit-learn>=1.2`. Los lanzadores la instalan solos.
- `CATEGORIAS` suma Multivariado, Aprendizaje automático, Estadística, Biomedicina, y Señales y superficies. Estas plantillas no enlazan a The R Graph Gallery.

### Corregido
- **Parámetros numéricos pequeños de las plantillas:** se redondeaban a 6 decimales, así que un umbral como 5e-8 llegaba al código como 0. Ahora se conservan 10 cifras significativas.
- La prueba `test_el_codigo_vale_en_python_3_9` (1.3.0) no detectaba las comillas anidadas en f-strings: con Python 3.12 o posterior, `ast.parse(feature_version=…)` no aplica esa restricción. Se renombra a `test_el_codigo_es_python_valido` y se añade la compilación real con un Python antiguo. Las 48 plantillas de 1.3.0 compilaban bien con Python 3.11.

### Problemas conocidos
- `tests/test_lab.py::test_ejecutar_celda_a_celda_conserva_las_variables` puede fallar con el equipo muy cargado: espera 90 s a que arranque el núcleo de Jupyter. Falló en 1 de 3 ejecuciones de la suite completa en un contenedor de 2 CPU, y pasa sola y al repetir.
- UMAP no se incluye: necesita `umap-learn` (con numba), una dependencia pesada.


## [1.3.0] - 2026-11-18

Huella: [`huella/v1.3.0.json`](huella/v1.3.0.json). Versiones: aplicación 1.3.0 · `.sty` 1.1.0 (sin cambios) · esquema 1.

### Añadido
- **Galería de gráficos (F-26):** 35 plantillas nuevas para el LAB que cubren, con las 13 anteriores, los 41 tipos de gráfico de [The R Graph Gallery](https://r-graph-gallery.com/), adaptados a Python. Total: 48 plantillas.
  - Distribución: densidad, crestas (ridgeline) y enjambre (beeswarm).
  - Correlación: mapa de calor, correlograma, burbujas, dispersión conectada y densidad 2D.
  - Ranking: radar, nube de palabras, coordenadas paralelas, piruleta, barras circulares y tabla.
  - Partes de un todo: treemap, dona, pastel, dendrograma, empaquetado circular y gofre (waffle).
  - Evolución: área, áreas apiladas, flujo (streamgraph) y serie temporal.
  - Mapas: mapa con puntos, coropletas, mapa de hexágonos, cartograma de Dorling, conexiones y mapa de burbujas.
  - Flujos: cuerdas, red, Sankey, arcos y agrupamiento de aristas (edge bundling).
- Todas usan matplotlib o seaborn (el dendrograma, también scipy): funcionan sin conexión y sin Chrome. Los algoritmos (treemap, empaquetado, disposición por fuerzas, Dorling, círculo máximo, nube de palabras) van en el propio código, que se puede editar.
- **Categorías** en el diálogo de gráficos (las 7 de la galería), además del filtro por biblioteca, y enlace a la página de la galería de cada tipo.
- **Datos de ejemplo por plantilla** (`docslab/datos_ejemplo/`): series, países, puntos, conexiones, red, flujos, jerarquía, puntuaciones y palabras, y el mapa base `mundo.geojson`. Los países y sus datos de población y PIB son de Natural Earth (dominio público); el resto es sintético. Su origen se documenta en `datos_ejemplo/LEEME.md`, y se regeneran con `herramientas/datos_ejemplo.py`.
- `tests/test_galeria.py`: cobertura de los 41 tipos, ejecución de las 35 con sus datos, código válido en Python 3.9 y copia segura de los datos de ejemplo.
- `herramientas/construir_graficos.py` acepta identificadores para regenerar solo algunas miniaturas.

### Cambiado
- **Nueva dependencia obligatoria:** `scipy>=1.9` (dendrograma). Los lanzadores la instalan solos.
- «Usar datos de ejemplo» (`POST …/lab/<nb>/ejemplo`) acepta `archivos` y copia los datos de la plantilla (y el mapa si lo necesita). Solo admite nombres de `datos_ejemplo/`; por defecto copia `ejemplo.csv`, como antes.
- «Probar con los datos de ejemplo» ejecuta el código en una carpeta con todos los datos de ejemplo.
- `GET /api/graficos` devuelve `categorias` y, en cada plantilla incluida, `categoria`, `referencia` y `ejemplo`.
- Las piezas comunes de las plantillas pasan a `docslab/graficos_comun.py`. `graficos.py` sigue exportando los mismos nombres.
- `SECURITY.md`: con soporte solo 1.3.x.


## [1.2.3] - 2026-11-18

Huella: [`huella/v1.2.3.json`](huella/v1.2.3.json). Versiones: aplicación 1.2.3 · `.sty` 1.1.0 (sin cambios) · esquema 1.

### Añadido
- **Catálogo de la plantilla: T36 «Referencias con estilo (gestor)»**, con la forma de uso de `\PCbibliografia` / `\PCref`, una cita volada con `\PCcitasup` y una lista numérica de ejemplo. El subtítulo y la banda de la página 3 pasan a «36 textos (T01–T36)». El catálogo sigue teniendo 7 páginas y la misma estructura; miniatura regenerada.

### Cambiado
- Para que T36 quepa en la página 3, se acortan los textos de relleno de T01, T02, T03, T08, T20 y T31 y el círculo de muestra de T25 (diámetro de 0,42 a 0,30 del ancho). Las variantes no cambian; solo su demostración.
- Cabecera de `catalogo.tex`: «Páginas 6-7» para la configuración global.

### Corregido
- LEEME y `docs/FUNCIONAL.md` (F-05): el editor ofrece 69 variantes (32 de imagen, 35 de texto, LaTeX libre y espacio). I30, I31 y T33, de posición absoluta, solo existen en la plantilla LaTeX. Antes se daba a entender que el editor incluía I01–I34 y T01–T36 completos.
- `empaquetar.py`: «36 textos».


## [1.2.2] - 2026-11-18

Huella: [`huella/v1.2.2.json`](huella/v1.2.2.json). Versiones: aplicación 1.2.2 · `.sty` 1.1.0 · esquema 1.

### Cambiado
- **LEEME reescrito** (22 secciones con índice):
  - instalación y arranque separados por sistema (Windows, macOS, Linux y Colab), con una tabla comparativa y los pasos de cada lanzador;
  - 6 diagramas Mermaid: funcionamiento general, lanzador, primer póster, compilación, LAB y arquitectura;
  - tabla de requisitos por sistema, conceptos clave, primeros pasos, mapa del editor, ubicación de los datos (copias de seguridad, cambio de equipo y migraciones), opciones y variables de entorno del servidor, y problemas frecuentes agrupados por tema y sistema.
- Datos corregidos en el LEEME:
  - el tiempo de compilación ahora es el medido;
  - la ruta real del zip para Overleaf (`dist/`, se genera con `empaquetar.py`);
  - el catálogo cubre T01–T35;
  - los nombres reales de los menús («Convertir en proyecto LaTeX», «Versiones anteriores»);
  - el árbol de código incluye `migraciones.py`, `lab.py` y `graficos.py`.
- `docs/FUNCIONAL.md` RNF-02: tiempo de compilación medido (≈ 2,4 s por cambio pequeño en A0) en lugar de la cifra no verificada de ~1 s.


## [1.2.1] - 2026-11-18

Huella: [`huella/v1.2.1.json`](huella/v1.2.1.json). Versiones: aplicación 1.2.1 · `.sty` 1.1.0 · esquema 1.

### Seguridad
- `SECURITY.md`: canal de reporte privado por correo (chalpm60@gmail.com), con la información que conviene incluir y el proceso de divulgación coordinada. GitHub Security Advisories queda previsto como canal secundario.

### Corregido
- Miniaturas de `catalogo-latex` y `ejemplo-capas-latex` regeneradas con `construir_plantillas.miniaturas()` en un TeX Live con español. Solo cambia el texto de la versión.
- `catalogo.tex` (plantilla y fuente): la cabecera y los autores ya no dicen «versión 2».
- LEEME y `empaquetar.py`: el catálogo tiene 7 páginas, no 6. Comprobado con la separación de palabras en español instalada.

### Cambiado
- `SECURITY.md`: solo la última versión MINOR recibe correcciones de seguridad; 1.0.x y 1.1.x quedan sin soporte. No se comprometen plazos de respuesta.
- `docs/VERSIONADO.md`: paquetes de TeX Live necesarios para la suite completa y un paso para actualizar la tabla de soporte al publicar.

### Verificado
- Los 11 fallos señalados como «Problemas conocidos» desde 1.0.0 eran del entorno: con `texlive-lang-spanish` y `luatex85.sty` (`texlive-luatex`) pasan las 313 pruebas (4 se saltan por herramientas opcionales).

## [1.2.0] - 2026-11-18

Huella: [`huella/v1.2.0.json`](huella/v1.2.0.json). Versiones: aplicación 1.2.0 · `.sty` 1.1.0 · esquema 1 · licencias AGPL-3.0-only (aplicación) y LPPL-1.3c (`.sty`).

### Cambiado
- **`postercientifico.sty` pasa a LPPL-1.3c o posterior** (antes AGPL-3.0-only), la licencia habitual de los paquetes LaTeX. Lleva el aviso de copyright y licencia recomendado por la LPPL, con estado de mantenimiento `maintained` y responsable Christian Alejandro Ponce Mejia. Texto de la licencia en `latex/LICENSE-LPPL-1.3c.txt`. Las copias de las plantillas LaTeX se sincronizan.
- Titular del copyright: Christian Alejandro Ponce Mejia (LEEME y `.sty`).
- `GET /api/estado` informa también `licencia_sty`; `docslab.__license_sty__`.
- `herramientas/huella.py` registra y compara la licencia de la `.sty`.
- `docs/VERSIONADO.md`: un cambio de licencia sube la versión MINOR del componente y de la aplicación.


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
- En un TeX Live sin `texlive-lang-spanish` ni `luatex85.sty` fallan 11 pruebas (las 9 de compilación de plantillas, una de la API y una de LuaLaTeX). Verificado como problema de entorno en 1.2.1.
- La API no tiene autenticación y los cuadernos ejecutan código arbitrario (ver `SECURITY.md`).

[Sin publicar]: ../../compare/v1.4.0...HEAD
[1.4.0]: ../../compare/v1.3.0...v1.4.0
[1.3.0]: ../../compare/v1.2.3...v1.3.0
[1.2.3]: ../../compare/v1.2.2...v1.2.3
[1.2.2]: ../../compare/v1.2.1...v1.2.2
[1.2.1]: ../../compare/v1.2.0...v1.2.1
[1.2.0]: ../../compare/v1.1.0...v1.2.0
[1.1.0]: ../../compare/v1.0.1...v1.1.0
[1.0.1]: ../../compare/v1.0.0...v1.0.1
[1.0.0]: ../../releases/tag/v1.0.0
