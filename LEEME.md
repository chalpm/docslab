# DocsLab

Editor web de documentos científicos hechos con LaTeX: **pósters, presentaciones de diapositivas, artículos, tesis y documentos generales**. Editas por bloques y capas, con formularios o directamente sobre la vista previa, ves el PDF real compilado, revisas que esté listo para imprimir y descargas el PDF (también preparado para la imprenta) o un zip para Overleaf. Las figuras pueden salir directamente de tus cuadernos de Colab o Jupyter.

Funciona en tu equipo (un pequeño servidor local con Python) o dentro de Google Colab.

**Versión 1.1.0** · Licencia [AGPL-3.0](LICENSE) · [Registro de cambios](CHANGELOG.md) · [Documentación técnica y funcional](docs/README.md) · [Seguridad](SECURITY.md)

## Qué incluye

- **Cinco tipos de documento.** Al crear un proyecto eliges qué vas a hacer:
  - **Póster**: una hoja grande con cabecera, filas, columnas y cajas.
  - **Presentación**: diapositivas (16:9, 16:10 o 4:3), cada una con su propia cuadrícula; diseños de portada, título y contenido, título de sección y en blanco; pie, numeración y barra de avance. Se hacen con el motor de DocsLab (no con Beamer), así que usan los mismos elementos, estilos y capas que el póster.
  - **Documento**: informe o guía con secciones, a una o dos columnas.
  - **Artículo**: título, autores, resumen y palabras clave (también en un segundo idioma), secciones numeradas, figuras, tablas y referencias; a una o dos columnas.
  - **Tesis**: plantilla genérica y configurable con portada (institución, grado, dirección, lugar y fecha), dedicatoria, agradecimientos, resumen, índices de contenido, figuras y tablas, capítulos con secciones y apéndices, numeración romana en las páginas preliminares y margen de encuadernación.
- **Posición libre cuando la quieras** (pósters y presentaciones). La cuadrícula sigue siendo lo normal, pero cualquier caja o elemento se puede **soltar de la cuadrícula** y arrastrar a cualquier punto de la página; su esquina cambia el ancho y las flechas del teclado lo mueven poco a poco. También puedes añadir textos, imágenes o cajas sueltos, o encender **Lienzo libre** en un póster o en una diapositiva para colocarlo todo a mano. «Volver a la cuadrícula» lo deshace. En documentos, artículos y tesis el texto corre de una página a otra y no hay posición libre.

- **Editor visual por capas.** El póster tiene capas *detrás* del contenido (fondos, formas, imágenes), el *contenido* (cabecera, filas de columnas con cajas, pie) y capas *delante* (sellos, notas, logotipos). Cada capa se oculta, se atenúa y se reordena; puedes crear las que quieras.
- **Edición directa sobre la vista previa.** Arrastra una caja o un elemento a otro sitio (también a otra columna), cambia el ancho de las columnas arrastrando el borde que hay entre ellas, haz doble clic en un texto para escribirlo ahí mismo y estira los logos de la cabecera desde su esquina (cada uno tiene su tamaño).
- **69 formas de colocar texto e imágenes** (I01–I34, T01–T36, más LaTeX libre y espacio) y **12 estilos de caja**, con miniaturas para elegir. Todas las cajas tienen un título opcional.
- **Referencias con estilo.** Un gestor de referencias por póster: escríbelas con un formulario, búscalas por DOI o impórtalas (BibTeX, RIS o CSL-JSON). Cita con `[@clave]` en cualquier texto y elige el estilo (APA 7, Vancouver, IEEE, Chicago, MLA 9, Harvard, Nature o ACS): las citas y la lista se escriben solas.
- **Componente Lab.** Crea tus propios componentes, con piezas (título, texto, cifra, imagen, lista, icono, columnas…) o con código LaTeX, y úsalos en cualquier póster. También puedes recrear cualquiera de los 69 incluidos para cambiarlo a tu gusto.
- **Ajustar a una página.** Si algo no cabe, DocsLab busca el tamaño de letra más grande con el que todo cabe (se puede deshacer).
- **Revisión para imprimir.** Resolución real de cada imagen, tamaño de letra (también dentro de las figuras), contraste, colores que cambian en tinta, tipografías incrustadas, textos de ejemplo, citas sin referencia y lo que queda demasiado cerca del borde, con un botón para verlo en el póster.
- **PDF para imprenta.** Con sangrado (el fondo pasa 3 o 5 mm del borde), marcas de corte y cajas TrimBox y BleedBox; en RGB o en CMYK.
- **PowerPoint.** Una diapositiva por cada página (una para un póster, todas las de una presentación): con el texto editable (cada línea es un cuadro de texto sobre una imagen del póster sin texto; las fórmulas y las letras de las figuras quedan en la imagen) o como una imagen idéntica al PDF. Lo editable necesita Ghostscript.
- **Tipografías.** 6 clásicas, 19 libres de TeX Live (Source Sans, Fira Sans, Roboto, Lato, Atkinson Hyperlegible, Libertinus, EB Garamond, Merriweather…) y las tuyas: sube un `.ttf` o un `.otf` y el póster se compila con LuaLaTeX.
- **Idioma del póster** (español, inglés, portugués, francés, alemán o italiano): separación de palabras, comillas y palabras de las referencias.
- **Plantillas**: 12 incluidas (académica A0, horizontal 48 × 36 in, por capas A1, mínima A1, el póster BGC en inglés y en español, el catálogo, un ejemplo en LaTeX, una presentación 16:9, un artículo a dos columnas, una tesis y un informe). Cualquier documento se guarda como plantilla y, más adelante, la actualiza.
- **LAB.** Cada documento tiene, junto a su editor, un apartado LAB con sus cuadernos de Python: créalos desde cero o sube un `.ipynb`, escribe celdas de código y de texto, y ejecútalo entero o celda por celda (las variables se conservan entre celdas, como en Jupyter o Colab). Incluye **plantillas de gráficos** con formulario (barras, líneas, dispersión, histograma, cajas, violín, mapa de calor… con matplotlib, seaborn o plotly) cuyo código queda en una celda y se puede editar; también puedes crear tus propias plantillas. Ver «LAB» más abajo.
- **Cuadernos**: sube un `.ipynb` con sus datos (o ábrelo desde una carpeta, por ejemplo tu Google Drive en Colab). DocsLab lo ejecuta, recoge las figuras que guarda y las deja listas para el póster. Al volver a ejecutarlo, el póster se actualiza solo.
- **Modo LaTeX**: si prefieres el código, cualquier proyecto se puede convertir y editar a mano, con resaltado y vista previa.
- **Compilación rápida**: la plantilla va precompilada (un «formato» de pdfLaTeX), no se compila lo que no ha cambiado y la miniatura se hace aparte. Un cambio pequeño tarda alrededor de un segundo.
- **Deshacer y rehacer, guardado automático, historial de versiones** y compilación automática al guardar.

## Instalación en tu equipo

1. **Python 3.9 o posterior** (en macOS, `brew install python` si no lo tienes).
2. **LaTeX** (pdfLaTeX) y las herramientas de PDF (Poppler):
   - macOS: instala MacTeX (`brew install --cask mactex-no-gui`, o el instalador de [tug.org/mactex](https://tug.org/mactex/)) y `brew install poppler ghostscript`.
   - Ubuntu o Debian:
     ```
     sudo apt install python3-venv texlive-latex-recommended texlive-latex-extra texlive-pictures texlive-fonts-recommended poppler-utils
     ```
     Opcional: `texlive-fonts-extra` (las tipografías libres), `texlive-luatex` (tipografías propias), `ghostscript` (PDF en CMYK y la comprobación de color) y `texlive-lang-spanish` u otro idioma (separación de palabras).
   - Windows: instala [MiKTeX](https://miktex.org/). No hace falta instalar paquetes a mano: DocsLab le pide a MiKTeX que descargue los que falten, así que la primera compilación puede tardar unos minutos. Para la revisión y las miniaturas, instala Poppler para Windows (por ejemplo `winget install oschwartz10612.Poppler`) y, para CMYK, Ghostscript.
3. **Arrancar.** En Windows, doble clic en `iniciar.bat`. En macOS y Linux, desde la carpeta `docslab`:
   ```
   sh iniciar.command
   ```
   En macOS también vale el doble clic en `iniciar.command` (si la primera vez macOS dice que no puede comprobarlo, ve a Ajustes del Sistema → Privacidad y seguridad → «Abrir igualmente», o usa la Terminal). Los dos lanzadores hacen lo mismo: la primera vez crean un entorno de Python propio (la carpeta `.venv`) e instalan ahí las dependencias, sin tocar el Python del sistema; tarda un par de minutos. Luego abren `http://127.0.0.1:8765` en el navegador. Deja la ventana abierta mientras usas DocsLab; Ctrl + C lo cierra. Si ya estaba abierto, solo abre el navegador. Los proyectos se guardan en la carpeta `datos/`.

   Lo mismo a mano:
   ```
   python3 -m venv .venv                       # Windows: py -m venv .venv
   source .venv/bin/activate                   # Windows: .venv\Scripts\activate
   python -m pip install -r requirements.txt
   python servidor.py --abrir
   ```
   Las siguientes veces basta con activar el entorno (`source .venv/bin/activate`) y `python servidor.py --abrir`.

Opciones útiles:

| Opción | Para qué sirve |
|---|---|
| `--puerto 9000` | otro puerto (con el lanzador: `sh iniciar.command --puerto 9000`) |
| `--datos ~/DocsLab` | guardar los proyectos en otra carpeta |
| `--raices ~/Documentos ~/Drive` | carpetas donde se pueden buscar cuadernos desde la aplicación (por defecto, tu carpeta personal) |
| `--host 0.0.0.0` | abrirlo a otras máquinas de tu red; **no tiene contraseña**, úsalo solo en redes de confianza |
| `--detalle` | mostrar en la terminal cada petición del navegador (para buscar un fallo) |

## En Google Colab

1. Sube `docslab.zip` a tu Google Drive, en la carpeta `DocsLab`.
2. Abre `abrir_docslab_en_colab.ipynb` en Colab y ejecuta todas las celdas. La primera vez instala LaTeX (3–4 minutos).
3. Abre el enlace que aparece al final. Tus proyectos quedan en `MyDrive/DocsLab/datos`.

Desde Colab, en **LAB › Abrir desde una carpeta (Drive)** puedes elegir tus cuadernos de `/content/drive/MyDrive/…`; se ejecutan en su propia carpeta, con sus datos. El enlace solo funciona mientras el cuaderno lanzador está conectado.

> Este lanzador se probó simulando el entorno; la instalación de LaTeX en Colab depende de los paquetes de Ubuntu de ese momento.

## Cómo se usa

**Inicio.** Arriba, tus documentos (con un filtro por tipo cuando hay de varios); abajo, las plantillas. «Documento nuevo» abre un asistente: eliges el tipo (póster, presentación, documento, artículo o tesis) y sus opciones (tamaño, columnas, colores, tipografía, idioma…). El menú ⋯ de cada tarjeta duplica, exporta, guarda como plantilla, actualiza su plantilla o borra. Desde el inicio también se entra en el **Componente Lab**.

**Editor.**

- *Izquierda* — **Estructura**: el árbol del documento, ordenado de delante hacia atrás (capas delante, contenido, capas detrás). En un póster el contenido son filas, columnas y cajas; en una presentación, las diapositivas (cada una con sus filas); en un documento, artículo o tesis, las secciones seguidas, con sangría según su nivel. Al elegir una diapositiva o una sección, la vista previa pasa a su página.
  - El ojo muestra u oculta; la **T** muestra u oculta el título de una caja; **+** añade una columna, una caja, un elemento o un elemento de capa.
  - Arrastra filas, columnas, cajas, elementos y elementos de capa para moverlos (también entre columnas o capas).
  - Teclado: flechas para recorrer, Alt + flechas para subir o bajar, Supr para borrar.
- *Izquierda* — **Imágenes**: sube PNG, JPG o PDF (también GIF, WEBP o TIFF, que se convierten a PNG). Selecciona una caja o un elemento y pulsa «Usar».
- *Izquierda* — **Referencias**: el gestor de referencias (ver más abajo).
- **LAB** (conmutador de arriba): los cuadernos y las plantillas de gráficos; ver más abajo.
- *Centro* — **la vista previa**:
  - clic para seleccionar; arrastra una caja o un elemento para cambiarlo de sitio (una línea marca dónde caerá);
  - con una caja elegida aparecen unos tiradores entre las columnas: arrástralos para cambiar su ancho;
  - doble clic en un texto o en el título de una caja para escribir ahí mismo (Esc o Ctrl + Intro para cerrar);
  - los elementos de las capas se arrastran, el cuadrito de la esquina cambia su tamaño y las flechas del teclado los empujan (Mayús para pasos largos); Ctrl + rueda para hacer zoom.
- **Posición libre** (pósters y presentaciones): con una caja o un elemento elegido, «Soltar de la cuadrícula» lo deja donde está, pero suelto; arrástralo por su asa (el cuadrito a su izquierda) o por la propia caja. El botón «Suelto» (abajo a la izquierda) añade un texto, una imagen o una caja ya sueltos. «Lienzo libre», en el diseño general del póster o en cada diapositiva, suelta todas las cajas de esa página.
- **Diapositivas**: el botón «Diapositiva» añade una con el diseño que elijas después de la actual; en su inspector se cambia el diseño, el título, el fondo, si lleva pie y sus notas, y se duplica, mueve, oculta o borra. Si el contenido de una no cabe, el aviso de arriba dice cuál.
- **Documentos, artículos y tesis**: «Título y autores» y «Resumen e índices» (en la tesis, también la portada y las páginas preliminares) van antes de las secciones. Cada sección tiene nivel (capítulo, sección, subsección…), numeración, salto de página y, en la tesis, si es un apéndice.
- *Derecha* — **el inspector**: el formulario de lo seleccionado. Sin selección, el diseño general (lienzo, letra y tipografías, idioma, colores, cajas, espacios, figuras y LaTeX propio).

**Texto con formato sencillo** (por defecto): escribe normalmente; los símbolos de LaTeX se escapan solos. Admite `**negrita**`, `*cursiva*`, `` `código` ``, `^superíndice^`, `~subíndice~`, `$x^2$` (matemáticas), `[@clave]` (una cita) y `{{\orden}}` (LaTeX sin tocar). Una línea en blanco separa párrafos. Si prefieres escribir LaTeX, cambia a «Código LaTeX» en el diseño general: los textos se convierten sin que cambie el póster.

**Compilar.** Se compila solo al guardar (un momento después de cada cambio) o con **Ctrl + S**. Si hay un error, la vista sigue mostrando la última versión buena y el panel inferior explica el error con un botón para ir al elemento que lo causa. Si algo no cabe, el aviso ofrece **Ajustar a una página** (también en el menú ⋯).

**Atajos.** Ctrl + Z deshacer, Ctrl + Mayús + Z rehacer, Ctrl + S guardar y compilar.

**Descargar.** «Revisar para imprimir…», «PDF para imprenta…», el PDF tal cual, el zip para Overleaf (`poster.tex`, la plantilla, las imágenes que se usan y las tipografías propias) o el zip del proyecto completo (copia de seguridad que se puede volver a importar).

## Referencias

En la pestaña **Referencias**:

- **Añadir** abre un formulario con los campos del tipo elegido (artículo, libro, capítulo, congreso, tesis, informe, web, datos, software, preprint…) y una vista previa en el estilo del póster. **Buscar por DOI** rellena el formulario con los datos que da doi.org (necesita conexión a internet).
- **Importar** acepta BibTeX (`.bib`), RIS (`.ris`, de Zotero, Mendeley o EndNote), CSL-JSON o una lista de DOI. **Exportar** descarga un `.bib`.
- El **estilo** (APA 7, Vancouver, IEEE, Chicago autor-fecha, MLA 9, Harvard, Nature o ACS) cambia a la vez todas las citas y la lista.
- **Citar**: en cualquier campo de texto, el botón de cita inserta `[@clave]`; varias juntas se escriben `[@a; @b]` y con página `[@a, p. 12]`. En los estilos numéricos, las citas se numeran por orden de lectura.
- La lista va en el elemento **Referencias con estilo** (T36): solo las citadas o todas.

## Componente Lab

El Lab (botón en el inicio y en el selector de elementos) es un banco de trabajo para hacer tus propios componentes:

- **Con piezas**, sin código: apila título, texto, cifra, etiqueta, imagen, lista, icono, separador, espacio, LaTeX o columnas con piezas dentro; decide qué partes se rellenan en cada póster (los *campos*) y elige la caja que lo envuelve.
- **Con código LaTeX**: escribe el código con `{{campo}}` donde va cada dato; los campos se crean solos y la vista previa compila al momento, con los errores señalados en tu código.
- **Recrear un incluido**: parte de cualquiera de las 69 variantes (como piezas ajustables o como código) y cámbiala.

Los componentes se guardan en tu biblioteca (`datos/componentes/`) y aparecen en «Tus componentes» al añadir un elemento. Cada póster guarda una copia del componente que usa: si lo cambias en el Lab, el inspector ofrece ponerlo al día. Se exportan e importan en `.json`.

## Revisión para imprimir y PDF para imprenta

**Descargar › Revisar para imprimir…** abre un panel con la revisión del PDF actual (si hay cambios, compila antes):

| Sección | Qué mira |
|---|---|
| Tamaño y páginas | el tamaño del papel, que no haya una segunda página ni filas que no caben, el margen y si hay color hasta el borde |
| Imágenes | la resolución real de cada imagen a su tamaño en el póster (también las de dentro de las figuras PDF), las que faltan y las de ejemplo |
| Tamaño de letra | el texto principal y lo más pequeño de cada parte, también dentro de las figuras, según el tamaño del póster |
| Contraste | cada texto frente a lo que tiene detrás (fórmula de las WCAG) |
| Color al imprimir | los colores del póster que la tinta (CMYK) no alcanza, con una muestra de cómo quedan |
| Tipografías | que todas vayan incrustadas y que ninguna sea de mapa de bits |
| Contenido | textos de ejemplo, citas sin referencia, líneas que se salen de su sitio y texto a menos de 5 mm del borde |

Cada comprobación explica qué pasa y cómo arreglarlo, y **Mostrar en el póster** acerca la vista previa a ese sitio. Los umbrales dependen del tamaño: en un A0 se recomiendan 150 ppi en las imágenes, 24 pt en el texto principal y 18 pt como mínimo (en un A1, unos 17 y 13 pt).

**Descargar › PDF para imprenta…** prepara otro PDF, sin tocar el del póster:

- **Sangrado** de 3 o 5 mm: el papel crece por cada lado y el fondo (y las imágenes o formas de las capas que llegan al borde) se alarga hasta ahí, para que al cortar no queden filos blancos.
- **Marcas de corte**: líneas en las esquinas, fuera del sangrado, en 10 mm de margen alrededor.
- **CMYK** (con Ghostscript y su perfil genérico). Úsalo solo si la imprenta lo pide; si te da su perfil ICC, mejor envía RGB y que conviertan ellos.

El PDF lleva las cajas TrimBox (el póster) y BleedBox (con el sangrado). En los proyectos de código el sangrado no se añade solo (las marcas y el CMYK sí).

## Tipografías

En el diseño general, **Tipografía del texto** y **Tipografía de los títulos**:

- **Clásicas**: Helvetica, Avant Garde, Palatino, Times, Bookman y Charter. Funcionan con cualquier LaTeX.
- **Libres de TeX Live**: Source Sans, Fira Sans, Roboto, Lato, Open Sans, Noto Sans, IBM Plex Sans, Atkinson Hyperlegible, Montserrat, Raleway, Cabin, Inter, Libertinus Serif, EB Garamond, Merriweather, Source Serif, Crimson, Noto Serif e IBM Plex Serif. Las que no estén instaladas salen marcadas (vienen en `texlive-fonts-extra`; MiKTeX y Overleaf las tienen).
- **Tuyas**: «Subir .ttf u .otf» (sube a la vez los archivos de la familia: normal, negrita, cursiva…). Se guardan en la carpeta `fuentes/` del proyecto. Si falta la negrita o la cursiva, se imitan. Un póster con una tipografía propia se compila con **LuaLaTeX** (algo más lento) y no puede combinarla con las libres de TeX Live: en su lugar se usa una clásica. El zip para Overleaf trae un `latexmkrc` para que Overleaf use LuaLaTeX sin tocar nada. Si la licencia de la tipografía no permite incrustarla en un PDF, la aplicación lo avisa.

En los proyectos de código, una primera línea `% !TEX program = lualatex` (o `xelatex`) hace que DocsLab compile con ese programa.

## LAB: cuadernos celda a celda y plantillas de gráficos

En el editor, arriba a la izquierda, el conmutador **Póster | LAB** (o Presentación, Tesis…) cambia entre el documento y su LAB.

**Cuadernos.** A la izquierda, los cuadernos del documento («Cuaderno nuevo», subir un `.ipynb` o abrir uno de una carpeta); en el centro, el cuaderno abierto; a la derecha, las figuras que ha guardado.

- «Código» y «Texto» añaden celdas (el texto es Markdown; doble clic para editarlo). Cada celda se sube, se baja, se convierte o se borra desde sus botones.
- ▶ ejecuta una celda; **Mayús + Intro** la ejecuta y pasa a la siguiente; **Ctrl + Intro** la ejecuta y se queda. «Ejecutar todo» recorre el cuaderno y se detiene en el primer error. En el menú ⋯: reiniciar Python y ejecutar todo, reiniciar (borra las variables) y limpiar las salidas.
- Python sigue encendido entre ejecuciones, así que las variables se conservan. Se apaga solo tras tres horas sin uso o al cerrar DocsLab.
- El cuaderno se guarda solo, con sus salidas, como un `.ipynb` normal. «Ejecutar en limpio» (en la tarjeta del cuaderno) lo ejecuta entero en un Python recién arrancado sin tocar el archivo.
- Al terminar cada ejecución, las imágenes que el código guardó en la carpeta del cuaderno (PDF, PNG o JPG) aparecen en «Figuras del cuaderno» y en «Imágenes». Selecciona en el documento dónde va una y pulsa «Usar». Si vuelves a ejecutar, el documento se actualiza.

**Gráfico de plantilla.** Eliges el tipo de gráfico, tus datos (un archivo CSV, TSV, Excel, JSON o Parquet de la carpeta del cuaderno, o una tabla `DataFrame` que ya exista en el cuaderno), las columnas y las opciones (rótulos, tamaño, colores: por defecto los del documento). «Insertar y ejecutar» añade una celda con el código ya escrito y la ejecuta. Ese código es Python normal: edítalo para ajustes avanzados. «Ajustar el gráfico» vuelve al formulario (si cambiaste el código a mano, avisa de que lo regenera). Los gráficos de plotly se ven interactivos en el LAB y entran al documento como imagen fija; guardarlos necesita `kaleido` (y, en sus versiones 1.x, Chrome).

**Plantillas de gráficos.** La segunda pestaña del LAB. Una plantilla es código Python con huecos `{{nombre}}` y la lista de parámetros del formulario que los rellenan (datos, una o varias columnas, texto, número, sí o no, lista de opciones, color o paleta). Abre una incluida para ver cómo está hecha, «Copiar para modificarla» te da una tuya, o crea una desde cero. «Probar con los datos de ejemplo» la ejecuta con `ejemplo.csv` y muestra el resultado. Tus plantillas se guardan en `datos/graficos/` y sirven para todos tus documentos.

Las plantillas incluidas usan `pandas`, `matplotlib`, `seaborn` y `plotly`, que se instalan con `requirements.txt`. Tu código puede usar cualquier otro paquete que instales en el Python de DocsLab.

## Cuadernos: figuras dinámicas desde Colab o Jupyter

1. En **LAB**, «Subir un cuaderno»: elige el `.ipynb` y, a la vez, sus datos (CSV, un zip con varios archivos…). O «Abrir desde una carpeta» para usar un cuaderno que ya está en el servidor.
2. **Ejecutar**. El registro muestra cada celda y lo que imprime. Al terminar, las figuras nuevas (PNG, JPG o PDF) se copian a `recursos/cuadernos/<cuaderno>/…` y el póster se recompila.
3. Usa las figuras desde **Figuras** (en la tarjeta del cuaderno) o desde **Imágenes › Cuadernos**.
4. Cuando cambies el análisis, vuelve a ejecutar: las rutas no cambian, así que el póster se actualiza solo.

Ajustes de cada cuaderno: carpeta donde guarda las figuras, tipos de archivo, preferir PDF cuando hay PNG y PDF de la misma figura, recoger también las imágenes que solo se muestran, **omitir las celdas propias de Colab** (montar Drive, subir archivos), **parámetros** (código que se inserta después de la celda que elijas, por ejemplo `CONFIG["figure_dpi"] = 200`), tiempo máximo por celda y núcleo.

¿Prefieres ejecutarlo en Colab? En «Traer figuras desde Colab» copia una celda, pégala al final de tu cuaderno de Colab, ejecútala y sube el zip que descarga.

> Un cuaderno ejecuta código Python con tus permisos. Ejecuta solo cuadernos en los que confíes.

## Plantillas

Una plantilla es una carpeta con `plantilla.json` (nombre, descripción, tipo), `modelo.json` (el póster) o los archivos `.tex`, `recursos/` (imágenes), `fuentes/` (tipografías propias) y, si tiene, `cuadernos/`. Desde la aplicación:

- **Guardar como plantilla nueva** (menú ⋯ de un póster, en el inicio o en el editor): copia diseño, contenido, imágenes, tipografías y cuadernos.
- **Actualizar la plantilla «…»** (mismo menú): aparece en el póster desde el que guardaste la plantilla y en los pósters creados con ella. Sustituye el contenido de la plantilla por el del póster y conserva su nombre y su descripción; los pósters que ya se crearon con ella no cambian. Así, para retocar una plantilla: crea un póster con ella, edítalo y actualízala.
- **Renombrar o describir y borrar** (menú ⋯ de la plantilla). Las incluidas no se pueden modificar: crea un póster con una de ellas y guárdalo como plantilla tuya.
- **Exportar / importar**: el zip de una plantilla se importa con «Importar zip» en el inicio (también acepta zips de proyectos de DocsLab y cualquier proyecto LaTeX, por ejemplo de Overleaf).

Las plantillas incluidas se regeneran con `python herramientas/construir_plantillas.py`, y las miniaturas de las variantes con `python herramientas/miniaturas_variantes.py`.

## La plantilla LaTeX sin la aplicación

`latex/postercientifico.sty` funciona sola, también en Overleaf. El zip `plantilla_postercientifico_overleaf.zip` trae la plantilla, un póster de ejemplo por capas (`main.tex`), el catálogo de 6 páginas con todas las variantes (`catalogo.tex`) y las imágenes de prueba. En Overleaf: *New Project › Upload Project*, compila con pdfLaTeX y cambia de documento en *Menu › Main document*. Las filas con `alto=llenar` y las cajas con `estirar` se miden en una pasada y se ajustan en la siguiente: Overleaf repite solo; a mano, repite `pdflatex` mientras el registro diga «Rerun … (vuelve a compilar)» (2 o 3 veces).

Lo esencial:

```latex
\documentclass{article}
\usepackage{postercientifico}
\posterconfig{tamano=A0, tema=salvia, columnas=3, fuente=30pt, estilo bloque=barra,
              familia=sourcesans, familia titulos=merriweather, idioma=spanish}
\titulo{...} \autores{...} \afiliaciones{...}
\colocartexto[capa=frente, x=0.5, y=0.5, rotacion=30, escala=9, opacidad=0.1]{BORRADOR}
\begin{document}
\cabecera
\begin{fila}[columnas=3, alto=llenar]
  \begin{columna}
    \begin{caja}[titulo={Introducción}] ... \end{caja}
    \begin{caja}[titulo={Métodos}, mostrar titulo=false] ... \end{caja}
  \end{columna}
  \begin{columna}[abarca=2] ... \end{columna}
\end{fila}
\piedeposter{izquierda}{centro}{derecha}
\end{document}
```

Más claves:

- Tipografía propia (compila con LuaLaTeX): `\posterfamilia{mia}{fuentes/}{Mia-Regular.ttf}{Mia-Bold.ttf}{}{}` y `familia=mia`.
- Para la imprenta: `sangrado=3mm, marcas corte=true`.

El catálogo documenta todas las claves de `\posterconfig`, las cajas, las filas, las capas y las tipografías.

## Estructura del código

```
iniciar.command             lanzador para macOS y Linux: crea el entorno .venv y arranca
iniciar.bat                 lo mismo para Windows
servidor.py                 arranque (python servidor.py --abrir)
docslab/                  servidor (Flask)
  app.py                    API
  almacen.py                proyectos, plantillas, recursos y zips
  modelo.py                 el modelo JSON del póster (temas, tamaños, tipografías)
  variantes.py              las 69 variantes de elemento
  generador.py              modelo → LaTeX (también el PDF para imprenta)
  texto.py                  formato sencillo → LaTeX
  bibliografia.py           referencias: estilos, citas, BibTeX, RIS, CSL-JSON y DOI
  componentes.py            Componente Lab: componentes propios y su vista previa
  compilador.py             pdfLaTeX / LuaLaTeX, formato precompilado, errores, marcas, CMYK
  revision.py               revisión antes de imprimir
  powerpoint.py             exportar a PowerPoint (.pptx)
  fuentes.py                tipografías propias (.ttf, .otf)
  cuadernos.py              ejecución de .ipynb y recogida de figuras
  trabajos.py               trabajos en segundo plano
static/                     aplicación web (Vue 3, pdf.js y CodeMirror incluidos; funciona sin conexión)
  js/editor.js              el editor; vista.js (vista previa), directa.js (edición directa),
                            inspector.js, referencias.js, lab.js, revision.js, powerpoint.js, tipografias.js…
latex/postercientifico.sty  la plantilla LaTeX (por capas; versión en su \ProvidesPackage)
plantillas/                 plantillas incluidas
herramientas/               construir plantillas, miniaturas, lanzador de Colab, empaquetado,
                            huella digital (huella.py) y referencia de la API (doc_api.py)
docs/                       documentación funcional, arquitectura, API y versionado
huella/                     huella digital de cada versión publicada
tests/                      pruebas (pytest) y prueba en navegador (e2e_navegador.py)
abrir_docslab_en_colab.ipynb
```

## Pruebas

```
python -m pip install pytest     # con el entorno .venv activado
python -m pytest                 # 317 pruebas; las que necesitan LaTeX, Poppler, LuaLaTeX o Ghostscript se saltan si faltan
python tests/e2e_navegador.py    # opcional: necesita playwright y chromium
```

## Problemas frecuentes

- **`error: externally-managed-environment` al hacer `pip install`** (Python de Homebrew en macOS, Ubuntu 23.04 o posterior, Debian 12…): el sistema no deja instalar paquetes en su Python. Usa `sh iniciar.command` o el entorno `.venv` de «Instalación»; no hace falta `--break-system-packages` ni `pipx`.
- **`command not found: pip` o `python`**: en macOS y Linux se llaman `pip3` y `python3`; dentro del entorno `.venv` activado ya valen `pip` y `python`.
- **«Falta pdflatex»**: instala TeX Live, MacTeX o MiKTeX (arriba) y reinicia DocsLab.
- **`File 'tcolorbox.sty' not found`** (u otro paquete) **con TeX Live**: instala `texlive-latex-extra` y `texlive-pictures`, o `tlmgr install` y el nombre del paquete.
- **`File 'grfext.sty' not found`** (u otro paquete) **con MiKTeX**: DocsLab le pide a MiKTeX que instale solo lo que falta; si aun así sale (sin internet, o una versión antigua de DocsLab), abre MiKTeX Console → Packages, busca el paquete (el nombre del archivo sin `.sty`) e instálalo, o en Settings elige «Always install missing packages on-the-fly». Luego vuelve a compilar.
- **El póster ocupa 2 páginas**: hay más contenido del que cabe. Usa «Ajustar a una página», acorta textos o reduce imágenes.
- **Una tipografía libre sale «no instalada»**: instala `texlive-fonts-extra` (o el paquete de esa tipografía) y reinicia DocsLab.
- **No se pueden subir tipografías**: hace falta LuaLaTeX (`texlive-luatex` en Ubuntu; viene con MacTeX y MiKTeX). La primera compilación con una tipografía nueva tarda unos segundos más.
- **CMYK no está disponible** o la sección «Color al imprimir» no se revisa: instala Ghostscript (`ghostscript` en Ubuntu, `brew install ghostscript` en macOS).
- **PowerPoint: falta «python-pptx»**: con los lanzadores se instala solo al arrancar; a mano, `python -m pip install -r requirements.txt` con el entorno `.venv` activado. **Sin la opción de texto editable**: hace falta Ghostscript.
- **La revisión dice «No se pudo revisar»**: faltan las herramientas de Poppler (`poppler-utils`).
- **Un cuaderno falla con `ModuleNotFoundError: google.colab`**: activa «Omitir las celdas propias de Colab».
- **Un cuaderno no encuentra sus datos**: súbelos en «Datos del cuaderno» (menú ⋯ de la tarjeta).
- **Falta un paquete de Python en el cuaderno**: instálalo en el entorno de DocsLab: `.venv/bin/python -m pip install …` (Windows: `.venv\Scripts\python -m pip install …`).
- **El puerto está ocupado**: `sh iniciar.command --puerto 9000` (o `python servidor.py --puerto 9000`).

## Licencias de terceros

Incluidos en `static/vendor/`: Vue 3 (MIT), pdf.js (Apache 2.0), CodeMirror 5 (MIT) y las tipografías Atkinson Hyperlegible Next y Mono (SIL Open Font License 1.1). Las licencias completas están junto a cada archivo.

## Si venías de PosterLab

DocsLab es la continuación de PosterLab. Tus pósters se abren igual: importa el zip de cada proyecto («Importar zip») o copia tu carpeta `datos` a la de DocsLab. Los proyectos sin tipo se tratan como pósters. La plantilla LaTeX conserva su nombre (`postercientifico.sty`) para que los proyectos LaTeX y los zips de Overleaf anteriores sigan compilando. En Colab, el cuaderno lanzador copia una vez `MyDrive/PosterLab/datos` a `MyDrive/DocsLab/datos` si esta última no existe.

## Licencia

Copyright (C) 2026 Christian.

DocsLab es software libre: puedes redistribuirlo y modificarlo bajo los términos de la **GNU Affero General Public License, versión 3** (`AGPL-3.0-only`), publicada por la Free Software Foundation. Se distribuye con la esperanza de que sea útil, pero **SIN NINGUNA GARANTÍA**, ni siquiera la implícita de COMERCIABILIDAD o IDONEIDAD PARA UN PROPÓSITO PARTICULAR. El texto completo está en [`LICENSE`](LICENSE).

En la práctica:

- Puedes usarlo, estudiarlo, modificarlo y redistribuirlo, también con fines comerciales.
- Si distribuyes una versión (modificada o no), debe ir con su código fuente y bajo la misma licencia.
- **Cláusula de red (§13):** si modificas DocsLab y lo ofreces a otras personas a través de una red (por ejemplo, un servidor compartido), debes ofrecerles el código fuente de tu versión modificada.
- Los documentos que produces con DocsLab (PDF, `.tex`, `.pptx`) son tuyos; la licencia cubre el programa, no tu contenido.

Cada archivo de código propio lleva la cabecera `SPDX-License-Identifier: AGPL-3.0-only`. Las librerías de `static/vendor/` conservan sus propias licencias (ver «Licencias de terceros»).
