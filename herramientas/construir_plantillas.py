#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Construye las plantillas incluidas en DocsLab (carpeta plantillas/).

    python herramientas/construir_plantillas.py [--sin-miniaturas]

Cada plantilla es una carpeta con plantilla.json, modelo.json (o los archivos
LaTeX), recursos/ y, si tiene, cuadernos/. Las miniaturas se generan
compilando cada plantilla una vez.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from docslab.nucleo import almacen as A, modelo as M  # noqa: E402
from docslab.salidas import compilador
from docslab.documento import variantes as V

DESTINO = RAIZ / "plantillas"
FUENTES = RAIZ / "herramientas" / "fuentes"      # imágenes de prueba, figuras y cuadernos
NBSP = " "   # espacio fino (se escribe como \, en LaTeX)

L1 = ("Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Ut purus elit, vestibulum ut, placerat ac, "
      "adipiscing vitae, felis. Curabitur dictum gravida mauris. Nam arcu libero, nonummy eget, consectetuer id, "
      "vulputate a, magna.")
L2 = ("Donec vehicula augue eu neque. Pellentesque habitant morbi tristique senectus et netus et malesuada fames "
      "ac turpis egestas. Mauris ut leo. Cras viverra metus rhoncus sem. Nulla et lectus vestibulum urna fringilla "
      "ultrices.")
L3 = ("Phasellus eu tellus sit amet tortor gravida placerat. Integer sapien est, iaculis in, pretium quis, viverra "
      "ac, nunc. Praesent eget sem vel leo ultrices bibendum. Aenean faucibus. Morbi dolor nulla, malesuada eu, "
      "pulvinar at, mollis ac, nulla.")
L4 = ("Curabitur auctor semper nulla. Donec varius orci eget risus. Duis nibh mi, congue eu, accumsan eleifend, "
      "sagittis quis, diam. Duis eget orci sit amet orci dignissim rutrum.")


# ------------------------------------------------------------------ ayudas
def el(tipo, **campos):
    e = V.elemento_nuevo(tipo, M.nuevo_id("e"))
    e.update(campos)
    return e


def blq(titulo, *elementos, **kw):
    b = copy.deepcopy(M.BLOQUE_DEFECTO)
    b.update({"id": M.nuevo_id("b"), "titulo": titulo, "elementos": list(elementos)})
    opciones = kw.pop("opciones", {})
    b.update(kw)
    b["opciones"] = opciones
    return b


def col(*bloques, abarca=1, dist="repartir"):
    c = copy.deepcopy(M.COLUMNA_DEFECTO)
    c.update({"id": M.nuevo_id("c"), "abarca": abarca, "distribucion": dist, "bloques": list(bloques)})
    return c


def fila(*columnas, alto="auto", rejilla=0):
    f = copy.deepcopy(M.FILA_DEFECTO)
    f.update({"id": M.nuevo_id("f"), "alto": alto, "rejilla": rejilla, "columnas": list(columnas)})
    return f


def base(tema="azul", idioma="es", **kw):
    m = M.normalizar({})
    m["colores"] = dict(tema=tema, **M.TEMAS[tema])
    m["idioma"] = idioma
    for clave, valor in kw.items():
        m[clave].update(valor)
    return m


def escribir(tid, pm, modelo=None, recursos=(), cuadernos=(), archivos=()):
    d = DESTINO / tid
    if d.exists():
        shutil.rmtree(d)
    (d / "recursos").mkdir(parents=True)
    for origen, rel in recursos:
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origen, p)
    for origen, rel in archivos:
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origen, p)
    for c, origen in cuadernos:
        cd = d / "cuadernos" / c["id"]
        cd.mkdir(parents=True, exist_ok=True)
        _cuaderno_sin_salidas(origen, cd / c["archivo"])
    if modelo is not None:
        (d / "modelo.json").write_text(json.dumps(M.normalizar(modelo), ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    pm = dict(pm)
    pm["cuadernos"] = [c for c, _ in cuadernos]
    (d / "plantilla.json").write_text(json.dumps(pm, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def _cuaderno_sin_salidas(origen: Path, destino: Path):
    import nbformat
    nb = nbformat.read(str(origen), as_version=4)
    for c in nb.cells:
        if c.cell_type == "code":
            c.outputs = []
            c.execution_count = None
            c.metadata.pop("execution", None)
    nbformat.write(nb, str(destino))


def cuaderno_meta(id_, archivo, carpeta):
    from docslab.lab.cuadernos import DEFECTO
    c = json.loads(json.dumps(DEFECTO))
    c.update({"id": id_, "nombre": archivo, "archivo": archivo, "origen": "subido", "carpeta_figuras": carpeta})
    return c


# ------------------------------------------------------------------ imágenes de prueba
IMG = FUENTES / "img"
PRUEBA = {n: (IMG / f"{n}.png", f"recursos/{n}.png") for n in
          ("prueba1", "prueba2", "prueba3", "prueba4", "prueba5", "prueba6", "logo1", "logo2", "qr_prueba")}


def r(n):
    return PRUEBA[n][1]


# ================================================================== plantillas
def academico():
    m = base("pizarra")
    m["cabecera"].update({"titulo": "Título del póster científico: lorem ipsum dolor sit amet consectetuer",
                          "subtitulo": "Subtítulo o mensaje principal del trabajo en una sola línea",
                          "autores": "Nombre Apellido^1^, Nombre Apellido^2^, Nombre Apellido^1,2^",
                          "afiliaciones": "^1^Departamento, Institución, Ciudad  ^2^Departamento, Institución, Ciudad",
                          "logo_izquierdo": r("logo1"), "logo_derecho": r("logo2")})
    m["tipografia"].update({"fuente": 30, "escalas": dict(m["tipografia"]["escalas"], titulo=3.1, subtitulo=1.7)})
    m["pie"].update({"izquierda": "Nombre del congreso · Ciudad, año", "centro": "Texto e imágenes de relleno",
                     "derecha": "nombre.apellido@institucion.example"})
    c1 = col(
        blq("Introducción",
            el("txtCapitular", letra="L", resto="orem", texto=" ipsum dolor sit amet, " + L1),
            el("imgEnvueltaDerecha", archivo=r("prueba3"), pie="Imagen envuelta por el texto.", tam=0.44,
               texto=L2 + " " + L3),
            el("txtVinetas", items=["Nulla malesuada porttitor diam.",
                                    "Donec felis erat, congue non, volutpat at, tincidunt tristique, libero.",
                                    "Vivamus viverra fermentum felis."])),
        blq("Objetivos",
            el("txtCitaGrande", cita="Lorem ipsum dolor sit amet, consectetuer adipiscing elit", autor=""),
            el("txtNumerada", items=["Quisque ullamcorper placerat ipsum.", "Cras nibh.",
                                     "Morbi vel justo vitae lacus tincidunt ultrices."])),
        blq("Métodos",
            el("imgTextoDerecha", archivo=r("prueba1"), pie="Montaje experimental.", tam=0.46, texto=L4),
            el("txtPasos", p1="Lorem ipsum dolor sit amet", p2="Consectetuer adipiscing elit",
               p3="Ut purus elit vestibulum"),
            el("txtEcuacion", titulo="", mostrar_titulo=False,
               ecuacion=r"\hat{y} = \operatorname{sign}\Bigl(\sum_{i=1}^{n} w_i x_i + b\Bigr)",
               texto="Donde $w_i$ son los pesos, $x_i$ las variables y $b$ el término independiente."),
            el("imgTres", a=r("prueba6"), b=r("prueba2"), c=r("prueba4"),
               pie="Tres imágenes en fila, recortadas a la misma altura.")))
    c2 = col(
        blq("Resultados",
            el("txtEntradilla", entradilla="Lorem ipsum dolor sit amet, consectetuer adipiscing elit ut purus elit.",
               texto=L2),
            el("imgAncho", archivo=r("prueba2"), pie="Imagen a todo el ancho de la columna, con el pie debajo."),
            el("txtCifras", c1=f"87{NBSP}%", t1="lorem ipsum dolor", c2=f"1{NBSP}234", t2="sit amet consectetuer",
               c3="0.92", t3="adipiscing elit"),
            el("imgRejilla", a=r("prueba1"), b=r("prueba6"), c=r("prueba3"), d=r("prueba4"),
               pie="Rejilla de cuatro paneles: (a) lorem, (b) ipsum, (c) dolor y (d) sit amet."),
            el("txtDosColumnas", texto=L3 + " " + L4),
            el("txtResaltado", titulo="Resultado principal", mostrar_titulo=False,
               texto="**Resultado principal.** Suspendisse vitae elit. Aliquam arcu neque, ornare in, ullamcorper quis, commodo eu, libero.")),
        blq("Trabajo futuro",
            el("txtLineaTiempo", titulo="", mostrar_titulo=False,
               hitos=[["Fase 1", "Curabitur tellus magna, porttitor a, commodo a, commodo in, tortor."],
                      ["Fase 2", "Donec interdum."], ["Fase 3", "Praesent scelerisque."]])))
    c3 = col(
        blq("Resultados (continuación)",
            el("imgGrandeDosDerecha", grande=r("prueba1"), b=r("prueba3"), c=r("prueba6"),
               pie="Una imagen grande y dos pequeñas a la derecha."),
            el("txtTabla", pie="Tabla 1. Valores de relleno para mostrar el formato de la tabla.",
               tabla={"columnas": "lrrr", "encabezado": True,
                      "filas": [["Grupo", "Lorem", "Ipsum", "Dolor"], ["Alfa", "12.4", "0.81", "134"],
                                ["Beta", "9.7", "0.76", "98"], ["Gamma", "15.2", "0.93", "211"],
                                ["Delta", "7.3", "0.64", "57"]]}),
            el("imgAnotada", archivo=r("prueba5"), pie="Imagen panorámica con anotaciones.",
               flechas=[[0.22, 0.80, 0.44, 0.52, "zona A"], [0.82, 0.22, 0.62, 0.46, "zona B"]])),
        blq("Discusión",
            el("imgTextoIzquierda", archivo=r("prueba4"), pie="Imagen a la derecha.", tam=0.4, texto=L1),
            el("txtCitaBarra", titulo="", mostrar_titulo=False, texto="Etiam euismod. Fusce facilisis lacinia dui.")),
        blq("Conclusiones",
            el("txtVinetas", items=["Etiam ac leo a risus tristique nonummy.", "Donec dignissim tincidunt nulla.",
                                    "Vestibulum rhoncus molestie odio."]),
            el("txtInvertido", titulo="", mostrar_titulo=False, texto="**Mensaje para llevar.** Nulla in ipsum.")),
        blq("Referencias",
            el("txtReferencias", items=[
                "Apellido N, Apellido N. Título del artículo de relleno. *Revista*. Año; vol(n): páginas.",
                "Apellido N, Apellido N, Apellido N. Título del artículo de relleno. *Revista*. Año; vol(n): páginas.",
                "Apellido N. *Título del libro de relleno*. Editorial; Año."])),
        blq("Agradecimientos y contacto",
            el("txtContacto", archivo=r("qr_prueba"), tam="6.5em",
               texto="Nulla mattis luctus nulla. Duis commodo velit at leo.\n\n**Contacto:**\nnombre@institucion.example")))
    m["filas"] = [fila(c1, c2, c3, alto="llenar", rejilla=3)]
    escribir("academico-a0", {"nombre": "Académico A0 vertical", "orden": 1,
                              "descripcion": "Tres columnas con texto de relleno e imágenes de prueba: muestra "
                                             "muchas de las variantes de imagen y de texto.",
                              "tipo": "estructurado", "etiquetas": ["A0", "vertical", "3 columnas"]},
             m, recursos=PRUEBA.values())


def horizontal():
    m = base("salvia")
    m["lienzo"].update({"tamano": "48x36in", "orientacion": "horizontal", "ancho": "48in", "alto": "36in",
                        "margen": "1.1in"})
    m["tipografia"].update({"fuente": 30, "interlinea": 1.3,
                            "escalas": dict(m["tipografia"]["escalas"], titulo=2.7, bloque=1.4)})
    m["estilo"].update({"bloque": "linea", "separacion_columnas": "0.9in", "nombre_figura": "Fig."})
    m["cabecera"].update({"estilo": "clara", "titulo": "Título del póster en formato horizontal: lorem ipsum dolor sit amet",
                          "subtitulo": "Subtítulo o mensaje principal del trabajo",
                          "autores": "Nombre Apellido^1^, Nombre Apellido^2^, Nombre Apellido^1^",
                          "afiliaciones": "^1^Departamento, Institución  ^2^Departamento, Institución",
                          "logo_izquierdo": r("logo1"), "logo_derecho": r("logo2"), "ancho_logos": 0.11,
                          "alto_logos": "5em"})
    m["pie"].update({"izquierda": "Nombre del congreso · Ciudad, año", "centro": "Texto e imágenes de relleno",
                     "derecha": "nombre.apellido@institucion.example"})
    c1 = col(
        blq("Introducción",
            el("txtEntradilla", entradilla="Lorem ipsum dolor sit amet, consectetuer adipiscing elit.", texto=L2),
            el("imgTituloSobre", archivo=r("prueba2"), titulo="Lorem ipsum", subtitulo="dolor sit amet"),
            el("txtDefiniciones", pares=[["Lorem", "Nam dui ligula, fringilla a, euismod sodales."],
                                         ["Ipsum", "Morbi auctor lorem non justo."],
                                         ["Dolor", "Nam lacus libero, pretium at, lobortis vitae."]])),
        blq("Objetivo",
            el("txtCajaTitulo", titulo="Pregunta de investigación", mostrar_titulo=True,
               texto="Nulla malesuada porttitor diam. Donec felis erat, congue non, volutpat at, tincidunt tristique, libero."),
            el("txtVinetas", items=["Etiam euismod.", "Fusce facilisis lacinia dui."])),
        blq("Métodos",
            el("imgPieLateral", archivo=r("prueba1"), pie="Pie de figura al lado de la imagen.", tam=0.6),
            el("txtEtiquetaMargen", rotulo="Muestra", texto="Quisque ullamcorper placerat ipsum. Cras nibh."),
            el("txtEtiquetaMargen", rotulo="Análisis", texto="Morbi vel justo vitae lacus tincidunt ultrices.")))
    c2 = col(
        blq("Resultados",
            el("txtCifras", c1=f"87{NBSP}%", t1="lorem ipsum dolor", c2=f"1{NBSP}234", t2="sit amet consectetuer",
               c3="0.92", t3="adipiscing elit"),
            el("imgGrandeTresAbajo", grande=r("prueba5"), a=r("prueba1"), b=r("prueba6"), c=r("prueba3"), tam=30,
               pie="Una imagen principal y tres detalles, a lo ancho de dos columnas."),
            el("txtTresColumnas", texto=L1 + " " + L2)),
        blq("Comparación",
            el("imgComparar", a=r("prueba1"), b=r("prueba4"), ra="Antes", rb="Después", tam=24,
               pie="Comparación de dos imágenes."),
            el("imgMiniatura", archivo=r("prueba3"), titulo="Lorem ipsum", texto="Pellentesque habitant morbi tristique."),
            el("imgMiniatura", archivo=r("prueba2"), titulo="Dolor sit amet", texto="Donec odio elit, dictum in.")),
        abarca=2)
    c3 = col(
        blq("Discusión",
            el("txtCitaGrande", cita="Lorem ipsum dolor sit amet, consectetuer adipiscing elit", autor=""),
            el("txtNotaLateral", nota="Nota breve al margen.", texto=L4),
            el("imgCirculo", archivo=r("prueba3"), pie="Recorte circular.", tam=50)),
        blq("Conclusiones",
            el("txtNumerada", items=["Suspendisse vitae elit.", "Aliquam arcu neque, ornare in, ullamcorper quis.",
                                     "Fusce sagittis erat at erat tristique mollis."]),
            el("txtBanda", texto="Lorem ipsum dolor sit amet", tam=1.15)),
        blq("Referencias y contacto",
            el("txtReferencias", items=["Apellido N, Apellido N. Título del artículo de relleno. *Revista*. Año; vol: páginas.",
                                        "Apellido N. *Título del libro de relleno*. Editorial; Año."]),
            el("txtContacto", archivo=r("qr_prueba"), texto="**Nombre Apellido**\nnombre@institucion.example")))
    m["filas"] = [fila(c1, c2, c3, alto="llenar", rejilla=4)]
    escribir("horizontal-48x36", {"nombre": "Horizontal 48 × 36 in", "orden": 2,
                                  "descripcion": "Cuatro columnas (la central ocupa dos), cabecera clara, cajas con "
                                                 "línea y tema verde.",
                                  "tipo": "estructurado", "etiquetas": ["48×36 in", "horizontal", "4 columnas"]},
             m, recursos=PRUEBA.values())


def capas():
    m = base("ciruela")
    m["lienzo"].update({"tamano": "A1", "ancho": "594mm", "alto": "841mm", "margen": "20mm"})
    m["tipografia"].update({"fuente": 22, "escalas": dict(m["tipografia"]["escalas"], titulo=3.0)})
    m["estilo"].update({"separacion_columnas": "14mm", "bloque": "caja", "numerar_bloques": True})
    m["cabecera"].update({"estilo": "degradado", "alineacion": "izquierda",
                          "titulo": "Un póster por capas",
                          "subtitulo": "Fondo, contenido y frente: cada capa se oculta, se atenúa y se ordena",
                          "autores": "Nombre Apellido^1^, Nombre Apellido^2^",
                          "afiliaciones": "^1^Institución  ^2^Institución",
                          "logo_derecho": r("logo1")})
    m["pie"].update({"estilo": "clara", "izquierda": "Plantilla «Capas» de DocsLab",
                     "derecha": "nombre.apellido@institucion.example"})
    m["capas"] = [
        {"id": "fondo", "nombre": "Fondo", "z": -10, "visible": True, "opacidad": 1, "elementos": [
            {"id": "a-fondoimg", "tipo": "imagen", "archivo": r("prueba2"), "x": 0, "y": 0, "ancla": "north west",
             "ancho": 1, "alto": 1, "ajuste": "cubrir", "opacidad": 0.07},
            {"id": "a-circulo", "tipo": "forma", "forma": "circulo", "x": 1.0, "y": 0.0, "ancho": 0.55,
             "fondo": "secundario!14", "ancla": "center"},
            {"id": "a-franja", "tipo": "forma", "forma": "rectangulo", "x": 0, "y": 1, "ancla": "south west",
             "ancho": 1, "alto": 0.012, "fondo": "acento"}]},
        {"id": "notas", "nombre": "Notas", "z": 5, "visible": True, "opacidad": 1, "elementos": [
            {"id": "a-nota", "tipo": "texto", "x": 0.975, "y": 0.455, "ancla": "north east", "ancho": 0.25,
             "texto": "**Esta nota está en la capa «Notas».** Ocúltala desde el panel de capas.",
             "fondo": "acento!15", "borde": "acento", "radio": "0.4em", "alineacion": "izquierda", "escala": 0.85},
            {"id": "a-flecha", "tipo": "forma", "forma": "flecha", "x": 0.80, "y": 0.50, "x2": 0.70, "y2": 0.545,
             "color": "acento", "grosor": "0.18em"}]},
        {"id": "frente", "nombre": "Frente", "z": 10, "visible": True, "opacidad": 1, "elementos": [
            {"id": "a-sello", "tipo": "texto", "texto": "BORRADOR", "x": 0.5, "y": 0.6, "rotacion": 28, "escala": 9,
             "opacidad": 0.1, "color": "acento", "negrita": True},
            {"id": "a-qr", "tipo": "imagen", "archivo": r("qr_prueba"), "x": 0.975, "y": 0.955, "ancla": "south east",
             "ancho": 0.07}]},
    ]
    c1 = col(
        blq("Capa de fondo", el("txtJustificado", texto="Detrás del contenido hay una imagen muy atenuada, un "
                                                        "círculo y una franja de color. Están en la capa «Fondo»."),
            el("imgAncho", archivo=r("prueba1"), pie="Figura dentro de una caja: forma parte del contenido.")),
        blq("Título oculto", el("txtJustificado", texto="Esta caja tiene título, pero está oculto: «Mostrar el título» "
                                                        "está desactivado. " + L2)),
        blq("Cajas de texto", el("txtResaltado", titulo="Nota con título", mostrar_titulo=True, texto=L4),
            el("txtCaja", estilo="nota", titulo="Recuerda", mostrar_titulo=True,
               texto="Cada caja de texto puede mostrar u ocultar su título.")))
    c1["bloques"][1]["mostrar_titulo"] = False
    c2 = col(
        blq("Capa de frente", el("txtJustificado", texto="El sello «BORRADOR» y el código QR están en la capa "
                                                        "«Frente», encima de todo. " + L1),
            el("imgRedondeada", archivo=r("prueba6"), pie="Imagen con esquinas redondeadas.")),
        blq("Capa propia", el("txtJustificado", texto="La nota y la flecha de la derecha están en una capa nueva, "
                                                      "«Notas», entre el contenido y el frente. " + L3)),
        blq("Estirada hasta abajo", el("txtJustificado", texto="La última caja de cada columna puede crecer hasta el "
                                                               "final de la fila."), estirar=True,
            estilo="resaltado"))
    m["filas"] = [fila(c1, c2, alto="llenar", rejilla=2)]
    escribir("capas-a1", {"nombre": "Capas (demostración)", "orden": 3,
                          "descripcion": "A1 con capa de fondo, una capa propia de notas y un sello en el frente; "
                                         "cajas con título oculto y caja estirada.",
                          "tipo": "estructurado", "etiquetas": ["A1", "capas"]},
             m, recursos=PRUEBA.values())


def minima():
    m = base("grafito")
    m["lienzo"].update({"tamano": "A1", "ancho": "594mm", "alto": "841mm", "margen": "24mm"})
    m["tipografia"].update({"fuente": 21, "familia": "palatino", "familia_titulos": "helvetica",
                            "escalas": dict(m["tipografia"]["escalas"], titulo=2.8, bloque=1.3)})
    m["estilo"].update({"bloque": "linea", "separacion_columnas": "16mm"})
    m["cabecera"].update({"estilo": "minima", "alineacion": "izquierda", "titulo": "Título del póster",
                          "subtitulo": "Una línea con el mensaje principal",
                          "autores": "Nombre Apellido · Nombre Apellido", "afiliaciones": "Institución, Ciudad"})
    m["pie"].update({"estilo": "clara", "izquierda": "Congreso · Ciudad, año", "derecha": "correo@institución"})
    c1 = col(blq("Introducción", el("txtJustificado", texto=L1 + "\n\n" + L2)),
             blq("Métodos", el("txtNumerada", items=["Primer paso del método.", "Segundo paso.", "Tercer paso."]),
                 el("imgAncho", archivo=r("prueba1"), pie="Esquema del método.")),
             dist="arriba")
    c2 = col(blq("Resultados", el("imgAncho", archivo=r("prueba2"), pie="Resultado principal."),
                 el("txtJustificado", texto=L3)),
             blq("Conclusiones", el("txtVinetas", items=["Primera conclusión.", "Segunda conclusión."])),
             dist="arriba")
    m["filas"] = [fila(c1, c2, alto="llenar", rejilla=2)]
    escribir("minima-a1", {"nombre": "Mínima A1", "orden": 4,
                           "descripcion": "Dos columnas sobrias: cabecera mínima, cajas con línea, Palatino para "
                                          "el texto y Helvetica para los títulos.",
                           "tipo": "estructurado", "etiquetas": ["A1", "2 columnas"]},
             m, recursos=[PRUEBA["prueba1"], PRUEBA["prueba2"]])


# ------------------------------------------------------------------ BGC (EN / ES)
def bgc(idioma: str):
    en = idioma == "en"
    nb = "nb-bgc"
    carpeta = "results" if en else "resultados"
    fig = FUENTES / ("bgc_en" if en else "bgc_es")

    def f(rel):  # figura del cuaderno
        return f"recursos/cuadernos/{nb}/{carpeta}/{rel}"
    F = {
        "clases": "1_data/1.3_bgcs_per_class.pdf" if en else "1_datos/1.3_bgcs_por_clase.pdf",
        "tsne": "1_data/1.5_a_tsne_by_class.pdf" if en else "1_datos/1.5_a_tsne_por_clase.pdf",
        "curva": "2_training/2.2_feature_selection_curve.pdf" if en else "2_entrenamiento/2.2_curva_seleccion_dominios.pdf",
        "confusion": "3_evaluation/3.2_confusion_matrix_test.pdf" if en else "3_evaluacion/3.2_matriz_confusion_prueba.pdf",
        "grupos": "4_groups_architecture/4.1_a_groups_tsne.pdf" if en else "4_grupos_arquitectura/4.1_a_grupos_tsne.pdf",
        "arbol": "4_groups_architecture/4.2_b_decision_tree.pdf" if en else "4_grupos_arquitectura/4.2_b_arbol_decision.pdf",
        "calor": "5_cluster_comparison/5.1_cluster_domain_heatmap.pdf" if en else "5_comparacion_clusteres/5.1_mapa_calor_clusters_dominios.pdf",
        "sintenia": "5_cluster_comparison/5.4_a_synteny_matrix.pdf" if en else "5_comparacion_clusteres/5.4_a_matriz_sintenia.pdf",
        "alineamiento": "5_cluster_comparison/5.5_alignment_terpene_locus1.pdf" if en else "5_comparacion_clusteres/5.5_alineamiento_terpene_locus1.pdf",
        "repetidos": "5_cluster_comparison/5.3_a_repeated_genes.pdf" if en else "5_comparacion_clusteres/5.3_a_genes_repetidos.pdf",
    }
    recursos = [(fig / Path(rel).name, f(rel)) for rel in F.values()]
    m = base("azul", idioma=idioma)
    m["lienzo"].update({"margen": "26mm"})
    m["tipografia"].update({"fuente": 24.5 if en else 24, "interlinea": 1.27,
                            "escalas": dict(m["tipografia"]["escalas"], titulo=2.65, subtitulo=1.3, autores=1.3,
                                            bloque=1.3, pie=0.78)})
    m["estilo"].update({"separacion_columnas": "18mm", "separacion_bloques": "0.75em", "relleno": "0.65em",
                        "nombre_figura": "Figure" if en else "Figura"})
    m["cabecera"].update({"ancho_logos": 0.001})
    n = NBSP
    if en:
        m["cabecera"].update({
            "titulo": "Classifying biosynthetic gene clusters of *Stutzerimonas*\nby their Pfam domain profile",
            "subtitulo": "DRAFT · [Meeting name] · [City, date]",
            "autores": "[First Last]^1^, [First Last]^1^, [First Last]^2^",
            "afiliaciones": "^1^[Institution · department · city]  ^2^[Institution · department · city]"})
        m["pie"].update({"izquierda": "Code and figures: `modelo_bgc_pfam_en.ipynb`", "centro": "DRAFT · [Repository URL]",
                         "derecha": "[email@institution]"})
        T = {
            "intro": ("1 · Introduction",
                      "Biosynthetic gene clusters (BGCs) encode the pathways of specialised metabolites. antiSMASH "
                      "detects them and assigns a product class with rules based on protein domains.\n\n"
                      "**Questions.** What do the BGCs of *Stutzerimonas* look like in terms of Pfam domains? Is a "
                      "BGC's domain profile enough to predict its class? Which domains and genes recur, and how "
                      "conserved is gene order?"),
            "datos": ("2 · The data",
                      f"One table of 1{n}272 antiSMASH regions. 81 genomes appear twice (GenBank and RefSeq); merging "
                      f"the copies leaves 652 BGCs from 85 genomes. Seven classes with fewer than 10 BGCs are excluded.",
                      "631 BGCs in 9 retained classes, from `betalactone` (146) to `nrp-metallophore` (25).",
                      f"The domain matrix has 631 BGCs × 1{n}251 Pfam domains; 4.3{n}% of its cells hold a domain, "
                      f"and there are 364 distinct presence/absence profiles. The median number of domains per BGC "
                      f"ranges from 37 (`naggn`) to 86 (`arylpolyene`)."),
            "tsne": ("3 · Classes separate by their domains",
                     f"t-SNE of the 1{n}251 domains, coloured by class. Most classes form compact groups; `nrps` and "
                     f"`nrp-metallophore` overlap (34 pairs of BGCs from the same genome overlap in the table)."),
            "metodo": ("4 · Method", [
                "**Split 70/30**, stratified: 441 BGCs to train, 190 held out until the end.",
                "**Model.** Linear SVM with recursive feature elimination (RFE), leave-one-out validation and the "
                "one-standard-error rule.",
                "**Exploration.** Ward groups on t-SNE, decision tree and gene-by-gene architecture.",
                "**Comparison.** Gene families by sequence similarity (≥ 0.5), synteny index and gene-by-gene "
                "alignment of the clusters."]),
            "curva": ("5 · How many domains does it need?",
                      "Validation accuracy peaks (0.978) at 75 domains; no smaller model lies within one standard error."),
            "confusion": ("6 · Performance on unseen BGCs",
                          f"186 of 190 held-out BGCs are classified correctly (accuracy 0.979, 95{n}% CI 0.947–0.992; "
                          f"balanced accuracy 0.956; MCC 0.976). Three of the four errors are `nrps` BGCs that lie "
                          f"inside the coordinates of an `nrp-metallophore` BGC of the same genome."),
            "grupos": ("7 · The classes form three groups",
                       "Ward clustering on the t-SNE map: G1 (398 BGCs, 8 classes), G2 (118: `betalactone` and "
                       "`ni-siderophore`) and G3 (115: `terpene`, `arylpolyene` and 1 `ni-siderophore`). The "
                       "silhouette keeps rising up to $k = 8$."),
            "arbol": ("8 · A few domains separate the groups",
                      f"A depth-3 tree using only domain presence or absence reproduces the groups (balanced accuracy "
                      f"0.981). `TrkA_C` is in 98{n}% of G3 and in no BGC outside it; `Glyoxalase` is in 96{n}% of G2 "
                      f"and 6{n}% of the rest."),
            "calor": ("9 · Characteristic domains of each class",
                      f"The 631 clusters against the characteristic domains of each class. 56 of the 1{n}251 domains "
                      f"are frequent (≥ 50{n}% of BGCs) in two or more classes and none in more than five; `MFS_1` "
                      f"(280 BGCs) and `KR` (262) are the most widespread."),
            "sintenia": ("10 · Synteny: gene order",
                         "Mean synteny index 0.400 within a class and 0.002 between classes. `betalactone` splits "
                         "into 6 loci with no neighbouring genes in common; `terpene` (0.79) and `ectoine` (0.64) "
                         "have the most conserved order."),
            "alineamiento": ("11 · Clusters aligned in order",
                             "The 65 `terpene` BGCs aligned gene by gene; each column is a gene family. 21 columns "
                             "hold the same family in ≥ 90{n}% of the BGCs.".replace("{n}", n)),
            "repetidos": ("12 · Genes repeated within a cluster",
                          f"The 19{n}390 genes form 1{n}788 families. 171 of 631 BGCs carry a repeated gene, mostly "
                          f"`DctP` (61 BGCs) and `OprD` (43); in 18 cases the copies are near-identical (similarity "
                          f"≥ 0.9)."),
            "concl": ("Conclusions", [
                f"With 75 of 1{n}251 domains, a linear SVM reproduces the antiSMASH class of unseen BGCs.",
                "The groups differ by the presence or absence of a few domains.",
                "Gene order is conserved within classes and almost never between them; `nrps` and "
                "`nrp-metallophore` share order (0.23).",
                "`nrps` labels that share a locus with an `nrp-metallophore` deserve review."]),
            "limit": ("Limitations",
                      "The split is by BGC, not by genome: 93 of the 190 test BGCs have an identical profile in "
                      "training (accuracy 0.989 on them, 0.969 on the rest). The model reproduces classes that "
                      "antiSMASH assigns by rules. The table stores neither strand nor gene coordinates, so synteny "
                      "assumes table order. t-SNE is descriptive."),
            "refs": "References",
            "sello": "DRAFT",
        }
    else:
        m["cabecera"].update({
            "titulo": "Clasificación de clústeres biosintéticos de *Stutzerimonas*\npor su perfil de dominios Pfam",
            "subtitulo": "BORRADOR · [Nombre del congreso] · [Ciudad, fecha]",
            "autores": "[Nombre Apellido]^1^, [Nombre Apellido]^1^, [Nombre Apellido]^2^",
            "afiliaciones": "^1^[Institución · departamento · ciudad]  ^2^[Institución · departamento · ciudad]"})
        m["pie"].update({"izquierda": "Código y figuras: `modelo_bgc_pfam_es.ipynb`",
                         "centro": "BORRADOR · [URL del repositorio]", "derecha": "[correo@institución]"})
        T = {
            "intro": ("1 · Introducción",
                      "Los clústeres de genes biosintéticos (BGCs) codifican las rutas de los metabolitos "
                      "especializados. antiSMASH los detecta y les asigna una clase de producto con reglas basadas en "
                      "dominios proteicos.\n\n**Preguntas.** ¿Cómo son los BGCs de *Stutzerimonas* en cuanto a "
                      "dominios Pfam? ¿Basta el perfil de dominios de un BGC para predecir su clase? ¿Qué dominios y "
                      "genes se repiten y qué tan conservado está el orden de los genes?"),
            "datos": ("2 · Los datos",
                      f"Una tabla con 1{n}272 regiones de antiSMASH. 81 genomas aparecen dos veces (GenBank y RefSeq); "
                      f"al unir las copias quedan 652 BGCs de 85 genomas. Se excluyen 7 clases con menos de 10 BGCs.",
                      "631 BGCs en 9 clases retenidas, de `betalactone` (146) a `nrp-metallophore` (25).",
                      f"La matriz de dominios tiene 631 BGCs × 1{n}251 dominios Pfam; el 4.3{n}% de sus celdas "
                      f"contiene un dominio y hay 364 perfiles de presencia/ausencia distintos. La mediana de dominios "
                      f"por BGC va de 37 (`naggn`) a 86 (`arylpolyene`)."),
            "tsne": ("3 · Las clases se separan por sus dominios",
                     f"t-SNE de los 1{n}251 dominios, coloreado por clase. La mayoría de las clases forman grupos "
                     f"compactos; `nrps` y `nrp-metallophore` se solapan (en la tabla hay 34 pares de BGCs del mismo "
                     f"genoma que se solapan)."),
            "metodo": ("4 · Método", [
                "**Partición 70/30** estratificada: 441 BGCs para entrenar y 190 apartados hasta el final.",
                "**Modelo.** SVM lineal con eliminación recursiva de dominios (RFE), validación *leave-one-out* y "
                "regla de un error estándar.",
                "**Exploración.** Grupos de Ward sobre el t-SNE, árbol de decisión y arquitectura gen a gen.",
                "**Comparación.** Familias de genes por similitud de secuencia (≥ 0.5), índice de sintenia y "
                "alineamiento de los clústeres gen a gen."]),
            "curva": ("5 · ¿Cuántos dominios necesita?",
                      "La exactitud de validación llega a su máximo (0.978) con 75 dominios; ningún modelo más "
                      "pequeño queda a menos de un error estándar."),
            "confusion": ("6 · Resultado en BGCs nuevos",
                          f"186 de 190 BGCs de prueba bien clasificados (exactitud 0.979, IC 95{n}% 0.947–0.992; "
                          f"exactitud balanceada 0.956; MCC 0.976). Tres de los cuatro errores son BGCs `nrps` que "
                          f"están dentro de las coordenadas de un BGC `nrp-metallophore` del mismo genoma."),
            "grupos": ("7 · Las clases forman tres grupos",
                       "Agrupamiento de Ward sobre el mapa t-SNE: G1 (398 BGCs, 8 clases), G2 (118: `betalactone` y "
                       "`ni-siderophore`) y G3 (115: `terpene`, `arylpolyene` y 1 `ni-siderophore`). La silueta "
                       "sigue subiendo hasta $k = 8$."),
            "arbol": ("8 · Pocos dominios separan los grupos",
                      f"Un árbol de profundidad 3, solo con presencia o ausencia de dominios, reproduce los grupos "
                      f"(exactitud balanceada 0.981). `TrkA_C` está en el 98{n}% de G3 y en ningún BGC fuera de él; "
                      f"`Glyoxalase`, en el 96{n}% de G2 y el 6{n}% del resto."),
            "calor": ("9 · Dominios característicos de cada clase",
                      f"Los 631 clústeres frente a los dominios característicos de cada clase. 56 de los 1{n}251 "
                      f"dominios son frecuentes (≥ 50{n}% de los BGCs) en dos o más clases y ninguno en más de cinco; "
                      f"`MFS_1` (280 BGCs) y `KR` (262) son los más extendidos."),
            "sintenia": ("10 · Sintenia: el orden de los genes",
                         "Índice de sintenia medio 0.400 dentro de una clase y 0.002 entre clases. `betalactone` se "
                         "reparte en 6 loci sin genes vecinos en común; `terpene` (0.79) y `ectoine` (0.64) son las "
                         "clases con el orden más conservado."),
            "alineamiento": ("11 · Clústeres alineados en orden",
                             f"Los 65 BGCs `terpene` alineados gen a gen; cada columna es una familia de genes. 21 "
                             f"columnas tienen la misma familia en ≥ 90{n}% de los BGCs."),
            "repetidos": ("12 · Genes que se repiten en un clúster",
                          f"Los 19{n}390 genes forman 1{n}788 familias. 171 de 631 BGCs tienen un gen repetido, sobre "
                          f"todo `DctP` (61 BGCs) y `OprD` (43); en 18 casos las copias son casi idénticas "
                          f"(similitud ≥ 0.9)."),
            "concl": ("Conclusiones", [
                f"Con 75 de 1{n}251 dominios, un SVM lineal reproduce la clase de antiSMASH de BGCs no vistos.",
                "Los grupos se distinguen por la presencia o ausencia de pocos dominios.",
                "El orden de los genes se conserva dentro de cada clase y casi nunca entre clases; `nrps` y "
                "`nrp-metallophore` comparten orden (0.23).",
                "Conviene revisar las etiquetas `nrps` que comparten locus con un `nrp-metallophore`."]),
            "limit": ("Limitaciones",
                      "La partición es por BGC, no por genoma: 93 de los 190 BGCs de prueba tienen un perfil idéntico "
                      "en el entrenamiento (exactitud 0.989 en ellos y 0.969 en el resto). El modelo reproduce las "
                      "clases que antiSMASH asigna con reglas. La tabla no guarda la hebra ni las coordenadas de cada "
                      "gen, así que la sintenia asume el orden de la tabla. t-SNE es descriptivo."),
            "refs": "Referencias",
            "sello": "BORRADOR",
        }
    refs = ["Blin K, *et al.* (2023) antiSMASH 7.0. *Nucleic Acids Res* 51: W46–W50.",
            "Mistry J, *et al.* (2021) Pfam. *Nucleic Acids Res* 49: D412–D419.",
            "Guyon I, *et al.* (2002) *Mach Learn* 46: 389–422.",
            "van der Maaten L, Hinton G (2008) *J Mach Learn Res* 9: 2579–2605.",
            "Navarro-Muñoz JC, *et al.* (2020) BiG-SCAPE. *Nat Chem Biol* 16: 60–68."]
    c1 = col(
        blq(T["intro"][0], el("txtJustificado", texto=T["intro"][1])),
        blq(T["datos"][0], el("txtJustificado", texto=T["datos"][1]),
            el("imgAncho", archivo=f(F["clases"]), pie=T["datos"][2]),
            el("txtJustificado", texto=T["datos"][3])),
        blq(T["tsne"][0], el("imgAncho", archivo=f(F["tsne"]), pie=T["tsne"][1])),
        blq(T["metodo"][0], el("txtNumerada", items=T["metodo"][1])))
    c2 = col(
        blq(T["curva"][0], el("imgAncho", archivo=f(F["curva"]), pie=T["curva"][1])),
        blq(T["confusion"][0], el("imgCentro", archivo=f(F["confusion"]), pie=T["confusion"][1], tam=80)),
        blq(T["grupos"][0], el("imgAncho", archivo=f(F["grupos"]), pie=T["grupos"][1])),
        blq(T["arbol"][0], el("imgAncho", archivo=f(F["arbol"]), pie=T["arbol"][1])))
    c3 = col(
        blq(T["calor"][0], el("imgAncho", archivo=f(F["calor"]), pie=T["calor"][1])),
        blq(T["sintenia"][0], el("imgCentro", archivo=f(F["sintenia"]), pie=T["sintenia"][1], tam=80)),
        blq(T["alineamiento"][0], el("imgAncho", archivo=f(F["alineamiento"]), pie=T["alineamiento"][1])),
        blq(T["repetidos"][0], el("imgAncho", archivo=f(F["repetidos"]), pie=T["repetidos"][1])))
    pequeno = {"escala_texto": 0.85}
    c4 = col(blq(T["concl"][0], el("txtVinetas", items=T["concl"][1]), estilo="linea", opciones=pequeno))
    c5 = col(blq(T["limit"][0], el("txtJustificado", texto=T["limit"][1]), estilo="linea", opciones=pequeno))
    c6 = col(blq(T["refs"], el("txtReferencias", items=refs), estilo="linea"))
    m["filas"] = [fila(c1, c2, c3, alto="llenar", rejilla=3), fila(c4, c5, c6, rejilla=3)]
    m["capas"][1]["elementos"].append({"id": "a-sello", "tipo": "texto", "texto": T["sello"], "x": 0.5, "y": 0.52,
                                       "rotacion": 30, "escala": 11, "opacidad": 0.08, "color": "acento",
                                       "negrita": True, "visible": False})
    archivo = "modelo_bgc_pfam_en.ipynb" if en else "modelo_bgc_pfam_es.ipynb"
    c = cuaderno_meta(nb, archivo, carpeta)
    c["recompilar"] = True
    nombre = "BGC Stutzerimonas (EN)" if en else "BGC Stutzerimonas (ES)"
    desc = ("English draft poster of the BGC classification notebook. The figures come from the attached notebook: "
            "add tabla_bgc-5.csv to it and run it to regenerate them.") if en else \
        ("Borrador del póster de clasificación de BGCs. Las figuras salen del cuaderno incluido: añádele "
         "tabla_bgc-5.csv y ejecútalo para regenerarlas.")
    escribir("bgc-" + idioma, {"nombre": nombre, "orden": 5 if en else 6, "descripcion": desc,
                               "tipo": "estructurado", "etiquetas": ["A0", "cuaderno", "BGC"]},
             m, recursos=recursos, cuadernos=[(c, FUENTES / archivo)])


# ------------------------------------------------------------------ plantilla LaTeX libre
def catalogo():
    archivos = [(FUENTES / "catalogo.tex", "catalogo.tex")] + \
        [(IMG / f"{n}.png", f"img/{n}.png") for n in ("prueba1", "prueba2", "prueba3", "prueba4", "prueba5",
                                                      "prueba6", "logo1", "logo2", "qr_prueba")]
    d = escribir("catalogo-latex", {"nombre": "Catálogo de variantes (LaTeX)", "orden": 7,
                                    "descripcion": "Proyecto LaTeX libre: el catálogo de la plantilla (34 imágenes, "
                                                   "35 textos, 12 estilos de caja, filas, capas y configuración). "
                                                   "Se edita el código.",
                                    "tipo": "latex", "principal": "catalogo.tex", "etiquetas": ["LaTeX", "A2"]},
                 None, archivos=archivos)
    shutil.copyfile(A.STY, d / "postercientifico.sty")


def ejemplo_latex():
    archivos = [(FUENTES / "ejemplo_capas.tex", "ejemplo_capas.tex")] + \
        [(IMG / f"{n}.png", f"img/{n}.png") for n in ("prueba1", "prueba2", "prueba3", "prueba4", "prueba6",
                                                      "logo1", "qr_prueba")]
    d = escribir("ejemplo-capas-latex", {"nombre": "Póster por capas (LaTeX)", "orden": 8,
                                         "descripcion": "Proyecto LaTeX libre: un póster A1 escrito a mano con capas, "
                                                        "filas que llenan la página y cajas con título opcional.",
                                         "tipo": "latex", "principal": "ejemplo_capas.tex", "etiquetas": ["LaTeX", "A1"]},
                 None, archivos=archivos)
    shutil.copyfile(A.STY, d / "postercientifico.sty")


# ------------------------------------------------------------------ presentación, artículo, tesis e informe
def _secciones(m):
    """Las secciones (cajas) de un documento hecho con el asistente, por título."""
    return {b["titulo"]: b for f in m["filas"] for c in f["columnas"] for b in c["bloques"]}


TABLA = {"columnas": "lrr", "encabezado": True,
         "filas": [["Grupo", "Media", "Desviación"], ["Control", "12.4", "1.8"], ["Tratamiento A", "18.9", "2.1"],
                   ["Tratamiento B", "21.3", "2.6"]]}


def presentacion():
    m = M.desde_asistente({"clase": "presentacion", "tamano": "16:9", "tema": "pizarra", "idioma": "es"})
    m["cabecera"].update({"titulo": "Título de la presentación", "subtitulo": "El mensaje principal en una línea",
                          "autores": "Nombre Apellido", "afiliaciones": "Institución · Congreso, año"})
    pg = {p["nombre"]: p for p in m["paginas"]}
    filas = {f["pag"]: f for f in m["filas"]}
    intro = filas[pg["Introducción"]["id"]]
    intro["columnas"][0]["bloques"][0]["elementos"] = [
        el("txtVinetas", items=["El problema, en una frase.", "Por qué importa ahora.", "Qué se propone en este trabajo."])]
    res = filas[pg["Un resultado con su figura"]["id"]]
    res["columnas"][0]["bloques"][0]["elementos"] = [
        el("txtJustificado", texto="Explica aquí lo que muestra la figura: **una idea por diapositiva**."),
        el("txtCifra", cifra="87 %", texto="de los casos mejoran con el método")]
    res["columnas"][1]["bloques"][0]["elementos"] = [el("imgAncho", archivo=r("prueba2"), pie="Resultado principal.", tam=100)]
    # una diapositiva con lienzo libre: todo colocado a mano
    libre = copy.deepcopy(M.PAGINA_DEFECTO)
    libre.update({"id": M.nuevo_id("p"), "nombre": "Una diapositiva con lienzo libre", "libre": True})
    m["paginas"].insert(4, libre)
    sueltas = [
        blq("", el("imgAncho", archivo=r("prueba1"), pie="", tam=100), mostrar_titulo=False, estilo="ninguno",
            opciones={"relleno": "0pt"}, libre=True, x=0.06, y=0.22, ancho=0.4),
        blq("", el("imgAncho", archivo=r("prueba3"), pie="", tam=100), mostrar_titulo=False, estilo="ninguno",
            opciones={"relleno": "0pt"}, libre=True, x=0.56, y=0.24, ancho=0.24, rotacion=-4),
        blq("", el("txtIzquierda", texto="Aquí cada cosa se **arrastra** a donde quieras: no hay filas ni columnas."),
            mostrar_titulo=False, estilo="ninguno", opciones={"relleno": "0pt"}, libre=True, x=0.5, y=0.76, ancho=0.42),
    ]
    f = fila(col(*sueltas), rejilla=1)
    f["pag"] = libre["id"]
    m["filas"].append(f)
    escribir("presentacion-16x9", {"nombre": "Presentación 16:9", "orden": 9, "clase": "presentacion",
                                   "descripcion": "Diapositivas sobrias: portada, contenido con viñetas, una figura "
                                                  "con su texto, una diapositiva con lienzo libre y el cierre.",
                                   "tipo": "estructurado", "etiquetas": ["16:9", "diapositivas"]},
             m, recursos=[PRUEBA["prueba1"], PRUEBA["prueba2"], PRUEBA["prueba3"]])


def articulo():
    m = M.desde_asistente({"clase": "paper", "tamano": "A4", "columnas": 2, "tema": "grafito", "idioma": "es"})
    m["documento"]["resumen"] = L1 + " " + L4
    s = _secciones(m)
    s["Introducción"]["elementos"] = [el("txtJustificado", texto=L1 + "\n\n" + L2)]
    s["Métodos"]["elementos"] = [el("txtJustificado", texto=L3),
                                 el("txtEcuacion", ecuacion="\\bar{x} = \\frac{1}{n}\\sum_{i=1}^{n} x_i",
                                    texto="Donde $n$ es el número de muestras.")]
    s["Resultados"]["elementos"] = [el("txtJustificado", texto=L2),
                                    el("imgAncho", archivo=r("prueba2"), pie="Resultado principal del estudio."),
                                    el("txtTabla", pie="Resumen de los grupos.", tabla=copy.deepcopy(TABLA)),
                                    el("txtJustificado", texto=L4)]
    s["Discusión"]["elementos"] = [el("txtJustificado", texto=L3 + "\n\n" + L1)]
    s["Conclusiones"]["elementos"] = [el("txtJustificado", texto=L4)]
    escribir("articulo-dos-columnas", {"nombre": "Artículo a dos columnas", "orden": 10, "clase": "paper",
                                       "descripcion": "Artículo científico genérico: título y resumen a todo el ancho, "
                                                      "texto a dos columnas, figura, tabla, ecuación y referencias.",
                                       "tipo": "estructurado", "etiquetas": ["A4", "2 columnas"]},
             m, recursos=[PRUEBA["prueba2"]])


def tesis():
    m = M.desde_asistente({"clase": "tesis", "tamano": "A4", "tema": "pizarra", "idioma": "es"})
    m["documento"].update({"resumen": L1 + "\n\n" + L2, "lista_figuras": True,
                           "agradecimientos": "A quienes acompañaron este trabajo."})
    s = _secciones(m)
    s["Introducción"]["elementos"] = [el("txtJustificado", texto=L1 + "\n\n" + L3)]
    s["Planteamiento del problema"]["elementos"] = [el("txtJustificado", texto=L2)]
    s["Objetivos"]["elementos"] = [el("txtNumerada", items=["Objetivo general del trabajo.", "Primer objetivo específico.",
                                                           "Segundo objetivo específico."])]
    s["Marco teórico"]["elementos"] = [el("txtJustificado", texto=L3 + "\n\n" + L4)]
    s["Metodología"]["elementos"] = [el("txtJustificado", texto=L2),
                                     el("imgAncho", archivo=r("prueba1"), pie="Esquema del método.", tam=70)]
    s["Resultados"]["elementos"] = [el("txtJustificado", texto=L1),
                                    el("imgAncho", archivo=r("prueba2"), pie="Resultado principal.", tam=80),
                                    el("txtTabla", pie="Resumen de los grupos.", tabla=copy.deepcopy(TABLA))]
    s["Conclusiones"]["elementos"] = [el("txtJustificado", texto=L4)]
    escribir("tesis-generica", {"nombre": "Tesis", "orden": 11, "clase": "tesis",
                                "descripcion": "Plantilla genérica y configurable: portada, agradecimientos, resumen, "
                                               "índices, capítulos con secciones, referencias y un apéndice.",
                                "tipo": "estructurado", "etiquetas": ["A4", "capítulos"]},
             m, recursos=[PRUEBA["prueba1"], PRUEBA["prueba2"]])


def informe():
    m = M.desde_asistente({"clase": "documento", "tamano": "A4", "tema": "salvia", "idioma": "es"})
    m["cabecera"].update({"titulo": "Título del informe", "subtitulo": "Una línea que dice de qué trata"})
    m["documento"]["indice"] = False
    s = _secciones(m)
    s["Introducción"]["elementos"] = [el("txtJustificado", texto=L1 + "\n\n" + L2)]
    s["Desarrollo"]["elementos"] = [el("txtJustificado", texto=L3),
                                    el("txtVinetas", items=["Primer punto.", "Segundo punto.", "Tercer punto."]),
                                    el("imgAncho", archivo=r("prueba3"), pie="Una figura del informe.", tam=75),
                                    el("txtResaltado", texto="Una idea que conviene destacar.")]
    s["Conclusiones"]["elementos"] = [el("txtJustificado", texto=L4)]
    escribir("informe-a4", {"nombre": "Informe", "orden": 12, "clase": "documento",
                            "descripcion": "Documento general: título, secciones numeradas, viñetas, una figura y "
                                           "un texto destacado.",
                            "tipo": "estructurado", "etiquetas": ["A4", "documento"]},
             m, recursos=[PRUEBA["prueba3"]])


def miniaturas(solo=None):
    with tempfile.TemporaryDirectory() as tmp:
        alm = A.Almacen(Path(tmp))
        for d in sorted(DESTINO.iterdir()):
            if not (d / "plantilla.json").exists() or (solo and d.name not in solo):
                continue
            meta = alm.crear_proyecto("tmp", d.name)
            pd = alm.dir_proyecto(meta["id"])
            if meta["tipo"] == "estructurado":
                alm.escribir_tex(meta["id"], marcas=False)
            res = compilador.compilar(pd, meta["principal"], copiar_sty=meta["tipo"] == "estructurado",
                                      avisar_paginas=meta["tipo"] == "estructurado" and meta.get("clase", "poster") == "poster")
            mini = pd / "build" / "miniatura.png"
            estado = "ok" if res.get("ok") else "ERROR"
            print(f"{d.name:22s} {estado} páginas={res.get('paginas')} pasadas={res.get('pasadas')} "
                  f"{res.get('segundos')} s avisos={[a['mensaje'][:60] for a in res.get('avisos', [])][:3]}")
            for e in res.get("errores", [])[:3]:
                print("     ", e)
            if mini.exists():
                compilador.miniatura(pd / "build" / (Path(meta["principal"]).stem + ".pdf"), d / "miniatura.png", 520)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-miniaturas", action="store_true")
    ap.add_argument("--solo", nargs="*", help="construir solo estas plantillas (por el nombre de su carpeta)")
    a = ap.parse_args()
    DESTINO.mkdir(exist_ok=True)
    todas = {"academico-a0": academico, "horizontal-48x36": horizontal, "capas-a1": capas, "minima-a1": minima,
             "bgc-en": lambda: bgc("en"), "bgc-es": lambda: bgc("es"), "catalogo-latex": catalogo,
             "ejemplo-capas-latex": ejemplo_latex, "presentacion-16x9": presentacion,
             "articulo-dos-columnas": articulo, "tesis-generica": tesis, "informe-a4": informe}
    for nombre, hacer in todas.items():
        if not a.solo or nombre in a.solo:
            hacer()
    if not a.sin_miniaturas:
        miniaturas(set(a.solo) if a.solo else None)


if __name__ == "__main__":
    main()
