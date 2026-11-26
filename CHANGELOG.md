# Registro de cambios

Todos los cambios relevantes de DocsLab se registran en este archivo.

El formato sigue [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[Versionado Semántico 2.0.0](https://semver.org/lang/es/). La política completa está en
[`docs/VERSIONADO.md`](docs/VERSIONADO.md).

Tipos de entrada: **Añadido**, **Cambiado**, **Obsoleto**, **Eliminado**, **Corregido** y **Seguridad**.

## [Sin publicar]

### Añadido
- Etiquetas y Releases automáticas en GitHub (`.github/workflows/versiones.yml` y `.github/scripts/etiquetar.py`). Al subir a `main`, se crean la etiqueta anotada `vX.Y.Z` y su Release, con las notas de este CHANGELOG, de cada versión que aún no las tenga. La versión se publica en el último commit que tocó `huella/vX.Y.Z.json`, siempre que su `__version__` coincida. Nunca se mueve ni se borra una etiqueta existente.

## [1.9.1] - 2026-11-23

Huella: [`huella/v1.9.1.json`](huella/v1.9.1.json). Versiones: aplicación 1.9.1 · `.sty` 1.1.0 · esquema 1 (sin cambios). Sin cambios en la API ni en las dependencias.

### Corregido
- **Importar un zip con un `proyecto.json` dañado dejaba DocsLab sin lista de proyectos** (H-01 de la auditoría de entrega del 2026-11-22). Antes, un `proyecto.json` que no era un objeto (o con campos de otro tipo) dejaba una carpeta a medias, y desde entonces `GET /api/proyectos` daba error 500: la pantalla de inicio se quedaba en «Cargando…».
  - Ahora el zip se rechaza con un mensaje claro y no deja carpeta.
  - Un proyecto dañado en disco se salta en la lista, sin ocultar los demás.
  - Un `plantilla.json` dañado da error 400 (antes, 500).
- **Guardar a la vez podía dañar el documento** (H-02 de la misma auditoría). Todas las escrituras de un archivo usaban el mismo temporal `.tmp`; con guardados simultáneos (dos pestañas, o el autoguardado mientras un trabajo en segundo plano actualizaba el proyecto) daban error 500 y podían dejar `modelo.json` o `proyecto.json` mezclados. Un `modelo.json` dañado se abría como documento en blanco, y el siguiente autoguardado lo sobrescribía.
  - Cada escritura usa ahora su propio temporal, volcado a disco antes de renombrarlo.
  - Un candado por proyecto hace que los guardados vayan de uno en uno.
  - Un `modelo.json` dañado ya no se abre en blanco: DocsLab avisa y se recupera desde «Historial».
  - El historial solo guarda copias legibles.
- `SECURITY.md`: la tabla de soporte marcaba 1.8.x; ahora 1.9.x.
- `CHANGELOG.md`: faltaban los enlaces del pie de 1.9.0 y 1.9.1.

### Cambiado
- `LEEME.md` pasa a llamarse `README.md`, para que GitHub lo muestre en la portada del repositorio. Se actualizan las referencias en `iniciar.command`, `servidor.py`, `salidas/compilador.py`, la pantalla de inicio, `docs/README.md` y `docs/FUNCIONAL.md`. Las entradas anteriores de este CHANGELOG conservan el nombre antiguo.
- El README tiene una sección nueva, «Créditos», que reconoce el trabajo de Claude (Anthropic) en el desarrollo.

### Añadido
- `tests/test_integridad.py` (11 pruebas de regresión de H-01 y H-02).

## [1.9.0] - 2026-11-21

Huella: [`huella/v1.9.0.json`](huella/v1.9.0.json). Versiones: aplicación 1.9.0 · `.sty` 1.1.0 (sin cambios) · esquema 1 (campos opcionales nuevos, sin migración). Rutas nuevas: `POST /api/proyectos/<pid>/word` y `GET /api/proyectos/<pid>/word.docx`.

### Añadido
- **PowerPoint todo editable** (F-30). Antes, en modo «Editable», solo el texto se podía cambiar; el resto iba en una imagen de fondo. Ahora, con PyMuPDF:
  - cajas, bandas, líneas y círculos son formas de PowerPoint (rectángulo, redondeado o forma libre), con relleno, borde y transparencia;
  - cada imagen es una imagen suelta, con su recorte y su opacidad (también las de las capas);
  - todo va en el orden en que se pinta en el PDF;
  - solo van como imagen, una por pieza, las fórmulas, los gráficos vectoriales con letras, los degradados y lo dibujado con código LaTeX.
- **Animaciones en PowerPoint**: en el inspector, «Animación en PowerPoint» para cajas, elementos y elementos de capa:
  - efecto de entrada: aparecer, desvanecer, subir, barrido o aumentar;
  - inicio: al hacer clic, con la anterior o después de la anterior;
  - duración y retraso.
  Las piezas de cada caja o elemento animado se agrupan para entrar juntas.
- **Transiciones** entre diapositivas (desvanecer, empujar, barrido, cubrir, dividir) con su velocidad, por diapositiva o para todo el documento, con un botón para copiarla a todas. También en modo imagen.
- **Word (.docx)** de documentos, artículos y tesis (F-31), escrito desde el modelo y todo editable:
  - estilos de título de Word con su numeración, capítulos y apéndices;
  - portada, dedicatoria, agradecimientos, resúmenes e índices (campos de Word);
  - dos columnas, número de página y encabezado;
  - listas, tablas de Word, figuras y tablas con pie numerado (SEQ), citas y bibliografía en el estilo del proyecto;
  - fórmulas como ecuaciones de Word con pandoc, o como imagen con su código como texto alternativo si no está;
  - el código LaTeX libre, los componentes y las imágenes anotadas, como imagen recortada del PDF.
  Menú «Descargar → Word (.docx)…». `/api/estado` informa de `word` (python-docx y pandoc).
- Dependencias: `pymupdf>=1.25` (AGPL-3.0, compatible con la licencia de DocsLab) y `python-docx>=1.1`. pandoc es opcional.
- Pruebas: `tests/test_animaciones.py` (8) y `tests/test_word.py` (12), con LibreOffice para comprobar que los archivos se abren y que las animaciones se reconocen.

### Cambiado
- El modo editable de PowerPoint ya no necesita Ghostscript: PyMuPDF quita el texto del PDF. Ghostscript queda como respaldo sin PyMuPDF.

## [1.8.0] - 2026-11-19

Huella: [`huella/v1.8.0.json`](huella/v1.8.0.json). Versiones: aplicación 1.8.0 · `.sty` 1.1.0 (sin cambios) · esquema 1. Rutas sin cambios.

Aplica una lista de comprobación de seguridad de 10 puntos. Lo que no aplica a una aplicación local de una persona (panel con doble factor, protección de formularios contra bots, límite de intentos de inicio de sesión, separación entre usuarios) queda explicado en «Lista de comprobación» de `SECURITY.md`.

### Añadido
- **Copias de seguridad automáticas** (`docslab/nucleo/copias.py`):
  - Al arrancar y cada 24 h, si algo cambió, se guarda un zip de proyectos, plantillas, componentes y gráficos, sin `build/` ni `formatos/`.
  - Se conservan las 7 más recientes.
  - Variables: `DOCSLAB_COPIAS` (cuántas; `0` las desactiva), `DOCSLAB_COPIAS_DIR` (mejor en otro disco o carpeta sincronizada) y `DOCSLAB_COPIAS_HORAS`.
  - La terminal dice dónde se guardan.
- **HTTPS opcional**: `--certificado` y `--clave` (o `DOCSLAB_CERTIFICADO` y `DOCSLAB_CLAVE`), con TLS 1.2 o posterior. Pensado para `--host 0.0.0.0` con un certificado de mkcert. Si DocsLab escucha fuera de este equipo sin HTTPS, la terminal avisa de que el tráfico va sin cifrar.
- `herramientas/revisar_dependencias.py`: pip-audit de `requirements.txt` y versión del JS incluido frente a la última de npm (Vue 3.x, pdf.js 4.x, CodeMirror 5.x).
- Pruebas:
  - `tests/test_copias.py`.
  - `tests/test_servidor_red.py`: HTTPS real con un certificado de openssl y el aviso de red.
  - `tests/test_higiene.py`: ninguna clave ni archivo de secretos en el repositorio, errores sin traza y pyflakes limpio.
- `SECURITY.md`: «Lista de comprobación» con el estado de los 10 puntos.

### Cambiado
- **Errores sin detalles internos:** un fallo inesperado en un trabajo (compilar, ejecutar…) muestra un mensaje genérico, y la traza va solo a la terminal. Antes aparecía en el registro de la interfaz con tipo y ruta. Los errores propios de DocsLab mantienen su mensaje.
- Vue 3.5.44 → 3.5.45.

### Eliminado
- Código sin usar:
  - `bibliografia.autor`, `variantes.campos_imagen`, `modelo.pagina_de_fila`, `modelo.renombrar_recurso`.
  - Las constantes `OPCIONES_BLOQUE` y `GENES`.
  - Variables sin usar en `compilador`, `revision` y `bibliografia`.
  - Las importaciones de comprobación, sustituidas por `importlib.util.find_spec`.
  - pyflakes queda limpio en todo el código.

### Corregido
- Contraste del aviso «hoja vacía» de la vista previa: 5,3:1, antes 3:1.

## [1.7.0] - 2026-11-18

Huella: [`huella/v1.7.0.json`](huella/v1.7.0.json). Versiones: aplicación 1.7.0 · `.sty` 1.1.0 (sin cambios) · esquema 1. Rutas sin cambios.

### Cambiado
- **El servidor necesita Python 3.11 o posterior** (antes, 3.9). Así se instala siempre Pillow 13.0 o posterior, sin los avisos de seguridad que seguían en Python 3.9 y 3.10. El valor está en `docslab.PYTHON_MINIMO`. Las plantillas de gráficos siguen generando código válido en Python 3.9, porque puede ejecutarse en otro núcleo o en Colab.
  - **Lanzadores:** `iniciar.command` usa `DOCSLAB_PYTHON` si se indica; si no, `python3` o el `python3.14`…`python3.11` más nuevo que haya. `iniciar.bat` prueba `py -3` y luego `py -3.14`…`py -3.11` y `python`. Si solo hay un Python anterior, dicen qué versión encontraron y cómo instalar una válida.
  - **Actualización:** un `.venv` creado con un Python anterior a 3.11 se rehace solo.
  - **Arranque manual:** `servidor.py` se niega a arrancar con Python < 3.11 y lo explica.
  - `requirements.txt`: `pillow>=13.0`, sin marcadores por versión de Python.
- `iniciar.bat` se guarda con finales de línea CRLF (`.gitattributes`): con LF, `cmd.exe` puede no encontrar las etiquetas de `call :etiqueta`.
- LEEME: requisitos y pasos por sistema con Python 3.11. El `python3` de macOS es 3.9 y Ubuntu 22.04 necesita `python3.11`.
- `docs/VERSIONADO.md`: subir la versión mínima de Python es MINOR.

### Añadido
- `tests/test_lanzadores.py`: versión mínima en `requirements.txt` y `servidor.py`, y lanzador de macOS/Linux con Pythons simulados (3.10 rechazado, búsqueda de uno más nuevo, `DOCSLAB_PYTHON`, `.venv` antiguo rehecho).

## [1.6.1] - 2026-11-18

Huella: [`huella/v1.6.1.json`](huella/v1.6.1.json). Versiones: aplicación 1.6.1 · `.sty` 1.1.0 (sin cambios) · esquema 1. Contrato sin cambios.

### Corregido
- **La página entera se desplazaba al usar la rueda en el editor** y dejaba un hueco vacío debajo, sin la barra de arriba. La causa eran las casillas invisibles de los interruptores del panel derecho (`position: absolute` sin un contenedor posicionado): el navegador las situaba respecto a la página, no al panel, y alargaban la página hasta casi 3 veces la ventana. Ahora el interruptor, los paneles y el editor son su contenedor, así que no salen del panel.
- `tests/auditoria_navegador.py` comprueba que la rueda no desplaza la página en el editor, el LAB y el Componente Lab. Con 1.6.0 esta comprobación falla (alto de 2509 px en una ventana de 900).

## [1.6.0] - 2026-11-18

Huella: [`huella/v1.6.0.json`](huella/v1.6.0.json). Versiones: aplicación 1.6.0 · `.sty` 1.1.0 (sin cambios) · esquema 1. Rutas de la API sin cambios (95).

Sale de la auditoría de prelanzamiento del 2026-11-18. Es MINOR y no PATCH porque añade opciones (`DOCSLAB_HOSTS`, `DOCSLAB_MAX_NUCLEOS`) y cambia lo que la API exige a los scripts propios (ver «Seguridad»). 1.5.x deja de tener soporte.

### Seguridad
- **Las salidas HTML de los cuadernos ya no ejecutan código en DocsLab.** Hasta 1.5.1 se pintaban tal cual en la página: abrir un `.ipynb` ajeno con una salida preparada (sin ejecutarlo) permitía usar la API y, con ella, ejecutar Python. Ahora van en un `<iframe sandbox="allow-scripts">` sin el origen de DocsLab. Comprobado en Chrome contra 1.5.1 (fallaba) y 1.6.0 (no).
- **Otras webs ya no pueden usar el servidor local** (`docslab/seguridad.py`):
  - **DNS rebinding:** solo se atienden `localhost`, `*.localhost`, direcciones IP y los nombres de la nueva variable `DOCSLAB_HOSTS`; el resto recibe 403. En 1.5.1, un dominio ajeno que apuntaba a 127.0.0.1 tenía la API entera.
  - **CSRF:** POST, PUT, PATCH y DELETE exigen la cabecera `X-DocsLab: 1` (la interfaz la pone sola) y, si llevan `Origin`, que sea el propio servidor. En 1.5.1, otra web podía crear e importar proyectos.
  - **Si usas la API desde tus scripts**, añade `X-DocsLab: 1` a esas peticiones (detalles en `docs/API.md`).
- Cabeceras `Content-Security-Policy: frame-ancestors 'self'` (más Colab en ese modo), `X-Content-Type-Options: nosniff` y `Referrer-Policy: same-origin`. Los `.js`, `.mjs` y `.css` se sirven siempre con su tipo MIME.
- **Dependencias:** mínimos sin avisos conocidos (pip-audit): `flask>=3.1.3`, `pillow>=13.0` en Python 3.11 o posterior (12.3 en 3.10 y 11.3 en 3.9, las últimas que admiten esos Python, todavía con avisos), `scipy>=1.10`, `scikit-learn>=1.5`.
- **Imágenes:** Pillow solo abre los formatos esperados (PNG/JPEG, y GIF, BMP, TIFF y WEBP al convertir). La exportación a PowerPoint ya no desactiva para todo el proceso el límite contra imágenes gigantes.
- **pdf.js 3.11.174 → 4.10.38** (compilación «legacy»; sin avisos en `npm audit`). Se mantiene `isEvalSupported: false`.
- La respuesta de doi.org se lee con un tope de 2 MB.

### Añadido
- `DOCSLAB_HOSTS`: nombres de equipo extra con los que se puede abrir DocsLab (con `--host 0.0.0.0`).
- `DOCSLAB_MAX_NUCLEOS` (4 por defecto): procesos de Python del LAB a la vez. Al pasar del tope se apaga el que lleva más tiempo sin usarse, y su cuaderno lo avisa.
- Pie en el inicio con la versión, las licencias (AGPL-3.0 y LPPL-1.3c) y dónde está el código fuente.
- `tests/test_seguridad.py` (21 pruebas) y `tests/auditoria_navegador.py`: axe-core, foco en diálogos, marco aislado, CSRF y DNS rebinding en un Chrome real.

### Cambiado
- Errores 404, 405 y 500 en JSON. El 500 no muestra detalles internos y se registra en la terminal.

### Corregido
- **Accesibilidad (WCAG 2.2 AA, sin infracciones de axe en inicio, asistente, editor, LAB y Componente Lab):**
  - Los diálogos retienen el foco con Tab y lo devuelven al cerrar (`static/js/foco.js`). El asistente de documento nuevo se cierra con Esc.
  - Las tarjetas del inicio ya no anidan botones dentro de otro botón: el nombre es el botón.
  - El árbol de estructura cumple ARIA: un `role="tree"` por grupo, con los botones del grupo fuera.
  - Las celdas del cuaderno se eligen con teclado.
  - Mejor contraste del contador de ejecución del LAB.

## [1.5.1] - 2026-11-18

Huella: [`huella/v1.5.1.json`](huella/v1.5.1.json). Versiones: aplicación 1.5.1 · `.sty` 1.1.0 (sin cambios) · esquema 1. Rutas y contrato de la API idénticos a 1.5.0.

`huella.py comparar` sugiere MINOR porque cuenta los módulos movidos como nuevos; el contrato público no cambia, así que el salto es PATCH (refactorización).

### Cambiado
- **Código del servidor reorganizado en subpaquetes** (movido con historial de git):
  - `nucleo/`: almacen, modelo, migraciones, trabajos.
  - `documento/`: generador, texto, variantes, bibliografia, componentes, fuentes.
  - `salidas/`: compilador, revision, powerpoint.
  - `lab/`: `nucleos.py` (antes `lab.py`), cuadernos y `graficos/` (antes `graficos.py`, `graficos_comun.py`, `graficos_galeria.py`, `graficos_ciencia.py` y `datos_ejemplo/`).
- **`app.py` partido en 9 blueprints de Flask** en `api/` (sistema, componentes, bibliografia, plantillas, proyectos, documento, lab, graficos, trabajos). `app.py` pasa de 1195 a 66 líneas y solo configura la app y registra las áreas. Las 95 rutas, sus métodos y respuestas no cambian.
- `herramientas/doc_api.py` y `herramientas/huella.py` leen las rutas de `docslab/api/`; `docs/API.md` regenerado.
- La ruta de ejecución de celdas del LAB comprueba nbclient directamente en vez de llamar a la función de estado del servidor (mismo resultado).
- Documentación (LEEME, ARQUITECTURA, FUNCIONAL, MIGRACIONES, VERSIONADO, SECURITY) con las rutas nuevas.

### Corregido
- Prueba en navegador (`tests/e2e_navegador.py`): el paso «descargar el PDF» buscaba el botón «PDF del póster», que ya se llama «PDF». Ya pasa completa.

## [1.5.0] - 2026-11-18

Huella: [`huella/v1.5.0.json`](huella/v1.5.0.json). Versiones: aplicación 1.5.0 · `.sty` 1.1.0 (sin cambios) · esquema 1.

### Añadido
- **Cuadernos del LAB: reiniciar Python a la vista.** Hay un botón «Reiniciar» junto a «Ejecutar todo» (antes solo estaba en el menú ⋯). Reiniciar arranca un proceso nuevo: se borran las variables y se cargan los paquetes recién instalados o actualizados.
- **Borrar las variables sin reiniciar** (menú ⋯; `POST …/lab/<nb>/borrar-variables`): equivale a `%reset -f` en el mismo proceso. Es más rápido, pero no recarga los paquetes.
- **Avisos de paquetes:**
  - Cuando una celda `%pip install`, `!pip install`, `%conda install` o `uv pip install` instala algo, aparece un aviso con «Reiniciar Python» y «Reiniciar y ejecutar todo». Si pip no instaló nada («Requirement already satisfied»), no hay aviso.
  - Ante un `ModuleNotFoundError`, el aviso ofrece añadir y ejecutar `%pip install <paquete>` justo antes de la celda que falló, con el nombre de pip correcto cuando difiere del módulo (sklearn → scikit-learn, cv2 → opencv-python, PIL → pillow, umap → umap-learn…).
  - Para `google.colab`, explica que es una celda propia de Colab.
- Pruebas:
  - `test_borrar_variables_conserva_el_proceso_y_reiniciar_lo_cambia` comprueba que borrar las variables mantiene el proceso de Python y reiniciar lo cambia.
  - `test_una_celda_no_se_queda_colgada_si_se_pierde_el_idle`.
  - El recorrido completo (falla el `import`, se instala el paquete, se reinicia y funciona) se comprobó en un navegador real.

### Corregido
- **Celdas que podían quedarse en «Ejecutando» hasta una hora** si se perdía el mensaje «idle» del canal iopub. Ahora, si Python ya contestó en el canal shell, la celda se da por terminada a los 3 s. [NO VERIFICADO] Es una posible causa del fallo intermitente de `test_ejecutar_celda_a_celda_conserva_las_variables`, pero no se ha podido reproducir el fallo para confirmarlo.

### Cambiado
- `SECURITY.md`: con soporte solo 1.5.x.


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

[Sin publicar]: ../../compare/v1.9.1...HEAD
[1.9.1]: ../../compare/v1.9.0...v1.9.1
[1.9.0]: ../../compare/v1.8.0...v1.9.0
[1.8.0]: ../../compare/v1.7.0...v1.8.0
[1.7.0]: ../../compare/v1.6.1...v1.7.0
[1.6.1]: ../../compare/v1.6.0...v1.6.1
[1.6.0]: ../../compare/v1.5.1...v1.6.0
[1.5.1]: ../../compare/v1.5.0...v1.5.1
[1.5.0]: ../../compare/v1.4.0...v1.5.0
[1.4.0]: ../../compare/v1.3.0...v1.4.0
[1.3.0]: ../../compare/v1.2.3...v1.3.0
[1.2.3]: ../../compare/v1.2.2...v1.2.3
[1.2.2]: ../../compare/v1.2.1...v1.2.2
[1.2.1]: ../../compare/v1.2.0...v1.2.1
[1.2.0]: ../../compare/v1.1.0...v1.2.0
[1.1.0]: ../../compare/v1.0.1...v1.1.0
[1.0.1]: ../../compare/v1.0.0...v1.0.1
[1.0.0]: ../../releases/tag/v1.0.0
