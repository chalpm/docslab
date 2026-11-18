# SPDX-License-Identifier: AGPL-3.0-only
"""Genera los datos de ejemplo de las plantillas de gráficos (docslab/datos_ejemplo/).

Uso (desde la raíz del proyecto):
    python herramientas/datos_ejemplo.py ne_110m_admin_0_countries.geojson

El argumento es el GeoJSON de países 1:110m de Natural Earth (dominio público):
https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson

Todo lo demás es sintético y reproducible (semilla fija), salvo la población y el PIB
de ejemplo_paises.csv, que son las estimaciones que publica Natural Earth. Los datos
científicos (multivariado, expresión, GWAS, supervivencia…) son simulados: sirven para
probar las plantillas y no describen ningún experimento real.
ejemplo.csv no se toca: es el de siempre.
"""
from __future__ import annotations

import csv
import json
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "docslab" / "lab" / "graficos" / "datos_ejemplo"
SEMILLA = 2026

CONTINENTES = {"Africa": "África", "Asia": "Asia", "Europe": "Europa", "North America": "América del Norte",
               "South America": "América del Sur", "Oceania": "Oceanía", "Antarctica": "Antártida",
               "Seven seas (open ocean)": "Océanos"}

# Coordenadas aproximadas (grados) de ciudades conocidas, para puntos y conexiones
CIUDADES = {
    "Ciudad de México": (19.43, -99.13), "Nueva York": (40.71, -74.01), "Bogotá": (4.71, -74.07),
    "Buenos Aires": (-34.60, -58.38), "São Paulo": (-23.55, -46.63), "Madrid": (40.42, -3.70),
    "Londres": (51.51, -0.13), "París": (48.86, 2.35), "El Cairo": (30.04, 31.24),
    "Nairobi": (-1.29, 36.82), "Ciudad del Cabo": (-33.92, 18.42), "Moscú": (55.76, 37.62),
    "Bombay": (19.08, 72.88), "Pekín": (39.90, 116.41), "Tokio": (35.68, 139.69), "Sídney": (-33.87, 151.21),
}


def _csv(nombre: str, cabecera: list[str], filas: list[list]):
    with (DESTINO / nombre).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cabecera)
        w.writerows(filas)
    print(f"{nombre}: {len(filas)} filas")


def _redondear(coords, n=2):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], n), round(coords[1], n)]
    return [_redondear(c, n) for c in coords]


def _area_centroide(anillo):
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(anillo, anillo[1:] + anillo[:1]):
        k = x0 * y1 - x1 * y0
        a += k
        cx += (x0 + x1) * k
        cy += (y0 + y1) * k
    a /= 2
    return (abs(a), (cx / (6 * a), cy / (6 * a))) if a else (0.0, tuple(anillo[0]))


def _centro(geom):
    """Centroide del polígono más grande del país (evita que caiga en el mar)."""
    poligonos = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return max((_area_centroide(p[0]) for p in poligonos), key=lambda t: t[0])[1]


def mundo(origen: Path):
    g = json.loads(origen.read_text(encoding="utf-8"))
    rasgos, paises = [], []
    for f in g["features"]:
        p = f["properties"]
        iso = p["ADM0_A3"]
        nombre = p.get("NAME_ES") or p["NAME"]
        cont = CONTINENTES.get(p["CONTINENT"], p["CONTINENT"])
        geom = {"type": f["geometry"]["type"], "coordinates": _redondear(f["geometry"]["coordinates"])}
        rasgos.append({"type": "Feature", "properties": {"iso3": iso, "nombre": nombre, "continente": cont},
                       "geometry": geom})
        if cont in ("Antártida", "Océanos") or not p.get("POP_EST"):
            continue
        lon, lat = _centro(f["geometry"])
        pib = p.get("GDP_MD") or 0
        paises.append([iso, nombre, cont, int(p["POP_EST"]), int(pib),
                       round(pib * 1e6 / p["POP_EST"]) if pib else "", round(lat, 2), round(lon, 2)])
    salida = {"type": "FeatureCollection",
              "fuente": "Natural Earth 1:110m Admin 0 – Countries (dominio público), coordenadas a 2 decimales",
              "features": rasgos}
    (DESTINO / "mundo.geojson").write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")),
                                           encoding="utf-8")
    print(f"mundo.geojson: {len(rasgos)} países")
    paises.sort(key=lambda r: r[1])
    _csv("ejemplo_paises.csv", ["iso3", "pais", "continente", "poblacion", "pib_musd", "pib_per_capita", "lat", "lon"],
         paises)


def series(r: random.Random):
    nombres = ["Norte", "Sur", "Este", "Oeste", "Centro"]
    base = {"Norte": 40, "Sur": 25, "Este": 30, "Oeste": 18, "Centro": 12}
    filas, inicio = [], date(2024, 1, 1)
    for semana in range(104):
        dia = inicio + timedelta(weeks=semana)
        for i, n in enumerate(nombres):
            v = base[n] * (1 + 0.004 * semana) + 8 * math.sin(2 * math.pi * (semana / 52 + i / 5)) + r.gauss(0, 2.5)
            filas.append([dia.isoformat(), n, round(max(v, 0.5), 2)])
    _csv("ejemplo_series.csv", ["fecha", "serie", "valor"], filas)


def red(r: random.Random):
    grupos = {"A": 7, "B": 6, "C": 6, "D": 5, "E": 6}
    nodos = [(f"{g}{i}", g) for g, n in grupos.items() for i in range(1, n + 1)]
    grupo = dict(nodos)
    aristas = set()
    for a, ga in nodos:                       # enlaces dentro del grupo (densos) y entre grupos (pocos)
        for b, gb in nodos:
            if a < b and r.random() < (0.45 if ga == gb else 0.035):
                aristas.add((a, b))
    filas = [[a, b, r.randint(1, 20), grupo[a], grupo[b]] for a, b in sorted(aristas)]
    _csv("ejemplo_red.csv", ["origen", "destino", "valor", "grupo_origen", "grupo_destino"], filas)


def flujos():
    # Sintético: fuentes → transformación → uso final (unidades arbitrarias; se conservan los totales)
    etapa1 = [("Solar", "Electricidad", 12), ("Eólica", "Electricidad", 15), ("Hidráulica", "Electricidad", 10),
              ("Gas", "Electricidad", 22), ("Gas", "Calor", 18), ("Carbón", "Electricidad", 14),
              ("Carbón", "Calor", 6), ("Petróleo", "Combustibles", 40), ("Biomasa", "Calor", 8),
              ("Biomasa", "Combustibles", 5)]
    etapa2 = [("Electricidad", "Hogares", 25), ("Electricidad", "Industria", 30), ("Electricidad", "Servicios", 18),
              ("Calor", "Hogares", 17), ("Calor", "Industria", 15), ("Combustibles", "Transporte", 38),
              ("Combustibles", "Industria", 7)]
    _csv("ejemplo_flujos.csv", ["origen", "destino", "valor"], [list(f) for f in etapa1 + etapa2])


def jerarquia(r: random.Random):
    areas = {"Biología": ["Ecología", "Genética", "Microbiología", "Botánica", "Zoología"],
             "Química": ["Orgánica", "Analítica", "Bioquímica", "Fisicoquímica"],
             "Física": ["Óptica", "Materia condensada", "Astrofísica", "Partículas"],
             "Medicina": ["Cardiología", "Oncología", "Neurología", "Pediatría", "Epidemiología", "Inmunología"],
             "Matemáticas": ["Álgebra", "Análisis", "Estadística"]}
    filas = [[a, s, r.randint(15, 160)] for a, subs in areas.items() for s in subs]
    _csv("ejemplo_jerarquia.csv", ["area", "subarea", "publicaciones"], filas)


def puntuaciones(r: random.Random):
    vars_ = ["Proteína", "Lípidos", "Carbohidratos", "Fibra", "Humedad", "Cenizas"]
    perfiles = {"Cereal": [11, 3, 70, 9, 12, 1.6], "Legumbre": [23, 2, 55, 15, 10, 3.5],
                "Semilla": [20, 45, 20, 8, 5, 3.0]}
    filas, n = [], 1
    for g, base in perfiles.items():
        for _ in range(4):
            filas.append([f"M{n:02d}", g] + [round(max(0.1, b * r.uniform(0.75, 1.25)), 1) for b in base])
            n += 1
    _csv("ejemplo_puntuaciones.csv", ["muestra", "grupo"] + vars_, filas)


def palabras(r: random.Random):
    lista = ("datos análisis modelo muestra hipótesis resultado método variable experimento medición error "
             "distribución media varianza correlación regresión gráfico tabla figura población estudio "
             "evidencia teoría observación simulación algoritmo red señal proteína gen célula especie "
             "clima energía temperatura presión tiempo frecuencia espectro molécula reacción enzima "
             "bacteria ecosistema suelo agua carbono nitrógeno sensor imagen protocolo revisión "
             "replicación incertidumbre precisión sesgo validación").split()
    filas = [[p, max(3, round(400 / (i + 1) ** 0.8 * r.uniform(0.85, 1.15)))] for i, p in enumerate(lista)]
    _csv("ejemplo_palabras.csv", ["palabra", "frecuencia"], filas)


def puntos(r: random.Random):
    filas = []
    for ciudad, (lat, lon) in CIUDADES.items():
        for _ in range(r.randint(25, 70)):
            filas.append([round(lat + r.gauss(0, 3), 3), round(lon + r.gauss(0, 4), 3), ciudad])
    _csv("ejemplo_puntos.csv", ["lat", "lon", "ciudad"], filas)


def conexiones(r: random.Random):
    centro = "Ciudad de México"
    filas = []
    for destino, (lat, lon) in CIUDADES.items():
        if destino != centro:
            la, lo = CIUDADES[centro]
            filas.append([centro, destino, la, lo, lat, lon, r.randint(5, 60)])
    for a, b in [("Madrid", "Buenos Aires"), ("Londres", "Nueva York"), ("Tokio", "Sídney"), ("París", "El Cairo")]:
        filas.append([a, b, *CIUDADES[a], *CIUDADES[b], r.randint(5, 60)])
    _csv("ejemplo_conexiones.csv", ["origen", "destino", "lat_origen", "lon_origen", "lat_destino", "lon_destino",
                                    "valor"], filas)


# ----------------------------------------------------------------- datos científicos (1.4.0)
# Cada generador usa su propia semilla, para que añadir uno no cambie los demás.
def multivariado():
    import numpy as np
    g = np.random.default_rng(SEMILLA + 1)
    grupos = {"Control": (0, 0, 0), "Tratamiento A": (3, 0.5, 0), "Tratamiento B": (2.5, 3, 0.5),
              "Tratamiento C": (-0.5, 2.5, 3)}
    carga = g.normal(0, 1, (3, 12))                 # 12 variables que dependen de 3 factores latentes
    filas, n = [], 1
    for nombre, centro in grupos.items():
        z = g.normal(centro, 0.8, (50, 3))
        x = np.exp(1.5 + 0.35 * (z @ carga) / 2 + g.normal(0, 0.15, (50, 12)))   # niveles positivos
        for fila in x:
            filas.append([f"S{n:03d}", nombre] + [round(float(v), 3) for v in fila])
            n += 1
    _csv("ejemplo_multivariado.csv", ["muestra", "grupo"] + [f"gen{i:02d}" for i in range(1, 13)], filas)


def expresion():
    import numpy as np
    g = np.random.default_rng(SEMILLA + 2)
    n = 3000
    efecto = np.where(g.random(n) < 0.08, g.normal(0, 2.2, n), g.normal(0, 0.25, n))
    se = g.uniform(0.35, 1.1, n)
    z = efecto / se
    from math import erfc, sqrt
    p = np.array([erfc(abs(v) / sqrt(2)) for v in z])
    orden = np.argsort(p)                            # Benjamini-Hochberg
    padj = np.empty(n)
    padj[orden] = np.minimum.accumulate((p[orden] * n / np.arange(1, n + 1))[::-1])[::-1]
    media = g.lognormal(5, 1.5, n)
    filas = [[f"GEN{i:04d}", round(float(efecto[i]), 4), float(f"{p[i]:.4g}"), float(f"{min(padj[i], 1):.4g}"),
              round(float(media[i]), 1)] for i in range(n)]
    _csv("ejemplo_expresion.csv", ["gen", "log2fc", "pvalor", "padj", "media"], filas)


def gwas():
    import numpy as np
    g = np.random.default_rng(SEMILLA + 3)
    largos = [249, 243, 198, 191, 182, 171, 159, 146, 141, 136, 135, 133, 115, 107, 102, 90, 83, 80, 59, 64, 47, 51]
    filas, k = [], 1
    for c, largo in enumerate(largos, start=1):
        m = int(largo * 2.5)
        pos = np.sort(g.integers(1, largo * 1_000_000, m))
        p = g.uniform(0, 1, m)
        if c in (2, 6, 11, 17):                       # cuatro señales «significativas»
            centro = pos[m // 2]
            cerca = np.abs(pos - centro) < 4_000_000
            p[cerca] = p[cerca] ** (1 + g.uniform(12, 25) * np.exp(-np.abs(pos[cerca] - centro) / 1.2e6))
        for x, v in zip(pos, p):
            filas.append([f"rs{k}", c, int(x), float(f"{max(v, 1e-300):.3g}")])
            k += 1
    _csv("ejemplo_gwas.csv", ["snp", "cromosoma", "posicion", "pvalor"], filas)


def supervivencia():
    import numpy as np
    g = np.random.default_rng(SEMILLA + 4)
    filas = []
    for grupo, mediana in [("Tratamiento", 36), ("Control", 15)]:
        t = g.exponential(mediana / np.log(2), 120)
        c = g.uniform(6, 60, 120)                      # censura por fin del seguimiento
        for i, (ti, ci) in enumerate(zip(t, c)):
            filas.append([f"{grupo[0]}{i + 1:03d}", grupo, round(float(min(ti, ci)), 1), int(ti <= ci)])
    _csv("ejemplo_supervivencia.csv", ["paciente", "grupo", "tiempo_meses", "evento"], filas)


def dosis():
    import numpy as np
    g = np.random.default_rng(SEMILLA + 5)
    dosis_ = [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100]
    filas = []
    for compuesto, ec50, hill in [("Compuesto 1", 0.8, 1.2), ("Compuesto 2", 6.0, 1.0), ("Compuesto 3", 25.0, 2.0)]:
        for d in dosis_:
            for r in range(3):
                y = 100 / (1 + (d / ec50) ** hill)
                filas.append([compuesto, d, r + 1, round(float(y + g.normal(0, 4)), 2)])
    _csv("ejemplo_dosis.csv", ["compuesto", "dosis_um", "replica", "viabilidad"], filas)


def clasificacion():
    import numpy as np
    g = np.random.default_rng(SEMILLA + 6)
    n = 400
    real = (g.random(n) < 0.4).astype(int)
    a = 1 / (1 + np.exp(-(real * 2.2 - 1.1 + g.normal(0, 1.0, n))))
    b = 1 / (1 + np.exp(-(real * 1.2 - 0.6 + g.normal(0, 1.0, n))))
    clases = ["Sano", "Leve", "Grave"]
    verdad = g.choice(3, n, p=[0.5, 0.3, 0.2])
    pred = np.where(g.random(n) < 0.78, verdad, g.integers(0, 3, n))
    filas = [[int(real[i]), round(float(a[i]), 4), round(float(b[i]), 4), clases[verdad[i]], clases[pred[i]]]
             for i in range(n)]
    _csv("ejemplo_clasificacion.csv", ["real", "modelo_a", "modelo_b", "clase_real", "clase_predicha"], filas)


def metodos():
    import numpy as np
    g = np.random.default_rng(SEMILLA + 7)
    verdad = g.uniform(40, 200, 60)
    a = verdad + g.normal(0, 6, 60)
    b = verdad * 1.03 + 2 + g.normal(0, 7, 60)
    _csv("ejemplo_metodos.csv", ["muestra", "metodo_a", "metodo_b"],
         [[f"M{i + 1:02d}", round(float(x), 1), round(float(y), 1)] for i, (x, y) in enumerate(zip(a, b))])


def metaanalisis():
    import numpy as np
    g = np.random.default_rng(SEMILLA + 8)
    filas = []
    for i, (n, nombre) in enumerate(zip([120, 340, 85, 410, 220, 150, 600, 95, 270, 180],
                                        ["Estudio A", "Estudio B", "Estudio C", "Estudio D", "Estudio E",
                                         "Estudio F", "Estudio G", "Estudio H", "Estudio I", "Estudio J"])):
        se = 2.4 / np.sqrt(n)
        log_or = g.normal(-0.3, 0.12) + g.normal(0, se)
        filas.append([nombre, 2015 + i, n, round(float(np.exp(log_or)), 3), round(float(np.exp(log_or - 1.96 * se)), 3),
                      round(float(np.exp(log_or + 1.96 * se)), 3)])
    _csv("ejemplo_metaanalisis.csv", ["estudio", "anio", "n", "or", "li", "ls"], filas)


def espectro():
    import numpy as np
    g = np.random.default_rng(SEMILLA + 9)
    x = np.linspace(400, 700, 1501)
    y = 0.05 + 0.0002 * (x - 400)
    for centro, alto, ancho in [(432, 0.9, 6), (468, 0.45, 9), (512, 1.0, 5), (557, 0.3, 12), (604, 0.7, 7),
                                (655, 0.55, 8)]:
        y = y + alto * np.exp(-0.5 * ((x - centro) / ancho) ** 2)
    y = y + g.normal(0, 0.012, x.size)
    _csv("ejemplo_espectro.csv", ["longitud_onda_nm", "intensidad"],
         [[round(float(a), 2), round(float(b), 4)] for a, b in zip(x, y)])


def superficie():
    import numpy as np
    xs = np.linspace(-3, 3, 41)
    filas = []
    for x in xs:
        for y in xs:
            z = 3 * (1 - x) ** 2 * np.exp(-x**2 - (y + 1) ** 2) - 10 * (x / 5 - x**3 - y**5) * np.exp(-x**2 - y**2) \
                - np.exp(-(x + 1) ** 2 - y**2) / 3
            filas.append([round(float(x), 2), round(float(y), 2), round(float(z), 4)])
    _csv("ejemplo_superficie.csv", ["x", "y", "z"], filas)


def conjuntos():
    import numpy as np
    g = np.random.default_rng(SEMILLA + 10)
    genes = [f"GEN{i:04d}" for i in range(1, 401)]
    filas = []
    for nombre, prob in [("Tejido A", 0.45), ("Tejido B", 0.35), ("Tejido C", 0.3)]:
        for gen in genes:
            if g.random() < prob:
                filas.append([gen, nombre])
    _csv("ejemplo_conjuntos.csv", ["elemento", "conjunto"], filas)


CIENTIFICOS = [multivariado, expresion, gwas, supervivencia, dosis, clasificacion, metodos, metaanalisis, espectro,
               superficie, conjuntos]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__)
    DESTINO.mkdir(parents=True, exist_ok=True)
    r = random.Random(SEMILLA)
    mundo(Path(argv[0]))
    series(r)
    red(r)
    flujos()
    jerarquia(r)
    puntuaciones(r)
    palabras(r)
    puntos(r)
    conexiones(r)
    for f in CIENTIFICOS:
        f()


if __name__ == "__main__":
    main()
