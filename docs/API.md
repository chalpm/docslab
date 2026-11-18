# Referencia de la API HTTP

> Archivo generado por `herramientas/doc_api.py` a partir de `docslab/app.py`. No editar a mano.

Total: **95** combinaciones método + ruta. Base: `http://127.0.0.1:8765`. Formato: JSON salvo descargas (PDF, PNG, ZIP, PPTX, BIB). Sin autenticación (ver `SECURITY.md`).

Parámetros de ruta: `<pid>` proyecto · `<tid>` plantilla o trabajo · `<cid>` componente · `<gid>` plantilla de gráfico · `<nb>` cuaderno · `<path:ruta>` ruta relativa dentro del proyecto.

## Estado del servidor

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/estado` | `estado` (L79) | — |

## Catálogo de variantes

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/variantes` | `lista_variantes` (L103) | — |

## Cuadernos (ejecución completa)

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/proyectos/<pid>/cuadernos` | `lista_cuadernos` (L1088) | — |
| `POST` | `/api/proyectos/<pid>/cuadernos` | `cuaderno_nuevo` (L1099) | — |
| `DELETE` | `/api/proyectos/<pid>/cuadernos/<nb>` | `cuaderno_borrar` (L1116) | — |
| `PATCH` | `/api/proyectos/<pid>/cuadernos/<nb>` | `cuaderno_cambiar` (L1112) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/archivos` | `cuaderno_archivos` (L1126) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/celda-colab` | `cuaderno_celda` (L1158) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/celdas` | `cuaderno_celdas` (L1122) | — |
| `POST` | `/api/proyectos/<pid>/cuadernos/<nb>/datos` | `cuaderno_datos` (L1130) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/ejecutado` | `cuaderno_ejecutado` (L1162) | — |
| `POST` | `/api/proyectos/<pid>/cuadernos/<nb>/ejecutar` | `cuaderno_ejecutar` (L1134) | — |
| `GET` | `/api/proyectos/<pid>/cuadernos/<nb>/figuras` | `cuaderno_figuras` (L1154) | — |
| `POST` | `/api/proyectos/<pid>/cuadernos/<nb>/importar` | `cuaderno_importar` (L1147) | — |

## LAB (núcleo interactivo, celda a celda)

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/proyectos/<pid>/lab/<nb>` | `lab_cuaderno` (L979) | — |
| `PUT` | `/api/proyectos/<pid>/lab/<nb>` | `lab_guardar` (L983) | — |
| `POST` | `/api/proyectos/<pid>/lab/<nb>/<accion>` | `lab_accion` (L1012) | — |
| `POST` | `/api/proyectos/<pid>/lab/<nb>/ejecutar` | `lab_ejecutar` (L997) | — |
| `GET` | `/api/proyectos/<pid>/lab/<nb>/estado` | `lab_estado` (L989) | — |

## Proyectos

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/proyectos` | `proyectos` (L299) | — |
| `POST` | `/api/proyectos` | `proyecto_nuevo` (L303) | — |
| `DELETE` | `/api/proyectos/<pid>` | `proyecto_borrar` (L336) | — |
| `GET` | `/api/proyectos/<pid>` | `proyecto` (L315) | — |
| `PATCH` | `/api/proyectos/<pid>` | `proyecto_cambiar` (L323) | — |
| `POST` | `/api/proyectos/<pid>/ajustar` | `ajustar` (L568) | — |
| `GET` | `/api/proyectos/<pid>/archivos` | `archivos` (L855) | — |
| `POST` | `/api/proyectos/<pid>/archivos` | `archivo_subir` (L873) | — |
| `DELETE` | `/api/proyectos/<pid>/archivos/<path:ruta>` | `archivo_borrar` (L868) | — |
| `GET` | `/api/proyectos/<pid>/archivos/<path:ruta>` | `archivo_leer` (L859) | — |
| `PUT` | `/api/proyectos/<pid>/archivos/<path:ruta>` | `archivo_escribir` (L863) | — |
| `GET` | `/api/proyectos/<pid>/bibliografia.bib` | `bib_exportar` (L253) | — |
| `GET` | `/api/proyectos/<pid>/compilacion` | `compilacion` (L803) | — |
| `POST` | `/api/proyectos/<pid>/compilar` | `compilar` (L792) | — |
| `POST` | `/api/proyectos/<pid>/convertir-latex` | `convertir_latex` (L371) | — |
| `POST` | `/api/proyectos/<pid>/duplicar` | `proyecto_duplicar` (L342) | — |
| `GET` | `/api/proyectos/<pid>/exportar` | `exportar` (L843) | — |
| `GET` | `/api/proyectos/<pid>/f/<path:ruta>` | `fichero` (L933) | — |
| `POST` | `/api/proyectos/<pid>/formato` | `formato_texto` (L354) | — |
| `DELETE` | `/api/proyectos/<pid>/fuentes` | `fuentes_borrar` (L906) | — |
| `GET` | `/api/proyectos/<pid>/fuentes` | `fuentes` (L889) | — |
| `POST` | `/api/proyectos/<pid>/fuentes` | `fuentes_subir` (L893) | — |
| `GET` | `/api/proyectos/<pid>/historial` | `historial` (L363) | — |
| `POST` | `/api/proyectos/<pid>/historial/<nombre>/restaurar` | `historial_restaurar` (L367) | — |
| `POST` | `/api/proyectos/<pid>/imprenta` | `imprenta` (L754) | — |
| `GET` | `/api/proyectos/<pid>/imprenta.pdf` | `imprenta_pdf` (L762) | — |
| `GET` | `/api/proyectos/<pid>/imprenta.png` | `imprenta_png` (L775) | — |
| `GET` | `/api/proyectos/<pid>/latex` | `ver_latex` (L375) | — |
| `GET` | `/api/proyectos/<pid>/miniatura` | `miniatura` (L836) | — |
| `PUT` | `/api/proyectos/<pid>/modelo` | `modelo_guardar` (L346) | — |
| `GET` | `/api/proyectos/<pid>/pdf` | `pdf` (L822) | — |
| `POST` | `/api/proyectos/<pid>/powerpoint` | `powerpoint` (L732) | — |
| `GET` | `/api/proyectos/<pid>/powerpoint.pptx` | `powerpoint_pptx` (L740) | — |
| `DELETE` | `/api/proyectos/<pid>/recursos` | `recursos_borrar` (L928) | — |
| `GET` | `/api/proyectos/<pid>/recursos` | `recursos` (L913) | — |
| `POST` | `/api/proyectos/<pid>/recursos` | `recursos_subir` (L917) | — |
| `POST` | `/api/proyectos/<pid>/revisar` | `revisar` (L598) | — |
| `GET` | `/api/proyectos/<pid>/trabajos` | `trabajos_proyecto` (L1175) | — |
| `GET` | `/api/proyectos/<pid>/vista` | `vista_recurso` (L941) | Miniatura de un recurso (PNG/JPG reducidos con Pillow, PDF con pdftoppm). |
| `POST` | `/api/proyectos/importar` | `proyecto_importar` (L308) | — |

## Plantillas

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/plantillas` | `plantillas` (L262) | — |
| `POST` | `/api/plantillas` | `plantilla_nueva` (L266) | — |
| `DELETE` | `/api/plantillas/<tid>` | `plantilla_borrar` (L280) | — |
| `PATCH` | `/api/plantillas/<tid>` | `plantilla_cambiar` (L271) | — |
| `PUT` | `/api/plantillas/<tid>` | `plantilla_reemplazar` (L275) | Sustituye el contenido de una plantilla propia por el de un proyecto. |
| `GET` | `/api/plantillas/<tid>/exportar` | `plantilla_exportar` (L292) | — |
| `GET` | `/api/plantillas/<tid>/miniatura` | `plantilla_miniatura` (L285) | — |

## Componente Lab

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/componentes` | `componentes` (L130) | — |
| `POST` | `/api/componentes` | `componente_nuevo` (L134) | — |
| `DELETE` | `/api/componentes/<cid>` | `componente_borrar` (L149) | — |
| `GET` | `/api/componentes/<cid>` | `componente` (L141) | — |
| `PUT` | `/api/componentes/<cid>` | `componente_guardar` (L145) | — |
| `POST` | `/api/componentes/<cid>/duplicar` | `componente_duplicar` (L153) | — |
| `GET` | `/api/componentes/<cid>/miniatura` | `componente_miniatura` (L198) | — |
| `POST` | `/api/componentes/codigo` | `componente_codigo` (L169) | El LaTeX de un componente (para «Ver el código» y «Pasar a código»). |
| `GET` | `/api/componentes/exportar` | `componentes_exportar` (L204) | — |
| `POST` | `/api/componentes/importar` | `componentes_importar` (L215) | — |
| `POST` | `/api/componentes/recrear` | `componente_recrear` (L157) | Un borrador (sin guardar, sin id) para recrear uno de los incluidos. |
| `POST` | `/api/componentes/vista` | `componente_vista` (L176) | — |
| `GET` | `/api/componentes/vistas/<h>.pdf` | `componente_vista_pdf` (L191) | — |

## Plantillas de gráficos

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/graficos` | `graficos_lista` (L1041) | — |
| `POST` | `/api/graficos` | `graficos_guardar` (L1051) | — |
| `DELETE` | `/api/graficos/<gid>` | `graficos_borrar` (L1055) | — |
| `GET` | `/api/graficos/<gid>/miniatura` | `graficos_miniatura` (L1060) | — |
| `POST` | `/api/graficos/generar` | `graficos_generar` (L1067) | — |
| `POST` | `/api/graficos/probar` | `graficos_probar` (L1073) | — |

## LAB (recursos)

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/lab/plotly.min.js` | `lab_plotly` (L1031) | — |

## Bibliografía

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/bibliografia/doi` | `bib_doi` (L246) | — |
| `POST` | `/api/bibliografia/formatear` | `bib_formatear` (L222) | — |
| `POST` | `/api/bibliografia/importar` | `bib_importar` (L236) | — |
| `POST` | `/api/bibliografia/vista` | `bibliografia_vista` (L229) | — |

## Trabajos en segundo plano

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/trabajos/<tid>` | `trabajo` (L1179) | — |
| `POST` | `/api/trabajos/<tid>/cancelar` | `trabajo_cancelar` (L1186) | — |

## Explorador de carpetas

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/api/explorar` | `explorar` (L1170) | — |

## Aplicación web

| Método | Ruta | Función (app.py) | Descripción |
|---|---|---|---|
| `GET` | `/` | `inicio` (L61) | — |
| `GET` | `/static/<path:ruta>` | `estatico` (L65) | — |
