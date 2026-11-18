#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Miniaturas de las plantillas de gráficos incluidas (static/img/graficos/<id>.png).

Cada una se dibuja con los datos de ejemplo y los valores iniciales de la plantilla.
Hace falta matplotlib, seaborn, pandas, plotly y kaleido (este último, con Chrome).
"""
from __future__ import annotations

import base64
import io
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from PIL import Image  # noqa: E402

from docslab import graficos as G  # noqa: E402

DESTINO = RAIZ / "static" / "img" / "graficos"
COLORES = {"primario": "2F4858", "acento": "C8553D"}


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    for t in G.INCLUIDAS:
        r = G.probar(G.generar(t, {}, COLORES))
        if not r["ok"]:
            raise SystemExit(f"{t['id']}: {r['error']}")
        if r.get("imagen"):
            png = base64.b64decode(r["imagen"].split(",", 1)[1])
        else:
            import plotly.io as pio
            png = pio.from_json(json.dumps(r["plotly"])).to_image(format="png", width=560, height=373, scale=1)
        im = Image.open(io.BytesIO(png)).convert("RGB")
        im.thumbnail((480, 360))
        im.save(DESTINO / f"{t['id']}.png", optimize=True)
        print(t["id"], im.size)


if __name__ == "__main__":
    main()
