// Campos del inspector. Cada campo edita obj[clave] directamente (el editor
// vigila el modelo y guarda solo).
import { tienda } from './tienda.js';
import { esDimension, nombreArchivo, tamano } from './util.js';
import { api, subir } from './api.js';
import { avisarError, avisar } from './tienda.js';
import { BotonCitar, insertarCita } from './referencias.js';

const { inject } = Vue;

let n = 0;
const uid = () => `campo-${++n}`;

const AYUDA_FORMATO = `
  <div class="ayuda-formato">
    <span><code>**negrita**</code> <code>*cursiva*</code> <code>\`código\`</code></span>
    <span><code>^superíndice^</code> <code>~subíndice~</code> <code>$x^2$</code> (matemáticas)</span>
    <span><code>{{\\orden}}</code> LaTeX sin tocar; línea en blanco = párrafo nuevo</span>
    <span><code>[@clave]</code> cita una referencia (panel Referencias); <code>[@a; @b, p. 12]</code> varias</span>
  </div>`;

// Encabezado de un campo de texto: etiqueta, botón «Citar» (si el proyecto
// tiene referencias) y la ayuda de formato.
const CABEZA_TEXTO = `
      <div class="etiqueta"><label :for="id">{{ etiqueta }}</label>
        <span class="botones-campo" v-if="formato">
          <boton-citar @insertar="citar"/>
          <button type="button" class="boton-ayuda" :class="{activo: verAyuda}" @click="verAyuda = !verAyuda" title="Cómo dar formato al texto" aria-label="Cómo dar formato al texto">?</button>
        </span></div>`;

export const CTexto = {
  name: 'c-texto',
  components: { BotonCitar },
  props: { obj: Object, clave: String, etiqueta: String, ayuda: String, placeholder: String, mono: Boolean, formato: Boolean },
  data: () => ({ id: uid(), verAyuda: false }),
  methods: { citar(clave) { insertarCita(this.$refs.entrada, clave); } },
  template: `
    <div class="campo">${CABEZA_TEXTO}
      <input :id="id" ref="entrada" class="entrada" :class="{codigo: mono}" v-model="obj[clave]" :placeholder="placeholder" spellcheck="true">
      <div v-if="verAyuda" v-html="ayudaFormato"></div>
      <span v-if="ayuda" class="ayuda">{{ ayuda }}</span>
    </div>`,
  created() { this.ayudaFormato = AYUDA_FORMATO; },
};

export const CParrafo = {
  name: 'c-parrafo',
  components: { BotonCitar },
  props: { obj: Object, clave: String, etiqueta: String, ayuda: String, filas: { type: Number, default: 5 }, formato: { type: Boolean, default: true } },
  data: () => ({ id: uid(), verAyuda: false }),
  methods: { citar(clave) { insertarCita(this.$refs.entrada, clave); } },
  template: `
    <div class="campo">${CABEZA_TEXTO}
      <textarea :id="id" ref="entrada" class="entrada" :rows="filas" v-model="obj[clave]" spellcheck="true"></textarea>
      <div v-if="verAyuda" v-html="ayudaFormato"></div>
      <span v-if="ayuda" class="ayuda">{{ ayuda }}</span>
    </div>`,
  created() { this.ayudaFormato = AYUDA_FORMATO; },
};

export const CLatex = {
  name: 'c-latex',
  props: { obj: Object, clave: String, etiqueta: String, ayuda: String, filas: { type: Number, default: 4 } },
  data: () => ({ id: uid() }),
  template: `
    <div class="campo">
      <label class="etiqueta" :for="id">{{ etiqueta }}</label>
      <textarea :id="id" class="entrada codigo" :rows="filas" v-model="obj[clave]" spellcheck="false" autocapitalize="off"></textarea>
      <span v-if="ayuda" class="ayuda">{{ ayuda }}</span>
    </div>`,
};

export const CNumero = {
  name: 'c-numero',
  props: { obj: Object, clave: String, etiqueta: String, ayuda: String, min: Number, max: Number, paso: { type: Number, default: 0.1 } },
  data: () => ({ id: uid() }),
  computed: {
    valor: {
      get() { return this.obj[this.clave]; },
      set(v) { this.obj[this.clave] = v === '' || v === null ? '' : Number(v); },
    },
  },
  template: `
    <div class="campo">
      <label class="etiqueta" :for="id">{{ etiqueta }}</label>
      <input :id="id" class="entrada" type="number" :min="min" :max="max" :step="paso" v-model="valor">
      <span v-if="ayuda" class="ayuda">{{ ayuda }}</span>
    </div>`,
};

export const CDeslizador = {
  name: 'c-deslizador',
  props: { obj: Object, clave: String, etiqueta: String, ayuda: String, min: Number, max: Number, paso: { type: Number, default: 1 }, sufijo: String },
  data: () => ({ id: uid() }),
  computed: {
    valor: {
      get() { const v = this.obj[this.clave]; return v === '' || v == null ? this.min : Number(v); },
      set(v) { this.obj[this.clave] = Number(v); },
    },
  },
  template: `
    <div class="campo">
      <label class="etiqueta" :for="id">{{ etiqueta }}</label>
      <div class="deslizador">
        <input :id="id" type="range" :min="min" :max="max" :step="paso" v-model.number="valor">
        <input class="entrada" type="number" :min="min" :max="max" :step="paso" v-model.number="valor" :aria-label="etiqueta">
      </div>
      <span v-if="ayuda" class="ayuda">{{ ayuda }}</span>
    </div>`,
};

export const CSeleccion = {
  name: 'c-seleccion',
  props: { obj: Object, clave: String, etiqueta: String, ayuda: String, opciones: Array },
  data: () => ({ id: uid() }),
  computed: {
    lista() { return (this.opciones || []).map((o) => (typeof o === 'object' ? o : { valor: o, texto: o })); },
  },
  template: `
    <div class="campo">
      <label class="etiqueta" :for="id">{{ etiqueta }}</label>
      <select :id="id" class="entrada" v-model="obj[clave]">
        <option v-for="o in lista" :key="o.valor" :value="o.valor">{{ o.texto }}</option>
      </select>
      <span v-if="ayuda" class="ayuda">{{ ayuda }}</span>
    </div>`,
};

export const CSegmentos = {
  name: 'c-segmentos',
  props: { obj: Object, clave: String, etiqueta: String, ayuda: String, opciones: Array },
  computed: {
    lista() { return (this.opciones || []).map((o) => (typeof o === 'object' ? o : { valor: o, texto: o })); },
  },
  template: `
    <div class="campo">
      <span class="etiqueta">{{ etiqueta }}</span>
      <div class="segmentos" role="group" :aria-label="etiqueta">
        <button v-for="o in lista" :key="o.valor" type="button" :class="{activo: obj[clave] === o.valor}" :aria-pressed="obj[clave] === o.valor" @click="obj[clave] = o.valor">{{ o.texto }}</button>
      </div>
      <span v-if="ayuda" class="ayuda">{{ ayuda }}</span>
    </div>`,
};

export const CInterruptor = {
  name: 'c-interruptor',
  props: { obj: Object, clave: String, etiqueta: String, ayuda: String, defecto: { type: Boolean, default: false } },
  computed: {
    valor: {
      get() { const v = this.obj[this.clave]; return v === undefined || v === '' ? this.defecto : v === true || v === 'true'; },
      set(v) { this.obj[this.clave] = v; },
    },
  },
  template: `
    <div class="campo">
      <label class="interruptor"><span class="texto">{{ etiqueta }}</span>
        <input type="checkbox" v-model="valor"><span class="pista"></span></label>
      <span v-if="ayuda" class="ayuda">{{ ayuda }}</span>
    </div>`,
};

const NOMBRES_COLOR = [
  ['primario', 'Primario'], ['secundario', 'Secundario'], ['acento', 'Acento'], ['texto', 'Texto'],
  ['tenue', 'Texto tenue'], ['fondo_bloque', 'Fondo de las cajas'], ['fondo', 'Fondo del lienzo'],
  ['blanco', 'Blanco'], ['negro', 'Negro'],
];
export const CColor = {
  name: 'c-color',
  props: { obj: Object, clave: String, etiqueta: String, ayuda: String, vacio: { type: String, default: 'Por defecto' }, sinNombres: Boolean },
  setup() { return { ed: inject('ed', null) }; },
  data: () => ({ id: uid() }),
  computed: {
    valor() { return String(this.obj[this.clave] ?? ''); },
    colores() { return this.ed && this.ed.modelo ? this.ed.modelo.colores : null; },
    nombres() { return this.sinNombres ? [] : NOMBRES_COLOR; },
    hex() {
      const v = this.valor.replace('#', '');
      if (/^[0-9A-Fa-f]{6}$/.test(v)) return '#' + v;
      const base = v.split('!')[0];
      return '#' + (this.resolver(base) || 'ffffff');
    },
    valido() {
      const v = this.valor.trim();
      return !v || /^#?[0-9A-Fa-f]{6}$/.test(v) || /^[A-Za-z][A-Za-z0-9_]*(![0-9]{1,3}(![A-Za-z][A-Za-z0-9_]*)?)*$/.test(v);
    },
  },
  methods: {
    resolver(nombre) {
      if (nombre === 'blanco') return 'ffffff';
      if (nombre === 'negro') return '000000';
      return this.colores ? this.colores[nombre] : null;
    },
    fondoMuestra(nombre) { const h = this.resolver(nombre); return h ? '#' + h : 'transparent'; },
    poner(v) { this.obj[this.clave] = v; },
    desdeSelector(ev) { this.obj[this.clave] = ev.target.value.replace('#', '').toUpperCase(); },
  },
  template: `
    <div class="campo selector-color">
      <label class="etiqueta" :for="id">{{ etiqueta }}</label>
      <div class="muestras">
        <button type="button" class="muestra ninguno" :class="{activa: !valor}" :title="vacio" :aria-label="vacio" @click="poner('')"></button>
        <button v-for="[k, t] in nombres" :key="k" type="button" class="muestra" :class="{activa: valor === k}" :title="t" :aria-label="t"
                :style="{background: fondoMuestra(k)}" @click="poner(k)"></button>
      </div>
      <div class="color-hex">
        <input type="color" :value="hex" @input="desdeSelector" :aria-label="'Elegir ' + (etiqueta || 'color')">
        <input :id="id" class="entrada codigo" :class="{invalida: !valido}" :value="valor" @change="poner($event.target.value.trim())" placeholder="1F4E79, acento!20…">
      </div>
      <span v-if="ayuda" class="ayuda">{{ ayuda }}</span>
    </div>`,
};

export const CDimension = {
  name: 'c-dimension',
  props: { obj: Object, clave: String, etiqueta: String, ayuda: String, placeholder: String, numeroValido: Boolean },
  data: () => ({ id: uid() }),
  computed: {
    valido() {
      const v = String(this.obj[this.clave] ?? '').trim();
      return !v || esDimension(v) || (this.numeroValido && /^-?\d*\.?\d+$/.test(v));
    },
  },
  template: `
    <div class="campo">
      <label class="etiqueta" :for="id">{{ etiqueta }}</label>
      <input :id="id" class="entrada codigo" :class="{invalida: !valido}" v-model.trim="obj[clave]" :placeholder="placeholder" spellcheck="false">
      <span v-if="!valido" class="ayuda" style="color:var(--rojo)">Escribe un número con unidad: 12mm, 2cm, 1.5em, 30pt…</span>
      <span v-else-if="ayuda" class="ayuda">{{ ayuda }}</span>
    </div>`,
};

export const CAncla = {
  name: 'c-ancla',
  props: { obj: Object, clave: String, etiqueta: String },
  created() {
    this.anclas = [['north west', 'arriba a la izquierda'], ['north', 'arriba'], ['north east', 'arriba a la derecha'],
      ['west', 'izquierda'], ['center', 'centro'], ['east', 'derecha'],
      ['south west', 'abajo a la izquierda'], ['south', 'abajo'], ['south east', 'abajo a la derecha']];
  },
  template: `
    <div class="campo">
      <span class="etiqueta">{{ etiqueta }}</span>
      <div class="ancla-selector" role="group" :aria-label="etiqueta">
        <button v-for="[a, t] in anclas" :key="a" type="button" :title="t" :aria-label="t" :class="{activo: (obj[clave] || 'center') === a}" @click="obj[clave] = a"><i></i></button>
      </div>
    </div>`,
};

export const CLista = {
  name: 'c-lista',
  props: { obj: Object, clave: String, etiqueta: String, ayuda: String },
  data: () => ({ id: uid() }),
  computed: {
    texto: {
      get() { return (this.obj[this.clave] || []).join('\n'); },
      set(v) { this.obj[this.clave] = v.split('\n'); },
    },
  },
  methods: { limpiar() { this.obj[this.clave] = (this.obj[this.clave] || []).filter((x) => String(x).trim() !== ''); } },
  template: `
    <div class="campo">
      <label class="etiqueta" :for="id">{{ etiqueta }}</label>
      <textarea :id="id" class="entrada" rows="5" v-model="texto" @blur="limpiar"></textarea>
      <span class="ayuda">{{ ayuda || 'Un elemento por línea.' }}</span>
    </div>`,
};

export const CPares = {
  name: 'c-pares',
  props: { obj: Object, clave: String, etiqueta: String, nombres: { type: Array, default: () => ['Término', 'Descripción'] } },
  created() { if (!Array.isArray(this.obj[this.clave])) this.obj[this.clave] = []; },
  computed: { filas() { return this.obj[this.clave] || []; } },
  methods: {
    agregar() { this.filas.push(['', '']); },
    quitar(i) { this.filas.splice(i, 1); },
  },
  template: `
    <div class="campo">
      <span class="etiqueta">{{ etiqueta }}</span>
      <div class="lista-editable">
        <div v-for="(f, i) in filas" :key="i" class="renglon dos">
          <input class="entrada" v-model="f[0]" :placeholder="nombres[0]" :aria-label="nombres[0] + ' ' + (i + 1)">
          <textarea class="entrada" rows="1" style="min-height:32px" v-model="f[1]" :placeholder="nombres[1]" :aria-label="nombres[1] + ' ' + (i + 1)"></textarea>
          <button type="button" class="btn icono pequeno fantasma" @click="quitar(i)" aria-label="Quitar"><icono n="cerrar"/></button>
        </div>
        <button type="button" class="btn pequeno" style="justify-self:start" @click="agregar"><icono n="mas"/>Añadir</button>
      </div>
    </div>`,
};

export const CFlechas = {
  name: 'c-flechas',
  props: { obj: Object, clave: String, etiqueta: String },
  created() { if (!Array.isArray(this.obj[this.clave])) this.obj[this.clave] = []; },
  computed: { filas() { return this.obj[this.clave] || []; } },
  methods: {
    agregar() { this.filas.push([0.2, 0.8, 0.45, 0.5, 'etiqueta']); },
    quitar(i) { this.filas.splice(i, 1); },
    num(f, k, v) { f[k] = Math.min(1, Math.max(0, Number(v) || 0)); },
  },
  template: `
    <div class="campo">
      <span class="etiqueta">{{ etiqueta }}</span>
      <span class="ayuda">Desde la etiqueta (x0, y0) hasta el punto señalado (x1, y1). 0 = izquierda o arriba, 1 = derecha o abajo.</span>
      <div class="lista-editable">
        <div v-for="(f, i) in filas" :key="i" class="renglon cinco">
          <input v-for="k in 4" :key="k" class="entrada" type="number" min="0" max="1" step="0.01" :value="f[k-1]" @input="num(f, k-1, $event.target.value)" :aria-label="['x0','y0','x1','y1'][k-1]">
          <input class="entrada" v-model="f[4]" placeholder="texto" aria-label="Texto">
          <button type="button" class="btn icono pequeno fantasma" @click="quitar(i)" aria-label="Quitar"><icono n="cerrar"/></button>
        </div>
        <button type="button" class="btn pequeno" style="justify-self:start" @click="agregar"><icono n="mas"/>Añadir flecha</button>
      </div>
    </div>`,
};

export const CTabla = {
  name: 'c-tabla',
  props: { obj: Object, clave: String, etiqueta: String },
  created() {
    let t = this.obj[this.clave];
    if (!t || typeof t !== 'object') { t = { columnas: 'lr', encabezado: true, filas: [['', '']] }; this.obj[this.clave] = t; }
    if (!Array.isArray(t.filas) || !t.filas.length) t.filas = [['']];
  },
  computed: {
    t() { return this.obj[this.clave]; },
    ncol() { return Math.max(...this.t.filas.map((f) => f.length)); },
    alineaciones() {
      const c = String(this.t.columnas || '').replace(/[^lcr]/g, '');
      return Array.from({ length: this.ncol }, (_, i) => c[i] || (i === 0 ? 'l' : 'r'));
    },
  },
  methods: {
    fila() { this.t.filas.push(Array(this.ncol).fill('')); },
    columna() { this.t.filas.forEach((f) => f.push('')); this.t.columnas = this.alineaciones.join('') + 'r'; },
    quitarFila() { if (this.t.filas.length > 1) this.t.filas.pop(); },
    quitarColumna() { if (this.ncol > 1) { this.t.filas.forEach((f) => f.splice(this.ncol - 1)); this.t.columnas = this.alineaciones.slice(0, -1).join(''); } },
    alinear(i) {
      const a = [...this.alineaciones];
      a[i] = { l: 'c', c: 'r', r: 'l' }[a[i]];
      this.t.columnas = a.join('');
    },
  },
  template: `
    <div class="campo">
      <span class="etiqueta">{{ etiqueta }}</span>
      <div class="tabla-editor">
        <table>
          <tr><td v-for="(a, i) in alineaciones" :key="'a'+i" style="text-align:center">
            <button type="button" class="btn fantasma pequeno" style="width:100%" @click="alinear(i)" :title="'Alineación de la columna ' + (i+1)">{{ {l:'izquierda', c:'centro', r:'derecha'}[a] }}</button></td></tr>
          <tr v-for="(f, i) in t.filas" :key="i">
            <td v-for="j in ncol" :key="j"><input v-model="f[j-1]" :aria-label="'Fila ' + (i+1) + ', columna ' + j"></td>
          </tr>
        </table>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <button type="button" class="btn pequeno" @click="fila"><icono n="mas"/>Fila</button>
        <button type="button" class="btn pequeno" @click="columna"><icono n="mas"/>Columna</button>
        <button type="button" class="btn pequeno fantasma" @click="quitarFila">Quitar fila</button>
        <button type="button" class="btn pequeno fantasma" @click="quitarColumna">Quitar columna</button>
      </div>
      <label class="interruptor"><span class="texto">La primera fila es el encabezado</span>
        <input type="checkbox" v-model="t.encabezado"><span class="pista"></span></label>
    </div>`,
};

// Selector de imagen del proyecto (recursos y figuras de cuadernos)
export const SelectorRecurso = {
  name: 'selector-recurso',
  props: { pid: String, actual: String },
  emits: ['elegir', 'cerrar'],
  data: () => ({ recursos: null, filtro: '', subiendo: false, encima: false }),
  computed: {
    lista() {
      const f = this.filtro.trim().toLowerCase();
      return (this.recursos || []).filter((r) => !f || r.ruta.toLowerCase().includes(f));
    },
  },
  methods: {
    tamano,
    vista(r) { return `api/proyectos/${this.pid}/vista?ruta=${encodeURIComponent(r.ruta)}&v=${encodeURIComponent(r.fecha)}`; },
    async cargar() {
      try { this.recursos = await api(`api/proyectos/${this.pid}/recursos`); } catch (e) { avisarError(e); }
    },
    async subirArchivos(archivos) {
      if (!archivos || !archivos.length) return;
      this.subiendo = true;
      try {
        const r = await subir(`api/proyectos/${this.pid}/recursos`, { archivos: [...archivos] });
        (r.errores || []).forEach((m) => avisar(m, { tipo: 'error', ms: 7000 }));
        await this.cargar();
        if (r.guardados && r.guardados.length === 1) this.$emit('elegir', r.guardados[0]);
      } catch (e) { avisarError(e); } finally { this.subiendo = false; }
    },
    soltar(ev) { this.encima = false; this.subirArchivos(ev.dataTransfer.files); },
  },
  mounted() { this.cargar(); },
  template: `
  <div class="fondo-dialogo" @mousedown.self="$emit('cerrar')" @keydown.esc="$emit('cerrar')">
    <div class="dialogo medio" role="dialog" aria-modal="true" aria-labelledby="tit-selector">
      <header>
        <div style="flex:1"><h2 id="tit-selector">Elegir una imagen</h2>
          <p>Imágenes subidas y figuras de los cuadernos. PNG, JPG o PDF (los PDF vectoriales se ven mejor impresos).</p></div>
        <button class="btn icono fantasma" @click="$emit('cerrar')" aria-label="Cerrar"><icono n="cerrar"/></button>
      </header>
      <div class="cuerpo">
        <div style="display:flex;gap:8px">
          <input class="entrada" v-model="filtro" placeholder="Buscar por nombre o carpeta" aria-label="Buscar imagen">
          <input ref="archivo" type="file" multiple accept=".png,.jpg,.jpeg,.pdf,.gif,.webp,.tif,.tiff,.bmp,.svg" hidden @change="subirArchivos($event.target.files); $event.target.value=''">
          <button class="btn" @click="$refs.archivo.click()" :disabled="subiendo"><icono n="subir"/>{{ subiendo ? 'Subiendo…' : 'Subir' }}</button>
        </div>
        <div class="zona-soltar" :class="{encima}" @dragover.prevent="encima = true" @dragleave="encima = false" @drop.prevent="soltar" v-if="recursos && !recursos.length">
          <strong>Todavía no hay imágenes en este proyecto.</strong> Arrastra aquí tus archivos o usa «Subir».
        </div>
        <div class="galeria" style="padding:0" v-else @dragover.prevent="encima = true" @drop.prevent="soltar">
          <button v-for="r in lista" :key="r.ruta" class="recurso" :class="{elegido: r.ruta === actual}" @click="$emit('elegir', r.ruta)" :title="r.ruta">
            <span class="miniatura"><img :src="vista(r)" alt="" loading="lazy"></span>
            <span class="nombre-rec">{{ r.nombre }}</span>
            <span class="meta-rec">{{ r.tipo.toUpperCase() }}, {{ tamano(r.tamano) }}<span v-if="r.origen === 'cuaderno'">, cuaderno</span></span>
          </button>
        </div>
      </div>
      <footer><button class="btn" @click="$emit('cerrar')">Cerrar</button></footer>
    </div>
  </div>`,
};

export const CImagen = {
  name: 'c-imagen',
  components: { SelectorRecurso },
  props: { obj: Object, clave: String, etiqueta: String, ayuda: String },
  setup() { return { ed: inject('ed', null) }; },
  data: () => ({ abierto: false }),
  computed: {
    ruta() { return this.obj[this.clave] || ''; },
    pid() { return this.ed && this.ed.pid; },
    src() { return this.ruta ? `api/proyectos/${this.pid}/vista?ruta=${encodeURIComponent(this.ruta)}` : ''; },
  },
  methods: {
    nombreArchivo,
    elegir(r) { this.obj[this.clave] = r; this.abierto = false; },
  },
  template: `
    <div class="campo">
      <span class="etiqueta">{{ etiqueta }}</span>
      <div style="display:grid;grid-template-columns:64px 1fr;gap:10px;align-items:center">
        <button type="button" class="recurso" style="padding:3px" @click="abierto = true" :aria-label="'Elegir ' + (etiqueta || 'imagen')">
          <span class="miniatura" style="aspect-ratio:1"><img v-if="src" :src="src" alt=""><icono v-else n="imagen"/></span>
        </button>
        <div style="display:grid;gap:4px;min-width:0">
          <span style="font-size:var(--t-xs);overflow:hidden;text-overflow:ellipsis;white-space:nowrap" :title="ruta">{{ ruta ? nombreArchivo(ruta) : 'Ninguna imagen' }}</span>
          <div style="display:flex;gap:6px">
            <button type="button" class="btn pequeno" @click="abierto = true">{{ ruta ? 'Cambiar' : 'Elegir' }}</button>
            <button v-if="ruta" type="button" class="btn pequeno fantasma" @click="obj[clave] = ''">Quitar</button>
          </div>
        </div>
      </div>
      <span v-if="ayuda" class="ayuda">{{ ayuda }}</span>
      <selector-recurso v-if="abierto" :pid="pid" :actual="ruta" @elegir="elegir" @cerrar="abierto = false"/>
    </div>`,
};

// Selector de tema de color, agrupado (sobrios y vivos)
export const CTema = {
  name: 'c-tema',
  props: { modelValue: String },
  emits: ['update:modelValue'],
  computed: {
    cat() { return tienda.catalogo; },
    grupos() {
      if (!this.cat) return [];
      return this.cat.grupos_temas || [{ nombre: '', temas: Object.keys(this.cat.temas) }];
    },
  },
  methods: {
    c(k) { return this.cat.temas[k] || {}; },
    nombre(k) { return k.charAt(0).toUpperCase() + k.slice(1); },
  },
  template: `
    <div class="selector-tema">
      <div v-for="g in grupos" :key="g.nombre" class="grupo-temas">
        <span v-if="g.nombre" class="nombre-grupo">{{ g.nombre }}</span>
        <div class="temas">
          <button v-for="k in g.temas" :key="k" type="button" class="tema-opcion" :class="{activo: modelValue === k}"
                  :aria-pressed="modelValue === k" @click="$emit('update:modelValue', k)">
            <span class="franjas"><i :style="{background:'#'+c(k).primario}"></i><i :style="{background:'#'+c(k).secundario}"></i><i :style="{background:'#'+c(k).acento}"></i><i :style="{background:'#'+c(k).fondo_bloque}"></i></span>{{ nombre(k) }}
          </button>
        </div>
      </div>
    </div>`,
};

// Campo de una variante según su tipo
export const CampoVariante = {
  name: 'campo-variante',
  components: { CTexto, CParrafo, CLatex, CNumero, CDeslizador, CSeleccion, CInterruptor, CColor, CDimension, CLista, CPares, CFlechas, CTabla, CImagen },
  props: { obj: Object, campo: Object },
  computed: {
    c() { return this.campo; },
  },
  template: `
    <c-imagen v-if="c.tipo === 'imagen'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta"/>
    <c-texto v-else-if="c.tipo === 'texto'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta" formato/>
    <c-parrafo v-else-if="c.tipo === 'parrafo'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta"/>
    <c-latex v-else-if="c.tipo === 'latex'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta"/>
    <c-lista v-else-if="c.tipo === 'lista'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta"/>
    <c-pares v-else-if="c.tipo === 'pares'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta"/>
    <c-pares v-else-if="c.tipo === 'hitos'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta" :nombres="['Fecha', 'Texto']"/>
    <c-flechas v-else-if="c.tipo === 'flechas'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta"/>
    <c-tabla v-else-if="c.tipo === 'tabla'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta"/>
    <c-deslizador v-else-if="c.tipo === 'porcentaje'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta" :min="5" :max="100" :paso="1"/>
    <c-deslizador v-else-if="c.tipo === 'fraccion'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta" :min="0.05" :max="0.95" :paso="0.01"/>
    <c-deslizador v-else-if="c.tipo === 'angulo'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta" :min="-30" :max="30" :paso="0.5"/>
    <c-numero v-else-if="c.tipo === 'numero'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta"/>
    <c-dimension v-else-if="c.tipo === 'dimension'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta"/>
    <c-seleccion v-else-if="c.tipo === 'seleccion'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta" :opciones="c.opciones"/>
    <c-interruptor v-else-if="c.tipo === 'booleano'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta"/>
    <c-color v-else-if="c.tipo === 'color'" :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta"/>
    <c-texto v-else :obj="obj" :clave="c.nombre" :etiqueta="c.etiqueta"/>`,
};

export const CAMPOS = { CTexto, CParrafo, CLatex, CNumero, CDeslizador, CSeleccion, CSegmentos, CInterruptor, CColor, CDimension, CAncla, CLista, CPares, CFlechas, CTabla, CImagen, CampoVariante, SelectorRecurso, CTema };
