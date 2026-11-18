// SPDX-License-Identifier: AGPL-3.0-only
// Gestor de referencias: lista en el estilo elegido (en el mismo orden y con las
// mismas etiquetas que en el documento), formulario, importación (BibTeX, RIS,
// CSL-JSON y DOI) y el botón para citar desde los campos de texto.
import { api, post, subir, descargar } from './api.js';
import { tienda, avisar, avisarError, confirmar } from './tienda.js';
import { retrasar, clonar, copiarTexto, textoPlano } from './util.js';
import { nuevoElemento, nuevoBloque } from './modeloed.js';

const { inject } = Vue;

// ---------------------------------------------------------------- utilidades
const NO_TEXTO = new Set(['id', 'tipo', 'archivo', 'estilo', 'forma', 'ancla']);
const RE_CITA = /\[(@[^\]\n]+)\]/g;

// Aplica fn(texto) a los textos del documento que tienen citas
function recorrerTextos(m, fn) {
  const visitar = (o) => {
    if (Array.isArray(o)) { o.forEach((x, i) => { if (typeof x === 'string') { if (x.includes('[@')) o[i] = fn(x); } else visitar(x); }); return; }
    if (o && typeof o === 'object') {
      for (const k of Object.keys(o)) {
        if (NO_TEXTO.has(k)) continue;
        const v = o[k];
        if (typeof v === 'string') { if (v.includes('[@')) o[k] = fn(v); } else visitar(v);
      }
    }
  };
  [m.cabecera, m.pie, ...(m.filas || []), ...(m.capas || [])].forEach(visitar);
}

const claveDe = (parte) => parte.trim().replace(/^@/, '').split(',')[0].trim();

function renombrarCitas(m, viejo, nuevo) {
  recorrerTextos(m, (t) => t.replace(RE_CITA, (todo, dentro) => '[' + dentro.split(';').map((p) => (
    claveDe(p) === viejo ? p.replace('@' + viejo, '@' + nuevo) : p)).join(';') + ']'));
}

const sinAcentos = (t) => String(t || '').normalize('NFKD').replace(/\p{M}/gu, '');

export function claveSugerida(ref, usadas) {
  const a = (ref.autores || [])[0];
  const base0 = a ? (a.literal || a.apellido || a.nombre || '') : String(ref.titulo || 'ref').split(/\s+/)[0];
  const base = sinAcentos(base0).toLowerCase().replace(/[^a-z]/g, '').slice(0, 20) || 'ref';
  const anio = String(ref.anio || '').replace(/\D/g, '').slice(0, 4);
  const clave = base + anio;
  if (!usadas.has(clave)) return clave;
  for (const l of 'abcdefghijklmnopqrstuvwxyz') if (!usadas.has(clave + l)) return clave + l;
  let n = 2; while (usadas.has(`${clave}-${n}`)) n++;
  return `${clave}-${n}`;
}

function resumen(ref) {
  const a = (ref.autores || [])[0];
  const quien = a ? (a.literal || a.apellido || a.nombre) : '';
  const mas = (ref.autores || []).length > 2 ? ' et al.' : (ref.autores || []).length === 2 ? ` y ${ref.autores[1].literal || ref.autores[1].apellido || ''}` : '';
  return [quien && quien + mas, ref.anio].filter(Boolean).join(', ');
}

const TITULO_LISTA = { es: 'Referencias', en: 'References', pt: 'Referências', fr: 'Références', de: 'Literatur', it: 'Bibliografia' };

// Escribe en un <input> o <textarea> donde estaba el cursor y avisa a v-model
// con un evento «input», así sirve para cualquier campo del inspector.
function escribir(el, valor, cursor) {
  el.value = valor;
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.focus();
  try { el.setSelectionRange(cursor, cursor); } catch { /* algunos tipos de entrada no tienen cursor */ }
}

export function insertarEnEntrada(el, texto) {
  if (!el) return false;
  const v = el.value || '';
  const a = typeof el.selectionStart === 'number' ? el.selectionStart : v.length;
  const b = typeof el.selectionEnd === 'number' ? el.selectionEnd : v.length;
  const antes = v.slice(0, a), despues = v.slice(b);
  const espacio = antes && !/[\s([]$/.test(antes) ? ' ' : '';
  escribir(el, antes + espacio + texto + despues, (antes + espacio + texto).length);
  return true;
}

// Inserta [@clave]; justo detrás de otra cita las junta: [@a] → [@a; @b]
export function insertarCita(el, clave) {
  if (!el) return false;
  const v = el.value || '';
  const a = typeof el.selectionStart === 'number' ? el.selectionStart : v.length;
  const b = typeof el.selectionEnd === 'number' ? el.selectionEnd : v.length;
  const antes = v.slice(0, a), despues = v.slice(b);
  const previa = a === b ? /\[(@[^\]\n]+)\]\s*$/.exec(antes) : null;
  if (previa) {
    const dentro = previa[1];
    if (dentro.split(';').some((p) => claveDe(p) === clave)) { el.focus(); return true; }
    const nuevo = antes.slice(0, previa.index) + `[${dentro}; @${clave}]`;
    escribir(el, nuevo + despues, nuevo.length);
    return true;
  }
  return insertarEnEntrada(el, `[@${clave}]`);
}

// ---------------------------------------------------------------- editor de personas (autores, editores)
const EditorPersonas = {
  name: 'editor-personas',
  props: { lista: Array, etiqueta: String },
  methods: {
    agregar() { this.lista.push({ apellido: '', nombre: '' }); },
    quitar(i) { this.lista.splice(i, 1); },
    alternar(p) {
      if ('literal' in p) { const t = p.literal; delete p.literal; p.apellido = t; p.nombre = ''; }
      else { p.literal = [p.nombre, p.apellido].filter(Boolean).join(' '); delete p.apellido; delete p.nombre; }
    },
    subir(i) { if (i > 0) { const [x] = this.lista.splice(i, 1); this.lista.splice(i - 1, 0, x); } },
    pegar(ev, i) {
      const t = (ev.clipboardData || window.clipboardData).getData('text');
      if (!t || !/;|\n| and | y /.test(t)) return;
      ev.preventDefault();
      const nombres = t.split(/;|\n| and | y /).map((x) => x.trim()).filter(Boolean);
      const personas = nombres.map((n) => {
        if (n.includes(',')) { const [ap, no] = n.split(','); return { apellido: ap.trim(), nombre: (no || '').trim() }; }
        const partes = n.split(/\s+/);
        return { apellido: partes.pop(), nombre: partes.join(' ') };
      });
      this.lista.splice(i, 1, ...personas);
    },
  },
  template: `
    <div class="campo">
      <span class="etiqueta">{{ etiqueta }}</span>
      <div class="personas">
        <div v-for="(p, i) in lista" :key="i" class="persona" :class="{organizacion: 'literal' in p}">
          <template v-if="'literal' in p">
            <input class="entrada" v-model="p.literal" placeholder="Organización (p. ej. World Health Organization)" :aria-label="'Organización ' + (i + 1)">
          </template>
          <template v-else>
            <input class="entrada" v-model="p.apellido" placeholder="Apellidos" :aria-label="'Apellidos ' + (i + 1)" @paste="pegar($event, i)">
            <input class="entrada" v-model="p.nombre" placeholder="Nombre" :aria-label="'Nombre ' + (i + 1)">
          </template>
          <button type="button" class="btn icono pequeno fantasma" @click="alternar(p)" :title="'literal' in p ? 'Es una organización. Pulsa si es una persona' : 'Es una persona. Pulsa si es una organización (OMS, un consorcio…)'" :aria-label="'literal' in p ? 'Cambiar a persona' : 'Cambiar a organización'"><icono :n="'literal' in p ? 'edificio' : 'persona'"/></button>
          <button type="button" class="btn icono pequeno fantasma" @click="subir(i)" :disabled="i === 0" title="Subir" aria-label="Subir"><icono n="arriba"/></button>
          <button type="button" class="btn icono pequeno fantasma" @click="quitar(i)" title="Quitar" aria-label="Quitar"><icono n="cerrar"/></button>
        </div>
        <button type="button" class="btn pequeno" style="justify-self:start" @click="agregar"><icono n="mas"/>Añadir</button>
        <span class="ayuda">Puedes pegar varios nombres separados por punto y coma («García, Ana; López, Beatriz»).</span>
      </div>
    </div>`,
};

// ---------------------------------------------------------------- formulario de una referencia
export const DialogoReferencia = {
  name: 'dialogo-referencia',
  components: { EditorPersonas },
  props: { inicial: Object, usadas: Object, estilo: String, idioma: String, nueva: Boolean },
  emits: ['guardar', 'cerrar'],
  data() {
    const r = clonar(this.inicial || {});
    r.autores = Array.isArray(r.autores) && r.autores.length ? r.autores : [{ apellido: '', nombre: '' }];
    r.editores = Array.isArray(r.editores) ? r.editores : [];
    return { r, vista: '', claveTocada: !this.nueva, buscandoDoi: false };
  },
  computed: {
    cat() { return tienda.catalogo.bibliografia; },
    tipos() { return Object.entries(this.cat.tipos).map(([k, v]) => ({ valor: k, texto: v })); },
    campos() { return (this.cat.campos[this.r.tipo] || []).filter((c) => c !== 'editores'); },
    conEditores() { return (this.cat.campos[this.r.tipo] || []).includes('editores'); },
    claveValida() { return /^[A-Za-z0-9_:.-]+$/.test(this.r.clave || '') && !this.usadas.has(this.r.clave); },
    nombreEstilo() { return this.cat.estilos[this.estilo] ? this.cat.estilos[this.estilo].nombre : this.estilo; },
    limpia() {
      const r = clonar(this.r);
      r.autores = (r.autores || []).filter((a) => (a.literal || a.apellido || a.nombre || '').trim());
      r.editores = (r.editores || []).filter((a) => (a.literal || a.apellido || a.nombre || '').trim());
      return r;
    },
  },
  watch: {
    r: { deep: true, handler() { this.sugerirClave(); this.previa(); } },
  },
  methods: {
    etiqueta(c) { return this.cat.etiquetas[c] || c; },
    sugerirClave() { if (!this.claveTocada) this.r.clave = claveSugerida(this.limpia, this.usadas); },
    async completarDoi() {
      if (!this.r.doi) return;
      this.buscandoDoi = true;
      try {
        const d = await api(`api/bibliografia/doi?doi=${encodeURIComponent(this.r.doi)}`);
        const clave = this.r.clave;
        Object.assign(this.r, d.referencia);
        if (!this.r.autores || !this.r.autores.length) this.r.autores = [{ apellido: '', nombre: '' }];
        if (!Array.isArray(this.r.editores)) this.r.editores = [];
        if (this.claveTocada) this.r.clave = clave;
        avisar('Datos completados desde doi.org');
      } catch (e) { avisarError(e); } finally { this.buscandoDoi = false; }
    },
    guardar() {
      if (!this.r.titulo || !String(this.r.titulo).trim()) { avisar('Escribe al menos el título.', { tipo: 'error' }); return; }
      if (!this.claveValida) { avisar('La clave debe ser única y sin espacios (letras, números, : . - _).', { tipo: 'error' }); return; }
      this.$emit('guardar', this.limpia);
    },
  },
  created() {
    this.previa = retrasar(async () => {
      try {
        const r = await post('api/bibliografia/formatear', { estilo: this.estilo, idioma: this.idioma, referencias: [{ ...this.limpia, clave: this.r.clave || 'x' }] });
        this.vista = r.entradas[0] ? `${r.entradas[0].etiqueta ? `<b>${r.entradas[0].etiqueta}</b> ` : ''}${r.entradas[0].html}` : '';
      } catch { /* sin vista previa */ }
    }, 250);
    this.sugerirClave();
    this.previa();
  },
  mounted() { const p = this.$el.querySelector('input[placeholder="Apellidos"]'); if (p && this.nueva) p.focus(); },
  template: `
  <div class="fondo-dialogo" @mousedown.self="$emit('cerrar')" @keydown.esc="$emit('cerrar')">
    <div class="dialogo medio" role="dialog" aria-modal="true" aria-labelledby="tit-ref">
      <header><div style="flex:1"><h2 id="tit-ref">{{ nueva ? 'Nueva referencia' : 'Editar la referencia' }}</h2>
        <p>Rellena lo que tengas: el estilo se encarga del orden, la puntuación y las cursivas.</p></div>
        <button class="btn icono fantasma" @click="$emit('cerrar')" aria-label="Cerrar"><icono n="cerrar"/></button></header>
      <div class="cuerpo">
        <div class="fila-campos">
          <label class="campo"><span class="etiqueta">Tipo</span>
            <select class="entrada" v-model="r.tipo"><option v-for="t in tipos" :key="t.valor" :value="t.valor">{{ t.texto }}</option></select></label>
          <label class="campo"><span class="etiqueta">Clave para citar</span>
            <input class="entrada codigo" :class="{invalida: !claveValida}" v-model="r.clave" @input="claveTocada = true" spellcheck="false">
            <span class="ayuda">En el texto: <code>[@{{ r.clave || 'clave' }}]</code></span></label>
        </div>
        <editor-personas :lista="r.autores" etiqueta="Autores (en orden)"/>
        <div class="fila-campos">
          <label class="campo"><span class="etiqueta">Año</span><input class="entrada" v-model="r.anio" placeholder="2024, en prensa…"></label>
          <label class="campo" v-if="campos.includes('doi')"><span class="etiqueta">DOI</span>
            <span style="display:flex;gap:6px"><input class="entrada codigo" v-model="r.doi" placeholder="10.1038/…" spellcheck="false">
            <button type="button" class="btn" @click="completarDoi" :disabled="!r.doi || buscandoDoi" title="Completar los datos desde doi.org (necesita internet)">{{ buscandoDoi ? 'Buscando…' : 'Completar' }}</button></span></label>
        </div>
        <label class="campo"><span class="etiqueta">Título</span><textarea class="entrada" rows="2" v-model="r.titulo"></textarea></label>
        <div class="fila-campos">
          <template v-for="c in campos" :key="c">
            <label class="campo" v-if="c !== 'doi'" :style="c === 'url' || c === 'revista' || c === 'nota' ? 'grid-column:1/-1' : ''"><span class="etiqueta">{{ etiqueta(c) }}</span>
              <input class="entrada" :class="{codigo: c === 'url'}" v-model="r[c]"></label>
          </template>
        </div>
        <editor-personas v-if="conEditores" :lista="r.editores" etiqueta="Editores del libro (opcional)"/>
      </div>
      <footer class="con-previa">
        <div class="previa-ref" aria-live="polite"><span class="etiqueta-previa">Así queda en {{ nombreEstilo }}</span><span v-html="vista || '…'"></span></div>
        <div class="botones-pie">
          <button class="btn" @click="$emit('cerrar')">Cancelar</button>
          <button class="btn primario" @click="guardar">{{ nueva ? 'Agregar la referencia' : 'Guardar los cambios' }}</button>
        </div>
      </footer>
    </div>
  </div>`,
};

// ---------------------------------------------------------------- importar (archivo, texto o DOI)
export const DialogoImportarRefs = {
  name: 'dialogo-importar-refs',
  props: { existentes: Array, modo: { type: String, default: 'archivo' } },
  emits: ['agregar', 'cerrar'],
  data() { return { pestana: this.modo, texto: '', dois: '', encontradas: [], errores: [], elegidas: new Set(), trabajando: false, progreso: '', encima: false }; },
  computed: {
    doisExistentes() { return new Set((this.existentes || []).map((r) => String(r.doi || '').toLowerCase()).filter(Boolean)); },
  },
  methods: {
    repetida(r) { return r.doi && this.doisExistentes.has(String(r.doi).toLowerCase()); },
    poner(refs, errores) {
      this.encontradas = refs;
      this.errores = errores || [];
      this.elegidas = new Set(refs.map((_, i) => i).filter((i) => !this.repetida(refs[i])));
      if (!refs.length && !this.errores.length) this.errores = ['No se encontró ninguna referencia en ese texto.'];
    },
    async leerTexto() {
      this.trabajando = true;
      try { const r = await post('api/bibliografia/importar', { texto: this.texto }); this.poner(r.referencias, r.errores); }
      catch (e) { avisarError(e); } finally { this.trabajando = false; }
    },
    async leerArchivo(f) {
      if (!f) return;
      this.trabajando = true;
      try { const r = await subir('api/bibliografia/importar', { archivo: f }); this.poner(r.referencias, r.errores); }
      catch (e) { avisarError(e); } finally { this.trabajando = false; }
    },
    soltar(ev) { this.encima = false; const f = ev.dataTransfer.files[0]; if (f) this.leerArchivo(f); },
    async buscarDois() {
      const lista = [...new Set(this.dois.split(/[\s,;]+/).map((x) => x.trim()).filter(Boolean))];
      if (!lista.length) return;
      this.trabajando = true;
      const refs = [], errores = [];
      for (const [i, d] of lista.entries()) {
        this.progreso = `${i + 1} de ${lista.length}`;
        try { const r = await api(`api/bibliografia/doi?doi=${encodeURIComponent(d)}`); refs.push(r.referencia); }
        catch (e) { errores.push(`${d}: ${e.message}`); }
      }
      this.progreso = '';
      this.trabajando = false;
      this.poner(refs, errores);
    },
    alternar(i) { if (this.elegidas.has(i)) this.elegidas.delete(i); else this.elegidas.add(i); },
    agregar() { this.$emit('agregar', this.encontradas.filter((_, i) => this.elegidas.has(i))); },
    resumen,
  },
  template: `
  <div class="fondo-dialogo" @mousedown.self="$emit('cerrar')" @keydown.esc="$emit('cerrar')">
    <div class="dialogo medio" role="dialog" aria-modal="true" aria-labelledby="tit-imp">
      <header><div style="flex:1"><h2 id="tit-imp">Importar referencias</h2>
        <p>Desde tu gestor (Zotero, Mendeley, EndNote…) exporta en BibTeX, RIS o CSL-JSON, o búscalas por DOI.</p></div>
        <button class="btn icono fantasma" @click="$emit('cerrar')" aria-label="Cerrar"><icono n="cerrar"/></button></header>
      <div class="cuerpo">
        <div class="segmentos" role="tablist">
          <button type="button" role="tab" :aria-selected="pestana === 'archivo'" :class="{activo: pestana === 'archivo'}" @click="pestana = 'archivo'">Archivo o texto</button>
          <button type="button" role="tab" :aria-selected="pestana === 'doi'" :class="{activo: pestana === 'doi'}" @click="pestana = 'doi'">Por DOI</button>
        </div>
        <template v-if="pestana === 'archivo'">
          <div class="zona-soltar" style="margin:0" :class="{encima}" @dragover.prevent="encima = true" @dragleave="encima = false" @drop.prevent="soltar">
            <input ref="arch" type="file" accept=".bib,.ris,.json,.txt,.nbib" hidden @change="leerArchivo($event.target.files[0]); $event.target.value = ''">
            <button class="btn" @click="$refs.arch.click()" :disabled="trabajando"><icono n="subir"/>Elegir un archivo .bib, .ris o .json</button>
            <span>o arrástralo aquí. También puedes pegar el texto debajo.</span>
          </div>
          <textarea class="entrada codigo" rows="6" v-model="texto" aria-label="Texto en BibTeX, RIS o CSL-JSON" placeholder="@article{garcia2020, author = {García, Ana and López, Beatriz}, title = {…}, journal = {…}, year = {2020}}"></textarea>
          <button class="btn" style="justify-self:start" @click="leerTexto" :disabled="!texto.trim() || trabajando">{{ trabajando ? 'Leyendo…' : 'Leer el texto' }}</button>
        </template>
        <template v-else>
          <textarea class="entrada codigo" rows="4" v-model="dois" aria-label="DOI, uno por línea" placeholder="10.1093/nar/gkab335&#10;10.1038/s41586-020-2649-2"></textarea>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <button class="btn" @click="buscarDois" :disabled="!dois.trim() || trabajando">{{ trabajando ? 'Buscando ' + progreso + '…' : 'Buscar en doi.org' }}</button>
            <span class="ayuda">Uno por línea; sirven también los enlaces https://doi.org/… Necesita conexión a internet.</span>
          </div>
        </template>
        <div v-if="errores.length" class="mensaje error" style="grid-template-columns:1fr"><div v-for="(e, i) in errores" :key="i">{{ e }}</div></div>
        <div v-if="encontradas.length" class="lista-importar">
          <label v-for="(r, i) in encontradas" :key="i" class="fila-importar">
            <input type="checkbox" :checked="elegidas.has(i)" @change="alternar(i)">
            <span><strong>{{ r.titulo || 'Sin título' }}</strong><br><span class="ayuda">{{ resumen(r) }}<template v-if="repetida(r)">. Ya está en el proyecto</template></span></span>
          </label>
        </div>
      </div>
      <footer>
        <button class="btn" @click="$emit('cerrar')">Cancelar</button>
        <button class="btn primario" :disabled="!elegidas.size" @click="agregar">Agregar {{ elegidas.size || '' }} {{ elegidas.size === 1 ? 'referencia' : 'referencias' }}</button>
      </footer>
    </div>
  </div>`,
};

// ---------------------------------------------------------------- panel Referencias
export const PanelReferencias = {
  name: 'panel-referencias',
  components: { DialogoReferencia, DialogoImportarRefs },
  setup() { return { ed: inject('ed') }; },
  data: () => ({
    vista: { entradas: [], citas: {}, desconocidas: [], hay_lista: false, incluir: 'citadas', ejemplo: '' },
    cargada: false, buscar: '', editando: null, importando: null, activo: true,
  }),
  computed: {
    m() { return this.ed.modelo; },
    bib() { return this.m.bibliografia; },
    cat() { return tienda.catalogo.bibliografia; },
    idioma() { return this.m.idioma || 'es'; },
    estilos() { return Object.entries(this.cat.estilos).map(([k, v]) => ({ valor: k, texto: v.nombre })); },
    citas() { return this.vista.citas || {}; },
    usadas() { return new Set(this.bib.referencias.map((r) => r.clave)); },
    porClave() { return Object.fromEntries(this.bib.referencias.map((r) => [r.clave, r])); },
    filtradas() {
      const q = sinAcentos(this.buscar.trim().toLowerCase());
      // solo las que siguen en el proyecto (la vista del servidor llega con un poco de retraso)
      return this.vista.entradas.filter((e) => this.porClave[e.clave] && (!q || sinAcentos(`${e.texto} ${e.clave}`.toLowerCase()).includes(q)));
    },
    enLista() { return this.filtradas.filter((e) => e.en_lista); },
    fuera() { return this.filtradas.filter((e) => !e.en_lista); },
    nuevas() {                      // agregadas hace un momento, antes de que llegue la vista
      const vistas = new Set(this.vista.entradas.map((e) => e.clave));
      return this.bib.referencias.filter((r) => !vistas.has(r.clave));
    },
  },
  watch: {
    m: { deep: true, handler() { if (this.activo) this.actualizarPronto(); } },
  },
  methods: {
    async actualizar() {
      try {
        this.vista = await post('api/bibliografia/vista', { modelo: this.m });
        this.cargada = true;
      } catch (e) { avisarError(e); }
    },
    nueva() { this.editando = { ref: { tipo: 'articulo', autores: [{ apellido: '', nombre: '' }], titulo: '', anio: '' }, nueva: true }; },
    editar(clave) { if (this.porClave[clave]) this.editando = { ref: this.porClave[clave], nueva: false, original: clave }; },
    usadasSin(clave) { const s = new Set(this.usadas); s.delete(clave); return s; },
    guardar(ref) {
      const lista = this.bib.referencias;
      if (this.editando.nueva) {
        lista.push(ref);
        avisar(`Referencia agregada. Cítala con [@${ref.clave}]`);
      } else {
        const i = lista.findIndex((r) => r.clave === this.editando.original);
        if (i >= 0) lista.splice(i, 1, ref);
        if (ref.clave !== this.editando.original) renombrarCitas(this.m, this.editando.original, ref.clave);
      }
      this.editando = null;
    },
    async quitar(clave) {
      const n = this.citas[clave] || 0;
      const ok = await confirmar({
        titulo: '¿Quitar la referencia?',
        texto: n ? `Está citada ${n} ${n === 1 ? 'vez' : 'veces'} en el documento: esas citas saldrán en rojo como [?${clave}] hasta que las cambies.` : 'Se quita de la lista de este proyecto.',
        aceptar: 'Quitar', peligro: true,
      });
      if (!ok) return;
      const i = this.bib.referencias.findIndex((r) => r.clave === clave);
      if (i >= 0) this.bib.referencias.splice(i, 1);
      avisar('Referencia quitada', { accion: { texto: 'Deshacer', fn: () => this.ed.deshacer() } });
    },
    agregarVarias(refs) {
      const usadas = new Set(this.usadas);
      for (const r of refs) {
        const ref = clonar(r);
        if (!ref.clave || usadas.has(ref.clave) || !/^[A-Za-z0-9_:.-]+$/.test(ref.clave)) ref.clave = claveSugerida(ref, usadas);
        usadas.add(ref.clave);
        this.bib.referencias.push(ref);
      }
      this.importando = null;
      avisar(refs.length === 1 ? 'Referencia agregada' : `${refs.length} referencias agregadas`);
    },
    async copiar(clave) {
      try { await copiarTexto(`[@${clave}]`); avisar(`Copiado: [@${clave}]. Pégalo en cualquier texto del documento.`); }
      catch { avisar(`Escribe [@${clave}] en el texto donde quieras citarla.`); }
    },
    citar(clave) {
      if (this.ed.insertarCita && this.ed.insertarCita(clave)) return;
      this.copiar(clave);
    },
    // Dónde poner la lista: junto a una lista escrita a mano (que se oculta), en una
    // caja que ya se llame «Referencias», en la caja seleccionada o en una caja nueva.
    agregarLista() {
      if (this.vista.hay_lista) { avisar('El documento ya tiene la lista de referencias.'); return; }
      const filas = this.m.filas || [];
      if (!filas.length) { avisar('Agrega primero una fila al documento.', { tipo: 'error' }); return; }
      const e = nuevoElemento('bibliografia');
      const cajas = filas.flatMap((f) => (f.visible === false ? [] : f.columnas.flatMap((c) => c.bloques.map((b) => ({ b, c })))));
      let destino = null, tras = -1, manual = null;
      for (const { b, c } of cajas) {
        const i = b.elementos.findIndex((x) => x.tipo === 'txtReferencias' && x.visible !== false);
        if (i >= 0) { destino = { b, c }; tras = i; manual = b.elementos[i]; break; }
      }
      if (!destino) destino = cajas.find(({ b }) => /referenc|bibliogr|literat|cita/i.test(textoPlano(b.titulo || ''))) || null;
      const sel = this.ed.indice.get(this.ed.sel);
      if (!destino && sel && sel.tipo === 'bloque') destino = { b: sel.obj, c: sel.columna };
      if (!destino) {
        const cols = filas[filas.length - 1].columnas;
        const c = cols[cols.length - 1];
        const b = nuevoBloque(TITULO_LISTA[this.idioma] || 'Referencias', false);
        c.bloques.push(b);
        destino = { b, c };
      }
      if (tras >= 0) destino.b.elementos.splice(tras + 1, 0, e); else destino.b.elementos.push(e);
      if (manual) manual.visible = false;
      this.ed.abiertos.add(destino.c.id); this.ed.abiertos.add(destino.b.id);
      this.ed.seleccionar(e.id);
      const donde = textoPlano(destino.b.titulo || '') || 'la caja';
      avisar(manual ? `Lista agregada en «${donde}». La lista escrita a mano quedó oculta, no borrada.` : `Lista de referencias agregada en «${donde}»`,
        { ms: 6500, accion: { texto: 'Deshacer', fn: () => this.ed.deshacer() } });
    },
    async exportar() {
      try { await this.ed.guardarAhora(); } catch { return; }
      descargar(`api/proyectos/${this.ed.pid}/bibliografia.bib`);
    },
    textoCitas(clave) {
      const n = this.citas[clave];
      return n ? (n === 1 ? 'citada 1 vez' : `citada ${n} veces`) : 'sin citar';
    },
  },
  created() { this.actualizarPronto = retrasar(() => this.actualizar(), 300); this.actualizar(); },
  activated() { this.activo = true; this.actualizar(); },
  deactivated() { this.activo = false; },
  template: `
  <div class="panel-refs">
    <div class="cabeza-refs">
      <label class="campo"><span class="etiqueta">Estilo de las referencias</span>
        <select class="entrada" v-model="bib.estilo"><option v-for="e in estilos" :key="e.valor" :value="e.valor">{{ e.texto }}</option></select>
        <span class="ayuda" v-if="vista.ejemplo">Así se cita: {{ vista.ejemplo }}. Escribe <code>[@clave]</code> en cualquier texto, o usa el botón de cita de cada campo.</span></label>
      <div class="acciones-refs">
        <button class="btn primario" @click="nueva"><icono n="mas"/>Nueva</button>
        <button class="btn" @click="importando = 'archivo'" title="Desde BibTeX, RIS o CSL-JSON (Zotero, Mendeley, EndNote…)"><icono n="importar"/>Importar</button>
        <button class="btn" @click="importando = 'doi'" title="Buscar por DOI en doi.org">DOI</button>
        <button class="btn icono" @click="exportar" title="Descargar las referencias en BibTeX (.bib)" aria-label="Descargar en BibTeX" :disabled="!bib.referencias.length"><icono n="descargar"/></button>
      </div>
      <input v-if="bib.referencias.length > 4" class="entrada" type="search" v-model="buscar" placeholder="Buscar referencia" aria-label="Buscar referencia">
    </div>

    <div v-if="vista.desconocidas.length" class="mensaje error" style="margin:0 10px;grid-template-columns:18px 1fr">
      <span class="icono-msg"><icono n="alerta"/></span>
      <span>Citas sin referencia (salen en rojo en el documento): <code v-for="k in vista.desconocidas" :key="k" style="margin-right:6px">[@{{ k }}]</code></span>
    </div>

    <div v-if="!bib.referencias.length" class="vacio" style="margin:0 10px">
      <strong>Todavía no hay referencias.</strong>
      <span>Agrégalas a mano, impórtalas de tu gestor (BibTeX, RIS) o búscalas por DOI. Luego cítalas con <code>[@clave]</code> y pon la lista en el documento.</span>
    </div>
    <template v-else>
      <div v-if="!vista.hay_lista && cargada" class="aviso-lista">
        <span>El documento todavía no muestra la lista.</span>
        <button class="btn pequeno" @click="agregarLista"><icono n="libro"/>Agregar la lista al documento</button>
      </div>
      <p v-if="enLista.length && vista.hay_lista" class="subtitulo-refs">En la lista del documento</p>
      <ol class="lista-refs" v-if="enLista.length">
        <li v-for="e in enLista" :key="e.clave" class="ref">
          <div class="texto-ref"><span class="etiqueta-ref" v-if="e.etiqueta">{{ e.etiqueta }}</span><span v-html="e.html"></span></div>
          <div class="pie-ref">
            <code class="clave-ref" :title="'[@' + e.clave + ']'">[@{{ e.clave }}]</code>
            <span class="ayuda">{{ textoCitas(e.clave) }}</span>
            <span class="acciones-ref">
              <button class="btn icono pequeno fantasma" @click="citar(e.clave)" title="Citar en el último texto que editaste (o copiar la cita)" aria-label="Citar"><icono n="cita"/></button>
              <button class="btn icono pequeno fantasma" @click="editar(e.clave)" title="Editar" aria-label="Editar"><icono n="lapiz"/></button>
              <button class="btn icono pequeno fantasma" @click="quitar(e.clave)" title="Quitar" aria-label="Quitar"><icono n="basura"/></button>
            </span>
          </div>
        </li>
      </ol>
      <template v-if="fuera.length || nuevas.length">
        <p class="subtitulo-refs">{{ vista.incluir === 'todas' ? 'Sin citar' : 'Sin citar: no salen en el documento hasta que las cites' }}</p>
        <ol class="lista-refs">
          <li v-for="e in fuera" :key="e.clave" class="ref sin-citar">
            <div class="texto-ref"><span v-html="e.html"></span></div>
            <div class="pie-ref">
              <code class="clave-ref" :title="'[@' + e.clave + ']'">[@{{ e.clave }}]</code>
              <span class="acciones-ref">
                <button class="btn icono pequeno fantasma" @click="citar(e.clave)" title="Citar en el último texto que editaste (o copiar la cita)" aria-label="Citar"><icono n="cita"/></button>
                <button class="btn icono pequeno fantasma" @click="editar(e.clave)" title="Editar" aria-label="Editar"><icono n="lapiz"/></button>
                <button class="btn icono pequeno fantasma" @click="quitar(e.clave)" title="Quitar" aria-label="Quitar"><icono n="basura"/></button>
              </span>
            </div>
          </li>
          <li v-for="r in nuevas" :key="'n-' + r.clave" class="ref sin-citar"><div class="texto-ref">{{ r.titulo }}</div></li>
        </ol>
      </template>
      <p v-if="buscar && !filtradas.length" class="ayuda" style="padding:0 10px">Ninguna referencia coincide con «{{ buscar }}».</p>
    </template>

    <dialogo-referencia v-if="editando" :inicial="editando.ref" :nueva="editando.nueva" :usadas="usadasSin(editando.original)"
      :estilo="bib.estilo" :idioma="idioma" @guardar="guardar" @cerrar="editando = null"/>
    <dialogo-importar-refs v-if="importando" :modo="importando" :existentes="bib.referencias" @agregar="agregarVarias" @cerrar="importando = null"/>
  </div>`,
};

// ---------------------------------------------------------------- botón «Citar» de los campos de texto
export const BotonCitar = {
  name: 'boton-citar',
  emits: ['insertar'],
  setup() { return { ed: inject('ed', null) }; },
  data: () => ({ abierto: false, q: '' }),
  computed: {
    refs() { return (this.ed && this.ed.modelo && this.ed.modelo.bibliografia && this.ed.modelo.bibliografia.referencias) || []; },
    lista() {
      const q = sinAcentos(this.q.trim().toLowerCase());
      return this.refs.filter((r) => !q || sinAcentos(`${r.clave} ${resumen(r)} ${r.titulo || ''}`.toLowerCase()).includes(q)).slice(0, 40);
    },
  },
  methods: {
    resumen,
    abrir() {
      this.abierto = !this.abierto;
      if (this.abierto) this.$nextTick(() => { const i = this.$el.querySelector('.menu-citas input'); if (i) i.focus(); });
    },
    elegir(r) { this.$emit('insertar', r.clave); this.abierto = false; this.q = ''; },
    cerrar(ev) { if (this.abierto && !this.$el.contains(ev.target)) this.abierto = false; },
  },
  mounted() { document.addEventListener('mousedown', this.cerrar); },
  beforeUnmount() { document.removeEventListener('mousedown', this.cerrar); },
  template: `
    <span v-if="refs.length" class="boton-citar menu-contenedor" @keydown.esc.stop="abierto = false">
      <button type="button" class="boton-ayuda" :class="{activo: abierto}" @mousedown.prevent @click="abrir" title="Citar una referencia" aria-label="Citar una referencia" :aria-expanded="abierto"><icono n="cita"/></button>
      <div class="menu menu-citas" v-if="abierto">
        <input class="entrada" type="search" v-model="q" placeholder="Buscar por autor, año o título" aria-label="Buscar referencia" @keydown.enter.prevent="lista[0] && elegir(lista[0])">
        <button v-for="r in lista" :key="r.clave" type="button" @mousedown.prevent @click="elegir(r)">
          <span style="display:grid;gap:1px;min-width:0"><strong>{{ resumen(r) || r.clave }}</strong>
          <span class="ayuda" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ r.titulo }}</span></span>
        </button>
        <p class="nota" v-if="!lista.length">Ninguna coincide.</p>
      </div>
    </span>`,
};
