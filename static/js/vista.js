// SPDX-License-Identifier: AGPL-3.0-only
// Vista previa del PDF con pdf.js, sobre una «mesa de luz», con marcos
// para seleccionar elementos y arrastrar los de las capas.

const { markRaw } = Vue;

const REAL = 96 / 72;             // píxeles CSS por punto PDF a tamaño real (pantalla de 96 ppp)
const MAX_PIXELES = 24e6;         // límite del lienzo de dibujo

export const VistaPdf = {
  name: 'vista-pdf',
  props: {
    url: String,                    // ruta del PDF (sin la versión)
    version: [Number, String],      // cambia en cada compilación
    posiciones: Object,             // {papel: {ancho, alto}, cajas: {id: {...}}}
    seleccion: String,
    nombres: Function,              // id → nombre visible
    tipos: Function,                // id → tipo ('item', 'bloque', …) o null si no existe
    editable: { type: Boolean, default: true },
    compilando: Boolean,
    aviso: String,                  // p. ej. «se muestra la última versión correcta»
    vacio: { type: String, default: 'Compila para ver aquí el documento.' },
    irA: Object,                    // {pagina, clave}: pasar a esa página
    reordenable: { type: Boolean, default: true },   // arrastrar cajas y elementos para cambiarlos de sitio
    zoomInicial: { type: String, default: 'ajustar' },
    resaltado: Object,              // {zona: {pagina, x0, y0, x1, y1} en fracciones de la página, clave}
  },
  // arrastrar(id, fase, x, y): mover una caja o un elemento a otro sitio (x, y en pt desde
  // arriba a la izquierda; fase = mover | soltar | cancelar). editar(id): doble clic.
  emits: ['seleccionar', 'mover', 'escalar', 'empujar', 'paginas', 'arrastrar', 'editar', 'pagina'],
  data: (vm) => ({
    zoom: vm.zoomInicial || 'ajustar', escala: 0.4, pagina: 1, numPaginas: 0, tamPagina: null, cargando: false, error: '',
    marcosVisibles: false, desplaz: {}, arrastre: null, hayPdf: false, brillo: null,
  }),
  computed: {
    textoZoom() { return `${Math.round((this.escala / REAL) * 100)} %`; },
    estiloHoja() {
      if (!this.tamPagina) return {};
      return { width: `${Math.round(this.tamPagina.ancho * this.escala)}px`, height: `${Math.round(this.tamPagina.alto * this.escala)}px` };
    },
    estiloBrillo() {
      const b = this.brillo;
      if (!b || !this.tamPagina) return {};
      const W = this.tamPagina.ancho * this.escala, H = this.tamPagina.alto * this.escala;
      const m = 5;
      return { left: `${b.x0 * W - m}px`, top: `${b.y0 * H - m}px`, width: `${Math.max(6, (b.x1 - b.x0) * W) + 2 * m}px`, height: `${Math.max(6, (b.y1 - b.y0) * H) + 2 * m}px` };
    },
    etiqueta() {
      if (!this.tamPagina) return '';
      const mm = (pt) => Math.round(pt / 72 * 25.4);      // puntos PDF (1/72 in)
      return `${mm(this.tamPagina.ancho)} × ${mm(this.tamPagina.alto)} mm`;
    },
    marcos() {
      const pos = this.posiciones;
      if (!pos || !pos.cajas || !pos.papel || !this.tamPagina || !this.editable) return [];
      const k = this.escala * (this.tamPagina.ancho / pos.papel.ancho);
      const capasDetras = [], contenido = [], delante = [];
      for (const [id, c] of Object.entries(pos.cajas)) {
        if ((c.pagina || 1) !== this.pagina) continue;
        let tipo = this.tipos ? this.tipos(id) : 'bloque';
        if (!tipo) continue;
        const detras = tipo === 'item-detras';
        if (detras) tipo = 'item';
        const d = this.desplaz[id] || { dx: 0, dy: 0, f: 1 };
        const m = {
          id, tipo,
          x: (c.x0 + d.dx) * k, y: (c.y0 + d.dy) * k,
          w: Math.max(4, (c.x1 - c.x0) * k * d.f), h: Math.max(4, (c.y1 - c.y0) * k * d.f),
          nombre: this.nombres ? this.nombres(id) : id,
        };
        if (tipo === 'libre') m.suelta = true;
        if (tipo === 'item') (detras ? capasDetras : delante).push(m);
        else contenido.push(m);
      }
      const orden = { fila: 0, columna: 1, cabecera: 2, pie: 2, bloque: 3, libre: 3, elemento: 4 };
      contenido.sort((a, b) => (orden[a.tipo] ?? 5) - (orden[b.tipo] ?? 5));
      return [...capasDetras, ...contenido, ...delante];
    },
  },
  watch: {
    url() { this.cargar(); },
    version() { this.cargar(); },
    pagina(n) { this.dibujar(); this.$emit('pagina', n); },
    irA(d) { if (d && d.pagina && d.pagina !== this.pagina && (!this.numPaginas || d.pagina <= this.numPaginas)) this.pagina = d.pagina; },
    posiciones() { this.desplaz = {}; },
    resaltado(r) { if (r && r.zona) this.enfocar(r.zona, r.clave); },
  },
  methods: {
    async cargar() {
      if (!this.url || !this.version) { this.hayPdf = false; return; }   // aún no se ha compilado
      if (!window.pdfjsLib) { this.error = 'No se pudo cargar el visor de PDF.'; return; }
      this.cargando = true;
      this.error = '';
      try {
        const tarea = window.pdfjsLib.getDocument({ url: `${this.url}${this.url.includes('?') ? '&' : '?'}v=${this.version || 0}`, isEvalSupported: false });
        const doc = await tarea.promise;
        if (this.doc) { try { this.doc.destroy(); } catch { /* ya cerrado */ } }
        this.doc = markRaw(doc);
        this.numPaginas = doc.numPages;
        this.$emit('paginas', doc.numPages);
        if (this.pagina > doc.numPages) this.pagina = 1;
        this.hayPdf = true;
        await this.dibujar();
      } catch (e) {
        if (e && e.name === 'MissingPDFException') { this.hayPdf = false; }
        else if (e && e.name !== 'RenderingCancelledException') { this.error = 'No se pudo mostrar el PDF: ' + (e.message || e); }
      } finally {
        this.cargando = false;
      }
    },
    calcularEscala(pag) {
      const vp = pag.getViewport({ scale: 1 });
      this.tamPagina = { ancho: vp.width, alto: vp.height };
      if (this.zoom === 'ajustar' || this.zoom === 'ancho') {
        const caja = this.$refs.mesa.getBoundingClientRect();
        const libreW = Math.max(120, caja.width - 100), libreH = Math.max(120, caja.height - 100);
        this.escala = this.zoom === 'ancho' ? libreW / vp.width : Math.min(libreW / vp.width, libreH / vp.height);
      } else {
        this.escala = this.zoom;
      }
    },
    async dibujar() {
      if (!this.doc) return;
      const n = Math.min(this.pagina, this.doc.numPages);
      const pag = await this.doc.getPage(n);
      this.calcularEscala(pag);
      const dpr = window.devicePixelRatio || 1;
      let escalaDibujo = this.escala * dpr;
      const vp1 = pag.getViewport({ scale: 1 });
      const px = vp1.width * vp1.height * escalaDibujo * escalaDibujo;
      if (px > MAX_PIXELES) escalaDibujo *= Math.sqrt(MAX_PIXELES / px);
      const vp = pag.getViewport({ scale: escalaDibujo });
      const lienzo = document.createElement('canvas');
      lienzo.width = Math.floor(vp.width);
      lienzo.height = Math.floor(vp.height);
      lienzo.style.width = `${Math.round(vp1.width * this.escala)}px`;
      lienzo.style.height = `${Math.round(vp1.height * this.escala)}px`;
      lienzo.setAttribute('aria-label', 'Vista previa del documento');
      lienzo.setAttribute('role', 'img');
      if (this.tareaDibujo) { try { this.tareaDibujo.cancel(); } catch { /* nada */ } }
      const tarea = pag.render({ canvasContext: lienzo.getContext('2d'), viewport: vp });
      this.tareaDibujo = markRaw(tarea);
      try {
        await tarea.promise;
      } catch (e) {
        if (e && e.name === 'RenderingCancelledException') return;
        throw e;
      }
      const hoja = this.$refs.hoja;
      if (!hoja) return;
      const viejo = hoja.querySelector('canvas');
      if (viejo) viejo.replaceWith(lienzo); else hoja.prepend(lienzo);
    },
    // ---- señalar una zona (revisión para imprimir): se acerca si hace falta y se marca un rato
    async enfocar(z, clave) {
      if (!this.hayPdf || !this.tamPagina) return;
      if (z.pagina && z.pagina !== this.pagina && z.pagina <= this.numPaginas) { this.pagina = z.pagina; await this.redibujar(); }
      const mesa = this.$refs.mesa.getBoundingClientRect();
      const wPt = Math.max(1, (z.x1 - z.x0) * this.tamPagina.ancho), hPt = Math.max(1, (z.y1 - z.y0) * this.tamPagina.alto);
      // solo se acerca si la zona se ve muy pequeña, y como mucho a tamaño real
      if (wPt * this.escala < 90 && hPt * this.escala < 60) {
        const objetivo = Math.min(REAL, Math.min(0.3 * mesa.width / wPt, 0.3 * mesa.height / hPt));
        if (objetivo > this.escala * 1.2) { this.zoom = objetivo; await this.redibujar(); }
      }
      this.brillo = { ...z, clave };
      clearTimeout(this.tBrillo);
      this.tBrillo = setTimeout(() => { this.brillo = null; }, 4500);
      await this.$nextTick();
      const el = this.$refs.brillo;
      const quieto = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (el) el.scrollIntoView({ block: 'center', inline: 'center', behavior: quieto ? 'auto' : 'smooth' });
    },
    // ---- zoom
    ponerZoom(z, centro) {
      const mesa = this.$refs.mesa;
      const antes = this.escala;
      let rel = null;
      if (centro && mesa) {
        const r = mesa.getBoundingClientRect();
        rel = { x: (mesa.scrollLeft + centro.x - r.left), y: (mesa.scrollTop + centro.y - r.top) };
      }
      this.zoom = z;
      this.redibujar().then(() => {
        if (rel && mesa && typeof z === 'number') {
          const f = this.escala / antes;
          const r = mesa.getBoundingClientRect();
          mesa.scrollLeft = rel.x * f - (centro.x - r.left);
          mesa.scrollTop = rel.y * f - (centro.y - r.top);
        }
      });
    },
    acercar(f, centro) { this.ponerZoom(Math.min(8 * REAL, Math.max(0.05, this.escala * f)), centro); },
    real() { this.ponerZoom(REAL); },
    rueda(ev) {
      if (!ev.ctrlKey && !ev.metaKey) return;
      ev.preventDefault();
      this.acercar(ev.deltaY < 0 ? 1.12 : 1 / 1.12, { x: ev.clientX, y: ev.clientY });
    },
    redibujar() {
      clearTimeout(this.tRedibujo);
      return new Promise((r) => { this.tRedibujo = setTimeout(() => this.dibujar().then(r, r), 40); });
    },
    // ---- marcos: seleccionar, mover, cambiar tamaño
    estiloMarco(m) { return { left: `${m.x}px`, top: `${m.y}px`, width: `${m.w}px`, height: `${m.h}px` }; },
    clases(m) {
      return [m.tipo === 'item' || m.suelta ? 'capa' : 'contenido', `nivel-${m.tipo}`, { seleccionado: m.id === this.seleccion }];
    },
    // pt de la página bajo el puntero
    puntoPt(ev) {
      const r = this.$refs.hoja.getBoundingClientRect();
      const k = this.escala * (this.tamPagina.ancho / this.posiciones.papel.ancho);
      return { x: (ev.clientX - r.left) / k, y: (ev.clientY - r.top) / k };
    },
    abajo(ev, m, modo = 'mover') {
      if (ev.button !== 0) return;
      ev.stopPropagation();
      if (this.editable && this.reordenable && (m.tipo === 'bloque' || m.tipo === 'elemento')) {
        // se selecciona ya; si además se arrastra, se cambia de sitio
        ev.preventDefault();
        if (m.id !== this.seleccion) this.$emit('seleccionar', m.id);
        this.arrastre = { id: m.id, modo: 'reordenar', x0: ev.clientX, y0: ev.clientY, movido: false, base: { dx: 0, dy: 0, f: 1 } };
        ev.currentTarget.setPointerCapture && ev.currentTarget.setPointerCapture(ev.pointerId);
        return;
      }
      // los logos de la cabecera no se mueven, solo cambian de tamaño desde su esquina
      if ((m.tipo !== 'item' && !m.suelta && !(m.tipo === 'logo' && modo === 'escalar')) || !this.editable) { this.$emit('seleccionar', m.id); return; }
      ev.preventDefault();
      this.arrastre = { id: m.id, modo, x0: ev.clientX, y0: ev.clientY, movido: false, w0: m.w, h0: m.h, base: { ...(this.desplaz[m.id] || { dx: 0, dy: 0, f: 1 }) } };
      ev.currentTarget.setPointerCapture && ev.currentTarget.setPointerCapture(ev.pointerId);
      if (m.id !== this.seleccion) this.$emit('seleccionar', m.id);
    },
    moverPuntero(ev) {
      const a = this.arrastre;
      if (!a) return;
      const dx = ev.clientX - a.x0, dy = ev.clientY - a.y0;
      if (!a.movido && Math.abs(dx) + Math.abs(dy) < 3) return;
      a.movido = true;
      const k = this.escala * (this.tamPagina.ancho / this.posiciones.papel.ancho);
      if (a.modo === 'reordenar') {
        this.desplaz = { ...this.desplaz, [a.id]: { dx: dx / k, dy: dy / k, f: 1 } };
        const p = this.puntoPt(ev);
        this.$emit('arrastrar', a.id, 'mover', p.x, p.y);
        return;
      }
      if (a.modo === 'mover') {
        this.desplaz = { ...this.desplaz, [a.id]: { dx: a.base.dx + dx / k, dy: a.base.dy + dy / k, f: a.base.f } };
      } else {
        const f = Math.max(0.1, (a.w0 + Math.max(dx, dy * (a.w0 / a.h0))) / a.w0);
        this.desplaz = { ...this.desplaz, [a.id]: { ...a.base, f: a.base.f * f } };
      }
    },
    arriba(ev) {
      const a = this.arrastre;
      this.arrastre = null;
      if (!a || !a.movido) return;
      if (a.modo === 'reordenar') {
        const resto = { ...this.desplaz };
        delete resto[a.id];
        this.desplaz = resto;
        const p = this.puntoPt(ev);
        this.$emit('arrastrar', a.id, 'soltar', p.x, p.y);
        return;
      }
      const k = this.escala * (this.tamPagina.ancho / this.posiciones.papel.ancho);
      const dx = ev.clientX - a.x0, dy = ev.clientY - a.y0;
      if (a.modo === 'mover') this.$emit('mover', a.id, dx / k, dy / k, this.posiciones.papel);
      else {
        const f = Math.max(0.1, (a.w0 + Math.max(dx, dy * (a.w0 / a.h0))) / a.w0);
        this.$emit('escalar', a.id, f);
      }
    },
    teclaMesa(ev) {
      if (!this.seleccion || !this.tipos || !/^(item|libre)/.test(String(this.tipos(this.seleccion) || ''))) return;
      const paso = ev.shiftKey ? 0.02 : 0.004;
      const d = { ArrowLeft: [-paso, 0], ArrowRight: [paso, 0], ArrowUp: [0, -paso], ArrowDown: [0, paso] }[ev.key];
      if (!d) return;
      ev.preventDefault();
      this.$emit('empujar', this.seleccion, d[0], d[1]);
    },
    titulo(m) {
      if (!this.editable) return m.nombre;
      if (m.suelta) return `${m.nombre} · suelta: arrástrala a donde quieras; la esquina cambia el ancho`;
      if ((m.tipo === 'bloque' || m.tipo === 'elemento') && this.reordenable) return `${m.nombre} · arrastra para moverlo, doble clic para escribir`;
      if (m.tipo === 'logo') return `${m.nombre} · arrastra la esquina para cambiar el tamaño`;
      return `${m.nombre} · doble clic para escribir`;
    },
    cancelarArrastre() {
      const a = this.arrastre;
      this.arrastre = null;
      if (a && a.modo === 'reordenar' && a.movido) {
        const resto = { ...this.desplaz };
        delete resto[a.id];
        this.desplaz = resto;
        this.$emit('arrastrar', a.id, 'cancelar', 0, 0);
      }
    },
    clicFondo(ev) { if (ev.target === ev.currentTarget || ev.target.classList.contains('lienzo-mesa')) this.$emit('seleccionar', null); },
  },
  mounted() {
    this.observador = new ResizeObserver(() => { if (this.zoom === 'ajustar' || this.zoom === 'ancho') this.redibujar(); });
    this.observador.observe(this.$refs.mesa);
    this.cargar();
  },
  beforeUnmount() {
    if (this.observador) this.observador.disconnect();
    if (this.doc) { try { this.doc.destroy(); } catch { /* nada */ } }
  },
  template: `
  <div class="centro">
    <div class="herramientas-vista">
      <div class="grupo-btn">
        <button class="btn icono pequeno" @click="acercar(1 / 1.25)" title="Alejar" aria-label="Alejar"><icono n="zoom-menos"/></button>
        <button class="btn pequeno" @click="ponerZoom('ajustar')" :class="{activo: zoom === 'ajustar'}" title="Ver la página entera">Entero</button>
        <button class="btn pequeno" @click="ponerZoom('ancho')" :class="{activo: zoom === 'ancho'}" title="Ajustar al ancho">Ancho</button>
        <button class="btn pequeno" @click="real" title="Tamaño real en pantalla">100 %</button>
        <button class="btn icono pequeno" @click="acercar(1.25)" title="Acercar" aria-label="Acercar"><icono n="zoom-mas"/></button>
      </div>
      <span class="zoom" aria-live="polite">{{ textoZoom }}</span>
      <template v-if="numPaginas > 1">
        <span class="divisor"></span>
        <button class="btn icono pequeno" :disabled="pagina <= 1" @click="pagina--" aria-label="Página anterior"><icono n="arriba"/></button>
        <span class="zoom">{{ pagina }} / {{ numPaginas }}</span>
        <button class="btn icono pequeno" :disabled="pagina >= numPaginas" @click="pagina++" aria-label="Página siguiente"><icono n="abajo"/></button>
      </template>
      <span v-if="aviso && hayPdf" class="chip aviso-chip" :title="aviso"><span class="punto"></span>{{ aviso }}</span>
      <span style="flex:1"></span>
      <label v-if="editable" class="interruptor" style="min-height:26px;gap:8px"><span class="texto" style="font-size:var(--t-xs)">Marcos</span>
        <input type="checkbox" v-model="marcosVisibles"><span class="pista"></span></label>
      <slot name="herramientas"></slot>
    </div>
    <div class="mesa con-cuadricula" ref="mesa" tabindex="0" @wheel="rueda" @keydown="teclaMesa" @click="clicFondo" aria-label="Mesa con la vista previa (Ctrl + rueda para hacer zoom)">
      <div class="lienzo-mesa" @click="clicFondo">
        <div class="hoja" ref="hoja" v-show="hayPdf" :style="estiloHoja" :class="{'mostrar-marcos': marcosVisibles}">
          <div class="marcas-corte"><i></i><i></i><i></i><i></i></div>
          <svg class="registro-marca arriba" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1"><circle cx="8" cy="8" r="4.4"/><path d="M8 0v16M0 8h16"/></svg>
          <svg class="registro-marca abajo" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1"><circle cx="8" cy="8" r="4.4"/><path d="M8 0v16M0 8h16"/></svg>
          <span class="etiqueta-hoja">{{ etiqueta }}</span>
          <div class="capa-marcas" @pointermove="moverPuntero" @pointerup="arriba" @pointercancel="cancelarArrastre">
            <div v-for="m in marcos" :key="m.id" class="marco" :class="clases(m)" :style="estiloMarco(m)" :title="titulo(m)" :data-id="m.id"
                 @pointerdown="abajo($event, m)" @dblclick.stop="editable && $emit('editar', m.id)">
              <span class="rotulo">{{ m.nombre }}</span>
 <span v-if="m.suelta" class="asa" @pointerdown.stop="abajo($event, m, 'mover')" title="Arrastra para mover la caja suelta"><icono n="arrastrar"/></span>
              <span v-if="m.tipo === 'item' || m.suelta || m.tipo === 'logo'" class="tirador" @pointerdown.stop="abajo($event, m, 'escalar')" title="Cambiar el tamaño"></span>
            </div>
          </div>
          <div v-if="brillo && (brillo.pagina || 1) === pagina" :key="brillo.clave" ref="brillo" class="resaltado-vista" :style="estiloBrillo" aria-hidden="true"></div>
          <div v-if="editable && posiciones && posiciones.papel && tamPagina" class="capa-edicion">
            <slot name="capa" :k="escala * (tamPagina.ancho / posiciones.papel.ancho)" :pagina="pagina"></slot>
          </div>
        </div>
      </div>
      <div class="estado-vista" v-if="!hayPdf && !cargando">
        <div class="hoja-vacia"><span>{{ compilando ? 'Compilando…' : 'Sin PDF' }}</span></div>
        <p v-if="error">{{ error }}</p>
        <p v-else>{{ compilando ? 'Preparando la primera vista previa.' : vacio }}</p>
      </div>
      <span class="chip trabajando compilando-velo" v-if="compilando && hayPdf"><span class="punto"></span>Compilando</span>
    </div>
    <slot name="pie"></slot>
  </div>`,
};
