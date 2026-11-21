# Referencia de la API HTTP

> Archivo generado por `herramientas/doc_api.py` a partir de `docslab/api/*.py`. No editar a mano.

Total: **97** combinaciones método + ruta. Base: `http://127.0.0.1:8765`. Formato: JSON salvo descargas (PDF, PNG, ZIP, PPTX, BIB). Sin autenticación (ver `SECURITY.md`).

**Cabecera obligatoria (desde 1.6.0):** las peticiones POST, PUT, PATCH y DELETE deben llevar `X-DocsLab: 1`; sin ella, 403. Si llevan `Origin`, debe ser el propio servidor. El servidor solo atiende a `localhost`, `*.localhost`, direcciones IP y los nombres de `DOCSLAB_HOSTS`. Los errores (400, 403, 404, 405, 413, 500) llegan en JSON: `{"error": "…"}`.

Parámetros de ruta: `<pid>` proyecto · `<tid>` plantilla o trabajo · `<cid>` componente · `<gid>` plantilla de gráfico · `<nb>` cuaderno · `<path:ruta>` ruta relativa dentro del proyecto.

## Estado del servidor

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/api/estado` | `estado` (sistema.py:49) | — |

## Catálogo de variantes

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/api/variantes` | `lista_variantes` (sistema.py:66) | — |

## Cuadernos (ejecución completa)

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/api/proyectos/<pid>/cuadernos` | `lista_cuadernos` (lab.py:88) | — |
| `POST` | `/api/proyectos/<pid>/cuadernos` | `cuaderno_nuevo` (lab.py:99) | — |
| `DELETE` | `/api/proyectos/<pid>/cuadernos/<nb>` | `cuaderno_borrar` (lab.py:116) | — |
| `PATCH` | `/api/proyectos/<pid>/cuadernos/<nb>` | `cuaderno_cambiar` (lab.py:112) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/archivos` | `cuaderno_archivos` (lab.py:126) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/celda-colab` | `cuaderno_celda` (lab.py:158) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/celdas` | `cuaderno_celdas` (lab.py:122) | — |
| `POST` | `/api/proyectos/<pid>/cuadernos/<nb>/datos` | `cuaderno_datos` (lab.py:130) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/ejecutado` | `cuaderno_ejecutado` (lab.py:162) | — |
| `POST` | `/api/proyectos/<pid>/cuadernos/<nb>/ejecutar` | `cuaderno_ejecutar` (lab.py:134) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/figuras` | `cuaderno_figuras` (lab.py:154) | — |
| `POST` | `/api/proyectos/<pid>/cuadernos/<nb>/importar` | `cuaderno_importar` (lab.py:147) | — |

## LAB (núcleo interactivo, celda a celda)

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/api/proyectos/<pid>/lab/<nb>` | `lab_cuaderno` (lab.py:24) | — |
| `PUT` | `/api/proyectos/<pid>/lab/<nb>` | `lab_guardar` (lab.py:28) | — |
| `POST` | `/api/proyectos/<pid>/lab/<nb>/<accion>` | `lab_accion` (lab.py:57) | — |
| `POST` | `/api/proyectos/<pid>/lab/<nb>/ejecutar` | `lab_ejecutar` (lab.py:42) | — |
| `GET` | `/api/proyectos/<pid>/lab/<nb>/estado` | `lab_estado` (lab.py:34) | — |

## Proyectos

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/api/proyectos` | `proyectos` (proyectos.py:27) | — |
| `POST` | `/api/proyectos` | `proyecto_nuevo` (proyectos.py:31) | — |
| `DELETE` | `/api/proyectos/<pid>` | `proyecto_borrar` (proyectos.py:64) | — |
| `GET` | `/api/proyectos/<pid>` | `proyecto` (proyectos.py:43) | — |
| `PATCH` | `/api/proyectos/<pid>` | `proyecto_cambiar` (proyectos.py:51) | — |
| `POST` | `/api/proyectos/<pid>/ajustar` | `ajustar` (documento.py:215) | — |
| `GET` | `/api/proyectos/<pid>/archivos` | `archivos` (proyectos.py:113) | — |
| `POST` | `/api/proyectos/<pid>/archivos` | `archivo_subir` (proyectos.py:131) | — |
| `DELETE` | `/api/proyectos/<pid>/archivos/<path:ruta>` | `archivo_borrar` (proyectos.py:126) | — |
| `GET` | `/api/proyectos/<pid>/archivos/<path:ruta>` | `archivo_leer` (proyectos.py:117) | — |
| `PUT` | `/api/proyectos/<pid>/archivos/<path:ruta>` | `archivo_escribir` (proyectos.py:121) | — |
| `GET` | `/api/proyectos/<pid>/bibliografia.bib` | `bib_exportar` (bibliografia.py:53) | — |
| `GET` | `/api/proyectos/<pid>/compilacion` | `compilacion` (documento.py:506) | — |
| `POST` | `/api/proyectos/<pid>/compilar` | `compilar` (documento.py:495) | — |
| `POST` | `/api/proyectos/<pid>/convertir-latex` | `convertir_latex` (proyectos.py:99) | — |
| `POST` | `/api/proyectos/<pid>/duplicar` | `proyecto_duplicar` (proyectos.py:70) | — |
| `GET` | `/api/proyectos/<pid>/exportar` | `exportar` (documento.py:546) | — |
| `GET` | `/api/proyectos/<pid>/f/<path:ruta>` | `fichero` (proyectos.py:191) | — |
| `POST` | `/api/proyectos/<pid>/formato` | `formato_texto` (proyectos.py:82) | — |
| `DELETE` | `/api/proyectos/<pid>/fuentes` | `fuentes_borrar` (proyectos.py:164) | — |
| `GET` | `/api/proyectos/<pid>/fuentes` | `fuentes` (proyectos.py:147) | — |
| `POST` | `/api/proyectos/<pid>/fuentes` | `fuentes_subir` (proyectos.py:151) | — |
| `GET` | `/api/proyectos/<pid>/historial` | `historial` (proyectos.py:91) | — |
| `POST` | `/api/proyectos/<pid>/historial/<nombre>/restaurar` | `historial_restaurar` (proyectos.py:95) | — |
| `POST` | `/api/proyectos/<pid>/imprenta` | `imprenta` (documento.py:457) | — |
| `GET` | `/api/proyectos/<pid>/imprenta.pdf` | `imprenta_pdf` (documento.py:465) | — |
| `GET` | `/api/proyectos/<pid>/imprenta.png` | `imprenta_png` (documento.py:478) | — |
| `GET` | `/api/proyectos/<pid>/latex` | `ver_latex` (proyectos.py:103) | — |
| `GET` | `/api/proyectos/<pid>/miniatura` | `miniatura` (documento.py:539) | — |
| `PUT` | `/api/proyectos/<pid>/modelo` | `modelo_guardar` (proyectos.py:74) | — |
| `GET` | `/api/proyectos/<pid>/pdf` | `pdf` (documento.py:525) | — |
| `POST` | `/api/proyectos/<pid>/powerpoint` | `powerpoint` (documento.py:379) | — |
| `GET` | `/api/proyectos/<pid>/powerpoint.pptx` | `powerpoint_pptx` (documento.py:387) | — |
| `DELETE` | `/api/proyectos/<pid>/recursos` | `recursos_borrar` (proyectos.py:186) | — |
| `GET` | `/api/proyectos/<pid>/recursos` | `recursos` (proyectos.py:171) | — |
| `POST` | `/api/proyectos/<pid>/recursos` | `recursos_subir` (proyectos.py:175) | — |
| `POST` | `/api/proyectos/<pid>/revisar` | `revisar` (documento.py:245) | — |
| `GET` | `/api/proyectos/<pid>/trabajos` | `trabajos_proyecto` (trabajos.py:19) | — |
| `GET` | `/api/proyectos/<pid>/vista` | `vista_recurso` (proyectos.py:199) | Miniatura de un recurso (PNG/JPG reducidos con Pillow, PDF con pdftoppm). |
| `POST` | `/api/proyectos/<pid>/word` | `word` (documento.py:437) | — |
| `GET` | `/api/proyectos/<pid>/word.docx` | `word_docx` (documento.py:443) | — |
| `POST` | `/api/proyectos/importar` | `proyecto_importar` (proyectos.py:36) | — |

## Plantillas

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/api/plantillas` | `plantillas` (plantillas.py:20) | — |
| `POST` | `/api/plantillas` | `plantilla_nueva` (plantillas.py:24) | — |
| `DELETE` | `/api/plantillas/<tid>` | `plantilla_borrar` (plantillas.py:38) | — |
| `PATCH` | `/api/plantillas/<tid>` | `plantilla_cambiar` (plantillas.py:29) | — |
| `PUT` | `/api/plantillas/<tid>` | `plantilla_reemplazar` (plantillas.py:33) | Sustituye el contenido de una plantilla propia por el de un proyecto. |
| `GET` | `/api/plantillas/<tid>/exportar` | `plantilla_exportar` (plantillas.py:50) | — |
| `GET` | `/api/plantillas/<tid>/miniatura` | `plantilla_miniatura` (plantillas.py:43) | — |

## Componente Lab

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/api/componentes` | `componentes` (componentes.py:30) | — |
| `POST` | `/api/componentes` | `componente_nuevo` (componentes.py:34) | — |
| `DELETE` | `/api/componentes/<cid>` | `componente_borrar` (componentes.py:49) | — |
| `GET` | `/api/componentes/<cid>` | `componente` (componentes.py:41) | — |
| `PUT` | `/api/componentes/<cid>` | `componente_guardar` (componentes.py:45) | — |
| `POST` | `/api/componentes/<cid>/duplicar` | `componente_duplicar` (componentes.py:53) | — |
| `GET` | `/api/componentes/<cid>/miniatura` | `componente_miniatura` (componentes.py:98) | — |
| `POST` | `/api/componentes/codigo` | `componente_codigo` (componentes.py:69) | El LaTeX de un componente (para «Ver el código» y «Pasar a código»). |
| `GET` | `/api/componentes/exportar` | `componentes_exportar` (componentes.py:104) | — |
| `POST` | `/api/componentes/importar` | `componentes_importar` (componentes.py:115) | — |
| `POST` | `/api/componentes/recrear` | `componente_recrear` (componentes.py:57) | Un borrador (sin guardar, sin id) para recrear uno de los incluidos. |
| `POST` | `/api/componentes/vista` | `componente_vista` (componentes.py:76) | — |
| `GET` | `/api/componentes/vistas/<h>.pdf` | `componente_vista_pdf` (componentes.py:91) | — |

## Plantillas de gráficos

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/api/graficos` | `graficos_lista` (graficos.py:21) | — |
| `POST` | `/api/graficos` | `graficos_guardar` (graficos.py:34) | — |
| `DELETE` | `/api/graficos/<gid>` | `graficos_borrar` (graficos.py:38) | — |
| `GET` | `/api/graficos/<gid>/miniatura` | `graficos_miniatura` (graficos.py:43) | — |
| `POST` | `/api/graficos/generar` | `graficos_generar` (graficos.py:50) | — |
| `POST` | `/api/graficos/probar` | `graficos_probar` (graficos.py:56) | — |

## LAB (recursos)

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/api/lab/plotly.min.js` | `lab_plotly` (lab.py:78) | — |

## Bibliografía

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/api/bibliografia/doi` | `bib_doi` (bibliografia.py:46) | — |
| `POST` | `/api/bibliografia/formatear` | `bib_formatear` (bibliografia.py:22) | — |
| `POST` | `/api/bibliografia/importar` | `bib_importar` (bibliografia.py:36) | — |
| `POST` | `/api/bibliografia/vista` | `bibliografia_vista` (bibliografia.py:29) | — |

## Trabajos en segundo plano

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/api/trabajos/<tid>` | `trabajo` (trabajos.py:23) | — |
| `POST` | `/api/trabajos/<tid>/cancelar` | `trabajo_cancelar` (trabajos.py:30) | — |

## Explorador de carpetas

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/api/explorar` | `explorar` (lab.py:170) | — |

## Aplicación web

| Método | Ruta | Función (docslab/api/) | Descripción |
|---|---|---|---|
| `GET` | `/` | `inicio` (sistema.py:28) | — |
| `GET` | `/static/<path:ruta>` | `estatico` (sistema.py:32) | — |
