// Errores y avisos de la última compilación.
import { tienda } from './tienda.js';

const TIPOS_AVISO = {
  desborde: 'Algo no cabe', archivo: 'Falta un archivo', caracter: 'Carácter sin glifo', plantilla: 'Plantilla', paginas: 'Páginas',
};

// Explicaciones en lenguaje llano para los errores más frecuentes de LaTeX
function explicar(msg) {
  const m = String(msg || '');
  if (/Undefined control sequence/.test(m)) return 'Hay una orden de LaTeX que no existe (¿una barra invertida \\ de más o mal escrita?).';
  if (/Missing \$ inserted/.test(m)) return 'Un símbolo como _ o ^ solo vale dentro de matemáticas ($…$). Si el texto es simple, revisa el formato del proyecto.';
  if (/Missing \} inserted|Extra \}|Runaway argument|Paragraph ended before/.test(m)) return 'Las llaves { } no están equilibradas.';
  const falta = /File `([^']+)' not found/.exec(m);
  if (falta) return explicarFalta(falta[1]);
  if (/Misplaced alignment tab/.test(m)) return 'Hay un & fuera de una tabla: escríbelo como \\& en modo LaTeX.';
  if (/Dimension too large/.test(m)) return 'Una medida es demasiado grande (¿un tamaño o escala exagerados?).';
  if (/Illegal unit of measure/.test(m)) return 'Una medida no tiene unidad válida (usa mm, cm, pt, em…).';
  return '';
}

// un archivo que no se encuentra: un paquete de LaTeX sin instalar o una imagen que falta
function explicarFalta(archivo) {
  const ext = (/\.([a-z0-9]+)$/i.exec(archivo) || [])[1] || '';
  if (/^(png|jpe?g|pdf|eps|gif|svg|tiff?)$/i.test(ext)) return 'Falta una imagen: súbela en «Imágenes» o revisa el nombre del archivo.';
  const parte = /\.code\.tex$/i.test(archivo);          // p. ej. una biblioteca de TikZ
  if (!/^(sty|cls|def|cfg|fd|ldf|clo|ltx)$/i.test(ext) && !parte) return 'Falta un archivo que el documento intenta cargar.';
  const paquete = parte ? '' : archivo.replace(/\.[^.]+$/, '');
  const que = parte ? 'parte de un paquete' : 'un paquete';
  const est = tienda.estado || {};
  if (est.miktex) {
    return `Es ${que} de LaTeX que MiKTeX no tiene instalado. DocsLab le pide que instale solo lo que falte; si no lo consiguió (¿sin internet?), abre MiKTeX Console → Packages, busca «${paquete || archivo}», instálalo y vuelve a compilar. En Settings puedes elegir «Always install missing packages on-the-fly».`;
  }
  const orden = paquete ? `tlmgr install ${paquete}` : `tlmgr search --global --file ${archivo}`;
  return `Es ${que} de LaTeX que falta en tu instalación. Con TeX Live: ${orden} (en Ubuntu o Debian suele venir en texlive-latex-extra). Luego vuelve a compilar.`;
}

export const PanelRegistro = {
  name: 'panel-registro',
  props: { compilacion: Object, nombres: Function, ajustando: Boolean },
  emits: ['ir', 'ajustar'],
  data: () => ({ abierto: false, verAvisos: false }),
  computed: {
    errores() { return (this.compilacion && this.compilacion.errores) || []; },
    avisos() { return (this.compilacion && this.compilacion.avisos) || []; },
    hay() { return this.errores.length || this.avisos.length; },
    noCabe() { return (this.compilacion && this.compilacion.paginas > 1) || this.avisos.some((a) => /no cabe/.test(a.mensaje)); },
  },
  watch: {
    errores(e) { if (e.length) this.abierto = true; },
  },
  methods: {
    explicar,
    tipoAviso(t) { return TIPOS_AVISO[t] || 'Aviso'; },
    nombre(id) { return this.nombres ? this.nombres(id) : id; },
  },
  template: `
  <section class="registro" v-if="compilacion && (hay || abierto)">
    <header>
      <button class="btn pequeno fantasma" @click="abierto = !abierto" :aria-expanded="abierto">
        <icono :n="errores.length ? 'alerta' : 'info'"/>
        <span v-if="errores.length">{{ errores.length }} {{ errores.length === 1 ? 'error' : 'errores' }}</span>
        <span v-else-if="avisos.length">{{ avisos.length }} {{ avisos.length === 1 ? 'aviso' : 'avisos' }}</span>
        <span v-else>Sin errores</span>
      </button>
      <span class="ayuda" v-if="compilacion.segundos">Última compilación: {{ compilacion.segundos }} s, {{ compilacion.pasadas }} {{ compilacion.pasadas === 1 ? 'pasada' : 'pasadas' }}<template v-if="compilacion.paginas">, {{ compilacion.paginas }} {{ compilacion.paginas === 1 ? 'página' : 'páginas' }}</template></span>
      <span style="flex:1"></span>
      <button v-if="abierto" class="btn icono pequeno fantasma" @click="abierto = false" aria-label="Cerrar el registro"><icono n="cerrar"/></button>
    </header>
    <div class="lista-mensajes" v-if="abierto">
      <div v-for="(e, i) in errores" :key="'e' + i" class="mensaje error">
        <span class="icono-msg"><icono n="alerta"/></span>
        <div>
          <strong>{{ e.mensaje }}</strong>
          <span v-if="e.linea && !e.elemento" class="ayuda"> (línea {{ e.linea }}<template v-if="e.archivo"> de {{ String(e.archivo).replace(/^\\.\\//, '') }}</template>)</span>
          <p v-if="explicar(e.mensaje)" class="ayuda">{{ explicar(e.mensaje) }}</p>
          <pre v-if="e.contexto">{{ e.contexto }}</pre>
          <div class="acciones-msg">
            <button v-if="e.elemento" class="btn pequeno" @click="$emit('ir', e)"><icono n="usar"/>Ir a «{{ nombre(e.elemento) }}»</button>
            <button v-else-if="e.linea" class="btn pequeno" @click="$emit('ir', e)"><icono n="usar"/>Ir a la línea {{ e.linea }}</button>
          </div>
        </div>
      </div>
      <div v-if="noCabe && !errores.length" class="mensaje aviso-msg">
        <span class="icono-msg"><icono n="encajar"/></span>
        <div><strong>El contenido no cabe en una página.</strong>
          <p class="ayuda">DocsLab puede buscar el tamaño de letra más grande con el que todo cabe (se puede deshacer).</p>
          <div class="acciones-msg"><button class="btn pequeno primario" :disabled="ajustando" @click="$emit('ajustar')"><icono n="encajar"/>Ajustar a una página</button></div></div>
      </div>
      <template v-if="avisos.length">
        <button class="btn pequeno fantasma" style="justify-self:start" @click="verAvisos = !verAvisos">{{ verAvisos ? 'Ocultar' : 'Ver' }} {{ avisos.length }} {{ avisos.length === 1 ? 'aviso' : 'avisos' }}</button>
        <template v-if="verAvisos">
          <div v-for="(a, i) in avisos" :key="'a' + i" class="mensaje aviso-msg">
            <span class="icono-msg"><icono n="info"/></span>
            <div><strong>{{ tipoAviso(a.tipo) }}</strong><span v-if="a.veces > 1" class="ayuda"> ({{ a.veces }} veces)</span>
              <pre>{{ a.mensaje }}</pre></div>
          </div>
        </template>
      </template>
    </div>
  </section>`,
};
