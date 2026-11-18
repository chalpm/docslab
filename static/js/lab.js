// SPDX-License-Identifier: AGPL-3.0-only
// Componente Lab: hacer y recrear componentes para las cajas del documento,
// sin código (piezas), con código LaTeX (plantilla con {{campos}}) o como
// preajuste de uno de los componentes incluidos.
import { api, post, put, borrar, subir, descargar } from './api.js';
import { tienda, avisar, avisarError, confirmar, ir } from './tienda.js';
import { retrasar, clonar, nuevoId, fecha, textoPlano } from './util.js';
import { CAMPOS } from './campos.js';
import { svgCaja, NOMBRES_ESTILO } from './dibujos.js';

const { reactive, provide, markRaw } = Vue;

const LOGO = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="8" cy="8" r="4.4"/><path d="M8 .8v14.4M.8 8h14.4"/></svg>';
const NOMBRE_CAMPO = /^[A-Za-z_][A-Za-z0-9_]{0,39}$/;
const RESERVADOS = new Set(['id', 'tipo', 'visible']);
const ICONO_PIEZA = { titulo: 'titulo', texto: 'texto', cifra: 'letra', etiqueta: 'cita', imagen: 'imagen', lista: 'revisar',
  icono: 'forma', separador: 'pie', espacio: 'estirar', latex: 'codigo', columnas: 'fila' };
const NOMBRES_MODO = { visual: 'Sin código', latex: 'Con código LaTeX', preajuste: 'Preajuste de un incluido' };
const ANCHOS = { estrecha: 'Estrecha (A0 en 4 columnas)', media: 'Media (A0 en 3 columnas)', ancha: 'Ancha (A0 en 2 columnas)' };
const COLORES_TEMA = [['pcPrimario', 'primario'], ['pcSecundario', 'secundario'], ['pcAcento', 'acento'], ['pcTexto', 'texto'],
  ['pcTenue', 'tenue'], ['pcBloque', 'fondo_bloque'], ['pcFondo', 'fondo'], ['pcContraste', 'contraste']];

// ---------------------------------------------------------------- piezas y puntos de partida
function pieza(tipo, extra = {}) {
  const d = clonar(tienda.catalogo.componentes.defectos_pieza[tipo] || {});
  return { id: nuevoId('p'), tipo, ...d, ...extra };
}

const CODIGO_EJEMPLO = `% Escribe LaTeX y pon {{campo}} donde va cada dato que se rellena en el inspector.
% {{#campo}}…{{/campo}} sale solo si el campo tiene algo; {{^campo}}…{{/campo}}, solo si está vacío.
\\PC@antes
{\\color{pcPrimario}\\bfseries\\tam{1.3}{{titulo}}\\par}
\\vspace{0.3em}
{{texto}}
{{#nota}}\\par{\\color{pcTenue}\\itshape\\tam{0.85}{{nota}}\\par}{{/nota}}
\\PC@despues
`;

const INICIOS = [
  { clave: 'visual', nombre: 'En blanco, sin código', texto: 'Junta piezas: títulos, textos, cifras, imágenes, iconos…', icono: 'pieza',
    datos: () => ({ modo: 'visual', nombre: 'Componente nuevo', diseno: { caja: { estilo: 'resaltado' }, alineacion: 'izquierda', separacion: '0.45em',
      piezas: [pieza('titulo'), pieza('texto')] } }) },
  { clave: 'latex', nombre: 'En blanco, con código', texto: 'Una plantilla LaTeX con huecos {{campo}}.', icono: 'codigo',
    datos: () => ({ modo: 'latex', nombre: 'Componente nuevo', codigo: CODIGO_EJEMPLO, preambulo: '', campos: [
      { nombre: 'titulo', tipo: 'texto', etiqueta: 'Título', defecto: 'Título' },
      { nombre: 'texto', tipo: 'parrafo', etiqueta: 'Texto', defecto: 'Texto de ejemplo con **negrita** y una fórmula $x^2$.' },
      { nombre: 'nota', tipo: 'texto', etiqueta: 'Nota (opcional)', defecto: '' }] }) },
  { clave: 'cifra', nombre: 'Tarjeta con cifra', texto: 'Etiqueta, una cifra grande y su explicación.', icono: 'letra',
    datos: () => ({ modo: 'visual', nombre: 'Tarjeta con cifra', diseno: { caja: { estilo: 'resaltado' }, alineacion: 'centro', separacion: '0.3em',
      piezas: [pieza('etiqueta', { valor: 'Resultado', etiqueta_campo: 'Etiqueta' }), pieza('cifra', { valor: '87 %', etiqueta_campo: 'Cifra' }),
        pieza('texto', { valor: 'de las muestras tenían el gen.', escala: 0.9, color: 'tenue', etiqueta_campo: 'Explicación' })] } }) },
  { clave: 'icono', nombre: 'Idea con icono', texto: 'Un icono en un círculo junto a un título y un texto.', icono: 'forma',
    datos: () => ({ modo: 'visual', nombre: 'Idea con icono', diseno: { caja: { estilo: 'sin-caja' }, alineacion: 'izquierda', separacion: '0.2em',
      piezas: [pieza('columnas', { separacion: '0.8em', alinear: 'arriba', columnas: [
        { ancho: 14, piezas: [pieza('icono', { valor: '51', escala: 1.6, alineacion: 'centro' })] },
        { ancho: 86, piezas: [pieza('titulo', { valor: 'Una idea clave', escala: 1.1 }), pieza('texto', { valor: 'Explícala en una o dos frases.', etiqueta_campo: 'Texto' })] }] })] } }) },
  { clave: 'perfil', nombre: 'Persona del equipo', texto: 'Foto redonda, nombre, cargo y una etiqueta.', icono: 'persona',
    datos: () => ({ modo: 'visual', nombre: 'Persona del equipo', diseno: { caja: { estilo: 'simple' }, alineacion: 'izquierda', separacion: '0.15em',
      piezas: [pieza('columnas', { separacion: '1em', alinear: 'centro', columnas: [
        { ancho: 28, piezas: [pieza('imagen', { circulo: true, ancho: 100, etiqueta_campo: 'Foto' })] },
        { ancho: 72, piezas: [pieza('titulo', { valor: 'Nombre Apellido', escala: 1.15, etiqueta_campo: 'Nombre' }),
          pieza('texto', { valor: 'Laboratorio de Genómica', color: 'tenue', etiqueta_campo: 'Cargo o grupo' }),
          pieza('etiqueta', { valor: 'Contacto', escala: 0.7, etiqueta_campo: 'Etiqueta' })] }] })] } }) },
  { clave: 'mensaje', nombre: 'Mensaje para llevar', texto: 'Texto claro sobre el color principal, centrado.', icono: 'cabecera',
    datos: () => ({ modo: 'visual', nombre: 'Mensaje para llevar', diseno: { caja: { estilo: 'invertido' }, alineacion: 'centro', separacion: '0.35em',
      piezas: [pieza('titulo', { valor: 'Mensaje para llevar', color: 'contraste', escala: 1.2 }),
        pieza('texto', { valor: 'La conclusión principal en una frase.', color: 'contraste', etiqueta_campo: 'Mensaje' })] } }) },
];

// ---------------------------------------------------------------- vista previa recortada
const VistaRecorte = {
  name: 'vista-recorte',
  props: { pdf: String, caja: Object, papel: Object },
  data: () => ({ error: '', medida: '' }),
  watch: { pdf() { this.dibujar(); } },
  methods: {
    async dibujar() {
      const turno = (this.turno = (this.turno || 0) + 1);
      if (!this.pdf || !this.caja || !this.papel || !window.pdfjsLib) return;
      try {
        const doc = await window.pdfjsLib.getDocument({ url: this.pdf, isEvalSupported: false }).promise;
        if (turno !== this.turno) { doc.destroy(); return; }
        const pag = await doc.getPage(1);
        const vp1 = pag.getViewport({ scale: 1 });
        const k = vp1.width / this.papel.ancho;          // unidades del PDF por pt de TeX
        const m = 10;
        const x0 = Math.max(0, this.caja.x0 - m) * k, y0 = Math.max(0, this.caja.y0 - m) * k;
        const w = (this.caja.x1 - this.caja.x0 + 2 * m) * k, h = (this.caja.y1 - this.caja.y0 + 2 * m) * k;
        const disponible = Math.max(160, (this.$refs.marco && this.$refs.marco.clientWidth) || 320);
        const css = disponible / w;
        const dpr = Math.min(3, window.devicePixelRatio || 1);
        const s = css * dpr;
        const lienzo = document.createElement('canvas');
        lienzo.width = Math.ceil(w * s);
        lienzo.height = Math.ceil(h * s);
        lienzo.style.width = `${Math.round(w * css)}px`;
        lienzo.style.height = `${Math.round(h * css)}px`;
        lienzo.setAttribute('role', 'img');
        lienzo.setAttribute('aria-label', 'Vista previa del componente');
        await pag.render({ canvasContext: lienzo.getContext('2d'), viewport: pag.getViewport({ scale: s, offsetX: -x0 * s, offsetY: -y0 * s }) }).promise;
        doc.destroy();
        if (turno !== this.turno || !this.$refs.marco) return;
        this.$refs.marco.replaceChildren(lienzo);
        this.medida = `${Math.round((this.caja.x1 - this.caja.x0) / 72.27 * 25.4)} × ${Math.round((this.caja.y1 - this.caja.y0) / 72.27 * 25.4)} mm`;
        this.error = '';
      } catch (e) {
        if (e && e.name !== 'RenderingCancelledException') this.error = 'No se pudo dibujar la vista previa.';
      }
    },
  },
  mounted() {
    this.dibujar();
    this.observador = new ResizeObserver(retrasar(() => this.dibujar(), 150));
    this.observador.observe(this.$refs.marco);
  },
  beforeUnmount() { if (this.observador) this.observador.disconnect(); },
  template: `
    <div class="recorte">
      <div class="marco-recorte" ref="marco"></div>
      <div class="pie-recorte"><span>{{ medida }}</span><span v-if="error" class="ayuda">{{ error }}</span></div>
    </div>`,
};

// ---------------------------------------------------------------- editor de código (CodeMirror)
const EditorCodigo = {
  name: 'editor-codigo',
  props: { modelValue: String, errores: Array, etiqueta: String, minimo: { type: Number, default: 180 } },
  emits: ['update:modelValue'],
  watch: {
    modelValue(v) {
      if (!this.cm || (v || '') === this.cm.getValue()) return;
      const c = this.cm.getCursor();
      this.cm.setValue(v || '');
      this.cm.setCursor(c);
    },
    errores: { deep: true, handler() { this.marcar(); } },
  },
  methods: {
    insertar(texto) { this.cm.replaceSelection(texto); this.cm.focus(); },
    enfocarLinea(n) { if (!this.cm || !n) return; this.cm.setCursor({ line: n - 1, ch: 0 }); this.cm.scrollIntoView({ line: n - 1, ch: 0 }, 80); this.cm.focus(); },
    marcar() {
      if (!this.cm) return;
      for (const l of this.marcadas || []) this.cm.removeLineClass(l, 'background', 'linea-error');
      this.marcadas = (this.errores || []).filter((e) => e.linea && e.linea <= this.cm.lineCount())
        .map((e) => this.cm.addLineClass(e.linea - 1, 'background', 'linea-error'));
    },
  },
  mounted() {
    this.cm = markRaw(window.CodeMirror(this.$refs.caja, {
      value: this.modelValue || '', mode: 'stex', lineNumbers: true, lineWrapping: true, matchBrackets: true,
      autoCloseBrackets: true, styleActiveLine: true, tabSize: 2, indentUnit: 2, viewportMargin: Infinity,
      extraKeys: { Tab: (cm) => cm.replaceSelection('  ') },
    }));
    this.cm.addOverlay({
      token(stream) {
        if (stream.match(/\{\{\s*[#^/]?\s*(?:[A-Za-z_][A-Za-z0-9_]*|\.|[0-9])\s*\}\}/)) return 'campo';
        while (stream.next() != null) { if (stream.match(/\{\{/, false)) break; }
        return null;
      },
    });
    this.cm.getWrapperElement().style.minHeight = `${this.minimo}px`;
    this.cm.on('change', () => { const v = this.cm.getValue(); if (v !== (this.modelValue || '')) this.$emit('update:modelValue', v); });
    this.$nextTick(() => { this.cm.refresh(); this.marcar(); });
  },
  template: `<div class="editor-codigo" ref="caja" :aria-label="etiqueta"></div>`,
};

// ---------------------------------------------------------------- campos (modo código)
const EditorCampos = {
  name: 'editor-campos',
  props: { campos: Array },
  emits: ['insertar'],
  computed: {
    tipos() { return Object.entries(tienda.catalogo.componentes.tipos).map(([k, v]) => ({ valor: k, texto: v })); },
    repetidos() {
      const vistos = new Set(), rep = new Set();
      for (const c of this.campos) { if (vistos.has(c.nombre)) rep.add(c.nombre); vistos.add(c.nombre); }
      return rep;
    },
  },
  methods: {
    valido(c) { return NOMBRE_CAMPO.test(c.nombre || '') && !RESERVADOS.has(c.nombre) && !this.repetidos.has(c.nombre); },
    agregar() {
      let n = 1;
      while (this.campos.some((c) => c.nombre === `campo${n}`)) n++;
      this.campos.push({ nombre: `campo${n}`, tipo: 'texto', etiqueta: `Campo ${n}`, defecto: '' });
    },
    quitar(i) { this.campos.splice(i, 1); },
    subir(i) { if (i > 0) { const [x] = this.campos.splice(i, 1); this.campos.splice(i - 1, 0, x); } },
    cambiarTipo(c, tipo) {
      c.tipo = tipo;
      const d = { lista: [], pares: [], hitos: [], booleano: false, numero: 1, porcentaje: 100, fraccion: 0.5, angulo: 0 };
      c.defecto = tipo in d ? clonar(d[tipo]) : (typeof c.defecto === 'string' ? c.defecto : '');
      if (tipo === 'seleccion' && !Array.isArray(c.opciones)) { c.opciones = [{ valor: 'a', texto: 'Opción A' }, { valor: 'b', texto: 'Opción B' }]; c.defecto = 'a'; }
    },
    lineas(c) {
      if (c.tipo === 'lista') return (c.defecto || []).join('\n');
      if (c.tipo === 'pares' || c.tipo === 'hitos') return (c.defecto || []).map((p) => `${p[0]} | ${p[1]}`).join('\n');
      if (c.tipo === 'seleccion') return (c.opciones || []).map((o) => (o.texto && o.texto !== o.valor ? `${o.valor} = ${o.texto}` : o.valor)).join('\n');
      return '';
    },
    ponerLineas(c, texto) {
      const ls = texto.split('\n');
      if (c.tipo === 'lista') c.defecto = ls;
      else if (c.tipo === 'pares' || c.tipo === 'hitos') c.defecto = ls.filter((l) => l.trim()).map((l) => { const [a, ...b] = l.split('|'); return [a.trim(), b.join('|').trim()]; });
      else if (c.tipo === 'seleccion') {
        c.opciones = ls.filter((l) => l.trim()).map((l) => { const [v, ...t] = l.split('='); return { valor: v.trim(), texto: (t.join('=').trim() || v.trim()) }; });
        if (!c.opciones.some((o) => o.valor === c.defecto) && c.opciones.length) c.defecto = c.opciones[0].valor;
      }
    },
  },
  template: `
    <div class="campos-lab">
      <div v-for="(c, i) in campos" :key="i" class="campo-lab">
        <div class="fila-campo-lab">
          <input class="entrada codigo" :class="{invalida: !valido(c)}" v-model.trim="c.nombre" aria-label="Nombre del campo" spellcheck="false" title="Nombre para la plantilla: letras, números y _">
          <input class="entrada" v-model="c.etiqueta" aria-label="Etiqueta en el inspector" placeholder="Etiqueta en el inspector">
          <select class="entrada" :value="c.tipo" @change="cambiarTipo(c, $event.target.value)" aria-label="Tipo de campo">
            <option v-for="t in tipos" :key="t.valor" :value="t.valor">{{ t.texto }}</option>
          </select>
          <span class="acciones-campo">
            <button type="button" class="btn pequeno" @click="$emit('insertar', '{{' + c.nombre + '}}')" :title="'Escribir {{' + c.nombre + '}} donde está el cursor'">{{ '{' + '{' }}{{ c.nombre }}{{ '}' + '}' }}</button>
            <button type="button" class="btn icono pequeno fantasma" @click="subir(i)" :disabled="i === 0" aria-label="Subir"><icono n="arriba"/></button>
            <button type="button" class="btn icono pequeno fantasma" @click="quitar(i)" aria-label="Quitar el campo"><icono n="basura"/></button>
          </span>
        </div>
        <div class="valor-campo-lab">
          <span class="ayuda" v-if="!valido(c)">El nombre empieza por una letra, solo lleva letras, números o _, y no se repite.</span>
          <template v-if="c.tipo === 'parrafo' || c.tipo === 'latex'">
            <textarea class="entrada" :class="{codigo: c.tipo === 'latex'}" rows="2" v-model="c.defecto" placeholder="Valor de ejemplo" aria-label="Valor de ejemplo"></textarea>
          </template>
          <template v-else-if="['lista', 'pares', 'hitos', 'seleccion'].includes(c.tipo)">
            <textarea class="entrada" rows="3" :value="lineas(c)" @input="ponerLineas(c, $event.target.value)" :aria-label="c.tipo === 'seleccion' ? 'Opciones' : 'Valor de ejemplo'"
              :placeholder="c.tipo === 'seleccion' ? 'valor = texto que se ve (una por línea)' : c.tipo === 'lista' ? 'Un elemento por línea' : 'término | descripción (uno por línea)'"></textarea>
            <label v-if="c.tipo === 'seleccion'" class="campo"><span class="etiqueta">Opción inicial</span>
              <select class="entrada" v-model="c.defecto"><option v-for="o in c.opciones" :key="o.valor" :value="o.valor">{{ o.texto }}</option></select></label>
          </template>
          <label v-else-if="c.tipo === 'booleano'" class="interruptor"><span class="texto">Valor inicial: {{ c.defecto ? 'sí' : 'no' }}</span>
            <input type="checkbox" v-model="c.defecto"><span class="pista"></span></label>
          <input v-else-if="['numero', 'porcentaje', 'fraccion', 'angulo'].includes(c.tipo)" class="entrada" type="number" step="any" v-model.number="c.defecto" aria-label="Valor de ejemplo">
          <span v-else-if="['imagen', 'tabla', 'flechas'].includes(c.tipo)" class="ayuda">Se elige en el documento; en la vista previa se ve un recuadro de muestra.</span>
          <input v-else class="entrada" :class="{codigo: c.tipo === 'dimension' || c.tipo === 'color'}" v-model="c.defecto" aria-label="Valor de ejemplo"
            :placeholder="c.tipo === 'color' ? 'acento, primario!20 o 1F4E79' : c.tipo === 'dimension' ? '2em, 12mm…' : 'Valor de ejemplo'">
        </div>
      </div>
      <button type="button" class="btn pequeno" style="justify-self:start" @click="agregar"><icono n="mas"/>Añadir un campo</button>
    </div>`,
};

// ---------------------------------------------------------------- piezas (modo sin código)
const EditorPieza = {
  name: 'editor-pieza',
  components: { ...CAMPOS },
  props: { p: Object, i: Number, total: Number, anidada: Boolean },
  emits: ['subir', 'bajar', 'quitar', 'duplicar'],
  data: () => ({ abierta: false }),
  computed: {
    cat() { return tienda.catalogo.componentes; },
    nombre() { return this.cat.piezas[this.p.tipo]; },
    resumen() {
      const v = this.p.valor;
      if (Array.isArray(v)) return v.filter(Boolean).join(', ');
      if (this.p.tipo === 'icono') { const x = this.cat.iconos.find((o) => o[0] === String(v)); return x ? x[1] : ''; }
      if (this.p.tipo === 'latex') return textoPlano(this.p.codigo, 40);
      if (this.p.tipo === 'columnas') return `${this.p.columnas.length} columnas`;
      return textoPlano(v, 48);
    },
    editableDisponible() { return ['titulo', 'texto', 'cifra', 'etiqueta', 'lista', 'icono'].includes(this.p.tipo); },
    alineaciones() {
      const o = [{ valor: '', texto: 'Igual' }, { valor: 'izquierda', texto: 'Izq.' }, { valor: 'centro', texto: 'Centro' }, { valor: 'derecha', texto: 'Der.' }];
      if (this.p.tipo === 'texto') o.push({ valor: 'justificado', texto: 'Justif.' });
      return o;
    },
    iconos() { return this.cat.iconos.map(([valor, texto]) => ({ valor, texto })); },
    vinetas() { return [['cuadrado', 'Cuadrado'], ['punto', 'Punto'], ['guion', 'Guion'], ['flecha', 'Flecha'], ['check', 'Marca'], ['numero', 'Números']].map(([valor, texto]) => ({ valor, texto })); },
    listaTexto: {
      get() { return (this.p.valor || []).join('\n'); },
      set(v) { this.p.valor = v.split('\n'); },
    },
  },
  methods: {
    agregarColumna() { if (this.p.columnas.length < 3) { this.p.columnas.push({ ancho: 33, piezas: [] }); } },
    quitarColumna(k) { if (this.p.columnas.length > 1) this.p.columnas.splice(k, 1); },
  },
  created() { this.icono = ICONO_PIEZA; },
  template: `
    <div class="pieza-lab" :class="{abierta}">
      <div class="cabeza-pieza">
        <button type="button" class="btn fantasma abrir-pieza" @click="abierta = !abierta" :aria-expanded="abierta">
          <icono :n="icono[p.tipo] || 'pieza'"/><strong>{{ nombre }}</strong><span class="resumen-pieza">{{ resumen }}</span>
        </button>
        <span v-if="p.editable" class="insignia-campo" :title="'Se rellena en el inspector como «' + (p.etiqueta_campo || nombre) + '»'">en el documento</span>
        <button type="button" class="btn icono pequeno fantasma" @click="$emit('subir')" :disabled="i === 0" aria-label="Subir"><icono n="arriba"/></button>
        <button type="button" class="btn icono pequeno fantasma" @click="$emit('bajar')" :disabled="i === total - 1" aria-label="Bajar"><icono n="abajo"/></button>
        <button type="button" class="btn icono pequeno fantasma" @click="$emit('duplicar')" aria-label="Duplicar"><icono n="duplicar"/></button>
        <button type="button" class="btn icono pequeno fantasma" @click="$emit('quitar')" aria-label="Quitar la pieza"><icono n="basura"/></button>
      </div>
      <div v-if="abierta" class="cuerpo-pieza">
        <template v-if="editableDisponible">
          <label class="interruptor"><span class="texto">Se cambia en cada documento</span><input type="checkbox" v-model="p.editable"><span class="pista"></span></label>
          <c-texto v-if="p.editable" :obj="p" clave="etiqueta_campo" etiqueta="Nombre del campo en el inspector"/>
        </template>
        <p v-if="p.tipo === 'imagen'" class="ayuda">La imagen se elige en cada documento (aquí se ve un recuadro de muestra).</p>
        <c-texto v-if="p.tipo === 'imagen'" :obj="p" clave="etiqueta_campo" etiqueta="Nombre del campo en el inspector"/>

        <c-texto v-if="['titulo', 'cifra', 'etiqueta'].includes(p.tipo)" :obj="p" clave="valor" :etiqueta="p.editable ? 'Texto de ejemplo' : 'Texto'" formato/>
        <c-parrafo v-if="p.tipo === 'texto'" :obj="p" clave="valor" :etiqueta="p.editable ? 'Texto de ejemplo' : 'Texto'" :filas="3"/>
        <div v-if="p.tipo === 'lista'" class="campo"><label class="etiqueta">{{ p.editable ? 'Elementos de ejemplo' : 'Elementos' }} (uno por línea)</label>
          <textarea class="entrada" rows="3" v-model="listaTexto"></textarea></div>
        <c-seleccion v-if="p.tipo === 'icono'" :obj="p" clave="valor" :etiqueta="p.editable ? 'Icono inicial' : 'Icono'" :opciones="iconos"/>
        <div v-if="p.tipo === 'latex'" class="campo"><label class="etiqueta">Código LaTeX</label>
          <textarea class="entrada codigo" rows="4" v-model="p.codigo" spellcheck="false"></textarea></div>

        <div class="fila-campos" v-if="['titulo', 'texto', 'cifra', 'etiqueta', 'icono'].includes(p.tipo)">
          <c-numero :obj="p" clave="escala" etiqueta="Tamaño (× letra)" :min="0.3" :max="12" :paso="0.05"/>
          <c-segmentos :obj="p" clave="alineacion" etiqueta="Alineación" :opciones="alineaciones"/>
        </div>
        <div class="fila-campos" v-if="['titulo', 'texto', 'cifra'].includes(p.tipo)">
          <c-interruptor :obj="p" clave="negrita" etiqueta="Negrita"/>
          <c-interruptor :obj="p" clave="cursiva" etiqueta="Cursiva"/>
        </div>
        <c-color v-if="['titulo', 'texto', 'cifra', 'etiqueta', 'icono', 'separador'].includes(p.tipo)" :obj="p" clave="color"
                 :etiqueta="p.tipo === 'etiqueta' || p.tipo === 'icono' ? 'Color del texto' : 'Color'" vacio="El del texto"/>
        <c-color v-if="p.tipo === 'etiqueta' || p.tipo === 'icono'" :obj="p" clave="fondo" etiqueta="Fondo" vacio="Acento"/>
        <c-interruptor v-if="p.tipo === 'icono'" :obj="p" clave="circulo" etiqueta="Dentro de un círculo"/>

        <template v-if="p.tipo === 'imagen'">
          <c-deslizador :obj="p" clave="ancho" etiqueta="Ancho (% del espacio)" :min="10" :max="100" :paso="1"/>
          <c-interruptor :obj="p" clave="circulo" etiqueta="Recorte circular"/>
          <template v-if="!p.circulo">
            <c-deslizador :obj="p" clave="alto" etiqueta="Alto (% del ancho; 0 = el de la imagen)" :min="0" :max="150" :paso="1"/>
            <c-interruptor :obj="p" clave="redondeo" etiqueta="Esquinas redondeadas"/>
          </template>
          <c-segmentos :obj="p" clave="alineacion" etiqueta="Alineación" :opciones="alineaciones.slice(1, 4)"/>
        </template>
        <template v-if="p.tipo === 'lista'">
          <c-seleccion :obj="p" clave="vineta" etiqueta="Viñeta" :opciones="vinetas"/>
          <c-color :obj="p" clave="color" etiqueta="Color de la viñeta" vacio="Acento"/>
        </template>
        <template v-if="p.tipo === 'separador'">
          <div class="fila-campos">
            <c-dimension :obj="p" clave="grosor" etiqueta="Grosor" placeholder="0.08em"/>
            <c-numero :obj="p" clave="ancho" etiqueta="Ancho (%)" :min="5" :max="100" :paso="1"/>
          </div>
          <c-segmentos :obj="p" clave="alineacion" etiqueta="Alineación" :opciones="alineaciones"/>
        </template>
        <c-dimension v-if="p.tipo === 'espacio'" :obj="p" clave="alto" etiqueta="Alto" placeholder="0.6em"/>
        <template v-if="p.tipo === 'columnas'">
          <div class="fila-campos">
            <c-dimension :obj="p" clave="separacion" etiqueta="Separación" placeholder="1em"/>
            <c-segmentos :obj="p" clave="alinear" etiqueta="Alinear" :opciones="[{valor:'arriba',texto:'Arriba'},{valor:'centro',texto:'Al centro'}]"/>
          </div>
          <div class="columnas-lab">
            <div v-for="(c, k) in p.columnas" :key="k" class="columna-lab">
              <div class="cabeza-columna-lab">
                <strong>Columna {{ k + 1 }}</strong>
                <label class="ancho-columna-lab"><input class="entrada" type="number" min="5" max="95" v-model.number="c.ancho" :aria-label="'Ancho de la columna ' + (k + 1)"> %</label>
                <button type="button" class="btn icono pequeno fantasma" @click="quitarColumna(k)" :disabled="p.columnas.length < 2" aria-label="Quitar la columna"><icono n="cerrar"/></button>
              </div>
              <editor-piezas :lista="c.piezas" anidada/>
            </div>
          </div>
          <button type="button" class="btn pequeno" style="justify-self:start" @click="agregarColumna" :disabled="p.columnas.length >= 3"><icono n="mas"/>Columna</button>
        </template>
      </div>
    </div>`,
};

const EditorPiezas = {
  name: 'editor-piezas',
  components: { EditorPieza },
  props: { lista: Array, anidada: Boolean },
  data: () => ({ menu: false }),
  computed: {
    tipos() { return Object.entries(tienda.catalogo.componentes.piezas).filter(([k]) => !(this.anidada && k === 'columnas')); },
  },
  methods: {
    agregar(tipo) { this.menu = false; this.lista.push(pieza(tipo, tipo === 'columnas' ? { columnas: [{ ancho: 50, piezas: [pieza('texto')] }, { ancho: 50, piezas: [pieza('texto')] }] } : {})); },
    mover(i, d) { const j = i + d; if (j < 0 || j >= this.lista.length) return; const [x] = this.lista.splice(i, 1); this.lista.splice(j, 0, x); },
    duplicar(i) {
      const copia = clonar(this.lista[i]);
      const renovar = (p) => { p.id = nuevoId('p'); delete p.campo; (p.columnas || []).forEach((c) => c.piezas.forEach(renovar)); };
      renovar(copia);
      this.lista.splice(i + 1, 0, copia);
    },
    cerrar(ev) { if (this.menu && !this.$el.contains(ev.target)) this.menu = false; },
  },
  created() { this.icono = ICONO_PIEZA; },
  mounted() { document.addEventListener('mousedown', this.cerrar); },
  beforeUnmount() { document.removeEventListener('mousedown', this.cerrar); },
  template: `
    <div class="piezas-lab" :class="{anidada}">
      <editor-pieza v-for="(p, i) in lista" :key="p.id" :p="p" :i="i" :total="lista.length" :anidada="anidada"
        @subir="mover(i, -1)" @bajar="mover(i, 1)" @quitar="lista.splice(i, 1)" @duplicar="duplicar(i)"/>
      <p v-if="!lista.length" class="ayuda">{{ anidada ? 'Columna vacía.' : 'Todavía no hay piezas.' }}</p>
      <div class="menu-contenedor">
        <button type="button" class="btn pequeno" @click="menu = !menu" :aria-expanded="menu"><icono n="mas"/>{{ anidada ? 'Pieza' : 'Añadir una pieza' }}</button>
        <div class="menu izquierda menu-piezas" v-if="menu">
          <button v-for="[k, nombre] in tipos" :key="k" type="button" @click="agregar(k)"><icono :n="icono[k] || 'pieza'"/>{{ nombre }}</button>
        </div>
      </div>
    </div>`,
};
EditorPieza.components.EditorPiezas = EditorPiezas;

// ---------------------------------------------------------------- caja del componente (modo sin código)
const PanelCaja = {
  name: 'panel-caja',
  components: { ...CAMPOS },
  props: { diseno: Object, colores: Object },
  computed: {
    estilos() { return ['sin-caja', ...tienda.catalogo.estilos_caja]; },
    caja() { return this.diseno.caja; },
  },
  methods: {
    svg(e) { return e === 'sin-caja' ? svgCaja('ninguno', this.colores, { titulo: false }) : svgCaja(e, this.colores, { titulo: false }); },
    nombre(e) { return e === 'sin-caja' ? 'Sin caja' : NOMBRES_ESTILO[e] || e; },
  },
  template: `
    <div class="panel-caja">
      <div class="campo"><span class="etiqueta">Caja que la envuelve</span>
        <div class="estilos-caja">
          <button v-for="e in estilos" :key="e" type="button" class="estilo-caja" :class="{activo: caja.estilo === e}" :aria-pressed="caja.estilo === e" @click="caja.estilo = e">
            <span v-html="svg(e)"></span>{{ nombre(e) }}</button>
        </div>
      </div>
      <template v-if="caja.estilo !== 'sin-caja'">
        <div class="fila-campos">
          <c-color :obj="caja" clave="fondo" etiqueta="Fondo" vacio="El del estilo"/>
          <c-color :obj="caja" clave="borde" etiqueta="Borde" vacio="El del estilo"/>
        </div>
        <div class="fila-campos tres">
          <c-dimension :obj="caja" clave="grosor" etiqueta="Grosor del borde" placeholder="del estilo"/>
          <c-dimension :obj="caja" clave="radio" etiqueta="Redondeo" placeholder="del documento"/>
          <c-dimension :obj="caja" clave="relleno" etiqueta="Margen interior" placeholder="del documento"/>
        </div>
        <c-interruptor :obj="caja" clave="sombra" etiqueta="Sombra"/>
      </template>
      <div class="fila-campos">
        <c-segmentos :obj="diseno" clave="alineacion" etiqueta="Alineación" :opciones="[{valor:'izquierda',texto:'Izq.'},{valor:'centro',texto:'Centro'},{valor:'derecha',texto:'Der.'}]"/>
        <c-dimension :obj="diseno" clave="separacion" etiqueta="Espacio entre piezas" placeholder="0.45em"/>
      </div>
    </div>`,
};

// ---------------------------------------------------------------- preajuste de un incluido
const EditorPreajuste = {
  name: 'editor-preajuste',
  components: { ...CAMPOS },
  props: { c: Object },
  computed: {
    base() { return tienda.catalogo.porClave[this.c.base]; },
    camposBase() { return this.base ? this.base.campos : []; },
    editables() { return new Set(this.c.campos.map((x) => x.nombre)); },
  },
  methods: {
    propio(nombre) { return this.c.campos.find((x) => x.nombre === nombre); },
    alternar(cb) {
      if (this.editables.has(cb.nombre)) {
        const i = this.c.campos.findIndex((x) => x.nombre === cb.nombre);
        const [quitado] = this.c.campos.splice(i, 1);
        this.c.fijos[cb.nombre] = clonar(quitado.defecto ?? cb.defecto ?? '');
      } else {
        const valor = cb.nombre in this.c.fijos ? this.c.fijos[cb.nombre] : cb.defecto;
        delete this.c.fijos[cb.nombre];
        const orden = this.camposBase.map((x) => x.nombre);
        const nuevo = { ...clonar(cb), defecto: clonar(valor ?? '') };
        const i = this.c.campos.findIndex((x) => orden.indexOf(x.nombre) > orden.indexOf(cb.nombre));
        if (i < 0) this.c.campos.push(nuevo); else this.c.campos.splice(i, 0, nuevo);
      }
    },
    campoValor(cb) { return { ...cb, nombre: 'defecto', etiqueta: 'Valor inicial' }; },
    fijoValor(cb) {
      if (!(cb.nombre in this.c.fijos)) this.c.fijos[cb.nombre] = clonar(cb.defecto ?? '');
      return { ...cb, etiqueta: 'Valor fijo' };
    },
  },
  template: `
    <div class="preajuste-lab" v-if="base">
      <p class="ayuda">Basado en <strong>{{ base.codigo }} · {{ base.nombre }}</strong>. Marca qué se cambia en cada documento; lo demás queda fijo con el valor que pongas aquí.</p>
      <div v-for="cb in camposBase" :key="cb.nombre" class="campo-preajuste" :class="{fijo: !editables.has(cb.nombre)}">
        <label class="interruptor"><span class="texto"><strong>{{ cb.etiqueta }}</strong> · {{ editables.has(cb.nombre) ? 'se cambia en el documento' : 'fijo' }}</span>
          <input type="checkbox" :checked="editables.has(cb.nombre)" @change="alternar(cb)" :disabled="cb.tipo === 'imagen'"><span class="pista"></span></label>
        <template v-if="cb.tipo === 'imagen'"><span class="ayuda">La imagen se elige en cada documento.</span></template>
        <template v-else-if="editables.has(cb.nombre)">
          <c-texto :obj="propio(cb.nombre)" clave="etiqueta" etiqueta="Nombre en el inspector"/>
          <campo-variante :obj="propio(cb.nombre)" :campo="campoValor(cb)"/>
        </template>
        <campo-variante v-else :obj="c.fijos" :campo="fijoValor(cb)"/>
      </div>
    </div>`,
};

// ---------------------------------------------------------------- Lab
export const VistaLab = {
  name: 'vista-lab',
  props: { cid: String },
  components: { VistaRecorte, EditorCodigo, EditorCampos, EditorPiezas, PanelCaja, EditorPreajuste, ...CAMPOS },
  setup() {
    // los campos de color muestran los colores del tema de la vista previa
    const contexto = reactive({ modelo: { colores: {} }, pid: null });
    provide('ed', contexto);
    return { contexto, logo: LOGO, tienda };
  },
  data: () => ({
    lista: null, actual: null, guardado: '', guardando: false, cargando: false,
    vista: null, ultimaBuena: null, compilando: false, tema: 'pizarra', ancho: 'media', enCaja: false,
    buscar: '', verAyuda: false, codigoVisual: null, verBiblioteca: window.innerWidth > 980, ultimaPeticion: 0,
  }),
  computed: {
    cat() { return tienda.catalogo.componentes; },
    temas() { return Object.keys(tienda.catalogo.temas); },
    sucio() { return !!this.actual && JSON.stringify(this.actual) !== this.guardado; },
    nuevo() { return !!this.actual && !this.actual.id; },
    recrear() {
      const q = this.buscar.trim().toLowerCase();
      return this.cat.recrear.filter((v) => !q || `${v.codigo} ${v.nombre}`.toLowerCase().includes(q));
    },
    erroresCodigo() { return ((this.vista && this.vista.errores) || []).filter((e) => e.donde === 'codigo'); },
    erroresPreambulo() { return ((this.vista && this.vista.errores) || []).filter((e) => e.donde === 'preambulo'); },
    nombresTema() { return COLORES_TEMA; },
    colores() { return tienda.catalogo.temas[this.tema] || {}; },
    baseVariante() { return this.actual && this.actual.base ? tienda.catalogo.porClave[this.actual.base] : null; },
  },
  watch: {
    cid: { immediate: true, handler(v) { this.abrirRuta(v); } },
    actual: { deep: true, handler() { this.codigoVisual = null; this.vistaPronto(); } },
    tema: { immediate: true, handler(t) { this.contexto.modelo.colores = tienda.catalogo.temas[t] || {}; this.vistaPronto(); } },
    ancho() { this.vistaPronto(); },
    enCaja() { this.vistaPronto(); },
  },
  methods: {
    fecha(s) { return fecha(new Date((s || 0) * 1000).toISOString()); },
    miniatura(c) { return c.tiene_miniatura ? `api/componentes/${c.id}/miniatura?v=${c.version}` : null; },
    async cargarLista() {
      try { this.lista = await api('api/componentes'); } catch (e) { avisarError(e); }
    },
    async abrirRuta(v) {
      if (!v) { this.actual = null; this.guardado = ''; this.vista = null; document.title = 'Componente Lab · DocsLab'; return; }
      if (v === 'nuevo') {
        const b = tienda.borradorLab;
        if (!b) { ir('#/lab'); return; }
        tienda.borradorLab = null;
        this.poner(b, false);
        return;
      }
      this.cargando = true;
      try { this.poner(await api(`api/componentes/${v}`), true); }
      catch (e) { avisarError(e); ir('#/lab'); }
      finally { this.cargando = false; }
    },
    poner(c, guardadoYa) {
      const d = clonar(c);
      if (d.modo === 'latex') { d.codigo = d.codigo || ''; d.preambulo = d.preambulo || ''; d.campos = d.campos || []; }
      if (d.modo === 'preajuste') { d.fijos = d.fijos || {}; d.campos = d.campos || []; }
      this.actual = d;
      this.guardado = guardadoYa ? JSON.stringify(d) : '';
      this.vista = null;
      this.ultimaBuena = null;
      document.title = `${d.nombre} · Componente Lab`;
      this.vistaYa();
    },
    async confirmarSalida() {
      if (!this.sucio) return true;
      return confirmar({ titulo: '¿Salir sin guardar?', texto: 'Hay cambios en este componente que no se han guardado.', aceptar: 'Salir sin guardar', peligro: true });
    },
    async irA(ruta) { if (await this.confirmarSalida()) { this.guardado = this.actual ? JSON.stringify(this.actual) : ''; ir(ruta); } },
    async empezar(inicio) {
      if (!(await this.confirmarSalida())) return;
      tienda.borradorLab = inicio.datos();
      if (this.cid === 'nuevo') this.abrirRuta('nuevo'); else ir('#/lab/nuevo');
    },
    async recrearIncluido(v, modo) {
      if (!(await this.confirmarSalida())) return;
      try {
        tienda.borradorLab = await post('api/componentes/recrear', { clave: v.clave, modo });
        if (this.cid === 'nuevo') this.abrirRuta('nuevo'); else ir('#/lab/nuevo');
      } catch (e) { avisarError(e); }
    },
    async guardar() {
      if (!this.actual || this.guardando) return;
      if (!String(this.actual.nombre || '').trim()) { avisar('Ponle un nombre al componente.', { tipo: 'error' }); return; }
      this.guardando = true;
      try {
        const r = this.actual.id ? await put(`api/componentes/${this.actual.id}`, this.actual) : await post('api/componentes', this.actual);
        const nuevo = !this.actual.id;
        this.actual = clonar(r);
        this.guardado = JSON.stringify(this.actual);
        avisar(nuevo ? `«${r.nombre}» guardado. Ya aparece en «Añadir un elemento» de tus documentos.` : `«${r.nombre}» guardado (versión ${r.version})`);
        if (nuevo) ir(`#/lab/${r.id}`);
        this.pedirVista(r.id);
        await this.cargarLista();
      } catch (e) { avisarError(e); } finally { this.guardando = false; }
    },
    async duplicar(c) {
      try { const r = await post(`api/componentes/${c.id}/duplicar`); await this.cargarLista(); avisar('Componente duplicado'); this.irA(`#/lab/${r.id}`); } catch (e) { avisarError(e); }
    },
    async borrarComp(c) {
      const ok = await confirmar({ titulo: `¿Borrar «${c.nombre}»?`, texto: 'Se quita de la biblioteca. Los documentos que ya lo usan lo conservan.', aceptar: 'Borrar', peligro: true });
      if (!ok) return;
      try {
        await borrar(`api/componentes/${c.id}`);
        if (this.actual && this.actual.id === c.id) { this.guardado = JSON.stringify(this.actual); ir('#/lab'); }
        await this.cargarLista();
        avisar('Componente borrado');
      } catch (e) { avisarError(e); }
    },
    exportar(c) { descargar(c ? `api/componentes/exportar?ids=${c.id}` : 'api/componentes/exportar'); },
    async importar(ev) {
      const f = ev.target.files[0]; ev.target.value = '';
      if (!f) return;
      try {
        const r = await subir('api/componentes/importar', { archivo: f });
        await this.cargarLista();
        avisar(r.length === 1 ? `Componente «${r[0].nombre}» importado` : `${r.length} componentes importados`);
        if (r.length === 1) this.irA(`#/lab/${r[0].id}`);
      } catch (e) { avisarError(e); }
    },
    async pasarACodigo() {
      const ok = await confirmar({
        titulo: '¿Pasar a código LaTeX?',
        texto: 'Verás y podrás cambiar todo el LaTeX del componente. El editor de piezas deja de estar disponible para este componente (si no guardas, puedes volver atrás).',
        aceptar: 'Pasar a código',
      });
      if (!ok) return;
      try {
        const r = await post('api/componentes/codigo', this.actual);
        const id = this.actual.id;
        this.actual = { ...clonar(r.como_latex), id, version: this.actual.version };
        if (!id) delete this.actual.id;
      } catch (e) { avisarError(e); }
    },
    async verCodigoVisual() {
      if (this.codigoVisual) { this.codigoVisual = null; return; }
      try { const r = await post('api/componentes/codigo', this.actual); this.codigoVisual = r.codigo + (r.preambulo ? `\n% Preámbulo:\n${r.preambulo}` : ''); } catch (e) { avisarError(e); }
    },
    insertar(texto) { if (this.$refs.codigo) this.$refs.codigo.insertar(texto); },
    // vista previa: se compila un momento después del último cambio
    vistaPronto() {
      if (!this.retrasoVista) this.retrasoVista = retrasar(() => this.pedirVista(), 900);
      this.retrasoVista();
    },
    vistaYa() { if (this.retrasoVista) this.retrasoVista.cancelar(); this.pedirVista(); },
    async pedirVista(miniatura) {
      if (!this.actual) return;
      const n = ++this.ultimaPeticion;
      this.compilando = true;
      try {
        const r = await post('api/componentes/vista', { componente: this.actual, tema: this.tema, ancho: this.ancho, en_caja: this.enCaja, miniatura_de: miniatura || null });
        if (miniatura) this.cargarLista();           // la miniatura ya está hecha, aunque esta vista quede vieja
        if (n !== this.ultimaPeticion) return;
        this.vista = r;
        if (r.ok) this.ultimaBuena = r;
      } catch (e) {
        if (n === this.ultimaPeticion) this.vista = { ok: false, errores: [{ mensaje: e.message }] };
      } finally { if (n === this.ultimaPeticion) this.compilando = false; }
    },
    irAError(e) {
      if (e.donde === 'codigo' && this.$refs.codigo) this.$refs.codigo.enfocarLinea(e.linea);
      if (e.donde === 'preambulo' && this.$refs.preambulo) this.$refs.preambulo.enfocarLinea(e.linea);
    },
    tecla(ev) {
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 's') { ev.preventDefault(); this.guardar(); }
    },
    antesDeSalir(ev) { if (this.sucio) { ev.preventDefault(); ev.returnValue = ''; } },
    usarColor(nombre) { this.insertar(nombre); },
  },
  created() { this.inicios = INICIOS; this.nombresModo = NOMBRES_MODO; this.anchos = ANCHOS; },
  mounted() {
    this.cargarLista();
    window.addEventListener('keydown', this.tecla);
    window.addEventListener('beforeunload', this.antesDeSalir);
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.tecla);
    window.removeEventListener('beforeunload', this.antesDeSalir);
    if (this.retrasoVista) this.retrasoVista.cancelar();
    document.title = 'DocsLab';
  },
  template: `
  <div class="lab">
    <header class="barra">
      <a class="marca" href="#/" @click.prevent="irA('#/')" title="Volver a tus documentos"><span v-html="logo"></span><span class="solo-ancho">DocsLab</span></a>
      <span class="divisor"></span>
      <button class="btn icono fantasma" :class="{activo: verBiblioteca}" @click="verBiblioteca = !verBiblioteca" title="Biblioteca de componentes" aria-label="Mostrar u ocultar la biblioteca"><icono n="panel-izq"/></button>
      <span class="titulo-lab"><icono n="matraz"/>Componente Lab</span>
      <template v-if="actual">
        <span class="divisor solo-ancho"></span>
        <input class="titulo-proyecto" v-model="actual.nombre" aria-label="Nombre del componente" :size="Math.min(36, Math.max(10, (actual.nombre || '').length))">
        <span class="chip" :class="sucio ? 'aviso-chip' : 'ok'" role="status"><span class="punto"></span>{{ nuevo ? 'Sin guardar' : sucio ? 'Cambios sin guardar' : 'Guardado · v' + actual.version }}</span>
      </template>
      <span class="espacio"></span>
      <a v-if="tienda && tienda.volverA" class="btn" :href="tienda.volverA" @click.prevent="irA(tienda.volverA)"><icono n="hoja"/><span class="solo-ancho">Volver al documento</span></a>
      <button v-if="actual" class="btn primario" @click="guardar" :disabled="guardando || (!sucio && !nuevo)" title="Guardar (Ctrl + S)"><icono n="check"/>{{ guardando ? 'Guardando…' : 'Guardar' }}</button>
    </header>

    <div class="cuerpo-lab" :class="{'sin-biblioteca': !verBiblioteca}">
      <aside class="biblioteca-lab panel" v-show="verBiblioteca" aria-label="Biblioteca de componentes">
        <div class="contenido-panel">
          <section class="seccion-lab">
            <div class="titulo-seccion-lab"><h2>Tus componentes</h2>
              <input ref="importador" type="file" accept=".json" hidden @change="importar">
              <button class="btn icono pequeno fantasma" @click="$refs.importador.click()" title="Importar componentes (.json)" aria-label="Importar componentes"><icono n="subir"/></button>
              <button class="btn icono pequeno fantasma" @click="exportar(null)" :disabled="!lista || !lista.length" title="Exportar todos (.json)" aria-label="Exportar todos"><icono n="descargar"/></button>
            </div>
            <p v-if="lista && !lista.length" class="ayuda">Aún no tienes. Empieza con una de las opciones de abajo.</p>
            <div class="lista-comp" v-if="lista && lista.length">
              <div v-for="c in lista" :key="c.id" class="comp-lab" :class="{activo: actual && actual.id === c.id}">
                <button type="button" class="abrir-comp" @click="irA('#/lab/' + c.id)">
                  <span class="mini-comp"><img v-if="miniatura(c)" :src="miniatura(c)" alt="" loading="lazy"><icono v-else :n="c.modo === 'latex' ? 'codigo' : 'pieza'"/></span>
                  <span class="datos-comp"><strong>{{ c.nombre }}</strong><span class="ayuda">{{ nombresModo[c.modo] }} · v{{ c.version }}</span></span>
                </button>
                <span class="acciones-comp">
                  <button class="btn icono pequeno fantasma" @click="duplicar(c)" title="Duplicar" aria-label="Duplicar"><icono n="duplicar"/></button>
                  <button class="btn icono pequeno fantasma" @click="exportar(c)" title="Exportar (.json)" aria-label="Exportar"><icono n="descargar"/></button>
                  <button class="btn icono pequeno fantasma" @click="borrarComp(c)" title="Borrar" aria-label="Borrar"><icono n="basura"/></button>
                </span>
              </div>
            </div>
          </section>
          <section class="seccion-lab" v-if="actual">
            <h2>Hacer uno nuevo</h2>
            <div class="inicios-lab">
              <button v-for="x in inicios" :key="x.clave" type="button" class="inicio-lab" @click="empezar(x)">
                <icono :n="x.icono"/><span><strong>{{ x.nombre }}</strong><span class="ayuda">{{ x.texto }}</span></span>
              </button>
            </div>
          </section>
          <section class="seccion-lab">
            <h2>Recrear uno incluido</h2>
            <p class="ayuda">Parte de cualquiera de los componentes de DocsLab: con su código LaTeX para cambiarlo a fondo, o sin código fijando valores.</p>
            <input class="entrada" type="search" v-model="buscar" placeholder="Buscar: cifra, cita, T21…" aria-label="Buscar componente incluido">
            <div class="recrear-lab">
              <div v-for="v in recrear" :key="v.clave" class="fila-recrear">
                <span class="codigo-var">{{ v.codigo }}</span><span class="nombre-recrear">{{ v.nombre }}</span>
                <button class="btn pequeno" @click="recrearIncluido(v, 'latex')" title="Recrear con su código LaTeX">Código</button>
                <button class="btn pequeno" @click="recrearIncluido(v, 'preajuste')" title="Recrear sin código (valores fijos)">Sin código</button>
              </div>
            </div>
          </section>
        </div>
      </aside>

      <main class="banco-lab" v-if="actual">
        <div class="cabeza-banco">
          <div class="modo-lab"><span class="chip">{{ nombresModo[actual.modo] }}</span>
            <button v-if="actual.modo !== 'latex'" class="btn pequeno" @click="pasarACodigo"><icono n="codigo"/>Pasar a código LaTeX</button>
            <button v-if="actual.modo === 'visual'" class="btn pequeno fantasma" @click="verCodigoVisual">{{ codigoVisual ? 'Ocultar el LaTeX' : 'Ver el LaTeX que se genera' }}</button>
          </div>
          <label class="campo"><span class="etiqueta">Descripción (se ve al elegirlo en el documento)</span>
            <input class="entrada" v-model="actual.descripcion" placeholder="Para qué sirve, en una frase"></label>
        </div>
        <pre v-if="codigoVisual" class="codigo-generado">{{ codigoVisual }}</pre>

        <template v-if="actual.modo === 'visual'">
          <section class="seccion-banco"><h3>Caja y alineación</h3><panel-caja :diseno="actual.diseno" :colores="colores"/></section>
          <section class="seccion-banco"><h3>Piezas <span class="ayuda">de arriba abajo; las marcadas «en el documento» se rellenan en el inspector</span></h3>
            <editor-piezas :lista="actual.diseno.piezas"/></section>
        </template>

        <template v-else-if="actual.modo === 'latex'">
          <section class="seccion-banco">
            <h3>Código <button class="boton-ayuda" :class="{activo: verAyuda}" @click="verAyuda = !verAyuda" title="Cómo se escribe" aria-label="Cómo se escribe">?</button></h3>
            <div v-if="verAyuda" class="ayuda-lab">
              <p><code>{{ '{' + '{' }}campo{{ '}' + '}' }}</code> se cambia por lo que se escribe en el inspector, ya en LaTeX (los textos con su formato, las listas como <code>\\item …</code>, los porcentajes como fracción).</p>
              <p><code>{{ '{' + '{' }}#campo{{ '}' + '}' }} … {{ '{' + '{' }}/campo{{ '}' + '}' }}</code> sale solo si el campo tiene algo; con una lista se repite por cada elemento, que es <code>{{ '{' + '{' }}.{{ '}' + '}' }}</code>. <code>{{ '{' + '{' }}^campo{{ '}' + '}' }} … {{ '{' + '{' }}/campo{{ '}' + '}' }}</code> sale si está vacío. <code>{{ '{' + '{' }}id{{ '}' + '}' }}</code> es único en cada uso.</p>
              <p><code>\\tam{1.5}</code> letra 1.5 veces la del documento · <code>\\PCimg[width=\\linewidth]{{ '{' }}{{ '{' + '{' }}imagen{{ '}' + '}' }}{{ '}' }}</code> imagen · <code>\\PC@antes</code> y <code>\\PC@despues</code> dejan el espacio de los demás elementos. Se pueden usar las órdenes con @ de la plantilla.</p>
              <div class="colores-lab"><span>Colores del tema (clic para escribirlos):</span>
                <button v-for="[n, k] in nombresTema" :key="n" type="button" class="color-lab" @click="usarColor(n)" :title="n"><i :style="{background: '#' + (colores[k] || 'fff')}"></i>{{ n }}</button>
              </div>
            </div>
            <editor-codigo ref="codigo" v-model="actual.codigo" :errores="erroresCodigo" etiqueta="Código LaTeX del componente" :minimo="220"/>
          </section>
          <section class="seccion-banco"><h3>Campos <span class="ayuda">lo que se rellena en el inspector</span></h3>
            <editor-campos :campos="actual.campos" @insertar="insertar"/></section>
          <details class="seccion-banco" :open="!!actual.preambulo">
            <summary>Preámbulo (opcional): paquetes y órdenes propias</summary>
            <p class="ayuda">Va una sola vez antes de \\begin{document}. Por ejemplo <code>\\usepackage{pifont}</code> o <code>\\newcommand…</code></p>
            <editor-codigo ref="preambulo" v-model="actual.preambulo" :errores="erroresPreambulo" etiqueta="Preámbulo del componente" :minimo="90"/>
          </details>
        </template>

        <template v-else>
          <section class="seccion-banco"><h3>Qué se cambia en el documento</h3><editor-preajuste :c="actual"/></section>
        </template>
      </main>

      <main class="banco-lab bienvenida-lab" v-else-if="!cargando">
        <div class="presentacion-lab">
          <icono n="matraz"/>
          <h1>Componente Lab</h1>
          <p>Crea tus propios elementos para las cajas del documento: <strong>sin código</strong>, juntando piezas, o <strong>con código LaTeX</strong>, con huecos que se rellenan desde el inspector. También puedes <strong>recrear</strong> cualquiera de los incluidos.</p>
          <p class="ayuda">Lo que guardes aparece en «Añadir un elemento» de todos tus documentos, en el grupo «Tus componentes».</p>
          <div class="inicios-lab grande">
            <button v-for="x in inicios" :key="x.clave" type="button" class="inicio-lab" @click="empezar(x)">
              <icono :n="x.icono"/><span><strong>{{ x.nombre }}</strong><span class="ayuda">{{ x.texto }}</span></span>
            </button>
          </div>
        </div>
      </main>

      <aside class="vista-lab panel" v-if="actual" aria-label="Vista previa">
        <div class="cabeza-vista-lab">
          <h3>Vista previa</h3>
          <span class="chip trabajando" v-if="compilando"><span class="punto"></span>Compilando</span>
          <button class="btn icono pequeno fantasma" @click="pedirVista()" title="Volver a compilar" aria-label="Volver a compilar"><icono n="compilar"/></button>
        </div>
        <div class="opciones-vista-lab">
          <label class="campo"><span class="etiqueta">Tema</span>
            <select class="entrada" v-model="tema"><option v-for="t in temas" :key="t" :value="t">{{ t.charAt(0).toUpperCase() + t.slice(1) }}</option></select></label>
          <label class="campo"><span class="etiqueta">Columna</span>
            <select class="entrada" v-model="ancho"><option v-for="(t, k) in anchos" :key="k" :value="k">{{ t }}</option></select></label>
          <label class="interruptor"><span class="texto">Dentro de una caja del documento</span><input type="checkbox" v-model="enCaja"><span class="pista"></span></label>
        </div>
        <div class="mesa-lab">
          <vista-recorte v-if="vista && vista.ok" :pdf="vista.pdf" :caja="vista.caja" :papel="vista.papel"/>
          <div v-else-if="vista && ultimaBuena" class="vista-vieja">
            <vista-recorte :pdf="ultimaBuena.pdf" :caja="ultimaBuena.caja" :papel="ultimaBuena.papel"/>
            <span class="chip aviso-chip"><span class="punto"></span>Se ve la última versión que compiló bien</span>
          </div>
          <p v-else-if="!vista" class="ayuda">{{ compilando ? 'Compilando la primera vista…' : 'La vista previa aparece al cambiar algo.' }}</p>
          <p v-else class="ayuda">No se pudo compilar: mira el mensaje de abajo.</p>
        </div>
        <div v-if="vista && vista.errores && vista.errores.length" class="errores-lab">
          <div v-for="(e, i) in vista.errores" :key="i" class="mensaje error">
            <span class="icono-msg"><icono n="alerta"/></span>
            <div><strong>{{ e.mensaje }}</strong>
              <span v-if="e.linea" class="ayuda"> · {{ e.donde === 'preambulo' ? 'preámbulo' : 'código' }}, línea {{ e.linea }}</span>
              <pre v-if="e.contexto">{{ e.contexto }}</pre>
              <div class="acciones-msg" v-if="e.linea"><button class="btn pequeno" @click="irAError(e)">Ir a la línea</button></div>
            </div>
          </div>
        </div>
        <div v-if="vista && vista.avisos && vista.avisos.length" class="errores-lab">
          <div v-for="(a, i) in vista.avisos" :key="i" class="mensaje aviso-msg"><span class="icono-msg"><icono n="info"/></span><div>{{ a.mensaje }}</div></div>
        </div>
        <p class="ayuda nota-vista">Se compila con el tamaño real: A0 y letra de 30 pt. En el documento se adapta a su letra y a su columna.</p>
      </aside>
    </div>
  </div>`,
};
