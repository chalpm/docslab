# Política de seguridad

## Versiones con soporte

Solo la **última versión MINOR publicada** recibe correcciones de seguridad, que salen como una versión PATCH (por ejemplo, 1.2.1). Las versiones anteriores no reciben correcciones: si usas una, actualiza a la última. Al publicarse una MINOR nueva, la anterior deja de tener soporte.

| Versión | Soporte |
|---|---|
| 1.8.x | ✅ Con soporte (Python 3.11 o posterior) |
| 1.7.x | ❌ Sin soporte: actualiza a 1.8.x |
| 1.6.x | ❌ Sin soporte: actualiza a 1.8.x |
| 1.5.x | ❌ Sin soporte: actualiza a 1.8.x (corrige fallos de seguridad, ver CHANGELOG) |
| 1.4.x | ❌ Sin soporte: actualiza a 1.8.x |
| 1.3.x | ❌ Sin soporte: actualiza a 1.8.x |
| 1.2.x | ❌ Sin soporte: actualiza a 1.8.x |
| 1.1.x | ❌ Sin soporte: actualiza a 1.8.x |
| 1.0.x | ❌ Sin soporte: actualiza a 1.8.x |

## Modelo de amenazas

DocsLab está pensado como **aplicación local de un solo usuario**.

| Superficie | Estado en 1.8.0 | Riesgo |
|---|---|---|
| Interfaz de red | Escucha en `127.0.0.1:8765` por defecto | Bajo en local |
| Otras webs abiertas en el navegador (CSRF) | Las peticiones que cambian algo exigen la cabecera `X-DocsLab: 1` (otra web no puede ponerla sin un permiso CORS que DocsLab nunca da) y, si traen `Origin`, que sea el propio servidor (`docslab/seguridad.py`; pruebas en `tests/test_seguridad.py`) | Bajo |
| DNS rebinding (un dominio ajeno que apunta a 127.0.0.1) | Solo se atienden `localhost`, `*.localhost`, direcciones IP y los nombres de `DOCSLAB_HOSTS`; el resto recibe 403 (en modo Colab filtra el proxy de Google) | Bajo |
| Salidas HTML de cuadernos | Se muestran en un `<iframe sandbox="allow-scripts">` sin el origen de DocsLab: un cuaderno ajeno no puede leer la página ni usar la API | Bajo |
| Marcos y tipos MIME | `Content-Security-Policy: frame-ancestors 'self'` (más Colab en ese modo), `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin` | Bajo |
| Imágenes subidas | Pillow ≥ 13.0 (sin avisos conocidos) solo con los formatos esperados y con su límite contra imágenes gigantes. Desde 1.7.0 el servidor exige Python 3.11, así que ya no se instalan Pillow anteriores | Bajo |
| Visor de PDF | pdf.js 4.10.38 con `isEvalSupported: false` | Bajo |
| Procesos del LAB | Como mucho `DOCSLAB_MAX_NUCLEOS` (4) a la vez; se apaga el que lleva más tiempo sin usarse | Bajo |
| `--host 0.0.0.0` | **Sin autenticación** | **Alto**: cualquiera en la red tiene acceso total |
| Cuadernos (`.ipynb`, LAB) | Ejecutan Python arbitrario con los permisos del usuario | **Alto** si el cuaderno no es de confianza |
| Compilación LaTeX | `-no-shell-escape` al compilar documentos (`salidas/compilador.py` L425 y L566). La precompilación del formato (L88) no lo pasa explícitamente, pero solo procesa contenido interno (`pcformato.tex` y la `.sty`) y depende del valor por defecto de la distribución | Bajo |
| Importación de zips | Se impide el *path traversal* (prueba `test_zip_malicioso_no_sale_de_su_carpeta`) | Bajo |
| Explorador de carpetas | Limitado a `--raices` (prueba `test_explorar_solo_dentro_de_las_raices`) | Bajo |
| Rutas y colores en el modelo | Se neutralizan antes de generar LaTeX (prueba `test_rutas_y_colores_peligrosos_se_neutralizan`) | Bajo |
| Búsqueda por DOI | Petición saliente a doi.org (solo el DOI); respuesta limitada a 2 MB | Bajo |
| Tráfico en la red | Por defecto solo `127.0.0.1` (no sale del equipo). Con `--host 0.0.0.0` el tráfico va sin cifrar salvo que se use `--certificado` y `--clave` (HTTPS, TLS 1.2 o posterior); la terminal avisa si no | Bajo en local; medio en red sin HTTPS |
| Pérdida de datos | Copias automáticas (zip) cada 24 h en `DOCSLAB_COPIAS_DIR`; se guardan 7 | Bajo si la carpeta está en otro disco |
| Mensajes de error | 500 y fallos inesperados de los trabajos sin detalles internos (la traza va solo a la terminal) | Bajo |

## Lista de comprobación (2026-11-19)

| Punto | Estado en DocsLab |
|---|---|
| 1. HTTPS en todas las páginas | Local: no hace falta (127.0.0.1 no sale del equipo). En red: `--certificado`/`--clave`; aviso si falta. En Colab, HTTPS por el proxy de Google |
| 2. Ninguna clave escondida en el código | Sí: `tests/test_higiene.py` busca claves y archivos de secretos en todo el repositorio |
| 3. Contraseña larga y doble factor en el panel | No aplica: DocsLab no tiene panel ni cuentas. Sí aplica a tu cuenta de GitHub y al correo de seguridad: actívalo ahí |
| 4. Copia de seguridad automática | Sí: `docslab/nucleo/copias.py` (cada 24 h, 7 copias) |
| 5. Todo actualizado | Sí a 2026-11-19: `herramientas/revisar_dependencias.py` (pip-audit y JS incluido frente a npm) |
| 6. Formulario protegido contra bots | No aplica: no hay formularios públicos. Las peticiones de otras webs se rechazan (cabecera `X-DocsLab` y `Origin`) |
| 7. Límite de intentos al iniciar sesión | No aplica: no hay inicio de sesión (uso local de una persona) |
| 8. Que cada usuario solo vea sus datos | No aplica (un solo usuario). Cada proyecto queda dentro de su carpeta: rutas comprobadas y pruebas de «zip slip» y de `--raices` |
| 9. Errores que no enseñen nada interno | Sí: 404/405/500 en JSON genérico y fallos inesperados de los trabajos sin traza (va a la terminal) |
| 10. Borrar lo que no uses | Sí: código sin usar eliminado en 1.8.0; `tests/test_higiene.py` comprueba con pyflakes que no vuelva |

## Recomendaciones de uso
- No uses `--host 0.0.0.0` fuera de una red de confianza. Si lo usas, sírvelo por HTTPS (`--certificado` y `--clave`, por ejemplo con mkcert). Si entras por un nombre (no por la IP), añádelo a `DOCSLAB_HOSTS`.
- Pon las copias de seguridad (`DOCSLAB_COPIAS_DIR`) en otro disco o en una carpeta sincronizada.
- Activa el doble factor en la cuenta de GitHub donde publiques DocsLab y en el correo de seguridad.
- Abre DocsLab siempre por `http://127.0.0.1:<puerto>/` o `http://localhost:<puerto>/`.
- Si usas la API desde tus propios scripts, las peticiones POST, PUT, PATCH y DELETE deben llevar la cabecera `X-DocsLab: 1`.
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

