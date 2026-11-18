// SPDX-License-Identifier: AGPL-3.0-only
// Raíz de la aplicación: rutas, diálogos y avisos.
import { tienda, cerrarDialogo, cerrarAviso, cargarEstado, cargarCatalogo, leerRuta, avisarError } from './tienda.js';
import { ComponenteIcono } from './iconos.js';
import { VistaInicio } from './inicio.js';
import { VistaEditor } from './editor.js';
import { VistaLab } from './lab.js';

const { createApp, nextTick } = Vue;

if (window.pdfjsLib) {
  window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'static/vendor/pdf.worker.min.js';
}

const Dialogo = {
  name: 'dialogo-global',
  data: () => ({ valor: '' }),
  computed: { d() { return tienda.dialogo; } },
  watch: {
    d: {
      immediate: true,
      handler(d) {
        if (!d) return;
        this.valor = d.valor ?? '';
        nextTick(() => {
          const el = this.$el && this.$el.querySelector && this.$el.querySelector('input, textarea, .btn.primario');
          if (el) { el.focus(); if (el.select) el.select(); }
        });
      },
    },
  },
  methods: {
    aceptar() { cerrarDialogo(this.d.tipo === 'preguntar' ? (this.valor.trim() ? this.valor : null) : true); },
    cancelar() { cerrarDialogo(this.d.tipo === 'preguntar' ? null : false); },
    tecla(ev) {
      if (ev.key === 'Escape') this.cancelar();
      if (ev.key === 'Enter' && !(this.d.multilinea && ev.target.tagName === 'TEXTAREA')) { ev.preventDefault(); this.aceptar(); }
    },
  },
  template: `
  <div v-if="d" class="fondo-dialogo" @mousedown.self="cancelar" @keydown="tecla">
    <div class="dialogo" role="dialog" aria-modal="true" aria-labelledby="tit-dialogo">
      <header><div><h2 id="tit-dialogo">{{ d.titulo }}</h2><p v-if="d.texto">{{ d.texto }}</p></div></header>
      <div class="cuerpo" v-if="d.tipo === 'preguntar'">
        <label class="campo"><span class="etiqueta" v-if="d.etiqueta">{{ d.etiqueta }}</span>
          <textarea v-if="d.multilinea" class="entrada" rows="4" v-model="valor"></textarea>
          <input v-else class="entrada" v-model="valor">
          <span class="ayuda" v-if="d.ayuda">{{ d.ayuda }}</span>
        </label>
      </div>
      <footer>
        <button class="btn" @click="cancelar">{{ d.cancelar || 'Cancelar' }}</button>
        <button class="btn" :class="d.peligro ? 'peligro' : 'primario'" @click="aceptar">{{ d.aceptar }}</button>
      </footer>
    </div>
  </div>`,
};

const Raiz = {
  components: { VistaInicio, VistaEditor, VistaLab, DialogoGlobal: Dialogo },
  computed: { t() { return tienda; } },
  methods: { cerrarAviso },
  template: `
    <vista-inicio v-if="t.ruta.vista === 'inicio'"/>
    <vista-editor v-else-if="t.ruta.vista === 'editor'" :key="t.ruta.pid" :pid="t.ruta.pid"/>
    <vista-lab v-else-if="t.ruta.vista === 'lab'" :cid="t.ruta.cid"/>
    <dialogo-global/>
    <div class="avisos" aria-live="polite">
      <div v-for="a in t.avisos" :key="a.id" class="aviso" :class="a.tipo">
        <span>{{ a.texto }}</span>
        <button v-if="a.accion" @click="a.accion.fn(); cerrarAviso(a.id)">{{ a.accion.texto }}</button>
        <button @click="cerrarAviso(a.id)" aria-label="Cerrar aviso">×</button>
      </div>
    </div>`,
};

async function arrancar() {
  leerRuta();
  window.addEventListener('hashchange', leerRuta);
  try {
    await Promise.all([cargarEstado(), cargarCatalogo()]);
  } catch (e) {
    avisarError(e);
  }
  const app = createApp(Raiz);
  app.component('icono', ComponenteIcono);
  app.config.errorHandler = (err) => avisarError(err);
  app.mount('#app');
}

arrancar();
