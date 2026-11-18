// Panel de imágenes del proyecto: subir, ver, usar y borrar.
import { api, subir, borrar } from './api.js';
import { avisar, avisarError, confirmar } from './tienda.js';
import { tamano, fecha } from './util.js';

const { inject } = Vue;

export const PanelRecursos = {
  name: 'panel-recursos',
  setup() { return { ed: inject('ed') }; },
  data: () => ({ recursos: null, filtro: 'todas', buscar: '', subiendo: 0, encima: false }),
  computed: {
    lista() {
      const q = this.buscar.trim().toLowerCase();
      return (this.recursos || []).filter((r) =>
        (this.filtro === 'todas' || (this.filtro === 'cuadernos' ? r.origen === 'cuaderno' : r.origen !== 'cuaderno')) &&
        (!q || r.ruta.toLowerCase().includes(q)));
    },
    cuentaCuadernos() { return (this.recursos || []).filter((r) => r.origen === 'cuaderno').length; },
  },
  watch: { 'ed.versionRecursos'() { this.cargar(); } },
  methods: {
    tamano, fecha,
    vista(r) { return `api/proyectos/${this.ed.pid}/vista?ruta=${encodeURIComponent(r.ruta)}&v=${encodeURIComponent(r.fecha)}`; },
    async cargar() {
      try { this.recursos = await api(`api/proyectos/${this.ed.pid}/recursos`); } catch (e) { avisarError(e); }
    },
    async subirArchivos(archivos) {
      if (!archivos || !archivos.length) return;
      this.subiendo = 0.01;
      try {
        const r = await subir(`api/proyectos/${this.ed.pid}/recursos`, { archivos: [...archivos] }, { alProgreso: (p) => { this.subiendo = Math.max(0.01, p); } });
        (r.errores || []).forEach((m) => avisar(m, { tipo: 'error', ms: 8000 }));
        if (r.guardados.length) avisar(r.guardados.length === 1 ? 'Imagen subida' : `${r.guardados.length} imágenes subidas`);
        await this.cargar();
      } catch (e) { avisarError(e); } finally { this.subiendo = 0; }
    },
    soltar(ev) { this.encima = false; this.subirArchivos(ev.dataTransfer.files); },
    usar(r) { this.ed.usarImagen(r.ruta); },
    async quitar(r) {
      const ok = await confirmar({
        titulo: `¿Borrar ${r.nombre}?`,
        texto: r.usado ? 'El documento usa esta imagen: en su lugar aparecerá un recuadro gris.' : 'Se borra el archivo del proyecto.',
        aceptar: 'Borrar', peligro: true,
      });
      if (!ok) return;
      try {
        await borrar(`api/proyectos/${this.ed.pid}/recursos?ruta=${encodeURIComponent(r.ruta)}`);
        await this.cargar();
        if (r.usado) this.ed.compilarPronto();
      } catch (e) { avisarError(e); }
    },
    arrastrar(ev, r) { ev.dataTransfer.setData('application/x-docslab-recurso', r.ruta); ev.dataTransfer.setData('text/plain', r.ruta); },
  },
  mounted() { this.cargar(); },
  template: `
  <div style="display:flex;flex-direction:column;min-height:100%" @dragover.prevent="encima = true" @dragleave.self="encima = false" @drop.prevent="soltar">
    <div style="padding:10px 10px 0;display:grid;gap:8px">
      <div style="display:flex;gap:6px">
        <input ref="archivo" type="file" multiple accept=".png,.jpg,.jpeg,.pdf,.gif,.webp,.tif,.tiff,.bmp,.svg" hidden @change="subirArchivos($event.target.files); $event.target.value=''">
        <button class="btn primario" style="flex:1" @click="$refs.archivo.click()" :disabled="subiendo > 0"><icono n="subir"/>{{ subiendo ? 'Subiendo ' + Math.round(subiendo * 100) + ' %' : 'Subir imágenes' }}</button>
      </div>
      <input class="entrada" v-model="buscar" placeholder="Buscar imagen" aria-label="Buscar imagen">
      <div class="segmentos">
        <button type="button" :class="{activo: filtro==='todas'}" @click="filtro='todas'">Todas</button>
        <button type="button" :class="{activo: filtro==='subidas'}" @click="filtro='subidas'">Subidas</button>
        <button type="button" :class="{activo: filtro==='cuadernos'}" @click="filtro='cuadernos'">Cuadernos ({{ cuentaCuadernos }})</button>
      </div>
      <p class="ayuda">Selecciona una caja, un elemento con imagen o una capa y pulsa «Usar». También puedes arrastrar archivos aquí.</p>
    </div>
    <div class="zona-soltar" :class="{encima}" v-if="recursos && !recursos.length">
      <strong>Sin imágenes todavía.</strong>
      <span>Arrastra aquí PNG, JPG o PDF, o súbelas con el botón. Las figuras de tus cuadernos aparecen solas al ejecutarlos.</span>
    </div>
    <div class="galeria compacta" v-else>
      <div v-for="r in lista" :key="r.ruta" class="recurso" draggable="true" @dragstart="arrastrar($event, r)" :title="r.ruta">
        <span class="miniatura"><img :src="vista(r)" alt="" loading="lazy"></span>
        <span class="nombre-rec">{{ r.nombre }}</span>
        <span class="meta-rec">{{ r.tipo.toUpperCase() }}, {{ tamano(r.tamano) }}</span>
        <span class="meta-rec" v-if="r.usado"><span class="usado">En el documento</span></span>
        <span class="acciones-rec">
          <button @click="usar(r)" title="Usar en la selección" aria-label="Usar en la selección"><icono n="usar"/></button>
          <button @click="quitar(r)" title="Borrar" aria-label="Borrar"><icono n="basura"/></button>
        </span>
      </div>
    </div>
  </div>`,
};
