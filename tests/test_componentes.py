"""Componente Lab: plantillas {{campo}}, diseños sin código, recrear los incluidos y su uso en el póster."""
import io
import json
import re

import pytest

from conftest import hay_latex
from docslab import compilador, componentes as C, generador as G, modelo as M, variantes as V

Valor = C.Valor


def _poster(*comps, elementos=None):
    m = M.normalizar({})
    m["componentes"] = {c["id"]: c for c in comps}
    m["filas"] = [{"id": "f-1", "columnas": [{"id": "c-1", "bloques": [
        {"id": "b-1", "titulo": "Caja", "elementos": elementos or [{"id": f"e-{i}", "tipo": "cmp:" + c["id"]}
                                                                    for i, c in enumerate(comps)]}]}]}]
    return M.normalizar(m)


LATEX = {"modo": "latex", "nombre": "Ficha", "codigo": "\\PC@antes{\\bfseries{{titulo}}}\\par\n\\begin{itemize}{{#items}}\\item {{.}}{{/items}}\\end{itemize}\n"
         "{{^nota}}sin nota{{/nota}} \\rule{{{ancho}}\\linewidth}{1pt} {\\color{{{color}}}x}\\PC@despues\n",
         "preambulo": "\\newcommand\\fichaPropia[1]{#1}",
         "campos": [{"nombre": "titulo", "tipo": "texto", "defecto": "Hola **mundo**"},
                    {"nombre": "items", "tipo": "lista", "defecto": ["a", "b"]},
                    {"nombre": "nota", "tipo": "texto", "defecto": ""},
                    {"nombre": "ancho", "tipo": "porcentaje", "defecto": 45},
                    {"nombre": "color", "tipo": "color", "defecto": "1F4E79"}]}


def test_plantilla_huecos_y_secciones():
    ctx = {"t": Valor("Hola"), "vacio": Valor("", verdad=False), "l": Valor("", [Valor("a"), Valor("b")], True),
           "p": Valor("", [Valor("x", partes={"0": Valor("A"), "1": Valor("B")})], True)}
    r = C.renderizar("{{t}}|{{#vacio}}no{{/vacio}}|{{^vacio}}sí{{/vacio}}|{{#l}}<{{.}}>{{/l}}|{{#p}}{{0}}={{1}}{{/p}}", [ctx])
    assert r == "Hola||sí|<a><b>|A=B"
    # lo que no es un campo se queda como está (LaTeX con llaves dobles)
    assert C.renderizar(r"\textbf{{x}} {{{t}}} {{ t }}", [ctx]) == r"\textbf{{x}} {Hola} Hola"
    # una orden pegada a un hueco no se junta con las letras del valor
    assert C.renderizar(r"\bfseries{{t}}\par{{^vacio}}fin{{/vacio}}", [ctx]) == r"\bfseries Hola\par fin"
    # una sección que no sale conserva sus saltos de línea (los errores dan la línea buena)
    assert C.renderizar("{{#vacio}}\nuno\n{{/vacio}}fin", [ctx]) == "\n\nfin"


def test_normalizar_campos():
    c = C.normalizar({"modo": "latex", "campos": [
        {"nombre": "bien", "tipo": "texto"}, {"nombre": "bien", "tipo": "texto"}, {"nombre": "1malo"},
        {"nombre": "id"}, {"nombre": "op", "tipo": "seleccion", "opciones": ["a", {"valor": "b", "texto": "Bé"}, "a"],
                            "defecto": "zz"}, {"nombre": "n", "tipo": "numero", "defecto": "3.5"},
        {"nombre": "l", "tipo": "lista", "defecto": "uno\n\ndos"}]})
    assert [x["nombre"] for x in c["campos"]] == ["bien", "op", "n", "l"]
    op = c["campos"][1]
    assert op["opciones"] == [{"valor": "a", "texto": "a"}, {"valor": "b", "texto": "Bé"}] and op["defecto"] == "a"
    assert c["campos"][2]["defecto"] == 3.5 and c["campos"][3]["defecto"] == ["uno", "dos"]
    assert C.normalizar({"modo": "raro"})["modo"] == "latex"


def test_valores_en_latex():
    c = C.normalizar(LATEX)
    cuerpo = C.cuerpo_instancia(c, {"titulo": "50 % & más"}, "simple", "e-1")
    assert r"\bfseries50 \% \& más" in cuerpo          # un número no se pega a la orden: no hace falta espacio
    assert r"\item a\item b" in cuerpo and "sin nota" in cuerpo and r"\rule{0.45\linewidth}{1pt}" in cuerpo
    assert r"\definecolor{pcke1color}{HTML}{1F4E79}" in cuerpo and r"\color{pcke1color}" in cuerpo
    # un color del tema no necesita definirse
    assert "pcAcento!20" in C.cuerpo_instancia(c, {"color": "acento!20"}, "simple", "e-1")


def test_diseno_sin_codigo():
    D = C.DEFECTOS_PIEZA
    pz = lambda t, **k: {**json.loads(json.dumps(D[t])), "tipo": t, **k}
    c = C.normalizar({"modo": "visual", "diseno": {"caja": {"estilo": "invertido", "fondo": "acento"}, "piezas": [
        pz("titulo", valor="T"), pz("texto", valor="fijo", editable=False), pz("imagen", editable=False),
        pz("icono", valor="72"), pz("columnas", columnas=[{"ancho": 40, "piezas": [pz("cifra")]},
                                                           {"ancho": 60, "piezas": [pz("titulo", valor="Otro")]}])]}})
    nombres = [(x["nombre"], x["tipo"]) for x in c["campos"]]
    assert nombres == [("titulo", "texto"), ("imagen", "imagen"), ("icono", "seleccion"), ("cifra", "texto"),
                       ("titulo2", "texto")]
    codigo, pre = C.codigo_de(c)
    assert "\\begin{caja}[estilo=invertido, sin titulo" in codigo and "fondo=pcAcento" in codigo
    assert "{{titulo}}" in codigo and "{{titulo2}}" in codigo and "fijo" in codigo and "{{imagen}}" in codigo
    assert "\\ding{{{icono}}}" in codigo and pre == "\\RequirePackage{pifont}"
    assert "minipage}[t]{\\dimexpr0.4\\linewidth-0.5em\\relax}" in codigo
    # pasar a código conserva los campos
    lx = C.a_codigo(c)
    assert lx["modo"] == "latex" and lx["codigo"] == codigo and [x["nombre"] for x in lx["campos"]] == [n for n, _ in nombres]


@pytest.mark.parametrize("clave", [v["clave"] for v in V.VARIANTES if v["clave"] not in C.NO_PREAJUSTE])
def test_recrear_cada_incluido(clave):
    c = C.desde_variante(clave, "latex")
    assert c["modo"] == "latex" and c["origen"] == clave
    cuerpo = c["codigo"].split("\n", 4)[-1]
    assert not re.search(r"#[0-9]", cuerpo)                # todos los argumentos son ahora {{campos}}
    nombres = {x["nombre"] for x in c["campos"]}
    usados = {n for _, n in C._ETIQUETA.findall(cuerpo)}         # (los comentarios de arriba explican {{campo}})
    assert usados - {".", "0", "1"} <= nombres
    assert C.llaves_equilibradas(c["codigo"]) is None
    p = C.desde_variante(clave, "preajuste")
    assert p["modo"] == "preajuste" and p["base"] == clave
    # el preajuste dibuja lo mismo que la variante original
    e = V.elemento_nuevo(clave, "e-x")
    assert G.llamada(C.elemento_preajuste(p, e), "simple") == G.llamada(e, "simple")


def test_componentes_en_el_poster():
    lx = C.normalizar(LATEX)
    pre = C.desde_variante("txtCifra", "preajuste")
    pre["fijos"] = {"texto": "fijo"}
    pre["campos"] = [x for x in pre["campos"] if x["nombre"] == "cifra"]
    roto = C.normalizar({"modo": "latex", "nombre": "Roto", "codigo": "\\textbf{sin cerrar"})
    m = _poster(lx, pre, roto)
    m["filas"][0]["columnas"][0]["bloques"][0]["elementos"].append({"id": "e-falta", "tipo": "cmp:k-noexiste"})
    tex, mapa = G.generar(m)
    i = tex.index("Componentes propios")
    assert "\\makeatletter" in tex[i:] and "\\newcommand\\fichaPropia[1]{#1}" in tex
    assert "\\expandafter\\def\\csname PCk@e-0\\endcsname{%" in tex and "\\csname PCk@e-0\\endcsname" in tex
    assert "\\txtCifra{87 \\%}{fijo}" in tex                  # el preajuste usa la orden incluida
    assert "\\PCcomponenteroto{Roto: Falta cerrar 1 llave" in tex
    assert "\\PCcomponenteroto{Falta la definición de este componente}" in tex
    # con «archivos» (vista previa del Lab) el código va aparte
    archivos = {}
    tex2, _ = G.generar(m, archivos=archivos)
    assert "\\makeatletter\\input{cmp-e-0}\\makeatother" in tex2 and "cmp-e-0.tex" in archivos
    assert f"cmp-pre-{lx['id']}.tex" in archivos


def test_citas_dentro_de_un_componente():
    lx = C.normalizar(LATEX)
    m = _poster(lx)
    m["filas"][0]["columnas"][0]["bloques"][0]["elementos"][0]["titulo"] = "Ver [@a]"
    m["bibliografia"] = {"estilo": "vancouver", "referencias": [{"clave": "a", "titulo": "X", "anio": "2020"}]}
    tex, _ = G.generar(M.normalizar(m))
    assert "Ver \\PCcita{(1)}" in tex


def test_localizar_error_en_un_componente():
    error = {"linea": 40, "contexto": "\\PCk@e-0 ->\\PC@antes {\\malo }\nl.40 \\end{fila}"}
    assert compilador.localizar_error(error, [""] * 50, {40: "f-1", 12: "e-0"}) == "e-0"


def test_api_de_componentes(cliente):
    c = cliente.post("/api/componentes", json=LATEX).get_json()
    cid = c["id"]
    assert c["version"] == 1 and cliente.get("/api/componentes").get_json()[0]["id"] == cid
    c2 = cliente.put(f"/api/componentes/{cid}", json={**c, "nombre": "Ficha 2"}).get_json()
    assert c2["version"] == 2 and c2["nombre"] == "Ficha 2"
    assert cliente.put(f"/api/componentes/{cid}", json=c2).get_json()["version"] == 2   # sin cambios, misma versión
    dup = cliente.post(f"/api/componentes/{cid}/duplicar").get_json()
    assert dup["id"] != cid and dup["nombre"].endswith("(copia)")
    exportado = cliente.get(f"/api/componentes/exportar?ids={cid}").get_data()
    importados = cliente.post("/api/componentes/importar", data={"archivo": (io.BytesIO(exportado), "c.json")},
                              content_type="multipart/form-data").get_json()
    assert len(importados) == 1 and importados[0]["id"] not in (cid, dup["id"])
    assert cliente.delete(f"/api/componentes/{dup['id']}").status_code == 200
    assert len(cliente.get("/api/componentes").get_json()) == 2
    # recrear devuelve un borrador sin guardar
    b = cliente.post("/api/componentes/recrear", json={"clave": "txtCifra"}).get_json()
    assert "id" not in b and "{{cifra}}" in b["codigo"]
    assert cliente.post("/api/componentes/recrear", json={"clave": "latex"}).status_code == 400
    r = cliente.post("/api/componentes/codigo", json={"modo": "visual", "diseno": {"piezas": [{"tipo": "titulo"}]}}).get_json()
    assert "{{titulo}}" in r["codigo"] and r["como_latex"]["modo"] == "latex"
    # copiar al Lab uno que solo estaba en un póster conserva su id
    solo = C.normalizar({**LATEX, "nombre": "De un colega"})
    r = cliente.post("/api/componentes", json={"componente": solo, "conservar_id": True}).get_json()
    assert r["id"] == solo["id"]
    assert cliente.get("/api/componentes/k-noexiste").status_code == 400
    assert cliente.post("/api/componentes/importar", json={"texto": "no es json"}).status_code == 400


@hay_latex
def test_poster_con_componentes_compila(tmp_path):
    import shutil
    from conftest import RAIZ
    D = C.DEFECTOS_PIEZA
    pz = lambda t, **k: {**json.loads(json.dumps(D[t])), "tipo": t, **k}
    visual = C.normalizar({"modo": "visual", "nombre": "V", "diseno": {"caja": {"estilo": "resaltado"}, "piezas": [
        pz("etiqueta"), pz("titulo"), pz("cifra"), pz("texto"), pz("imagen", circulo=True, ancho=30), pz("lista"),
        pz("icono"), pz("separador"), pz("espacio"), pz("latex"),
        pz("columnas", columnas=[{"ancho": 30, "piezas": [pz("icono", valor="37")]}, {"ancho": 70, "piezas": [pz("texto")]}])]}})
    recreado = C.desde_variante("imgAnotada", "latex")
    m = _poster(visual, C.normalizar(LATEX), recreado, C.desde_variante("txtLineaTiempo", "preajuste"))
    tex, _ = G.generar(m)
    shutil.copy(RAIZ / "latex" / "postercientifico.sty", tmp_path)
    (tmp_path / "p.tex").write_text(tex, encoding="utf-8")
    res = compilador.compilar(tmp_path, "p.tex", max_pasadas=2, hacer_miniatura=False)
    assert res["ok"], res["errores"]
    assert not [a for a in res["avisos"] if a["tipo"] == "plantilla"], res["avisos"]


@hay_latex
def test_vista_previa_del_lab(tmp_path):
    bien = C.compilar_vista(C.normalizar(LATEX), tmp_path)
    assert bien["ok"] and bien["caja"]["x1"] > bien["caja"]["x0"] and not bien["errores"]
    assert C.compilar_vista(C.normalizar(LATEX), tmp_path)["huella"] == bien["huella"]      # en caché
    malo = C.normalizar({**LATEX, "codigo": "% una\n% dos\n\\ordenquenoexiste{{titulo}}\n"})
    r = C.compilar_vista(malo, tmp_path)
    assert not r["ok"] and r["errores"][0]["donde"] == "codigo" and r["errores"][0]["linea"] == 3
    destino = tmp_path / "mini.png"
    if compilador.pdftoppm():
        assert C.miniatura_desde_vista(tmp_path, bien["huella"], destino) and destino.stat().st_size > 200
