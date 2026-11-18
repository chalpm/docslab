// SPDX-License-Identifier: AGPL-3.0-only
// Edición directa sobre la vista previa: dónde cae una caja o un elemento que
// se arrastra, tiradores para cambiar el ancho de las columnas y el cuadro para
// escribir un texto con doble clic.
import { CTexto, CParrafo } from './campos.js';
import { variante, nombreNodo } from './modeloed.js';

const { inject } = Vue;

const HUECO_MIN = 4;          // pt

export const EdicionDirecta = {
  name: 'edicion-directa',
  components: { CTexto, CParrafo },
  props: { k: Number, pagina: Number },
  setup() { return { ed: inject('ed') }; },
  data: () => ({ ajuste: null }),
  computed: {
    cajas() { const p = this.ed.compilacion && this.ed.compilacion.posiciones; return (p && p.cajas) || {}; },
    // ---------------------------------------------------------- arrastrar cajas y elementos
    objetivo() {
      const a = this.ed.arrastre;
      if (!a) return null;
      const info = this.ed.indice.get(a.id);
      if (!info) return null;
      return info.tipo === 'bloque' ? this.objetivoCaja(info, a) : info.tipo === 'elemento' ? this.objetivoElemento(info, a) : null;
    },
    // ---------------------------------------------------------- ancho de las columnas
    fila() {
      const info = this.ed.indice.get(this.ed.sel);
      if (!info) return null;
      const f = info.tipo === 'fila' ? info.obj : info.fila;
      if (!f || f.visible === false || (f.columnas || []).length < 2) return null;
      const r = this.rect(f.id);
      const cols = f.columnas.map((c) => this.rect(c.id));
      if (!r || cols.some((c) => !c)) return null;
      return { f, r, cols };
    },
    tiradores() {
      const d = this.fila;
      if (!d) return [];
      return d.cols.slice(0, -1).map((c, i) => ({ i, x: (c.x1 + d.cols[i + 1].x0) / 2, y0: d.r.y0, y1: d.r.y1 }));
    },
    // ---------------------------------------------------------- escribir con doble clic
    editando() {
      const id = this.ed.editandoId;
      const info = id && this.ed.indice.get(id);
      if (!info) return null;
      const r = this.rect(id);
      if (!r) return null;
      return { info, r, campos: this.camposTexto(info), nombre: nombreNodo(info) };
    },
    estiloEditor() {
      const e = this.editando;
      if (!e) return {};
      const ancho = Math.max(300, Math.min(520, (e.r.x1 - e.r.x0) * this.k));
      const hojaAlto = this.$el && this.$el.parentElement ? this.$el.parentElement.clientHeight : 99999;
      const abajo = e.r.y1 * this.k + 8;
      const arriba = e.r.y0 * this.k - 8;
      const cabeAbajo = abajo + 260 < hojaAlto || arriba < 260;
      return { left: `${Math.max(0, e.r.x0 * this.k)}px`, width: `${ancho}px`,
        ...(cabeAbajo ? { top: `${abajo}px` } : { top: `${arriba}px`, transform: 'translateY(-100%)' }) };
    },
  },
  watch: {
    'ed.editandoId'(id) { if (id) this.$nextTick(() => { const el = this.$el.querySelector('.editor-en-vista .entrada'); if (el) { el.focus(); if (el.select) el.select(); } }); },
  },
  methods: {
    rect(id) {
      const c = this.cajas[id];
      return c && (c.pagina || 1) === this.pagina ? c : null;
    },
    // dónde caería una caja: delante o detrás de otra caja, o dentro de una columna vacía
    objetivoCaja(info, a) {
      // la columna bajo el puntero (o la más cercana por arriba o por abajo)
      let col = null, rc = null, mejor = Infinity;
      for (const f of this.ed.modelo.filas) {
        if (f.visible === false) continue;
        for (const c of f.columnas) {
          const r = this.rect(c.id);
          if (!r || a.x < r.x0 || a.x > r.x1) continue;
          const d = a.y < r.y0 ? r.y0 - a.y : a.y > r.y1 ? a.y - r.y1 : 0;
          if (d < mejor && d < 160) { mejor = d; col = c; rc = r; }
        }
      }
      if (!col) return null;
      const lista = col.bloques.filter((b) => b.id !== info.obj.id && !b.libre && this.rect(b.id));
      const sig = lista.find((b) => { const r = this.rect(b.id); return a.y < (r.y0 + r.y1) / 2; });
      let destino, pos, y;
      if (sig) { destino = sig.id; pos = 'antes'; y = this.rect(sig.id).y0 - HUECO_MIN; }
      else if (lista.length) { const ult = lista[lista.length - 1]; destino = ult.id; pos = 'despues'; y = this.rect(ult.id).y1 + HUECO_MIN; }
      else { destino = col.id; pos = 'dentro'; y = rc.y0 + 10; }
      // soltarla donde ya está no hace nada
      const i = info.lista.indexOf(info.obj);
      if (info.columna === col && ((pos === 'antes' && info.lista[i + 1] && info.lista[i + 1].id === destino) ||
          (pos === 'despues' && info.lista[i - 1] && info.lista[i - 1].id === destino))) return null;
      return { destino, pos, x0: rc.x0, x1: rc.x1, y, texto: `a ${nombreNodo(this.ed.indice.get(col.id)).toLowerCase()}` };
    },
    // dónde caería un elemento: dentro de la caja que está bajo el puntero
    objetivoElemento(info, a) {
      let caja = null, rb = null, area = Infinity;
      for (const f of this.ed.modelo.filas) {
        if (f.visible === false) continue;
        for (const c of f.columnas) {
          for (const b of c.bloques) {
            const r = this.rect(b.id);
            if (r && a.x >= r.x0 && a.x <= r.x1 && a.y >= r.y0 && a.y <= r.y1) {
              const ar = (r.x1 - r.x0) * (r.y1 - r.y0);
              if (ar < area) { caja = b; rb = r; area = ar; }
            }
          }
        }
      }
      if (!caja) return null;
      const lista = caja.elementos.filter((e) => e.id !== info.obj.id && this.rect(e.id));
      const sig = lista.find((e) => { const r = this.rect(e.id); return a.y < (r.y0 + r.y1) / 2; });
      let destino, pos, y, x0 = rb.x0 + 6, x1 = rb.x1 - 6;
      if (sig) { const r = this.rect(sig.id); destino = sig.id; pos = 'antes'; y = r.y0 - 1; x0 = r.x0; x1 = r.x1; }
      else if (lista.length) { const r = this.rect(lista[lista.length - 1].id); destino = lista[lista.length - 1].id; pos = 'despues'; y = r.y1 + 1; x0 = r.x0; x1 = r.x1; }
      else { destino = caja.id; pos = 'dentro'; y = rb.y1 - 8; }
      const i = info.lista.indexOf(info.obj);
      if (info.bloque === caja && ((pos === 'antes' && info.lista[i + 1] && info.lista[i + 1].id === destino) ||
          (pos === 'despues' && info.lista[i - 1] && info.lista[i - 1].id === destino))) return null;
      return { destino, pos, x0, x1, y, texto: `a «${nombreNodo(this.ed.indice.get(caja.id))}»` };
    },
    soltar() {
      const o = this.objetivo, a = this.ed.arrastre;
      this.ed.arrastre = null;
      if (o && a) this.ed.moverNodo(a.id, o.destino, o.pos);
    },
    estiloLinea(o) {
      return { left: `${o.x0 * this.k}px`, top: `${o.y * this.k - 1.5}px`, width: `${(o.x1 - o.x0) * this.k}px` };
    },
    // ---------------------------------------------------------- columnas
    rejilla(f) {
      const r = Number(f.rejilla) || 0;
      return r > 0 ? r : f.columnas.reduce((s, c) => s + Math.max(1, Number(c.abarca) || 1), 0);
    },
    tomarBorde(ev, t) {
      if (ev.button !== 0) return;
      ev.preventDefault();
      ev.stopPropagation();
      const d = this.fila;
      const R = this.rejilla(d.f);
      const G = R * Math.ceil(12 / R);                // al menos 12 pasos, sin mover los otros bordes
      const factor = G / R;
      const inicios = [0];
      for (const c of d.f.columnas) inicios.push(inicios[inicios.length - 1] + Math.max(1, Number(c.abarca) || 1) * factor);
      const hueco = Math.max(0, d.cols[1].x0 - d.cols[0].x1);
      const paso = (d.r.x1 - d.r.x0 + hueco) / G;
      this.ajuste = { i: t.i, G, inicios, hueco, paso, r: d.r, u: inicios[t.i + 1], f: d.f };
      ev.currentTarget.setPointerCapture && ev.currentTarget.setPointerCapture(ev.pointerId);
    },
    moverBorde(ev) {
      const a = this.ajuste;
      if (!a) return;
      const caja = this.$el.getBoundingClientRect();
      const x = (ev.clientX - caja.left) / this.k;
      const u = Math.round((x - a.r.x0 + a.hueco / 2) / a.paso);
      a.u = Math.min(a.inicios[a.i + 2] - 1, Math.max(a.inicios[a.i] + 1, u));
    },
    soltarBorde() {
      const a = this.ajuste;
      this.ajuste = null;
      if (!a || a.u === a.inicios[a.i + 1]) return;
      const inicios = [...a.inicios];
      inicios[a.i + 1] = a.u;
      a.f.rejilla = a.G;
      a.f.columnas.forEach((c, j) => { c.abarca = inicios[j + 1] - inicios[j]; });
    },
    estiloGuia() {
      const a = this.ajuste;
      const x = a.r.x0 + a.u * a.paso - a.hueco / 2;
      return { left: `${x * this.k - 1}px`, top: `${a.r.y0 * this.k}px`, height: `${(a.r.y1 - a.r.y0) * this.k}px` };
    },
    textoGuia() {
      const a = this.ajuste;
      const izq = a.u - a.inicios[a.i], der = a.inicios[a.i + 2] - a.u;
      const pct = (n) => Math.round((n / a.G) * 100);
      return `${pct(izq)} % · ${pct(der)} %`;
    },
    // ---------------------------------------------------------- textos
    camposTexto(info) {
      const o = info.obj;
      switch (info.tipo) {
        case 'cabecera': return [['titulo', 'Título', 'texto'], ['subtitulo', 'Subtítulo', 'texto'], ['autores', 'Autores', 'texto'], ['afiliaciones', 'Afiliaciones', 'texto']].map(([c, e, t]) => ({ obj: o, clave: c, etiqueta: e, tipo: t }));
        case 'pie': return [['izquierda', 'Izquierda'], ['centro', 'Centro'], ['derecha', 'Derecha']].map(([c, e]) => ({ obj: o, clave: c, etiqueta: e, tipo: 'texto' }));
        case 'bloque': {
          // una caja suelta con un solo elemento (un texto suelto): se escribe su texto
          if (o.libre && o.elementos.length === 1 && o.mostrar_titulo === false) return this.camposTexto({ tipo: 'elemento', obj: o.elementos[0] });
          return [{ obj: o, clave: 'titulo', etiqueta: this.ed.flujo ? 'Título de la sección' : 'Título de la caja', tipo: 'texto' }];
        }
        case 'item': return o.tipo === 'texto' ? [{ obj: o, clave: 'texto', etiqueta: 'Texto', tipo: 'parrafo' }] : [];
        case 'elemento': {
          const v = variante(o);
          const campos = (v ? v.campos : []).filter((c) => c.tipo === 'texto' || c.tipo === 'parrafo');
          return campos.slice(0, 4).map((c) => ({ obj: o, clave: c.nombre, etiqueta: c.etiqueta, tipo: c.tipo }));
        }
        default: return [];
      }
    },
    cerrarEditor() { this.ed.editandoId = null; },
    teclaEditor(ev) {
      if (ev.key === 'Escape' || (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey))) { ev.preventDefault(); this.cerrarEditor(); }
    },
    fuera(ev) {
      if (this.ed.editandoId && this.$refs.editor && !this.$refs.editor.contains(ev.target) && !ev.target.closest('.menu-contenedor')) this.cerrarEditor();
    },
  },
  created() { this.ed.soltarEnVista = () => this.soltar(); },
  mounted() { document.addEventListener('pointerdown', this.fuera, true); },
  beforeUnmount() { document.removeEventListener('pointerdown', this.fuera, true); },
  template: `
    <div class="edicion-directa" @pointermove="moverBorde" @pointerup="soltarBorde" @pointercancel="ajuste = null">
      <template v-if="objetivo">
        <div class="linea-soltar" :style="estiloLinea(objetivo)"><span>{{ objetivo.texto }}</span></div>
      </template>
      <div v-for="t in tiradores" :key="t.i" class="tirador-columna" :class="{activo: ajuste && ajuste.i === t.i}"
           :style="{left: (t.x * k - 6) + 'px', top: (t.y0 * k) + 'px', height: ((t.y1 - t.y0) * k) + 'px'}"
           title="Arrastra para cambiar el ancho de las columnas" @pointerdown="tomarBorde($event, t)"><i></i></div>
      <div v-if="ajuste" class="guia-columna" :style="estiloGuia()"><span>{{ textoGuia() }}</span></div>
      <div v-if="editando && editando.campos.length" ref="editor" class="editor-en-vista" :style="estiloEditor" @keydown="teclaEditor" @pointerdown.stop @dblclick.stop>
        <header><strong>{{ editando.nombre }}</strong>
          <button type="button" class="btn icono pequeno fantasma" @click="cerrarEditor" aria-label="Cerrar"><icono n="cerrar"/></button></header>
        <template v-for="c in editando.campos" :key="c.clave">
          <c-parrafo v-if="c.tipo === 'parrafo'" :obj="c.obj" :clave="c.clave" :etiqueta="c.etiqueta" :filas="4"/>
          <c-texto v-else :obj="c.obj" :clave="c.clave" :etiqueta="c.etiqueta" formato/>
        </template>
        <span class="ayuda">Se guarda solo. Esc o Ctrl + Intro para cerrar.</span>
      </div>
    </div>`,
};
