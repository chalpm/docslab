// SPDX-License-Identifier: AGPL-3.0-only
// LAB: los cuadernos del documento, celda a celda, y las plantillas de gráficos.
import { api, post, put, borrar, subir } from './api.js';
import { tienda, avisar, avisarError, confirmar, preguntar } from './tienda.js';
import { fecha, clonar, nuevoId } from './util.js';
import { PanelCuadernos } from './cuadernos.js';

const { inject, markRaw } = Vue;

const NOMBRE_BIB = { matplotlib: 'matplotlib', seaborn: 'seaborn', plotly: 'plotly (interactivo)' };
const NOMBRE_TIPO = {
  datos: 'Datos', columna: 'Una columna', columnas: 'Varias columnas', texto: 'Texto', numero: 'Número',
  interruptor: 'Sí o no', opcion: 'Lista de opciones', color: 'Color', paleta: 'Paleta de colores',
};
const NOMBRE_PALETA = { documento: 'Los colores del documento' };
const EXT_DATOS = /\.(csv|tsv|tab|txt|xlsx|xls|json|parquet)$/i;

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// Markdown mínimo para las celdas de texto (títulos, listas, énfasis y código)
function mdSimple(fuente) {
  const enLinea = (t) => esc(t)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  const out = [];
  let lista = null, parrafo = [], codigo = null;
  const cerrar = () => {
    if (parrafo.length) { out.push('<p>' + parrafo.map(enLinea).join('<br>') + '</p>'); parrafo = []; }
    if (lista) { out.push(`</${lista}>`); lista = null; }
  };
  for (const ln of String(fuente || '').split('\n')) {
    if (codigo !== null) {
      if (/^```/.test(ln)) { out.push('<pre>' + esc(codigo.join('\n')) + '</pre>'); codigo = null; } else codigo.push(ln);
      continue;
    }
    let m;
    if (/^```/.test(ln)) { cerrar(); codigo = []; }
    else if ((m = /^(#{1,6})\s+(.*)$/.exec(ln))) { cerrar(); out.push(`<h${m[1].length}>${enLinea(m[2])}</h${m[1].length}>`); }
    else if ((m = /^\s*([-*+]|\d+[.)])\s+(.*)$/.exec(ln))) {
      const tipo = /\d/.test(m[1]) ? 'ol' : 'ul';
      if (parrafo.length) { out.push('<p>' + parrafo.map(enLinea).join('<br>') + '</p>'); parrafo = []; }
      if (lista !== tipo) { if (lista) out.push(`</${lista}>`); out.push(`<${tipo}>`); lista = tipo; }
      out.push('<li>' + enLinea(m[2]) + '</li>');
    } else if (!ln.trim()) cerrar();
    else { if (lista) { out.push(`</${lista}>`); lista = null; } parrafo.push(ln); }
  }
  if (codigo !== null) out.push('<pre>' + esc(codigo.join('\n')) + '</pre>');
  cerrar();
  return out.join('');
}

// Salida HTML de una celda (tablas de pandas, etc.) en un marco aislado: sin el mismo origen que
// DocsLab, así que un cuaderno ajeno no puede leer la página ni llamar a la API. Solo avisa de su alto.
function marcoHtml(html, id) {
  return `<!doctype html><meta charset="utf-8"><style>
html,body{margin:0;background:#fff;color:#1d1d1f;font:13px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
body{padding:2px}table{border-collapse:collapse}th,td{border:1px solid #d9d9de;padding:3px 8px;text-align:right}
th{background:#f4f4f6}img{max-width:100%}</style>${html}<script>
(function(){var u=0;function a(){var h=Math.ceil(document.documentElement.scrollHeight);if(h!==u){u=h;parent.postMessage({docslabAlto:h,id:${JSON.stringify(id)}},'*');}}
addEventListener('load',a);new ResizeObserver(a).observe(document.documentElement);a();})();</script>`;
}

// Una figura de plotly, viva, en un marco aislado
function marcoPlotly(figura) {
  const datos = JSON.stringify(figura).replace(/</g, '\\u003c');
  const base = new URL('api/lab/plotly.min.js', document.baseURI).href;
  return `<!doctype html><meta charset="utf-8"><style>html,body{margin:0;height:100%;background:#fff}#g{width:100%;height:100%}</style>
<div id="g"></div><script src="${base}"></script><script>
const f = ${datos};
const l = Object.assign({}, f.layout || {}); delete l.width; delete l.height; l.autosize = true;
Plotly.newPlot('g', f.data || [], l, {responsive: true, displaylogo: false});</script>`;
}

// Editor de código Python (CodeMirror) que crece con su contenido
const CodigoPy = {
  name: 'codigo-py',
  props: { modelValue: String, soloLectura: Boolean, etiqueta: String },
  emits: ['update:modelValue', 'ejecutar', 'ejecutar-y-seguir'],
  watch: {
    modelValue(v) { if (this.cm && v !== this.cm.getValue()) { this.poniendo = true; this.cm.setValue(v || ''); this.poniendo = false; } },
    soloLectura(v) { if (this.cm) this.cm.setOption('readOnly', v); },
  },
  methods: {
    enfocar() { this.cm.focus(); },
    insertar(texto) { this.cm.replaceSelection(texto); this.cm.focus(); },
  },
  mounted() {
    this.cm = markRaw(window.CodeMirror(this.$el, {
      value: this.modelValue || '', mode: 'python', indentUnit: 4, tabSize: 4, lineWrapping: false, viewportMargin: Infinity,
      matchBrackets: true, autoCloseBrackets: true, readOnly: this.soloLectura, screenReaderLabel: this.etiqueta || 'Código de Python',
      extraKeys: {
        'Shift-Enter': () => this.$emit('ejecutar-y-seguir'),
        'Ctrl-Enter': () => this.$emit('ejecutar'), 'Cmd-Enter': () => this.$emit('ejecutar'),
        Tab: (cm) => (cm.somethingSelected() ? cm.indentSelection('add') : cm.replaceSelection('    ', 'end')),
        'Shift-Tab': (cm) => cm.indentSelection('subtract'),
      },
    }));
    this.cm.on('change', () => { if (!this.poniendo) this.$emit('update:modelValue', this.cm.getValue()); });
  },
  template: '<div class="codigo-py"></div>',
};

const SalidaCelda = {
  name: 'salida-celda',
  props: { s: Object },
  computed: {
    plotly() { return this.s.t === 'plotly' ? marcoPlotly(this.s.figura) : ''; },
    alto() { const h = this.s.figura && this.s.figura.layout && this.s.figura.layout.height; return Math.min(640, Math.max(260, Number(h) || 380)); },
    svg() { return this.s.t === 'svg' ? 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(this.s.svg) : ''; },
    html() { return this.s.t === 'html' ? marcoHtml(this.s.html, this.idMarco) : ''; },
  },
  data() { return { idMarco: 'm' + Math.random().toString(36).slice(2), altoHtml: 60 }; },
  mounted() {
    this.alMensaje = (e) => {
      const m = this.$refs.marco;
      if (!m || e.source !== m.contentWindow || !e.data || e.data.id !== this.idMarco) return;
      this.altoHtml = Math.min(460, Math.max(24, Number(e.data.docslabAlto) || 60));
    };
    window.addEventListener('message', this.alMensaje);
  },
  unmounted() { window.removeEventListener('message', this.alMensaje); },
  template: `
  <pre v-if="s.t === 'texto'" class="salida texto" :class="{aviso: s.canal === 'stderr'}">{{ s.texto }}</pre>
  <div v-else-if="s.t === 'error'" class="salida error">
    <strong>{{ s.nombre }}</strong>: {{ s.valor }}
    <details v-if="s.traza"><summary>Ver dónde falló</summary><pre>{{ s.traza }}</pre></details>
  </div>
  <div v-else-if="s.t === 'img'" class="salida figura"><img :src="'data:' + s.mime + ';base64,' + s.b64" alt="Figura que mostró la celda"></div>
  <div v-else-if="s.t === 'svg'" class="salida figura"><img :src="svg" alt="Figura que mostró la celda"></div>
  <iframe v-else-if="s.t === 'html'" ref="marco" class="salida html" sandbox="allow-scripts" :srcdoc="html" :style="{height: altoHtml + 'px'}" title="Resultado de la celda (HTML)"></iframe>
  <iframe v-else-if="s.t === 'plotly'" class="salida plotly" sandbox="allow-scripts" :srcdoc="plotly" :style="{height: alto + 'px'}" title="Gráfico interactivo"></iframe>`,
};

// ---------------------------------------------------------------- formulario de un gráfico
// Instalar paquetes desde una celda: %pip install …, !pip install …, %conda install …
const RE_INSTALAR = /^\s*[%!]\s*(?:pip3?|python3?\s+-m\s+pip|conda|mamba|micromamba|uv\s+pip)\s+install\b/m;
// Lo que escriben pip, uv y conda cuando instalan o actualizan algo
const RE_INSTALADO = /Successfully installed|Installed \d+ packages?|Executing transaction: done/;
// Módulos cuyo paquete de pip se llama distinto
const PAQUETE_DE = {
  sklearn: 'scikit-learn', cv2: 'opencv-python', PIL: 'pillow', yaml: 'pyyaml', bs4: 'beautifulsoup4',
  umap: 'umap-learn', skimage: 'scikit-image', Bio: 'biopython', dateutil: 'python-dateutil', docx: 'python-docx',
  pptx: 'python-pptx', Crypto: 'pycryptodome', serial: 'pyserial', dotenv: 'python-dotenv', jwt: 'PyJWT',
  attr: 'attrs', fitz: 'pymupdf', osgeo: 'gdal', mpl_toolkits: 'matplotlib', sentence_transformers: 'sentence-transformers',
};

const DialogoGrafico = {
  name: 'dialogo-grafico',
  props: { nb: String, inicial: Object },      // inicial: {plantilla, valores} al reajustar una celda
  emits: ['insertar', 'cerrar', 'plantillas'],
  setup() { return { ed: inject('ed') }; },
  data: () => ({
    cat: null, t: null, valores: {}, filtro: '', categoria: '', archivos: [], variables: null, columnas: null, filas: null,
    cargandoCols: false, errorCols: '', codigo: '', verCodigo: false, trabajando: false, subiendo: false,
  }),
  computed: {
    lista() {
      return (this.cat ? this.cat.plantillas : []).filter((t) => (!this.filtro || t.biblioteca === this.filtro)
        && (!this.categoria || t.categoria === this.categoria));
    },
    datos() { const p = this.t && this.t.parametros.find((x) => x.tipo === 'datos'); return p ? this.valores[p.nombre] : null; },
    colores() { return (this.ed.modelo && this.ed.modelo.colores) || {}; },
    archivosDatos() { return this.archivos.filter((a) => EXT_DATOS.test(a.ruta)); },
    opcionesColor() {
      const c = this.colores;
      return [['primario', 'Primario del documento'], ['acento', 'Acento del documento'], ['secundario', 'Secundario del documento']]
        .filter(([k]) => c[k]).map(([k, n]) => ({ valor: k, texto: n }));
    },
  },
  methods: {
    nombreBib: (b) => NOMBRE_BIB[b] || b,
    nombrePaleta: (p) => NOMBRE_PALETA[p] || p,
    async elegir(t, valores) {
      this.t = t;
      const v = {};
      for (const p of t.parametros) v[p.nombre] = clonar(valores && p.nombre in valores ? valores[p.nombre] : (p.defecto ?? (p.tipo === 'columnas' ? [] : '')));
      this.valores = v;
      this.codigo = '';
      this.verCodigo = false;
      await this.cargarArchivos();
      const d = this.datos;
      if (d && !valores) {
        // por defecto, el primer archivo de datos del cuaderno (o los de ejemplo si no hay ninguno)
        if (!this.archivosDatos.some((a) => a.ruta === d.archivo)) d.archivo = this.archivosDatos.length ? this.archivosDatos[0].ruta : '';
      }
      this.leerColumnas(!valores);
    },
    async cargarArchivos() {
      try { this.archivos = await api(`api/proyectos/${this.ed.pid}/cuadernos/${this.nb}/archivos`); } catch (e) { this.archivos = []; }
    },
    async cargarVariables() {
      try { this.variables = (await post(`api/proyectos/${this.ed.pid}/lab/${this.nb}/variables`)).variables; } catch (e) { this.variables = []; avisarError(e); }
    },
    async modoDatos(modo) {
      const d = this.datos;
      d.modo = modo;
      if (modo === 'variable') {
        await this.cargarVariables();
        if (!this.variables.some((v) => v.nombre === d.variable)) d.variable = this.variables.length ? this.variables[0].nombre : '';
      }
      this.leerColumnas(true);
    },
    async usarEjemplo() {
      try {
        const r = await post(`api/proyectos/${this.ed.pid}/lab/${this.nb}/ejemplo`, { archivos: (this.t && this.t.ejemplo) || [] });
        await this.cargarArchivos();
        Object.assign(this.datos, { modo: 'archivo', archivo: r.archivo });
        this.leerColumnas(true);
      } catch (e) { avisarError(e); }
    },
    async subirDatos(ev) {
      const fs = [...ev.target.files];
      ev.target.value = '';
      if (!fs.length) return;
      this.subiendo = true;
      try {
        await subir(`api/proyectos/${this.ed.pid}/cuadernos/${this.nb}/datos`, { datos: fs });
        await this.cargarArchivos();
        const nuevo = this.archivosDatos.find((a) => fs.some((f) => a.ruta.endsWith(f.name)));
        if (nuevo) { Object.assign(this.datos, { modo: 'archivo', archivo: nuevo.ruta }); this.leerColumnas(true); }
      } catch (e) { avisarError(e); } finally { this.subiendo = false; }
    },
    // las columnas de los datos elegidos (las lee el núcleo de Python del cuaderno)
    async leerColumnas(ajustar) {
      const d = this.datos;
      this.columnas = null; this.errorCols = ''; this.filas = null;
      if (!d || (d.modo === 'variable' ? !d.variable : !d.archivo)) return;
      this.cargandoCols = true;
      try {
        const r = await post(`api/proyectos/${this.ed.pid}/lab/${this.nb}/columnas`, { datos: d });
        this.columnas = r.columnas; this.filas = r.filas;
        if (ajustar) this.ajustarColumnas();
      } catch (e) { this.errorCols = e.message; } finally { this.cargandoCols = false; }
    },
    // si la columna por defecto de la plantilla no existe en estos datos, se elige una que sí
    ajustarColumnas() {
      const cols = this.columnas || [];
      const nombres = cols.map((c) => c.nombre);
      const usadas = new Set();
      for (const p of this.t.parametros) {
        if (p.tipo === 'columna') {
          const v = this.valores[p.nombre];
          if (v && nombres.includes(v)) { usadas.add(v); continue; }
          if (p.opcional) { this.valores[p.nombre] = ''; continue; }
          const cand = cols.filter((c) => (p.numerica ? c.numerica : true) && !usadas.has(c.nombre));
          const otra = (p.numerica ? cand : cols.filter((c) => !c.numerica && !usadas.has(c.nombre)).concat(cand))[0] || cols[0];
          this.valores[p.nombre] = otra ? otra.nombre : '';
          if (otra) usadas.add(otra.nombre);
        } else if (p.tipo === 'columnas') {
          const v = (this.valores[p.nombre] || []).filter((x) => nombres.includes(x));
          this.valores[p.nombre] = v.length ? v : cols.filter((c) => (p.numerica ? c.numerica : true)).map((c) => c.nombre).slice(0, 8);
        }
      }
    },
    colsDe(p) { const cols = this.columnas || []; return p.numerica ? [...cols.filter((c) => c.numerica), ...cols.filter((c) => !c.numerica)] : cols; },
    alternarColumna(p, nombre) {
      const v = this.valores[p.nombre];
      const i = v.indexOf(nombre);
      if (i >= 0) v.splice(i, 1); else v.push(nombre);
    },
    esColorDoc(v) { return this.opcionesColor.some((o) => o.valor === v); },
    hexDe(v) { const c = this.esColorDoc(v) ? this.colores[v] : v; return /^#?[0-9a-f]{6}$/i.test(String(c || '')) ? '#' + String(c).replace('#', '') : '#2f4858'; },
    async generar() {
      const r = await post('api/graficos/generar', { plantilla: this.t, valores: this.valores, colores: this.colores });
      return r.codigo;
    },
    async alternarCodigo() {
      this.verCodigo = !this.verCodigo;
      if (this.verCodigo) { try { this.codigo = await this.generar(); } catch (e) { this.verCodigo = false; avisarError(e); } }
    },
    async insertar(ejecutar) {
      this.trabajando = true;
      try {
        const codigo = await this.generar();
        this.$emit('insertar', { codigo, meta: { plantilla: this.t.id, nombre: this.t.nombre, valores: clonar(this.valores) }, ejecutar });
      } catch (e) { avisarError(e); } finally { this.trabajando = false; }
    },
  },
  async mounted() {
    try {
      this.cat = await api('api/graficos');
      if (this.inicial) {
        const t = this.cat.plantillas.find((x) => x.id === this.inicial.plantilla);
        if (t) await this.elegir(t, this.inicial.valores);
        else avisar('La plantilla de este gráfico ya no existe: elige otra.', { tipo: 'error' });
      }
    } catch (e) { avisarError(e); }
  },
  template: `
  <div class="fondo-dialogo" @mousedown.self="$emit('cerrar')" @keydown.esc="$emit('cerrar')">
    <div class="dialogo grande dialogo-grafico" role="dialog" aria-modal="true" aria-labelledby="tit-grafico">
      <header>
        <div style="flex:1"><h2 id="tit-grafico">{{ t ? t.nombre : 'Gráfico desde una plantilla' }}</h2>
          <p v-if="!t">Elige el tipo de gráfico. Después eliges tus datos y sus opciones; el código queda en una celda y se puede editar.</p>
          <p v-else>{{ t.descripcion }}
            <a v-if="t.referencia" :href="t.referencia" target="_blank" rel="noopener">Este tipo de gráfico en The R Graph Gallery</a></p></div>
        <button class="btn icono fantasma" @click="$emit('cerrar')" aria-label="Cerrar"><icono n="cerrar"/></button>
      </header>

      <div class="cuerpo" v-if="!t">
        <div v-if="cat && cat.categorias" class="filtro-clases" role="group" aria-label="Filtrar por tipo de gráfico">
          <button type="button" :class="{activo: !categoria}" @click="categoria = ''">Todos los tipos</button>
          <button v-for="c in cat.categorias" :key="c" type="button" :class="{activo: categoria === c}" @click="categoria = c">{{ c }}</button>
        </div>
        <div class="filtro-clases" role="group" aria-label="Filtrar por biblioteca">
          <button type="button" :class="{activo: !filtro}" @click="filtro = ''">Todas</button>
          <button v-for="b in (cat ? cat.bibliotecas : [])" :key="b" type="button" :class="{activo: filtro === b}" @click="filtro = b">{{ b }}</button>
        </div>
        <div class="galeria-graficos">
          <button v-for="g in lista" :key="g.id" class="tarjeta-grafico" @click="elegir(g)">
            <span class="mini"><img v-if="g.miniatura" :src="g.miniatura" alt="" loading="lazy"><icono v-else n="imagen"/></span>
            <strong>{{ g.nombre }}</strong>
            <span class="detalle">{{ g.categoria ? g.categoria + ' · ' : '' }}{{ g.biblioteca }}{{ g.incluida ? '' : ' · tuya' }}</span>
          </button>
        </div>
        <p class="ayuda">¿Falta alguno? En «Plantillas de gráficos» puedes crear las tuyas o copiar una de estas y cambiar su código.
          <button class="enlace" @click="$emit('plantillas')">Abrir las plantillas</button></p>
      </div>

      <div class="cuerpo dos-columnas" v-else>
        <div class="formulario-grafico">
          <template v-for="p in t.parametros" :key="p.nombre">
            <div v-if="p.tipo === 'datos'" class="campo bloque-datos">
              <span class="etiqueta">{{ p.etiqueta }}</span>
              <div class="segmentos">
                <button type="button" :class="{activo: valores[p.nombre].modo !== 'variable'}" @click="modoDatos('archivo')">Un archivo</button>
                <button type="button" :class="{activo: valores[p.nombre].modo === 'variable'}" @click="modoDatos('variable')">Una tabla del cuaderno</button>
              </div>
              <template v-if="valores[p.nombre].modo !== 'variable'">
                <select class="entrada" v-model="valores[p.nombre].archivo" @change="leerColumnas(true)" aria-label="Archivo de datos">
                  <option value="" disabled>Elige un archivo…</option>
                  <option v-for="a in archivosDatos" :key="a.ruta" :value="a.ruta">{{ a.ruta }}</option>
                </select>
                <div style="display:flex;gap:6px;flex-wrap:wrap">
                  <input ref="datos" type="file" multiple hidden accept=".csv,.tsv,.tab,.txt,.xlsx,.xls,.json,.parquet" @change="subirDatos">
                  <button class="btn pequeno" @click="$refs.datos[0].click()" :disabled="subiendo"><icono n="subir"/>{{ subiendo ? 'Subiendo…' : 'Subir datos' }}</button>
                  <button class="btn pequeno" @click="usarEjemplo">Usar datos de ejemplo</button>
                </div>
              </template>
              <template v-else>
                <select class="entrada" v-model="valores[p.nombre].variable" @change="leerColumnas(true)" aria-label="Tabla del cuaderno">
                  <option value="" disabled>{{ variables && !variables.length ? 'No hay tablas todavía' : 'Elige una tabla…' }}</option>
                  <option v-for="v in variables || []" :key="v.nombre" :value="v.nombre">{{ v.nombre }} ({{ v.filas }} filas, {{ v.columnas }} columnas)</option>
                </select>
                <span class="ayuda">Son los DataFrame de pandas que ya existen: ejecuta antes la celda que los crea.</span>
              </template>
              <span class="ayuda" v-if="cargandoCols">Leyendo las columnas…</span>
              <span class="ayuda" v-else-if="errorCols" style="color:var(--rojo)">No se pudieron leer: {{ errorCols }}</span>
              <span class="ayuda" v-else-if="columnas">{{ filas }} filas, {{ columnas.length }} columnas</span>
            </div>
            <label v-else-if="p.tipo === 'columna'" class="campo"><span class="etiqueta">{{ p.etiqueta }}</span>
              <select class="entrada" v-model="valores[p.nombre]" :disabled="!columnas">
                <option v-if="p.opcional" value="">Ninguna</option>
                <option v-for="c in colsDe(p)" :key="c.nombre" :value="c.nombre">{{ c.nombre }}{{ c.numerica ? '' : ' (texto)' }}</option>
              </select></label>
            <div v-else-if="p.tipo === 'columnas'" class="campo"><span class="etiqueta">{{ p.etiqueta }}</span>
              <div class="casillas">
                <label v-for="c in colsDe(p)" :key="c.nombre"><input type="checkbox" :checked="valores[p.nombre].includes(c.nombre)" @change="alternarColumna(p, c.nombre)">{{ c.nombre }}</label>
              </div></div>
            <label v-else-if="p.tipo === 'numero'" class="campo corto"><span class="etiqueta">{{ p.etiqueta }}</span>
              <input class="entrada" type="number" v-model.number="valores[p.nombre]" :min="p.min" :max="p.max" step="any"></label>
            <label v-else-if="p.tipo === 'interruptor'" class="interruptor"><span class="texto">{{ p.etiqueta }}</span>
              <input type="checkbox" v-model="valores[p.nombre]"><span class="pista"></span></label>
            <label v-else-if="p.tipo === 'opcion'" class="campo"><span class="etiqueta">{{ p.etiqueta }}</span>
              <select class="entrada" v-model="valores[p.nombre]"><option v-for="o in p.opciones || []" :key="o" :value="o">{{ o }}</option></select></label>
            <label v-else-if="p.tipo === 'paleta'" class="campo"><span class="etiqueta">{{ p.etiqueta }}</span>
              <select class="entrada" v-model="valores[p.nombre]"><option v-for="o in cat.paletas" :key="o" :value="o">{{ nombrePaleta(o) }}</option></select></label>
            <div v-else-if="p.tipo === 'color'" class="campo"><span class="etiqueta">{{ p.etiqueta }}</span>
              <div class="color-grafico">
                <input type="color" :value="hexDe(valores[p.nombre])" @input="valores[p.nombre] = $event.target.value" :aria-label="p.etiqueta">
                <select class="entrada" :value="esColorDoc(valores[p.nombre]) ? valores[p.nombre] : ''" @change="valores[p.nombre] = $event.target.value || hexDe(valores[p.nombre])">
                  <option v-for="o in opcionesColor" :key="o.valor" :value="o.valor">{{ o.texto }}</option>
                  <option value="">Otro color</option>
                </select>
              </div></div>
            <label v-else class="campo"><span class="etiqueta">{{ p.etiqueta }}</span>
              <input class="entrada" v-model="valores[p.nombre]"></label>
            <span v-if="p.ayuda" class="ayuda" style="margin-top:-6px">{{ p.ayuda }}</span>
          </template>
        </div>
        <aside class="lado-grafico">
          <span class="mini grande"><img v-if="t.miniatura" :src="t.miniatura" alt=""><icono v-else n="imagen"/></span>
          <p class="ayuda">La miniatura es con los datos de ejemplo. Al insertarlo, la celda se ejecuta con tus datos y la figura se guarda en la carpeta del cuaderno, lista para el documento.</p>
          <button class="btn pequeno" @click="alternarCodigo"><icono n="codigo"/>{{ verCodigo ? 'Ocultar el código' : 'Ver el código que se va a insertar' }}</button>
          <pre v-if="verCodigo" class="codigo-previo">{{ codigo }}</pre>
        </aside>
      </div>

      <footer v-if="t">
        <button v-if="!inicial" class="btn" @click="t = null" style="margin-right:auto"><icono n="arriba" style="transform:rotate(-90deg)"/>Otro gráfico</button>
        <button class="btn" @click="$emit('cerrar')">Cancelar</button>
        <button class="btn" :disabled="trabajando" @click="insertar(false)">{{ inicial ? 'Actualizar el código' : 'Insertar sin ejecutar' }}</button>
        <button class="btn primario" :disabled="trabajando" @click="insertar(true)"><icono n="play"/>{{ inicial ? 'Actualizar y ejecutar' : 'Insertar y ejecutar' }}</button>
      </footer>
    </div>
  </div>`,
};

// ---------------------------------------------------------------- el cuaderno, celda a celda
const CuadernoLab = {
  name: 'cuaderno-lab',
  components: { SalidaCelda, DialogoGrafico, CodigoPy },
  props: { c: Object },
  emits: ['figuras', 'plantillas', 'tanda'],
  setup() { return { ed: inject('ed') }; },
  data: () => ({
    celdas: null, nucleo: { estado: 'apagado', cola: [] }, rev: 0, sel: null, editando: null, guardado: true,
    grafico: null, tanda: 0, error: '', menu: false, aviso: null,
  }),
  computed: {
    base() { return `api/proyectos/${this.ed.pid}/lab/${this.c.id}`; },
    ocupado() { return this.nucleo.estado === 'ocupado'; },
    chip() {
      if (this.ocupado) return { clase: 'trabajando', texto: 'Ejecutando' };
      if (this.nucleo.estado === 'listo') return { clase: 'ok', texto: 'Python listo' };
      return { clase: '', texto: 'Python apagado' };
    },
    puedeEjecutar() { return !tienda.estado || tienda.estado.cuadernos !== false; },
  },
  watch: { 'c.id'() { this.cargar(); } },
  methods: {
    async cargar() {
      clearTimeout(this._sondeo); clearTimeout(this._guardar);
      this.celdas = null; this.sel = null; this.editando = null; this.error = '';
      try {
        const d = await api(this.base);
        this.celdas = d.celdas; this.nucleo = d.nucleo; this.rev = d.rev; this.tanda = d.nucleo.tanda; this.guardado = true;
        if (this.ocupado) this.sondear();
      } catch (e) { this.error = e.message; }
    },
    filas(cel) { return Math.max(cel.tipo === 'codigo' ? 2 : 1, String(cel.fuente).split('\n').length); },
    estadoCelda(cel) {
      if (this.nucleo.en_curso === cel.id) return 'corriendo';
      if ((this.nucleo.cola || []).includes(cel.id)) return 'en-cola';
      return '';
    },
    marca(cel) { const e = this.estadoCelda(cel); return e ? '*' : (cel.n ?? ' '); },
    html: (cel) => mdSimple(cel.fuente),
    // ------------------------------------------------ guardar
    tocar() {
      this.guardado = false;
      clearTimeout(this._guardar);
      this._guardar = setTimeout(() => this.guardar(), 900);
    },
    carga() { return this.celdas.map((x) => ({ id: x.id, tipo: x.tipo, fuente: x.fuente, meta: x.meta || {} })); },
    async guardar() {
      clearTimeout(this._guardar);
      if (this.guardado || !this.celdas) return;
      this.guardado = true;
      try { await put(this.base, { celdas: this.carga() }); } catch (e) { this.guardado = false; avisarError(e); }
    },
    alEscribir(cel) {
      // si se toca a mano el código de un gráfico de plantilla, deja de ser «ajustable» sin avisar
      if (cel.meta && cel.meta.plantilla) cel.meta.editado = true;
      this.tocar();
    },
    // ------------------------------------------------ celdas
    nueva(tipo, fuente = '', meta = {}) { return { id: nuevoId('c').replace(/[^A-Za-z0-9_-]/g, ''), tipo, fuente, meta, n: null, salidas: [] }; },
    agregar(tipo, despuesDe, fuente = '', meta = {}) {
      const cel = this.nueva(tipo, fuente, meta);
      let i = this.celdas.findIndex((x) => x.id === (despuesDe ?? this.sel));
      i = i < 0 ? this.celdas.length : i + 1;
      this.celdas.splice(i, 0, cel);
      this.sel = cel.id;
      if (tipo === 'texto') this.editando = cel.id;
      this.tocar();
      this.$nextTick(() => this.enfocar(cel.id));
      return cel;
    },
    enfocar(id) {
      const celda = this.$el.querySelector && this.$el.querySelector(`[data-celda="${id}"]`);
      if (!celda) return;
      const cm = celda.querySelector('.CodeMirror'), ta = celda.querySelector('textarea.fuente');
      if (cm && cm.CodeMirror) cm.CodeMirror.focus(); else if (ta) ta.focus();
    },
    seguir(cel) {                                  // como en Jupyter: ejecuta y pasa a la celda siguiente (o crea una)
      this.ejecutar([cel.id]);
      const sig = this.celdas[this.celdas.indexOf(cel) + 1];
      if (sig) { this.sel = sig.id; if (sig.tipo === 'texto') this.editando = null; this.$nextTick(() => this.enfocar(sig.id)); } else this.agregar('codigo', cel.id);
    },
    mover(cel, d) {
      const i = this.celdas.indexOf(cel), j = i + d;
      if (j < 0 || j >= this.celdas.length) return;
      this.celdas.splice(i, 1); this.celdas.splice(j, 0, cel);
      this.tocar();
    },
    cambiarTipo(cel) {
      cel.tipo = cel.tipo === 'codigo' ? 'texto' : 'codigo';
      cel.salidas = []; cel.n = null; cel.meta = {};
      this.editando = cel.tipo === 'texto' ? cel.id : null;
      this.tocar();
    },
    async quitar(cel) {
      if (String(cel.fuente).trim().length > 60) {
        const ok = await confirmar({ titulo: '¿Borrar la celda?', texto: 'Se borra su código y su salida.', aceptar: 'Borrar', peligro: true });
        if (!ok) return;
      }
      this.celdas.splice(this.celdas.indexOf(cel), 1);
      this.tocar();
    },
    tecla(ev) {                                    // celdas de texto
      if ((ev.key === 'Enter' && (ev.shiftKey || ev.ctrlKey || ev.metaKey)) || ev.key === 'Escape') { ev.preventDefault(); this.editando = null; }
    },
    // ------------------------------------------------ ejecutar
    async ejecutar(ids, { todas = false, reiniciar = false } = {}) {
      if (!this.puedeEjecutar) { avisar('Para ejecutar código hace falta instalar nbclient e ipykernel en el Python de DocsLab.', { tipo: 'error', ms: 8000 }); return; }
      clearTimeout(this._guardar);
      this.guardado = true;
      this._ultimas = todas || !ids ? this.celdas.filter((x) => x.tipo === 'codigo').map((x) => x.id) : ids;
      if (reiniciar) this.aviso = null;
      try {
        const r = await post(this.base + '/ejecutar', { celdas: this.carga(), ids, todas, reiniciar });
        this.nucleo = r.nucleo;
        if (r.celdas) this.fundir(r.celdas);
        this.sondear();
      } catch (e) { avisarError(e); }
    },
    ejecutarDesde(cel) {
      const i = this.celdas.indexOf(cel);
      this.ejecutar(this.celdas.slice(i).filter((x) => x.tipo === 'codigo').map((x) => x.id));
    },
    fundir(cambios) {
      for (const n of cambios) {
        const cel = this.celdas.find((x) => x.id === n.id);
        if (cel) { cel.salidas = n.salidas || []; cel.n = n.n; }
      }
    },
    sondear() {
      clearTimeout(this._sondeo);
      this._sondeo = setTimeout(async () => {
        try {
          const r = await api(`${this.base}/estado?rev=${this.rev}`);
          this.fundir(r.celdas);
          this.rev = r.rev; this.nucleo = r.nucleo;
          if (r.nucleo.estado === 'ocupado') { this.sondear(); return; }
          if (r.nucleo.tanda !== this.tanda) { this.tanda = r.nucleo.tanda; this.alTerminar(r.nucleo); }
        } catch (e) { this.error = e.message; }
      }, 450);
    },
    alTerminar(n) {
      this.$emit('tanda');
      if (n.error) { avisar(n.error, { tipo: 'error', ms: 9000 }); return; }
      this.revisarPaquetes();
      if (n.figuras_nuevas) {
        avisar(n.figuras_nuevas === 1 ? 'Una figura lista para el documento' : `${n.figuras_nuevas} figuras listas para el documento`);
        this.ed.recursosCambiaron();
        this.$emit('figuras');
        if (this.c.recompilar !== false) this.ed.compilarAhora();
      }
    },
    async accion(nombre, { preguntar = true } = {}) {
      this.menu = false;
      try {
        if (preguntar && nombre === 'reiniciar') {
          const ok = await confirmar({ titulo: '¿Reiniciar Python?', texto: 'Python se cierra y vuelve a arrancar en la siguiente ejecución: se borran las variables y se cargan de nuevo los paquetes (también los recién instalados). El código y las salidas del cuaderno se conservan.', aceptar: 'Reiniciar' });
          if (!ok) return;
        }
        if (preguntar && nombre === 'borrar-variables') {
          const ok = await confirmar({ titulo: '¿Borrar las variables?', texto: 'Se borran todas las variables y tablas en memoria sin reiniciar Python (es más rápido). Los paquetes ya importados siguen cargados: si instalaste o actualizaste alguno, usa «Reiniciar Python».', aceptar: 'Borrar las variables' });
          if (!ok) return;
        }
        await this.guardar();
        const r = await post(`${this.base}/${nombre}`);
        this.fundir(r.celdas); this.nucleo = r.nucleo; this.rev = r.rev;
        if (nombre === 'interrumpir') this.sondear();
        if (nombre === 'reiniciar') { this.aviso = null; avisar('Python reiniciado: la próxima celda arranca uno nuevo, con los paquetes al día'); }
        if (nombre === 'borrar-variables') avisar('Variables borradas');
      } catch (e) { avisarError(e); }
    },
    // ------------------------------------------------ paquetes nuevos o que faltan
    revisarPaquetes() {
      const hechas = (this._ultimas || []).map((id) => this.celdas.find((x) => x.id === id)).filter(Boolean);
      for (const cel of hechas) {
        const salidas = cel.salidas || [];
        const err = salidas.find((s) => s.t === 'error');
        const textos = salidas.filter((s) => s.t === 'texto').map((s) => s.texto).join('\n');
        // solo si de verdad se instaló algo («Requirement already satisfied» no pide reiniciar)
        if (RE_INSTALAR.test(cel.fuente) && !err && RE_INSTALADO.test(textos)) {
          this.aviso = { tipo: 'instalado' };
          return;
        }
        if (err && err.nombre === 'ModuleNotFoundError') {
          const m = /No module named '([^']+)'/.exec(err.valor || '');
          if (!m) continue;
          const modulo = m[1], raiz = modulo.split('.')[0];
          if (modulo.startsWith('google.colab')) {
            this.aviso = { tipo: 'colab' };
            return;
          }
          const paquete = PAQUETE_DE[raiz] || raiz;
          if (/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(paquete)) {
            this.aviso = { tipo: 'falta', modulo: raiz, paquete, celda: cel.id };
            return;
          }
        }
      }
    },
    instalarQueFalta() {
      const a = this.aviso;
      const i = this.celdas.findIndex((x) => x.id === a.celda);
      const cel = this.nueva('codigo', `%pip install ${a.paquete}`);
      this.celdas.splice(i < 0 ? this.celdas.length : i, 0, cel);
      this.aviso = null;
      this.tocar();
      this.ejecutar([cel.id]);
    },
    reiniciarDesdeAviso(todo) {
      this.aviso = null;
      if (todo) this.ejecutar(null, { todas: true, reiniciar: true });
      else this.accion('reiniciar', { preguntar: false });
    },
    // ------------------------------------------------ gráficos de plantilla
    abrirGrafico(cel) {
      if (cel && cel.meta.editado) {
        confirmar({ titulo: 'Este código se cambió a mano', texto: 'Al volver al formulario se genera de nuevo y se pierden esos cambios.', aceptar: 'Volver al formulario' })
          .then((ok) => { if (ok) this.grafico = { celda: cel.id, inicial: { plantilla: cel.meta.plantilla, valores: cel.meta.valores } }; });
        return;
      }
      this.grafico = cel ? { celda: cel.id, inicial: { plantilla: cel.meta.plantilla, valores: cel.meta.valores } } : { celda: null, inicial: null };
    },
    insertarGrafico({ codigo, meta, ejecutar }) {
      let cel = this.grafico.celda && this.celdas.find((x) => x.id === this.grafico.celda);
      if (cel) { cel.fuente = codigo; cel.meta = meta; this.tocar(); } else cel = this.agregar('codigo', undefined, codigo, meta);
      this.grafico = null;
      if (ejecutar) this.ejecutar([cel.id]);
    },
  },
  mounted() { this.cargar(); },
  beforeUnmount() { clearTimeout(this._sondeo); this.guardar(); },
  template: `
  <section class="cuaderno-lab" aria-label="Cuaderno">
    <header class="barra-lab">
      <h2 :title="c.ruta || c.nombre">{{ c.nombre }}</h2>
      <span class="chip" :class="chip.clase" role="status"><span class="punto"></span>{{ chip.texto }}</span>
      <span class="ayuda" v-if="celdas">{{ guardado ? 'Guardado' : 'Guardando…' }}</span>
      <span class="espacio"></span>
      <button class="btn pequeno" @click="agregar('codigo')" :disabled="!celdas"><icono n="mas"/>Código</button>
      <button class="btn pequeno" @click="agregar('texto')" :disabled="!celdas"><icono n="mas"/>Texto</button>
      <button class="btn pequeno" @click="abrirGrafico(null)" :disabled="!celdas"><icono n="imagen"/>Gráfico de plantilla</button>
      <span class="divisor"></span>
      <span class="grupo-ejecucion">
        <button v-if="!ocupado" class="btn pequeno primario" @click="ejecutar(null, {todas: true})" :disabled="!celdas"><icono n="play"/>Ejecutar todo</button>
      <button v-else class="btn pequeno peligro" @click="accion('interrumpir')"><icono n="parar"/>Interrumpir</button>
      <button class="btn pequeno" @click="accion('reiniciar')" :disabled="!celdas || nucleo.estado === 'apagado'"
              title="Reiniciar Python: borra las variables y vuelve a cargar los paquetes (por ejemplo, después de instalar uno)"><icono n="deshacer"/>Reiniciar</button>
      <div class="menu-contenedor">
        <button class="btn icono pequeno" @click="menu = !menu" aria-label="Más opciones de ejecución" aria-haspopup="true" :aria-expanded="menu"><icono n="puntos"/></button>
        <div class="menu" v-if="menu">
          <button @click="menu = false; ejecutar(null, {todas: true, reiniciar: true})"><icono n="play"/>Reiniciar Python y ejecutar todo</button>
          <button @click="accion('reiniciar')"><icono n="deshacer"/>Reiniciar Python (para paquetes nuevos o actualizados)</button>
          <button @click="accion('borrar-variables')" :disabled="ocupado || nucleo.estado !== 'listo'"><icono n="basura"/>Borrar las variables (sin reiniciar)</button>
          <button @click="accion('limpiar')" :disabled="ocupado"><icono n="basura"/>Limpiar todas las salidas</button>
          <p class="nota">Para instalar un paquete, escribe en una celda <code>%pip install nombre</code> y después reinicia Python.</p>
          <p class="nota">Mayús + Intro ejecuta la celda y pasa a la siguiente; Ctrl + Intro la ejecuta y se queda.</p>
        </div>
      </div>
      </span>
    </header>

    <div class="aviso-paquetes" v-if="aviso" role="status">
      <template v-if="aviso.tipo === 'instalado'">
        <span><strong>Instalaste paquetes.</strong> Reinicia Python para que el cuaderno los use (las variables se borran; el código y las salidas, no).</span>
        <button class="btn pequeno primario" @click="reiniciarDesdeAviso(false)" :disabled="ocupado"><icono n="deshacer"/>Reiniciar Python</button>
        <button class="btn pequeno" @click="reiniciarDesdeAviso(true)" :disabled="ocupado"><icono n="play"/>Reiniciar y ejecutar todo</button>
      </template>
      <template v-else-if="aviso.tipo === 'falta'">
        <span><strong>Falta el paquete «{{ aviso.modulo }}».</strong>
          <template v-if="aviso.paquete !== aviso.modulo"> Se instala con el nombre «{{ aviso.paquete }}».</template>
          Puedes añadir una celda que lo instale y después reiniciar Python.</span>
        <button class="btn pequeno primario" @click="instalarQueFalta" :disabled="ocupado"><icono n="mas"/>Añadir <code>%pip install {{ aviso.paquete }}</code></button>
      </template>
      <template v-else-if="aviso.tipo === 'colab'">
        <span><strong>Esta celda es propia de Google Colab</strong> (por ejemplo, montar Drive) y aquí no hace falta: bórrala o sáltala.</span>
      </template>
      <button class="btn icono pequeno fantasma" @click="aviso = null" aria-label="Cerrar el aviso"><icono n="cerrar"/></button>
    </div>

    <div class="celdas-lab" v-if="celdas">
      <div v-if="!celdas.length" class="vacio">
        <strong>El cuaderno está vacío.</strong>
        <span>Añade una celda de código o empieza por un gráfico de plantilla.</span>
      </div>
      <article v-for="cel in celdas" :key="cel.id" class="celda-lab" :data-celda="cel.id"
               :class="[cel.tipo, estadoCelda(cel), {elegida: sel === cel.id}]" @focusin="sel = cel.id" @click="sel = cel.id">
        <div class="margen">
          <template v-if="cel.tipo === 'codigo'">
            <button v-if="estadoCelda(cel) !== 'corriendo'" class="btn icono pequeno fantasma" @click.stop="ejecutar([cel.id])" title="Ejecutar esta celda (Ctrl + Intro)" aria-label="Ejecutar esta celda"><icono n="play"/></button>
            <button v-else class="btn icono pequeno fantasma" @click.stop="accion('interrumpir')" title="Interrumpir" aria-label="Interrumpir"><icono n="parar"/></button>
            <span class="cuenta" :title="estadoCelda(cel) === 'en-cola' ? 'En cola' : ''">[{{ marca(cel) }}]</span>
          </template>
        </div>
        <div class="contenido">
          <div class="acciones-celda">
            <button v-if="cel.meta && cel.meta.plantilla" class="btn pequeno" @click.stop="abrirGrafico(cel)" title="Volver al formulario de este gráfico"><icono n="ajustes"/>Ajustar el gráfico</button>
            <button v-if="cel.tipo === 'codigo'" class="btn icono pequeno fantasma" @click.stop="ejecutarDesde(cel)" title="Ejecutar desde aquí hasta el final" aria-label="Ejecutar desde aquí hasta el final"><icono n="abajo"/></button>
            <button class="btn icono pequeno fantasma" @click.stop="mover(cel, -1)" title="Subir" aria-label="Subir la celda"><icono n="arriba"/></button>
            <button class="btn icono pequeno fantasma" @click.stop="mover(cel, 1)" title="Bajar" aria-label="Bajar la celda"><icono n="abajo" style="opacity:.6"/></button>
            <button class="btn pequeno fantasma" @click.stop="cambiarTipo(cel)" :title="cel.tipo === 'codigo' ? 'Convertir en texto' : 'Convertir en código'">{{ cel.tipo === 'codigo' ? 'A texto' : 'A código' }}</button>
            <button class="btn icono pequeno fantasma" @click.stop="quitar(cel)" title="Borrar la celda" aria-label="Borrar la celda"><icono n="basura"/></button>
          </div>
          <div v-if="cel.tipo !== 'codigo' && editando !== cel.id" class="texto-md" v-html="html(cel) || '<p class=vacia>Celda de texto vacía: doble clic para escribir</p>'"
               @dblclick="editando = cel.id; $nextTick(() => enfocar(cel.id))" tabindex="0" @keydown.enter="editando = cel.id; $nextTick(() => enfocar(cel.id))"></div>
          <codigo-py v-else-if="cel.tipo === 'codigo'" v-model="cel.fuente" @update:model-value="alEscribir(cel)"
                     @ejecutar="ejecutar([cel.id])" @ejecutar-y-seguir="seguir(cel)" etiqueta="Código de la celda"/>
          <textarea v-else class="fuente texto" :rows="filas(cel)" v-model="cel.fuente" @input="tocar()" @keydown="tecla($event)" @blur="editando = null"
                    aria-label="Texto de la celda (Markdown)" placeholder="Texto (Markdown): # Título, **negrita**, - lista"></textarea>
          <div v-if="cel.tipo === 'codigo' && cel.salidas && cel.salidas.length" class="salidas">
            <salida-celda v-for="(s, i) in cel.salidas" :key="i" :s="s"/>
          </div>
        </div>
      </article>
      <div class="pie-celdas" v-if="celdas.length">
        <button class="btn pequeno" @click="sel = null; agregar('codigo')"><icono n="mas"/>Código</button>
        <button class="btn pequeno" @click="sel = null; agregar('texto')"><icono n="mas"/>Texto</button>
        <button class="btn pequeno" @click="sel = null; abrirGrafico(null)"><icono n="imagen"/>Gráfico de plantilla</button>
      </div>
    </div>
    <p v-else-if="error" class="mensaje error" style="margin:16px">{{ error }}</p>
    <p v-else class="ayuda" style="padding:16px">Abriendo el cuaderno…</p>

    <dialogo-grafico v-if="grafico" :nb="c.id" :inicial="grafico.inicial" @insertar="insertarGrafico" @cerrar="grafico = null"
                     @plantillas="grafico = null; $emit('plantillas')"/>
  </section>`,
};

// ---------------------------------------------------------------- plantillas de gráficos
const PlantillasGraficos = {
  name: 'plantillas-graficos',
  components: { SalidaCelda, CodigoPy },
  setup() { return { ed: inject('ed') }; },
  data: () => ({ cat: null, t: null, sucio: false, prueba: null, probando: false, guardando: false }),
  computed: {
    propias() { return this.cat ? this.cat.plantillas.filter((x) => !x.incluida) : []; },
    incluidas() { return this.cat ? this.cat.plantillas.filter((x) => x.incluida) : []; },
    tipos() { return (this.cat ? this.cat.tipos : []).map((k) => ({ valor: k, texto: NOMBRE_TIPO[k] || k })); },
    colores() { return (this.ed.modelo && this.ed.modelo.colores) || {}; },
    huecosSinParametro() {
      if (!this.t) return [];
      const nombres = new Set(this.t.parametros.map((p) => p.nombre));
      const usados = new Set([...String(this.t.codigo).matchAll(/\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}/g)].map((m) => m[1]));
      return [...usados].filter((n) => !nombres.has(n));
    },
  },
  methods: {
    nombreBib: (b) => NOMBRE_BIB[b] || b,
    async cargar(elegir) {
      try {
        this.cat = await api('api/graficos');
        if (elegir) { const t = this.cat.plantillas.find((x) => x.id === elegir); if (t) this.abrir(t, true); }
      } catch (e) { avisarError(e); }
    },
    async abrir(t, sinPreguntar) {
      if (this.sucio && !sinPreguntar) {
        const ok = await confirmar({ titulo: 'Hay cambios sin guardar', texto: 'Si abres otra plantilla se pierden.', aceptar: 'Descartar los cambios', peligro: true });
        if (!ok) return;
      }
      this.t = clonar(t); this.sucio = false; this.prueba = null;
    },
    nueva() { this.abrir({ ...clonar(this.cat.nueva), id: '', incluida: false }); },
    copiar() {
      this.t = { ...clonar(this.t), id: '', incluida: false, nombre: this.t.nombre + ' (mía)', miniatura: '' };
      this.sucio = true;
      avisar('Es una copia tuya: cambia lo que quieras y guárdala.');
    },
    agregarParametro() {
      let n = 'opcion', i = 1;
      while (this.t.parametros.some((p) => p.nombre === n)) n = 'opcion' + (++i);
      this.t.parametros.push({ nombre: n, etiqueta: 'Opción nueva', tipo: 'texto', defecto: '' });
      this.sucio = true;
    },
    cambioTipo(p) {
      p.defecto = { numero: 0, interruptor: false, columnas: [], datos: { modo: 'archivo', archivo: 'ejemplo.csv' }, paleta: 'documento', color: 'primario' }[p.tipo] ?? '';
      if (p.tipo === 'opcion' && !p.opciones) p.opciones = [];
      this.sucio = true;
    },
    listaDe(v) { return Array.isArray(v) ? v.join(', ') : ''; },
    aLista(texto) { return String(texto).split(',').map((x) => x.trim()).filter(Boolean); },
    insertarHueco(p) { this.$refs.codigo.insertar(`{{${p.nombre}}}`); this.sucio = true; },
    async probar() {
      this.probando = true;
      try { this.prueba = await post('api/graficos/probar', { plantilla: this.t, colores: this.colores, guardar_miniatura: !this.sucio && !this.t.incluida }); }
      catch (e) { avisarError(e); } finally { this.probando = false; }
    },
    async guardar() {
      this.guardando = true;
      try {
        const g = await post('api/graficos', this.t);
        this.t.id = g.id; this.sucio = false;
        // la miniatura sale de probarla con los datos de ejemplo
        this.prueba = await post('api/graficos/probar', { plantilla: this.t, colores: this.colores, guardar_miniatura: true });
        avisar(this.prueba.ok ? 'Plantilla guardada' : 'Plantilla guardada, pero al probarla dio un error', { tipo: this.prueba.ok ? 'info' : 'error' });
        await this.cargar();
      } catch (e) { avisarError(e); } finally { this.guardando = false; }
    },
    async quitar() {
      const ok = await confirmar({ titulo: `¿Borrar la plantilla «${this.t.nombre}»?`, texto: 'Los gráficos que ya hiciste con ella no cambian: su código está en sus cuadernos.', aceptar: 'Borrar', peligro: true });
      if (!ok) return;
      try { if (this.t.id) await borrar(`api/graficos/${this.t.id}`); this.t = null; this.sucio = false; await this.cargar(); } catch (e) { avisarError(e); }
    },
  },
  mounted() { this.cargar(); },
  template: `
  <section class="plantillas-graficos">
    <aside class="lista-graficos" aria-label="Plantillas de gráficos">
      <button class="btn primario" @click="nueva" :disabled="!cat"><icono n="mas"/>Plantilla nueva</button>
      <template v-if="propias.length">
        <h3>Tuyas</h3>
        <button v-for="g in propias" :key="g.id" class="fila-grafico" :class="{activo: t && t.id === g.id}" @click="abrir(g)">
          <span class="mini"><img v-if="g.miniatura" :src="g.miniatura" alt="" loading="lazy"><icono v-else n="imagen"/></span>
          <span><strong>{{ g.nombre }}</strong><span class="detalle">{{ g.biblioteca }}</span></span></button>
      </template>
      <h3>Incluidas</h3>
      <button v-for="g in incluidas" :key="g.id" class="fila-grafico" :class="{activo: t && t.id === g.id}" @click="abrir(g)">
        <span class="mini"><img v-if="g.miniatura" :src="g.miniatura" alt="" loading="lazy"><icono v-else n="imagen"/></span>
        <span><strong>{{ g.nombre }}</strong><span class="detalle">{{ g.biblioteca }}</span></span></button>
    </aside>

    <div class="editor-grafico" v-if="t">
      <header class="barra-lab">
        <h2>{{ t.nombre }}</h2>
        <span class="chip" v-if="t.incluida">Incluida</span>
        <span class="ayuda" v-else-if="sucio">Cambios sin guardar</span>
        <span class="espacio"></span>
        <button class="btn pequeno" @click="probar" :disabled="probando"><icono n="play"/>{{ probando ? 'Probando…' : 'Probar con los datos de ejemplo' }}</button>
        <button v-if="t.incluida" class="btn pequeno primario" @click="copiar"><icono n="duplicar"/>Copiar para modificarla</button>
        <template v-else>
          <button class="btn pequeno primario" @click="guardar" :disabled="guardando"><icono n="check"/>{{ guardando ? 'Guardando…' : 'Guardar' }}</button>
          <button class="btn pequeno peligro" @click="quitar"><icono n="basura"/>Borrar</button>
        </template>
      </header>
      <div class="cuerpo-grafico">
        <div class="col-codigo">
          <p v-if="t.incluida" class="mensaje" style="grid-template-columns:1fr">Las plantillas incluidas no se cambian. «Copiar para modificarla» te da una tuya con este mismo código.</p>
          <fieldset :disabled="t.incluida">
            <div class="fila-campos">
              <label class="campo"><span class="etiqueta">Nombre</span><input class="entrada" v-model="t.nombre" maxlength="80" @input="sucio = true"></label>
              <label class="campo"><span class="etiqueta">Biblioteca</span>
                <select class="entrada" v-model="t.biblioteca" @change="sucio = true"><option v-for="b in cat.bibliotecas" :key="b" :value="b">{{ nombreBib(b) }}</option></select></label>
            </div>
            <label class="campo"><span class="etiqueta">Descripción</span><input class="entrada" v-model="t.descripcion" maxlength="400" @input="sucio = true"></label>
            <div class="campo">
              <span class="etiqueta">Código Python</span>
              <div class="huecos" v-if="t.parametros.length">
                <span class="ayuda">Insertar:</span>
                <button v-for="p in t.parametros" :key="p.nombre" type="button" class="hueco" @click="insertarHueco(p)" :title="'Insertar el valor de «' + p.etiqueta + '»'">{{ '{' + '{' + p.nombre + '}' + '}' }}</button>
              </div>
              <codigo-py ref="codigo" class="grande" :key="t.id || 'nueva'" v-model="t.codigo" @update:model-value="sucio = true" :solo-lectura="t.incluida"
                         etiqueta="Código Python de la plantilla"/>
              <span class="ayuda">Cada <code>{{ '{' + '{nombre}' + '}' }}</code> se cambia por el valor del formulario, ya escrito como Python (los textos con sus comillas). Guarda la figura con <code>savefig</code> o <code>write_image</code> para que llegue al documento.</span>
              <span class="ayuda" v-if="huecosSinParametro.length" style="color:var(--rojo)">Falta definir el parámetro: {{ huecosSinParametro.join(', ') }}</span>
            </div>
            <div class="campo">
              <span class="etiqueta">Parámetros del formulario</span>
              <div class="tabla-parametros">
                <div class="cabeza"><span>Nombre en el código</span><span>Rótulo</span><span>Tipo</span><span>Valor inicial</span><span></span></div>
                <div v-for="(p, i) in t.parametros" :key="i" class="fila-par">
                  <input class="entrada codigo" v-model.trim="p.nombre" @input="sucio = true" aria-label="Nombre en el código">
                  <input class="entrada" v-model="p.etiqueta" @input="sucio = true" aria-label="Rótulo">
                  <select class="entrada" v-model="p.tipo" @change="cambioTipo(p)" aria-label="Tipo"><option v-for="o in tipos" :key="o.valor" :value="o.valor">{{ o.texto }}</option></select>
                  <span class="defecto">
                    <span v-if="p.tipo === 'datos'" class="ayuda">ejemplo.csv</span>
                    <input v-else-if="p.tipo === 'numero'" class="entrada" type="number" step="any" v-model.number="p.defecto" @input="sucio = true" aria-label="Valor inicial">
                    <input v-else-if="p.tipo === 'interruptor'" type="checkbox" v-model="p.defecto" @change="sucio = true" aria-label="Valor inicial">
                    <input v-else-if="p.tipo === 'columnas'" class="entrada" :value="listaDe(p.defecto)" @change="p.defecto = aLista($event.target.value); sucio = true" placeholder="valor, peso" aria-label="Columnas iniciales">
                    <select v-else-if="p.tipo === 'paleta'" class="entrada" v-model="p.defecto" @change="sucio = true" aria-label="Valor inicial"><option v-for="o in cat.paletas" :key="o" :value="o">{{ o }}</option></select>
                    <input v-else class="entrada" v-model="p.defecto" @input="sucio = true" :placeholder="p.tipo === 'color' ? 'primario o #336699' : ''" aria-label="Valor inicial">
                    <input v-if="p.tipo === 'opcion'" class="entrada" :value="listaDe(p.opciones)" @change="p.opciones = aLista($event.target.value); sucio = true" placeholder="opciones, separadas, por comas" aria-label="Opciones">
                    <label v-if="p.tipo === 'columna' || p.tipo === 'columnas'" class="mini-casilla"><input type="checkbox" v-model="p.numerica" @change="sucio = true">numérica</label>
                    <label v-if="p.tipo === 'columna'" class="mini-casilla"><input type="checkbox" v-model="p.opcional" @change="sucio = true">opcional</label>
                  </span>
                  <button type="button" class="btn icono pequeno fantasma" @click="t.parametros.splice(i, 1); sucio = true" aria-label="Quitar el parámetro"><icono n="cerrar"/></button>
                </div>
              </div>
              <button type="button" class="btn pequeno" style="justify-self:start" @click="agregarParametro"><icono n="mas"/>Parámetro</button>
            </div>
          </fieldset>
        </div>
        <aside class="col-prueba">
          <h3>Prueba</h3>
          <template v-if="prueba">
            <div v-if="prueba.imagen" class="salida figura"><img :src="prueba.imagen" alt="Resultado de la prueba"></div>
            <salida-celda v-else-if="prueba.plotly" :s="{t: 'plotly', figura: prueba.plotly}"/>
            <p v-else-if="prueba.ok" class="ayuda">El código terminó bien, pero no dibujó ninguna figura.</p>
            <pre v-if="prueba.error" class="salida error">{{ prueba.error }}</pre>
            <pre v-if="prueba.salida" class="salida texto">{{ prueba.salida }}</pre>
          </template>
          <template v-else>
            <span class="mini grande" v-if="t.miniatura"><img :src="t.miniatura" alt=""></span>
            <p class="ayuda">«Probar» ejecuta el código con los valores iniciales y los datos de ejemplo: <code>ejemplo.csv</code> (grupo, tratamiento, tiempo, valor, peso y altura), <code>ejemplo_series.csv</code>, <code>ejemplo_paises.csv</code>, <code>ejemplo_puntos.csv</code>, <code>ejemplo_conexiones.csv</code>, <code>ejemplo_red.csv</code>, <code>ejemplo_flujos.csv</code>, <code>ejemplo_jerarquia.csv</code>, <code>ejemplo_puntuaciones.csv</code>, <code>ejemplo_palabras.csv</code> y el mapa <code>mundo.geojson</code>.</p>
          </template>
        </aside>
      </div>
    </div>
    <div v-else class="vacio" style="margin:24px;align-self:start">
      <strong>Plantillas de gráficos</strong>
      <span>Una plantilla es código Python con huecos que se rellenan desde un formulario: datos, columnas, textos y colores. Abre una incluida para ver cómo está hecha, cópiala para cambiarla o crea una desde cero. Sirven para todos tus documentos.</span>
    </div>
  </section>`,
};

// ---------------------------------------------------------------- la vista LAB del editor
export const LabDocumento = {
  name: 'lab-documento',
  components: { PanelCuadernos, CuadernoLab, PlantillasGraficos },
  setup() { return { ed: inject('ed') }; },
  data: () => ({ seccion: 'cuadernos', actual: null, figuras: null, verFiguras: true }),
  watch: {
    // los editores de código se miden al mostrarse
    'ed.vistaLab'(v) { if (v) this.$nextTick(() => window.dispatchEvent(new Event('resize'))); },
    seccion() { this.$nextTick(() => window.dispatchEvent(new Event('resize'))); },
  },
  methods: {
    fecha,
    abrir(c) { this.actual = c; this.cargarFiguras(); },
    alCambiarLista(lista) {
      if (this.actual) this.actual = lista.find((x) => x.id === this.actual.id) || null;
      if (!this.actual && lista.length) this.abrir(lista[0]);
    },
    async cargarFiguras() {
      if (!this.actual) { this.figuras = null; return; }
      try { this.figuras = await api(`api/proyectos/${this.ed.pid}/cuadernos/${this.actual.id}/figuras`); } catch (e) { this.figuras = []; }
    },
    vista(f) { return `api/proyectos/${this.ed.pid}/vista?ruta=${encodeURIComponent(f.ruta)}&v=${encodeURIComponent(f.fecha)}`; },
    usar(f) {
      this.ed.usarImagen(f.ruta);
      this.ed.vistaLab = false;
    },
    async nuevo() {
      const nombre = await preguntar({ titulo: 'Cuaderno nuevo', etiqueta: 'Nombre', valor: 'Análisis', aceptar: 'Crear' });
      if (!nombre) return;
      try {
        const c = await post(`api/proyectos/${this.ed.pid}/cuadernos`, { nuevo: nombre });
        await this.$refs.lista.cargar();
        this.abrir(c);
      } catch (e) { avisarError(e); }
    },
  },
  template: `
  <div class="lab-doc">
    <nav class="sub-lab" aria-label="Secciones del LAB">
      <div class="segmentos sin-cortes" role="tablist">
        <button role="tab" :aria-selected="seccion === 'cuadernos'" :class="{activo: seccion === 'cuadernos'}" @click="seccion = 'cuadernos'">Cuadernos</button>
        <button role="tab" :aria-selected="seccion === 'graficos'" :class="{activo: seccion === 'graficos'}" @click="seccion = 'graficos'">Plantillas de gráficos</button>
      </div>
      <span class="ayuda solo-ancho" v-if="seccion === 'cuadernos'">Los cuadernos de Python de este documento. Las figuras que guardan quedan listas para usarlas en él.</span>
      <span class="ayuda solo-ancho" v-else>Tipos de gráfico con formulario y código editable. Sirven para todos tus documentos.</span>
    </nav>

    <div class="cuerpo-lab" v-show="seccion === 'cuadernos'">
      <aside class="panel izq" aria-label="Cuadernos del documento">
        <div class="contenido-panel">
          <div style="padding:10px 10px 0"><button class="btn primario" style="width:100%" @click="nuevo"><icono n="mas"/>Cuaderno nuevo</button></div>
          <panel-cuadernos ref="lista" en-lab :activo="actual && actual.id" @abrir="abrir" @lista="alCambiarLista" @figuras="cargarFiguras"/>
        </div>
      </aside>
      <cuaderno-lab v-if="actual" :c="actual" :key="actual.id" @figuras="cargarFiguras" @tanda="$refs.lista.cargar()" @plantillas="seccion = 'graficos'"/>
      <div v-else class="vacio" style="margin:24px;align-self:start">
        <strong>Aquí se escriben y se ejecutan los cuadernos.</strong>
        <span>Crea uno nuevo o sube un .ipynb de Colab o Jupyter. Puedes ejecutarlo entero o celda por celda, y añadir gráficos desde una plantilla.</span>
      </div>
      <aside class="panel der figuras-lab" v-if="actual" aria-label="Figuras del cuaderno">
        <div class="contenido-panel">
          <h3>Figuras del cuaderno</h3>
          <p class="ayuda" v-if="figuras && !figuras.length">Todavía no hay. Aparecen aquí cuando el código guarda una imagen (PDF, PNG o JPG) en la carpeta del cuaderno.</p>
          <p class="ayuda" v-else>Elige en el documento dónde va (una caja o un elemento con imagen) y pulsa «Usar».</p>
          <div class="galeria compacta" style="padding:0">
            <div v-for="f in figuras || []" :key="f.ruta" class="recurso" :title="f.ruta">
              <span class="miniatura"><img :src="vista(f)" alt="" loading="lazy"></span>
              <span class="nombre-rec">{{ f.nombre }}</span>
              <span class="meta-rec">{{ fecha(f.fecha) }}</span>
              <button class="btn pequeno" @click="usar(f)"><icono n="usar"/>Usar</button>
            </div>
          </div>
        </div>
      </aside>
    </div>
    <plantillas-graficos v-if="seccion === 'graficos'"/>
  </div>`,
};
