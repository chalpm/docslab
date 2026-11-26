# SPDX-License-Identifier: AGPL-3.0-only
"""Crea las etiquetas y Releases de DocsLab que falten, a partir del historial.

Regla: la versión X.Y.Z se publica en el último commit que tocó `huella/vX.Y.Z.json`
(la huella es lo último que se genera al publicar), siempre que en ese commit
`__version__` sea X.Y.Z y el CHANGELOG tenga la entrada `## [X.Y.Z]`.

Nunca mueve ni borra una etiqueta o Release existente. Se puede ejecutar cuantas veces
haga falta: solo crea lo que falta.

    python .github/scripts/etiquetar.py --simular     # dice qué haría, sin tocar nada
    python .github/scripts/etiquetar.py               # crea etiquetas (git push) y Releases (gh)
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RE_HUELLA = re.compile(r"^huella/v(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)\.json$")


def git(*a, ok=True):
    r = subprocess.run(["git", *a], capture_output=True, text=True)
    if ok and r.returncode:
        sys.exit(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout.strip()


def clave(v):
    base, _, pre = v.partition("-")
    return tuple(int(x) for x in base.split(".")) + ((0, pre) if pre else (1, ""))


def notas(changelog, v, etiqueta, repo):
    m = re.search(rf"^## \[{re.escape(v)}\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]: |\Z)", changelog, re.M | re.S)
    if not m:
        return None
    texto = m.group(1).strip()
    if repo:   # enlaces relativos del CHANGELOG → archivos de esa etiqueta
        texto = re.sub(r"\]\((?!https?://|#|\.\./)([^)]+)\)",
                       lambda x: f"](https://github.com/{repo}/blob/{etiqueta}/{x.group(1)})", texto)
    return texto + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simular", action="store_true")
    a = ap.parse_args()
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    versiones = sorted((m.group(1) for f in git("ls-files", "huella").splitlines() if (m := RE_HUELLA.match(f))),
                       key=clave)
    if not versiones:
        print("No hay huellas: nada que publicar.")
        return
    remotas = set()
    if not a.simular:
        git("fetch", "--tags", "--force", "origin", ok=False)
    for linea in git("tag", "--list", "v*").splitlines():
        remotas.add(linea)
    ultima = max((v for v in versiones if "-" not in v), key=clave, default=None)
    hay_gh = not a.simular and subprocess.run(["gh", "--version"], capture_output=True).returncode == 0
    for v in versiones:
        t = f"v{v}"
        commit = git("log", "-1", "--format=%H", "HEAD", "--", f"huella/{t}.json")
        vc = re.search(r'__version__\s*=\s*"([^"]+)"', git("show", f"{commit}:docslab/__init__.py", ok=False) or "")
        if not vc or vc.group(1) != v:
            print(f"{t}: se salta (en {commit[:7]} __version__ no es {v})")
            continue
        cuerpo = notas(changelog, v, t, repo)
        if cuerpo is None:
            print(f"{t}: se salta (el CHANGELOG no tiene «## [{v}]»)")
            continue
        if t in remotas:
            apunta = git("rev-parse", f"{t}^{{commit}}")
            if apunta != commit:
                print(f"{t}: AVISO, la etiqueta existe en {apunta[:7]} y no en {commit[:7]}; no se mueve")
            else:
                print(f"{t}: la etiqueta ya existe en {commit[:7]}")
        elif a.simular:
            print(f"{t}: crearía la etiqueta en {commit[:7]}")
        else:
            git("tag", "-a", t, commit, "-m", f"DocsLab {v}")
            git("push", "origin", f"refs/tags/{t}")
            print(f"{t}: etiqueta creada en {commit[:7]}")
        if a.simular or not hay_gh:
            if a.simular:
                print(f"     y su Release «DocsLab {v}»" + (" (latest)" if v == ultima else ""))
            continue
        if subprocess.run(["gh", "release", "view", t], capture_output=True).returncode == 0:
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(cuerpo)
        orden = ["gh", "release", "create", t, "--verify-tag", "--title", f"DocsLab {v}", "--notes-file", f.name]
        orden += ["--prerelease"] if "-" in v else (["--latest"] if v == ultima else ["--latest=false"])
        r = subprocess.run(orden, capture_output=True, text=True)
        print(f"{t}: Release {'creada' if r.returncode == 0 else 'NO creada: ' + r.stderr.strip()}")


if __name__ == "__main__":
    main()
