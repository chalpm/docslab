# Política de versionado y publicación

## 1. Estándares adoptados

| Aspecto | Estándar |
|---|---|
| Números de versión | [Semantic Versioning 2.0.0](https://semver.org/lang/es/) |
| Registro de cambios | [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/) → `CHANGELOG.md` |
| Mensajes de commit | [Conventional Commits 1.0.0](https://www.conventionalcommits.org/es/v1.0.0/) |
| Etiquetas de git | `vMAJOR.MINOR.PATCH` anotadas (`git tag -a v1.1.0 -m "..."`) |
| Ramas | `main` siempre publicable; trabajo en `feat/…`, `fix/…`, `docs/…` |
| Prerreleases | `1.1.0-rc.1`, `1.1.0-beta.2` (SemVer §9) |

## 2. Ejes versionados

DocsLab tiene cuatro contratos que evolucionan a ritmos distintos. Cada uno lleva su propio número.

| Eje | Dónde vive | Tipo | Quién depende de él |
|---|---|---|---|
| **Aplicación** | `docslab/__init__.py` → `__version__` | SemVer | Usuarios, `/api/estado`, empaquetado |
| **Plantilla LaTeX** | `latex/postercientifico.sty` → `\ProvidesPackage[… vX.Y.Z …]` y `docslab.__version_sty__` | SemVer | `.tex` de usuarios, Overleaf, proyectos en modo LaTeX |
| **Esquema del modelo** | `docslab/modelo.py` → `ESQUEMA` (clave `version_esquema` en `modelo.json`) | Entero creciente | `modelo.json` de proyectos y plantillas |
| **Exportación de componentes** | `docslab/componentes.py` → `"version": 1` | Entero creciente | `.json` de componentes exportados |

Cuando cambia la plantilla `.sty` o el esquema, también cambia la aplicación, como mínimo en MINOR.

## 3. Qué incrementar

### Aplicación
| Cambio | Salto |
|---|---|
| Se elimina o renombra una ruta de la API, una variante, un estilo, una clase o una plantilla incluida | **MAJOR** |
| Un proyecto guardado deja de abrirse o cambia su resultado sin migración | **MAJOR** |
| Sube `ESQUEMA` sin migración automática | **MAJOR** |
| Se añade una ruta, variante, estilo, idioma, tipografía, plantilla o función de usuario | **MINOR** |
| Sube `ESQUEMA` con migración automática y probada | **MINOR** |
| Nueva dependencia obligatoria en `requirements.txt` | **MINOR** (se anota en el CHANGELOG) |
| Cambio de licencia de la aplicación o de un componente | **MINOR** (del componente y de la aplicación) |
| Corrección de errores sin cambio de contrato, rendimiento, textos o documentación | **PATCH** |

### Plantilla `postercientifico.sty`
- **MAJOR**: se elimina o renombra una clave de `\posterconfig`, un entorno o una orden pública, o el resultado visual de un `.tex` existente cambia de forma incompatible.
- **MINOR**: nuevas claves, entornos u opciones con valores por defecto que no alteran lo existente.
- **PATCH**: correcciones.
- Licencia propia: **LPPL-1.3c** (no la AGPL de la aplicación). Su cabecera de copyright y mantenimiento no se elimina; las copias en `plantillas/*-latex/` deben ser idénticas (`tests/test_version.py`).

### Esquema del modelo
- Sube en 1 cada vez que cambia la forma de `modelo.json` de un modo que `normalizar()` no resuelve completando valores por defecto (renombrar, mover o cambiar el tipo de un campo).
- Cada subida debe venir con una función de migración `N-1 → N` en `docslab/migraciones.py` y un fixture del esquema de origen. El procedimiento está en [`MIGRACIONES.md`](MIGRACIONES.md).

## 4. Huella digital

`herramientas/huella.py` produce `huella/vX.Y.Z.json` con:

- los números de versión de los cuatro ejes y las licencias (aplicación y `.sty`);
- el **contrato público**: las rutas de la API, las 69 variantes, los estilos de caja y bibliográficos, las clases, los tamaños, los temas, los idiomas, las familias tipográficas y las plantillas incluidas;
- las dependencias, el número de funciones de prueba por archivo y las líneas de código por módulo;
- el SHA-256 y el tamaño de cada archivo, más un `sha256_global` del árbol.

Quedan fuera `.git/`, `datos/`, `.venv/`, `__pycache__/`, `dist/` y la propia carpeta `huella/`.

```bash
python herramientas/huella.py generar                               # huella/v<versión>.json
python herramientas/huella.py verificar huella/v1.0.0.json          # ¿el árbol coincide?
python herramientas/huella.py comparar huella/v1.0.0.json huella/v1.1.0.json
```

`comparar` lista los cambios por eje y sugiere el salto: **MAJOR** si se quitó algo del contrato o cambió el esquema, **MINOR** si se añadió algo y **PATCH** si solo cambiaron archivos. Es orientativo: los cambios de comportamiento hay que juzgarlos a mano.

## 5. Lista de comprobación para publicar

1. Las entradas de `## [Sin publicar]` en `CHANGELOG.md` están completas.
2. Decide el salto con `huella.py comparar` contra la huella anterior, junto con tu revisión.
3. Actualiza `__version__` (y, si cambian, `__version_sty__` con `\ProvidesPackage` o `ESQUEMA`).
4. En `CHANGELOG.md`, mueve `[Sin publicar]` a `## [X.Y.Z] - AAAA-MM-DD` y añade el enlace al pie.
5. `python herramientas/doc_api.py`, para regenerar `docs/API.md`.
6. `python -m pytest`: todas las pruebas en verde, en un entorno con TeX Live completo. En Debian/Ubuntu, como mínimo: `texlive-latex-extra`, `texlive-lang-spanish`, `texlive-luatex` (incluye `luatex85.sty`), Poppler y Ghostscript.
7. `python herramientas/huella.py generar`.
8. `git commit -m "chore(release): vX.Y.Z"` y `git tag -a vX.Y.Z -m "DocsLab X.Y.Z"`.
9. `python herramientas/empaquetar.py` si se distribuye un zip; anota su SHA-256 en las notas de la versión.
10. En `SECURITY.md`, actualiza la tabla de soporte: la nueva MINOR pasa a tener soporte y la anterior deja de tenerlo.

## 6. Commits

```
<tipo>(<ámbito opcional>): <resumen en imperativo>

<cuerpo opcional>

BREAKING CHANGE: <descripción>   ← obliga a subir MAJOR
```

Tipos: `feat` (MINOR), `fix` (PATCH), `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
Ámbitos sugeridos: `api`, `editor`, `sty`, `modelo`, `bibliografia`, `lab`, `cuadernos`, `revision`, `imprenta`, `pptx`, `fuentes`, `plantillas`.
