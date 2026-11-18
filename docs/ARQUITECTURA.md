# Arquitectura · DocsLab 1.1.0

## 1. Vista general

```
Navegador (Vue 3 sin bundler, pdf.js, CodeMirror; todo en static/vendor, sin conexión)
        │  HTTP/JSON  (95 rutas, ver docs/API.md)
        ▼
Flask  docslab/app.py ──────────────┐
  │                                 │ trabajos.py  (hilos: compilar, ejecutar cuadernos;
  ├─ almacen.py   disco: proyectos, │               progreso, registro y cancelación)
  │               plantillas, zips  │
  ├─ modelo.py    modelo JSON        │
  │    └─ migraciones.py  esquema N→N+1 │
  ├─ generador.py modelo → .tex ─────┼─► compilador.py ─► pdflatex / lualatex (-no-shell-escape)
  │    ├─ variantes.py  (69)         │        │                 formato precompilado (mylatexformat)
  │    ├─ texto.py      marcado      │        ├─► pdftoppm (Poppler): miniaturas y recortes
  │    ├─ bibliografia.py            │        └─► gs (Ghostscript): CMYK
  │    ├─ componentes.py             │
  │    └─ fuentes.py                 │
  ├─ revision.py   análisis del PDF ─┤
  ├─ powerpoint.py PDF → .pptx ──────┤  (pdftohtml -xml, Ghostscript para el modo editable)
  ├─ cuadernos.py  .ipynb completo ──┤  (nbclient/nbformat)
  ├─ lab.py        núcleo interactivo┘  (ipykernel, celda a celda; se apaga tras 3 h sin uso)
  └─ graficos.py   plantillas de gráficos → código Python
```

## 2. Módulos del backend

| Módulo | Líneas | Responsabilidad |
|---|---:|---|
| `app.py` | 1189 | Fábrica de Flask, rutas y validación de entrada |
| `almacen.py` | 661 | Disco: proyectos, plantillas, recursos, historial, importar/exportar zips (Overleaf, proyecto, plantilla) |
| `modelo.py` | 815 | Esquema y valores por defecto del modelo JSON: clases, tamaños, temas, idiomas, tipografías, capas, `normalizar()` |
| `migraciones.py` | 107 | Migraciones del esquema del modelo, en cadena, con detección de modelos heredados y de esquemas más nuevos (ver `MIGRACIONES.md`) |
| `variantes.py` | 360 | Catálogo de las 69 variantes de elemento y sus campos |
| `generador.py` | 1183 | Modelo → LaTeX, con un mapa línea→elemento para ubicar errores. También el PDF para imprenta |
| `texto.py` | 148 | Marcado sencillo (`**`, `*`, `^`, `~`, `$…$`, `[@clave]`, `{{…}}`) → LaTeX escapado |
| `bibliografia.py` | 1837 | 8 estilos de cita, numeración, BibTeX/RIS/CSL-JSON y DOI |
| `componentes.py` | 1052 | Componente Lab: piezas o código, campos `{{…}}`, vista previa, importar/exportar (formato v1) |
| `compilador.py` | 624 | Detecta el motor (TeX Live o MiKTeX), formato precompilado, pasadas, errores, marcas de posición y CMYK |
| `revision.py` | 1147 | Revisión antes de imprimir (resolución, letra, contraste, gama, tipografías, contenido) |
| `powerpoint.py` | 584 | Exportación .pptx editable (texto sobre imagen sin texto) o como imagen |
| `fuentes.py` | 172 | Tipografías propias .ttf/.otf: lectura de metadatos, familias, licencia de incrustación |
| `cuadernos.py` | 502 | Ejecución completa de `.ipynb`, recogida de figuras y celda para Colab |
| `lab.py` | 540 | Núcleos Jupyter persistentes por cuaderno del LAB |
| `graficos.py` | 556 | Plantillas de gráficos (`{{param}}`) → código Python |
| `trabajos.py` | 116 | Cola de trabajos en hilos, con progreso, registro (400 líneas) y cancelación |

## 3. Frontend (`static/js`)

Son módulos ES cargados por `index.html`, sin paso de compilación. Piezas principales: `app.js` (arranque y rutas), `inicio.js` (inicio y asistente), `editor.js` (el editor), `vista.js` (vista previa con pdf.js), `directa.js` (edición directa), `inspector.js` y `campos.js` (formularios), `arbol.js` (estructura), `referencias.js`, `lab.js`, `cuaderno.js`, `cuadernos.js`, `revision.js`, `powerpoint.js`, `tipografias.js`, `latex.js` (modo código), `modeloed.js` (operaciones sobre el modelo), `tienda.js` (estado), `api.js` (cliente HTTP) y `util.js`.

## 4. Almacenamiento (`datos/`, configurable con `--datos`)

```
datos/
  proyectos/<pid>/
    modelo.json            ← proyectos estructurados (clave version_esquema; actual: 1)
    *.tex                  ← proyectos en modo LaTeX
    postercientifico.sty
    recursos/              imágenes (recursos/cuadernos/<nb>/… para las figuras de cuadernos)
    fuentes/               tipografías propias
    cuadernos/             .ipynb y sus datos
    historial/             modelo-AAAAMMDD-HHMMSS.json (≥120 s entre copias; se guardan las 30 últimas)
                           modelo-antes-de-esquema-<N>.json (copia previa a una migración)
    build/                 salida de LaTeX
  plantillas/<tid>/        plantillas del usuario (misma forma + plantilla.json)
  componentes/             biblioteca del Componente Lab
  graficos/                plantillas de gráficos propias
```

Las plantillas incluidas viven en `plantillas/` dentro de la aplicación y son de solo lectura.

## 5. Flujo de compilación

1. El cliente guarda (`PUT /api/proyectos/<pid>/modelo`) → `almacen.guardar_modelo()` → `modelo.normalizar()` (que primero aplica `migraciones.migrar()`) y copia al historial.
2. `POST …/compilar` crea un trabajo → `generador.generar()` produce el `.tex` y el mapa de líneas.
3. `compilador.compilar()`: usa el formato precompilado si existe y repite pasadas hasta que el `.aux` deja de cambiar; si nada ha cambiado, no compila.
4. Con un error, se conserva el último PDF correcto y el error se traduce al elemento de origen.
5. La miniatura y las marcas de posición (para la edición directa) se generan aparte.

## 6. Dependencias externas

| Tipo | Componente | Obligatorio |
|---|---|---|
| Python | flask, pillow, python-pptx, nbclient, nbformat, ipykernel, pandas, matplotlib, seaborn, plotly, kaleido | Sí (`requirements.txt`) |
| Sistema | pdfLaTeX (TeX Live / MacTeX / MiKTeX) | Sí |
| Sistema | Poppler (`pdftoppm`, `pdftohtml`) | Para la revisión, las miniaturas y PowerPoint |
| Sistema | Ghostscript | Para CMYK y PowerPoint editable |
| Sistema | LuaLaTeX | Para tipografías propias |
| Incluidas | Vue 3, pdf.js, CodeMirror, Atkinson Hyperlegible | Sí, con sus licencias en `static/vendor/` |

## 7. Herramientas (`herramientas/`)

| Script | Uso |
|---|---|
| `construir_plantillas.py` | Regenera las plantillas incluidas |
| `construir_graficos.py` | Regenera las miniaturas de las plantillas de gráficos |
| `miniaturas_variantes.py` | Regenera las miniaturas de las 69 variantes |
| `imagenes_prueba.py` | Imágenes de prueba |
| `crear_lanzador_colab.py` | Genera `abrir_docslab_en_colab.ipynb` |
| `empaquetar.py` | Zip de distribución |
| `huella.py` | Huella digital de la versión (ver `VERSIONADO.md`) |
| `doc_api.py` | Genera `docs/API.md` |
