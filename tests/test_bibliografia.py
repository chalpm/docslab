# SPDX-License-Identifier: AGPL-3.0-only
"""Gestor de referencias: estilos, citas en el póster e importación."""
import io
import subprocess

import pytest

from conftest import RAIZ, hay_latex
from docslab import bibliografia as B, generador as G, modelo as M, variantes as V

ARTICULO = {"clave": "garcia2020", "tipo": "articulo", "anio": "2020", "titulo": "Un título de prueba",
            "autores": [{"apellido": "García", "nombre": "Ana"}, {"apellido": "López", "nombre": "Beatriz"}],
            "revista": "Revista de Pruebas", "volumen": "3", "numero": "2", "paginas": "10-20", "doi": "10.1000/xyz"}
LIBRO = {"clave": "who2021", "tipo": "libro", "anio": "2021", "titulo": "Informe mundial",
         "autores": [{"literal": "World Health Organization"}], "editorial": "WHO Press", "lugar": "Ginebra"}
OTRO = {"clave": "smith2019", "tipo": "articulo", "anio": "2019", "titulo": "Otro artículo",
        "autores": [{"apellido": "Smith", "nombre": "John A."}, {"apellido": "Wang", "nombre": "Li"},
                    {"apellido": "Kim", "nombre": "Soo"}],
        "revista": "Journal of Tests", "volumen": "1", "paginas": "1-9"}


def _poster(estilo, textos, refs=(ARTICULO, LIBRO, OTRO), incluir="citadas", idioma="es"):
    m = M.normalizar({})
    m["idioma"] = idioma
    m["bibliografia"] = {"estilo": estilo, "referencias": [dict(r) for r in refs]}
    elementos = []
    for i, t in enumerate(textos):
        e = V.elemento_nuevo("txtJustificado", f"e-{i}")
        e["texto"] = t
        elementos.append(e)
    lista = V.elemento_nuevo("bibliografia", "e-bib")
    lista["incluir"] = incluir
    elementos.append(lista)
    m["filas"] = [{"id": "f-1", "columnas": [{"id": "c-1", "bloques": [
        {"id": "b-1", "titulo": "Caja", "elementos": elementos}]}]}]
    return M.normalizar(m)


@pytest.mark.parametrize("estilo,esperado", [
    ("apa", "García, A. y López, B. (2020). Un título de prueba. Revista de Pruebas, 3(2), 10–20. https://doi.org/10.1000/xyz"),
    ("vancouver", "García A, López B. Un título de prueba. Revista de Pruebas. 2020;3(2):10-20. doi:10.1000/xyz"),
    ("ieee", "A. García y B. López, “Un título de prueba,” Revista de Pruebas, vol. 3, no. 2, pp. 10–20, 2020. doi: 10.1000/xyz"),
    ("chicago", "García, Ana y Beatriz López. 2020. “Un título de prueba.” Revista de Pruebas 3 (2): 10–20. https://doi.org/10.1000/xyz"),
    ("mla", "García, Ana y Beatriz López. “Un título de prueba.” Revista de Pruebas, vol. 3, no. 2, 2020, pp. 10–20, https://doi.org/10.1000/xyz"),
    ("harvard", "García, A. y López, B. (2020) ‘Un título de prueba’, Revista de Pruebas, 3(2), pp. 10–20. Disponible en: https://doi.org/10.1000/xyz"),
    ("nature", "García, A. & López, B. Un título de prueba. Revista de Pruebas 3, 10–20 (2020). https://doi.org/10.1000/xyz"),
    ("acs", "García, A.; López, B. Un título de prueba. Revista de Pruebas 2020, 3 (2), 10–20. https://doi.org/10.1000/xyz"),
])
def test_cada_estilo_formatea_un_articulo(estilo, esperado):
    e = B.formatear([ARTICULO], estilo, "es")[0]
    assert e["texto"] == esperado
    # la revista (o el volumen) va en cursiva, salvo en Vancouver (NLM no usa cursivas)
    assert ("<i>" in e["html"]) == (estilo != "vancouver")


def test_palabras_segun_el_idioma():
    assert B.formatear([ARTICULO], "apa", "en")[0]["texto"].startswith("García, A., & López, B. (2020).")
    assert B.ejemplo_cita("apa", "en") == "(García & López, 2020)"
    assert B.ejemplo_cita("apa", "es") == "(García y López, 2020)"
    sin_anio = dict(ARTICULO, anio="")
    assert "(s. f.)" in B.formatear([sin_anio], "apa", "es")[0]["texto"]
    assert "(n.d.)" in B.formatear([sin_anio], "apa", "en")[0]["texto"]


def test_el_html_se_escapa():
    malo = dict(ARTICULO, titulo="<script>alert(1)</script> & más")
    html = B.formatear([malo], "apa", "es")[0]["html"]
    assert "<script>" not in html and "&lt;script&gt;" in html and "&amp; más" in html


def test_citas_autor_anio_en_el_poster():
    tex, _ = G.generar(_poster("apa", ["Uno [@garcia2020].", "Dos [@smith2019; @garcia2020, p. 12].", "Mal [@nada]."]))
    assert r"\PCcita{(García y López, 2020)}" in tex
    # APA ordena por autor dentro del paréntesis
    assert r"\PCcita{(García y López, 2020, p. 12; Smith et al., 2019)}" in tex
    assert r"\PCcitadesconocida{nada}" in tex
    # la lista (solo las citadas) va en orden alfabético y con sangría francesa
    lista = tex[tex.index(r"\PCbibliografia[autor]"):]
    assert lista.index("García") < lista.index("Smith") and "Informe mundial" not in lista


def test_citas_numericas_en_orden_de_aparicion():
    m = _poster("vancouver", ["Primero [@smith2019].", "Luego [@garcia2020; @smith2019] y [@who2021]."])
    tex, _ = G.generar(m)
    assert r"\PCcita{(1)}" in tex and r"\PCcita{(1,2)}" in tex and r"\PCcita{(3)}" in tex
    lista = tex[tex.index(r"\PCbibliografia[numerica]"):]
    assert lista.index(r"\PCref{1.}{Smith") < lista.index(r"\PCref{2.}{García") < lista.index(r"\PCref{3.}{World")
    # superíndice pegado a la palabra (Nature) y corchetes (IEEE)
    assert "Primero\\PCcitasup{1}" in G.generar(_poster("nature", ["Primero [@smith2019]."]))[0].replace("{{", "").replace("}}", "")
    assert r"\PCcita{[1, 2]}" in G.generar(_poster("ieee", ["A [@smith2019; @garcia2020]."]))[0]


def test_rango_de_numeros():
    textos = ["[@garcia2020]", "[@smith2019]", "[@who2021]", "[@garcia2020; @smith2019; @who2021]"]
    assert r"\PCcita{(1–3)}" in G.generar(_poster("vancouver", textos))[0]


def test_lo_oculto_no_cuenta_para_numerar():
    m = _poster("vancouver", ["Oculto [@who2021].", "Visible [@garcia2020]."])
    m["filas"][0]["columnas"][0]["bloques"][0]["elementos"][0]["visible"] = False
    tex, _ = G.generar(m)
    assert r"\PCcita{(1)}" in tex and "World Health" not in tex
    v = G.vista_bibliografia(m)
    assert [(e["clave"], e["etiqueta"], e["en_lista"]) for e in v["entradas"]] == [
        ("garcia2020", "1.", True), ("who2021", "", False), ("smith2019", "", False)]
    assert v["citas"] == {"garcia2020": 1} and v["hay_lista"] and v["desconocidas"] == []


def test_todas_las_referencias():
    tex, _ = G.generar(_poster("apa", ["Nada citado."], incluir="todas"))
    assert "Informe mundial" in tex and "Otro artículo" in tex


def test_sin_referencias_la_lista_queda_vacia():
    tex, _ = G.generar(_poster("apa", ["Sin citas."], refs=()))
    assert r"\PCbibliografiavacia" in tex


def test_citas_en_formato_latex_y_al_convertir():
    m = _poster("apa", ["Texto con 5 % y una cita [@garcia2020]."])
    t0, _ = G.generar(m)
    ml = M.convertir_formato(m, "latex")
    assert "[@garcia2020]" in ml["filas"][0]["columnas"][0]["bloques"][0]["elementos"][0]["texto"]
    assert G.generar(ml)[0] == t0
    assert G.generar(M.convertir_formato(ml, "simple"))[0] == t0


def test_mismo_autor_y_anio_llevan_letra():
    a = dict(ARTICULO, clave="a1", titulo="Alfa")
    b = dict(ARTICULO, clave="a2", titulo="Beta")
    tex, _ = G.generar(_poster("apa", ["[@a2] y [@a1]"], refs=(a, b)))
    assert "(García y López, 2020b)" in tex and "(García y López, 2020a)" in tex


def test_leer_bibtex():
    texto = r"""
    @string{nar = "Nucleic Acids Research"}
    % un comentario
    @article{Lopez2019,
      author = {L{\'o}pez, Beatriz and Smith, John A. and {World Health Organization}},
      title = {Biosynthetic gene clusters in {Streptomyces} \& co.},
      journal = nar, year = 2019, volume = {47}, number = {3}, pages = {1200--1215},
      doi = {https://doi.org/10.1093/nar/gkz001}
    }
    @book{libro, editor = {Pérez, Carlos}, title = "Un libro", publisher = {Ed. X}, year = {2001}, edition = {2}}
    @misc{roto, title = {Sin cerrar
    """
    refs, errores = B.leer_bibtex(texto)
    assert len(refs) == 2 and errores
    r = refs[0]
    assert r["clave"] == "Lopez2019" and r["tipo"] == "articulo"
    assert r["autores"][0] == {"apellido": "López", "nombre": "Beatriz"}
    assert r["autores"][2] == {"literal": "World Health Organization"}
    assert r["titulo"] == "Biosynthetic gene clusters in Streptomyces & co."
    assert r["revista"] == "Nucleic Acids Research" and r["paginas"] == "1200–1215" or r["paginas"] == "1200--1215"
    assert r["doi"] == "10.1093/nar/gkz001"
    assert refs[1]["tipo"] == "libro" and refs[1]["editores"] == [{"apellido": "Pérez", "nombre": "Carlos"}]


def test_leer_ris_y_csl():
    ris = ("TY  - JOUR\nAU  - García, Ana\nAU  - López, Beatriz\nTI  - Título RIS\nT2  - Revista RIS\n"
           "PY  - 2018/05/01\nVL  - 7\nIS  - 1\nSP  - 3\nEP  - 9\nDO  - 10.1/abc\nER  - \n")
    refs, err = B.leer_ris(ris)
    assert not err and refs[0]["titulo"] == "Título RIS" and refs[0]["anio"] == "2018"
    assert refs[0]["paginas"].replace("–", "-") == "3-9" and refs[0]["revista"] == "Revista RIS"
    csl = ('[{"id": "x1", "type": "article-journal", "title": "Título CSL", "container-title": "Revista CSL",'
           '"author": [{"family": "Kim", "given": "Soo"}, {"literal": "Consorcio Z"}],'
           '"issued": {"date-parts": [[2022, 3]]}, "DOI": "10.2/def", "volume": "4"}]')
    refs, err = B.leer_csl(csl)
    assert not err and refs[0]["autores"] == [{"apellido": "Kim", "nombre": "Soo"}, {"literal": "Consorcio Z"}]
    assert refs[0]["anio"] == "2022" and refs[0]["tipo"] == "articulo"
    # importar_texto reconoce el formato solo
    assert B.importar_texto(ris)[0][0]["titulo"] == "Título RIS"
    assert B.importar_texto(csl)[0][0]["titulo"] == "Título CSL"


def test_bibtex_de_ida_y_vuelta():
    texto = B.a_bibtex([ARTICULO, LIBRO, OTRO])
    refs, err = B.leer_bibtex(texto)
    assert not err and [r["clave"] for r in refs] == ["garcia2020", "who2021", "smith2019"]
    assert refs[0]["autores"] == ARTICULO["autores"] and refs[1]["autores"] == LIBRO["autores"]
    for k in ("titulo", "revista", "volumen", "numero", "doi", "anio"):
        assert refs[0][k] == ARTICULO[k]


def test_claves_y_doi():
    assert B.clave_sugerida(ARTICULO) == "garcia2020"
    assert B.clave_sugerida(ARTICULO, {"garcia2020"}) == "garcia2020a"
    lista = B.normalizar_lista([dict(ARTICULO), dict(ARTICULO, titulo="Otro"), {"titulo": "sin clave", "clave": "con espacio"}])
    assert [r["clave"] for r in lista] == ["garcia2020", "garcia2020a", "sin"]
    assert B.limpiar_doi("https://doi.org/10.1038/S41586-020-2649-2") == "10.1038/S41586-020-2649-2"
    assert B.limpiar_doi("doi: 10.1000/abc.") == "10.1000/abc"
    with pytest.raises(ValueError):
        B.buscar_doi("esto no es un doi")


def test_api_de_referencias(cliente):
    r = cliente.post("/api/bibliografia/formatear", json={"estilo": "ieee", "idioma": "en", "referencias": [ARTICULO]}).get_json()
    assert r["entradas"][0]["etiqueta"] == "[1]" and r["ejemplo"] == "[1]"
    r = cliente.post("/api/bibliografia/importar", json={"texto": "@article{a, title={T}, author={X, Y}, year={2000}}"}).get_json()
    assert r["referencias"][0]["titulo"] == "T"
    r = cliente.post("/api/bibliografia/importar", data={"archivo": (io.BytesIO(B.a_bibtex([LIBRO]).encode()), "r.bib")},
                     content_type="multipart/form-data").get_json()
    assert r["referencias"][0]["clave"] == "who2021"
    assert cliente.get("/api/bibliografia/doi?doi=nada").status_code == 400
    v = cliente.post("/api/bibliografia/vista", json={"modelo": _poster("apa", ["[@smith2019]"])}).get_json()
    assert [e["clave"] for e in v["entradas"] if e["en_lista"]] == ["smith2019"]
    assert cliente.post("/api/bibliografia/vista", json={}).status_code == 400
    # el .bib del proyecto
    pid = cliente.post("/api/proyectos", json={"nombre": "Bib"}).get_json()["id"]
    m = cliente.get(f"/api/proyectos/{pid}").get_json()["modelo"]
    m["bibliografia"]["referencias"] = [ARTICULO]
    cliente.put(f"/api/proyectos/{pid}/modelo", json=m)
    bib = cliente.get(f"/api/proyectos/{pid}/bibliografia.bib").get_data(as_text=True)
    assert "@article{garcia2020," in bib


@hay_latex
@pytest.mark.parametrize("estilo", ["apa", "vancouver", "nature", "mla"])
def test_poster_con_referencias_compila(estilo, tmp_path):
    import shutil
    m = _poster(estilo, ["Uno [@garcia2020].", "Dos [@smith2019; @garcia2020, p. 12] y [@nada].",
                         "Tres [@who2021]."], incluir="todas")
    m["bibliografia"]["referencias"][0]["url"] = "https://example.org/una/ruta/muy/larga/que/tiene/que/partirse/al/final/de/la/linea"
    tex, _ = G.generar(m)
    shutil.copy(RAIZ / "latex" / "postercientifico.sty", tmp_path)
    (tmp_path / "p.tex").write_text(tex, encoding="utf-8")
    for _ in range(3):
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "p.tex"], cwd=tmp_path, capture_output=True,
                           text=True, errors="replace")
    log = (tmp_path / "p.log").read_text(encoding="utf-8", errors="replace")
    assert r.returncode == 0, log[-3000:]
    assert "Cita desconocida" in log                     # [@nada] avisa
    assert "Overfull \\hbox" not in log, [l for l in log.splitlines() if "Overfull" in l]
