// SPDX-License-Identifier: AGPL-3.0-only
// Exportar el documento a PowerPoint (.pptx): todo editable (texto, formas e imágenes, con animaciones) o como imagen.
import { post, esperarTrabajo, descargar } from './api.js';
import { tienda, avisar, avisarError } from './tienda.js';
import { tamano } from './util.js';

const { inject } = Vue;

export const DialogoPowerpoint = {
  name: 'dialogo-powerpoint',
  emits: ['cerrar'],
  setup() { return { ed: inject('ed') }; },
  data() {
    const previas = (this.ed && this.ed.meta && this.ed.meta.ajustes && this.ed.meta.ajustes.powerpoint) || {};
    return { modo: previas.modo || 'editable', alta: !!previas.alta, trabajando: false, progreso: 0, mensaje: '', hecho: null };
  },
  computed: {
    hay() { return (tienda.estado && tienda.estado.powerpoint) || { pptx: true, editable: true, imagen: true }; },
    modoEfectivo() { return this.modo === 'editable' && !this.hay.editable ? 'imagen' : this.modo; },
  },
  watch: { modo() { this.hecho = null; }, alta() { this.hecho = null; } },
  methods: {
    tamano,
    async generar() {
      if (this.trabajando) return;
      this.trabajando = true;
      this.progreso = 0.04;
      this.mensaje = 'Preparando…';
      this.hecho = null;
      try {
        if (this.ed.guardarAhora && this.ed.modelo) await this.ed.guardarAhora();
        if (this.ed.antesDeCompilar) await this.ed.antesDeCompilar();
        const t = await post(`api/proyectos/${this.ed.pid}/powerpoint`, { modo: this.modoEfectivo, alta: this.alta });
        const fin = await esperarTrabajo(t.id, { intervalo: 350, alCambiar: (x) => { this.progreso = x.progreso; if (x.mensaje) this.mensaje = x.mensaje; } });
        if (fin.estado === 'error') { avisar(fin.mensaje || 'No se pudo hacer el PowerPoint', { tipo: 'error', ms: 9000 }); return; }
        if (fin.estado !== 'terminado' || !fin.resultado) return;
        this.hecho = fin.resultado;
        if (this.ed.meta) this.ed.meta.ajustes = { ...(this.ed.meta.ajustes || {}), powerpoint: { modo: this.modo, alta: this.alta } };
        for (const n of fin.resultado.notas || []) avisar(n, { ms: 9000 });
        descargar(`${fin.resultado.url}?descargar=1`);
      } catch (e) {
        avisarError(e);
      } finally {
        this.trabajando = false;
      }
    },
    descargarOtraVez() { if (this.hecho) descargar(`${this.hecho.url}?descargar=1`); },
  },
  template: `
  <div class="fondo-dialogo" @mousedown.self="!trabajando && $emit('cerrar')" @keydown.esc="!trabajando && $emit('cerrar')">
    <div class="dialogo medio dialogo-powerpoint" role="dialog" aria-modal="true" aria-labelledby="tit-pptx">
      <header><div style="flex:1"><h2 id="tit-pptx">PowerPoint</h2>
        <p>Una diapositiva por cada página, del mismo tamaño, para presentar en pantalla, enviar a un congreso que pide .pptx o retocar en PowerPoint, Keynote o Google Slides.</p></div>
        <button class="btn icono fantasma" @click="$emit('cerrar')" :disabled="trabajando" aria-label="Cerrar"><icono n="cerrar"/></button></header>
      <div class="cuerpo">
        <div v-if="!hay.pptx" class="mensaje error" style="grid-template-columns:1fr">
          <div>Falta el paquete de Python «python-pptx». Instálalo en el entorno de DocsLab (<code>python -m pip install python-pptx</code>) y reinicia DocsLab.</div>
        </div>
        <div class="opciones-pptx" role="radiogroup" aria-label="Cómo va el texto">
          <label class="opcion-pptx" :class="{activa: modoEfectivo === 'editable', desactivada: !hay.editable}">
            <input type="radio" value="editable" v-model="modo" :disabled="!hay.editable">
            <span><strong>Editable</strong>
              <template v-if="hay.todo_editable !== false">
                <span class="ayuda">Todo se puede cambiar: el texto en cuadros de texto, las cajas, bandas y líneas como formas de PowerPoint y cada imagen por separado. Solo van como imagen, una por pieza, las fórmulas, los gráficos vectoriales con letras y los degradados.</span>
                <span class="ayuda">Lleva las animaciones y transiciones que pongas en el inspector («Animación en PowerPoint»).</span>
              </template>
              <span class="ayuda" v-else>Cada línea de texto es un cuadro de texto; el resto va en una imagen de fondo. Instala el paquete de Python «pymupdf» para que también sean editables las imágenes y las formas.</span>
              <span class="ayuda" v-if="!hay.editable">Necesita PyMuPDF (o Ghostscript) y Poppler en el ordenador donde corre DocsLab.</span></span>
          </label>
          <label class="opcion-pptx" :class="{activa: modoEfectivo === 'imagen'}">
            <input type="radio" value="imagen" v-model="modo">
            <span><strong>Imagen</strong>
              <span class="ayuda">Cada página como una imagen: se ve exactamente igual que el PDF, pero no se puede editar. Lleva las transiciones, no las animaciones.</span></span>
          </label>
        </div>
        <label class="interruptor"><span class="texto">Imágenes en alta resolución</span>
          <input type="checkbox" v-model="alta"><span class="pista"></span></label>
        <span class="ayuda" style="margin-top:-8px">Para proyectarlo grande o imprimirlo desde PowerPoint. El archivo pesa más.</span>
        <p class="ayuda">La letra se pide como Arial, Times New Roman… según la del documento; si en tu ordenador falta alguna, PowerPoint pone otra parecida. Para imprimir, el PDF sigue siendo lo mejor.</p>
      </div>
      <footer>
        <div class="izq progreso-imprenta" v-if="trabajando" role="status">
          <span class="ayuda">{{ mensaje }}</span>
          <div class="barra-progreso"><div :style="{width: Math.round(Math.max(0.06, progreso) * 100) + '%'}"></div></div>
        </div>
        <span v-else-if="hecho" class="izq ayuda">Listo: {{ tamano(hecho.bytes) }}<template v-if="hecho.cuadros">, {{ hecho.cuadros }} cuadros de texto</template><template v-if="hecho.formas">, {{ hecho.formas }} formas</template><template v-if="hecho.imagenes">, {{ hecho.imagenes }} imágenes</template><template v-if="hecho.animadas">, {{ hecho.animadas }} animaciones</template>.
          <button class="btn pequeno fantasma" @click="descargarOtraVez"><icono n="descargar"/>Descargar otra vez</button></span>
        <button class="btn" @click="$emit('cerrar')" :disabled="trabajando">Cerrar</button>
        <button class="btn primario" @click="generar" :disabled="trabajando || !hay.pptx"><icono n="diapositiva"/>{{ trabajando ? 'Preparando…' : 'Preparar y descargar' }}</button>
      </footer>
    </div>
  </div>`,
};
