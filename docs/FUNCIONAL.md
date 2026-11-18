# Especificación funcional · DocsLab 1.2.0

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
**Módulos.** `modelo.py` (`CLASES`, `desde_asistente`), `generador.py`. **API.** Proyectos. **Pruebas.** `test_clases.py` · `test_el_asistente_crea_cada_clase`, `test_cada_clase_compila`, `test_secciones_de_una_tesis`. **Estado.** Estable.

## F-02 · Asistente de documento nuevo
**Descripción.** Elección de clase, tamaño, columnas, colores, tipografía e idioma. Ajusta la letra y las imágenes al tamaño.
**Módulos.** `modelo.py`. **API.** `POST /api/proyectos`. **Pruebas.** `test_generador.py` · `test_asistente`, `test_asistente_ajusta_imagen_y_letra`. **Estado.** Estable.

## F-03 · Editor por capas
**Descripción.** Capas detrás, contenido y delante; mostrar, ocultar, atenuar y reordenar; capas propias con elementos (texto, imagen, forma) colocados por coordenadas, rotación, escala y opacidad.
**Módulos.** `modelo.py` (`CAPAS_DEFECTO`, `ITEM_TIPOS`), `generador.py`. **Pruebas.** `test_generador.py` · `test_capas_y_elementos_de_capa`. **Estado.** Estable.

## F-04 · Edición directa y posición libre
**Descripción.** Arrastrar cajas y elementos en la vista previa, cambiar el ancho de las columnas, editar texto con doble clic, cambiar el tamaño de los logos, soltar elementos de la cuadrícula y «Lienzo libre».
**Módulos.** `compilador.py` (marcas de posición), frontend `directa.js` y `vista.js`. **Pruebas.** `test_clases.py` · `test_una_caja_suelta_sale_de_la_cuadricula`, `test_la_caja_suelta_queda_donde_se_pone`. Interacción: `e2e_navegador.py`. **Estado.** Estable (backend) / Parcial (interacción, solo en e2e).

## F-05 · Variantes de elemento y estilos de caja
**Descripción.** 69 variantes (I01–I34 de imagen, T01–T36 de texto, LaTeX libre y espacio) con miniaturas, y 12 estilos de caja. Todas las cajas tienen un título opcional.
**Módulos.** `variantes.py`, `generador.py`. **API.** `GET /api/variantes`. **Pruebas.** `test_generador.py` · `test_cada_variante_genera_su_orden`, `test_titulo_oculto_en_cajas_y_cajas_de_texto`. **Estado.** Estable.

## F-06 · Texto con formato sencillo
**Descripción.** `**negrita**`, `*cursiva*`, `` `código` ``, `^sup^`, `~sub~`, `$mat$`, `[@cita]` y `{{LaTeX}}`; escape automático; párrafos separados por una línea en blanco. Conversión al modo «Código LaTeX» sin que cambie el resultado.
**Módulos.** `texto.py`. **Pruebas.** `test_texto.py` (6), `test_generador.py` · `test_convertir_formato_no_cambia_el_poster`. **Estado.** Estable.

## F-07 · Referencias bibliográficas
**Descripción.** Formulario por tipo de referencia, búsqueda por DOI (doi.org), importación de BibTeX, RIS, CSL-JSON y listas de DOI, y exportación a `.bib`. Ocho estilos: APA 7, Vancouver, IEEE, Chicago autor-fecha, MLA 9, Harvard, Nature y ACS. Citas `[@a; @b, p. 12]`, numeradas por orden de lectura en los estilos numéricos, y letra a/b cuando coinciden autor y año. Lista T36: solo las citadas o todas.
**Módulos.** `bibliografia.py`. **API.** Bibliografía y `GET …/bibliografia.bib`. **Pruebas.** `test_bibliografia.py` (17). **Estado.** Estable (DOI: Parcial, depende de la red).

## F-08 · Componente Lab
**Descripción.** Componentes propios hechos con piezas (título, texto, cifra, imagen, lista, icono, columnas…) o con código LaTeX con `{{campo}}`. Se pueden recrear a partir de los 69 incluidos. Biblioteca en `datos/componentes/`, con una copia dentro de cada póster y aviso de actualización. Importación y exportación en JSON (formato v1).
**Módulos.** `componentes.py`. **API.** Componente Lab. **Pruebas.** `test_componentes.py` (11). **Estado.** Estable.

## F-09 · Compilación
**Descripción.** Compila al guardar o con Ctrl + S, con formato precompilado, sin recompilar si nada cambió y con la miniatura aparte. Ante un error, mantiene el último PDF correcto y lo ubica en el elemento de origen. Con MiKTeX, instala los paquetes que faltan. Avisa de lo que no cabe.
**Módulos.** `compilador.py`, `trabajos.py`. **API.** `POST …/compilar`, `GET …/compilacion`, `…/pdf`, Trabajos. **Pruebas.** `test_api.py` · `test_compilar_errores_y_ultimo_pdf_correcto`, `test_compilar_sin_cambios_no_repite_y_miniatura_aparte`; `test_motores.py` (6). **Estado.** Estable.

## F-10 · Ajustar a una página
**Descripción.** Busca el tamaño de letra más grande con el que todo cabe. Se puede deshacer.
**Módulos.** `app.py`, `compilador.py`. **API.** `POST …/ajustar`. **Pruebas.** Sin prueba específica. **Estado.** Parcial.

## F-11 · Revisión para imprimir
**Descripción.** Tamaño y páginas, resolución real de las imágenes (también dentro de las figuras PDF), tamaño de letra según el formato, contraste WCAG, colores fuera de la gama CMYK, tipografías incrustadas o de mapa de bits, textos de ejemplo, citas sin referencia y texto a menos de 5 mm del borde, con «Mostrar en el póster». Umbrales en A0: 150 ppi, 24 pt en el texto principal y 18 pt como mínimo.
**Módulos.** `revision.py`. **API.** `POST …/revisar`. **Pruebas.** `test_revision.py` (11). **Estado.** Estable.

## F-12 · PDF para imprenta
**Descripción.** Sangrado de 3 o 5 mm (alarga lo que toca el borde), marcas de corte con 10 mm de margen, TrimBox y BleedBox, y RGB o CMYK (Ghostscript). Nunca modifica el PDF del proyecto.
**Módulos.** `generador.py`, `compilador.py`. **API.** `POST …/imprenta`, `GET …/imprenta.pdf|png`. **Pruebas.** `test_revision.py` · `test_pdf_para_imprenta_con_sangrado_y_marcas`, `test_pdf_para_imprenta_en_cmyk`. **Estado.** Estable.

## F-13 · Exportar a PowerPoint
**Descripción.** Una diapositiva por página. Modo editable (cada línea es un cuadro de texto sobre una imagen sin texto; las fórmulas y el texto de las figuras quedan en la imagen; necesita Ghostscript) o modo imagen. Reduce los pósters que superan el tamaño máximo de PowerPoint.
**Módulos.** `powerpoint.py`. **API.** `POST …/powerpoint`, `GET …/powerpoint.pptx`. **Pruebas.** `test_powerpoint.py` (9). **Estado.** Estable.

## F-14 · Tipografías
**Descripción.** 6 clásicas, 19 libres de TeX Live (con marca si no están instaladas) y propias (.ttf/.otf) con imitación de negrita y cursiva cuando faltan, compiladas con LuaLaTeX y con aviso de licencia de incrustación. El zip para Overleaf incluye un `latexmkrc`.
**Módulos.** `fuentes.py`, `modelo.py` (`FAMILIAS_INFO`). **API.** `…/fuentes`. **Pruebas.** `test_fuentes.py` (7). **Estado.** Estable.

## F-15 · Idioma del documento
**Descripción.** Español, inglés, portugués, francés, alemán o italiano: separación de palabras, comillas y palabras fijas de las referencias. Avisa si falta el paquete del idioma.
**Módulos.** `modelo.py` (`IDIOMAS`), `bibliografia.py`. **Pruebas.** `test_generador.py` · `test_idioma_del_poster`; `test_bibliografia.py` · `test_palabras_segun_el_idioma`. **Estado.** Estable.

## F-16 · Imágenes y recursos
**Descripción.** Subida de PNG, JPG y PDF; GIF, WEBP, TIFF y BMP se convierten a PNG; SVG opcional con cairosvg. Imagen de reserva del tamaño pedido.
**Módulos.** `almacen.py`. **API.** `…/recursos`, `…/f/<ruta>`. **Pruebas.** `test_api.py` · `test_recursos`; `test_generador.py` · `test_imagen_de_reserva_mide_lo_pedido`. **Estado.** Estable.

## F-17 · Cuadernos (ejecución completa)
**Descripción.** Subir un `.ipynb` con sus datos o abrirlo desde una carpeta permitida (`--raices`). Ejecución con registro por celda y recogida de figuras en `recursos/cuadernos/<nb>/` con rutas estables (al volver a ejecutar, el documento se actualiza). Ajustes: carpeta de figuras, extensiones, preferir PDF, omitir celdas de Colab, parámetros inyectados, tiempo máximo y núcleo. «Traer figuras desde Colab».
**Módulos.** `cuadernos.py`, `trabajos.py`. **API.** Cuadernos, Explorador. **Pruebas.** `test_api.py` · `test_cuaderno_genera_figuras`, `test_explorar_solo_dentro_de_las_raices`. **Estado.** Estable.

## F-18 · LAB interactivo
**Descripción.** Cuadernos celda a celda (código y Markdown) con un núcleo persistente que conserva las variables y se apaga tras 3 h sin uso; ejecutar todo, reiniciar, limpiar y «Ejecutar en limpio»; guardado automático como `.ipynb`.
**Módulos.** `lab.py`. **API.** LAB. **Pruebas.** `test_lab.py` · `test_cuaderno_nuevo_y_edicion`, `test_ejecutar_celda_a_celda_conserva_las_variables`. **Estado.** Estable.

## F-19 · Plantillas de gráficos
**Descripción.** Gráficos con formulario (barras, líneas, dispersión, histograma, cajas, violín, mapa de calor… con matplotlib, seaborn o plotly). Datos: CSV, TSV, Excel, JSON, Parquet o un DataFrame del cuaderno. El código generado se inserta en una celda editable. Plantillas propias en `datos/graficos/`, con prueba sobre `ejemplo.csv`.
**Módulos.** `graficos.py`. **API.** Plantillas de gráficos. **Pruebas.** `test_lab.py` · `test_generar_codigo_de_plantilla`, `test_las_plantillas_incluidas_generan_python_valido`, `test_plantillas_propias`, `test_un_grafico_de_plantilla_llega_al_documento`. **Estado.** Estable.

## F-20 · Modo LaTeX
**Descripción.** Convierte un proyecto estructurado a `.tex` editable con resaltado y vista previa, y guarda una copia previa del modelo. La línea `% !TEX program = lualatex|xelatex` elige el motor.
**Módulos.** `almacen.py`, `compilador.py`. **API.** `POST …/convertir-latex`, `…/archivos`, `…/latex`. **Pruebas.** `test_fuentes.py` · `test_motor_de_un_proyecto_latex`; `test_revision.py` · `test_imprenta_y_revision_de_un_proyecto_latex`. **Estado.** Estable.

## F-21 · Plantillas de documento
**Descripción.** 12 plantillas incluidas, de solo lectura. Guardar como plantilla, actualizar la plantilla de origen, renombrar, describir, borrar, exportar e importar en zip.
**Módulos.** `almacen.py`. **API.** Plantillas. **Pruebas.** `test_api.py` · `test_plantillas_incluidas`, `test_plantilla_propia_y_zips`, `test_actualizar_plantilla_desde_un_poster`; `test_generador.py` · `test_las_plantillas_compilan_en_una_pagina`. **Estado.** Estable.

## F-22 · Importar y exportar proyectos
**Descripción.** Zip para Overleaf (`poster.tex`, `.sty`, las imágenes que se usan y las tipografías), zip del proyecto completo (copia de seguridad) e importación de zips de DocsLab, de plantillas o de cualquier proyecto LaTeX, con protección contra *path traversal*.
**Módulos.** `almacen.py`. **API.** `GET …/exportar`, `POST /api/proyectos/importar`. **Pruebas.** `test_api.py` · `test_plantilla_propia_y_zips`, `test_zip_malicioso_no_sale_de_su_carpeta`. **Estado.** Estable.

## F-23 · Historial, deshacer y guardado automático
**Descripción.** Deshacer y rehacer en el cliente; guardado automático; historial en el servidor (copias con al menos 120 s de diferencia, se conservan 30) y restauración.
**Módulos.** `almacen.py`, frontend `tienda.js` y `editor.js`. **API.** `…/historial`, `…/historial/<nombre>/restaurar`. **Pruebas.** Sin prueba específica. **Estado.** Parcial.

## F-24 · Despliegue
**Descripción.** `iniciar.command` (macOS/Linux) e `iniciar.bat` (Windows) crean `.venv`, instalan las dependencias y abren `http://127.0.0.1:8765`; si ya está en marcha, solo abren el navegador. Opciones `--puerto`, `--datos`, `--raices`, `--host` y `--detalle`. Lanzador de Colab que usa Drive.
**Módulos.** `servidor.py`, `herramientas/crear_lanzador_colab.py`. **API.** `GET /api/estado`. **Pruebas.** `test_api.py` · `test_estado_y_catalogo`. Colab [NO VERIFICADO] en un Colab real (según el LEEME, se probó en un entorno simulado). **Estado.** Parcial.

## F-25 · Migración del esquema de proyectos
**Introducida en.** 1.1.0.
**Descripción.** Al abrir un proyecto guardado con un esquema anterior, DocsLab lo lleva al esquema actual aplicando migraciones en cadena (N→N+1) y guarda antes una copia en `historial/modelo-antes-de-esquema-<N>.json`. Los proyectos heredados (PosterLab, DocsLab 2.1.0 y 1.0.x) se reconocen como esquema 1. Un proyecto de un esquema más nuevo no se abre y muestra «Actualiza DocsLab para abrirlo».
**Reglas.** Leer no reescribe el archivo; la versión migrada se guarda al primer cambio. Ninguna migración pierde datos en silencio.
**Módulos.** `migraciones.py`, `modelo.py`, `almacen.py`. **API.** `GET`/`PUT /api/proyectos/<pid>/modelo` (400 si el esquema es más nuevo). **Pruebas.** `test_migraciones.py` (15 funciones; las de cadena usan un registro simulado porque aún no hay migraciones reales). **Estado.** Estable.

---

## Requisitos no funcionales

| ID | Requisito | Fuente |
|---|---|---|
| RNF-01 | Funciona sin conexión (librerías incluidas), salvo la búsqueda por DOI | LEEME |
| RNF-02 | Recompilación rápida. Medido el 2026-11-18 (plantilla Académico A0, Linux, TeX Live): primera compilación ≈ 5,3 s; cambio pequeño ≈ 2,4 s. El LEEME original decía ~1 s | Medición |
| RNF-03 | Python ≥ 3.9 | `requirements.txt` |
| RNF-04 | Uso local de un solo usuario, sin autenticación | `SECURITY.md` |
| RNF-06 | Compatibilidad hacia atrás: todo proyecto de un esquema anterior se abre sin pérdida de datos | `docs/MIGRACIONES.md`, F-25 |
| RNF-07 | Licencias: AGPL-3.0-only (aplicación) y LPPL-1.3c (`postercientifico.sty`); cabecera SPDX en cada archivo de código propio | `LICENSE`, `latex/LICENSE-LPPL-1.3c.txt` |
| RNF-05 | Las funciones opcionales se desactivan si faltan sus herramientas (Poppler, Ghostscript, LuaLaTeX), con aviso | Pruebas con `skip` |
