# Referencia de la API HTTP

> Archivo generado por `herramientas/doc_api.py` a partir de `docslab/app.py`. No editar a mano.

Total: **95** combinaciones método + ruta. Base: `http://127.0.0.1:8765`. Formato: JSON salvo descargas (PDF, PNG, ZIP, PPTX, BIB). Sin autenticación (ver `SECURITY.md`).

Parámetros de ruta: `<pid>` proyecto · `<tid>` plantilla o trabajo · `<cid>` componente · `<gid>` plantilla de gráfico · `<nb>` cuaderno · `<path:ruta>` ruta relativa dentro del proyecto.

## Estado del servidor

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/estado` | `estado` (L80) | — |

## Catálogo de variantes

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/variantes` | `lista_variantes` (L104) | — |

## Cuadernos (ejecución completa)

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/proyectos/<pid>/cuadernos` | `lista_cuadernos` (L1092) | — |
| `POST` | `/api/proyectos/<pid>/cuadernos` | `cuaderno_nuevo` (L1103) | — |
| `DELETE` | `/api/proyectos/<pid>/cuadernos/<nb>` | `cuaderno_borrar` (L1120) | — |
| `PATCH` | `/api/proyectos/<pid>/cuadernos/<nb>` | `cuaderno_cambiar` (L1116) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/archivos` | `cuaderno_archivos` (L1130) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/celda-colab` | `cuaderno_celda` (L1162) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/celdas` | `cuaderno_celdas` (L1126) | — |
| `POST` | `/api/proyectos/<pid>/cuadernos/<nb>/datos` | `cuaderno_datos` (L1134) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/ejecutado` | `cuaderno_ejecutado` (L1166) | — |
| `POST` | `/api/proyectos/<pid>/cuadernos/<nb>/ejecutar` | `cuaderno_ejecutar` (L1138) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/figuras` | `cuaderno_figuras` (L1158) | — |
| `POST` | `/api/proyectos/<pid>/cuadernos/<nb>/importar` | `cuaderno_importar` (L1151) | — |

## LAB (núcleo interactivo, celda a celda)

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/proyectos/<pid>/lab/<nb>` | `lab_cuaderno` (L980) | — |
| `PUT` | `/api/proyectos/<pid>/lab/<nb>` | `lab_guardar` (L984) | — |
| `POST` | `/api/proyectos/<pid>/lab/<nb>/<accion>` | `lab_accion` (L1013) | — |
| `POST` | `/api/proyectos/<pid>/lab/<nb>/ejecutar` | `lab_ejecutar` (L998) | — |
| `GET` | `/api/proyectos/<pid>/lab/<nb>/estado` | `lab_estado` (L990) | — |

## Proyectos

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/proyectos` | `proyectos` (L300) | — |
| `POST` | `/api/proyectos` | `proyecto_nuevo` (L304) | — |
| `DELETE` | `/api/proyectos/<pid>` | `proyecto_borrar` (L337) | — |
| `GET` | `/api/proyectos/<pid>` | `proyecto` (L316) | — |
| `PATCH` | `/api/proyectos/<pid>` | `proyecto_cambiar` (L324) | — |
| `POST` | `/api/proyectos/<pid>/ajustar` | `ajustar` (L569) | — |
| `GET` | `/api/proyectos/<pid>/archivos` | `archivos` (L856) | — |
| `POST` | `/api/proyectos/<pid>/archivos` | `archivo_subir` (L874) | — |
| `DELETE` | `/api/proyectos/<pid>/archivos/<path:ruta>` | `archivo_borrar` (L869) | — |
| `GET` | `/api/proyectos/<pid>/archivos/<path:ruta>` | `archivo_leer` (L860) | — |
| `PUT` | `/api/proyectos/<pid>/archivos/<path:ruta>` | `archivo_escribir` (L864) | — |
| `GET` | `/api/proyectos/<pid>/bibliografia.bib` | `bib_exportar` (L254) | — |
| `GET` | `/api/proyectos/<pid>/compilacion` | `compilacion` (L804) | — |
| `POST` | `/api/proyectos/<pid>/compilar` | `compilar` (L793) | — |
| `POST` | `/api/proyectos/<pid>/convertir-latex` | `convertir_latex` (L372) | — |
| `POST` | `/api/proyectos/<pid>/duplicar` | `proyecto_duplicar` (L343) | — |
| `GET` | `/api/proyectos/<pid>/exportar` | `exportar` (L844) | — |
| `GET` | `/api/proyectos/<pid>/f/<path:ruta>` | `fichero` (L934) | — |
| `POST` | `/api/proyectos/<pid>/formato` | `formato_texto` (L355) | — |
| `DELETE` | `/api/proyectos/<pid>/fuentes` | `fuentes_borrar` (L907) | — |
| `GET` | `/api/proyectos/<pid>/fuentes` | `fuentes` (L890) | — |
| `POST` | `/api/proyectos/<pid>/fuentes` | `fuentes_subir` (L894) | — |
| `GET` | `/api/proyectos/<pid>/historial` | `historial` (L364) | — |
| `POST` | `/api/proyectos/<pid>/historial/<nombre>/restaurar` | `historial_restaurar` (L368) | — |
| `POST` | `/api/proyectos/<pid>/imprenta` | `imprenta` (L755) | — |
| `GET` | `/api/proyectos/<pid>/imprenta.pdf` | `imprenta_pdf` (L763) | — |
| `GET` | `/api/proyectos/<pid>/imprenta.png` | `imprenta_png` (L776) | — |
| `GET` | `/api/proyectos/<pid>/latex` | `ver_latex` (L376) | — |
| `GET` | `/api/proyectos/<pid>/miniatura` | `miniatura` (L837) | — |
| `PUT` | `/api/proyectos/<pid>/modelo` | `modelo_guardar` (L347) | — |
| `GET` | `/api/proyectos/<pid>/pdf` | `pdf` (L823) | — |
| `POST` | `/api/proyectos/<pid>/powerpoint` | `powerpoint` (L733) | — |
| `GET` | `/api/proyectos/<pid>/powerpoint.pptx` | `powerpoint_pptx` (L741) | — |
| `DELETE` | `/api/proyectos/<pid>/recursos` | `recursos_borrar` (L929) | — |
| `GET` | `/api/proyectos/<pid>/recursos` | `recursos` (L914) | — |
| `POST` | `/api/proyectos/<pid>/recursos` | `recursos_subir` (L918) | — |
| `POST` | `/api/proyectos/<pid>/revisar` | `revisar` (L599) | — |
| `GET` | `/api/proyectos/<pid>/trabajos` | `trabajos_proyecto` (L1179) | — |
| `GET` | `/api/proyectos/<pid>/vista` | `vista_recurso` (L942) | Miniatura de un recurso (PNG/JPG reducidos con Pillow, PDF con pdftoppm). |
| `POST` | `/api/proyectos/importar` | `proyecto_importar` (L309) | — |

## Plantillas

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/plantillas` | `plantillas` (L263) | — |
| `POST` | `/api/plantillas` | `plantilla_nueva` (L267) | — |
| `DELETE` | `/api/plantillas/<tid>` | `plantilla_borrar` (L281) | — |
| `PATCH` | `/api/plantillas/<tid>` | `plantilla_cambiar` (L272) | — |
| `PUT` | `/api/plantillas/<tid>` | `plantilla_reemplazar` (L276) | Sustituye el contenido de una plantilla propia por el de un proyecto. |
| `GET` | `/api/plantillas/<tid>/exportar` | `plantilla_exportar` (L293) | — |
| `GET` | `/api/plantillas/<tid>/miniatura` | `plantilla_miniatura` (L286) | — |

## Componente Lab

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/componentes` | `componentes` (L131) | — |
| `POST` | `/api/componentes` | `componente_nuevo` (L135) | — |
| `DELETE` | `/api/componentes/<cid>` | `componente_borrar` (L150) | — |
| `GET` | `/api/componentes/<cid>` | `componente` (L142) | — |
| `PUT` | `/api/componentes/<cid>` | `componente_guardar` (L146) | — |
| `POST` | `/api/componentes/<cid>/duplicar` | `componente_duplicar` (L154) | — |
| `GET` | `/api/componentes/<cid>/miniatura` | `componente_miniatura` (L199) | — |
| `POST` | `/api/componentes/codigo` | `componente_codigo` (L170) | El LaTeX de un componente (para «Ver el código» y «Pasar a código»). |
| `GET` | `/api/componentes/exportar` | `componentes_exportar` (L205) | — |
| `POST` | `/api/componentes/importar` | `componentes_importar` (L216) | — |
| `POST` | `/api/componentes/recrear` | `componente_recrear` (L158) | Un borrador (sin guardar, sin id) para recrear uno de los incluidos. |
| `POST` | `/api/componentes/vista` | `componente_vista` (L177) | — |
| `GET` | `/api/componentes/vistas/<h>.pdf` | `componente_vista_pdf` (L192) | — |

## Plantillas de gráficos

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/graficos` | `graficos_lista` (L1042) | — |
| `POST` | `/api/graficos` | `graficos_guardar` (L1055) | — |
| `DELETE` | `/api/graficos/<gid>` | `graficos_borrar` (L1059) | — |
| `GET` | `/api/graficos/<gid>/miniatura` | `graficos_miniatura` (L1064) | — |
| `POST` | `/api/graficos/generar` | `graficos_generar` (L1071) | — |
| `POST` | `/api/graficos/probar` | `graficos_probar` (L1077) | — |

## LAB (recursos)

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/lab/plotly.min.js` | `lab_plotly` (L1032) | — |

## Bibliografía

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/bibliografia/doi` | `bib_doi` (L247) | — |
| `POST` | `/api/bibliografia/formatear` | `bib_formatear` (L223) | — |
| `POST` | `/api/bibliografia/importar` | `bib_importar` (L237) | — |
| `POST` | `/api/bibliografia/vista` | `bibliografia_vista` (L230) | — |

## Trabajos en segundo plano

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/trabajos/<tid>` | `trabajo` (L1183) | — |
| `POST` | `/api/trabajos/<tid>/cancelar` | `trabajo_cancelar` (L1190) | — |

## Explorador de carpetas

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/explorar` | `explorar` (L1174) | — |

## Aplicación web

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/` | `inicio` (L62) | — |
| `GET` | `/static/<path:ruta>` | `estatico` (L66) | — |
