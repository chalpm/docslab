# Especificación funcional · DocsLab 1.6.1

Catálogo de funciones con identificadores estables (**F-NN**). Cada versión futura indica en el CHANGELOG qué F-NN añade, cambia o retira. Los identificadores no se reutilizan.

Columnas: **Módulos** (backend), **API** (grupo de `docs/API.md`), **Pruebas** (archivo · funciones de prueba representativas).

| Estado | Significado |
|---|---|
| Estable | Cubierto por pruebas automáticas |
| Parcial | Cobertura indirecta o sin prueba específica |

---

## F-01 · Clases de documento
**Descripción.** Al crear un proyecto se elige su clase: póster, presentación (16:9, 16:10 o 4:3), documento, artículo o tesis. Cada clase define su estructura (filas/columnas/cajas, diapositivas o secciones con nivel), sus páginas preliminares y su numeración.
**Reglas.** Un póster es una sola hoja. Una presentación avisa de qué diapositiva no cabe. En documentos, artículos y tesis el texto pasa de una página a la siguiente y no hay posición libre.
**Módulos.** `nucleo/modelo.py` (`CLASES`, `desde_asistente`), `documento/generador.py`. **API.** Proyectos. **Pruebas.** `test_clases.py` · `test_el_asistente_crea_cada_clase`, `test_cada_clase_compila`, `test_secciones_de_una_tesis`. **Estado.** Estable.

## F-02 · Asistente de documento nuevo
**Descripción.** Elección de clase, tamaño, columnas, colores, tipografía e idioma. Ajusta la letra y las imágenes al tamaño.
**Módulos.** `nucleo/modelo.py`. **API.** `POST /api/proyectos`. **Pruebas.** `test_generador.py` · `test_asistente`, `test_asistente_ajusta_imagen_y_letra`. **Estado.** Estable.

## F-03 · Editor por capas
**Descripción.** Capas detrás, contenido y delante; mostrar, ocultar, atenuar y reordenar; capas propias con elementos (texto, imagen, forma) colocados por coordenadas, rotación, escala y opacidad.
**Módulos.** `nucleo/modelo.py` (`CAPAS_DEFECTO`, `ITEM_TIPOS`), `documento/generador.py`. **Pruebas.** `test_generador.py` · `test_capas_y_elementos_de_capa`. **Estado.** Estable.

## F-04 · Edición directa y posición libre
**Descripción.** Arrastrar cajas y elementos en la vista previa, cambiar el ancho de las columnas, editar texto con doble clic, cambiar el tamaño de los logos, soltar elementos de la cuadrícula y «Lienzo libre».
**Módulos.** `salidas/compilador.py` (marcas de posición), frontend `directa.js` y `vista.js`. **Pruebas.** `test_clases.py` · `test_una_caja_suelta_sale_de_la_cuadricula`, `test_la_caja_suelta_queda_donde_se_pone`. Interacción: `e2e_navegador.py`. **Estado.** Estable (backend) / Parcial (interacción, solo en e2e).

## F-05 · Variantes de elemento y estilos de caja
**Descripción.** 69 variantes en el editor: 32 de imagen (I01–I34 salvo I30 e I31), 35 de texto (T01–T36 salvo T33), LaTeX libre y espacio, con miniaturas, y 12 estilos de caja. I30, I31 y T33 (posición absoluta) solo existen en la plantilla LaTeX; en el editor se sustituyen por las capas (F-03) y la posición libre (F-04). El catálogo de la plantilla muestra las 70 variantes numeradas. Todas las cajas tienen un título opcional.
**Módulos.** `documento/variantes.py`, `documento/generador.py`. **API.** `GET /api/variantes`. **Pruebas.** `test_generador.py` · `test_cada_variante_genera_su_orden`, `test_titulo_oculto_en_cajas_y_cajas_de_texto`. **Estado.** Estable.

## F-06 · Texto con formato sencillo
**Descripción.** `**negrita**`, `*cursiva*`, `` `código` ``, `^sup^`, `~sub~`, `$mat$`, `[@cita]` y `{{LaTeX}}`; escape automático; párrafos separados por una línea en blanco. Conversión al modo «Código LaTeX» sin que cambie el resultado.
**Módulos.** `documento/texto.py`. **Pruebas.** `test_texto.py` (6), `test_generador.py` · `test_convertir_formato_no_cambia_el_poster`. **Estado.** Estable.

## F-07 · Referencias bibliográficas
**Descripción.** Formulario por tipo de referencia, búsqueda por DOI (doi.org), importación de BibTeX, RIS, CSL-JSON y listas de DOI, y exportación a `.bib`. Ocho estilos: APA 7, Vancouver, IEEE, Chicago autor-fecha, MLA 9, Harvard, Nature y ACS. Citas `[@a; @b, p. 12]`, numeradas por orden de lectura en los estilos numéricos, y letra a/b cuando coinciden autor y año. Lista T36: solo las citadas o todas.
**Módulos.** `documento/bibliografia.py`. **API.** Bibliografía y `GET …/bibliografia.bib`. **Pruebas.** `test_bibliografia.py` (17). **Estado.** Estable (DOI: Parcial, depende de la red).

## F-08 · Componente Lab
**Descripción.** Componentes propios hechos con piezas (título, texto, cifra, imagen, lista, icono, columnas…) o con código LaTeX con `{{campo}}`. Se pueden recrear a partir de los 69 incluidos. Biblioteca en `datos/componentes/`, con una copia dentro de cada póster y aviso de actualización. Importación y exportación en JSON (formato v1).
**Módulos.** `documento/componentes.py`. **API.** Componente Lab. **Pruebas.** `test_componentes.py` (11). **Estado.** Estable.

## F-09 · Compilación
**Descripción.** Compila al guardar o con Ctrl + S, con formato precompilado, sin recompilar si nada cambió y con la miniatura aparte. Ante un error, mantiene el último PDF correcto y lo ubica en el elemento de origen. Con MiKTeX, instala los paquetes que faltan. Avisa de lo que no cabe.
**Módulos.** `salidas/compilador.py`, `nucleo/trabajos.py`. **API.** `POST …/compilar`, `GET …/compilacion`, `…/pdf`, Trabajos. **Pruebas.** `test_api.py` · `test_compilar_errores_y_ultimo_pdf_correcto`, `test_compilar_sin_cambios_no_repite_y_miniatura_aparte`; `test_motores.py` (6). **Estado.** Estable.

## F-10 · Ajustar a una página
**Descripción.** Busca el tamaño de letra más grande con el que todo cabe. Se puede deshacer.
**Módulos.** `api/documento.py`, `salidas/compilador.py`. **API.** `POST …/ajustar`. **Pruebas.** Sin prueba específica. **Estado.** Parcial.

## F-11 · Revisión para imprimir
**Descripción.** Tamaño y páginas, resolución real de las imágenes (también dentro de las figuras PDF), tamaño de letra según el formato, contraste WCAG, colores fuera de la gama CMYK, tipografías incrustadas o de mapa de bits, textos de ejemplo, citas sin referencia y texto a menos de 5 mm del borde, con «Mostrar en el póster». Umbrales en A0: 150 ppi, 24 pt en el texto principal y 18 pt como mínimo.
**Módulos.** `salidas/revision.py`. **API.** `POST …/revisar`. **Pruebas.** `test_revision.py` (11). **Estado.** Estable.

## F-12 · PDF para imprenta
**Descripción.** Sangrado de 3 o 5 mm (alarga lo que toca el borde), marcas de corte con 10 mm de margen, TrimBox y BleedBox, y RGB o CMYK (Ghostscript). Nunca modifica el PDF del proyecto.
**Módulos.** `documento/generador.py`, `salidas/compilador.py`. **API.** `POST …/imprenta`, `GET …/imprenta.pdf|png`. **Pruebas.** `test_revision.py` · `test_pdf_para_imprenta_con_sangrado_y_marcas`, `test_pdf_para_imprenta_en_cmyk`. **Estado.** Estable.

## F-13 · Exportar a PowerPoint
**Descripción.** Una diapositiva por página. Modo editable (cada línea es un cuadro de texto sobre una imagen sin texto; las fórmulas y el texto de las figuras quedan en la imagen; necesita Ghostscript) o modo imagen. Reduce los pósters que superan el tamaño máximo de PowerPoint.
**Módulos.** `salidas/powerpoint.py`. **API.** `POST …/powerpoint`, `GET …/powerpoint.pptx`. **Pruebas.** `test_powerpoint.py` (9). **Estado.** Estable.

## F-14 · Tipografías
**Descripción.** 6 clásicas, 19 libres de TeX Live (con marca si no están instaladas) y propias (.ttf/.otf) con imitación de negrita y cursiva cuando faltan, compiladas con LuaLaTeX y con aviso de licencia de incrustación. El zip para Overleaf incluye un `latexmkrc`.
**Módulos.** `documento/fuentes.py`, `nucleo/modelo.py` (`FAMILIAS_INFO`). **API.** `…/fuentes`. **Pruebas.** `test_fuentes.py` (7). **Estado.** Estable.

## F-15 · Idioma del documento
**Descripción.** Español, inglés, portugués, francés, alemán o italiano: separación de palabras, comillas y palabras fijas de las referencias. Avisa si falta el paquete del idioma.
**Módulos.** `nucleo/modelo.py` (`IDIOMAS`), `documento/bibliografia.py`. **Pruebas.** `test_generador.py` · `test_idioma_del_poster`; `test_bibliografia.py` · `test_palabras_segun_el_idioma`. **Estado.** Estable.

## F-16 · Imágenes y recursos
**Descripción.** Subida de PNG, JPG y PDF; GIF, WEBP, TIFF y BMP se convierten a PNG; SVG opcional con cairosvg. Imagen de reserva del tamaño pedido.
**Módulos.** `nucleo/almacen.py`. **API.** `…/recursos`, `…/f/<ruta>`. **Pruebas.** `test_api.py` · `test_recursos`; `test_generador.py` · `test_imagen_de_reserva_mide_lo_pedido`. **Estado.** Estable.

## F-17 · Cuadernos (ejecución completa)
**Descripción.** Subir un `.ipynb` con sus datos o abrirlo desde una carpeta permitida (`--raices`). Ejecución con registro por celda y recogida de figuras en `recursos/cuadernos/<nb>/` con rutas estables (al volver a ejecutar, el documento se actualiza). Ajustes: carpeta de figuras, extensiones, preferir PDF, omitir celdas de Colab, parámetros inyectados, tiempo máximo y núcleo. «Traer figuras desde Colab».
**Módulos.** `lab/cuadernos.py`, `nucleo/trabajos.py`. **API.** Cuadernos, Explorador. **Pruebas.** `test_api.py` · `test_cuaderno_genera_figuras`, `test_explorar_solo_dentro_de_las_raices`. **Estado.** Estable.

## F-18 · LAB interactivo
**Descripción.** Cuadernos celda a celda (código y Markdown) con un núcleo persistente que conserva las variables y se apaga tras 3 h sin uso. Acciones: ejecutar todo, interrumpir, limpiar salidas, «Ejecutar en limpio», y guardado automático como `.ipynb`. Desde 1.5.0:
- **Reiniciar Python**, con botón visible: nuevo proceso, para cargar paquetes instalados o actualizados.
- **Borrar las variables (sin reiniciar)**, como `%reset -f` en el mismo proceso.
- **Avisos de paquetes:**
  - tras un `%pip|!pip|%conda|uv pip install` que instaló algo, se propone reiniciar (o reiniciar y ejecutar todo);
  - ante un `ModuleNotFoundError`, se propone insertar y ejecutar `%pip install <paquete>`, con el nombre de pip correcto para los módulos que se llaman distinto;
  - ante `google.colab`, se explica que esa celda es propia de Colab.
- **Red de seguridad:** si Python contesta en el canal shell pero no llega el «idle» del canal iopub, la celda se da por terminada a los 3 s.

**Módulos.** `lab/nucleos.py` (`borrar_variables`, `_respuesta_shell`), frontend `cuaderno.js`. **API.** `POST …/lab/<nb>/reiniciar`, `POST …/lab/<nb>/borrar-variables`. **Pruebas.** `test_lab.py` · `test_cuaderno_nuevo_y_edicion`, `test_ejecutar_celda_a_celda_conserva_las_variables`, `test_borrar_variables_conserva_el_proceso_y_reiniciar_lo_cambia`, `test_una_celda_no_se_queda_colgada_si_se_pierde_el_idle`. Los avisos se probaron en un navegador real con un paquete instalado de verdad. **Estado.** Estable.

## F-19 · Plantillas de gráficos
**Descripción.** Gráficos con formulario: 73 plantillas incluidas (ver F-26 y F-27) con matplotlib, seaborn o plotly, filtrables por categoría y por biblioteca. Datos: CSV, TSV, Excel, JSON, Parquet o un DataFrame del cuaderno. El código generado se inserta en una celda editable. Plantillas propias en `datos/graficos/`; «Probar» las ejecuta con todos los datos de ejemplo.
**Módulos.** `lab/graficos/__init__.py`, `lab/graficos/comun.py`. **API.** Plantillas de gráficos. **Pruebas.** `test_lab.py` · `test_generar_codigo_de_plantilla`, `test_las_plantillas_incluidas_generan_python_valido`, `test_plantillas_propias`, `test_un_grafico_de_plantilla_llega_al_documento`. **Estado.** Estable.

## F-20 · Modo LaTeX
**Descripción.** Convierte un proyecto estructurado a `.tex` editable con resaltado y vista previa, y guarda una copia previa del modelo. La línea `% !TEX program = lualatex|xelatex` elige el motor.
**Módulos.** `nucleo/almacen.py`, `salidas/compilador.py`. **API.** `POST …/convertir-latex`, `…/archivos`, `…/latex`. **Pruebas.** `test_fuentes.py` · `test_motor_de_un_proyecto_latex`; `test_revision.py` · `test_imprenta_y_revision_de_un_proyecto_latex`. **Estado.** Estable.

## F-21 · Plantillas de documento
**Descripción.** 12 plantillas incluidas, de solo lectura. Guardar como plantilla, actualizar la plantilla de origen, renombrar, describir, borrar, exportar e importar en zip.
**Módulos.** `nucleo/almacen.py`. **API.** Plantillas. **Pruebas.** `test_api.py` · `test_plantillas_incluidas`, `test_plantilla_propia_y_zips`, `test_actualizar_plantilla_desde_un_poster`; `test_generador.py` · `test_las_plantillas_compilan_en_una_pagina`. **Estado.** Estable.

## F-22 · Importar y exportar proyectos
**Descripción.** Zip para Overleaf (`poster.tex`, `.sty`, las imágenes que se usan y las tipografías), zip del proyecto completo (copia de seguridad) e importación de zips de DocsLab, de plantillas o de cualquier proyecto LaTeX, con protección contra *path traversal*.
**Módulos.** `nucleo/almacen.py`. **API.** `GET …/exportar`, `POST /api/proyectos/importar`. **Pruebas.** `test_api.py` · `test_plantilla_propia_y_zips`, `test_zip_malicioso_no_sale_de_su_carpeta`. **Estado.** Estable.

## F-23 · Historial, deshacer y guardado automático
**Descripción.** Deshacer y rehacer en el cliente; guardado automático; historial en el servidor (copias con al menos 120 s de diferencia, se conservan 30) y restauración.
**Módulos.** `nucleo/almacen.py`, frontend `tienda.js` y `editor.js`. **API.** `…/historial`, `…/historial/<nombre>/restaurar`. **Pruebas.** Sin prueba específica. **Estado.** Parcial.

## F-24 · Despliegue
**Descripción.** `iniciar.command` (macOS/Linux) e `iniciar.bat` (Windows) crean `.venv`, instalan las dependencias y abren `http://127.0.0.1:8765`; si ya está en marcha, solo abren el navegador. Opciones `--puerto`, `--datos`, `--raices`, `--host` y `--detalle`. Lanzador de Colab que usa Drive.
**Módulos.** `servidor.py`, `herramientas/crear_lanzador_colab.py`. **API.** `GET /api/estado`. **Pruebas.** `test_api.py` · `test_estado_y_catalogo`. Colab [NO VERIFICADO] en un Colab real (según el LEEME, se probó en un entorno simulado). **Estado.** Parcial.

## F-25 · Migración del esquema de proyectos
**Introducida en.** 1.1.0.
**Descripción.** Al abrir un proyecto guardado con un esquema anterior, DocsLab lo lleva al esquema actual aplicando migraciones en cadena (N→N+1) y guarda antes una copia en `historial/modelo-antes-de-esquema-<N>.json`. Los proyectos heredados (PosterLab, DocsLab 2.1.0 y 1.0.x) se reconocen como esquema 1. Un proyecto de un esquema más nuevo no se abre y muestra «Actualiza DocsLab para abrirlo».
**Reglas.** Leer no reescribe el archivo; la versión migrada se guarda al primer cambio. Ninguna migración pierde datos en silencio.
**Módulos.** `nucleo/migraciones.py`, `nucleo/modelo.py`, `nucleo/almacen.py`. **API.** `GET`/`PUT /api/proyectos/<pid>/modelo` (400 si el esquema es más nuevo). **Pruebas.** `test_migraciones.py` (15 funciones; las de cadena usan un registro simulado porque aún no hay migraciones reales). **Estado.** Estable.

## F-26 · Galería de gráficos
**Introducida en.** 1.3.0.
**Descripción.** Las 7 categorías y los 41 tipos de gráfico de The R Graph Gallery (Distribución, Correlación, Ranking, Partes de un todo, Evolución, Mapas y Flujos), adaptados a Python. Son 35 plantillas nuevas más las 13 anteriores, ahora con categoría y enlace a su página de la galería. Las nuevas usan matplotlib o seaborn (y scipy para el dendrograma), sin conexión ni Chrome. Los mapas usan `mundo.geojson` (Natural Earth, dominio público) con proyección Equal Earth o longitud/latitud, y zonas predefinidas. «Usar datos de ejemplo» copia al cuaderno los datos de cada plantilla (y el mapa base si lo necesita), solo desde `lab/graficos/datos_ejemplo/`.
**Reglas.** Código válido en Python 3.9 o posterior. Ninguna plantilla depende de geopandas, networkx, squarify, wordcloud ni circlify: los algoritmos (squarify, empaquetado circular, Fruchterman-Reingold, Dorling, círculo máximo, Chaikin, espiral de palabras) van en el propio código, editable.
**Módulos.** `lab/graficos/galeria.py`, `lab/graficos/__init__.py` (`CATEGORIAS`, `archivos_ejemplo`), `lab/nucleos.py` (`copiar_ejemplo`), `lab/graficos/datos_ejemplo/`, `herramientas/datos_ejemplo.py`, `herramientas/construir_graficos.py`; frontend `cuaderno.js`. **API.** `GET /api/graficos` (`categorias`, `ejemplo` por plantilla), `POST …/lab/<nb>/ejemplo` (`archivos`). **Pruebas.** `test_galeria.py` · `test_cada_tipo_de_la_galeria_tiene_plantilla`, `test_las_plantillas_de_la_galeria_dibujan_con_sus_datos_de_ejemplo`, `test_el_codigo_vale_en_python_3_9` (48), `test_usar_datos_de_ejemplo_copia_los_de_la_plantilla`. **Estado.** Estable.

## F-27 · Plantillas de análisis científico y de datos
**Introducida en.** 1.4.0.
**Descripción.** 25 plantillas en 5 categorías:
- **Multivariado:** PCA 2D (con % de varianza y elipses del 95 %), PCA 3D, biplot, varianza explicada, t-SNE 2D y 3D, NMDS/MDS con distancias Bray-Curtis, euclídea, Jaccard, Manhattan o correlación, y mapa de calor con agrupamiento jerárquico.
- **Aprendizaje automático:** k-means sobre el PCA, que añade la columna `cluster` a la tabla; elección de k por codo y silueta; ROC con AUC y punto de Youden; matriz de confusión con informe de clasificación.
- **Estadística:** comparación de grupos con t de Welch, t de Student o Mann-Whitney, corrección de Holm o Bonferroni y prueba global (ANOVA o Kruskal-Wallis); raincloud; Q-Q con Shapiro-Wilk; Bland-Altman; ajuste de curva (8 modelos) con banda de confianza por el método delta y R²; forest plot con efecto combinado por el inverso de la varianza e I².
- **Biomedicina:** volcán, Manhattan, Kaplan-Meier (IC de Greenwood, censuras, log-rank para k grupos y tabla de pacientes en riesgo), dosis-respuesta (logística de 4 parámetros, CI50) y Venn de 2 o 3 conjuntos.
- **Señales y superficies:** espectro con suavizado Savitzky-Golay y detección de picos; superficie 3D o contornos.

**Reglas.**
- Cada plantilla imprime sus estadísticos en la salida de la celda.
- t-SNE usa el método exacto hasta 1500 filas (más fiel y sin puntos sueltos en 3D) y Barnes-Hut a partir de ahí.
- NMDS es compatible con la API de MDS de scikit-learn antes y después de 1.8.
- Los datos de ejemplo científicos son simulados.

**Módulos.** `lab/graficos/ciencia.py`, `lab/graficos/datos_ejemplo/` (11 archivos nuevos), `herramientas/datos_ejemplo.py`. **API.** Sin rutas nuevas. **Pruebas.** `test_galeria.py` · `test_las_plantillas_cientificas_dibujan_con_sus_datos_de_ejemplo`, `test_pedidos_de_las_plantillas_cientificas`, `test_el_codigo_compila_en_un_python_antiguo`, `test_los_numeros_pequenos_no_se_redondean_a_cero`. **Estado.** Estable.

## F-28 · Protección del servidor local y accesibilidad
**Introducida en.** 1.6.0.
**Descripción.** Cierra las vías por las que otra web abierta en el mismo navegador, o un cuaderno ajeno, podía usar DocsLab: comprobación del Host (DNS rebinding), cabecera `X-DocsLab` y `Origin` en las peticiones que cambian algo, salidas HTML de los cuadernos en un marco aislado, cabeceras CSP y nosniff, errores en JSON, Pillow solo con los formatos esperados y pdf.js 4.10.38. Además, accesibilidad WCAG 2.2 AA en lo que comprueba axe: los diálogos retienen y devuelven el foco, el asistente se cierra con Esc, las tarjetas tienen su nombre como botón, el árbol de estructura cumple ARIA y las celdas del cuaderno se eligen con teclado. Pie del inicio con la versión, las licencias y dónde está el código fuente.
**Reglas.**
- Se atienden `localhost`, `*.localhost`, direcciones IP y los nombres de `DOCSLAB_HOSTS`; en modo Colab no se comprueba el Host (lo hace el proxy).
- Una petición POST, PUT, PATCH o DELETE sin `X-DocsLab: 1`, o con un `Origin` distinto del servidor (incluido `null`), recibe 403.
- Como mucho `DOCSLAB_MAX_NUCLEOS` (4) procesos de Python del LAB a la vez; se apaga el que lleva más tiempo sin usarse y su cuaderno lo avisa.
**Módulos.** `seguridad.py`, `api/sistema.py` (tipos MIME), `lab/nucleos.py` (`hacer_sitio`), `nucleo/almacen.py` (`FORMATOS_*`), `salidas/powerpoint.py` (`abrir_render`); frontend `api.js`, `foco.js`, `cuaderno.js`, `arbol.js`, `inicio.js`, `cuadernos.js`. **API.** Sin rutas nuevas; cabecera obligatoria en las que cambian algo. **Pruebas.** `test_seguridad.py` (21); `test_lab.py` · `test_tope_de_procesos_del_lab_apaga_el_mas_antiguo`; `test_bibliografia.py` · `test_buscar_doi_no_lee_respuestas_enormes`; `tests/auditoria_navegador.py` (axe, foco, marco aislado, CSRF y rebinding en Chrome). **Estado.** Estable.

---

## Requisitos no funcionales

| ID | Requisito | Fuente |
|---|---|---|
| RNF-01 | Funciona sin conexión (librerías incluidas), salvo la búsqueda por DOI | LEEME |
| RNF-02 | Recompilación rápida. Medido el 2026-11-18 (plantilla Académico A0, Linux, TeX Live): primera compilación ≈ 5,3 s; cambio pequeño ≈ 2,4 s. El LEEME original decía ~1 s | Medición |
| RNF-03 | Python ≥ 3.9 | `requirements.txt` |
| RNF-04 | Uso local de un solo usuario, sin autenticación; protegido frente a otras webs del mismo navegador (F-28) | `SECURITY.md` |
| RNF-06 | Compatibilidad hacia atrás: todo proyecto de un esquema anterior se abre sin pérdida de datos | `docs/MIGRACIONES.md`, F-25 |
| RNF-07 | Licencias: AGPL-3.0-only (aplicación) y LPPL-1.3c (`postercientifico.sty`); cabecera SPDX en cada archivo de código propio | `LICENSE`, `latex/LICENSE-LPPL-1.3c.txt` |
| RNF-08 | Accesibilidad: sin infracciones de axe-core (WCAG 2.0/2.1/2.2 A y AA) en inicio, asistente, editor, LAB y Componente Lab | `tests/auditoria_navegador.py` |
| RNF-05 | Las funciones opcionales se desactivan si faltan sus herramientas (Poppler, Ghostscript, LuaLaTeX), con aviso | Pruebas con `skip` |
