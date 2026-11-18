// SPDX-License-Identifier: AGPL-3.0-only
// Panel de cuadernos (Colab / Jupyter): subir o enlazar, configurar, ejecutar y usar sus figuras.
import { api, patch, borrar, subir, descargar, esperarTrabajo, post } from './api.js';
import { tienda, avisar, avisarError, confirmar } from './tienda.js';
import { fecha, tamano, copiarTexto } from './util.js';

const { inject } = Vue;

// Explorador de carpetas del servidor (Drive montado en Colab, carpetas del equipo…)
const Explorador = {
  name: 'explorador-servidor',
  emits: ['elegir', 'cerrar'],
  data: () => ({ ruta: '', padre: null, entradas: [], cargando: false, error: '' }),
  methods: {
    async abrir(ruta) {
      this.cargando = true;
      this.error = '';
      try {
        const r = await api(`api/explorar?ruta=${encodeURIComponent(ruta || '')}`);
        Object.assign(this, { ruta: r.ruta, padre: r.padre, entradas: r.entradas });
      } catch (e) { this.error = e.message; } finally { this.cargando = false; }
    },
    clic(e) { if (e.carpeta) this.abrir(e.ruta); else this.$emit('elegir', e.ruta); },
  },
  mounted() { this.abrir(''); },
  template: `
  <div class="fondo-dialogo" @mousedown.self="$emit('cerrar')" @keydown.esc="$emit('cerrar')">
    <div class="dialogo medio" role="dialog" aria-modal="true" aria-labelledby="tit-explorador">
      <header>
        <div style="flex:1"><h2 id="tit-explorador">Abrir un cuaderno del servidor</h2>
          <p>El cuaderno se ejecuta en su propia carpeta, con sus datos. En Colab, monta Drive y busca en /content/drive.</p></div>
        <button class="btn icono fantasma" @click="$emit('cerrar')" aria-label="Cerrar"><icono n="cerrar"/></button>
      </header>
      <div class="cuerpo">
        <div class="ruta-actual">{{ ruta || 'Carpetas permitidas' }}</div>
        <p v-if="error" class="ayuda" style="color:var(--rojo)">{{ error }}</p>
        <div class="explorador">
          <button v-if="padre !== null && ruta" @click="abrir(padre)"><icono n="arriba"/>Subir un nivel</button>
          <button v-for="e in entradas" :key="e.ruta" @click="clic(e)"><icono :n="e.carpeta ? 'carpeta' : 'cuaderno'"/>{{ e.nombre }}</button>
          <p v-if="!cargando && !entradas.length" class="ayuda" style="padding:10px">Esta carpeta no tiene subcarpetas ni cuadernos.</p>
        </div>
      </div>
      <footer><button class="btn" @click="$emit('cerrar')">Cancelar</button></footer>
    </div>
  </div>`,
};

// nombre del módulo que falta → paquete que se instala con pip (cuando no coinciden)
const PAQUETES_PIP = {
  sklearn: 'scikit-learn', cv2: 'opencv-python', PIL: 'pillow', skimage: 'scikit-image', yaml: 'pyyaml',
  Bio: 'biopython', bs4: 'beautifulsoup4', dateutil: 'python-dateutil', mpl_toolkits: 'matplotlib',
  umap: 'umap-learn', docx: 'python-docx', pptx: 'python-pptx', Levenshtein: 'python-Levenshtein',
};

const TarjetaCuaderno = {
  name: 'tarjeta-cuaderno',
  props: { c: Object, enLab: Boolean, activo: Boolean },
  emits: ['cambio', 'abrir', 'figuras'],
  setup() { return { ed: inject('ed') }; },
  data: () => ({ pestana: null, trabajo: null, celdas: null, figuras: null, archivos: null, subiendo: 0, menu: false, celdaColab: '' }),
  computed: {
    ultima() { return this.c.ultima_ejecucion; },
    ejecutando() { return this.trabajo && ['pendiente', 'ejecutando'].includes(this.trabajo.estado); },
    chip() {
      if (this.ejecutando) return { clase: 'trabajando', texto: 'Ejecutando' };
      if (!this.ultima) return { clase: '', texto: 'Sin ejecutar' };
      if (this.ultima.ok) return { clase: 'ok', texto: this.ultima.importado ? 'Figuras importadas' : 'Ejecutado' };
      return { clase: 'error', texto: this.ultima.error && this.ultima.error.tipo === 'cancelado' ? 'Cancelado' : 'Con errores' };
    },
    registro() { return this.trabajo && this.trabajo.registro ? this.trabajo.registro.slice(-60).join('\n') : ''; },
    // un paquete que falta en el Python de DocsLab: cómo instalarlo ahí
    faltaModulo() {
      const e = this.ultima && this.ultima.error;
      if (!e || e.tipo !== 'ModuleNotFoundError') return null;
      const m = /No module named '([^'.]+)/.exec(String(e.mensaje || ''));
      if (!m || m[1] === 'google') return null;
      const paquete = PAQUETES_PIP[m[1]] || m[1];
      const est = tienda.estado || {};
      if (est.colab) return { paquete, colab: true, comando: `%pip install ${paquete}` };
      return { paquete, colab: false, comando: `"${est.python_exe || 'python3'}" -m pip install ${paquete}` };
    },
    par() { return this.c.parametros || { despues_de: -1, codigo: '' }; },
    extensiones: {
      get() { return (this.c.patrones_ext || []).join(', '); },
      set(v) { this.c.patrones_ext = v.split(/[\s,;]+/).map((x) => x.replace(/^\./, '').trim().toLowerCase()).filter(Boolean); },
    },
  },
  watch: {
    registro() { this.$nextTick(() => { const r = this.$refs.registro; if (r) r.scrollTop = r.scrollHeight; }); },
  },
  methods: {
    fecha, tamano,
    async seguir(id) {
      try {
        const fin = await esperarTrabajo(id, { registro: true, intervalo: 1000, alCambiar: (t) => { this.trabajo = t; } });
        this.trabajo = fin;
        const r = fin.resultado;
        if (fin.estado === 'terminado' && r) {
          if (r.ok) avisar(`«${this.c.nombre}» terminó: ${r.figuras.length} figuras recogidas`);
          else if (r.error && r.error.tipo !== 'cancelado') avisar(`«${this.c.nombre}» terminó con un error: ${r.error.tipo}`, { tipo: 'error', ms: 8000 });
          this.ed.recursosCambiaron();
          this.$emit('figuras');
          if (r.figuras.length && this.c.recompilar !== false) this.ed.compilarAhora();
          if (this.pestana === 'figuras') this.cargarFiguras();
        } else if (fin.estado === 'error') {
          avisar(`No se pudo ejecutar: ${fin.mensaje}`, { tipo: 'error', ms: 9000 });
        }
        this.$emit('cambio');
      } catch (e) { avisarError(e); }
    },
    async ejecutar() {
      try {
        await this.guardar();
        const t = await post(`api/proyectos/${this.ed.pid}/cuadernos/${this.c.id}/ejecutar`);
        this.trabajo = t;
        this.pestana = 'registro';
        this.seguir(t.id);
      } catch (e) { avisarError(e); }
    },
    async cancelar() {
      if (!this.trabajo) return;
      try { await post(`api/trabajos/${this.trabajo.id}/cancelar`); avisar('Cancelando…'); } catch (e) { avisarError(e); }
    },
    async guardar() {
      const datos = {};
      for (const k of ['patrones_ext', 'carpeta_figuras', 'preferir_pdf', 'recoger_mostradas', 'omitir_colab', 'parametros', 'tiempo_celda', 'recompilar', 'kernel']) datos[k] = this.c[k];
      try { await patch(`api/proyectos/${this.ed.pid}/cuadernos/${this.c.id}`, datos); } catch (e) { avisarError(e); }
    },
    async abrirPestana(p) {
      this.menu = false;
      this.pestana = this.pestana === p ? null : p;
      if (this.pestana === 'figuras') this.cargarFiguras();
      if (this.pestana === 'ajustes' && !this.celdas) this.cargarCeldas();
      if (this.pestana === 'datos') this.cargarArchivos();
      if (this.pestana === 'colab' && !this.celdaColab) {
        try { this.celdaColab = await api(`api/proyectos/${this.ed.pid}/cuadernos/${this.c.id}/celda-colab`, { texto: true }); } catch (e) { avisarError(e); }
      }
    },
    async cargarFiguras() { try { this.figuras = await api(`api/proyectos/${this.ed.pid}/cuadernos/${this.c.id}/figuras`); } catch (e) { avisarError(e); } },
    async cargarCeldas() { try { this.celdas = await api(`api/proyectos/${this.ed.pid}/cuadernos/${this.c.id}/celdas`); } catch (e) { avisarError(e); } },
    async cargarArchivos() { try { this.archivos = await api(`api/proyectos/${this.ed.pid}/cuadernos/${this.c.id}/archivos`); } catch (e) { avisarError(e); } },
    vista(f) { return `api/proyectos/${this.ed.pid}/vista?ruta=${encodeURIComponent(f.ruta)}&v=${encodeURIComponent(f.fecha)}`; },
    usar(f) { this.ed.usarImagen(f.ruta); },
    async subirDatos(archivos) {
      if (!archivos || !archivos.length) return;
      this.subiendo = 0.01;
      try {
        await subir(`api/proyectos/${this.ed.pid}/cuadernos/${this.c.id}/datos`, { datos: [...archivos] }, { alProgreso: (p) => { this.subiendo = Math.max(0.01, p); } });
        avisar('Datos subidos');
        await this.cargarArchivos();
      } catch (e) { avisarError(e); } finally { this.subiendo = 0; }
    },
    async importarZip(ev) {
      const f = ev.target.files[0];
      ev.target.value = '';
      if (!f) return;
      try {
        const r = await subir(`api/proyectos/${this.ed.pid}/cuadernos/${this.c.id}/importar`, { archivo: f });
        avisar(`${r.figuras.length} figuras importadas`);
        this.ed.recursosCambiaron();
        this.ed.compilarAhora();
        this.$emit('cambio');
        this.$emit('figuras');
        this.pestana = 'figuras';
        this.cargarFiguras();
      } catch (e) { avisarError(e); }
    },
    async copiarComando() {
      try { await copiarTexto(this.faltaModulo.comando); avisar('Orden copiada: pégala en una terminal'); } catch (e) { avisarError(e); }
    },
    async copiarCelda() {
      try { await copiarTexto(this.celdaColab); avisar('Celda copiada: pégala al final del cuaderno en Colab'); } catch (e) { avisarError(e); }
    },
    async quitar() {
      this.menu = false;
      const ok = await confirmar({
        titulo: `¿Quitar «${this.c.nombre}» del proyecto?`,
        texto: this.c.origen === 'ruta' ? 'El cuaderno original no se toca. Las figuras ya recogidas se conservan.' : 'Se borra la copia del cuaderno y sus datos. Las figuras ya recogidas se conservan.',
        aceptar: 'Quitar', peligro: true,
      });
      if (!ok) return;
      try { await borrar(`api/proyectos/${this.ed.pid}/cuadernos/${this.c.id}`); this.$emit('cambio'); } catch (e) { avisarError(e); }
    },
    descargarEjecutado() { this.menu = false; descargar(`api/proyectos/${this.ed.pid}/cuadernos/${this.c.id}/ejecutado`); },
    elegirCelda(i) { this.par.despues_de = i; this.guardar(); },
  },
  mounted() {
    if (this.c.trabajo) { this.trabajo = { id: this.c.trabajo, estado: 'ejecutando' }; this.pestana = 'registro'; this.seguir(this.c.trabajo); }
  },
  template: `
  <article class="cuaderno" :class="{activo: activo}">
    <header>
      <span class="ico" style="margin-top:2px;color:var(--acento)"><icono n="cuaderno"/></span>
      <div class="titulo-nb">
        <h3 :title="c.ruta || c.nombre">{{ c.nombre }}</h3>
        <div class="detalle">{{ c.origen === 'ruta' ? 'Se ejecuta en su carpeta del servidor' : 'Copia subida al proyecto' }}</div>
        <div class="estado-nb" style="margin-top:6px">
          <span class="chip" :class="chip.clase"><span class="punto"></span>{{ chip.texto }}</span>
          <span v-if="ultima && !ejecutando" class="ayuda">{{ fecha(ultima.fecha) }}<template v-if="ultima.n_figuras !== undefined">, {{ ultima.n_figuras }} figuras</template><template v-if="ultima.segundos">, {{ Math.round(ultima.segundos) }} s</template></span>
        </div>
      </div>
      <div class="menu-contenedor">
        <button class="btn icono pequeno fantasma" @click="menu = !menu" :aria-label="'Opciones de ' + c.nombre"><icono n="puntos"/></button>
        <div class="menu" v-if="menu">
          <button @click="abrirPestana('ajustes')"><icono n="ajustes"/>Ajustes de ejecución</button>
          <button @click="abrirPestana('datos')" v-if="c.origen !== 'ruta'"><icono n="carpeta"/>Datos del cuaderno</button>
          <button @click="abrirPestana('colab')"><icono n="colab"/>Traer figuras desde Colab</button>
          <button @click="descargarEjecutado" :disabled="!ultima || ultima.importado"><icono n="descargar"/>Descargar el cuaderno ejecutado</button>
          <div class="separador"></div>
          <button class="peligro" @click="quitar"><icono n="basura"/>Quitar del proyecto</button>
        </div>
      </div>
    </header>
    <div class="cuerpo-nb">
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <button v-if="enLab" class="btn pequeno" :class="{primario: !activo}" @click="$emit('abrir')" :disabled="activo"><icono n="cuaderno"/>{{ activo ? 'Abierto' : 'Abrir' }}</button>
        <button v-if="!ejecutando" class="btn pequeno" :class="{primario: !enLab}" @click="ejecutar" title="Ejecuta el cuaderno entero en un Python recién arrancado, sin cambiar el archivo; el resultado se puede descargar"><icono n="play"/>{{ enLab ? 'Ejecutar en limpio' : 'Ejecutar' }}</button>
        <button v-else class="btn pequeno peligro" @click="cancelar"><icono n="parar"/>Cancelar</button>
        <button class="btn pequeno" :class="{activo: pestana==='figuras'}" @click="abrirPestana('figuras')"><icono n="imagen"/>Figuras</button>
        <button class="btn pequeno" :class="{activo: pestana==='registro'}" @click="abrirPestana('registro')" v-if="trabajo"><icono n="texto"/>Registro</button>
        <button class="btn pequeno" :class="{activo: pestana==='ajustes'}" @click="abrirPestana('ajustes')"><icono n="ajustes"/>Ajustes</button>
      </div>
      <div v-if="ejecutando" style="display:grid;gap:4px">
        <div class="barra-progreso"><div :style="{width: Math.round((trabajo.progreso || 0) * 100) + '%'}"></div></div>
        <span class="ayuda">{{ trabajo.mensaje || 'Preparando el núcleo de Python…' }}</span>
      </div>
      <div v-if="!ejecutando && ultima && ultima.error && ultima.error.tipo !== 'cancelado'" class="mensaje error" style="grid-template-columns:1fr">
        <div><strong>{{ ultima.error.tipo }}</strong>: {{ ultima.error.mensaje }}
          <p class="ayuda" v-if="ultima.error.tipo === 'ModuleNotFoundError' && String(ultima.error.mensaje).includes('google')">Es una celda de Colab: activa «Omitir las celdas de Colab» en Ajustes.</p>
          <p class="ayuda" v-else-if="ultima.error.tipo === 'FileNotFoundError'">Falta un archivo: súbelo en «Datos del cuaderno» (menú ⋯).</p>
          <p class="ayuda" v-else-if="faltaModulo && faltaModulo.colab">Falta «{{ faltaModulo.paquete }}»: añade al principio del cuaderno una celda con <code>{{ faltaModulo.comando }}</code> y vuelve a ejecutarlo.</p>
          <template v-else-if="faltaModulo">
            <p class="ayuda">Falta «{{ faltaModulo.paquete }}» en el Python de DocsLab. Instálalo desde una terminal y vuelve a ejecutar el cuaderno:</p>
            <div class="orden-pip"><code>{{ faltaModulo.comando }}</code>
              <button class="btn pequeno" @click="copiarComando"><icono n="portapapeles"/>Copiar</button></div>
          </template>
        </div>
      </div>

      <div v-if="pestana === 'registro'" class="registro-nb" ref="registro">{{ registro || 'Sin mensajes todavía.' }}</div>

      <div v-if="pestana === 'figuras'">
        <p v-if="figuras && !figuras.length" class="ayuda">Todavía no hay figuras. Ejecuta el cuaderno o importa el zip de Colab.</p>
        <div class="galeria compacta" style="padding:0">
          <div v-for="f in figuras || []" :key="f.ruta" class="recurso" :title="f.ruta">
            <span class="miniatura"><img :src="vista(f)" alt="" loading="lazy"></span>
            <span class="nombre-rec">{{ f.nombre }}</span>
            <span class="meta-rec">{{ fecha(f.fecha) }}</span>
            <span class="acciones-rec"><button @click="usar(f)" title="Usar en la selección" aria-label="Usar en la selección"><icono n="usar"/></button></span>
          </div>
        </div>
      </div>

      <div v-if="pestana === 'ajustes'" style="display:grid;gap:10px">
        <label class="campo"><span class="etiqueta">Carpeta donde guarda sus figuras</span>
          <input class="entrada codigo" v-model.trim="c.carpeta_figuras" placeholder="resultados (vacío = toda la carpeta)" @change="guardar"></label>
        <label class="campo"><span class="etiqueta">Tipos de archivo que se recogen</span>
          <input class="entrada codigo" v-model.lazy="extensiones" @change="guardar"></label>
        <label class="interruptor"><span class="texto">Preferir PDF si hay PNG y PDF de la misma figura</span><input type="checkbox" v-model="c.preferir_pdf" @change="guardar"><span class="pista"></span></label>
        <label class="interruptor"><span class="texto">Recoger también las imágenes que el cuaderno muestra</span><input type="checkbox" v-model="c.recoger_mostradas" @change="guardar"><span class="pista"></span></label>
        <label class="interruptor"><span class="texto">Omitir las celdas propias de Colab (montar Drive, subir archivos)</span><input type="checkbox" v-model="c.omitir_colab" @change="guardar"><span class="pista"></span></label>
        <label class="interruptor"><span class="texto">Recompilar el documento al terminar</span><input type="checkbox" :checked="c.recompilar !== false" @change="c.recompilar = $event.target.checked; guardar()"><span class="pista"></span></label>
        <label class="campo"><span class="etiqueta">Parámetros (código Python que se añade antes de ejecutar)</span>
          <textarea class="entrada codigo" rows="3" v-model="par.codigo" placeholder='CONFIG["figure_dpi"] = 200' @change="guardar"></textarea></label>
        <div class="campo" v-if="par.codigo && par.codigo.trim()"><span class="etiqueta">Insertarlos después de la celda</span>
          <div class="celdas" v-if="celdas">
            <div class="celda" :class="{elegida: par.despues_de === -1}" @click="elegirCelda(-1)"><span class="n">0</span><span>Al principio del cuaderno</span></div>
            <div v-for="cel in celdas" :key="cel.indice" class="celda" :class="{md: cel.tipo !== 'code', colab: cel.colab, elegida: par.despues_de === cel.indice}" @click="elegirCelda(cel.indice)">
              <span class="n">{{ cel.indice + 1 }}</span><span>{{ cel.primera || '(vacía)' }}</span></div>
          </div>
        </div>
        <div class="fila-campos">
          <label class="campo"><span class="etiqueta">Tiempo máximo por celda (s)</span>
            <input class="entrada" type="number" min="10" step="10" v-model.number="c.tiempo_celda" @change="guardar"></label>
          <label class="campo"><span class="etiqueta">Núcleo</span>
            <input class="entrada codigo" v-model.trim="c.kernel" placeholder="el del cuaderno" @change="guardar"></label>
        </div>
      </div>

      <div v-if="pestana === 'datos'" style="display:grid;gap:8px">
        <p class="ayuda">Archivos de la carpeta de trabajo (el cuaderno los ve en su carpeta actual). Un .zip se descomprime solo.</p>
        <input ref="datos" type="file" multiple hidden @change="subirDatos($event.target.files); $event.target.value=''">
        <button class="btn pequeno" style="justify-self:start" @click="$refs.datos.click()" :disabled="subiendo > 0"><icono n="subir"/>{{ subiendo ? 'Subiendo ' + Math.round(subiendo * 100) + ' %' : 'Subir datos (CSV, zip…)' }}</button>
        <div class="celdas" v-if="archivos">
          <div v-for="a in archivos" :key="a.ruta" class="celda" style="cursor:default"><span class="n">{{ tamano(a.tamano) }}</span><span>{{ a.ruta }}</span></div>
        </div>
      </div>

      <div v-if="pestana === 'colab'" style="display:grid;gap:8px">
        <p class="ayuda">Si prefieres ejecutar el cuaderno en Google Colab: copia esta celda, pégala al final del cuaderno y ejecútala. Descargará un zip con las figuras; súbelo aquí.</p>
        <pre class="registro-nb" style="max-height:150px">{{ celdaColab }}</pre>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button class="btn pequeno" @click="copiarCelda"><icono n="portapapeles"/>Copiar la celda</button>
          <input ref="zip" type="file" accept=".zip" hidden @change="importarZip">
          <button class="btn pequeno primario" @click="$refs.zip.click()"><icono n="importar"/>Importar el zip de figuras</button>
        </div>
      </div>
    </div>
  </article>`,
  created() { if (!this.c.parametros) this.c.parametros = { despues_de: -1, codigo: '' }; },
};

export const PanelCuadernos = {
  name: 'panel-cuadernos',
  components: { TarjetaCuaderno, ExploradorServidor: Explorador },
  props: { enLab: Boolean, activo: String },
  emits: ['abrir', 'lista', 'figuras'],
  setup() { return { ed: inject('ed') }; },
  data: () => ({ cuadernos: null, explorar: false, subiendo: 0 }),
  computed: {
    estado() { return tienda.estado; },
    puedeExplorar() { return this.estado && this.estado.raices && this.estado.raices.length; },
  },
  methods: {
    async cargar() {
      try { this.cuadernos = await api(`api/proyectos/${this.ed.pid}/cuadernos`); this.$emit('lista', this.cuadernos); } catch (e) { avisarError(e); }
    },
    async subirCuaderno(ev) {
      const archivos = [...ev.target.files];
      ev.target.value = '';
      const nb = archivos.find((f) => f.name.toLowerCase().endsWith('.ipynb'));
      if (!nb) { avisar('Elige un archivo .ipynb (y si quieres, sus datos a la vez)', { tipo: 'error' }); return; }
      const datos = archivos.filter((f) => f !== nb);
      this.subiendo = 0.01;
      try {
        await subir(`api/proyectos/${this.ed.pid}/cuadernos`, { cuaderno: nb, datos }, { alProgreso: (p) => { this.subiendo = Math.max(0.01, p); } });
        avisar(`Cuaderno «${nb.name}» añadido`);
        await this.cargar();
      } catch (e) { avisarError(e); } finally { this.subiendo = 0; }
    },
    async enlazar(ruta) {
      this.explorar = false;
      try {
        await post(`api/proyectos/${this.ed.pid}/cuadernos`, { ruta });
        avisar('Cuaderno enlazado');
        await this.cargar();
      } catch (e) { avisarError(e); }
    },
  },
  mounted() { this.cargar(); },
  template: `
  <div class="cuadernos">
    <div style="display:grid;gap:8px">
      <input ref="nb" type="file" multiple accept=".ipynb,.csv,.tsv,.txt,.json,.xlsx,.zip,.fasta,.fa,.gb,.gbk,.npy,.pkl,.parquet" hidden @change="subirCuaderno">
      <button class="btn" :class="{primario: !enLab}" @click="$refs.nb.click()" :disabled="subiendo > 0"><icono n="subir"/>{{ subiendo ? 'Subiendo ' + Math.round(subiendo * 100) + ' %' : 'Subir un cuaderno (.ipynb)' }}</button>
      <button v-if="puedeExplorar" class="btn" @click="explorar = true"><icono n="carpeta"/>Abrir desde una carpeta{{ estado.colab ? ' (Drive)' : '' }}</button>
    </div>
    <div v-if="cuadernos && !cuadernos.length" class="vacio">
      <strong>Genera las figuras desde tus cuadernos.</strong>
      <span>Crea un cuaderno nuevo o sube el .ipynb de Colab o Jupyter junto con sus datos. DocsLab lo ejecuta aquí, recoge las figuras que guarda (PNG, JPG o PDF) y las deja en «Imágenes». Al volver a ejecutarlo, el documento se actualiza solo.</span>
      <span>¿Prefieres ejecutarlo en Colab? Súbelo igualmente y usa «Traer figuras desde Colab».</span>
    </div>
    <tarjeta-cuaderno v-for="c in cuadernos || []" :key="c.id" :c="c" :en-lab="enLab" :activo="activo === c.id" @cambio="cargar" @abrir="$emit('abrir', c)" @figuras="$emit('figuras')"/>
    <explorador-servidor v-if="explorar" @elegir="enlazar" @cerrar="explorar = false"/>
  </div>`,
};
