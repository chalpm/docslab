// SPDX-License-Identifier: AGPL-3.0-only
// Editor de un proyecto: barra superior, paneles, guardado automático,
// compilación, deshacer y todas las operaciones sobre el modelo.
import { api, post, patch, put, descargar, esperarTrabajo } from './api.js';
import { tienda, avisar, avisarError, confirmar, preguntar, ir, cargarBiblioteca } from './tienda.js';
import { retrasar, clonar, redondear, aFraccion, copiarTexto, fecha, recortar } from './util.js';
import {
  indexar, ancestros, nombreNodo, nuevaFila, nuevaColumna, nuevoBloque, nuevoElemento, nuevaCapa, nuevoItem,
  conIdsNuevos, mover, camposImagen, variante, nuevoElementoComponente,
  nuevaPagina, nuevoBloqueLibre, nuevaSeccion, NOMBRES_CLASE, ARTICULO_CLASE, esFlujo,
} from './modeloed.js';
import { Arbol } from './arbol.js';
import { Inspector } from './inspector.js';
import { VistaPdf } from './vista.js';
import { PanelRecursos } from './recursos.js';
import { LabDocumento } from './cuaderno.js';
import { PanelRegistro } from './registro.js';
import { SelectorVariantes } from './variantes.js';
import { CuerpoLatex } from './latex.js';
import { PanelReferencias, insertarCita } from './referencias.js';
import { EdicionDirecta } from './directa.js';
import { PanelRevision, DialogoImprenta } from './revision.js';
import { DialogoPowerpoint } from './powerpoint.js';

const { reactive, computed, watch, provide, onMounted, onBeforeUnmount, nextTick } = Vue;

const LOGO = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="8" cy="8" r="4.4"/><path d="M8 .8v14.4M.8 8h14.4"/></svg>';

// ---------------------------------------------------------------- diálogos del editor
const DialogoHistorial = {
  name: 'dialogo-historial',
  props: { pid: String },
  emits: ['restaurar', 'cerrar'],
  data: () => ({ versiones: null }),
  methods: { fecha },
  async mounted() {
    try { this.versiones = await api(`api/proyectos/${this.pid}/historial`); } catch (e) { avisarError(e); }
  },
  template: `
  <div class="fondo-dialogo" @mousedown.self="$emit('cerrar')" @keydown.esc="$emit('cerrar')">
    <div class="dialogo" role="dialog" aria-modal="true" aria-labelledby="tit-historial">
      <header><div style="flex:1"><h2 id="tit-historial">Versiones guardadas</h2>
        <p>DocsLab guarda una copia del documento como mucho cada dos minutos mientras editas (las 30 últimas).</p></div>
        <button class="btn icono fantasma" @click="$emit('cerrar')" aria-label="Cerrar"><icono n="cerrar"/></button></header>
      <div class="cuerpo">
        <p v-if="versiones && !versiones.length" class="ayuda">Todavía no hay versiones anteriores.</p>
        <div class="explorador" v-if="versiones && versiones.length">
          <button v-for="v in versiones" :key="v.nombre" @click="$emit('restaurar', v.nombre)">
            <icono n="historial"/><span style="flex:1">{{ fecha(v.fecha) }}</span><span class="ayuda">Restaurar</span></button>
        </div>
      </div>
      <footer><button class="btn" @click="$emit('cerrar')">Cerrar</button></footer>
    </div>
  </div>`,
};

const DialogoCodigo = {
  name: 'dialogo-codigo',
  props: { pid: String },
  emits: ['cerrar'],
  data: () => ({ codigo: '' }),
  methods: {
    async copiar() { await copiarTexto(this.codigo); avisar('Código copiado'); },
  },
  async mounted() {
    try { this.codigo = await api(`api/proyectos/${this.pid}/latex`, { texto: true }); } catch (e) { avisarError(e); }
  },
  template: `
  <div class="fondo-dialogo" @mousedown.self="$emit('cerrar')" @keydown.esc="$emit('cerrar')">
    <div class="dialogo ancho" role="dialog" aria-modal="true" aria-labelledby="tit-codigo">
      <header><div style="flex:1"><h2 id="tit-codigo">Código LaTeX</h2>
        <p>Es lo que se compila. Para editarlo a mano, convierte el proyecto en proyecto LaTeX (menú Más).</p></div>
        <button class="btn icono fantasma" @click="$emit('cerrar')" aria-label="Cerrar"><icono n="cerrar"/></button></header>
      <div class="cuerpo"><pre class="registro-nb" style="max-height:62vh;font-size:12.5px">{{ codigo || 'Cargando…' }}</pre></div>
      <footer><button class="btn" @click="copiar"><icono n="portapapeles"/>Copiar</button><button class="btn primario" @click="$emit('cerrar')">Cerrar</button></footer>
    </div>
  </div>`,
};

// ---------------------------------------------------------------- editor
export const VistaEditor = {
  name: 'vista-editor',
  props: { pid: String },
  components: { ArbolEstructura: Arbol, InspectorEditor: Inspector, VistaPdf, EdicionDirecta, PanelRecursos, LabDocumento, PanelReferencias, PanelRegistro, SelectorVariantes, CuerpoLatex, DialogoHistorial, DialogoCodigo, PanelRevision, DialogoImprenta, DialogoPowerpoint },
  setup(props) {
    const pid = props.pid;
    const ed = reactive({
      pid, meta: null, modelo: null, sel: null, abiertos: new Set(),
      estado: 'cargando', compilando: false, compilacion: null, version: 0,
      puedeDeshacer: false, puedeRehacer: false, versionRecursos: 0,
      dialogoVariantes: null, panelIzq: 'estructura', verIzq: window.innerWidth > 820, verDer: window.innerWidth > 820,
      antesDeCompilar: null, menu: null, dialogo: null, plantillaPropia: null,
      arrastre: null, editandoId: null, soltarEnVista: null, ajustando: null,
      revision: false, resaltado: null, paginaVista: 1, irPagina: null, vistaLab: false, labAbierto: false,
    });
    // clase de documento: póster, presentación, documento, artículo o tesis
    ed.clase = computed(() => (ed.modelo && ed.modelo.clase) || (ed.meta && ed.meta.clase) || 'poster');
    ed.flujo = computed(() => esFlujo(ed.modelo));
    ed.nombreClase = computed(() => NOMBRES_CLASE[ed.clase] || 'Póster');
    ed.articulo = computed(() => ARTICULO_CLASE[ed.clase] || 'el póster');
    ed.indice = computed(() => (ed.modelo ? indexar(ed.modelo) : new Map()));
    // los componentes propios del póster, para el inspector y el árbol
    watch(() => ed.modelo && ed.modelo.componentes, (c) => { tienda.componentes = c || {}; }, { immediate: true });
    ed.urlPdf = `api/proyectos/${pid}/pdf`;

    // ------------------------------------------------ historia (deshacer / rehacer)
    let pila = [], futuro = [], instantanea = '', ignorar = false, ultimoGuardado = '';
    const botones = () => { ed.puedeDeshacer = pila.length > 0 || historiaPronto.pendiente(); ed.puedeRehacer = futuro.length > 0; };
    function confirmarHistoria() {
      if (!ed.modelo) return;
      const ahora = JSON.stringify(ed.modelo);
      if (ahora === instantanea) return;
      pila.push(instantanea);
      if (pila.length > 150) pila.shift();
      futuro = [];
      instantanea = ahora;
      botones();
    }
    const historiaPronto = retrasar(confirmarHistoria, 450);
    function restaurar(json) {
      ignorar = true;
      ed.modelo = JSON.parse(json);
      ignorar = false;
      instantanea = json;
      if (ed.sel && !ed.indice.get(ed.sel)) ed.sel = null;
      botones();
      ed.estado = 'cambios';
      guardarPronto();
    }
    ed.deshacer = () => {
      historiaPronto.cancelar(); confirmarHistoria();
      if (!pila.length) return;
      futuro.push(instantanea);
      restaurar(pila.pop());
    };
    ed.rehacer = () => {
      historiaPronto.cancelar(); confirmarHistoria();
      if (!futuro.length) return;
      pila.push(instantanea);
      restaurar(futuro.pop());
    };

    // ------------------------------------------------ guardado y compilación
    async function guardarAhora() {
      if (!ed.modelo) return;
      const json = JSON.stringify(ed.modelo);
      if (json === ultimoGuardado) { if (ed.estado !== 'error') ed.estado = 'guardado'; return; }
      ed.estado = 'guardando';
      try {
        await put(`api/proyectos/${pid}/modelo`, JSON.parse(json));
        ultimoGuardado = json;
        ed.estado = JSON.stringify(ed.modelo) === json ? 'guardado' : 'cambios';
      } catch (e) {
        ed.estado = 'error';
        avisarError(e);
        throw e;
      }
    }
    let compilacionPendiente = false;
    async function compilar() {
      if (ed.compilando) { compilacionPendiente = true; return; }
      ed.compilando = true;
      try {
        const t = await post(`api/proyectos/${pid}/compilar`);
        const fin = await esperarTrabajo(t.id, { intervalo: 350 });
        if (fin.estado === 'error') avisar(`No se pudo compilar: ${fin.mensaje}`, { tipo: 'error', ms: 9000 });
        const res = await api(`api/proyectos/${pid}/compilacion`);
        if (res) { ed.compilacion = res; ed.version = res.version; }
      } catch (e) {
        avisarError(e);
      } finally {
        ed.compilando = false;
        if (compilacionPendiente) { compilacionPendiente = false; compilar(); }
      }
    }
    const compilarPronto = retrasar(compilar, 250);
    const guardarPronto = retrasar(async () => {
      try { await guardarAhora(); } catch { return; }
      if (ed.meta && ed.meta.ajustes.auto_compilar !== false) compilarPronto();
    }, 700);
    ed.compilarPronto = () => compilarPronto();
    ed.compilarAhora = async () => {
      guardarPronto.cancelar(); compilarPronto.cancelar();
      try {
        if (ed.antesDeCompilar) await ed.antesDeCompilar();
        await guardarAhora();
      } catch { return; }
      await compilar();
    };
    ed.guardarAhora = guardarAhora;
    ed.marcarCambios = () => { ed.estado = 'cambios'; };
    ed.marcarGuardado = () => { ed.estado = 'guardado'; };
    ed.recursosCambiaron = () => { ed.versionRecursos++; };

    watch(() => ed.modelo, () => {
      if (ignorar || !ed.modelo) return;
      ed.estado = 'cambios';
      historiaPronto();
      ed.puedeDeshacer = true;
      guardarPronto();
    }, { deep: true, flush: 'sync' });

    // ------------------------------------------------ carga
    async function cargar() {
      try {
        const d = await api(`api/proyectos/${pid}`);
        ed.meta = d.meta;
        ed.plantillaPropia = d.plantilla_propia || null;
        if (d.meta.tipo === 'estructurado') {
          ignorar = true;
          ed.modelo = d.modelo;
          ignorar = false;
          instantanea = ultimoGuardado = JSON.stringify(d.modelo);
          d.modelo.filas.forEach((f) => { ed.abiertos.add(f.id); f.columnas.forEach((c) => ed.abiertos.add(c.id)); });
          if (d.modelo.clase === 'presentacion' && d.modelo.paginas[0]) ed.abiertos.add(d.modelo.paginas[0].id);
          d.modelo.capas.forEach((c) => { if (c.elementos.length) ed.abiertos.add(c.id); });
        }
        ed.estado = 'guardado';
        document.title = `${d.meta.nombre} · DocsLab`;
        const c = await api(`api/proyectos/${pid}/compilacion`);
        if (c) { ed.compilacion = c; ed.version = c.version; }
        if (!c && d.meta.ajustes.auto_compilar !== false) compilar();
      } catch (e) {
        avisarError(e);
        ir('#/');
      }
    }

    // ------------------------------------------------ selección y árbol
    ed.seleccionar = (id, op = {}) => {
      ed.sel = id || null;
      if (!id) return;
      const info = ed.indice.get(id);
      ancestros(info).forEach((a) => ed.abiertos.add(a));
      if (!op.desdeVista) irAPaginaDe(id);
      // desde la vista previa no se cambia la pestaña de la izquierda: Imágenes y
      // Referencias se usan sobre lo que se selecciona en el póster
      if (op.desdeVista && !ed.verDer && window.innerWidth > 820) ed.verDer = true;
    };
    // La vista previa sigue a lo que se selecciona en el árbol (diapositiva o página del documento)
    let irPendiente = null;
    function paginaDe(id) {
      const pos = ed.compilacion && ed.compilacion.posiciones;
      const info = ed.indice.get(id);
      if (!pos || !info) return null;
      const caja = pos.cajas && pos.cajas[id];
      if (caja) return caja.pagina || 1;
      const pg = info.tipo === 'pagina' ? info.obj : info.pagina;
      return pg && pos.paginas ? (pos.paginas[pg.id] || null) : null;
    }
    function irAPaginaDe(id) {
      if (ed.clase === 'poster') return;
      const n = paginaDe(id);
      if (n) { irPendiente = null; if (n !== ed.paginaVista) ed.irPagina = { pagina: n, clave: Date.now() }; }
      else irPendiente = id;
    }
    watch(() => ed.version, () => { if (irPendiente && ed.sel === irPendiente) irAPaginaDe(irPendiente); else irPendiente = null; });
    // La diapositiva en la que se trabaja: la de la selección o la que se ve
    ed.pagActual = () => {
      const m = ed.modelo;
      if (!m || m.clase !== 'presentacion') return null;
      const info = ed.indice.get(ed.sel);
      if (info && info.tipo === 'pagina') return info.obj;
      if (info && info.pagina) return info.pagina;
      const mapa = (ed.compilacion && ed.compilacion.posiciones && ed.compilacion.posiciones.paginas) || {};
      let mejor = null, nMejor = 0;
      for (const pg of m.paginas) { const n = mapa[pg.id]; if (n && n <= ed.paginaVista && n >= nMejor) { mejor = pg; nMejor = n; } }
      return mejor || m.paginas[0] || null;
    };
    let ultimoCampo = null;
    function alEnfocar(ev) {
      const t = ev.target;
      const esTexto = t && (t.tagName === 'TEXTAREA' || (t.tagName === 'INPUT' && ['text', 'search', ''].includes(t.type)));
      if (esTexto && t.closest('.panel.der') && !t.closest('.menu') && !t.classList.contains('codigo')) ultimoCampo = t;
    }
    ed.insertarCita = (clave) => {
      if (!ultimoCampo || !document.body.contains(ultimoCampo)) return false;
      return insertarCita(ultimoCampo, clave);
    };
    // edición directa en la vista previa
    ed.arrastrar = (id, fase, x, y) => {
      if (fase === 'mover') ed.arrastre = { id, x, y };
      else if (fase === 'soltar') { ed.arrastre = { id, x, y }; if (ed.soltarEnVista) ed.soltarEnVista(); ed.arrastre = null; }
      else ed.arrastre = null;
    };
    ed.editarEnVista = (id) => {
      if (!ed.indice.get(id)) return;
      ed.seleccionar(id, { desdeVista: true });
      ed.editandoId = id;
    };
    watch(() => ed.sel, (s) => { if (ed.editandoId && ed.editandoId !== s) ed.editandoId = null; });
    ed.alternarAbierto = (id) => { if (ed.abiertos.has(id)) ed.abiertos.delete(id); else ed.abiertos.add(id); };
    ed.nombre = (id) => nombreNodo(ed.indice.get(id));
    ed.tipo = (id) => {
      const info = ed.indice.get(id);
      if (!info) return null;
      if (info.tipo === 'item') return Number(info.capa.z) < 0 ? 'item-detras' : 'item';
      if (ed.flujo) return ['fila', 'columna', 'pagina'].includes(info.tipo) ? null : info.tipo;
      if (info.tipo === 'pagina') return null;
      if (info.tipo === 'bloque' && info.obj.libre) return 'libre';
      // una caja suelta con un solo elemento se maneja entera
      if (info.tipo === 'elemento' && info.bloque.libre && info.bloque.elementos.length === 1) return null;
      return info.tipo;
    };

    // ------------------------------------------------ operaciones sobre el modelo
    ed.alternarVisible = (id) => { const o = ed.indice.get(id)?.obj; if (o) o.visible = !(o.visible !== false); };
    ed.alternarTitulo = (id) => { const o = ed.indice.get(id)?.obj; if (o) o.mostrar_titulo = !(o.mostrar_titulo !== false); };
    ed.agregarFila = (columnas = 2) => {
      const f = nuevaFila(columnas);
      const pg = ed.pagActual();
      if (pg) {
        f.pag = pg.id;
        f.columnas.forEach((c) => c.bloques.forEach((b) => { b.titulo = ''; b.mostrar_titulo = false; }));
        ed.abiertos.add(pg.id);
      }
      ed.modelo.filas.push(f);
      ed.abiertos.add(f.id); f.columnas.forEach((c) => ed.abiertos.add(c.id));
      ed.seleccionar(f.id);
    };
    ed.agregarHijo = (id) => {
      const info = ed.indice.get(id);
      if (!info) return;
      if (info.tipo === 'fila') {
        const c = nuevaColumna();
        info.obj.columnas.push(c);
        const suma = info.obj.columnas.reduce((s, x) => s + Math.max(1, Number(x.abarca) || 1), 0);
        if (Number(info.obj.rejilla) > 0) info.obj.rejilla = Math.max(Number(info.obj.rejilla), suma);
        ed.abiertos.add(info.obj.id); ed.abiertos.add(c.id);
        ed.seleccionar(c.id);
      } else if (info.tipo === 'pagina') {
        ed.seleccionar(id);
        ed.agregarFila(1);
      } else if (info.tipo === 'columna') {
        const destino = info.pagina || ed.modelo.lienzo;
        const b = ed.flujo ? nuevaSeccion(1) : destino.libre ? nuevoBloqueLibre('caja') : nuevoBloque();
        if (b.libre) Object.assign(b, sitioLibre());
        info.obj.bloques.push(b);
        ed.abiertos.add(info.obj.id);
        ed.seleccionar(b.id);
      } else if (info.tipo === 'bloque') {
        ed.dialogoVariantes = { bloque: id };
      }
    };
    ed.abrirVariantes = (bloque, reemplazar) => { ed.dialogoVariantes = { bloque, reemplazar }; };
    // Copia la definición de un componente del Lab en el póster (o la pone al día)
    ed.traerComponente = async (cid) => {
      const c = await api(`api/componentes/${cid}`);
      if (!ed.modelo.componentes) ed.modelo.componentes = {};
      const antes = ed.modelo.componentes[cid];
      ed.modelo.componentes[cid] = c;
      if (antes && antes.version !== c.version) avisar(`«${c.nombre}» se puso al día (versión ${c.version}) en todo el documento`);
      return c;
    };
    ed.elegirVariante = async (clave) => {
      const d = ed.dialogoVariantes;
      ed.dialogoVariantes = null;
      if (!d) return;
      if (d.reemplazar) { ed.cambiarVariante(d.reemplazar, clave); return; }
      const info = ed.indice.get(d.bloque);
      if (!info) return;
      let e;
      if (clave.startsWith('cmp:')) {
        const cid = clave.slice(4);
        let c = (ed.modelo.componentes || {})[cid];
        const enLab = (tienda.biblioteca || []).find((x) => x.id === cid);
        try {
          if (!c || (enLab && enLab.version > (c.version || 0))) c = await ed.traerComponente(cid);
        } catch (err) { if (!c) { avisarError(err); return; } }
        e = nuevoElementoComponente(c);
      } else {
        e = nuevoElemento(clave);
      }
      const s = ed.indice.get(ed.sel);
      if (s && s.tipo === 'elemento' && s.bloque === info.obj) info.obj.elementos.splice(s.i + 1, 0, e);
      else info.obj.elementos.push(e);
      ed.abiertos.add(info.obj.id);
      ed.seleccionar(e.id);
    };
    ed.cambiarVariante = (id, clave) => {
      const info = ed.indice.get(id);
      if (!info || info.obj.tipo === clave || clave.startsWith('cmp:')) return;
      const viejo = info.obj, vv = variante(viejo);
      const nuevo = nuevoElemento(clave);
      const tiposViejos = Object.fromEntries((vv ? vv.campos : []).map((c) => [c.nombre, c.tipo]));
      const compatibles = (a, b) => a === b || (['texto', 'parrafo'].includes(a) && ['texto', 'parrafo'].includes(b));
      for (const c of tienda.catalogo.porClave[clave].campos) {
        const v = viejo[c.nombre];
        if (v !== undefined && v !== '' && compatibles(tiposViejos[c.nombre], c.tipo)) nuevo[c.nombre] = clonar(v);
      }
      nuevo.id = viejo.id;
      nuevo.visible = viejo.visible !== false;
      info.lista.splice(info.i, 1, nuevo);
    };
    ed.agregarCapa = (delante) => {
      const zs = ed.modelo.capas.map((c) => Number(c.z) || 0);
      const z = delante ? Math.max(0, ...zs.filter((x) => x >= 0)) + 5 : Math.min(0, ...zs.filter((x) => x < 0)) - 5;
      const c = nuevaCapa(delante ? 'Capa nueva (delante)' : 'Capa nueva (detrás)', z);
      ed.modelo.capas.push(c);
      ed.abiertos.add(c.id);
      ed.seleccionar(c.id);
    };
    ed.agregarItem = (capaId, tipo) => {
      const capa = ed.indice.get(capaId)?.obj;
      if (!capa) return;
      const it = nuevoItem(tipo);
      if (tipo === 'imagen') it.ancho = 0.25;
      if (tipo === 'forma') { it.ancho = 0.2; }
      capa.elementos.push(it);
      ed.abiertos.add(capa.id);
      ed.seleccionar(it.id);
      if (capa.visible === false) avisar('La capa está oculta: enciéndela para ver el elemento.');
    };
    // ------------------------------------------------ posición libre (pósters y presentaciones)
    const todosLosBloques = (pg) => ed.modelo.filas.filter((f) => !pg || f.pag === pg.id).flatMap((f) => f.columnas.flatMap((c) => c.bloques));
    function posCaja(id) {
      const p = ed.compilacion && ed.compilacion.posiciones;
      const c = p && p.cajas && p.cajas[id];
      if (!c || !p.papel) return null;
      return { x: redondear(c.x0 / p.papel.ancho), y: redondear(c.y0 / p.papel.alto), ancho: redondear((c.x1 - c.x0) / p.papel.ancho) };
    }
    function sitioLibre(n) {
      const k = (n ?? todosLosBloques(ed.pagActual()).filter((b) => b.libre).length) % 8;
      return { x: redondear(0.1 + 0.03 * k), y: redondear(0.18 + 0.04 * k), ancho: 0.3 };
    }
    function columnaAnfitriona(pg) {
      const filas = ed.modelo.filas.filter((f) => !pg || f.pag === pg.id);
      let f = filas[filas.length - 1];
      if (!f) {
        f = nuevaFila(1);
        f.columnas[0].bloques = [];
        if (pg) f.pag = pg.id;
        ed.modelo.filas.push(f);
      }
      if (!f.columnas.length) f.columnas.push(nuevaColumna(false));
      return f.columnas[f.columnas.length - 1];
    }
    // Suelta una caja (o un elemento, en una caja propia) de la cuadrícula, en el sitio donde está
    ed.soltar = (id) => {
      const info = ed.indice.get(id);
      if (!info || ed.flujo) return;
      if (info.tipo === 'bloque') {
        if (info.obj.libre) return;
        Object.assign(info.obj, { libre: true, estirar: false, rotacion: 0, ...(posCaja(id) || sitioLibre()) });
        ed.seleccionar(id);
      } else if (info.tipo === 'elemento') {
        const b = nuevoBloque('', false);
        Object.assign(b, { libre: true, rotacion: 0, mostrar_titulo: false, estilo: 'ninguno', opciones: { relleno: '0pt' }, ...(posCaja(id) || sitioLibre()) });
        info.lista.splice(info.i, 1);
        b.elementos.push(info.obj);
        info.columna.bloques.push(b);
        ed.seleccionar(b.id);
      } else return;
      avisar('Ya está suelta: arrástrala en la vista previa a donde quieras.', { accion: { texto: 'Deshacer', fn: () => ed.deshacer() } });
    };
    ed.aCuadricula = (id) => {
      const b = ed.indice.get(id)?.obj;
      if (!b || !b.libre) return;
      b.libre = false;
      avisar('La caja volvió a su columna de la cuadrícula.');
    };
    // Añade una caja suelta nueva (texto, imagen o caja con título) a la página que se ve
    ed.agregarLibre = (que = 'texto') => {
      if (ed.flujo) return;
      const pg = ed.pagActual();
      const b = nuevoBloqueLibre(que);
      Object.assign(b, sitioLibre());
      const col = columnaAnfitriona(pg);
      col.bloques.push(b);
      [pg && pg.id, b.id].filter(Boolean).forEach((x) => ed.abiertos.add(x));
      const f = ed.modelo.filas.find((x) => x.columnas.includes(col));
      ed.abiertos.add(f.id); ed.abiertos.add(col.id);
      ed.seleccionar(b.id);
    };
    // Lienzo libre: toda la página (póster o diapositiva) deja la cuadrícula
    ed.lienzoLibre = async (activar) => {
      if (ed.flujo) return;
      const pg = ed.pagActual();
      const destino = pg || ed.modelo.lienzo;
      const bloques = todosLosBloques(pg);
      if (activar) {
        let n = 0;
        bloques.forEach((b) => { if (!b.libre) Object.assign(b, { libre: true, estirar: false, rotacion: 0, ...(posCaja(b.id) || sitioLibre(n++)) }); });
        destino.libre = true;
        avisar('Lienzo libre: arrastra cada caja a donde quieras. Lo nuevo que añadas también queda suelto.', { ms: 7000, accion: { texto: 'Deshacer', fn: () => ed.deshacer() } });
      } else {
        const sueltas = bloques.filter((b) => b.libre).length;
        if (sueltas) {
          const ok = await confirmar({ titulo: '¿Volver a la cuadrícula?', texto: `${sueltas === 1 ? 'La caja suelta vuelve' : `Las ${sueltas} cajas sueltas vuelven`} a su fila y su columna, y se pierde la posición que le diste.`, aceptar: 'Volver a la cuadrícula' });
          if (!ok) return;
        }
        bloques.forEach((b) => { b.libre = false; });
        destino.libre = false;
      }
    };

    // ------------------------------------------------ diapositivas
    ed.agregarPagina = (diseno = 'contenido') => {
      const m = ed.modelo;
      const act = ed.pagActual();
      const pg = nuevaPagina(diseno === 'seccion' ? 'Sección nueva' : diseno === 'contenido' ? 'Diapositiva nueva' : '', diseno);
      m.paginas.splice(act ? m.paginas.indexOf(act) + 1 : m.paginas.length, 0, pg);
      if (diseno === 'contenido') {
        const f = nuevaFila(1);
        f.pag = pg.id;
        Object.assign(f.columnas[0].bloques[0], { titulo: '', mostrar_titulo: false });
        m.filas.push(f);
        ed.abiertos.add(f.id); ed.abiertos.add(f.columnas[0].id);
      }
      ed.abiertos.add(pg.id);
      ed.seleccionar(pg.id);
    };
    function duplicarPagina(info) {
      const m = ed.modelo;
      const copia = conIdsNuevos(info.obj);
      const filas = m.filas.filter((f) => f.pag === info.obj.id).map((f) => ({ ...conIdsNuevos(f), pag: copia.id }));
      m.paginas.splice(info.i + 1, 0, copia);
      m.filas.push(...filas);
      ed.abiertos.add(copia.id);
      ed.seleccionar(copia.id);
    }
    function eliminarPagina(info) {
      const m = ed.modelo;
      if (m.paginas.length <= 1) { avisar('Una presentación necesita al menos una diapositiva.'); return; }
      const nombre = nombreNodo(info);
      m.filas = m.filas.filter((f) => f.pag !== info.obj.id);
      m.paginas.splice(info.i, 1);
      ed.sel = (m.paginas[Math.min(info.i, m.paginas.length - 1)] || {}).id || null;
      if (ed.sel) irAPaginaDe(ed.sel);
      avisar(`Diapositiva «${nombre}» borrada`, { accion: { texto: 'Deshacer', fn: () => ed.deshacer() } });
    }
    // ------------------------------------------------ secciones (documentos, artículos y tesis)
    ed.agregarSeccion = (nivel) => {
      const m = ed.modelo;
      if (!m.filas.length) m.filas.push({ ...nuevaFila(1), columnas: [nuevaColumna(false)] });
      const info = ed.indice.get(ed.sel);
      const ref = info && (info.tipo === 'bloque' ? info : info.tipo === 'elemento' ? ed.indice.get(info.bloque.id) : null);
      const b = nuevaSeccion(nivel || (ref ? Number(ref.obj.nivel) || 1 : 1));
      if (ref) ref.lista.splice(ref.i + 1, 0, b);
      else { const f = m.filas[m.filas.length - 1]; f.columnas[f.columnas.length - 1].bloques.push(b); }
      ed.abiertos.add(b.id);
      ed.seleccionar(b.id);
    };

    ed.duplicar = (id) => {
      const info = ed.indice.get(id);
      if (!info || !info.lista || info.tipo === 'capa') return;
      if (info.tipo === 'pagina') { duplicarPagina(info); return; }
      const copia = conIdsNuevos(info.obj);
      if (copia.libre) { copia.x = redondear((Number(copia.x) || 0) + 0.02); copia.y = redondear((Number(copia.y) || 0) + 0.02); }
      info.lista.splice(info.i + 1, 0, copia);
      ed.seleccionar(copia.id);
    };
    ed.eliminar = (id) => {
      const info = ed.indice.get(id);
      if (!info || !info.lista) return;
      if (info.tipo === 'capa' && ['fondo', 'frente'].includes(id)) return;
      if (info.tipo === 'pagina') { eliminarPagina(info); return; }
      const nombre = nombreNodo(info);
      info.lista.splice(info.i, 1);
      const vecino = info.lista[Math.min(info.i, info.lista.length - 1)];
      ed.sel = vecino ? vecino.id : (info.padre ? info.padre.id : null);
      avisar(`«${nombre}» borrado`, { accion: { texto: 'Deshacer', fn: () => ed.deshacer() } });
    };
    ed.desplazar = (id, delta) => {
      const info = ed.indice.get(id);
      if (!info || !info.lista) return;
      if (info.tipo === 'fila' && info.pagina) {           // dentro de su diapositiva
        const suyas = info.lista.filter((f) => f.pag === info.obj.pag);
        const otra = suyas[suyas.indexOf(info.obj) + delta];
        if (!otra) return;
        const a = info.i, b = info.lista.indexOf(otra);
        [info.lista[a], info.lista[b]] = [info.lista[b], info.lista[a]];
        return;
      }
      const d = info.tipo === 'item' ? -delta : delta;      // las capas se ven de arriba (delante) a abajo
      const j = info.i + d;
      if (j < 0 || j >= info.lista.length) return;
      const [o] = info.lista.splice(info.i, 1);
      info.lista.splice(j, 0, o);
    };
    const HIJOS = { fila: 'columnas', columna: 'bloques', bloque: 'elementos', capa: 'elementos' };
    ed.moverNodo = (origen, destino, pos) => {
      const io = ed.indice.get(origen), id = ed.indice.get(destino);
      if (!io || !id || origen === destino) return;
      let lista, indice;
      if (io.tipo === 'fila' && id.tipo === 'pagina') {     // una fila que cambia de diapositiva
        io.obj.pag = id.obj.id;
        ed.abiertos.add(id.obj.id);
        ed.seleccionar(origen);
        return;
      }
      if (io.tipo === 'fila' && id.tipo === 'fila' && id.obj.pag) io.obj.pag = id.obj.pag;
      if (pos === 'dentro') {
        lista = id.obj[HIJOS[id.tipo]];
        if (!lista) return;
        indice = lista.length;
      } else {
        lista = id.lista;
        const invertido = id.tipo === 'item';
        indice = id.i + ((pos === 'despues') !== invertido ? 1 : 0);
      }
      mover(io.lista, io.i, lista, indice);
      ed.seleccionar(origen);
    };
    ed.moverItemACapa = (itemId, capaId) => {
      const info = ed.indice.get(itemId), capa = ed.indice.get(capaId)?.obj;
      if (!info || !capa || info.capa === capa) return;
      const [it] = info.lista.splice(info.i, 1);
      capa.elementos.push(it);
      ed.abiertos.add(capa.id);
    };
    ed.usarImagen = (ruta) => {
      const info = ed.indice.get(ed.sel);
      if (info && info.tipo === 'elemento') {
        const campos = camposImagen(info.obj);
        if (campos.length) {
          const vacio = campos.find((c) => !info.obj[c]) || campos[0];
          info.obj[vacio] = ruta;
          avisar('Imagen colocada en el elemento');
          return;
        }
      }
      if (info && info.tipo === 'item' && info.obj.tipo === 'imagen') { info.obj.archivo = ruta; return; }
      if (info && info.tipo === 'capa') {
        const it = nuevoItem('imagen');
        Object.assign(it, { archivo: ruta, ancho: 0.3 });
        info.obj.elementos.push(it);
        ed.abiertos.add(info.obj.id);
        ed.seleccionar(it.id);
        return;
      }
      const bloque = info && info.tipo === 'bloque' ? info.obj : info && info.tipo === 'elemento' ? info.bloque : null;
      if (bloque) {
        const e = nuevoElemento('imgAncho');
        e.archivo = ruta;
        if (info.tipo === 'elemento') bloque.elementos.splice(info.i + 1, 0, e); else bloque.elementos.push(e);
        ed.abiertos.add(bloque.id);
        ed.seleccionar(e.id);
        avisar('Imagen añadida a la caja');
        return;
      }
      if (info && info.tipo === 'cabecera') {
        const c = ed.modelo.cabecera;
        if (!c.logo_izquierdo) c.logo_izquierdo = ruta; else c.logo_derecho = ruta;
        return;
      }
      if (!ed.flujo && (!info || ['pagina', 'poster'].includes(info.tipo)) && ((ed.pagActual() || ed.modelo.lienzo).libre)) {
        ed.agregarLibre('imagen');
        ed.indice.get(ed.sel).obj.elementos[0].archivo = ruta;
        return;
      }
      avisar('Selecciona primero una caja, un elemento con imagen o una capa (en «Estructura» o en la vista previa).');
    };
    // Mover y escalar elementos de capa desde la vista previa
    ed.moverItem = (id, dxPt, dyPt, papel) => {
      const it = ed.indice.get(id)?.obj;
      if (!it || !papel) return;
      const fx = aFraccion(it.x, papel.ancho) ?? 0.5, fy = aFraccion(it.y, papel.alto) ?? 0.5;
      it.x = redondear(fx + dxPt / papel.ancho);
      it.y = redondear(fy + dyPt / papel.alto);
      if (it.tipo === 'forma' && ['linea', 'flecha'].includes(it.forma)) {
        const fx2 = aFraccion(it.x2, papel.ancho) ?? 0.6, fy2 = aFraccion(it.y2, papel.alto) ?? fy;
        it.x2 = redondear(fx2 + dxPt / papel.ancho);
        it.y2 = redondear(fy2 + dyPt / papel.alto);
      }
    };
    ed.empujarItem = (id, dx, dy) => {
      const papel = ed.compilacion && ed.compilacion.posiciones && ed.compilacion.posiciones.papel;
      if (!papel) return;
      ed.moverItem(id, dx * papel.ancho, dy * papel.alto, papel);
    };
    ed.escalarItem = (id, f) => {
      const info = ed.indice.get(id);
      if (info && info.tipo === 'logo') {              // tamaño del logo en %, de 5 en 5
        const o = info.obj, antes = Number(o[info.clave]) || 100;
        o[info.clave] = Math.min(300, Math.max(30, Math.round((antes * f) / 5) * 5));
        return;
      }
      const it = info?.obj;
      const pos = ed.compilacion && ed.compilacion.posiciones;
      if (!it || !pos || !pos.papel) return;
      const papel = pos.papel;
      const escalar = (v, ref) => { const fr = aFraccion(v, ref); return fr == null ? null : redondear(fr * f); };
      let hecho = false;
      if (info.tipo === 'bloque') {                     // caja suelta: cambia el ancho (y el alto si es fijo)
        const antes = aFraccion(it.ancho, papel.ancho) ?? (pos.cajas[id] ? (pos.cajas[id].x1 - pos.cajas[id].x0) / papel.ancho : 0.3);
        it.ancho = redondear(Math.min(1, Math.max(0.03, antes * f)));
        if (it.alto !== '' && it.alto != null) { const v = escalar(it.alto, papel.alto); if (v != null) it.alto = v; }
        return;
      }
      if (it.tipo === 'texto') { it.escala = redondear((Number(it.escala) || 1) * f, 2); hecho = true; }
      if (it.ancho !== '' && it.ancho != null) { const v = escalar(it.ancho, papel.ancho); if (v != null) { it.ancho = v; hecho = true; } }
      if (it.alto !== '' && it.alto != null) { const v = escalar(it.alto, papel.alto); if (v != null) { it.alto = v; hecho = true; } }
      if (!hecho && pos.cajas[id]) { const c = pos.cajas[id]; it.ancho = redondear((c.x1 - c.x0) / papel.ancho * f); }
    };

    // ------------------------------------------------ proyecto
    ed.renombrar = async (nombre) => {
      nombre = String(nombre || '').trim();
      if (!nombre || nombre === ed.meta.nombre) return;
      try { const m = await patch(`api/proyectos/${pid}`, { nombre }); ed.meta.nombre = m.nombre; document.title = `${m.nombre} · DocsLab`; } catch (e) { avisarError(e); }
    };
    ed.alternarAuto = async () => {
      const v = !(ed.meta.ajustes.auto_compilar !== false);
      try { const m = await patch(`api/proyectos/${pid}`, { ajustes: { auto_compilar: v } }); ed.meta.ajustes = m.ajustes; avisar(v ? 'Se compilará solo al guardar' : 'Compila con el botón o con Ctrl + S'); } catch (e) { avisarError(e); }
    };
    ed.comoPlantilla = async () => {
      ed.menu = null;
      const nombre = await preguntar({ titulo: 'Guardar como plantilla nueva', texto: 'Copia el diseño, el contenido, las imágenes y los cuadernos. Aparecerá en la pantalla de inicio.', etiqueta: 'Nombre de la plantilla', valor: ed.meta.nombre, aceptar: 'Guardar plantilla' });
      if (!nombre) return;
      try {
        await ed.compilarAhora();
        const t = await post('api/plantillas', { proyecto: pid, nombre });
        ed.plantillaPropia = { id: t.id, nombre: t.nombre };
        avisar(`Plantilla «${t.nombre}» guardada`);
      } catch (e) { avisarError(e); }
    };
    ed.actualizarPlantilla = async () => {
      ed.menu = null;
      const t = ed.plantillaPropia;
      if (!t) return;
      const ok = await confirmar({
        titulo: `¿Actualizar la plantilla «${t.nombre}»?`,
        texto: 'Su contenido pasa a ser el de este documento: diseño, textos, imágenes y cuadernos. Conserva su nombre y su descripción. Los documentos que ya se crearon con ella no cambian.',
        aceptar: 'Actualizar la plantilla',
      });
      if (!ok) return;
      try {
        await ed.compilarAhora();
        const r = await put(`api/plantillas/${t.id}`, { proyecto: pid });
        ed.plantillaPropia = { id: r.id, nombre: r.nombre };
        avisar(`Plantilla «${r.nombre}» actualizada`);
      } catch (e) { avisarError(e); }
    };
    ed.duplicarProyecto = async () => {
      ed.menu = null;
      try { const p = await post(`api/proyectos/${pid}/duplicar`); avisar('Proyecto duplicado', { accion: { texto: 'Abrir', fn: () => ir(`#/p/${p.id}`) } }); } catch (e) { avisarError(e); }
    };
    ed.convertirLatex = async () => {
      ed.menu = null;
      const ok = await confirmar({
        titulo: '¿Convertir en proyecto LaTeX?',
        texto: 'Podrás editar el código a mano, pero el editor visual dejará de estar disponible para este proyecto. Si quieres conservar las dos cosas, duplica antes el proyecto.',
        aceptar: 'Convertir',
      });
      if (!ok) return;
      try {
        await guardarAhora();
        await post(`api/proyectos/${pid}/convertir-latex`);
        location.reload();
      } catch (e) { avisarError(e); }
    };
    ed.cambiarFormato = async (nuevo) => {
      if (!ed.modelo || ed.modelo.formato_texto === nuevo) return;
      const ok = await confirmar({
        titulo: nuevo === 'latex' ? '¿Escribir los textos en código LaTeX?' : '¿Volver al texto con formato sencillo?',
        texto: nuevo === 'latex'
          ? 'Todos los textos se convierten a su código LaTeX (por ejemplo, **negrita** pasa a \\textbf{negrita}). Desde ahora escribe \\% para el porcentaje y $...$ para las fórmulas.'
          : 'Los textos con órdenes de LaTeX se conservan tal cual dentro de {{ }}, así que el documento no cambia.',
        aceptar: 'Convertir los textos',
      });
      if (!ok) return;
      try {
        historiaPronto.cancelar(); confirmarHistoria();
        await guardarAhora();
        const r = await post(`api/proyectos/${pid}/formato`, { formato: nuevo });
        pila.push(instantanea); futuro = [];
        ignorar = true; ed.modelo = r.modelo; ignorar = false;
        instantanea = ultimoGuardado = JSON.stringify(r.modelo);
        botones();
        ed.estado = 'guardado';
        compilarPronto();
      } catch (e) { avisarError(e); }
    };
    ed.restaurarVersion = async (nombre) => {
      ed.dialogo = null;
      try {
        historiaPronto.cancelar(); confirmarHistoria();
        const r = await post(`api/proyectos/${pid}/historial/${encodeURIComponent(nombre)}/restaurar`);
        pila.push(instantanea); futuro = [];
        ignorar = true; ed.modelo = r.modelo; ignorar = false;
        instantanea = ultimoGuardado = JSON.stringify(r.modelo);
        botones();
        avisar('Versión restaurada');
        compilarPronto();
      } catch (e) { avisarError(e); }
    };
    // Componente Lab
    ed.abrirEnLab = async (cid) => {
      try {
        await guardarAhora();
        const lista = await cargarBiblioteca();
        if (!lista.some((x) => x.id === cid)) {
          const c = (ed.modelo.componentes || {})[cid];
          if (!c) return;
          await post('api/componentes', { componente: c, conservar_id: true });
          avisar(`«${c.nombre}» se copió a tu biblioteca del Lab`);
        }
        tienda.volverA = `#/p/${pid}`;
        ir(`#/lab/${cid}`);
      } catch (e) { avisarError(e); }
    };
    ed.ponerAlDia = async (cid) => {
      try {
        const c = await ed.traerComponente(cid);
        // los usos que no tengan un campo nuevo toman su valor inicial
        for (const info of ed.indice.values()) {
          if (info.tipo !== 'elemento' || info.obj.tipo !== `cmp:${cid}`) continue;
          for (const campo of c.campos || []) if (!(campo.nombre in info.obj)) info.obj[campo.nombre] = clonar(campo.defecto ?? '');
        }
      } catch (e) { avisarError(e); }
    };
    // Ajustar a una página: el servidor busca la letra más grande con la que cabe
    ed.ajustarPagina = async () => {
      ed.menu = null;
      if (ed.ajustando || !ed.modelo) return;
      try {
        historiaPronto.cancelar(); confirmarHistoria();
        await guardarAhora();
        ed.ajustando = { mensaje: 'Midiendo…', progreso: 0.02, id: null };
        const t = await post(`api/proyectos/${pid}/ajustar`);
        ed.ajustando.id = t.id;
        const fin = await esperarTrabajo(t.id, { intervalo: 500, alCambiar: (x) => { if (ed.ajustando) Object.assign(ed.ajustando, { mensaje: x.mensaje || ed.ajustando.mensaje, progreso: x.progreso }); } });
        ed.ajustando = null;
        if (fin.estado === 'cancelado') { avisar('Ajuste cancelado'); return; }
        if (fin.estado === 'error') { avisar(fin.mensaje || 'No se pudo ajustar', { tipo: 'error', ms: 8000 }); return; }
        const r = fin.resultado;
        if (!r) return;
        if (r.ya_cabia) { avisar(ed.clase === 'presentacion' ? 'Todas las diapositivas caben ya.' : 'El póster ya cabe en una página.'); return; }
        if (!r.cabe) {
          avisar(`No cabe ni con la letra a ${r.minima} pt: reduce imágenes o quita contenido.`, { tipo: 'error', ms: 9000 });
          return;
        }
        ed.modelo.tipografia.fuente = r.fuente;
        avisar(`Letra de ${r.antes} pt a ${r.fuente} pt: ya cabe`, { ms: 8000, accion: { texto: 'Deshacer', fn: () => ed.deshacer() } });
      } catch (e) { ed.ajustando = null; avisarError(e); }
    };
    ed.cancelarAjuste = async () => {
      const id = ed.ajustando && ed.ajustando.id;
      if (id) { try { await post(`api/trabajos/${id}/cancelar`); } catch (e) { avisarError(e); } }
    };
    // Revisión para imprimir: señalar en la vista previa lo que dice cada comprobación
    ed.mostrarEnPoster = (it) => {
      if (it.elemento && ed.indice.get(it.elemento)) ed.seleccionar(it.elemento, { desdeVista: true });
      let zona = it.zona || null;
      const caja = !zona && it.elemento && ed.compilacion && ed.compilacion.posiciones && ed.compilacion.posiciones.cajas[it.elemento];
      const papel = ed.compilacion && ed.compilacion.posiciones && ed.compilacion.posiciones.papel;
      if (caja && papel) zona = { pagina: caja.pagina || 1, x0: caja.x0 / papel.ancho, y0: caja.y0 / papel.alto, x1: caja.x1 / papel.ancho, y1: caja.y1 / papel.alto };
      if (zona) ed.resaltado = { zona, clave: Date.now() };
    };
    ed.recargarCompilacion = async () => {
      try {
        const c = await api(`api/proyectos/${pid}/compilacion`);
        if (c && c.version !== ed.version) { ed.compilacion = c; ed.version = c.version; }
      } catch (e) { avisarError(e); }
    };
    ed.descargar = (que) => {
      ed.menu = null;
      const rutas = { pdf: `api/proyectos/${pid}/pdf?descargar=1`, overleaf: `api/proyectos/${pid}/exportar?tipo=overleaf`, proyecto: `api/proyectos/${pid}/exportar?tipo=proyecto` };
      if (que === 'pdf' && !(ed.compilacion && ed.compilacion.ok)) {
        avisar('Todavía no hay un PDF correcto: compila primero.', { tipo: 'error' });
        return;
      }
      descargar(rutas[que]);
    };

    provide('ed', ed);

    // ------------------------------------------------ teclado y salida
    function tecla(ev) {
      const mod = ev.ctrlKey || ev.metaKey;
      if (!mod) return;
      const k = ev.key.toLowerCase();
      if (k === 's') { ev.preventDefault(); ed.compilarAhora(); return; }
      const t = ev.target;
      const escribiendo = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable || t.closest('.CodeMirror'));
      if (escribiendo || !ed.modelo || ed.vistaLab) return;
      if (k === 'z' && !ev.shiftKey) { ev.preventDefault(); ed.deshacer(); }
      else if ((k === 'z' && ev.shiftKey) || k === 'y') { ev.preventDefault(); ed.rehacer(); }
    }
    function antesDeSalir(ev) {
      if (['cambios', 'guardando', 'error'].includes(ed.estado)) { ev.preventDefault(); ev.returnValue = ''; }
    }
    function cerrarMenus(ev) { if (!ev.target.closest('.menu-contenedor')) ed.menu = null; }
    onMounted(() => {
      cargar();
      cargarBiblioteca();
      window.addEventListener('keydown', tecla);
      window.addEventListener('beforeunload', antesDeSalir);
      document.addEventListener('mousedown', cerrarMenus);
      document.addEventListener('focusin', alEnfocar);
    });
    onBeforeUnmount(() => {
      window.removeEventListener('keydown', tecla);
      window.removeEventListener('beforeunload', antesDeSalir);
      document.removeEventListener('mousedown', cerrarMenus);
      document.removeEventListener('focusin', alEnfocar);
      if (guardarPronto.pendiente()) guardarPronto.ya();
      document.title = 'DocsLab';
    });

    const chip = computed(() => {
      if (ed.compilando) return { clase: 'trabajando', texto: 'Compilando' };
      if (ed.estado === 'guardando') return { clase: 'trabajando', texto: 'Guardando' };
      if (ed.estado === 'cambios') return { clase: 'aviso-chip', texto: 'Cambios sin guardar' };
      if (ed.estado === 'error') return { clase: 'error', texto: 'No se pudo guardar' };
      const c = ed.compilacion;
      if (c && c.errores && c.errores.length) return { clase: 'error', texto: `${c.errores.length} ${c.errores.length === 1 ? 'error' : 'errores'} de LaTeX` };
      const visual = ed.meta && ed.meta.tipo === 'estructurado';
      if (c && visual && ed.clase === 'poster' && c.paginas > 1) return { clase: 'aviso-chip', texto: `Ocupa ${c.paginas} páginas`, ajustar: true };
      const largas = (c && visual && ed.clase === 'presentacion' && c.diapositivas_largas) || [];
      if (largas.length) return { clase: 'aviso-chip', texto: largas.length === 1 ? 'Una diapositiva no cabe' : `${largas.length} diapositivas no caben`, ajustar: true, ir: largas[0] };
      if (c && visual && !ed.flujo && (c.avisos || []).some((a) => /no cabe/.test(a.mensaje))) return { clase: 'aviso-chip', texto: 'Algo no cabe', ajustar: true };
      return { clase: 'ok', texto: 'Guardado' };
    });
    const pestanas = [
      { clave: 'estructura', nombre: 'Estructura', icono: 'capas' },
      { clave: 'imagenes', nombre: 'Imágenes', icono: 'imagen' },
      { clave: 'referencias', nombre: 'Referencias', icono: 'libro' },
    ];
    return { ed, chip, logo: LOGO, tienda, recortar, pestanas };
  },
  methods: {
    irAError(e) {
      if (e.elemento && this.ed.indice.get(e.elemento)) this.ed.seleccionar(e.elemento, { desdeVista: true });
      else avisar('El error está en el código generado; revisa el elemento que cambiaste por última vez o mira «Ver el código LaTeX».');
    },
    alternarMenu(m) { this.ed.menu = this.ed.menu === m ? null : m; },
    verLab(v) { this.ed.vistaLab = v; if (v) this.ed.labAbierto = true; },
  },
  template: `
  <div class="editor" :class="{'con-revision': ed.revision}" v-if="ed.meta">
    <header class="barra">
      <a class="marca" href="#/" title="Volver a tus documentos"><span v-html="logo"></span><span class="solo-ancho">DocsLab</span></a>
      <span class="divisor"></span>
      <input class="titulo-proyecto" :value="ed.meta.nombre" @change="ed.renombrar($event.target.value)" @keydown.enter="$event.target.blur()" aria-label="Nombre del proyecto" :size="Math.min(40, Math.max(8, ed.meta.nombre.length))">
      <div class="segmentos sin-cortes cambio-vista" role="tablist" aria-label="Documento o LAB">
        <button role="tab" :aria-selected="!ed.vistaLab" :class="{activo: !ed.vistaLab}" @click="verLab(false)" :title="'Editar ' + ed.articulo">{{ ed.nombreClase }}</button>
        <button role="tab" :aria-selected="ed.vistaLab" :class="{activo: ed.vistaLab}" @click="verLab(true)" title="Cuadernos de Python y plantillas de gráficos de este documento">LAB</button>
      </div>
      <span class="chip" :class="chip.clase" role="status"><span class="punto"></span>{{ chip.texto }}</span>
      <button v-if="chip.ir && !ed.compilando" class="btn pequeno" @click="ed.seleccionar(chip.ir)">Ver cuál</button>
      <button v-if="chip.ajustar && !ed.ajustando && !ed.compilando" class="btn pequeno" @click="ed.ajustarPagina()" :title="ed.clase === 'presentacion' ? 'Busca el tamaño de letra más grande con el que cada diapositiva cabe en su página' : 'Busca el tamaño de letra más grande con el que todo cabe en una página'"><icono n="encajar"/><span class="solo-ancho">{{ ed.clase === 'presentacion' ? 'Ajustar la letra' : 'Ajustar a una página' }}</span></button>
      <span v-if="ed.ajustando" class="chip trabajando" role="status"><span class="punto"></span>{{ ed.ajustando.mensaje }}
        <button type="button" class="cerrar-chip" @click="ed.cancelarAjuste()" aria-label="Cancelar el ajuste" title="Cancelar">×</button></span>
      <span class="espacio"></span>
      <template v-if="ed.modelo && !ed.vistaLab">
        <button class="btn icono fantasma" @click="ed.deshacer()" :disabled="!ed.puedeDeshacer" title="Deshacer (Ctrl + Z)" aria-label="Deshacer"><icono n="deshacer"/></button>
        <button class="btn icono fantasma" @click="ed.rehacer()" :disabled="!ed.puedeRehacer" title="Rehacer (Ctrl + Mayús + Z)" aria-label="Rehacer"><icono n="rehacer"/></button>
        <span class="divisor solo-ancho"></span>
        <button class="btn icono fantasma" :class="{activo: ed.verIzq}" @click="ed.verIzq = !ed.verIzq" title="Panel de estructura" aria-label="Mostrar u ocultar el panel izquierdo"><icono n="panel-izq"/></button>
        <button class="btn icono fantasma" :class="{activo: ed.verDer}" @click="ed.verDer = !ed.verDer" title="Inspector" aria-label="Mostrar u ocultar el inspector"><icono n="panel-der"/></button>
      </template>
      <button class="btn primario" @click="ed.compilarAhora()" :disabled="ed.compilando" title="Guardar y compilar (Ctrl + S)"><icono n="compilar"/><span class="solo-ancho">{{ ed.compilando ? 'Compilando…' : 'Compilar' }}</span></button>
      <div class="menu-contenedor">
        <button class="btn" @click="alternarMenu('descargar')" aria-haspopup="true" :aria-expanded="ed.menu === 'descargar'"><icono n="descargar"/><span class="solo-ancho">Descargar</span></button>
        <div class="menu" v-if="ed.menu === 'descargar'">
          <button @click="ed.menu = null; ed.revision = true"><icono n="revisar"/>Revisar para imprimir…</button>
          <button @click="ed.menu = null; ed.dialogo = 'imprenta'"><icono n="imprenta"/>PDF para imprenta…</button>
          <div class="separador"></div>
          <button @click="ed.descargar('pdf')"><icono n="hoja"/>PDF</button>
          <button @click="ed.menu = null; ed.dialogo = 'powerpoint'"><icono n="diapositiva"/>PowerPoint (.pptx)…</button>
          <button @click="ed.descargar('overleaf')"><icono n="archivo"/>Zip para Overleaf</button>
          <button @click="ed.descargar('proyecto')"><icono n="carpeta"/>Zip del proyecto (copia de seguridad)</button>
          <p class="nota">El zip para Overleaf trae el .tex, la plantilla y solo las imágenes que se usan.</p>
        </div>
      </div>
      <div class="menu-contenedor">
        <button class="btn icono" @click="alternarMenu('mas')" aria-label="Más opciones" aria-haspopup="true" :aria-expanded="ed.menu === 'mas'"><icono n="puntos"/></button>
        <div class="menu" v-if="ed.menu === 'mas'">
          <button @click="ed.alternarAuto()"><icono :n="ed.meta.ajustes.auto_compilar !== false ? 'check' : 'compilar'"/>{{ ed.meta.ajustes.auto_compilar !== false ? 'Compilar solo al guardar: sí' : 'Compilar solo al guardar: no' }}</button>
          <button @click="ed.comoPlantilla()"><icono n="plantilla"/>Guardar como plantilla nueva</button>
          <button v-if="ed.plantillaPropia" @click="ed.actualizarPlantilla()" :title="'Actualizar la plantilla «' + ed.plantillaPropia.nombre + '» con este documento'"><icono n="plantilla"/>Actualizar la plantilla «{{ recortar(ed.plantillaPropia.nombre) }}»</button>
          <button v-if="ed.modelo && !ed.flujo" @click="ed.ajustarPagina()" :disabled="!!ed.ajustando"><icono n="encajar"/>{{ ed.clase === 'presentacion' ? 'Ajustar la letra a las diapositivas' : 'Ajustar a una página' }}</button>
          <button @click="ed.duplicarProyecto()"><icono n="duplicar"/>Duplicar el proyecto</button>
          <template v-if="ed.modelo">
            <button @click="ed.menu = null; ed.dialogo = 'historial'"><icono n="historial"/>Versiones anteriores</button>
            <button @click="ed.menu = null; ed.dialogo = 'codigo'"><icono n="codigo"/>Ver el código LaTeX</button>
            <div class="separador"></div>
            <button @click="ed.convertirLatex()"><icono n="codigo"/>Convertir en proyecto LaTeX</button>
          </template>
          <div class="separador"></div>
          <a href="#/"><icono n="casa"/>Volver a tus documentos</a>
        </div>
      </div>
    </header>

    <div v-if="ed.modelo" v-show="!ed.vistaLab" class="cuerpo-editor" :class="{'sin-izq': !ed.verIzq, 'sin-der': !ed.verDer}">
      <aside class="panel izq" v-show="ed.verIzq" aria-label="Estructura, imágenes y referencias">
        <div class="pestanas" role="tablist">
          <button v-for="p in pestanas" :key="p.clave" role="tab" :aria-selected="ed.panelIzq === p.clave" :class="{activo: ed.panelIzq === p.clave}"
                  @click="ed.panelIzq = p.clave" :title="p.nombre" :aria-label="p.nombre"><icono :n="p.icono"/><span class="nombre-pestana">{{ p.nombre }}</span></button>
        </div>
        <div class="contenido-panel">
          <keep-alive>
            <arbol-estructura v-if="ed.panelIzq === 'estructura'"/>
            <panel-recursos v-else-if="ed.panelIzq === 'imagenes'"/>
            <panel-referencias v-else/>
          </keep-alive>
        </div>
        <div class="pie-panel" v-if="ed.panelIzq === 'estructura' && ed.flujo">
          <button class="btn pequeno" @click="ed.agregarSeccion(1)"><icono n="mas"/>{{ ed.clase === 'tesis' ? 'Capítulo' : 'Sección' }}</button>
          <button class="btn pequeno" @click="ed.agregarSeccion(2)"><icono n="mas"/>{{ ed.clase === 'tesis' ? 'Sección' : 'Subsección' }}</button>
        </div>
        <div class="pie-panel" v-else-if="ed.panelIzq === 'estructura'">
          <div class="menu-contenedor" v-if="ed.clase === 'presentacion'">
            <button class="btn pequeno primario" @click="alternarMenu('pagina')" aria-haspopup="true" :aria-expanded="ed.menu === 'pagina'"><icono n="diapositiva"/>Diapositiva</button>
            <div class="menu arriba" v-if="ed.menu === 'pagina'">
              <button @click="ed.menu = null; ed.agregarPagina('contenido')"><icono n="diapositiva"/>Título y contenido</button>
              <button @click="ed.menu = null; ed.agregarPagina('seccion')"><icono n="titulo"/>Título de sección</button>
              <button @click="ed.menu = null; ed.agregarPagina('vacia')"><icono n="hoja"/>En blanco</button>
              <button @click="ed.menu = null; ed.agregarPagina('portada')"><icono n="cabecera"/>Portada</button>
            </div>
          </div>
          <button class="btn pequeno" @click="ed.agregarFila()"><icono n="fila"/>Fila</button>
          <div class="menu-contenedor">
            <button class="btn pequeno" @click="alternarMenu('suelto')" aria-haspopup="true" :aria-expanded="ed.menu === 'suelto'" title="Añade algo que se coloca arrastrándolo, fuera de la cuadrícula"><icono n="arrastrar"/>Suelto</button>
            <div class="menu arriba" v-if="ed.menu === 'suelto'">
              <button @click="ed.menu = null; ed.agregarLibre('texto')"><icono n="texto"/>Texto suelto</button>
              <button @click="ed.menu = null; ed.agregarLibre('imagen')"><icono n="imagen"/>Imagen suelta</button>
              <button @click="ed.menu = null; ed.agregarLibre('caja')"><icono n="caja"/>Caja suelta con título</button>
              <p class="nota">Lo suelto se arrastra en la vista previa a cualquier punto de la página.</p>
            </div>
          </div>
          <div class="menu-contenedor">
            <button class="btn pequeno" @click="alternarMenu('capa')" aria-haspopup="true" :aria-expanded="ed.menu === 'capa'"><icono n="capas"/>Capa</button>
            <div class="menu arriba" v-if="ed.menu === 'capa'">
              <button @click="ed.menu = null; ed.agregarCapa(true)"><icono n="capas"/>Capa delante del contenido</button>
              <button @click="ed.menu = null; ed.agregarCapa(false)"><icono n="capas"/>Capa detrás del contenido</button>
            </div>
          </div>
        </div>
      </aside>

      <vista-pdf :url="ed.urlPdf" :version="ed.version" :posiciones="ed.compilacion && ed.compilacion.posiciones"
                 :seleccion="ed.sel" :nombres="ed.nombre" :tipos="ed.tipo" :compilando="ed.compilando"
                 :aviso="ed.compilacion && !ed.compilacion.ok && ed.compilacion.pdf_anterior ? 'Se ve la última versión que compiló bien' : ''"
                 @seleccionar="(id) => ed.seleccionar(id, {desdeVista: true})" @mover="ed.moverItem" @escalar="ed.escalarItem" @empujar="ed.empujarItem"
                 :resaltado="ed.resaltado" @arrastrar="ed.arrastrar" @editar="ed.editarEnVista"
                 :ir-a="ed.irPagina" :reordenable="!ed.flujo" :zoom-inicial="ed.flujo ? 'ancho' : 'ajustar'" @pagina="(n) => ed.paginaVista = n">
        <template #capa="{ k, pagina }"><edicion-directa :k="k" :pagina="pagina"/></template>
        <template #pie><panel-registro :compilacion="ed.compilacion" :nombres="ed.nombre" :ajustando="!!ed.ajustando" @ir="irAError" @ajustar="ed.ajustarPagina()"/></template>
      </vista-pdf>

      <aside class="panel der" v-show="ed.verDer" aria-label="Inspector">
        <div class="contenido-panel"><inspector-editor/></div>
      </aside>
    </div>

    <cuerpo-latex v-else-if="ed.meta.tipo === 'latex'" v-show="!ed.vistaLab"/>
    <lab-documento v-if="ed.labAbierto" v-show="ed.vistaLab"/>

    <selector-variantes v-if="ed.dialogoVariantes" :titulo="ed.dialogoVariantes.reemplazar ? 'Cambiar la variante del elemento' : 'Añadir un elemento a la caja'"
                        :actual="ed.dialogoVariantes.reemplazar && ed.indice.get(ed.dialogoVariantes.reemplazar) ? ed.indice.get(ed.dialogoVariantes.reemplazar).obj.tipo : ''"
                        :con-propios="!ed.dialogoVariantes.reemplazar"
                        @elegir="ed.elegirVariante" @cerrar="ed.dialogoVariantes = null"/>
    <dialogo-historial v-if="ed.dialogo === 'historial'" :pid="ed.pid" @restaurar="ed.restaurarVersion" @cerrar="ed.dialogo = null"/>
    <dialogo-codigo v-if="ed.dialogo === 'codigo'" :pid="ed.pid" @cerrar="ed.dialogo = null"/>
    <dialogo-imprenta v-if="ed.dialogo === 'imprenta'" @cerrar="ed.dialogo = null"/>
    <dialogo-powerpoint v-if="ed.dialogo === 'powerpoint'" @cerrar="ed.dialogo = null"/>
    <panel-revision v-if="ed.revision" @cerrar="ed.revision = false" @imprenta="ed.dialogo = 'imprenta'"/>
  </div>
  <div v-else class="arranque"><p>Abriendo el proyecto…</p></div>`,
};
