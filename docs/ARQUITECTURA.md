# Arquitectura · DocsLab 1.5.1

## 1. Vista general

```
Navegador (Vue 3 sin bundler, pdf.js, CodeMirror; todo en static/vendor, sin conexión)
        │  HTTP/JSON  (95 rutas, ver docs/API.md)
        ▼
Flask  docslab/app.py  crear_app(): configuración, errores y registro de 9 blueprints
  │
  ├─ api/        rutas HTTP por área (sistema, componentes, bibliografia, plantillas,
  │              proyectos, documento, lab, graficos, trabajos)
  │
  ├─ nucleo/     almacen.py   disco: proyectos, plantillas, recursos, historial, zips
  │              modelo.py    modelo JSON  └─ migraciones.py  esquema N→N+1
  │              trabajos.py  hilos: compilar, ejecutar; progreso, registro, cancelación
  │
  ├─ documento/  generador.py modelo → .tex ──────┐
  │              variantes.py (69) · texto.py     │
  │              bibliografia.py · componentes.py │
  │              fuentes.py                       │
  │                                               ▼
  ├─ salidas/    compilador.py ─► pdflatex / lualatex (-no-shell-escape), formato precompilado
  │                    ├─► pdftoppm (Poppler): miniaturas y recortes
  │                    └─► gs (Ghostscript): CMYK
  │              revision.py    análisis del PDF
  │              powerpoint.py  PDF → .pptx (pdftohtml -xml; Ghostscript en modo editable)
  │
  └─ lab/        nucleos.py    núcleo interactivo (ipykernel, celda a celda; se apaga tras 3 h sin uso)
                 cuadernos.py  .ipynb completo (nbclient/nbformat)
                 graficos/     plantillas de gráficos → código Python (+ datos_ejemplo/)
```

Dependencias entre subpaquetes (estado en 1.5.1): `api` usa todos; `lab` solo usa `nucleo`; `nucleo`, `documento` y `salidas` se importan entre sí (p. ej., `almacen` usa `generador` y `compilador`; `generador` usa `compilador`). Separarlos en capas estrictas queda como trabajo futuro.

## 2. Módulos del backend

| Módulo (`docslab/…`) | Líneas | Responsabilidad |
|---|---:|---|
| `app.py` | 66 | Fábrica de Flask: configuración, manejadores de error, contexto compartido y registro de los blueprints |
| `api/sistema.py` | 85 | Estado del servidor, catálogo, tipografías del sistema, archivos estáticos |
| `api/componentes.py` | 120 | Rutas del Componente Lab |
| `api/bibliografia.py` | 60 | Importar referencias, DOI, estilos |
| `api/plantillas.py` | 55 | Plantillas incluidas y propias |
| `api/proyectos.py` | 231 | Crear, listar, importar/exportar proyectos, recursos, historial |
| `api/documento.py` | 500 | Modelo, LaTeX, compilar, ajustar, revisión, imprenta, PowerPoint |
| `api/lab.py` | 173 | Cuadernos del LAB: ejecutar, reiniciar, borrar variables, instalar paquetes, ejemplos |
| `api/graficos.py` | 69 | Plantillas de gráficos |
| `api/trabajos.py` | 33 | Estado y cancelación de trabajos en segundo plano |
| `nucleo/almacen.py` | 678 | Disco: proyectos, plantillas, recursos, historial, importar/exportar zips (Overleaf, proyecto, plantilla) |
| `nucleo/modelo.py` | 819 | Esquema y valores por defecto del modelo JSON: clases, tamaños, temas, idiomas, tipografías, capas, `normalizar()` |
| `nucleo/migraciones.py` | 107 | Migraciones del esquema del modelo, en cadena, con detección de modelos heredados y de esquemas más nuevos (ver `MIGRACIONES.md`) |
| `nucleo/trabajos.py` | 117 | Cola de trabajos en hilos, con progreso, registro (400 líneas) y cancelación |
| `documento/variantes.py` | 361 | Catálogo de las 69 variantes de elemento y sus campos |
| `documento/generador.py` | 1184 | Modelo → LaTeX, con un mapa línea→elemento para ubicar errores. También el PDF para imprenta |
| `documento/texto.py` | 149 | Marcado sencillo (`**`, `*`, `^`, `~`, `$…$`, `[@clave]`, `{{…}}`) → LaTeX escapado |
| `documento/bibliografia.py` | 1838 | 8 estilos de cita, numeración, BibTeX/RIS/CSL-JSON y DOI |
| `documento/componentes.py` | 1054 | Componente Lab: piezas o código, campos `{{…}}`, vista previa, importar/exportar (formato v1) |
| `documento/fuentes.py` | 173 | Tipografías propias .ttf/.otf: lectura de metadatos, familias, licencia de incrustación |
| `salidas/compilador.py` | 625 | Detecta el motor (TeX Live o MiKTeX), formato precompilado, pasadas, errores, marcas de posición y CMYK |
| `salidas/revision.py` | 1149 | Revisión antes de imprimir (resolución, letra, contraste, gama, tipografías, contenido) |
| `salidas/powerpoint.py` | 585 | Exportación .pptx editable (texto sobre imagen sin texto) o como imagen |
| `lab/nucleos.py` | 596 | Núcleos Jupyter persistentes por cuaderno del LAB; reiniciar y borrar variables |
| `lab/cuadernos.py` | 503 | Ejecución completa de `.ipynb`, recogida de figuras y celda para Colab |
| `lab/graficos/__init__.py` | 540 | Catálogo de plantillas de gráficos (`{{param}}`) → código Python; categorías; probar con los datos de ejemplo |
| `lab/graficos/comun.py` | 60 | Piezas comunes de las plantillas (parámetros, cabeceras y pies de código) |
| `lab/graficos/galeria.py` | 1219 | Las plantillas de la galería (F-26) |
| `lab/graficos/ciencia.py` | 955 | Las 25 plantillas de análisis científico (F-27) |
| `lab/graficos/datos_ejemplo/` | — | Datos de ejemplo de las plantillas y mapa base |

Cada área de `api/` expone `registrar(app, c)`: crea su `Blueprint`, toma del contexto `c` (un `SimpleNamespace` con `alm`, `trabajos`, `raices`, `lab`, `graficos`, `biblio` y las utilidades `json_body`, `sin_cache`, `archivos_subidos`) lo que necesita, y se registra en la app.

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
| Python | flask, pillow, python-pptx, nbclient, nbformat, ipykernel, pandas, matplotlib, seaborn, plotly, kaleido, scipy, scikit-learn | Sí (`requirements.txt`) |
| Datos | Natural Earth 1:110m (países), en `docslab/datos_ejemplo/mundo.geojson` | Incluido (dominio público) |
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
| `datos_ejemplo.py` | Regenera `docslab/datos_ejemplo/` (necesita el GeoJSON de Natural Earth) |
| `huella.py` | Huella digital de la versión (ver `VERSIONADO.md`) |
| `doc_api.py` | Genera `docs/API.md` |
