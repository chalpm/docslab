// SPDX-License-Identifier: AGPL-3.0-only
// Pantalla de inicio: pósters, plantillas, asistente y zips.
import { api, post, patch, put, borrar, subir, descargar } from './api.js';
import { tienda, avisar, avisarError, confirmar, preguntar, ir } from './tienda.js';
import { fecha, aMm, recortar } from './util.js';
import { svgPoster, svgCaja, svgCabecera, svgDiapositiva, svgDocumento, NOMBRES_ESTILO, NOMBRES_CABECERA } from './dibujos.js';
import { NOMBRES_CLASE, ARTICULO_CLASE } from './modeloed.js';

const CLASES = [
  { clave: 'poster', nombre: 'Póster', nota: 'Una hoja grande con filas, columnas y cajas', nuevo: 'Póster nuevo', tamano: 'A0' },
  { clave: 'presentacion', nombre: 'Presentación', nota: 'Diapositivas, cada una con su cuadrícula', nuevo: 'Presentación nueva', tamano: '16:9' },
  { clave: 'documento', nombre: 'Documento', nota: 'Informe, guía o reporte con secciones', nuevo: 'Documento nuevo', tamano: 'A4' },
  { clave: 'paper', nombre: 'Artículo', nota: 'Resumen, secciones y referencias; a una o dos columnas', nuevo: 'Artículo nuevo', tamano: 'A4' },
  { clave: 'tesis', nombre: 'Tesis', nota: 'Portada, índice, capítulos y apéndices', nuevo: 'Tesis nueva', tamano: 'A4' },
];
const PLURAL_CLASE = { poster: 'Pósters', presentacion: 'Presentaciones', documento: 'Documentos', paper: 'Artículos', tesis: 'Tesis' };
import { CTema } from './campos.js';

export const HojaMini = {
  name: 'hoja-mini',
  props: { src: String, proporcion: { type: Number, default: 841 / 1189 }, etiqueta: String },
  data: () => ({ fallo: false }),
  watch: { src() { this.fallo = false; } },
  computed: {
    estiloVacio() {
      const alto = 190, ancho = Math.min(176, alto * this.proporcion);
      return { width: `${Math.round(ancho)}px`, height: `${Math.round(ancho / this.proporcion)}px` };
    },
  },
  template: `
    <div class="hoja-mini" :style="src && !fallo ? null : estiloVacio">
      <img v-if="src && !fallo" :src="src" alt="" loading="lazy" @error="fallo = true">
      <div v-else class="sin-imagen">Sin vista previa</div>
      <div class="marcas-corte"><i></i><i></i><i></i><i></i></div>
      <span v-if="etiqueta" class="etiqueta-papel">{{ etiqueta }}</span>
    </div>`,
};

const Asistente = {
  name: 'asistente-nuevo',
  components: { CTema },
  emits: ['cerrar'],
  data() {
    return {
      clase: 'poster', nombre: 'Póster nuevo', tamano: 'A0', orientacion: 'vertical', columnas: 3, tema: 'pizarra',
      familia: 'helvetica', idioma: 'es', estilo_bloque: 'barra', cabecera: 'banda', creando: false,
      columnasTexto: 1, tituloDiapositiva: 'banda', clases: CLASES,
    };
  },
  computed: {
    cat() { return tienda.catalogo; },
    colores() { return this.cat ? this.cat.temas[this.tema] : null; },
    esPoster() { return this.clase === 'poster'; },
    esDiapos() { return this.clase === 'presentacion'; },
    esFlujo() { return ['documento', 'paper', 'tesis'].includes(this.clase); },
    def() { return CLASES.find((c) => c.clave === this.clase); },
    tamanos() { return (this.cat && this.cat.clases && this.cat.clases[this.clase] ? this.cat.clases[this.clase].tamanos : Object.keys((this.cat || {}).tamanos || {})); },
    dims() {
      const t = (this.cat && this.cat.tamanos[this.tamano]) || ['841mm', '1189mm'];
      let a = aMm(t[0]) || 841, b = aMm(t[1]) || 1189;
      if (this.esDiapos || (this.esPoster && this.orientacion === 'horizontal')) [a, b] = [Math.max(a, b), Math.min(a, b)];
      else [a, b] = [Math.min(a, b), Math.max(a, b)];
      return { ancho: a, alto: b };
    },
    previa() {
      if (!this.colores) return '';
      if (this.esDiapos) return svgDiapositiva({ ...this.dims, colores: this.colores, titulo: this.tituloDiapositiva });
      if (this.esFlujo) return svgDocumento({ ...this.dims, colores: this.colores, columnas: this.clase === 'paper' ? this.columnasTexto : 1, clase: this.clase });
      return svgPoster({ ...this.dims, columnas: this.columnas, colores: this.colores, estiloCaja: this.estilo_bloque, cabecera: this.cabecera });
    },
    articulo() { return ARTICULO_CLASE[this.clase]; },
    estiloPrevia() {
      const r = this.dims.ancho / this.dims.alto;
      const alto = r < 1 ? 280 : Math.round(210 / r);
      return { width: `${Math.round(alto * r)}px`, height: `${alto}px` };
    },
  },
  methods: {
    svgCaja(e) { return svgCaja(e, this.colores); },
    svgCab(e) { return svgCabecera(e, this.colores); },
    familiasGrupo(g) { return Object.entries((this.cat && this.cat.familias_info) || {}).filter(([, v]) => v.grupo === g); },
    noInstalada(id) { return !!(tienda.estado && tienda.estado.familias && tienda.estado.familias[id] === false); },
    etiquetaTam(k) {
      const t = this.cat.tamanos[k];
      return `${k} (${t[0]} × ${t[1]})`;
    },
    elegirClase(c) {
      const anterior = this.def;
      if (!this.nombre.trim() || this.nombre === anterior.nuevo) this.nombre = c.nuevo;
      this.clase = c.clave;
      this.tamano = c.tamano;
      // cada tipo tiene su letra habitual; se respeta si ya se eligió otra
      const habitual = { poster: 'helvetica', presentacion: 'helvetica', documento: 'palatino', paper: 'times', tesis: 'palatino' };
      if (Object.values(habitual).includes(this.familia)) this.familia = habitual[c.clave];
    },
    async crear() {
      this.creando = true;
      try {
        const comun = { clase: this.clase, tamano: this.tamano, tema: this.tema, familia: this.familia, idioma: this.idioma };
        const propio = this.esPoster ? { orientacion: this.orientacion, columnas: this.columnas, estilo_bloque: this.estilo_bloque, cabecera: this.cabecera }
          : this.esDiapos ? { titulo_diapositiva: this.tituloDiapositiva }
            : { columnas: this.clase === 'paper' ? this.columnasTexto : 1 };
        const p = await post('api/proyectos', { nombre: this.nombre, asistente: { ...comun, ...propio } });
        this.$emit('cerrar');
        ir(`#/p/${p.id}`);
      } catch (e) { avisarError(e); } finally { this.creando = false; }
    },
  },
  template: `
  <div class="fondo-dialogo" @mousedown.self="$emit('cerrar')" @keydown.esc="$emit('cerrar')">
    <div class="dialogo ancho" role="dialog" aria-modal="true" aria-labelledby="tit-asistente">
      <header>
        <div style="flex:1">
          <h2 id="tit-asistente">Documento nuevo</h2>
          <p>Elige qué vas a hacer y su aspecto. Todo se puede cambiar después en el editor.</p>
        </div>
        <button class="btn icono fantasma" @click="$emit('cerrar')" aria-label="Cerrar"><icono n="cerrar"/></button>
      </header>
      <div class="cuerpo" v-if="cat">
        <div class="asistente">
          <div class="opciones">
            <div class="campo"><span class="etiqueta">Tipo de documento</span>
              <div class="tipos-doc" role="radiogroup" aria-label="Tipo de documento">
                <button v-for="c in clases" :key="c.clave" type="button" role="radio" :aria-checked="clase === c.clave" :class="{activo: clase === c.clave}" @click="elegirClase(c)">
                  <strong>{{ c.nombre }}</strong><span>{{ c.nota }}</span></button>
              </div></div>
            <label class="campo"><span class="etiqueta">Nombre del proyecto</span>
              <input class="entrada" v-model="nombre" maxlength="150"></label>
            <div class="fila-campos">
              <label class="campo"><span class="etiqueta">{{ esPoster ? 'Tamaño del lienzo' : esDiapos ? 'Formato de las diapositivas' : 'Tamaño de la página' }}</span>
                <select class="entrada" v-model="tamano">
                  <option v-for="k in tamanos" :key="k" :value="k">{{ etiquetaTam(k) }}</option>
                </select></label>
              <div class="campo" v-if="clase === 'paper'"><span class="etiqueta">Columnas de texto</span>
                <div class="segmentos">
                  <button type="button" :class="{activo: columnasTexto===1}" @click="columnasTexto=1">Una</button>
                  <button type="button" :class="{activo: columnasTexto===2}" @click="columnasTexto=2">Dos</button>
                </div></div>
              <div class="campo" v-if="esDiapos"><span class="etiqueta">Títulos de las diapositivas</span>
                <div class="segmentos">
                  <button type="button" :class="{activo: tituloDiapositiva==='banda'}" @click="tituloDiapositiva='banda'">Banda</button>
                  <button type="button" :class="{activo: tituloDiapositiva==='linea'}" @click="tituloDiapositiva='linea'">Línea</button>
                  <button type="button" :class="{activo: tituloDiapositiva==='simple'}" @click="tituloDiapositiva='simple'">Sencillo</button>
                </div></div>
              <div class="campo" v-if="esPoster"><span class="etiqueta">Orientación</span>
                <div class="segmentos">
                  <button type="button" :class="{activo: orientacion==='vertical'}" @click="orientacion='vertical'">Vertical</button>
                  <button type="button" :class="{activo: orientacion==='horizontal'}" @click="orientacion='horizontal'">Horizontal</button>
                </div></div>
            </div>
            <div class="fila-campos">
              <div class="campo" v-if="esPoster"><span class="etiqueta">Columnas</span>
                <div class="segmentos">
                  <button v-for="n in 6" :key="n" type="button" :class="{activo: columnas===n}" @click="columnas=n">{{ n }}</button>
                </div></div>
              <label class="campo"><span class="etiqueta">Tipografía</span>
                <select class="entrada" v-model="familia">
                  <optgroup label="Clásicas">
                    <option v-for="[id, v] in familiasGrupo('clasica')" :key="id" :value="id">{{ v.nombre }}</option>
                  </optgroup>
                  <optgroup label="Libres de TeX Live">
                    <option v-for="[id, v] in familiasGrupo('libre')" :key="id" :value="id" :disabled="noInstalada(id)">{{ v.nombre }}{{ noInstalada(id) ? ' (no instalada)' : '' }}</option>
                  </optgroup>
                </select></label>
            </div>
            <div class="fila-campos">
              <label class="campo"><span class="etiqueta">Idioma</span>
                <select class="entrada" v-model="idioma">
                  <option v-for="(d, k) in cat.idiomas" :key="k" :value="k">{{ d.nombre }}</option>
                </select></label>
            </div>
            <div class="campo"><span class="etiqueta">Colores</span>
              <c-tema v-model="tema"/></div>
            <div class="campo" v-if="esPoster"><span class="etiqueta">Estilo de las cajas</span>
              <div class="estilos-caja">
                <button v-for="e in cat.estilos_caja" :key="e" type="button" class="estilo-caja" :class="{activo: estilo_bloque===e}" @click="estilo_bloque=e" :title="nombresEstilo[e]">
                  <span v-html="svgCaja(e)"></span>{{ nombresEstilo[e] }}
                </button>
              </div></div>
            <div class="campo" v-if="esPoster"><span class="etiqueta">Cabecera</span>
              <div class="estilos-caja">
                <button v-for="e in cat.estilos_cabecera" :key="e" type="button" class="estilo-caja" :class="{activo: cabecera===e}" @click="cabecera=e">
                  <span v-html="svgCab(e)"></span>{{ nombresCabecera[e] }}
                </button>
              </div></div>
          </div>
          <div class="previa"><div class="hoja-mini" :style="estiloPrevia" v-html="previa"></div></div>
        </div>
      </div>
      <footer>
        <button class="btn" @click="$emit('cerrar')">Cancelar</button>
        <button class="btn primario" :disabled="creando || !nombre.trim()" @click="crear">{{ creando ? 'Creando…' : 'Crear ' + articulo }}</button>
      </footer>
    </div>
  </div>`,
  created() {
    this.nombresEstilo = NOMBRES_ESTILO;
    this.nombresCabecera = NOMBRES_CABECERA;
  },
};

export const VistaInicio = {
  name: 'vista-inicio',
  components: { HojaMini, AsistenteNuevo: Asistente },
  data: () => ({ proyectos: null, plantillas: null, menu: null, asistente: false, importando: false, filtro: '' }),
  computed: {
    estado() { return tienda.estado; },
    version() { return (tienda.estado && tienda.estado.version) || ""; },
    incluidas() { return (this.plantillas || []).filter((p) => p.incluida); },
    propias() { return (this.plantillas || []).filter((p) => !p.incluida); },
    // tipos de documento que hay entre los proyectos (para filtrar)
    clasesPresentes() {
      const hay = new Set((this.proyectos || []).map((p) => p.clase || 'poster'));
      return CLASES.filter((c) => hay.has(c.clave)).map((c) => ({ clave: c.clave, nombre: PLURAL_CLASE[c.clave] }));
    },
    visibles() { return (this.proyectos || []).filter((p) => !this.filtro || (p.clase || 'poster') === this.filtro); },
  },
  methods: {
    fecha,
    nombreClase(x) { return NOMBRES_CLASE[(x && x.clase) || 'poster'] || 'Póster'; },
    async cargar() {
      try {
        [this.proyectos, this.plantillas] = await Promise.all([api('api/proyectos'), api('api/plantillas')]);
      } catch (e) { avisarError(e); }
    },
    abrir(p) { ir(`#/p/${p.id}`); },
    alternarMenu(clave) { this.menu = this.menu === clave ? null : clave; },
    cerrarMenus(ev) { if (!ev.target.closest('.menu-contenedor')) this.menu = null; },
    miniProyecto(p) { return p.tiene_miniatura ? `api/proyectos/${p.id}/miniatura?v=${encodeURIComponent(p.modificado || '')}` : null; },
    miniPlantilla(t) { return t.tiene_miniatura ? `api/plantillas/${t.id}/miniatura` : null; },
    async desdePlantilla(t) {
      const nombre = await preguntar({
        titulo: `${this.nombreClase(t)} desde «${t.nombre}»`, texto: t.descripcion || '', etiqueta: 'Nombre del proyecto',
        valor: t.nombre, aceptar: 'Crear',
      });
      if (!nombre) return;
      try {
        const p = await post('api/proyectos', { nombre, plantilla: t.id });
        ir(`#/p/${p.id}`);
      } catch (e) { avisarError(e); }
    },
    async renombrar(p) {
      this.menu = null;
      const nombre = await preguntar({ titulo: 'Renombrar el proyecto', etiqueta: 'Nombre', valor: p.nombre, aceptar: 'Guardar' });
      if (!nombre) return;
      try { await patch(`api/proyectos/${p.id}`, { nombre }); await this.cargar(); } catch (e) { avisarError(e); }
    },
    async duplicar(p) {
      this.menu = null;
      try { await post(`api/proyectos/${p.id}/duplicar`); await this.cargar(); avisar('Proyecto duplicado'); } catch (e) { avisarError(e); }
    },
    async borrarProyecto(p) {
      this.menu = null;
      const ok = await confirmar({ titulo: `¿Borrar «${p.nombre}»?`, texto: 'Se borran el proyecto, sus imágenes y sus cuadernos. No se puede deshacer.', aceptar: 'Borrar', peligro: true });
      if (!ok) return;
      try { await borrar(`api/proyectos/${p.id}`); await this.cargar(); avisar('Proyecto borrado'); } catch (e) { avisarError(e); }
    },
    async comoPlantilla(p) {
      this.menu = null;
      const nombre = await preguntar({ titulo: 'Guardar como plantilla nueva', texto: 'La plantilla copia el diseño, el contenido, las imágenes y los cuadernos del proyecto.', etiqueta: 'Nombre de la plantilla', valor: p.nombre, aceptar: 'Guardar plantilla' });
      if (!nombre) return;
      try { await post('api/plantillas', { proyecto: p.id, nombre }); await this.cargar(); avisar('Plantilla guardada'); } catch (e) { avisarError(e); }
    },
    async actualizarPlantilla(p) {
      this.menu = null;
      const t = p.plantilla_propia;
      if (!t) return;
      const ok = await confirmar({
        titulo: `¿Actualizar la plantilla «${t.nombre}»?`,
        texto: `Su contenido pasa a ser el de «${p.nombre}»: diseño, textos, imágenes y cuadernos. Conserva su nombre y su descripción. Los documentos que ya se crearon con ella no cambian.`,
        aceptar: 'Actualizar la plantilla',
      });
      if (!ok) return;
      try { await put(`api/plantillas/${t.id}`, { proyecto: p.id }); await this.cargar(); avisar(`Plantilla «${t.nombre}» actualizada`); } catch (e) { avisarError(e); }
    },
    recortar,
    async editarPlantilla(t) {
      this.menu = null;
      const nombre = await preguntar({ titulo: 'Renombrar la plantilla', etiqueta: 'Nombre', valor: t.nombre, aceptar: 'Guardar' });
      if (!nombre) return;
      const descripcion = await preguntar({ titulo: 'Descripción de la plantilla', etiqueta: 'Descripción (opcional)', valor: t.descripcion || '', aceptar: 'Guardar', multilinea: true });
      try { await patch(`api/plantillas/${t.id}`, { nombre, descripcion: descripcion ?? t.descripcion ?? '' }); await this.cargar(); } catch (e) { avisarError(e); }
    },
    async borrarPlantilla(t) {
      this.menu = null;
      const ok = await confirmar({ titulo: `¿Borrar la plantilla «${t.nombre}»?`, texto: 'Los documentos creados con ella no cambian.', aceptar: 'Borrar', peligro: true });
      if (!ok) return;
      try { await borrar(`api/plantillas/${t.id}`); await this.cargar(); } catch (e) { avisarError(e); }
    },
    descargar(url) { this.menu = null; descargar(url); },
    elegirZip() { this.$refs.zip.click(); },
    async importar(ev) {
      const f = ev.target.files[0];
      ev.target.value = '';
      if (!f) return;
      this.importando = true;
      try {
        const r = await subir('api/proyectos/importar', { archivo: f });
        if (r.tipo === 'plantilla') {
          avisar(`Plantilla «${r.plantilla.nombre}» importada`);
          await this.cargar();
        } else {
          avisar(`Proyecto «${r.proyecto.nombre}» importado`);
          ir(`#/p/${r.proyecto.id}`);
        }
      } catch (e) { avisarError(e); } finally { this.importando = false; }
    },
  },
  mounted() {
    this.cargar();
    document.addEventListener('mousedown', this.cerrarMenus);
  },
  beforeUnmount() { document.removeEventListener('mousedown', this.cerrarMenus); },
  template: `
  <div class="inicio">
    <header class="barra">
      <a class="marca" href="#/"><span v-html="logo"></span>DocsLab</a>
      <span class="espacio"></span>
      <a class="btn fantasma" href="#/lab" title="Crea y recrea componentes para tus documentos, con o sin código LaTeX"><icono n="matraz"/>Componente Lab</a>
      <span class="estado-tex" v-if="estado">
        <span v-if="estado.pdflatex" class="chip ok" :title="estado.tex"><span class="punto"></span>LaTeX listo</span>
        <span v-else class="chip error"><span class="punto"></span>Falta pdflatex</span>
        <span v-if="estado.colab" class="chip">Google Colab</span>
      </span>
    </header>
    <main>
      <div class="cabeza">
        <div>
          <h1>Tus documentos</h1>
          <p>Pósters, presentaciones, artículos, tesis y documentos: edita por bloques, compila con LaTeX y descarga el PDF. Las figuras pueden salir directamente de tus cuadernos de Colab o Jupyter.</p>
        </div>
        <div class="acciones">
          <input ref="zip" type="file" accept=".zip" hidden @change="importar">
          <button class="btn" @click="elegirZip" :disabled="importando"><icono n="importar"/>{{ importando ? 'Importando…' : 'Importar zip' }}</button>
          <button class="btn primario" @click="asistente = true"><icono n="mas"/>Documento nuevo</button>
        </div>
      </div>

      <div v-if="estado && !estado.pdflatex" class="vacio">
        <strong>No se encontró pdflatex en este equipo.</strong>
        Puedes editar, pero para ver el PDF hace falta TeX Live (o MiKTeX). La guía LEEME explica cómo instalarlo, o abre DocsLab en Google Colab con el cuaderno lanzador.
      </div>

      <section>
        <div class="filtro-clases" v-if="clasesPresentes.length > 1" role="group" aria-label="Filtrar por tipo de documento">
          <button type="button" :class="{activo: !filtro}" :aria-pressed="!filtro" @click="filtro = ''">Todo</button>
          <button v-for="c in clasesPresentes" :key="c.clave" type="button" :class="{activo: filtro === c.clave}" :aria-pressed="filtro === c.clave" @click="filtro = c.clave">{{ c.nombre }}</button>
        </div>
        <div class="mesa-hojas" v-if="proyectos">
          <button class="tarjeta-hoja tarjeta-nueva" @click="asistente = true">
            <div class="soporte"><div class="hoja-mini" style="width:136px;height:192px"><span><icono n="mas"/>Documento nuevo</span></div></div>
            <div class="pie-tarjeta"><span class="nombre">Empezar desde cero</span><span class="detalle">Póster, presentación, artículo, tesis o documento</span></div>
          </button>
          <div v-for="p in visibles" :key="p.id" class="tarjeta-hoja" @click="abrir(p)">
            <div class="soporte"><hoja-mini :src="miniProyecto(p)"/></div>
            <div class="pie-tarjeta">
              <button type="button" class="nombre boton-nombre" @click.stop="abrir(p)">{{ p.nombre }}</button>
              <span class="detalle">{{ p.tipo === 'latex' ? 'Código LaTeX' : nombreClase(p) }}, {{ fecha(p.modificado) }}</span>
            </div>
            <div class="menu-tarjeta menu-contenedor" @click.stop>
              <button class="btn icono pequeno fantasma" :aria-label="'Opciones de ' + p.nombre" @click="alternarMenu('p' + p.id)"><icono n="puntos"/></button>
              <div class="menu" v-if="menu === 'p' + p.id">
                <button @click="abrir(p)"><icono n="lapiz"/>Abrir</button>
                <button @click="renombrar(p)"><icono n="texto"/>Renombrar</button>
                <button @click="duplicar(p)"><icono n="duplicar"/>Duplicar</button>
                <button @click="comoPlantilla(p)"><icono n="plantilla"/>Guardar como plantilla nueva</button>
                <button v-if="p.plantilla_propia" @click="actualizarPlantilla(p)" :title="'Actualizar la plantilla «' + p.plantilla_propia.nombre + '» con este documento'"><icono n="plantilla"/>Actualizar la plantilla «{{ recortar(p.plantilla_propia.nombre) }}»</button>
                <div class="separador"></div>
                <button v-if="p.tiene_pdf" @click="descargar('api/proyectos/' + p.id + '/pdf?descargar=1')"><icono n="descargar"/>Descargar el PDF</button>
                <button @click="descargar('api/proyectos/' + p.id + '/exportar?tipo=overleaf')"><icono n="descargar"/>Zip para Overleaf</button>
                <button @click="descargar('api/proyectos/' + p.id + '/exportar?tipo=proyecto')"><icono n="descargar"/>Zip del proyecto (copia de seguridad)</button>
                <div class="separador"></div>
                <button class="peligro" @click="borrarProyecto(p)"><icono n="basura"/>Borrar</button>
              </div>
            </div>
          </div>
        </div>
        <p v-else class="ayuda">Cargando…</p>
      </section>

      <section>
        <h2>Plantillas</h2>
        <p class="sub">Empieza con un diseño hecho. Cualquier documento se puede guardar como plantilla desde su menú, y desde ese mismo documento se puede actualizar la plantilla más adelante.</p>
        <div class="mesa-hojas" v-if="plantillas">
          <div v-for="t in [...incluidas, ...propias]" :key="t.id" class="tarjeta-hoja"
               @click="desdePlantilla(t)" :title="t.descripcion">
            <div class="soporte"><hoja-mini :src="miniPlantilla(t)"/></div>
            <div class="pie-tarjeta">
              <button type="button" class="nombre boton-nombre" :aria-label="'Crear un documento con la plantilla ' + t.nombre" @click.stop="desdePlantilla(t)">{{ t.nombre }}</button>
              <span class="detalle">{{ t.tipo === 'latex' ? 'Código LaTeX' : nombreClase(t) }}, {{ t.incluida ? 'incluida' : 'tuya' }}<template v-if="t.etiquetas && t.etiquetas.length">, {{ t.etiquetas.join(', ') }}</template></span>
            </div>
            <div class="menu-tarjeta menu-contenedor" @click.stop>
              <button class="btn icono pequeno fantasma" :aria-label="'Opciones de ' + t.nombre" @click="alternarMenu('t' + t.id)"><icono n="puntos"/></button>
              <div class="menu" v-if="menu === 't' + t.id">
                <p class="nota" v-if="t.descripcion">{{ t.descripcion }}</p>
                <button @click="menu = null; desdePlantilla(t)"><icono n="mas"/>Crear un documento con ella</button>
                <button @click="descargar('api/plantillas/' + t.id + '/exportar')"><icono n="descargar"/>Exportar (zip)</button>
                <template v-if="!t.incluida">
                  <button @click="editarPlantilla(t)"><icono n="lapiz"/>Renombrar o describir</button>
                  <div class="separador"></div>
                  <button class="peligro" @click="borrarPlantilla(t)"><icono n="basura"/>Borrar la plantilla</button>
                </template>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
    <footer class="pie-inicio">
      DocsLab {{ version }} · Software libre bajo la
      <a href="https://www.gnu.org/licenses/agpl-3.0.html" target="_blank" rel="noopener">licencia GNU AGPL-3.0</a>
      (la plantilla LaTeX, bajo la <a href="https://www.latex-project.org/lppl/lppl-1-3c/" target="_blank" rel="noopener">LPPL-1.3c</a>).
      El código fuente completo está en la carpeta de DocsLab; el texto de las licencias, en <code>LICENSE</code> y <code>latex/</code>.
      Copyright © 2026 Christian Alejandro Ponce Mejia.
    </footer>
    <asistente-nuevo v-if="asistente" @cerrar="asistente = false"/>
  </div>`,
  created() {
    this.logo = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="8" cy="8" r="4.4"/><path d="M8 .8v14.4M.8 8h14.4"/></svg>';
  },
};
