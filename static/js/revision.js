// SPDX-License-Identifier: AGPL-3.0-only
// Revisión antes de imprimir (panel lateral) y PDF para imprenta (diálogo).
import { post, esperarTrabajo, descargar } from './api.js';
import { tienda, avisar, avisarError } from './tienda.js';
import { tamano } from './util.js';

const { inject } = Vue;

const ICONO_NIVEL = { problema: 'alerta', aviso: 'info', bien: 'check', info: 'info' };
const ORDEN = { problema: 0, aviso: 1, info: 2, bien: 3 };
const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;
const numero = (x, d = 0) => Number(x).toLocaleString('es', { maximumFractionDigits: d });

// ---------------------------------------------------------------- panel de revisión
export const PanelRevision = {
  name: 'panel-revision',
  emits: ['cerrar', 'imprenta'],
  setup() { return { ed: inject('ed') }; },
  data: () => ({ cargando: false, progreso: 0, mensaje: '', resultado: null, error: '', abiertas: {} }),
  computed: {
    secciones() { return (this.resultado && this.resultado.secciones) || []; },
    resumen() { return (this.resultado && this.resultado.resumen) || { problemas: 0, avisos: 0, bien: 0 }; },
    papel() {
      const p = this.resultado && this.resultado.papel;
      if (!p) return '';
      const nombre = p.nombre ? `${p.nombre}, ` : '';
      return `${nombre}${numero(p.ancho_mm)} × ${numero(p.alto_mm)} mm, ${plural(p.paginas || 1, 'página', 'páginas')}`;
    },
    titular() {
      const r = this.resumen;
      if (r.problemas) return plural(r.problemas, 'cosa por corregir', 'cosas por corregir');
      if (r.avisos) return 'Se puede imprimir';
      return 'Listo para imprimir';
    },
    subtitular() {
      const r = this.resumen;
      if (r.problemas) return r.avisos ? `Y ${plural(r.avisos, 'aviso', 'avisos')} que conviene mirar.` : 'Lo demás está en orden.';
      if (r.avisos) return `Con ${plural(r.avisos, 'aviso', 'avisos')} que conviene mirar antes.`;
      return 'Imágenes, letra, colores y tipografías en orden.';
    },
    estadoGeneral() { return this.resumen.problemas ? 'problema' : this.resumen.avisos ? 'aviso' : 'bien'; },
    conPoster() { return !!this.ed.modelo; },
  },
  methods: {
    icono(n) { return ICONO_NIVEL[n] || 'info'; },
    abierta(id) { return !!this.abiertas[id]; },
    alternar(id) { this.abiertas = { ...this.abiertas, [id]: !this.abiertas[id] }; },
    cuenta(s) {
      const p = s.items.filter((x) => x.nivel === 'problema').length;
      const a = s.items.filter((x) => x.nivel === 'aviso').length;
      if (p) return plural(p, 'por corregir', 'por corregir');
      if (a) return plural(a, 'aviso', 'avisos');
      return s.estado === 'bien' ? 'Bien' : '';
    },
    async revisar() {
      if (this.cargando) return;
      this.cargando = true;
      this.error = '';
      this.progreso = 0.05;
      this.mensaje = 'Poniendo el PDF al día';
      try {
        if (this.ed.guardarAhora && this.ed.modelo) await this.ed.guardarAhora();
        if (this.ed.antesDeCompilar) await this.ed.antesDeCompilar();
        const t = await post(`api/proyectos/${this.ed.pid}/revisar`);
        const fin = await esperarTrabajo(t.id, { intervalo: 300, alCambiar: (x) => { this.progreso = x.progreso; if (x.mensaje) this.mensaje = x.mensaje; } });
        if (fin.estado === 'error') { this.error = fin.mensaje || 'No se pudo revisar el documento'; return; }
        this.resultado = fin.resultado;
        // se abren las secciones con algo que mirar
        const abiertas = {};
        for (const s of this.secciones) abiertas[s.id] = ORDEN[s.estado] <= 1;
        this.abiertas = abiertas;
        // la vista previa enseña el PDF que se acaba de revisar
        if (fin.resultado && fin.resultado.version && this.ed.recargarCompilacion) this.ed.recargarCompilacion();
      } catch (e) {
        this.error = e.message || String(e);
      } finally {
        this.cargando = false;
      }
    },
    mostrar(it) {
      this.ed.mostrarEnPoster(it);
      if (window.innerWidth <= 820) this.$emit('cerrar');
    },
    puedeMostrar(it) { return !!(it.zona || (it.elemento && this.ed.indice && this.ed.indice.get(it.elemento))); },
  },
  mounted() {
    this.revisar();
    this.$nextTick(() => { if (this.$refs.titulo) this.$refs.titulo.focus(); });
  },
  template: `
  <aside class="revision" role="complementary" aria-labelledby="tit-revision" @keydown.esc="$emit('cerrar')">
    <header class="cabeza-revision">
      <div class="tira-control" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
      <div class="titulos">
        <h2 id="tit-revision" ref="titulo" tabindex="-1">Revisión para imprimir</h2>
        <p v-if="papel">{{ papel }}</p>
      </div>
      <button class="btn icono fantasma" @click="$emit('cerrar')" aria-label="Cerrar la revisión"><icono n="cerrar"/></button>
    </header>

    <div class="cuerpo-revision">
      <div v-if="cargando" class="estado-revision" role="status">
        <strong>Revisando…</strong>
        <span class="ayuda">{{ mensaje }}</span>
        <div class="barra-progreso"><div :style="{width: Math.round(Math.max(0.06, progreso) * 100) + '%'}"></div></div>
      </div>
      <div v-else-if="error" class="estado-revision con-error" role="alert">
        <strong>No se pudo revisar</strong>
        <span>{{ error }}</span>
        <button class="btn pequeno" @click="revisar"><icono n="compilar"/>Intentarlo otra vez</button>
      </div>
      <template v-else-if="resultado">
        <div class="estado-revision" :class="'general-' + estadoGeneral">
          <span class="sello"><icono :n="icono(estadoGeneral)"/></span>
          <div>
            <strong>{{ titular }}</strong>
            <span>{{ subtitular }}</span>
          </div>
        </div>
        <p v-if="resultado.faltan && resultado.faltan.length" class="ayuda nota-faltan">
          Sin {{ resultado.faltan.join(', ') }} (de Poppler) algunas comprobaciones no se pueden hacer.</p>

        <section v-for="s in secciones" :key="s.id" class="seccion-revision" :class="'estado-' + s.estado">
          <button class="cabeza-seccion" @click="alternar(s.id)" :aria-expanded="abierta(s.id)" :aria-controls="'rev-' + s.id">
            <span class="marca-estado"><icono :n="icono(s.estado)"/></span>
            <span class="nombre-seccion">{{ s.titulo }}</span>
            <span class="cuenta-seccion">{{ cuenta(s) }}</span>
            <span class="flecha" :class="{abierta: abierta(s.id)}"><icono n="chevron"/></span>
          </button>
          <ul v-if="abierta(s.id)" class="items-revision" :id="'rev-' + s.id">
            <li v-for="(it, i) in s.items" :key="i" :class="'nivel-' + it.nivel">
              <span class="marca-nivel"><icono :n="icono(it.nivel)"/></span>
              <div class="texto-item">
                <p class="titulo-item">{{ it.titulo }}</p>
                <p v-if="it.detalle" class="detalle-item">{{ it.detalle }}</p>
                <p v-if="it.muestra" class="muestra-item">«{{ it.muestra }}»</p>
                <div v-if="it.color_antes" class="antes-despues" :aria-label="'En pantalla ' + it.color_antes + ', impreso ' + it.color_despues">
                  <span><i :style="{background: it.color_antes}"></i>Pantalla</span>
                  <span><i :style="{background: it.color_despues}"></i>Tinta</span>
                </div>
                <div v-if="it.color_texto" class="prueba-contraste" :style="{color: it.color_texto, background: it.color_fondo}">
                  Aa <span>{{ String(it.contraste).replace('.', ',') }}:1</span></div>
                <p v-if="it.consejo" class="consejo-item">{{ it.consejo }}</p>
                <div v-if="puedeMostrar(it) || it.accion === 'ajustar'" class="acciones-item">
                  <button v-if="puedeMostrar(it)" class="btn pequeno" @click="mostrar(it)"><icono n="buscar"/>Mostrar en el documento</button>
                  <button v-if="it.accion === 'ajustar' && conPoster" class="btn pequeno" :disabled="!!ed.ajustando" @click="ed.ajustarPagina()"><icono n="encajar"/>Ajustar a una página</button>
                </div>
              </div>
            </li>
          </ul>
        </section>
      </template>
    </div>

    <footer class="pie-revision">
      <button class="btn" @click="revisar" :disabled="cargando"><icono n="compilar"/>Revisar de nuevo</button>
      <span style="flex:1"></span>
      <button class="btn primario" @click="$emit('imprenta')"><icono n="imprenta"/>PDF para imprenta…</button>
    </footer>
  </aside>`,
};

// ---------------------------------------------------------------- PDF para imprenta
const SANGRADOS = [
  { mm: 0, texto: 'Sin sangrado' },
  { mm: 3, texto: '3 mm' },
  { mm: 5, texto: '5 mm' },
];

export const DialogoImprenta = {
  name: 'dialogo-imprenta',
  emits: ['cerrar'],
  setup() { return { ed: inject('ed'), sangrados: SANGRADOS }; },
  data() {
    const previas = (this.ed && this.ed.meta && this.ed.meta.ajustes && this.ed.meta.ajustes.imprenta) || {};
    return {
      sangrado: Number(previas.sangrado_mm ?? 3), marcas: previas.marcas_corte ?? true, cmyk: !!previas.cmyk,
      trabajando: false, progreso: 0, mensaje: '', hecho: null, version: 0,
    };
  },
  computed: {
    esLatex() { return this.ed.meta && this.ed.meta.tipo === 'latex'; },
    hayGs() { return !!(tienda.estado && tienda.estado.ghostscript); },
    sangradoEfectivo() { return this.esLatex ? 0 : this.sangrado; },
    papel() {
      const c = this.ed.compilacion || {};
      if (c.pagina_mm && c.pagina_mm[0]) return { ancho: c.pagina_mm[0], alto: c.pagina_mm[1] };
      const p = c.posiciones && c.posiciones.papel;
      if (p && p.ancho) return { ancho: p.ancho / 72.27 * 25.4, alto: p.alto / 72.27 * 25.4 };
      return { ancho: 841, alto: 1189 };
    },
    final() {
      const extra = 2 * (this.sangradoEfectivo + (this.marcas ? 10 : 0));
      return { ancho: this.papel.ancho + extra, alto: this.papel.alto + extra };
    },
    textoFinal() {
      const f = (x) => numero(Math.round(x));
      const base = `${f(this.papel.ancho)} × ${f(this.papel.alto)} mm`;
      if (!this.sangradoEfectivo && !this.marcas) return `El PDF mide ${base}, como el documento.`;
      const partes = [];
      if (this.sangradoEfectivo) partes.push(`${this.sangradoEfectivo} mm de sangrado`);
      if (this.marcas) partes.push('10 mm para las marcas');
      return `El documento mide ${base}; con ${partes.join(' y ')} por cada lado, el PDF mide ${f(this.final.ancho)} × ${f(this.final.alto)} mm. La imprenta corta por el tamaño del documento.`;
    },
    // esquema (no está a escala: el sangrado se exagera para que se vea)
    esquema() {
      const w = 150, h = Math.round(w * this.papel.alto / this.papel.ancho);
      const s = this.sangradoEfectivo ? (this.sangradoEfectivo >= 5 ? 13 : 9) : 0;
      const m = this.marcas ? 16 : 0;
      const pad = 6;
      const x0 = pad + m + s, y0 = pad + m + s;
      const tw = w + 2 * (s + m) + 2 * pad, th = h + 2 * (s + m) + 2 * pad;
      const marcas = [];
      if (this.marcas) {
        for (const [cx, cy, sx, sy] of [[x0, y0, -1, -1], [x0 + w, y0, 1, -1], [x0, y0 + h, -1, 1], [x0 + w, y0 + h, 1, 1]]) {
          marcas.push({ x1: cx + sx * (s + 3), y1: cy, x2: cx + sx * (s + m), y2: cy });
          marcas.push({ x1: cx, y1: cy + sy * (s + 3), x2: cx, y2: cy + sy * (s + m) });
        }
      }
      return { w, h, s, m, x0, y0, tw, th, marcas, pad };
    },
    fondoPoster() {
      const c = this.ed.modelo && this.ed.modelo.colores && this.ed.modelo.colores.fondo;
      return c ? `#${String(c).replace('#', '')}` : '#FFFFFF';
    },
    miniatura() { return `api/proyectos/${this.ed.pid}/miniatura?v=${this.ed.version || 0}`; },
    miniaturaHecha() { return this.hecho ? `api/proyectos/${this.ed.pid}/imprenta.png?v=${this.version}` : ''; },
  },
  watch: {
    sangrado() { this.hecho = null; },
    marcas() { this.hecho = null; },
    cmyk() { this.hecho = null; },
  },
  methods: {
    tamano,
    async generar() {
      if (this.trabajando) return;
      this.trabajando = true;
      this.progreso = 0.04;
      this.mensaje = 'Preparando…';
      this.hecho = null;
      try {
        if (this.ed.guardarAhora && this.ed.modelo) await this.ed.guardarAhora();
        if (this.ed.antesDeCompilar) await this.ed.antesDeCompilar();
        const t = await post(`api/proyectos/${this.ed.pid}/imprenta`, { sangrado_mm: this.sangradoEfectivo, marcas_corte: this.marcas, cmyk: this.cmyk && this.hayGs });
        const fin = await esperarTrabajo(t.id, { intervalo: 350, alCambiar: (x) => { this.progreso = x.progreso; if (x.mensaje) this.mensaje = x.mensaje; } });
        if (fin.estado === 'error') { avisar(fin.mensaje || 'No se pudo preparar el PDF', { tipo: 'error', ms: 9000 }); return; }
        if (fin.estado !== 'terminado' || !fin.resultado) return;
        this.hecho = fin.resultado;
        this.version = Date.now();
        if (this.ed.meta) this.ed.meta.ajustes = { ...(this.ed.meta.ajustes || {}), imprenta: { sangrado_mm: this.sangrado, marcas_corte: this.marcas, cmyk: this.cmyk } };
        for (const n of fin.resultado.notas || []) avisar(n, { ms: 8000 });
        descargar(`${fin.resultado.url}?descargar=1`);
      } catch (e) {
        avisarError(e);
      } finally {
        this.trabajando = false;
      }
    },
    descargarOtraVez() { if (this.hecho) descargar(`${this.hecho.url}?descargar=1`); },
  },
  template: `
  <div class="fondo-dialogo" @mousedown.self="!trabajando && $emit('cerrar')" @keydown.esc="!trabajando && $emit('cerrar')">
    <div class="dialogo medio dialogo-imprenta" role="dialog" aria-modal="true" aria-labelledby="tit-imprenta">
      <header><div style="flex:1"><h2 id="tit-imprenta">PDF para imprenta</h2>
        <p>Con sangrado y marcas de corte si la imprenta los pide. Si no sabes qué pedir, pregunta: lo más común es 3 mm de sangrado.</p></div>
        <button class="btn icono fantasma" @click="$emit('cerrar')" :disabled="trabajando" aria-label="Cerrar"><icono n="cerrar"/></button></header>
      <div class="cuerpo cuerpo-imprenta">
        <div class="opciones-imprenta">
          <div class="campo">
            <span class="etiqueta">Sangrado</span>
            <div class="segmentos sin-cortes" role="radiogroup" aria-label="Sangrado">
              <button v-for="o in sangrados" :key="o.mm" type="button" role="radio" :aria-checked="sangrado === o.mm"
                      :class="{activo: sangradoEfectivo === o.mm}" :disabled="esLatex && o.mm > 0" @click="sangrado = o.mm">{{ o.texto }}</button>
            </div>
            <span class="ayuda" v-if="esLatex">En los proyectos de código el sangrado no se añade solo: haz el fondo 3 mm más grande en tu .tex si lo necesitas.</span>
            <span class="ayuda" v-else>El fondo y lo que llega al borde se alargan por fuera; al cortar no quedan filos blancos.</span>
          </div>
          <label class="interruptor"><span class="texto">Marcas de corte</span>
            <input type="checkbox" v-model="marcas"><span class="pista"></span></label>
          <span class="ayuda" style="margin-top:-8px">Líneas finas en las esquinas que marcan por dónde cortar.</span>
          <div class="campo">
            <span class="etiqueta">Color</span>
            <div class="segmentos sin-cortes" role="radiogroup" aria-label="Color">
              <button type="button" role="radio" :aria-checked="!cmyk" :class="{activo: !cmyk}" @click="cmyk = false">RGB, como en pantalla</button>
              <button type="button" role="radio" :aria-checked="cmyk" :class="{activo: cmyk && hayGs}" :disabled="!hayGs" @click="cmyk = true">CMYK</button>
            </div>
            <span class="ayuda" v-if="!hayGs">Para CMYK hace falta Ghostscript (gs) en el ordenador donde corre DocsLab.</span>
            <span class="ayuda" v-else-if="cmyk">Colores de tinta con un perfil genérico. Úsalo solo si la imprenta lo pide; si te da su perfil ICC, mejor envía RGB y que conviertan ellos.</span>
            <span class="ayuda" v-else>Lo que piden casi todas las imprentas digitales y de gran formato.</span>
          </div>
          <p class="medidas-imprenta">{{ textoFinal }}</p>
        </div>
        <figure class="esquema-imprenta">
          <img v-if="hecho" :src="miniaturaHecha" alt="Primera página del PDF para imprenta" class="resultado-imprenta">
          <svg v-else :viewBox="'0 0 ' + esquema.tw + ' ' + esquema.th" :width="esquema.tw" :height="esquema.th" role="img"
               aria-label="Esquema del papel: el documento, el sangrado alrededor y las marcas de corte">
            <defs>
              <pattern id="rayado-sangrado" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width="5" height="5" :fill="fondoPoster"/><line x1="0" y1="0" x2="0" y2="5" stroke="rgba(30,36,33,.28)" stroke-width="1.6"/>
              </pattern>
            </defs>
            <rect x="0.5" y="0.5" :width="esquema.tw - 1" :height="esquema.th - 1" class="papel-esquema"/>
            <rect v-if="esquema.s" :x="esquema.x0 - esquema.s" :y="esquema.y0 - esquema.s" :width="esquema.w + 2 * esquema.s" :height="esquema.h + 2 * esquema.s" fill="url(#rayado-sangrado)"/>
            <rect :x="esquema.x0" :y="esquema.y0" :width="esquema.w" :height="esquema.h" :fill="fondoPoster"/>
            <image :href="miniatura" :x="esquema.x0" :y="esquema.y0" :width="esquema.w" :height="esquema.h" preserveAspectRatio="none"/>
            <rect :x="esquema.x0" :y="esquema.y0" :width="esquema.w" :height="esquema.h" class="corte-esquema"/>
            <line v-for="(l, i) in esquema.marcas" :key="i" :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2" class="marca-esquema"/>
          </svg>
          <figcaption class="ayuda">
            <template v-if="hecho">Así ha quedado: {{ tamano(hecho.bytes) }}<template v-if="hecho.cmyk">, en CMYK</template>.</template>
            <template v-else>Esquema, no a escala: la línea discontinua es por donde se corta<template v-if="sangradoEfectivo">; lo rayado es el sangrado</template>.</template>
          </figcaption>
        </figure>
      </div>
      <footer>
        <div class="izq progreso-imprenta" v-if="trabajando" role="status">
          <span class="ayuda">{{ mensaje }}</span>
          <div class="barra-progreso"><div :style="{width: Math.round(Math.max(0.06, progreso) * 100) + '%'}"></div></div>
        </div>
        <button v-else-if="hecho" class="btn izq fantasma" @click="descargarOtraVez"><icono n="descargar"/>Descargar otra vez</button>
        <button class="btn" @click="$emit('cerrar')" :disabled="trabajando">Cerrar</button>
        <button class="btn primario" @click="generar" :disabled="trabajando"><icono n="imprenta"/>{{ trabajando ? 'Preparando…' : 'Preparar y descargar' }}</button>
      </footer>
    </div>
  </div>`,
};
