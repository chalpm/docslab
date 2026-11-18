// SPDX-License-Identifier: AGPL-3.0-only
// Tipografías del documento: clásicas, libres de TeX Live y las propias (.ttf, .otf).
import { api, subir, borrar } from './api.js';
import { tienda, avisar, avisarError } from './tienda.js';

const { inject } = Vue;

// Nombre CSS con el que se carga en el navegador cada tipografía propia (para la muestra)
const cargadas = new Map();
function cargarEnNavegador(pid, f) {
  const clave = `${pid}:${f.id}:${f.archivos.normal}`;
  if (cargadas.has(clave)) return cargadas.get(clave);
  const nombre = `PL-${f.id}`;
  cargadas.set(clave, nombre);
  const url = (ruta) => `url("api/proyectos/${pid}/f/${ruta.split('/').map(encodeURIComponent).join('/')}")`;
  const caras = [[f.archivos.normal, { weight: '400', style: 'normal' }], [f.archivos.negrita, { weight: '700', style: 'normal' }],
    [f.archivos.cursiva, { weight: '400', style: 'italic' }], [f.archivos.negrita_cursiva, { weight: '700', style: 'italic' }]];
  for (const [ruta, desc] of caras) {
    if (!ruta || !window.FontFace) continue;
    const cara = new FontFace(nombre, url(ruta), desc);
    cara.load().then((c) => document.fonts.add(c)).catch(() => { /* la muestra usa la letra del sistema */ });
  }
  return nombre;
}

export const SelectorTipografias = {
  name: 'selector-tipografias',
  setup() { return { ed: inject('ed') }; },
  data: () => ({ subiendo: false }),
  computed: {
    m() { return this.ed.modelo; },
    tp() { return this.m.tipografia; },
    info() { return (tienda.catalogo && tienda.catalogo.familias_info) || {}; },
    instaladas() { return (tienda.estado && tienda.estado.familias) || {}; },
    hayLua() { return !(tienda.estado && tienda.estado.lualatex === false); },
    propias() { return Array.isArray(this.tp.propias) ? this.tp.propias : []; },
    idsPropias() { return new Set(this.propias.map((f) => f.id)); },
    usaPropia() { return this.idsPropias.has(this.tp.familia) || this.idsPropias.has(this.tp.familia_titulos); },
    clasicas() { return Object.entries(this.info).filter(([, v]) => v.grupo === 'clasica'); },
    libres() { return Object.entries(this.info).filter(([, v]) => v.grupo === 'libre'); },
    // con una propia se compila con LuaLaTeX y las libres no se pueden combinar con ella
    avisoLibre() {
      if (!this.usaPropia) return '';
      const libre = [this.tp.familia, this.tp.familia_titulos].find((f) => this.info[f] && this.info[f].grupo === 'libre');
      return libre ? `${this.info[libre].nombre} no se combina con una tipografía propia: en su lugar se usa ${this.info[libre].tipo === 'serif' ? 'Palatino' : 'Helvetica'}.` : '';
    },
  },
  methods: {
    etiquetaLibre(id, v) {
      const falta = this.instaladas[id] === false;
      return falta ? `${v.nombre} (no instalada)` : v.nombre;
    },
    libreDesactivada(id) { return this.instaladas[id] === false; },
    estiloMuestra(f) { return { fontFamily: `"${cargarEnNavegador(this.ed.pid, f)}", sans-serif` }; },
    estilos(f) { return (f.estilos || []).join(', '); },
    cambiar(clave, valor) { this.tp[clave] = valor; },
    async sincronizar() {
      try {
        const r = await api(`api/proyectos/${this.ed.pid}/fuentes`);
        this.ponerLista(r.familias || []);
      } catch { /* sin conexión: se queda la lista del modelo */ }
    },
    ponerLista(lista) {
      const limpia = lista.map((f) => ({ id: f.id, nombre: f.nombre, archivos: f.archivos, estilos: f.estilos, incrustable: f.incrustable }));
      if (JSON.stringify(limpia) !== JSON.stringify(this.propias)) this.tp.propias = limpia;
      const ids = new Set(limpia.map((f) => f.id));
      if (String(this.tp.familia || '').startsWith('propia-') && !ids.has(this.tp.familia)) this.tp.familia = 'helvetica';
      if (String(this.tp.familia_titulos || '').startsWith('propia-') && !ids.has(this.tp.familia_titulos)) this.tp.familia_titulos = '';
    },
    async subirArchivos(ev) {
      const archivos = [...ev.target.files];
      ev.target.value = '';
      if (!archivos.length) return;
      this.subiendo = true;
      try {
        const r = await subir(`api/proyectos/${this.ed.pid}/fuentes`, { archivos });
        for (const e of r.errores || []) avisar(e, { tipo: 'error', ms: 9000 });
        this.ponerLista(r.familias || []);
        const nuevas = (r.nuevas || []).map((id) => this.propias.find((f) => f.id === id)).filter(Boolean);
        if (nuevas.length === 1) {
          const f = nuevas[0];
          const antes = this.tp.familia;
          this.tp.familia = f.id;
          avisar(`${f.nombre} es ahora la tipografía del texto`, { ms: 7000, accion: { texto: 'Deshacer', fn: () => { this.tp.familia = antes; } } });
        } else if (nuevas.length > 1) {
          avisar(`${nuevas.length} tipografías añadidas: elígelas en «Tipografía del texto» o «de los títulos»`);
        }
      } catch (e) { avisarError(e); } finally { this.subiendo = false; }
    },
    async quitar(f) {
      try {
        const r = await borrar(`api/proyectos/${this.ed.pid}/fuentes?familia=${encodeURIComponent(f.id)}`);
        this.ponerLista(r.familias || []);
        avisar(`${f.nombre} quitada del documento`);
      } catch (e) { avisarError(e); }
    },
  },
  mounted() { this.sincronizar(); },
  template: `
  <div class="tipografias">
    <div class="fila-campos">
      <label class="campo"><span class="etiqueta">Tipografía del texto</span>
        <select class="entrada" :value="tp.familia" @change="cambiar('familia', $event.target.value)">
          <optgroup v-if="propias.length" label="Tuyas">
            <option v-for="f in propias" :key="f.id" :value="f.id" :disabled="!hayLua">{{ f.nombre }}</option>
          </optgroup>
          <optgroup label="Clásicas">
            <option v-for="[id, v] in clasicas" :key="id" :value="id">{{ v.nombre }}</option>
          </optgroup>
          <optgroup label="Libres de TeX Live">
            <option v-for="[id, v] in libres" :key="id" :value="id" :disabled="libreDesactivada(id)">{{ etiquetaLibre(id, v) }}</option>
          </optgroup>
        </select>
      </label>
      <label class="campo"><span class="etiqueta">Tipografía de los títulos</span>
        <select class="entrada" :value="tp.familia_titulos || ''" @change="cambiar('familia_titulos', $event.target.value)">
          <option value="">La misma que el texto</option>
          <optgroup v-if="propias.length" label="Tuyas">
            <option v-for="f in propias" :key="f.id" :value="f.id" :disabled="!hayLua">{{ f.nombre }}</option>
          </optgroup>
          <optgroup label="Clásicas">
            <option v-for="[id, v] in clasicas" :key="id" :value="id">{{ v.nombre }}</option>
          </optgroup>
          <optgroup label="Libres de TeX Live">
            <option v-for="[id, v] in libres" :key="id" :value="id" :disabled="libreDesactivada(id)">{{ etiquetaLibre(id, v) }}</option>
          </optgroup>
        </select>
      </label>
    </div>
    <p v-if="avisoLibre" class="ayuda aviso-tipografia">{{ avisoLibre }}</p>

    <div class="propias">
      <div class="cabeza-propias">
        <span class="etiqueta">Tus tipografías</span>
        <input ref="archivo" type="file" accept=".ttf,.otf,font/ttf,font/otf" multiple hidden @change="subirArchivos">
        <button class="btn pequeno" :disabled="subiendo || !hayLua" @click="$refs.archivo.click()"><icono n="subir"/>{{ subiendo ? 'Subiendo…' : 'Subir .ttf u .otf' }}</button>
      </div>
      <p v-if="!hayLua" class="ayuda">Para usar tipografías propias hace falta LuaLaTeX (viene con TeX Live y MiKTeX).</p>
      <ul v-if="propias.length" class="lista-propias">
        <li v-for="f in propias" :key="f.id">
          <div class="muestra-propia" :style="estiloMuestra(f)">
            <strong>{{ f.nombre }}</strong> <span>Aa Bb 123 <b>Negrita</b> <i>Cursiva</i></span>
          </div>
          <span class="ayuda">{{ estilos(f) }}<template v-if="!f.archivos.negrita">; la negrita se imita</template><template v-if="!f.archivos.cursiva">; la cursiva se imita</template></span>
          <span v-if="f.incrustable === false" class="ayuda aviso-tipografia">Su licencia no deja incrustarla en un PDF: la imprenta podría rechazarlo.</span>
          <div class="acciones-propia">
            <button class="btn pequeno" :class="{activo: tp.familia === f.id}" @click="cambiar('familia', f.id)">Para el texto</button>
            <button class="btn pequeno" :class="{activo: tp.familia_titulos === f.id}" @click="cambiar('familia_titulos', f.id)">Para los títulos</button>
            <button class="btn icono pequeno fantasma" @click="quitar(f)" :aria-label="'Quitar ' + f.nombre" title="Quitar del documento"><icono n="basura"/></button>
          </div>
        </li>
      </ul>
      <p class="ayuda" v-else>Sube los archivos de la familia (normal, negrita, cursiva…) de una vez. Con una tipografía propia el documento se compila con LuaLaTeX: tarda algo más.</p>
    </div>
  </div>`,
};
