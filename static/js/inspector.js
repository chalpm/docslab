// SPDX-License-Identifier: AGPL-3.0-only
// Inspector: el formulario de lo que está seleccionado.
import { CAMPOS } from './campos.js';
import { tienda } from './tienda.js';
import { svgCaja, svgCabecera, NOMBRES_ESTILO, NOMBRES_CABECERA } from './dibujos.js';
import { nombreNodo, variante, tieneTitulo, NOMBRES_DISENO, nombreNivel } from './modeloed.js';
import { aMm } from './util.js';
import { SelectorTipografias } from './tipografias.js';

const { inject } = Vue;

const comun = {
  components: CAMPOS,
  props: { info: Object },
  setup() { return { ed: inject('ed') }; },
  computed: {
    cat() { return tienda.catalogo; },
    colores() { return this.ed.modelo.colores; },
    clase() { return this.ed.clase; },
    flujo() { return this.ed.flujo; },
    diapos() { return this.ed.clase === 'presentacion'; },
  },
};

// Animación de entrada y transiciones: solo se ven al exportar a PowerPoint (salidas/animaciones.py)
export const EFECTOS_ANIMACION = [
  { valor: '', texto: 'Ninguna' }, { valor: 'aparecer', texto: 'Aparecer' }, { valor: 'desvanecer', texto: 'Desvanecer' },
  { valor: 'subir', texto: 'Subir desde abajo' }, { valor: 'barrido', texto: 'Barrido' }, { valor: 'aumentar', texto: 'Aumentar' },
];
export const INICIOS_ANIMACION = [
  { valor: 'clic', texto: 'Al hacer clic' }, { valor: 'con', texto: 'Con la anterior' }, { valor: 'despues', texto: 'Después de la anterior' },
];
export const EFECTOS_TRANSICION = [
  { valor: '', texto: 'Ninguna' }, { valor: 'desvanecer', texto: 'Desvanecer' }, { valor: 'empujar', texto: 'Empujar' },
  { valor: 'barrido', texto: 'Barrido' }, { valor: 'cubrir', texto: 'Cubrir' }, { valor: 'dividir', texto: 'Dividir' },
];
export const VELOCIDADES_TRANSICION = [{ valor: 'rapida', texto: 'Rápida' }, { valor: 'media', texto: 'Media' }, { valor: 'lenta', texto: 'Lenta' }];

const CAnimacion = {
  name: 'c-animacion',
  components: CAMPOS,
  props: { obj: Object, que: { type: String, default: 'este elemento' } },
  computed: {
    efecto: {
      get() { return (this.obj.animacion && this.obj.animacion.efecto) || ''; },
      set(v) {
        if (!v) { delete this.obj.animacion; return; }
        this.obj.animacion = { inicio: 'clic', duracion: 0.5, retraso: 0, ...(this.obj.animacion || {}), efecto: v };
      },
    },
    efectos() { return EFECTOS_ANIMACION; },
    inicios() { return INICIOS_ANIMACION; },
  },
  template: `
    <details class="seccion" :open="!!efecto">
      <summary>Animación en PowerPoint<span v-if="efecto" class="insignia">{{ efectos.find((e) => e.valor === efecto).texto }}</span></summary>
      <div class="contenido-seccion">
        <div class="campo"><label class="etiqueta" :for="'anim-' + obj.id">Efecto de entrada</label>
          <select :id="'anim-' + obj.id" class="entrada" v-model="efecto">
            <option v-for="o in efectos" :key="o.valor" :value="o.valor">{{ o.texto }}</option>
          </select></div>
        <template v-if="efecto">
          <c-seleccion :obj="obj.animacion" clave="inicio" etiqueta="Empieza" :opciones="inicios"/>
          <div class="fila-campos">
            <c-numero :obj="obj.animacion" clave="duracion" etiqueta="Duración (s)" :min="0.1" :max="10" :paso="0.1"/>
            <c-numero :obj="obj.animacion" clave="retraso" etiqueta="Retraso (s)" :min="0" :max="30" :paso="0.1"/>
          </div>
        </template>
        <p class="ayuda">Al exportar a PowerPoint (modo editable), {{ que }} entra con este efecto, en el orden del documento. En el PDF no se ve.</p>
      </div>
    </details>`,
};

const CTransicion = {
  name: 'c-transicion',
  components: CAMPOS,
  props: { obj: Object, etiqueta: { type: String, default: 'Transición en PowerPoint' }, ayuda: String },
  emits: ['todas'],
  computed: {
    efecto: {
      get() { return (this.obj.transicion && this.obj.transicion.efecto) || ''; },
      set(v) {
        if (!v) { delete this.obj.transicion; return; }
        this.obj.transicion = { velocidad: 'media', ...(this.obj.transicion || {}), efecto: v };
      },
    },
    efectos() { return EFECTOS_TRANSICION; },
    velocidades() { return VELOCIDADES_TRANSICION; },
  },
  template: `
    <div class="seccion">
      <div class="campo"><label class="etiqueta" :for="'trans-' + (obj.id || 'doc')">{{ etiqueta }}</label>
        <select :id="'trans-' + (obj.id || 'doc')" class="entrada" v-model="efecto">
          <option v-for="o in efectos" :key="o.valor" :value="o.valor">{{ o.texto }}</option>
        </select></div>
      <c-segmentos v-if="efecto" :obj="obj.transicion" clave="velocidad" etiqueta="Velocidad" :opciones="velocidades"/>
      <span v-if="ayuda" class="ayuda">{{ ayuda }}</span>
      <slot/>
    </div>`,
};

// Selector visual de estilos de caja
const SelectorEstilo = {
  name: 'selector-estilo',
  props: { obj: Object, clave: String, conDefecto: Boolean, etiqueta: String },
  setup() { return { ed: inject('ed') }; },
  computed: {
    estilos() { return tienda.catalogo.estilos_caja; },
    colores() { return this.ed.modelo.colores; },
    defecto() { return this.ed.modelo.estilo.bloque; },
  },
  methods: {
    svg(e) { return svgCaja(e, this.colores); },
    nombre(e) { return NOMBRES_ESTILO[e] || e; },
  },
  template: `
    <div class="campo">
      <span class="etiqueta">{{ etiqueta || 'Estilo' }}</span>
      <div class="estilos-caja">
        <button v-if="conDefecto" type="button" class="estilo-caja" :class="{activo: !obj[clave]}" @click="obj[clave] = ''" :title="'El general: ' + nombre(defecto)">
          <span v-html="svg(defecto)"></span>El general
        </button>
        <button v-for="e in estilos" :key="e" type="button" class="estilo-caja" :class="{activo: obj[clave] === e}" @click="obj[clave] = e" :aria-pressed="obj[clave] === e">
          <span v-html="svg(e)"></span>{{ nombre(e) }}
        </button>
      </div>
    </div>`,
};

// ---------------------------------------------------------------- póster
const InspPoster = {
  name: 'insp-poster',
  ...comun,
  components: { ...CAMPOS, SelectorEstilo, SelectorTipografias, CTransicion },
  computed: {
    ...comun.computed,
    m() { return this.ed.modelo; },
    tamanos() {
      const suyos = ((this.cat.clases || {})[this.clase] || {}).tamanos || Object.keys(this.cat.tamanos);
      const lista = suyos.includes(this.m.lienzo.tamano) || !this.cat.tamanos[this.m.lienzo.tamano] ? suyos : [...suyos, this.m.lienzo.tamano];
      return [...lista.map((k) => ({ valor: k, texto: `${k} (${this.cat.tamanos[k].join(' × ')})` })),
        { valor: 'personalizado', texto: 'Personalizado' }];
    },
    pres() { return this.m.presentacion; },
    doc() { return this.m.documento; },
    sueltas() { return this.m.filas.reduce((n, f) => n + f.columnas.reduce((k, c) => k + c.bloques.filter((b) => b.libre).length, 0), 0); },
  },
  watch: {
    'm.lienzo.tamano'(t) { this.aplicarTamano(); },
    'm.lienzo.orientacion'() { this.aplicarTamano(); },
  },
  methods: {
    aplicarTamano() {
      const lz = this.m.lienzo;
      const t = this.cat.tamanos[lz.tamano];
      if (!t) return;
      let [a, b] = t;
      const ma = aMm(a), mb = aMm(b);
      if (this.diapos) lz.orientacion = 'horizontal';
      const horizontal = lz.orientacion === 'horizontal';
      if ((horizontal && ma < mb) || (!horizontal && ma > mb)) [a, b] = [b, a];
      if (lz.ancho !== a || lz.alto !== b) { lz.ancho = a; lz.alto = b; }
    },
    aplicarTema(k) {
      Object.assign(this.m.colores, { tema: k, ...this.cat.temas[k] });
    },
    idiomaInstalado(k) { return !(tienda.estado && tienda.estado.idiomas && tienda.estado.idiomas[k] === false); },
    cambiarIdioma(k) {
      this.m.idioma = k;
      const palabras = Object.values(this.cat.idiomas).map((d) => d.figura);
      const actual = String(this.m.estilo.nombre_figura || '').trim();
      if (k && (!actual || palabras.includes(actual))) this.m.estilo.nombre_figura = this.cat.idiomas[k].figura;
    },
    escalas() {
      const lista = [['titulo', 'Título'], ['subtitulo', 'Subtítulo'], ['autores', 'Autores'], ['afiliaciones', 'Afiliaciones'],
        ['bloque', 'Títulos de las cajas'], ['pie', 'Pies de figura'], ['cita', 'Citas grandes'], ['cifra', 'Cifras destacadas'],
        ['referencias', 'Referencias'], ['piedeposter', this.diapos ? 'Pie de las diapositivas' : 'Pie del póster']];
      return this.flujo ? lista.filter(([k]) => k !== 'piedeposter') : lista;
    },
  },
  template: `
  <div class="inspector">
    <div class="encabezado-insp"><span class="tipo-insp"><icono n="hoja"/>{{ ed.nombreClase }}</span><h2>Diseño general</h2>
      <p class="ayuda" v-if="flujo">Afecta a todo el documento: página, letra, colores y numeración.</p>
      <p class="ayuda" v-else>Afecta a {{ diapos ? 'toda la presentación' : 'todo el póster' }}. Cada caja o elemento puede cambiar su propio estilo.</p></div>

    <div class="seccion">
      <h3>{{ flujo ? 'Página' : diapos ? 'Diapositiva' : 'Lienzo' }}</h3>
      <c-seleccion :obj="m.lienzo" clave="tamano" etiqueta="Tamaño" :opciones="tamanos"/>
      <c-segmentos v-if="!diapos" :obj="m.lienzo" clave="orientacion" etiqueta="Orientación" :opciones="[{valor:'vertical',texto:'Vertical'},{valor:'horizontal',texto:'Horizontal'}]"/>
      <div class="fila-campos tres">
        <c-dimension :obj="m.lienzo" clave="ancho" etiqueta="Ancho" @change="m.lienzo.tamano = 'personalizado'"/>
        <c-dimension :obj="m.lienzo" clave="alto" etiqueta="Alto" @change="m.lienzo.tamano = 'personalizado'"/>
        <c-dimension :obj="m.lienzo" clave="margen" etiqueta="Margen"/>
      </div>
      <details class="seccion" style="border:0;padding:0">
        <summary>Márgenes distintos por lado</summary>
        <div class="contenido-seccion">
          <div class="fila-campos">
            <c-dimension :obj="m.lienzo" clave="margen_superior" etiqueta="Arriba" :placeholder="m.lienzo.margen"/>
            <c-dimension :obj="m.lienzo" clave="margen_inferior" etiqueta="Abajo" :placeholder="m.lienzo.margen"/>
            <c-dimension :obj="m.lienzo" clave="margen_izquierdo" etiqueta="Izquierda" :placeholder="m.lienzo.margen"/>
            <c-dimension :obj="m.lienzo" clave="margen_derecho" etiqueta="Derecha" :placeholder="m.lienzo.margen"/>
          </div>
          <p class="ayuda">Vacío = el margen general. En una tesis el izquierdo suele ser mayor, para encuadernar.</p>
        </div>
      </details>
      <div class="campo" v-if="clase === 'poster'">
        <label class="interruptor"><span class="texto">Lienzo libre</span>
          <input type="checkbox" :checked="!!m.lienzo.libre" @click.prevent="ed.lienzoLibre(!m.lienzo.libre)"><span class="pista"></span></label>
        <span class="ayuda" v-if="m.lienzo.libre">Las cajas están sueltas ({{ sueltas }}): arrástralas en la vista previa. Lo que añadas también queda suelto.</span>
        <span class="ayuda" v-else>Suelta todas las cajas de la cuadrícula para colocarlas a mano. Para soltar solo una, selecciónala y usa «Soltar de la cuadrícula».</span>
      </div>
    </div>

    <div class="seccion" v-if="diapos">
      <h3>Diapositivas</h3>
      <c-segmentos :obj="pres" clave="titulo" etiqueta="Estilo de los títulos" :opciones="[{valor:'banda',texto:'Banda'},{valor:'linea',texto:'Línea'},{valor:'simple',texto:'Sencillo'}]"
        ayuda="Cada diapositiva puede usar otro."/>
      <c-numero :obj="pres" clave="escala_titulo" etiqueta="Tamaño de los títulos (× letra)" :min="0.8" :max="4" :paso="0.05"/>
      <c-texto :obj="pres" clave="pie" etiqueta="Pie de las diapositivas" formato placeholder="Título corto · Autor"/>
      <c-interruptor :obj="pres" clave="numerar" etiqueta="Numerar las diapositivas" :defecto="true"/>
      <c-interruptor :obj="pres" clave="progreso" etiqueta="Barra de avance" ayuda="Una línea fina abajo que crece con cada diapositiva."/>
    </div>

    <div class="seccion" v-if="flujo">
      <h3>Texto del documento</h3>
      <c-segmentos v-if="clase !== 'tesis'" :obj="doc" clave="columnas" etiqueta="Columnas de texto" :opciones="[{valor:1,texto:'Una'},{valor:2,texto:'Dos'}]"
        ayuda="A dos columnas, el título y el resumen ocupan todo el ancho."/>
      <c-segmentos :obj="doc" clave="parrafos" etiqueta="Párrafos" :opciones="[{valor:'sangria',texto:'Con sangría'},{valor:'separados',texto:'Separados'}]"/>
      <c-segmentos :obj="m.estilo" clave="alinear_texto" etiqueta="Alineación del texto" :opciones="[{valor:'justificado',texto:'Justificado'},{valor:'izquierda',texto:'Izquierda'}]"/>
      <c-interruptor :obj="doc" clave="numerar_secciones" :etiqueta="clase === 'tesis' ? 'Numerar capítulos y secciones' : 'Numerar las secciones'" :defecto="true"/>
      <c-interruptor :obj="doc" clave="numerar_paginas" etiqueta="Numerar las páginas" :defecto="true"/>
      <c-texto :obj="doc" clave="encabezado" etiqueta="Encabezado de las páginas" formato placeholder="vacío = sin encabezado"/>
      <div class="fila-campos">
        <c-numero v-if="clase === 'tesis'" :obj="doc" clave="escala_capitulo" etiqueta="Tamaño de los capítulos (× letra)" :min="1" :max="4" :paso="0.05"/>
        <c-numero :obj="doc" clave="escala_seccion" etiqueta="Tamaño de las secciones (× letra)" :min="1" :max="3" :paso="0.05"/>
      </div>
    </div>

    <div class="seccion">
      <h3>Texto</h3>
      <div class="fila-campos">
        <c-numero :obj="m.tipografia" clave="fuente" etiqueta="Tamaño de la letra (pt)" :min="6" :max="120" :paso="0.5"/>
        <c-numero :obj="m.tipografia" clave="interlinea" etiqueta="Interlineado" :min="1" :max="2" :paso="0.02"/>
      </div>
      <selector-tipografias/>
      <label class="campo"><span class="etiqueta">Idioma</span>
        <select class="entrada" :value="m.idioma || ''" @change="cambiarIdioma($event.target.value)">
          <option value="">Sin definir (reglas del inglés)</option>
          <option v-for="(d, k) in cat.idiomas" :key="k" :value="k">{{ d.nombre }}{{ idiomaInstalado(k) ? '' : ' (no instalado)' }}</option>
        </select>
        <span class="ayuda" v-if="m.idioma && !idiomaInstalado(m.idioma)">Falta el paquete de este idioma en tu LaTeX: se compila igual, pero las palabras se separan como en inglés.</span>
        <span class="ayuda" v-else>Separa bien las palabras al final de cada línea y elige las comillas y las palabras de las referencias.</span>
      </label>
      <div class="campo"><span class="etiqueta">Cómo se escribe el texto</span>
        <div class="segmentos" role="group" aria-label="Cómo se escribe el texto">
          <button type="button" :class="{activo: m.formato_texto !== 'latex'}" :aria-pressed="m.formato_texto !== 'latex'" @click="ed.cambiarFormato('simple')">Formato sencillo</button>
          <button type="button" :class="{activo: m.formato_texto === 'latex'}" :aria-pressed="m.formato_texto === 'latex'" @click="ed.cambiarFormato('latex')">Código LaTeX</button>
        </div>
        <span class="ayuda" v-if="m.formato_texto === 'latex'">El texto se copia tal cual: escribe \\textbf{...}, \\% o $x^2$.</span>
        <span class="ayuda" v-else>Los símbolos especiales se escriben tal cual. Admite **negrita**, *cursiva*, ^sup^, ~sub~ y $matemáticas$.</span>
      </div>
      <details class="seccion" style="border:0;padding:0">
        <summary>Tamaños relativos (múltiplos de la letra)</summary>
        <div class="contenido-seccion">
          <div class="fila-campos">
            <c-numero v-for="[k, t] in escalas()" :key="k" :obj="m.tipografia.escalas" :clave="k" :etiqueta="t" :min="0.3" :max="8" :paso="0.05"/>
          </div>
        </div>
      </details>
    </div>

    <div class="seccion">
      <h3>Colores</h3>
      <c-tema :model-value="m.colores.tema" @update:model-value="aplicarTema"/>
      <details class="seccion" style="border:0;padding:0">
        <summary>Cambiar colores sueltos</summary>
        <div class="contenido-seccion">
          <c-color :obj="m.colores" clave="primario" etiqueta="Primario (barras y títulos)" sin-nombres/>
          <c-color :obj="m.colores" clave="secundario" etiqueta="Secundario" sin-nombres/>
          <c-color :obj="m.colores" clave="acento" etiqueta="Acento (detalles)" sin-nombres/>
          <c-color :obj="m.colores" clave="fondo" etiqueta="Fondo del lienzo" sin-nombres/>
          <c-color :obj="m.colores" clave="fondo_bloque" etiqueta="Fondo de las cajas" sin-nombres/>
          <c-color :obj="m.colores" clave="texto" etiqueta="Texto" sin-nombres/>
          <c-color :obj="m.colores" clave="tenue" etiqueta="Texto secundario" sin-nombres/>
          <c-color :obj="m.colores" clave="contraste" etiqueta="Texto sobre el color primario" sin-nombres/>
        </div>
      </details>
    </div>

    <div class="seccion" v-if="!flujo">
      <h3>Cajas</h3>
      <selector-estilo :obj="m.estilo" clave="bloque" etiqueta="Estilo de todas las cajas"/>
      <c-interruptor :obj="m.estilo" clave="mostrar_titulos" etiqueta="Mostrar los títulos de las cajas" :defecto="true"
        ayuda="Si lo apagas se ocultan todos; cada caja puede encender o apagar el suyo."/>
      <c-interruptor :obj="m.estilo" clave="numerar_bloques" etiqueta="Numerar las cajas"/>
      <c-segmentos :obj="m.estilo" clave="alineacion_titulos" etiqueta="Alineación de los títulos" :opciones="[{valor:'izquierda',texto:'Izquierda'},{valor:'centro',texto:'Centro'},{valor:'derecha',texto:'Derecha'}]"/>
      <c-segmentos :obj="m.estilo" clave="alinear_texto" etiqueta="Alineación del texto" :opciones="[{valor:'justificado',texto:'Justificado'},{valor:'izquierda',texto:'Izquierda'},{valor:'centro',texto:'Centro'}]"/>
      <c-interruptor :obj="m.estilo" clave="sombra" etiqueta="Sombra en todas las cajas"/>
      <div class="fila-campos">
        <c-dimension :obj="m.estilo" clave="radio" etiqueta="Redondeo de esquinas"/>
        <c-dimension :obj="m.estilo" clave="relleno" etiqueta="Margen interior"/>
      </div>
    </div>

    <div class="seccion">
      <h3>Espacios</h3>
      <div class="fila-campos">
        <c-dimension :obj="m.estilo" clave="separacion_columnas" :etiqueta="flujo ? 'Entre las columnas de texto' : 'Entre columnas'"/>
        <c-dimension v-if="!flujo" :obj="m.estilo" clave="separacion_filas" etiqueta="Entre filas" placeholder="como entre cajas"/>
        <c-dimension v-if="!flujo" :obj="m.estilo" clave="separacion_bloques" etiqueta="Entre cajas"/>
        <c-dimension :obj="m.estilo" clave="separacion_elementos" etiqueta="Entre elementos"/>
        <c-dimension :obj="m.estilo" clave="separacion_imagenes" etiqueta="Entre imágenes de un mosaico"/>
      </div>
    </div>

    <div class="seccion">
      <h3>{{ flujo ? 'Figuras y tablas' : 'Figuras' }}</h3>
      <c-interruptor :obj="m.estilo" clave="numerar_figuras" etiqueta="Numerar los pies de figura" :defecto="true"/>
      <c-texto :obj="m.estilo" clave="nombre_figura" etiqueta="Palabra del pie" placeholder="Figura"/>
      <template v-if="flujo">
        <c-interruptor :obj="doc" clave="numerar_tablas" etiqueta="Numerar los títulos de las tablas" :defecto="true"/>
        <c-texto :obj="doc" clave="nombre_tabla" etiqueta="Palabra de las tablas" placeholder="Tabla"/>
      </template>
    </div>

    <c-transicion v-if="!diapos" :obj="m" etiqueta="Transición entre páginas en PowerPoint"
      ayuda="Al exportar a PowerPoint, cada página entra con esta transición. En el PDF no se ve."/>

    <details class="seccion">
      <summary>Avanzado</summary>
      <div class="contenido-seccion">
        <c-interruptor v-if="!flujo" :obj="m" clave="contenido_visible" etiqueta="Mostrar el contenido" :defecto="true" ayuda="Apágalo para ver solo las capas de fondo y de frente."/>
        <c-latex :obj="m.latex" clave="preambulo" etiqueta="Preámbulo propio" ayuda="Paquetes u órdenes que se añaden antes de \\begin{document}." :filas="4"/>
        <c-latex :obj="m.latex" clave="antes" etiqueta="Justo después de \\begin{document}" :filas="2"/>
        <c-latex :obj="m.latex" clave="despues" etiqueta="Antes de \\end{document}" :filas="2"/>
      </div>
    </details>
  </div>`,
};

// ---------------------------------------------------------------- cabecera y pie
const InspCabecera = {
  name: 'insp-cabecera',
  ...comun,
  computed: { ...comun.computed, c() { return this.ed.modelo.cabecera; } },
  methods: { svg(e) { return svgCabecera(e, this.colores); }, nombre: (e) => NOMBRES_CABECERA[e] || e },
  mounted() { if (this.info.tipo === 'logo') this.$nextTick(() => this.$refs.logos && this.$refs.logos.scrollIntoView({ block: 'nearest' })); },
  template: `
  <div class="inspector">
    <div class="encabezado-insp"><span class="tipo-insp"><icono n="cabecera"/>{{ diapos ? 'Portada' : flujo ? 'Título' : 'Cabecera' }}</span><h2>{{ flujo ? 'Título y autores' : 'Título, autores y logos' }}</h2>
      <p class="ayuda" v-if="diapos">Es lo que muestran las diapositivas con el diseño «Portada».</p>
      <p class="ayuda" v-else-if="clase === 'tesis'">Van en la portada, junto con los datos de «Portada, resumen e índices».</p></div>
    <div class="seccion">
      <c-interruptor v-if="!diapos" :obj="c" clave="visible" :etiqueta="flujo ? (clase === 'tesis' ? 'Mostrar la portada' : 'Mostrar el título') : 'Mostrar la cabecera'" :defecto="true"/>
      <c-parrafo :obj="c" clave="titulo" etiqueta="Título" :filas="2"/>
      <c-texto :obj="c" clave="subtitulo" etiqueta="Subtítulo" formato/>
      <c-texto :obj="c" clave="autores" etiqueta="Autores" formato ayuda="Para las afiliaciones usa superíndices: Ana Pérez^1^"/>
      <c-texto :obj="c" clave="afiliaciones" etiqueta="Afiliaciones" formato/>
    </div>
    <div class="seccion" v-if="(flujo && clase !== 'tesis') || diapos">
      <c-segmentos :obj="c" clave="alineacion" etiqueta="Alineación" :opciones="[{valor:'centro',texto:'Centrado'},{valor:'izquierda',texto:'A la izquierda'}]"/>
    </div>
    <div class="seccion" v-if="!flujo && !diapos">
      <h3>Aspecto</h3>
      <div class="campo"><span class="etiqueta">Estilo</span>
        <div class="estilos-caja">
          <button v-for="e in cat.estilos_cabecera" :key="e" type="button" class="estilo-caja" :class="{activo: c.estilo === e}" @click="c.estilo = e"><span v-html="svg(e)"></span>{{ nombre(e) }}</button>
        </div></div>
      <c-segmentos :obj="c" clave="alineacion" etiqueta="Alineación" :opciones="[{valor:'centro',texto:'Centrada'},{valor:'izquierda',texto:'A la izquierda'}]"/>
      <c-imagen v-if="c.estilo === 'imagen'" :obj="c" clave="imagen" etiqueta="Imagen de fondo"/>
      <c-deslizador v-if="c.estilo === 'imagen'" :obj="c" clave="oscurecer" etiqueta="Oscurecer la imagen" :min="0" :max="0.9" :paso="0.05"/>
      <c-color :obj="c" clave="fondo" etiqueta="Color de fondo"/>
      <c-color :obj="c" clave="color_texto" etiqueta="Color del texto"/>
    </div>
    <div class="seccion" ref="logos" :class="{resaltada: info.tipo === 'logo'}">
      <h3>Logos</h3>
      <c-imagen :obj="c" clave="logo_izquierdo" etiqueta="Logo izquierdo"/>
      <c-deslizador v-if="c.logo_izquierdo" :obj="c" clave="tam_logo_izquierdo" etiqueta="Tamaño del logo izquierdo (%)" :min="30" :max="300" :paso="5"/>
      <c-imagen :obj="c" clave="logo_derecho" etiqueta="Logo derecho"/>
      <c-deslizador v-if="c.logo_derecho" :obj="c" clave="tam_logo_derecho" etiqueta="Tamaño del logo derecho (%)" :min="30" :max="300" :paso="5"/>
      <p class="ayuda" v-if="c.logo_izquierdo || c.logo_derecho">Cambia solo el logo: el título no se mueve. También puedes hacer clic en un logo de la vista previa y arrastrar su esquina. Si un logo deja de crecer es que ya llena el ancho de su hueco: sube «Hueco base» (eso sí estrecha el título).</p>
      <div class="fila-campos">
        <c-numero :obj="c" clave="ancho_logos" etiqueta="Hueco base (fracción del ancho)" :min="0.03" :max="0.4" :paso="0.01"/>
        <c-dimension :obj="c" clave="alto_logos" etiqueta="Alto base"/>
      </div>
    </div>
  </div>`,
};

const InspPie = {
  name: 'insp-pie',
  ...comun,
  computed: { ...comun.computed, p() { return this.ed.modelo.pie; } },
  template: `
  <div class="inspector">
    <div class="encabezado-insp"><span class="tipo-insp"><icono n="pie"/>Pie del póster</span><h2>Banda inferior</h2></div>
    <div class="seccion">
      <c-interruptor :obj="p" clave="visible" etiqueta="Mostrar el pie" :defecto="true"/>
      <c-segmentos :obj="p" clave="estilo" etiqueta="Estilo" :opciones="[{valor:'banda',texto:'Banda'},{valor:'clara',texto:'Clara'},{valor:'ninguno',texto:'Sin fondo'}]"/>
      <c-texto :obj="p" clave="izquierda" etiqueta="Texto a la izquierda" formato/>
      <c-texto :obj="p" clave="centro" etiqueta="Texto en el centro" formato/>
      <c-texto :obj="p" clave="derecha" etiqueta="Texto a la derecha" formato/>
      <c-color :obj="p" clave="fondo" etiqueta="Color de fondo"/>
      <c-color :obj="p" clave="color_texto" etiqueta="Color del texto"/>
    </div>
  </div>`,
};

// ---------------------------------------------------------------- documento: portada, resumen e índices
const InspDocumento = {
  name: 'insp-documento',
  ...comun,
  computed: {
    ...comun.computed,
    d() { return this.ed.modelo.documento; },
    p() { return this.ed.modelo.documento.portada; },
    tesis() { return this.clase === 'tesis'; },
  },
  created() { if (!this.d.portada || typeof this.d.portada !== 'object') this.d.portada = { visible: false }; },
  template: `
  <div class="inspector">
    <div class="encabezado-insp"><span class="tipo-insp"><icono n="libro"/>{{ ed.nombreClase }}</span><h2>{{ tesis ? 'Portada, resumen e índices' : 'Resumen e índices' }}</h2>
      <p class="ayuda">Lo que va antes del texto. El título y los autores están en «Título y autores». Lo que dejes vacío no aparece.</p></div>

    <div class="seccion" v-if="tesis">
      <h3>Portada</h3>
      <c-interruptor :obj="p" clave="visible" etiqueta="Página de portada" :defecto="true"/>
      <template v-if="p.visible !== false">
        <c-texto :obj="p" clave="institucion" etiqueta="Institución" formato/>
        <c-texto :obj="p" clave="dependencia" etiqueta="Facultad, departamento o programa" formato/>
        <c-texto :obj="p" clave="tipo" etiqueta="Tipo de trabajo" formato placeholder="TESIS"/>
        <c-texto :obj="p" clave="grado" etiqueta="Texto del grado" formato placeholder="que para obtener el título de …"/>
        <c-texto :obj="p" clave="presenta" etiqueta="Antes del nombre" formato placeholder="presenta"/>
        <c-parrafo :obj="p" clave="director" etiqueta="Dirección o comité" :filas="2"/>
        <div class="fila-campos">
          <c-texto :obj="p" clave="lugar" etiqueta="Lugar" formato/>
          <c-texto :obj="p" clave="fecha" etiqueta="Fecha" formato/>
        </div>
      </template>
    </div>
    <div class="seccion" v-if="tesis">
      <h3>Páginas preliminares</h3>
      <c-parrafo :obj="d" clave="dedicatoria" etiqueta="Dedicatoria" :filas="2"/>
      <c-texto :obj="d" clave="titulo_agradecimientos" etiqueta="Título de los agradecimientos"/>
      <c-parrafo :obj="d" clave="agradecimientos" etiqueta="Agradecimientos" :filas="4"/>
    </div>

    <div class="seccion">
      <h3>Resumen</h3>
      <c-texto :obj="d" clave="titulo_resumen" etiqueta="Título" placeholder="Resumen"/>
      <c-parrafo :obj="d" clave="resumen" etiqueta="Texto del resumen" :filas="6"/>
      <div class="fila-campos">
        <c-texto :obj="d" clave="titulo_palabras" etiqueta="Rótulo" placeholder="Palabras clave"/>
        <c-texto :obj="d" clave="palabras_clave" etiqueta="Palabras clave" formato/>
      </div>
    </div>
    <details class="seccion" :open="!!(d.resumen2 || d.palabras_clave2)">
      <summary>Resumen en otro idioma</summary>
      <div class="contenido-seccion">
        <c-texto :obj="d" clave="titulo_resumen2" etiqueta="Título" placeholder="Abstract"/>
        <c-parrafo :obj="d" clave="resumen2" etiqueta="Texto" :filas="6"/>
        <div class="fila-campos">
          <c-texto :obj="d" clave="titulo_palabras2" etiqueta="Rótulo" placeholder="Keywords"/>
          <c-texto :obj="d" clave="palabras_clave2" etiqueta="Palabras clave" formato/>
        </div>
      </div>
    </details>

    <div class="seccion">
      <h3>Índices</h3>
      <c-interruptor :obj="d" clave="indice" etiqueta="Índice del contenido"/>
      <c-texto v-if="d.indice" :obj="d" clave="titulo_indice" etiqueta="Título del índice" placeholder="Índice"/>
      <c-interruptor :obj="d" clave="lista_figuras" etiqueta="Índice de figuras"/>
      <c-texto v-if="d.lista_figuras" :obj="d" clave="titulo_figuras" etiqueta="Título" placeholder="Índice de figuras"/>
      <c-interruptor :obj="d" clave="lista_tablas" etiqueta="Índice de tablas"/>
      <c-texto v-if="d.lista_tablas" :obj="d" clave="titulo_tablas" etiqueta="Título" placeholder="Índice de tablas"/>
      <p class="ayuda">Se rellenan solos con los títulos de las secciones y los pies de figuras y tablas.</p>
    </div>
    <details class="seccion" v-if="tesis">
      <summary>Palabras de capítulos y apéndices</summary>
      <div class="contenido-seccion">
        <div class="fila-campos">
          <c-texto :obj="d" clave="nombre_capitulo" etiqueta="Capítulo" placeholder="Capítulo"/>
          <c-texto :obj="d" clave="nombre_apendice" etiqueta="Apéndice" placeholder="Apéndice"/>
        </div>
      </div>
    </details>
  </div>`,
};

// ---------------------------------------------------------------- diapositiva
const InspPagina = {
  name: 'insp-pagina',
  ...comun,
  components: { ...CAMPOS, CTransicion },
  props: { info: Object },
  methods: {
    aTodas() {
      for (const pg of this.ed.modelo.paginas) {
        if (pg !== this.p) pg.transicion = { ...this.p.transicion };
      }
    },
  },
  computed: {
    ...comun.computed,
    p() { return this.info.obj; },
    disenos() { return (this.cat.disenos_pagina || []).map((k) => ({ valor: k, texto: NOMBRES_DISENO[k] || k })); },
    conTitulo() { return ['contenido', 'seccion'].includes(this.p.diseno); },
    sueltas() { return this.ed.modelo.filas.filter((f) => f.pag === this.p.id).reduce((n, f) => n + f.columnas.reduce((k, c) => k + c.bloques.filter((b) => b.libre).length, 0), 0); },
  },
  template: `
  <div class="inspector">
    <div class="encabezado-insp"><span class="tipo-insp"><icono n="diapositiva"/>Diapositiva {{ info.i + 1 }} de {{ info.lista.length }}</span><h2>{{ p.nombre || 'Sin título' }}</h2>
      <div class="acciones-insp">
        <button class="btn pequeno primario" @click="ed.agregarFila(1)"><icono n="fila"/>Fila</button>
        <button class="btn pequeno" @click="ed.agregarLibre('texto')"><icono n="texto"/>Texto suelto</button>
        <button class="btn pequeno" @click="ed.agregarLibre('imagen')"><icono n="imagen"/>Imagen suelta</button>
      </div>
      <div class="acciones-insp">
        <button class="btn pequeno" @click="ed.desplazar(p.id, -1)" :disabled="info.i === 0"><icono n="arriba"/>Antes</button>
        <button class="btn pequeno" @click="ed.desplazar(p.id, 1)" :disabled="info.i === info.lista.length - 1"><icono n="abajo"/>Después</button>
        <button class="btn pequeno" @click="ed.duplicar(p.id)"><icono n="duplicar"/>Duplicar</button>
        <button class="btn pequeno peligro" @click="ed.eliminar(p.id)" :disabled="info.lista.length < 2"><icono n="basura"/>Borrar</button>
      </div></div>
    <div class="seccion">
      <c-seleccion :obj="p" clave="diseno" etiqueta="Diseño" :opciones="disenos"/>
      <p class="ayuda" v-if="p.diseno === 'portada'">Muestra el título, los autores y los logos de «Portada: título y autores».</p>
      <c-texto :obj="p" clave="nombre" :etiqueta="conTitulo ? 'Título' : 'Nombre (solo para la lista)'" formato/>
      <c-texto v-if="conTitulo" :obj="p" clave="subtitulo" etiqueta="Subtítulo" formato/>
      <c-segmentos v-if="p.diseno === 'contenido'" :obj="p" clave="estilo" etiqueta="Estilo del título"
        :opciones="[{valor:'',texto:'General'},{valor:'banda',texto:'Banda'},{valor:'linea',texto:'Línea'},{valor:'simple',texto:'Sencillo'}]"/>
    </div>
    <div class="seccion">
      <div class="campo">
        <label class="interruptor"><span class="texto">Lienzo libre en esta diapositiva</span>
          <input type="checkbox" :checked="!!p.libre" @click.prevent="ed.lienzoLibre(!p.libre)"><span class="pista"></span></label>
        <span class="ayuda" v-if="p.libre">Sus cajas están sueltas ({{ sueltas }}): arrástralas en la vista previa. Lo que añadas también queda suelto.</span>
        <span class="ayuda" v-else>Suelta todas sus cajas de la cuadrícula para colocarlas a mano. Para soltar solo una, selecciónala y usa «Soltar de la cuadrícula».</span>
      </div>
      <c-color :obj="p" clave="fondo" etiqueta="Color de fondo" vacio="El general"/>
      <c-interruptor :obj="p" clave="pie" etiqueta="Mostrar el pie y el número" :defecto="true"/>
      <c-interruptor :obj="p" clave="visible" etiqueta="Incluir en la presentación" :defecto="true" ayuda="Apagada se conserva aquí, pero no sale en el PDF."/>
    </div>
    <c-transicion :obj="p" ayuda="Al exportar a PowerPoint, esta diapositiva entra con esta transición. En el PDF no se ve.">
      <button v-if="p.transicion" class="btn pequeno" style="justify-self:start" @click="aTodas">Usarla en todas las diapositivas</button>
    </c-transicion>
    <div class="seccion">
      <c-parrafo :obj="p" clave="notas" etiqueta="Notas para quien expone" :filas="3"/>
      <p class="ayuda">No salen en el PDF.</p>
    </div>
  </div>`,
};

// ---------------------------------------------------------------- filas y columnas
const InspFila = {
  name: 'insp-fila',
  ...comun,
  props: { info: Object },
  computed: {
    ...comun.computed,
    f() { return this.info.obj; },
    modoAlto() { const a = this.f.alto || 'auto'; return a === 'auto' || a === 'llenar' ? a : 'fijo'; },
    suma() { return this.f.columnas.reduce((s, c) => s + Math.max(1, Number(c.abarca) || 1), 0); },
  },
  methods: {
    ponerAlto(modo) { this.f.alto = modo === 'fijo' ? '40cm' : modo; },
  },
  template: `
  <div class="inspector">
    <div class="encabezado-insp"><span class="tipo-insp"><icono n="fila"/>Fila</span><h2>Fila {{ (info.n ?? info.i) + 1 }}</h2>
      <div class="acciones-insp">
        <button class="btn pequeno" @click="ed.agregarHijo(f.id)"><icono n="mas"/>Columna</button>
        <button class="btn pequeno" @click="ed.desplazar(f.id, -1)" :disabled="info.i === 0"><icono n="arriba"/>Subir</button>
        <button class="btn pequeno" @click="ed.desplazar(f.id, 1)" :disabled="info.i === info.lista.length - 1"><icono n="abajo"/>Bajar</button>
        <button class="btn pequeno peligro" @click="ed.eliminar(f.id)"><icono n="basura"/>Borrar</button>
      </div></div>
    <div class="seccion">
      <c-interruptor :obj="f" clave="visible" etiqueta="Mostrar la fila" :defecto="true"/>
      <div class="campo"><span class="etiqueta">Alto de la fila</span>
        <div class="segmentos">
          <button type="button" :class="{activo: modoAlto==='auto'}" @click="ponerAlto('auto')">Automático</button>
          <button type="button" :class="{activo: modoAlto==='llenar'}" @click="ponerAlto('llenar')">Llenar la página</button>
          <button type="button" :class="{activo: modoAlto==='fijo'}" @click="ponerAlto('fijo')">Fijo</button>
        </div>
        <span class="ayuda" v-if="modoAlto==='llenar'">Ocupa todo el alto libre hasta el pie. Las columnas terminan a la misma altura.</span>
      </div>
      <c-dimension v-if="modoAlto==='fijo'" :obj="f" clave="alto" etiqueta="Alto"/>
      <c-numero :obj="f" clave="rejilla" etiqueta="Columnas de la retícula" :min="0" :max="12" :paso="1"
        :ayuda="'0 = la suma de lo que ocupan sus columnas (ahora ' + suma + ').'"/>
      <c-interruptor :obj="f" clave="igualar" etiqueta="Columnas de la misma altura" :defecto="true"/>
      <div class="fila-campos">
        <c-dimension :obj="f" clave="separacion" etiqueta="Separación entre columnas" :placeholder="ed.modelo.estilo.separacion_columnas"/>
        <c-dimension :obj="f" clave="despues" etiqueta="Espacio después" placeholder="el general"/>
      </div>
    </div>
  </div>`,
};

const InspColumna = {
  name: 'insp-columna',
  ...comun,
  props: { info: Object },
  computed: { ...comun.computed, c() { return this.info.obj; }, maximo() { return Math.max(1, Number(this.info.fila.rejilla) || 6); } },
  template: `
  <div class="inspector">
    <div class="encabezado-insp"><span class="tipo-insp"><icono n="columna"/>Columna</span><h2>Columna {{ info.i + 1 }} de la fila</h2>
      <div class="acciones-insp">
        <button class="btn pequeno" @click="ed.agregarHijo(c.id)"><icono n="mas"/>Caja</button>
        <button class="btn pequeno" @click="ed.desplazar(c.id, -1)" :disabled="info.i === 0"><icono n="arriba"/>Antes</button>
        <button class="btn pequeno" @click="ed.desplazar(c.id, 1)" :disabled="info.i === info.lista.length - 1"><icono n="abajo"/>Después</button>
        <button class="btn pequeno peligro" @click="ed.eliminar(c.id)"><icono n="basura"/>Borrar</button>
      </div></div>
    <div class="seccion">
      <c-deslizador :obj="c" clave="abarca" etiqueta="Columnas de la retícula que ocupa" :min="1" :max="maximo" :paso="1"/>
      <c-segmentos :obj="c" clave="distribucion" etiqueta="Reparto del alto entre sus cajas"
        :opciones="[{valor:'repartir',texto:'Repartir'},{valor:'arriba',texto:'Arriba'},{valor:'centro',texto:'Centro'},{valor:'abajo',texto:'Abajo'}]"
        ayuda="Cuando la fila es más alta que la columna: repartir separa las cajas; arriba, centro y abajo las juntan."/>
    </div>
  </div>`,
};

// ---------------------------------------------------------------- caja
const InspBloque = {
  name: 'insp-bloque',
  ...comun,
  components: { ...CAMPOS, SelectorEstilo, CAnimacion },
  props: { info: Object },
  computed: {
    ...comun.computed,
    b() { return this.info.obj; },
    op() { return this.b.opciones || {}; },
    titulosGlobales() { return this.ed.modelo.estilo.mostrar_titulos !== false; },
    suelta() { return !!this.b.libre && !this.flujo; },
    niveles() { return ((this.cat.niveles || {})[this.clase] || []).map((t, i) => ({ valor: i + 1, texto: t })); },
    nombreNivel() { return nombreNivel(this.ed.modelo, this.b.nivel); },
    unico() { return this.suelta && this.b.elementos.length === 1 ? this.b.elementos[0] : null; },
    camposUnico() { const v = this.unico && variante(this.unico); return v ? v.campos.filter((c) => !['titulo', 'mostrar_titulo'].includes(c.nombre)) : []; },
  },
  created() {
    if (!this.b.opciones || Array.isArray(this.b.opciones)) this.b.opciones = {};
    if (this.flujo && !this.b.nivel) this.b.nivel = 1;
  },
  template: `
  <div class="inspector" v-if="flujo">
    <div class="encabezado-insp"><span class="tipo-insp"><icono n="caja"/>{{ nombreNivel }}</span><h2>{{ b.titulo || 'Sin título' }}</h2>
      <div class="acciones-insp">
        <button class="btn pequeno primario" @click="ed.agregarHijo(b.id)"><icono n="mas"/>Elemento</button>
        <button class="btn pequeno" @click="ed.desplazar(b.id, -1)" :disabled="info.i === 0"><icono n="arriba"/>Subir</button>
        <button class="btn pequeno" @click="ed.desplazar(b.id, 1)" :disabled="info.i === info.lista.length - 1"><icono n="abajo"/>Bajar</button>
        <button class="btn pequeno" @click="ed.duplicar(b.id)"><icono n="duplicar"/>Duplicar</button>
        <button class="btn pequeno peligro" @click="ed.eliminar(b.id)"><icono n="basura"/>Borrar</button>
      </div></div>
    <div class="seccion">
      <c-texto :obj="b" clave="titulo" etiqueta="Título" formato/>
      <c-segmentos :obj="b" clave="nivel" etiqueta="Nivel" :opciones="niveles"/>
      <c-interruptor :obj="b" clave="mostrar_titulo" etiqueta="Mostrar el título" :defecto="true" ayuda="Sin título, su contenido sigue al de la sección anterior."/>
      <c-interruptor :obj="b" clave="numerar" etiqueta="Numerar" :defecto="true" ayuda="Apágalo en las referencias o los agradecimientos."/>
      <c-interruptor :obj="b" clave="salto" etiqueta="Empezar en una página nueva"/>
      <c-interruptor v-if="clase === 'tesis' && Number(b.nivel) === 1" :obj="b" clave="apendice" etiqueta="Es un apéndice" ayuda="Se numera con letras: Apéndice A, B…"/>
      <c-interruptor :obj="b" clave="visible" etiqueta="Incluir en el documento" :defecto="true"/>
    </div>
  </div>
  <div class="inspector" v-else>
    <div class="encabezado-insp"><span class="tipo-insp"><icono n="caja"/>{{ suelta ? 'Caja suelta' : 'Caja' }}</span><h2>{{ b.titulo || (suelta ? 'Caja suelta' : 'Caja sin título') }}</h2>
      <div class="acciones-insp">
        <button class="btn pequeno primario" @click="ed.agregarHijo(b.id)"><icono n="mas"/>Elemento</button>
        <button v-if="!suelta" class="btn pequeno" @click="ed.desplazar(b.id, -1)" :disabled="info.i === 0"><icono n="arriba"/>Subir</button>
        <button v-if="!suelta" class="btn pequeno" @click="ed.desplazar(b.id, 1)" :disabled="info.i === info.lista.length - 1"><icono n="abajo"/>Bajar</button>
        <button class="btn pequeno" @click="ed.duplicar(b.id)"><icono n="duplicar"/>Duplicar</button>
        <button class="btn pequeno peligro" @click="ed.eliminar(b.id)"><icono n="basura"/>Borrar</button>
      </div>
      <div class="acciones-insp">
        <button v-if="!suelta" class="btn pequeno" @click="ed.soltar(b.id)" title="Sale de su columna y se coloca arrastrándola a cualquier punto de la página"><icono n="arrastrar"/>Soltar de la cuadrícula</button>
        <button v-else class="btn pequeno" @click="ed.aCuadricula(b.id)" title="Vuelve a su fila y su columna"><icono n="columna"/>Volver a la cuadrícula</button>
      </div>
      <p class="ayuda" v-if="suelta">Arrástrala en la vista previa; el cuadrito de la esquina cambia su ancho. Con las flechas del teclado se mueve poco a poco.</p></div>
    <div class="seccion" v-if="suelta">
      <h3>Posición <span class="ayuda">0 = izquierda o arriba, 1 = derecha o abajo</span></h3>
      <div class="fila-campos">
        <c-dimension :obj="b" clave="x" etiqueta="x" numero-valido/>
        <c-dimension :obj="b" clave="y" etiqueta="y" numero-valido/>
        <c-dimension :obj="b" clave="ancho" etiqueta="Ancho" numero-valido/>
        <c-dimension :obj="b" clave="alto" etiqueta="Alto" numero-valido placeholder="automático"/>
      </div>
      <c-deslizador :obj="b" clave="rotacion" etiqueta="Giro (grados)" :min="-180" :max="180" :paso="1"/>
    </div>
    <div class="seccion" v-if="unico && camposUnico.length">
      <h3>Contenido</h3>
      <campo-variante v-for="c in camposUnico" :key="c.nombre" :obj="unico" :campo="c"/>
    </div>
    <div class="seccion">
      <div class="tarjeta-titulo">
        <c-texto :obj="b" clave="titulo" etiqueta="Título" formato/>
        <c-interruptor :obj="b" clave="mostrar_titulo" etiqueta="Mostrar el título" :defecto="true"
          :ayuda="titulosGlobales ? 'El título se guarda aunque esté oculto.' : 'Los títulos están apagados en el diseño general (Cajas).'"/>
      </div>
      <div class="fila-campos">
        <c-texto :obj="b" clave="numero" etiqueta="Número" placeholder="automático"/>
        <c-interruptor :obj="b" clave="visible" etiqueta="Mostrar la caja" :defecto="true"/>
      </div>
      <c-interruptor v-if="!suelta" :obj="b" clave="estirar" etiqueta="Estirar hasta el final de la columna" ayuda="Útil en la última caja de cada columna para que todas terminen igual."/>
    </div>
    <div class="seccion">
      <selector-estilo :obj="b" clave="estilo" con-defecto/>
    </div>
    <c-animacion :obj="b" que="la caja entera (con lo que tenga dentro sin animación propia)"/>
    <details class="seccion">
      <summary>Colores, bordes y texto de esta caja</summary>
      <div class="contenido-seccion">
        <c-color :obj="op" clave="fondo" etiqueta="Fondo"/>
        <c-color :obj="op" clave="borde" etiqueta="Borde"/>
        <c-color :obj="op" clave="fondo_titulo" etiqueta="Fondo del título"/>
        <c-color :obj="op" clave="color_titulo" etiqueta="Color del título"/>
        <c-color :obj="op" clave="color_texto" etiqueta="Color del texto"/>
        <div class="fila-campos">
          <c-dimension :obj="op" clave="grosor_borde" etiqueta="Grosor del borde" placeholder="0.07em"/>
          <c-dimension :obj="op" clave="radio" etiqueta="Redondeo" placeholder="el general"/>
          <c-dimension :obj="op" clave="relleno" etiqueta="Margen interior" placeholder="el general"/>
          <c-dimension :obj="op" clave="alto" etiqueta="Alto fijo" placeholder="automático"/>
          <c-numero :obj="op" clave="escala_titulo" etiqueta="Escala del título" :min="0.5" :max="4" :paso="0.05"/>
          <c-numero :obj="op" clave="escala_texto" etiqueta="Escala del texto" :min="0.4" :max="4" :paso="0.05"/>
          <c-numero :obj="op" clave="columnas" etiqueta="Columnas de texto" :min="1" :max="4" :paso="1"/>
          <c-numero :obj="op" clave="opacidad" etiqueta="Opacidad del fondo" :min="0" :max="1" :paso="0.05"/>
        </div>
        <c-segmentos :obj="op" clave="alineacion_titulo" etiqueta="Alineación del título" :opciones="[{valor:'',texto:'General'},{valor:'izquierda',texto:'Izq.'},{valor:'centro',texto:'Centro'},{valor:'derecha',texto:'Der.'}]"/>
        <c-segmentos :obj="op" clave="alinear_texto" etiqueta="Alineación del texto" :opciones="[{valor:'',texto:'General'},{valor:'justificado',texto:'Justif.'},{valor:'izquierda',texto:'Izq.'},{valor:'centro',texto:'Centro'}]"/>
        <c-interruptor :obj="op" clave="sombra" etiqueta="Sombra"/>
        <c-latex :obj="op" clave="tcb" etiqueta="Opciones de tcolorbox" ayuda="Para usuarios de LaTeX: se añaden tal cual (p. ej. sharp corners)." :filas="2"/>
      </div>
    </details>
  </div>`,
};

// ---------------------------------------------------------------- elemento de caja
const InspElemento = {
  name: 'insp-elemento',
  ...comun,
  components: { ...CAMPOS, CAnimacion },
  props: { info: Object },
  computed: {
    ...comun.computed,
    e() { return this.info.obj; },
    v() { return variante(this.e); },
    campos() {
      if (!this.v) return [];
      return this.v.campos.filter((c) => !(tieneTitulo(this.e) && (c.nombre === 'titulo' || c.nombre === 'mostrar_titulo')));
    },
    conTitulo() { return tieneTitulo(this.e); },
    comp() { return this.v && this.v.componente ? this.v.componente : null; },
    enLab() { return this.comp ? (tienda.biblioteca || []).find((x) => x.id === this.comp.id) : null; },
    masNueva() { return this.enLab && this.enLab.version > (this.comp.version || 0) ? this.enLab.version : 0; },
    mismosGrupo() {
      if (!this.v) return [];
      return this.cat.variantes.filter((x) => x.grupo === this.v.grupo).map((x) => ({ valor: x.clave, texto: `${x.codigo} · ${x.nombre}` }));
    },
  },
  methods: {
    verReferencias() { this.ed.verIzq = true; this.ed.panelIzq = 'referencias'; },
  },
  template: `
  <div class="inspector" v-if="!v">
    <div class="encabezado-insp"><span class="tipo-insp"><icono n="alerta"/>Elemento</span><h2>Componente que falta</h2>
      <p class="ayuda">Este documento no trae la definición del componente «{{ e.tipo.slice(4) }}». Bórralo o cámbialo por otro elemento.</p>
      <div class="acciones-insp"><button class="btn pequeno peligro" @click="ed.eliminar(e.id)"><icono n="basura"/>Borrar</button></div></div>
  </div>
  <div class="inspector" v-else>
    <div class="encabezado-insp"><span class="tipo-insp"><icono :n="comp ? 'pieza' : 'texto'"/>{{ comp ? 'Componente propio · versión ' + (comp.version || 1) : 'Elemento ' + v.codigo }}</span><h2>{{ v.nombre }}</h2>
      <div v-if="comp" class="tarjeta-componente">
        <p class="ayuda" v-if="v.nota">{{ v.nota }}</p>
        <p class="ayuda" v-if="masNueva">En el Lab hay una versión más nueva ({{ masNueva }}). Al ponerla al día cambia en todo el documento.</p>
        <div class="acciones-insp">
          <button class="btn pequeno" @click="ed.abrirEnLab(comp.id)"><icono n="matraz"/>Abrir en el Lab</button>
          <button v-if="masNueva" class="btn pequeno primario" @click="ed.ponerAlDia(comp.id)"><icono n="compilar"/>Poner al día</button>
        </div>
      </div>
      <div class="acciones-insp">
        <button class="btn pequeno" @click="ed.desplazar(e.id, -1)" :disabled="info.i === 0"><icono n="arriba"/>Subir</button>
        <button class="btn pequeno" @click="ed.desplazar(e.id, 1)" :disabled="info.i === info.lista.length - 1"><icono n="abajo"/>Bajar</button>
        <button class="btn pequeno" @click="ed.duplicar(e.id)"><icono n="duplicar"/>Duplicar</button>
        <button class="btn pequeno peligro" @click="ed.eliminar(e.id)"><icono n="basura"/>Borrar</button>
      </div>
      <div class="acciones-insp" v-if="!flujo && !info.bloque.libre">
        <button class="btn pequeno" @click="ed.soltar(e.id)" title="Sale de su caja y se coloca arrastrándolo a cualquier punto de la página"><icono n="arrastrar"/>Soltar de la cuadrícula</button>
      </div></div>
    <div class="seccion" v-if="conTitulo">
      <div class="tarjeta-titulo">
        <c-texto :obj="e" clave="titulo" etiqueta="Título de la caja" formato/>
        <c-interruptor :obj="e" clave="mostrar_titulo" etiqueta="Mostrar el título" :defecto="v.clave === 'txtCajaTitulo' || v.clave === 'txtCaja'"/>
      </div>
    </div>
    <div class="seccion">
      <p v-if="v.nota && !comp" class="ayuda">{{ v.nota }}</p>
      <template v-if="v.clave === 'bibliografia'">
        <div class="campo"><label class="etiqueta" for="estilo-bib">Estilo de las referencias</label>
          <select id="estilo-bib" class="entrada" v-model="ed.modelo.bibliografia.estilo">
            <option v-for="(d, k) in cat.bibliografia.estilos" :key="k" :value="k">{{ d.nombre }}</option>
          </select></div>
        <button class="btn pequeno" style="justify-self:start" @click="verReferencias"><icono n="libro"/>Editar las referencias ({{ ed.modelo.bibliografia.referencias.length }})</button>
      </template>
      <campo-variante v-for="c in campos" :key="c.nombre" :obj="e" :campo="c"/>
      <c-interruptor :obj="e" clave="visible" etiqueta="Mostrar el elemento" :defecto="true"/>
    </div>
    <c-animacion :obj="e"/>
    <details class="seccion" v-if="!comp">
      <summary>Cambiar por otra variante</summary>
      <div class="contenido-seccion">
        <p class="ayuda">Se conservan los campos que se llaman igual (texto, imagen, pie…).</p>
        <div class="campo"><label class="etiqueta" for="cambio-var">Variante</label>
          <select id="cambio-var" class="entrada" :value="e.tipo" @change="ed.cambiarVariante(e.id, $event.target.value)">
            <option v-for="o in mismosGrupo" :key="o.valor" :value="o.valor">{{ o.texto }}</option>
          </select></div>
        <button class="btn pequeno" style="justify-self:start" @click="ed.abrirVariantes(info.bloque.id, e.id)">Ver todas las variantes</button>
      </div>
    </details>
  </div>`,
};

// ---------------------------------------------------------------- capas
const InspCapa = {
  name: 'insp-capa',
  ...comun,
  props: { info: Object },
  computed: {
    ...comun.computed,
    c() { return this.info.obj; },
    propia() { return !['fondo', 'frente'].includes(this.c.id); },
  },
  template: `
  <div class="inspector">
    <div class="encabezado-insp"><span class="tipo-insp"><icono n="capas"/>Capa</span><h2>{{ c.nombre }}</h2>
      <p class="ayuda">{{ Number(c.z) < 0 ? 'Se pinta detrás del contenido.' : 'Se pinta delante del contenido.' }} Sus elementos se colocan en cualquier punto del lienzo.</p>
      <div class="acciones-insp">
        <button class="btn pequeno" @click="ed.agregarItem(c.id, 'texto')"><icono n="texto"/>Texto</button>
        <button class="btn pequeno" @click="ed.agregarItem(c.id, 'imagen')"><icono n="imagen"/>Imagen</button>
        <button class="btn pequeno" @click="ed.agregarItem(c.id, 'forma')"><icono n="forma"/>Forma</button>
        <button class="btn pequeno" @click="ed.agregarItem(c.id, 'latex')"><icono n="codigo"/>LaTeX</button>
      </div></div>
    <div class="seccion">
      <c-texto :obj="c" clave="nombre" etiqueta="Nombre"/>
      <c-interruptor :obj="c" clave="visible" etiqueta="Mostrar la capa" :defecto="true"/>
      <c-deslizador :obj="c" clave="z" etiqueta="Orden (z)" :min="-50" :max="50" :paso="1"
        ayuda="Negativo: detrás del contenido. Positivo: delante. Entre capas, la de z mayor queda encima."/>
      <c-deslizador :obj="c" clave="opacidad" etiqueta="Opacidad de toda la capa" :min="0" :max="1" :paso="0.05"/>
      <button v-if="propia" class="btn pequeno peligro" style="justify-self:start" @click="ed.eliminar(c.id)"><icono n="basura"/>Borrar la capa</button>
    </div>
  </div>`,
};

const InspItem = {
  name: 'insp-item',
  ...comun,
  components: { ...CAMPOS, CAnimacion },
  props: { info: Object },
  computed: {
    ...comun.computed,
    it() { return this.info.obj; },
    capas() { return this.ed.modelo.capas.map((c) => ({ valor: c.id, texto: `${c.nombre} (z ${c.z})` })); },
    titulo() { return nombreNodo(this.info); },
    esLinea() { return this.it.tipo === 'forma' && ['linea', 'flecha'].includes(this.it.forma); },
  },
  template: `
  <div class="inspector">
    <div class="encabezado-insp"><span class="tipo-insp"><icono n="capas"/>Elemento de la capa «{{ info.capa.nombre }}»</span><h2>{{ titulo }}</h2>
      <div class="acciones-insp">
        <button class="btn pequeno" @click="ed.duplicar(it.id)"><icono n="duplicar"/>Duplicar</button>
        <button class="btn pequeno peligro" @click="ed.eliminar(it.id)"><icono n="basura"/>Borrar</button>
      </div>
      <p class="ayuda">Arrástralo en la vista previa para moverlo; el cuadrito de la esquina cambia su tamaño.</p></div>

    <div class="seccion" v-if="it.tipo === 'imagen'">
      <c-imagen :obj="it" clave="archivo" etiqueta="Imagen"/>
      <c-segmentos :obj="it" clave="ajuste" etiqueta="Ajuste" :opciones="[{valor:'ajustar',texto:'Ajustar'},{valor:'cubrir',texto:'Cubrir (recorta)'},{valor:'estirar',texto:'Estirar'}]"/>
    </div>
    <div class="seccion" v-else-if="it.tipo === 'texto'">
      <c-parrafo :obj="it" clave="texto" etiqueta="Texto" :filas="3"/>
      <div class="fila-campos">
        <c-numero :obj="it" clave="escala" etiqueta="Tamaño (× letra)" :min="0.2" :max="40" :paso="0.1"/>
        <c-segmentos :obj="it" clave="alineacion" etiqueta="Alineación" :opciones="[{valor:'izquierda',texto:'Izq.'},{valor:'centro',texto:'Centro'},{valor:'derecha',texto:'Der.'}]"/>
      </div>
      <div class="fila-campos">
        <c-interruptor :obj="it" clave="negrita" etiqueta="Negrita"/>
        <c-interruptor :obj="it" clave="cursiva" etiqueta="Cursiva"/>
      </div>
      <c-color :obj="it" clave="color" etiqueta="Color del texto"/>
      <c-color :obj="it" clave="fondo" etiqueta="Fondo" vacio="Sin fondo"/>
      <c-color :obj="it" clave="borde" etiqueta="Borde" vacio="Sin borde"/>
      <div class="fila-campos tres">
        <c-dimension :obj="it" clave="grosor" etiqueta="Grosor"/>
        <c-dimension :obj="it" clave="radio" etiqueta="Redondeo"/>
        <c-dimension :obj="it" clave="relleno" etiqueta="Margen"/>
      </div>
    </div>
    <div class="seccion" v-else-if="it.tipo === 'forma'">
      <c-segmentos :obj="it" clave="forma" etiqueta="Forma" :opciones="[{valor:'rectangulo',texto:'Rect.'},{valor:'circulo',texto:'Círculo'},{valor:'elipse',texto:'Elipse'},{valor:'linea',texto:'Línea'},{valor:'flecha',texto:'Flecha'}]"/>
      <c-color v-if="!esLinea" :obj="it" clave="fondo" etiqueta="Relleno" vacio="Sin relleno"/>
      <c-color :obj="it" :clave="esLinea ? 'color' : 'borde'" :etiqueta="esLinea ? 'Color de la línea' : 'Borde'" :vacio="esLinea ? 'Color del texto' : 'Sin borde'"/>
      <div class="fila-campos">
        <c-dimension :obj="it" clave="grosor" etiqueta="Grosor"/>
        <c-dimension v-if="!esLinea" :obj="it" clave="radio" etiqueta="Redondeo"/>
      </div>
      <div class="fila-campos" v-if="esLinea">
        <c-dimension :obj="it" clave="x2" etiqueta="Hasta x" numero-valido placeholder="0–1"/>
        <c-dimension :obj="it" clave="y2" etiqueta="Hasta y" numero-valido placeholder="0–1"/>
      </div>
    </div>
    <div class="seccion" v-else>
      <c-latex :obj="it" clave="codigo" etiqueta="Código LaTeX" :filas="5"/>
    </div>

    <div class="seccion">
      <h3>Posición <span class="ayuda">0 = izquierda o arriba, 1 = derecha o abajo</span></h3>
      <div class="fila-campos">
        <c-dimension :obj="it" clave="x" etiqueta="x" numero-valido/>
        <c-dimension :obj="it" clave="y" etiqueta="y" numero-valido/>
        <c-dimension :obj="it" clave="ancho" etiqueta="Ancho" numero-valido placeholder="automático"/>
        <c-dimension :obj="it" clave="alto" etiqueta="Alto" numero-valido placeholder="automático"/>
      </div>
      <c-ancla :obj="it" clave="ancla" etiqueta="Punto que se coloca en (x, y)"/>
      <c-deslizador :obj="it" clave="rotacion" etiqueta="Giro (grados)" :min="-180" :max="180" :paso="1"/>
      <c-deslizador :obj="it" clave="opacidad" etiqueta="Opacidad" :min="0" :max="1" :paso="0.05"/>
      <div class="fila-campos">
        <c-numero :obj="it" clave="pagina" etiqueta="Solo en la página" :min="1" :paso="1" ayuda="Vacío = todas"/>
        <c-interruptor :obj="it" clave="visible" etiqueta="Visible" :defecto="true"/>
      </div>
      <div class="campo"><label class="etiqueta" for="mover-capa">Capa</label>
        <select id="mover-capa" class="entrada" :value="info.capa.id" @change="ed.moverItemACapa(it.id, $event.target.value)">
          <option v-for="o in capas" :key="o.valor" :value="o.valor">{{ o.texto }}</option>
        </select></div>
    </div>
    <c-animacion :obj="it"/>
  </div>`,
};

export const Inspector = {
  name: 'inspector-editor',
  components: { InspPoster, InspCabecera, InspPie, InspFila, InspColumna, InspBloque, InspElemento, InspCapa, InspItem, InspDocumento, InspPagina },
  setup() { return { ed: inject('ed') }; },
  computed: {
    info() { return this.ed.indice.get(this.ed.sel || 'poster') || this.ed.indice.get('poster'); },
    componente() { return this.info.tipo === 'logo' ? 'insp-cabecera' : `insp-${this.info.tipo}`; },
    clave() { return `${this.info.tipo}:${(this.info.obj && this.info.obj.id) || this.info.tipo}`; },
  },
  template: `<component :is="componente" :info="info" :key="clave"/>`,
};
