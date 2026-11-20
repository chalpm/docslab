# SPDX-License-Identifier: AGPL-3.0-only
"""Registro de los elementos que se pueden poner dentro de una caja.

Cada variante corresponde a una orden de postercientifico.sty (I01–I34,
T01–T36). La aplicación usa este registro para dibujar el formulario de cada
elemento y el generador para escribir la orden LaTeX.

Tipos de campo:
  imagen      ruta de un recurso del proyecto
  texto       una línea (se convierte según el formato del proyecto)
  parrafo     varios párrafos
  latex       código LaTeX sin tocar
  lista       una entrada por línea
  pares       lista de [término, descripción]
  hitos       lista de [fecha, texto]
  flechas     lista de [x0, y0, x1, y1, texto] (coordenadas de 0 a 1 sobre la imagen)
  tabla       {"columnas": "lrr", "filas": [[...], ...], "encabezado": true}
  porcentaje  número (0–100) → fracción del ancho de la columna
  fraccion    número entre 0 y 1
  numero      número
  angulo      grados
  dimension   longitud LaTeX (4.2em, 3cm)
  seleccion   una de «opciones»
  booleano    sí / no
  color       hexadecimal (1F4E79) o vacío
"""
from __future__ import annotations

ESTILOS_CAJA = ["barra", "linea", "caja", "simple", "borde", "sombra", "resaltado",
                "invertido", "contorno", "cita", "nota", "ninguno"]


def C(nombre, tipo, etiqueta, defecto=None, **extra):
    d = {"nombre": nombre, "tipo": tipo, "etiqueta": etiqueta}
    if defecto is not None:
        d["defecto"] = defecto
    d.update(extra)
    return d


# Campos que comparten las cajas de texto con título opcional
def campos_titulo(defecto_titulo="", mostrar=False):
    return [C("titulo", "texto", "Título de la caja", defecto_titulo),
            C("mostrar_titulo", "booleano", "Mostrar el título", mostrar)]


def campos_color():
    return [C("fondo", "color", "Color de fondo (opcional)", ""),
            C("borde", "color", "Color del borde (opcional)", "")]


PIE = "Pie de figura."
TXT = "Escribe aquí el texto. Una línea en blanco separa párrafos."

VARIANTES = [
    # ------------------------------------------------------------------ imágenes
    {"clave": "imgAncho", "codigo": "I01", "grupo": "imagen", "nombre": "A todo el ancho, pie debajo",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Ancho (% de la columna)", 100)],
     "args": [("opt_pct", "tam", 100), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgPieArriba", "codigo": "I02", "grupo": "imagen", "nombre": "Pie encima de la imagen",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Ancho (% de la columna)", 100)],
     "args": [("opt_pct", "tam", 100), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgCentro", "codigo": "I03", "grupo": "imagen", "nombre": "Centrada y estrecha",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Ancho (% de la columna)", 60)],
     "args": [("opt_pct", "tam", 60), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgIzquierda", "codigo": "I04", "grupo": "imagen", "nombre": "Alineada a la izquierda",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Ancho (% de la columna)", 60)],
     "args": [("opt_pct", "tam", 60), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgDerecha", "codigo": "I05", "grupo": "imagen", "nombre": "Alineada a la derecha",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Ancho (% de la columna)", 60)],
     "args": [("opt_pct", "tam", 60), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgTextoDerecha", "codigo": "I06", "grupo": "imagen", "nombre": "Imagen a la izquierda, texto a la derecha",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("texto", "parrafo", "Texto", TXT), C("tam", "fraccion", "Fracción para la imagen", 0.45)],
     "args": [("opt_num", "tam", 0.45), ("img", "archivo"), ("txt", "pie"), ("par", "texto")]},
    {"clave": "imgTextoIzquierda", "codigo": "I07", "grupo": "imagen", "nombre": "Imagen a la derecha, texto a la izquierda",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("texto", "parrafo", "Texto", TXT), C("tam", "fraccion", "Fracción para la imagen", 0.45)],
     "args": [("opt_num", "tam", 0.45), ("img", "archivo"), ("txt", "pie"), ("par", "texto")]},
    {"clave": "imgEnvueltaIzquierda", "codigo": "I08", "grupo": "imagen", "nombre": "Texto que rodea la imagen (izquierda)",
     "nota": "El texto que rodea la imagen es el campo «Texto» (debe ser más largo que la imagen).",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("texto", "parrafo", "Texto", TXT + " " + TXT + " " + TXT),
                C("tam", "fraccion", "Fracción para la imagen", 0.42)],
     "args": [("opt_num", "tam", 0.42), ("img", "archivo"), ("txt", "pie")], "despues": ("par", "texto")},
    {"clave": "imgEnvueltaDerecha", "codigo": "I09", "grupo": "imagen", "nombre": "Texto que rodea la imagen (derecha)",
     "nota": "El texto que rodea la imagen es el campo «Texto» (debe ser más largo que la imagen).",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("texto", "parrafo", "Texto", TXT + " " + TXT + " " + TXT),
                C("tam", "fraccion", "Fracción para la imagen", 0.42)],
     "args": [("opt_num", "tam", 0.42), ("img", "archivo"), ("txt", "pie")], "despues": ("par", "texto")},
    {"clave": "imgDos", "codigo": "I10", "grupo": "imagen", "nombre": "Dos en fila",
     "campos": [C("a", "imagen", "Imagen A", ""), C("b", "imagen", "Imagen B", ""),
                C("pie", "texto", "Pie de figura", PIE), C("tam", "porcentaje", "Alto (% del ancho)", 36)],
     "args": [("opt_pct", "tam", 36), ("img", "a"), ("img", "b"), ("txt", "pie")]},
    {"clave": "imgTres", "codigo": "I11", "grupo": "imagen", "nombre": "Tres en fila",
     "campos": [C("a", "imagen", "Imagen A", ""), C("b", "imagen", "Imagen B", ""), C("c", "imagen", "Imagen C", ""),
                C("pie", "texto", "Pie de figura", PIE), C("tam", "porcentaje", "Alto (% del ancho)", 27)],
     "args": [("opt_pct", "tam", 27), ("img", "a"), ("img", "b"), ("img", "c"), ("txt", "pie")]},
    {"clave": "imgCuatro", "codigo": "I12", "grupo": "imagen", "nombre": "Cuatro en fila",
     "campos": [C("a", "imagen", "Imagen A", ""), C("b", "imagen", "Imagen B", ""), C("c", "imagen", "Imagen C", ""),
                C("d", "imagen", "Imagen D", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Alto (% del ancho)", 22)],
     "args": [("opt_pct", "tam", 22), ("img", "a"), ("img", "b"), ("img", "c"), ("img", "d"), ("txt", "pie")]},
    {"clave": "imgRejilla", "codigo": "I13", "grupo": "imagen", "nombre": "Rejilla 2 × 2 con paneles",
     "campos": [C("a", "imagen", "Panel a", ""), C("b", "imagen", "Panel b", ""), C("c", "imagen", "Panel c", ""),
                C("d", "imagen", "Panel d", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Alto de cada celda (% del ancho)", 34)],
     "args": [("opt_pct", "tam", 34), ("img", "a"), ("img", "b"), ("img", "c"), ("img", "d"), ("txt", "pie")]},
    {"clave": "imgRejillaSeis", "codigo": "I14", "grupo": "imagen", "nombre": "Rejilla 3 × 2 con paneles",
     "campos": [C("a", "imagen", "Panel a", ""), C("b", "imagen", "Panel b", ""), C("c", "imagen", "Panel c", ""),
                C("d", "imagen", "Panel d", ""), C("e", "imagen", "Panel e", ""), C("f", "imagen", "Panel f", ""),
                C("pie", "texto", "Pie de figura", PIE), C("tam", "porcentaje", "Alto de cada celda (% del ancho)", 25)],
     "args": [("opt_pct", "tam", 25), ("img", "a"), ("img", "b"), ("img", "c"), ("img", "d"), ("img", "e"),
              ("img", "f"), ("txt", "pie")]},
    {"clave": "imgGrandeDosDerecha", "codigo": "I15", "grupo": "imagen", "nombre": "Una grande y dos pequeñas a la derecha",
     "campos": [C("grande", "imagen", "Imagen grande", ""), C("b", "imagen", "Pequeña arriba", ""),
                C("c", "imagen", "Pequeña abajo", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Alto (% del ancho)", 50)],
     "args": [("opt_pct", "tam", 50), ("img", "grande"), ("img", "b"), ("img", "c"), ("txt", "pie")]},
    {"clave": "imgDosIzquierdaGrande", "codigo": "I16", "grupo": "imagen", "nombre": "Dos pequeñas a la izquierda y una grande",
     "campos": [C("a", "imagen", "Pequeña arriba", ""), C("b", "imagen", "Pequeña abajo", ""),
                C("grande", "imagen", "Imagen grande", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Alto (% del ancho)", 50)],
     "args": [("opt_pct", "tam", 50), ("img", "a"), ("img", "b"), ("img", "grande"), ("txt", "pie")]},
    {"clave": "imgGrandeTresAbajo", "codigo": "I17", "grupo": "imagen", "nombre": "Una grande arriba y tres debajo",
     "campos": [C("grande", "imagen", "Imagen grande", ""), C("a", "imagen", "Pequeña 1", ""),
                C("b", "imagen", "Pequeña 2", ""), C("c", "imagen", "Pequeña 3", ""),
                C("pie", "texto", "Pie de figura", PIE), C("tam", "porcentaje", "Alto de la grande (% del ancho)", 50)],
     "args": [("opt_pct", "tam", 50), ("img", "grande"), ("img", "a"), ("img", "b"), ("img", "c"), ("txt", "pie")]},
    {"clave": "imgPieLateral", "codigo": "I18", "grupo": "imagen", "nombre": "Pie al lado de la imagen",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "fraccion", "Fracción para la imagen", 0.62)],
     "args": [("opt_num", "tam", 0.62), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgPieSobre", "codigo": "I19", "grupo": "imagen", "nombre": "Pie sobre la imagen, en una banda",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Ancho (% de la columna)", 100)],
     "args": [("opt_pct", "tam", 100), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgMarco", "codigo": "I20", "grupo": "imagen", "nombre": "Con marco",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Ancho (% de la columna)", 100)],
     "args": [("opt_pct", "tam", 100), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgRedondeada", "codigo": "I21", "grupo": "imagen", "nombre": "Esquinas redondeadas",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Alto (% del ancho)", 62)],
     "args": [("opt_pct", "tam", 62), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgCirculo", "codigo": "I22", "grupo": "imagen", "nombre": "Recorte circular",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Diámetro (% del ancho)", 60)],
     "args": [("opt_pct", "tam", 60), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgSombra", "codigo": "I23", "grupo": "imagen", "nombre": "Con sombra",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Ancho (% de la columna)", 94)],
     "args": [("opt_pct", "tam", 94), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgInclinada", "codigo": "I24", "grupo": "imagen", "nombre": "Inclinada, tipo fotografía",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "angulo", "Ángulo (grados)", 4)],
     "args": [("opt_num", "tam", 4), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgDetalle", "codigo": "I25", "grupo": "imagen", "nombre": "Con un detalle ampliado en la esquina",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("detalle", "imagen", "Detalle", ""),
                C("pie", "texto", "Pie de figura", PIE), C("tam", "fraccion", "Tamaño del detalle (fracción)", 0.36)],
     "args": [("opt_num", "tam", 0.36), ("img", "archivo"), ("img", "detalle"), ("txt", "pie")]},
    {"clave": "imgAnotada", "codigo": "I26", "grupo": "imagen", "nombre": "Con flechas y etiquetas",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("flechas", "flechas", "Flechas (de la etiqueta al punto; 0–1 sobre la imagen)",
                  [[0.2, 0.8, 0.42, 0.55, "zona A"], [0.82, 0.22, 0.62, 0.45, "zona B"]]),
                C("tam", "porcentaje", "Ancho (% de la columna)", 100)],
     "args": [("opt_pct", "tam", 100), ("img", "archivo"), ("txt", "pie"), ("flechas", "flechas")]},
    {"clave": "imgPanoramica", "codigo": "I27", "grupo": "imagen", "nombre": "Franja panorámica",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Alto (% del ancho)", 24)],
     "args": [("opt_pct", "tam", 24), ("img", "archivo"), ("txt", "pie")]},
    {"clave": "imgPila", "codigo": "I28", "grupo": "imagen", "nombre": "Dos apiladas con etiquetas A y B",
     "campos": [C("a", "imagen", "Imagen A", ""), C("b", "imagen", "Imagen B", ""),
                C("pie", "texto", "Pie de figura", PIE), C("tam", "porcentaje", "Alto de cada una (% del ancho)", 38)],
     "args": [("opt_pct", "tam", 38), ("img", "a"), ("img", "b"), ("txt", "pie")]},
    {"clave": "imgCollage", "codigo": "I29", "grupo": "imagen", "nombre": "Collage de tres imágenes superpuestas",
     "campos": [C("a", "imagen", "Imagen izquierda", ""), C("b", "imagen", "Imagen central", ""),
                C("c", "imagen", "Imagen derecha", ""), C("pie", "texto", "Pie de figura", PIE),
                C("tam", "porcentaje", "Alto total (% del ancho)", 62)],
     "args": [("opt_pct", "tam", 62), ("img", "a"), ("img", "b"), ("img", "c"), ("txt", "pie")]},
    {"clave": "imgTituloSobre", "codigo": "I32", "grupo": "imagen", "nombre": "Imagen con título encima",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("titulo", "texto", "Título", "Título sobre la imagen"),
                C("subtitulo", "texto", "Subtítulo", "Subtítulo"), C("tam", "porcentaje", "Alto (% del ancho)", 50)],
     "args": [("opt_pct", "tam", 50), ("img", "archivo"), ("txt", "titulo"), ("txt", "subtitulo")]},
    {"clave": "imgComparar", "codigo": "I33", "grupo": "imagen", "nombre": "Comparación con rótulos",
     "campos": [C("a", "imagen", "Imagen A", ""), C("b", "imagen", "Imagen B", ""),
                C("ra", "texto", "Rótulo A", "Antes"), C("rb", "texto", "Rótulo B", "Después"),
                C("pie", "texto", "Pie de figura", PIE), C("tam", "porcentaje", "Alto (% del ancho)", 40)],
     "args": [("opt_pct", "tam", 40), ("img", "a"), ("img", "b"), ("txt", "ra"), ("txt", "rb"), ("txt", "pie")]},
    {"clave": "imgMiniatura", "codigo": "I34", "grupo": "imagen", "nombre": "Miniatura con texto",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("titulo", "texto", "Título", "Resultado"),
                C("texto", "texto", "Texto", "Una frase que lo explica."), C("tam", "dimension", "Lado", "4.2em")],
     "args": [("opt_dim", "tam", "4.2em"), ("img", "archivo"), ("txt", "titulo"), ("txt", "texto")]},
    # ------------------------------------------------------------------ texto
    {"clave": "txtJustificado", "codigo": "T01", "grupo": "texto", "nombre": "Párrafo justificado",
     "campos": [C("texto", "parrafo", "Texto", TXT)], "args": [("par", "texto")]},
    {"clave": "txtIzquierda", "codigo": "T02", "grupo": "texto", "nombre": "Alineado a la izquierda",
     "campos": [C("texto", "parrafo", "Texto", TXT)], "args": [("par", "texto")]},
    {"clave": "txtDerecha", "codigo": "T03", "grupo": "texto", "nombre": "Alineado a la derecha",
     "campos": [C("texto", "parrafo", "Texto", TXT)], "args": [("par", "texto")]},
    {"clave": "txtCentrado", "codigo": "T04", "grupo": "texto", "nombre": "Centrado",
     "campos": [C("texto", "parrafo", "Texto", TXT), C("tam", "porcentaje", "Ancho (% de la columna)", 100)],
     "args": [("opt_pct", "tam", 100), ("par", "texto")]},
    {"clave": "txtDosColumnas", "codigo": "T05", "grupo": "texto", "nombre": "Dos columnas",
     "campos": [C("texto", "parrafo", "Texto", TXT + " " + TXT)], "args": [("par", "texto")]},
    {"clave": "txtTresColumnas", "codigo": "T06", "grupo": "texto", "nombre": "Tres columnas",
     "campos": [C("texto", "parrafo", "Texto", TXT + " " + TXT)], "args": [("par", "texto")]},
    {"clave": "txtDosColumnasFilete", "codigo": "T07", "grupo": "texto", "nombre": "Dos columnas con filete central",
     "campos": [C("texto", "parrafo", "Texto", TXT + " " + TXT)], "args": [("par", "texto")]},
    {"clave": "txtAsimetrico", "codigo": "T08", "grupo": "texto", "nombre": "Dos columnas desiguales",
     "campos": [C("izquierda", "parrafo", "Columna estrecha", "**Texto corto.**"), C("derecha", "parrafo", "Columna ancha", TXT),
                C("tam", "fraccion", "Fracción de la columna estrecha", 0.33)],
     "args": [("opt_num", "tam", 0.33), ("par", "izquierda"), ("par", "derecha")]},
    {"clave": "txtCapitular", "codigo": "T09", "grupo": "texto", "nombre": "Letra capitular",
     "campos": [C("letra", "texto", "Letra capitular", "E"), C("resto", "texto", "Resto de la primera palabra", "scribe"),
                C("texto", "parrafo", "Resto del texto", "aquí el texto del párrafo."), C("tam", "numero", "Líneas", 3)],
     "args": [("opt_num", "tam", 3), ("txt", "letra"), ("txt", "resto"), ("par", "texto")]},
    {"clave": "txtEntradilla", "codigo": "T10", "grupo": "texto", "nombre": "Entradilla destacada y cuerpo",
     "campos": [C("entradilla", "texto", "Entradilla", "Una frase que resume el mensaje."), C("texto", "parrafo", "Cuerpo", TXT),
                C("tam", "numero", "Escala de la entradilla", 1.3)],
     "args": [("opt_num", "tam", 1.3), ("txt", "entradilla"), ("par", "texto")]},
    {"clave": "txtVinetas", "codigo": "T11", "grupo": "texto", "nombre": "Lista con viñetas",
     "campos": [C("items", "lista", "Elementos (uno por línea)", ["Primer punto", "Segundo punto", "Tercer punto"])],
     "args": [("items", "items")]},
    {"clave": "txtNumerada", "codigo": "T12", "grupo": "texto", "nombre": "Lista numerada",
     "campos": [C("items", "lista", "Elementos (uno por línea)", ["Primer paso", "Segundo paso", "Tercer paso"])],
     "args": [("items", "items")]},
    {"clave": "txtDefiniciones", "codigo": "T13", "grupo": "texto", "nombre": "Lista de definiciones",
     "campos": [C("pares", "pares", "Término y descripción", [["Término", "Descripción del término."],
                                                               ["Otro término", "Otra descripción."]])],
     "args": [("defs", "pares")]},
    {"clave": "txtCitaGrande", "codigo": "T14", "grupo": "texto", "nombre": "Cita grande centrada",
     "campos": [C("cita", "texto", "Cita", "Una frase para destacar"), C("autor", "texto", "Autor", "")],
     "args": [("txt", "cita"), ("txt", "autor")]},
    {"clave": "txtCitaBarra", "codigo": "T15", "grupo": "caja", "nombre": "Cita con barra lateral",
     "campos": campos_titulo("Cita") + [C("texto", "parrafo", "Texto", TXT)],
     "args": [("claves_caja", ("titulo", "mostrar_titulo")), ("par", "texto")]},
    {"clave": "txtResaltado", "codigo": "T16", "grupo": "caja", "nombre": "Resaltado sobre fondo de color",
     "campos": campos_titulo("Resultado principal") + [C("texto", "parrafo", "Texto", TXT)] + campos_color(),
     "args": [("claves_caja", ("titulo", "mostrar_titulo", "fondo", "borde")), ("par", "texto")]},
    {"clave": "txtRecuadro", "codigo": "T17", "grupo": "caja", "nombre": "Recuadro con borde",
     "campos": campos_titulo("Recuadro") + [C("texto", "parrafo", "Texto", TXT)] + campos_color(),
     "args": [("claves_caja", ("titulo", "mostrar_titulo", "fondo", "borde")), ("par", "texto")]},
    {"clave": "txtCajaTitulo", "codigo": "T18", "grupo": "caja", "nombre": "Caja con título",
     "campos": campos_titulo("Título de la caja", True) + [C("texto", "parrafo", "Texto", TXT)] + campos_color(),
     "args": [("claves_caja", ("mostrar_titulo_forzado", "fondo", "borde")), ("txt", "titulo"), ("par", "texto")]},
    {"clave": "txtInvertido", "codigo": "T19", "grupo": "caja", "nombre": "Texto en negativo",
     "campos": campos_titulo("Mensaje para llevar") + [C("texto", "parrafo", "Texto", TXT)],
     "args": [("claves_caja", ("titulo", "mostrar_titulo")), ("par", "texto")]},
    {"clave": "txtNotaLateral", "codigo": "T20", "grupo": "texto", "nombre": "Nota lateral junto al texto",
     "campos": [C("nota", "parrafo", "Nota", "Nota breve al margen."), C("texto", "parrafo", "Texto", TXT),
                C("tam", "fraccion", "Fracción de la nota", 0.28)],
     "args": [("opt_num", "tam", 0.28), ("par", "nota"), ("par", "texto")]},
    {"clave": "txtCifra", "codigo": "T21", "grupo": "texto", "nombre": "Cifra destacada",
     "campos": [C("cifra", "texto", "Cifra", "87 %"), C("texto", "texto", "Explicación", "de lo que mide la cifra")],
     "args": [("txt", "cifra"), ("txt", "texto")]},
    {"clave": "txtCifras", "codigo": "T22", "grupo": "texto", "nombre": "Tres cifras en fila",
     "campos": [C("c1", "texto", "Cifra 1", "12"), C("t1", "texto", "Texto 1", "primera"),
                C("c2", "texto", "Cifra 2", "34"), C("t2", "texto", "Texto 2", "segunda"),
                C("c3", "texto", "Cifra 3", "56"), C("t3", "texto", "Texto 3", "tercera")],
     "args": [("txt", "c1"), ("txt", "t1"), ("txt", "c2"), ("txt", "t2"), ("txt", "c3"), ("txt", "t3")]},
    {"clave": "txtSobreImagen", "codigo": "T23", "grupo": "texto", "nombre": "Texto sobre una imagen",
     "campos": [C("archivo", "imagen", "Imagen", ""), C("texto", "parrafo", "Texto", "**Mensaje.** Una frase sobre la imagen."),
                C("tam", "porcentaje", "Alto (% del ancho)", 55)],
     "args": [("opt_pct", "tam", 55), ("img", "archivo"), ("par", "texto")]},
    {"clave": "txtVertical", "codigo": "T24", "grupo": "texto", "nombre": "Rótulo vertical junto al texto",
     "campos": [C("rotulo", "texto", "Rótulo", "NOTA"), C("texto", "parrafo", "Texto", TXT)],
     "args": [("txt", "rotulo"), ("par", "texto")]},
    {"clave": "txtCirculo", "codigo": "T25", "grupo": "texto", "nombre": "Texto dentro de un círculo",
     "campos": [C("texto", "parrafo", "Texto", "**Mensaje**\ncorto"), C("tam", "porcentaje", "Diámetro (% del ancho)", 50)],
     "args": [("opt_pct", "tam", 50), ("par", "texto")]},
    {"clave": "txtTabla", "codigo": "T26", "grupo": "texto", "nombre": "Tabla",
     "campos": [C("pie", "texto", "Pie de la tabla", "Tabla 1. Descripción de la tabla."),
                C("tabla", "tabla", "Tabla", {"columnas": "lrr", "encabezado": True,
                                               "filas": [["Grupo", "Valor A", "Valor B"], ["Uno", "1.0", "2.0"],
                                                         ["Dos", "3.0", "4.0"]]})],
     "args": [("txt", "pie"), ("tabla", "tabla")]},
    {"clave": "txtEcuacion", "codigo": "T27", "grupo": "caja", "nombre": "Ecuación con su explicación",
     "campos": campos_titulo("Ecuación") + [C("ecuacion", "latex", "Ecuación (LaTeX, sin $)", r"E = m c^{2}"),
                                             C("texto", "parrafo", "Explicación", "Donde $E$ es la energía.")],
     "args": [("claves_caja", ("titulo", "mostrar_titulo")), ("raw", "ecuacion"), ("par", "texto")]},
    {"clave": "txtPasos", "codigo": "T28", "grupo": "texto", "nombre": "Tres pasos numerados en fila",
     "campos": [C("p1", "texto", "Paso 1", "Primer paso"), C("p2", "texto", "Paso 2", "Segundo paso"),
                C("p3", "texto", "Paso 3", "Tercer paso")],
     "args": [("txt", "p1"), ("txt", "p2"), ("txt", "p3")]},
    {"clave": "txtLineaTiempo", "codigo": "T29", "grupo": "caja", "nombre": "Línea de tiempo vertical",
     "campos": campos_titulo("Cronología") + [C("hitos", "hitos", "Hitos (fecha y texto)",
                                                 [["Fase 1", "Primer hito."], ["Fase 2", "Segundo hito."],
                                                  ["Fase 3", "Tercer hito."]])],
     "args": [("claves_caja", ("titulo", "mostrar_titulo")), ("hitos", "hitos")]},
    {"clave": "txtReferencias", "codigo": "T30", "grupo": "texto", "nombre": "Referencias en letra pequeña",
     "campos": [C("items", "lista", "Referencias (una por línea)",
                  ["Apellido N, *et al.* (Año) Título. *Revista* vol: páginas."])],
     "args": [("items", "items")]},
    {"clave": "txtEtiquetaMargen", "codigo": "T31", "grupo": "texto", "nombre": "Rótulo al margen y texto",
     "campos": [C("rotulo", "texto", "Rótulo", "Rótulo"), C("texto", "parrafo", "Texto", TXT),
                C("tam", "fraccion", "Fracción del rótulo", 0.24)],
     "args": [("opt_num", "tam", 0.24), ("txt", "rotulo"), ("par", "texto")]},
    {"clave": "txtBanda", "codigo": "T32", "grupo": "texto", "nombre": "Banda a todo el ancho",
     "campos": [C("texto", "texto", "Texto", "Mensaje principal"), C("tam", "numero", "Escala del texto", 1.5)],
     "args": [("opt_num", "tam", 1.5), ("txt", "texto")]},
    {"clave": "txtContacto", "codigo": "T34", "grupo": "texto", "nombre": "Tarjeta de contacto con código QR",
     "campos": [C("archivo", "imagen", "Código QR (imagen)", ""), C("texto", "parrafo", "Texto",
                                                                   "**Nombre Apellido**\ncorreo@institución"),
                C("tam", "dimension", "Lado del QR", "5.5em")],
     "args": [("opt_dim", "tam", "5.5em"), ("img", "archivo"), ("par", "texto")]},
    {"clave": "txtCaja", "codigo": "T35", "grupo": "caja", "nombre": "Caja de texto con cualquier estilo",
     "campos": campos_titulo("Título", True) + [C("estilo", "seleccion", "Estilo", "borde", opciones=ESTILOS_CAJA),
                                                C("texto", "parrafo", "Texto", TXT)] + campos_color(),
     "args": [("claves_caja", ("estilo", "titulo", "mostrar_titulo", "fondo", "borde")), ("par", "texto")]},
    {"clave": "bibliografia", "codigo": "T36", "grupo": "texto", "nombre": "Referencias con estilo (gestor)",
     "nota": "Se arma sola con las referencias del panel Referencias, en el estilo elegido allí. "
             "En cualquier texto, cita con [@clave] o [@a; @b, p. 12].",
     "campos": [C("incluir", "seleccion", "Qué referencias", "citadas",
                  opciones=[{"valor": "citadas", "texto": "Solo las citadas en el póster"},
                            {"valor": "todas", "texto": "Todas las del proyecto"}]),
                C("columnas", "numero", "Columnas", 1)],
     "args": []},
    # ------------------------------------------------------------------ otros
    {"clave": "latex", "codigo": "L", "grupo": "otros", "nombre": "Código LaTeX libre",
     "campos": [C("codigo", "latex", "Código LaTeX", r"\txtCifra{42}{una cifra escrita en LaTeX}")],
     "args": []},
    {"clave": "espacio", "codigo": "E", "grupo": "otros", "nombre": "Espacio vertical",
     "campos": [C("alto", "dimension", "Alto (vacío = todo el espacio libre)", "1em")],
     "args": []},
]

POR_CLAVE = {v["clave"]: v for v in VARIANTES}

GRUPOS = [
    {"clave": "texto", "nombre": "Texto"},
    {"clave": "caja", "nombre": "Cajas de texto (con título opcional)"},
    {"clave": "imagen", "nombre": "Imágenes"},
    {"clave": "otros", "nombre": "Otros"},
]


def elemento_nuevo(clave: str, id_: str) -> dict:
    """Elemento con los valores por defecto de su variante."""
    v = POR_CLAVE[clave]
    e = {"id": id_, "tipo": clave, "visible": True}
    for c in v["campos"]:
        d = c.get("defecto")
        if isinstance(d, (list, dict)):
            import copy
            d = copy.deepcopy(d)
        e[c["nombre"]] = d if d is not None else ""
    return e
