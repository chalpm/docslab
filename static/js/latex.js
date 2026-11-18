// Cuerpo del editor para proyectos en modo LaTeX: archivos, código y vista previa.
import { api, subir, borrar, patch } from './api.js';
import { avisar, avisarError, confirmar, preguntar } from './tienda.js';
import { retrasar, tamano } from './util.js';
import { VistaPdf } from './vista.js';
import { PanelRegistro } from './registro.js';

const { inject, markRaw } = Vue;

const MODOS = { tex: 'stex', sty: 'stex', cls: 'stex', bib: 'stex', bst: 'stex' };

export const CuerpoLatex = {
  name: 'cuerpo-latex',
  components: { VistaPdf, PanelRegistro },
  setup() { return { ed: inject('ed') }; },
  data: () => ({ archivos: [], abierto: null, esImagen: false, sucio: false, guardando: false, cargandoArchivo: false }),
  computed: {
    principal() { return this.ed.meta.principal; },
    textos() { return this.archivos.filter((a) => a.texto); },
    otros() { return this.archivos.filter((a) => !a.texto); },
    errores() { return (this.ed.compilacion && this.ed.compilacion.errores) || []; },
  },
  watch: {
    errores() { this.marcarErrores(); },
  },
  methods: {
    tamano,
    async cargarLista() {
      try { this.archivos = await api(`api/proyectos/${this.ed.pid}/archivos`); } catch (e) { avisarError(e); }
    },
    async abrir(ruta, linea) {
      if (this.sucio) await this.guardarYa();
      const a = this.archivos.find((x) => x.ruta === ruta);
      this.abierto = ruta;
      this.esImagen = a ? !a.texto : false;
      if (this.esImagen) return;
      this.cargandoArchivo = true;
      try {
        const texto = await api(`api/proyectos/${this.ed.pid}/archivos/${ruta.split('/').map(encodeURIComponent).join('/')}`, { texto: true });
        const ext = ruta.split('.').pop().toLowerCase();
        this.cm.setOption('mode', MODOS[ext] || null);
        this.ignorar = true;
        this.cm.setValue(texto);
        this.cm.clearHistory();
        this.ignorar = false;
        this.sucio = false;
        this.marcarErrores();
        this.$nextTick(() => {
          this.cm.refresh();
          if (linea) { this.cm.setCursor({ line: linea - 1, ch: 0 }); this.cm.scrollIntoView({ line: linea - 1, ch: 0 }, 120); }
          this.cm.focus();
        });
      } catch (e) { avisarError(e); } finally { this.cargandoArchivo = false; }
    },
    async guardarYa() {
      if (!this.abierto || this.esImagen || !this.sucio) return;
      this.guardar.cancelar();
      this.guardando = true;
      const ruta = this.abierto, texto = this.cm.getValue();
      try {
        await api(`api/proyectos/${this.ed.pid}/archivos/${ruta.split('/').map(encodeURIComponent).join('/')}`, { metodo: 'PUT', cuerpo: texto });
        if (this.abierto === ruta && this.cm.getValue() === texto) this.sucio = false;
        this.ed.marcarGuardado();
      } catch (e) { avisarError(e); } finally { this.guardando = false; }
    },
    marcarErrores() {
      if (!this.cm) return;
      for (const l of this.lineasMarcadas || []) this.cm.removeLineClass(l, 'background', 'linea-error');
      this.lineasMarcadas = [];
      const nombre = (this.abierto || '').split('/').pop();
      for (const e of this.errores) {
        const archivo = String(e.archivo || this.principal).replace(/^\.\//, '');
        if (e.linea && archivo.split('/').pop() === nombre) {
          const h = this.cm.addLineClass(e.linea - 1, 'background', 'linea-error');
          this.lineasMarcadas.push(h);
        }
      }
    },
    irAError(e) {
      const archivo = String(e.archivo || this.principal).replace(/^\.\//, '');
      const a = this.archivos.find((x) => x.ruta === archivo || x.ruta.endsWith('/' + archivo)) || { ruta: this.principal };
      this.abrir(a.ruta, e.linea);
    },
    async nuevo() {
      const nombre = await preguntar({ titulo: 'Archivo nuevo', etiqueta: 'Nombre (con carpeta si quieres)', valor: 'seccion.tex', aceptar: 'Crear', ayuda: 'Se pueden editar .tex, .sty, .bib, .txt, .csv y similares.' });
      if (!nombre) return;
      try {
        await api(`api/proyectos/${this.ed.pid}/archivos/${nombre.split('/').map(encodeURIComponent).join('/')}`, { metodo: 'PUT', cuerpo: '' });
        await this.cargarLista();
        const a = this.archivos.find((x) => x.ruta.endsWith(nombre.split('/').pop()));
        if (a) this.abrir(a.ruta);
      } catch (e) { avisarError(e); }
    },
    async subirArchivos(ev) {
      const archivos = [...ev.target.files];
      ev.target.value = '';
      if (!archivos.length) return;
      try {
        const r = await subir(`api/proyectos/${this.ed.pid}/archivos`, { archivos, carpeta: '' });
        avisar(`${r.guardados.length} archivos subidos`);
        await this.cargarLista();
      } catch (e) { avisarError(e); }
    },
    async quitar(a) {
      const ok = await confirmar({ titulo: `¿Borrar ${a.ruta}?`, aceptar: 'Borrar', peligro: true });
      if (!ok) return;
      try {
        await borrar(`api/proyectos/${this.ed.pid}/archivos/${a.ruta.split('/').map(encodeURIComponent).join('/')}`);
        if (this.abierto === a.ruta) { this.abierto = null; this.cm.setValue(''); }
        await this.cargarLista();
      } catch (e) { avisarError(e); }
    },
    async hacerPrincipal(a) {
      try {
        const meta = await patch(`api/proyectos/${this.ed.pid}`, { principal: a.ruta });
        this.ed.meta.principal = meta.principal;
        avisar(`${a.ruta} es ahora el archivo principal`);
      } catch (e) { avisarError(e); }
    },
    src(ruta) { return `api/proyectos/${this.ed.pid}/f/${ruta.split('/').map(encodeURIComponent).join('/')}`; },
  },
  async mounted() {
    this.cm = markRaw(window.CodeMirror(this.$refs.cm, {
      lineNumbers: true, lineWrapping: true, matchBrackets: true, autoCloseBrackets: true, styleActiveLine: true,
      indentUnit: 2, tabSize: 2, mode: 'stex', spellcheck: true,
      extraKeys: {
        'Ctrl-S': () => this.ed.compilarAhora(), 'Cmd-S': () => this.ed.compilarAhora(),
        'Ctrl-F': 'findPersistent', 'Cmd-F': 'findPersistent',
      },
    }));
    this.guardar = retrasar(() => this.guardarYa().then(() => { if (this.ed.meta.ajustes.auto_compilar) this.ed.compilarPronto(); }), 900);
    this.cm.on('change', () => {
      if (this.ignorar) return;
      this.sucio = true;
      this.ed.marcarCambios();
      this.guardar();
    });
    this.ed.antesDeCompilar = () => this.guardarYa();
    await this.cargarLista();
    if (this.archivos.find((a) => a.ruta === this.principal)) this.abrir(this.principal);
  },
  beforeUnmount() { if (this.guardar) this.guardar.ya(); this.ed.antesDeCompilar = null; },
  template: `
  <div class="editor-latex">
    <nav class="archivos" aria-label="Archivos del proyecto">
      <div style="display:flex;gap:6px;padding:10px 10px 6px">
        <button class="btn pequeno" @click="nuevo"><icono n="mas"/>Nuevo</button>
        <input ref="subida" type="file" multiple hidden @change="subirArchivos">
        <button class="btn pequeno" @click="$refs.subida.click()"><icono n="subir"/>Subir</button>
      </div>
      <div class="grupo-arbol"><span>Código</span><span class="linea"></span></div>
      <div v-for="a in textos" :key="a.ruta" style="display:flex;align-items:center">
        <button class="archivo" :class="{activo: abierto === a.ruta}" @click="abrir(a.ruta)" :title="a.ruta">
          <icono :n="a.ruta === principal ? 'hoja' : 'archivo'"/><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ a.ruta }}</span>
          <span v-if="a.ruta === principal" class="insignia-z">principal</span>
        </button>
      </div>
      <div class="grupo-arbol"><span>Imágenes y otros</span><span class="linea"></span></div>
      <button v-for="a in otros" :key="a.ruta" class="archivo no-texto" :class="{activo: abierto === a.ruta}" @click="abrir(a.ruta)" :title="a.ruta + ' (' + tamano(a.tamano) + ')'">
        <icono :n="a.imagen ? 'imagen' : 'archivo'"/><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ a.ruta }}</span>
      </button>
    </nav>
    <section class="codigo-panel">
      <header>
        <strong style="font-size:var(--t-s)">{{ abierto || 'Elige un archivo' }}</strong>
        <span v-if="sucio" class="chip aviso-chip"><span class="punto"></span>Sin guardar</span>
        <span style="flex:1"></span>
        <template v-if="abierto">
          <button v-if="!esImagen && abierto.endsWith('.tex') && abierto !== principal" class="btn pequeno fantasma" @click="hacerPrincipal({ruta: abierto})">Usar como principal</button>
          <button class="btn icono pequeno fantasma" @click="quitar({ruta: abierto})" title="Borrar el archivo" aria-label="Borrar el archivo"><icono n="basura"/></button>
        </template>
      </header>
      <div style="position:relative;min-height:0">
        <div ref="cm" style="position:absolute;inset:0" v-show="!esImagen"></div>
        <div v-if="esImagen && abierto" style="position:absolute;inset:0;display:grid;place-items:center;background:var(--mesa);padding:20px">
          <img :src="src(abierto)" alt="" style="max-width:100%;max-height:100%;background:#fff;box-shadow:var(--sombra-hoja)" v-if="!abierto.endsWith('.pdf')">
          <p v-else class="ayuda">Los PDF se ven en la vista previa cuando el documento los incluye.</p>
        </div>
      </div>
    </section>
    <vista-pdf :url="ed.urlPdf" :version="ed.version" :editable="false" :compilando="ed.compilando" :resaltado="ed.resaltado"
               :aviso="ed.compilacion && !ed.compilacion.ok && ed.compilacion.pdf_anterior ? 'Se ve la última versión que compiló bien' : ''"
               vacio="Compila (Ctrl + S) para ver el PDF.">
      <template #pie>
        <panel-registro :compilacion="ed.compilacion" @ir="irAError"/>
      </template>
    </vista-pdf>
  </div>`,
};
