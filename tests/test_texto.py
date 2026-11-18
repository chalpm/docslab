# SPDX-License-Identifier: AGPL-3.0-only
from docslab.documento import texto as T


def test_escapa_los_simbolos_de_latex():
    assert T.convertir("50 % de A & B_1 #2 $3 {x}", parrafos=False) == r"50 \% de A \& B\_1 \#2 \$3 \{x\}"


def test_marcado_sencillo():
    assert T.convertir("**negrita** y *cursiva*", parrafos=False) == r"\textbf{negrita} y \textit{cursiva}"
    assert T.convertir("H~2~O y x^2^", parrafos=False) == r"H\textsubscript{2}O y x\textsuperscript{2}"
    assert T.convertir("`gen-1` y $E=mc^2$", parrafos=False) == r"\codigo{gen-1} y $E=mc^2$"


def test_latex_sin_tocar_con_llaves_anidadas():
    assert T.convertir(r"a {{\textcolor{red}{b}}} c", parrafos=False) == r"a \textcolor{red}{b} c"


def test_parrafos_y_saltos_de_linea():
    assert T.convertir("uno\ndos\n\ntres") == r"uno\newline dos\par tres"
    assert T.convertir("uno\ndos", parrafos=False) == r"uno\newline dos"


def test_formato_latex_copia_tal_cual():
    assert T.convertir(r"  \textbf{x} 50\%  ", "latex") == r"\textbf{x} 50\%"


def test_lista():
    assert T.lista(["*a*", "", "b"]) == [r"\textit{a}", "", "b"]
    assert T.lista("a\n\nb") == ["a", "b"]
