// SPDX-License-Identifier: AGPL-3.0-only
// Árbol de estructura: capas, cabecera, filas, columnas, cajas y elementos.
// Se pinta como una lista plana (más fácil de arrastrar y recorrer con el teclado).
import { nombreNodo, detalleNodo, iconoNodo, tieneTitulo } from './modeloed.js';

const { inject } = Vue;

const CONTIENE = { pagina: 'fila', fila: 'columna', columna: 'bloque', bloque: 'elemento', capa: 'item' };
const ARRASTRABLES = new Set(['pagina', 'fila', 'columna', 'bloque', 'elemento', 'item']);

export const Arbol = {
  name: 'arbol-estructura',
  setup() { return { ed: inject('ed') }; },
  data: () => ({ arrastre: null, destino: null, menuCapa: null }),
  computed: {
    filas() {
      const ed = this.ed, m = ed.modelo, idx = ed.indice, ab = ed.abiertos;
      const flujo = ed.flujo, diapos = m.clase === 'presentacion';
      const out = [];
      const nodo = (id, nivel, extra = {}) => {
        const info = idx.get(id);
        if (!info) return;
        const o = info.obj;
        let hijos = 0;
        if (info.tipo === 'fila') hijos = o.columnas.length;
        else if (info.tipo === 'columna') hijos = o.bloques.length;
        else if (info.tipo === 'bloque') hijos = o.elementos.length;
        else if (info.tipo === 'capa') hijos = o.elementos.length;
        else if (info.tipo === 'pagina') hijos = m.filas.filter((f) => f.pag === o.id).length;
        const visible = ['columna', 'poster', 'documento'].includes(info.tipo) ? true : o.visible !== false;
        out.push({
          id, tipo: info.tipo, nivel, nombre: nombreNodo(info), detalle: detalleNodo(info), icono: iconoNodo(info),
          hijos, abierto: ab.has(id), visible, info,
          titulo: info.tipo === 'bloque' || (info.tipo === 'elemento' && tieneTitulo(o)) ? o.mostrar_titulo !== false : null,
          suelta: info.tipo === 'bloque' && !!o.libre && !flujo,
          ...extra,
        });
      };
      nodo('poster', 0);
      const capas = [...m.capas].sort((a, b) => Number(b.z) - Number(a.z));
      const pintarCapas = (lista) => lista.forEach((capa) => {
        nodo(capa.id, 0, { z: Number(capa.z) });
        if (ab.has(capa.id)) [...capa.elementos].reverse().forEach((it) => nodo(it.id, 1));
      });
      out.push({ id: 'g-delante', tipo: 'grupo', nombre: 'Delante del contenido', delante: true });
      pintarCapas(capas.filter((c) => Number(c.z) >= 0));
      out.push({ id: 'g-contenido', tipo: 'grupo', nombre: 'Contenido', contenido: true });
      nodo('cabecera', 0);
      const pintarFila = (f, n0) => {
        nodo(f.id, n0);
        if (!ab.has(f.id)) return;
        f.columnas.forEach((c) => {
          nodo(c.id, n0 + 1);
          if (!ab.has(c.id)) return;
          c.bloques.forEach((b) => {
            nodo(b.id, n0 + 2);
            if (!ab.has(b.id)) return;
            b.elementos.forEach((e) => nodo(e.id, n0 + 3));
          });
        });
      };
      if (flujo) {
        // documentos: las secciones seguidas, con sangría según su nivel
        nodo('documento', 0);
        m.filas.forEach((f) => f.columnas.forEach((c) => c.bloques.forEach((b) => {
          const nv = Math.max(0, Math.min(3, (Number(b.nivel) || 1) - 1));
          nodo(b.id, nv, { seccion: true });
          if (ab.has(b.id)) b.elementos.forEach((e) => nodo(e.id, nv + 1));
        })));
      } else if (diapos) {
        m.paginas.forEach((pg) => {
          nodo(pg.id, 0);
          if (ab.has(pg.id)) m.filas.filter((f) => f.pag === pg.id).forEach((f) => pintarFila(f, 1));
        });
      } else {
        m.filas.forEach((f) => pintarFila(f, 0));
        nodo('pie', 0);
      }
      out.push({ id: 'g-detras', tipo: 'grupo', nombre: 'Detrás del contenido', delante: false });
      pintarCapas(capas.filter((c) => Number(c.z) < 0));
      return out;
    },
  },
  methods: {
    clic(f) { if (f.tipo !== 'grupo') this.ed.seleccionar(f.id, { desdeArbol: true }); },
    alternar(f) { this.ed.alternarAbierto(f.id); },
    // ---- teclado
    tecla(ev, f) {
      const visibles = this.filas.filter((x) => x.tipo !== 'grupo');
      const i = visibles.findIndex((x) => x.id === f.id);
      const enfocar = (x) => { if (!x) return; this.ed.seleccionar(x.id, { desdeArbol: true }); this.$nextTick(() => { const el = this.$el.querySelector(`[data-id="${x.id}"]`); if (el) el.focus(); }); };
      if (ev.key === 'ArrowDown' && !ev.altKey) { ev.preventDefault(); enfocar(visibles[i + 1]); }
      else if (ev.key === 'ArrowUp' && !ev.altKey) { ev.preventDefault(); enfocar(visibles[i - 1]); }
      else if (ev.key === 'ArrowRight' && f.hijos && !f.abierto) { ev.preventDefault(); this.ed.alternarAbierto(f.id); }
      else if (ev.key === 'ArrowLeft' && f.hijos && f.abierto) { ev.preventDefault(); this.ed.alternarAbierto(f.id); }
      else if ((ev.key === 'ArrowUp' || ev.key === 'ArrowDown') && ev.altKey) { ev.preventDefault(); this.ed.desplazar(f.id, ev.key === 'ArrowUp' ? -1 : 1); }
      else if (ev.key === 'Delete' && ARRASTRABLES.has(f.tipo)) { ev.preventDefault(); this.ed.eliminar(f.id); }
      else if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); this.clic(f); }
    },
    // ---- arrastrar y soltar
    empezar(ev, f) {
      if (!ARRASTRABLES.has(f.tipo)) { ev.preventDefault(); return; }
      this.arrastre = { id: f.id, tipo: f.tipo };
      ev.dataTransfer.effectAllowed = 'move';
      ev.dataTransfer.setData('text/plain', f.id);
    },
    posicion(ev, f) {
      const a = this.arrastre;
      if (!a || f.tipo === 'grupo' || f.id === a.id) return null;
      const r = ev.currentTarget.getBoundingClientRect();
      const y = (ev.clientY - r.top) / r.height;
      const mismo = f.tipo === a.tipo;
      const dentro = CONTIENE[f.tipo] === a.tipo;
      if (mismo && dentro) return y < 0.3 ? 'antes' : y > 0.7 ? 'despues' : 'dentro';
      if (mismo) return y < 0.5 ? 'antes' : 'despues';
      if (dentro) return 'dentro';
      return null;
    },
    sobre(ev, f) {
      const pos = this.posicion(ev, f);
      if (!pos) { this.destino = null; return; }
      ev.preventDefault();
      ev.dataTransfer.dropEffect = 'move';
      this.destino = { id: f.id, pos };
    },
    soltar(ev, f) {
      const pos = this.posicion(ev, f);
      if (pos && this.arrastre) {
        ev.preventDefault();
        this.ed.moverNodo(this.arrastre.id, f.id, pos);
      }
      this.terminar();
    },
    terminar() { this.arrastre = null; this.destino = null; },
    claseDestino(f) {
      if (!this.destino || this.destino.id !== f.id) return '';
      return { antes: 'soltar-antes', despues: 'soltar-despues', dentro: 'soltar-dentro' }[this.destino.pos];
    },
    puedeAgregar(f) { return ['pagina', 'fila', 'columna', 'bloque', 'capa'].includes(f.tipo); },
    textoAgregar(f) {
      return { pagina: 'Añadir una fila a la diapositiva', fila: 'Añadir una columna', columna: 'Añadir una caja', bloque: 'Añadir un elemento', capa: 'Añadir un elemento a la capa' }[f.tipo];
    },
    nuevoContenido() {
      const ed = this.ed;
      if (ed.flujo) ed.agregarSeccion(1); else if (ed.clase === 'presentacion') ed.agregarPagina('contenido'); else ed.agregarFila();
    },
    textoNuevo() { return this.ed.flujo ? 'Nueva sección' : this.ed.clase === 'presentacion' ? 'Nueva diapositiva' : 'Nueva fila'; },
    puedeQuitar(f) {
      if (f.tipo === 'capa') return !['fondo', 'frente'].includes(f.id);
      return ARRASTRABLES.has(f.tipo);
    },
    agregar(f, ev) {
      if (f.tipo === 'capa') { this.menuCapa = this.menuCapa === f.id ? null : f.id; ev.stopPropagation(); return; }
      this.ed.agregarHijo(f.id);
    },
    agregarItem(capa, tipo) { this.menuCapa = null; this.ed.agregarItem(capa, tipo); },
    cerrarMenu(ev) { if (!ev.target.closest('.menu-contenedor')) this.menuCapa = null; },
  },
  watch: {
    'ed.sel'(id) {
      if (!id) return;
      this.$nextTick(() => {
        const el = this.$el && this.$el.querySelector(`[data-id="${CSS.escape(id)}"]`);
        if (el) el.scrollIntoView({ block: 'nearest' });
      });
    },
  },
  mounted() { document.addEventListener('mousedown', this.cerrarMenu); },
  beforeUnmount() { document.removeEventListener('mousedown', this.cerrarMenu); },
  template: `
  <div class="arbol" role="tree" aria-label="Estructura del documento">
    <template v-for="f in filas" :key="f.id">
      <div v-if="f.tipo === 'grupo'" class="grupo-arbol">
        <span>{{ f.nombre }}</span><span class="linea"></span>
        <button v-if="!f.contenido" class="btn icono pequeno fantasma" :title="f.delante ? 'Nueva capa delante del contenido' : 'Nueva capa detrás del contenido'"
                :aria-label="f.delante ? 'Nueva capa delante' : 'Nueva capa detrás'" @click="ed.agregarCapa(f.delante)"><icono n="mas"/></button>
        <button v-else class="btn icono pequeno fantasma" :title="textoNuevo()" :aria-label="textoNuevo()" @click="nuevoContenido()"><icono n="mas"/></button>
      </div>
      <div v-else class="fila-nodo" role="treeitem" :data-id="f.id"
           :aria-selected="ed.sel === f.id" :aria-expanded="f.hijos ? f.abierto : undefined" :aria-level="f.nivel + 1"
           :tabindex="ed.sel === f.id || (!ed.sel && f.id === 'poster') ? 0 : -1"
           :class="[{seleccionado: ed.sel === f.id, atenuado: !f.visible, 'capa-nodo': f.tipo === 'capa', 'pagina-nodo': f.tipo === 'pagina', arrastrando: arrastre && arrastre.id === f.id}, claseDestino(f)]"
           :style="{paddingLeft: (6 + f.nivel * 16) + 'px'}"
           :draggable="!['poster', 'capa', 'cabecera', 'pie', 'documento'].includes(f.tipo)"
           @click="clic(f)" @keydown="tecla($event, f)"
           @dragstart="empezar($event, f)" @dragover="sobre($event, f)" @dragleave="destino = destino && destino.id === f.id ? null : destino"
           @drop="soltar($event, f)" @dragend="terminar">
        <button v-if="f.hijos" class="flecha" :class="{abierta: f.abierto}" @click.stop="alternar(f)" :aria-label="f.abierto ? 'Plegar' : 'Desplegar'" tabindex="-1"><icono n="chevron"/></button>
        <span v-else class="flecha" aria-hidden="true"></span>
        <span class="tipo"><icono :n="f.icono"/></span>
        <span class="nombre-nodo">{{ f.nombre }}</span>
        <span v-if="f.tipo === 'capa'" class="insignia-z" :title="'Orden de la capa (z): ' + f.z">{{ f.z }}</span>
        <span v-else-if="f.suelta" class="insignia-libre" title="Caja suelta: se coloca arrastrándola en la vista previa">suelta</span>
        <span v-else-if="f.detalle" class="detalle-nodo">{{ f.detalle }}</span>
        <span class="acciones-nodo" @click.stop>
          <span v-if="f.tipo === 'capa'" class="menu-contenedor">
            <button class="solo-hover" :title="textoAgregar(f)" :aria-label="textoAgregar(f)" @click="agregar(f, $event)"><icono n="mas"/></button>
            <div class="menu" v-if="menuCapa === f.id" style="min-width:180px">
              <button @click="agregarItem(f.id, 'texto')"><icono n="texto"/>Texto</button>
              <button @click="agregarItem(f.id, 'imagen')"><icono n="imagen"/>Imagen</button>
              <button @click="agregarItem(f.id, 'forma')"><icono n="forma"/>Forma o flecha</button>
              <button @click="agregarItem(f.id, 'latex')"><icono n="codigo"/>Código LaTeX</button>
            </div>
          </span>
          <button v-else-if="puedeAgregar(f)" class="solo-hover" :title="textoAgregar(f)" :aria-label="textoAgregar(f)" @click="agregar(f, $event)"><icono n="mas"/></button>
          <button v-if="puedeQuitar(f)" class="solo-hover" title="Duplicar" aria-label="Duplicar" @click="ed.duplicar(f.id)" v-show="f.tipo !== 'capa'"><icono n="duplicar"/></button>
          <button v-if="puedeQuitar(f)" class="solo-hover" title="Borrar (Supr)" aria-label="Borrar" @click="ed.eliminar(f.id)"><icono n="basura"/></button>
          <button v-if="f.titulo !== null" :class="f.titulo ? 'tit-on' : 'apagado'" :title="f.titulo ? 'Ocultar el título' : 'Mostrar el título'"
                  :aria-label="f.titulo ? 'Ocultar el título' : 'Mostrar el título'" :aria-pressed="f.titulo" @click="ed.alternarTitulo(f.id)"><icono :n="f.titulo ? 'titulo' : 'titulo-no'"/></button>
          <button v-if="!['poster', 'columna', 'documento'].includes(f.tipo)" :class="{apagado: !f.visible}" :title="f.visible ? 'Ocultar' : 'Mostrar'"
                  :aria-label="f.visible ? 'Ocultar' : 'Mostrar'" :aria-pressed="!f.visible" @click="ed.alternarVisible(f.id)"><icono :n="f.visible ? 'ojo' : 'ojo-no'"/></button>
        </span>
      </div>
    </template>
  </div>`,
};
