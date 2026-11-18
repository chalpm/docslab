// SPDX-License-Identifier: AGPL-3.0-only
// Diálogo para elegir un elemento: las 69 variantes incluidas (I01–I34, T01–T36)
// y los componentes propios del Componente Lab.
import { tienda, cargarBiblioteca, ir } from './tienda.js';

export const SelectorVariantes = {
  name: 'selector-variantes',
  props: { titulo: { type: String, default: 'Añadir un elemento a la caja' }, actual: String, conPropios: { type: Boolean, default: true } },
  emits: ['elegir', 'cerrar'],
  data: () => ({ filtro: '', grupo: 'todos', sinImagen: {} }),
  computed: {
    cat() { return tienda.catalogo; },
    f() { return this.filtro.trim().toLowerCase(); },
    grupos() {
      return this.cat.grupos
        .filter((g) => this.grupo === 'todos' || g.clave === this.grupo)
        .map((g) => ({
          ...g,
          variantes: this.cat.variantes.filter((v) => v.grupo === g.clave &&
            (!this.f || v.nombre.toLowerCase().includes(this.f) || v.codigo.toLowerCase().includes(this.f) || v.clave.toLowerCase().includes(this.f))),
        }))
        .filter((g) => g.variantes.length);
    },
    // los del Lab y los que solo están en este documento (de una plantilla o de un colega)
    propios() {
      if (!this.conPropios || !(this.grupo === 'todos' || this.grupo === 'propios')) return [];
      const lista = (tienda.biblioteca || []).map((c) => ({ ...c, enLab: true }));
      const ids = new Set(lista.map((c) => c.id));
      for (const [id, c] of Object.entries(tienda.componentes || {})) {
        if (!ids.has(id)) lista.push({ id, nombre: c.nombre, descripcion: c.descripcion, modo: c.modo, version: c.version, enLab: false });
      }
      return lista.filter((c) => !this.f || `${c.nombre} ${c.descripcion || ''}`.toLowerCase().includes(this.f));
    },
  },
  methods: {
    img(v) { return `static/img/variantes/${v.clave}.png`; },
    mini(c) { return c.enLab && c.tiene_miniatura ? `api/componentes/${c.id}/miniatura?v=${c.version}` : null; },
    abrirLab() {
      if (tienda.ruta.pid) tienda.volverA = `#/p/${tienda.ruta.pid}`;
      this.$emit('cerrar');
      ir('#/lab');
    },
  },
  created() { this.cortos = { texto: 'Texto', caja: 'Cajas de texto', imagen: 'Imágenes', otros: 'Otros' }; },
  mounted() {
    this.$nextTick(() => this.$refs.buscar && this.$refs.buscar.focus());
    if (this.conPropios) cargarBiblioteca();
  },
  template: `
  <div class="fondo-dialogo" @mousedown.self="$emit('cerrar')" @keydown.esc="$emit('cerrar')">
    <div class="dialogo ancho" role="dialog" aria-modal="true" aria-labelledby="tit-variantes">
      <header>
        <div style="flex:1"><h2 id="tit-variantes">{{ titulo }}</h2>
          <p>Cada variante es una forma de colocar texto o imágenes dentro de una caja. Puedes cambiarla después.</p></div>
        <button class="btn icono fantasma" @click="$emit('cerrar')" aria-label="Cerrar"><icono n="cerrar"/></button>
      </header>
      <div class="cuerpo">
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <input ref="buscar" class="entrada" style="flex:1;min-width:200px" v-model="filtro" placeholder="Buscar: tabla, cita, dos imágenes, I13…" aria-label="Buscar variante">
          <div class="segmentos sin-cortes" style="flex:none">
            <button type="button" :class="{activo: grupo==='todos'}" @click="grupo='todos'">Todas</button>
            <button v-for="g in cat.grupos" :key="g.clave" type="button" :class="{activo: grupo===g.clave}" @click="grupo=g.clave">{{ cortos[g.clave] || g.nombre }}</button>
            <button v-if="conPropios" type="button" :class="{activo: grupo==='propios'}" @click="grupo='propios'">Tuyos</button>
          </div>
        </div>
        <div class="variantes">
          <section v-if="conPropios && (grupo === 'todos' || grupo === 'propios')" class="seccion-propios">
            <h3>Tus componentes <button type="button" class="btn pequeno fantasma" @click="abrirLab"><icono n="matraz"/>Abrir el Componente Lab</button></h3>
            <div class="rejilla-variantes" v-if="propios.length">
              <button v-for="c in propios" :key="c.id" type="button" class="variante" @click="$emit('elegir', 'cmp:' + c.id)" :title="c.descripcion || c.nombre">
                <span class="previa-var"><img v-if="mini(c) && !sinImagen[c.id]" :src="mini(c)" alt="" loading="lazy" @error="sinImagen[c.id] = true"><icono v-else n="pieza"/></span>
                <span class="codigo-var">{{ c.enLab ? 'Lab · v' + c.version : 'Solo en este documento' }}</span>
                <span class="nombre-var">{{ c.nombre }}</span>
              </button>
            </div>
            <p v-else class="ayuda">{{ filtro ? 'Ninguno de tus componentes coincide.' : 'Todavía no tienes. En el Componente Lab puedes hacerlos sin código, con código LaTeX o recreando uno de estos.' }}</p>
          </section>
          <section v-for="g in grupo === 'propios' ? [] : grupos" :key="g.clave">
            <h3>{{ g.nombre }}</h3>
            <div class="rejilla-variantes">
              <button v-for="v in g.variantes" :key="v.clave" type="button" class="variante" :class="{elegido: v.clave === actual}" @click="$emit('elegir', v.clave)">
                <span class="previa-var"><img v-if="!sinImagen[v.clave]" :src="img(v)" alt="" loading="lazy" @error="sinImagen[v.clave] = true"><icono v-else :n="v.grupo === 'imagen' ? 'imagen' : 'texto'"/></span>
                <span class="codigo-var">{{ v.codigo }}</span>
                <span class="nombre-var">{{ v.nombre }}</span>
              </button>
            </div>
          </section>
          <p v-if="grupo !== 'propios' && !grupos.length && !propios.length" class="ayuda">Nada coincide con «{{ filtro }}».</p>
        </div>
      </div>
    </div>
  </div>`,
};
