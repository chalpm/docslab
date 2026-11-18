# Política de seguridad

## Versiones con soporte

Solo la **última versión MINOR publicada** recibe correcciones de seguridad, que salen como una versión PATCH (por ejemplo, 1.2.1). Las versiones anteriores no reciben correcciones: si usas una, actualiza a la última. Al publicarse una MINOR nueva, la anterior deja de tener soporte.

| Versión | Soporte |
|---|---|
| 1.4.x | ✅ Con soporte |
| 1.3.x | ❌ Sin soporte: actualiza a 1.4.x |
| 1.2.x | ❌ Sin soporte: actualiza a 1.4.x |
| 1.1.x | ❌ Sin soporte: actualiza a 1.4.x |
| 1.0.x | ❌ Sin soporte: actualiza a 1.4.x |

## Modelo de amenazas

DocsLab está pensado como **aplicación local de un solo usuario**.

| Superficie | Estado en 1.0.0 | Riesgo |
|---|---|---|
| Interfaz de red | Escucha en `127.0.0.1:8765` por defecto | Bajo en local |
| `--host 0.0.0.0` | **Sin autenticación** | **Alto**: cualquiera en la red tiene acceso total |
| Cuadernos (`.ipynb`, LAB) | Ejecutan Python arbitrario con los permisos del usuario | **Alto** si el cuaderno no es de confianza |
| Compilación LaTeX | `-no-shell-escape` al compilar documentos (`compilador.py` L424 y L565). La precompilación del formato (L86) no lo pasa explícitamente, pero solo procesa contenido interno (`pcformato.tex` y la `.sty`) y depende del valor por defecto de la distribución | Bajo |
| Importación de zips | Se impide el *path traversal* (prueba `test_zip_malicioso_no_sale_de_su_carpeta`) | Bajo |
| Explorador de carpetas | Limitado a `--raices` (prueba `test_explorar_solo_dentro_de_las_raices`) | Bajo |
| Rutas y colores en el modelo | Se neutralizan antes de generar LaTeX (prueba `test_rutas_y_colores_peligrosos_se_neutralizan`) | Bajo |
| Búsqueda por DOI | Petición saliente a doi.org | Bajo |

## Recomendaciones de uso
- No uses `--host 0.0.0.0` fuera de una red de confianza.
- Ejecuta solo cuadernos y plantillas de origen conocido.
- En Colab, el enlace público solo funciona mientras el lanzador está conectado; no lo compartas.

## Reportar una vulnerabilidad

**No abras un issue público.** Reporta en privado por correo:

📧 **chalpm60@gmail.com** · asunto: `[DocsLab][seguridad] <resumen breve>`

Incluye, si puedes:
- versión de DocsLab (`GET /api/estado` o `docslab/__init__.py`) y sistema operativo;
- componente afectado (API, cuadernos/LAB, compilación LaTeX, importación de zips…);
- pasos para reproducirlo o una prueba de concepto mínima;
- impacto que estimas (quién puede explotarlo y qué consigue).

Qué esperar:
- Se acusa recibo y se evalúa el reporte; **no hay plazos de respuesta comprometidos**.
- Si se confirma, la corrección sale como versión PATCH de la última MINOR con soporte y se registra en `CHANGELOG.md` en la sección **Seguridad**, con crédito a quien la reportó si así lo desea.
- Pedimos divulgación coordinada: no publiques detalles hasta que haya una versión corregida.

> Canal secundario previsto: **GitHub Security Advisories** (reporte privado en el repositorio). Se activará cuando el repositorio público exista.

