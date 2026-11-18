# Migraciones del esquema del modelo

## Qué problema resuelven

Cada proyecto estructurado se guarda en `modelo.json`. Su forma es el **esquema**, identificado por la clave `version_esquema` (un entero; el actual está en `docslab/modelo.py → ESQUEMA`).

Si una versión futura cambia esa forma, por ejemplo renombrando o moviendo un campo, los proyectos guardados antes conservan la forma vieja. `modelo.normalizar()` solo **completa** los campos que faltan: no sabe que `tam_logo_izquierdo` ahora vive en `logos.izquierdo.tam`, así que el valor del usuario se perdería sin aviso.

Una **migración** es una función que transforma un modelo del esquema N al N+1. Al abrir un proyecto se aplican en cadena hasta el esquema actual.

```
modelo.json (esquema 1) ──1→2──► esquema 2 ──2→3──► esquema 3 (actual) ──► normalizar() ──► editor
```

## Cómo funciona

| Pieza | Dónde |
|---|---|
| Registro de migraciones y motor (`migrar`, `version_de`, `@migracion`) | `docslab/migraciones.py` |
| Punto único de entrada: `modelo.normalizar()` llama a `migrar()` antes de completar los valores por defecto | `docslab/modelo.py` |
| Copia de seguridad al abrir un proyecto que necesita migrar: `historial/modelo-antes-de-esquema-<N>.json` (una vez por esquema) | `almacen.leer_modelo()` |
| Errores (`ErrorEsquema`) convertidos en `ErrorAlmacen` → HTTP 400 con un mensaje para el usuario | `docslab/almacen.py` |
| Fixtures de cada esquema anterior | `tests/fixtures/esquemas/v<N>/*.json` |
| Pruebas | `tests/test_migraciones.py` |

Comportamiento:

- **Abrir un proyecto antiguo:** se migra en memoria y se guarda una copia del original en `historial/`. El archivo en disco no cambia hasta que se guarda (al primer cambio).
- **Proyecto de un esquema más nuevo** (creado con un DocsLab posterior): no se abre. Se muestra «Actualiza DocsLab para abrirlo», para no destruir datos que esta versión no entiende.
- **Proyectos heredados** (PosterLab, DocsLab 2.1.0 original, DocsLab 1.0.x) no tienen `version_esquema`; algunos llevan la clave antigua `esquema` con 1 o 2. Todos tienen la estructura del esquema 1: se tratan como versión 1 y se retira la clave antigua.

> **Por qué la clave cambió de `esquema` a `version_esquema` en 1.1.0.** DocsLab 2.1.0 guardaba `"esquema": 2`, y en 1.0.0 la numeración se reinició a 1. Si se hubiera mantenido la clave, el futuro esquema 2 sería indistinguible de los archivos viejos con `"esquema": 2`, y la migración 1→2 se habría saltado en ellos. Con la clave nueva no hay ambigüedad: sin `version_esquema` → heredado → 1.

## Cómo añadir una migración (procedimiento)

1. **Fixture del esquema de origen.** Antes de tocar nada, copia uno o varios `modelo.json` reales del esquema actual N a `tests/fixtures/esquemas/vN/`. Si ya hay, comprueba que cubren los campos que vas a cambiar.
2. **Sube el esquema.** En `docslab/modelo.py`: `ESQUEMA = N + 1`, y ajusta `DEFECTO` a la forma nueva.
3. **Escribe la migración** en `docslab/migraciones.py`:
   ```python
   @migracion(desde=N)
   def _n_a_n1(m: dict) -> dict:
       cab = m.get("cabecera", {})
       if "tam_logo_izquierdo" in cab:
           cab.setdefault("logos", {}).setdefault("izquierdo", {})["tam"] = cab.pop("tam_logo_izquierdo")
       return m
   ```
   Reglas:
   - función **pura** (sin disco, red ni hora), determinista;
   - tolera la ausencia de campos (los modelos viejos pueden estar incompletos);
   - **no pierde datos en silencio**: lo que no tenga destino se guarda en `m.setdefault("_migrado", {})[str(N)]`;
   - no llama a `normalizar()`: eso ocurre después.
4. **Actualiza las plantillas incluidas**: `python herramientas/construir_plantillas.py` (o migra sus `modelo.json`). `tests/test_version.py` exige que estén en el esquema actual.
5. **Pruebas**: añade a `tests/test_migraciones.py` una prueba concreta de la transformación (entrada → salida esperada). Las genéricas ya comprueban que todos los fixtures llegan al esquema actual y generan LaTeX, y que hay una migración por cada salto.
6. **Frontend**: revisa que `static/js` use los campos nuevos.
7. **Versión y registro**: con migración automática el salto de la aplicación es **MINOR**; sin ella, **MAJOR**. Anótalo en `CHANGELOG.md` (Cambiado) y regenera la huella. `huella.py comparar` detecta el cambio de `esquema_modelo`.

## Qué no requiere migración

Añadir un campo nuevo con valor por defecto en `DEFECTO`, o nuevas opciones en listas (`TEMAS`, `IDIOMAS`…): `normalizar()` ya lo completa. Eso no sube `ESQUEMA`.
