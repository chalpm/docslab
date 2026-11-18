# Política de seguridad

## Versiones con soporte

| Versión | Soporte |
|---|---|
| 1.0.x | ✅ |

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
[NO VERIFICADO] Aún no hay un canal definido. Hasta que lo haya, repórtala en privado al responsable del proyecto, no en un issue público.
