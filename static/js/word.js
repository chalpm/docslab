// SPDX-License-Identifier: AGPL-3.0-only
// Exportar un documento, artículo o tesis a Word (.docx): todo editable, con los estilos de Word.
import { post, esperarTrabajo, descargar } from './api.js';
import { tienda, avisar, avisarError } from './tienda.js';
import { tamano } from './util.js';

const { inject } = Vue;

export const DialogoWord = {
  name: 'dialogo-word',
  emits: ['cerrar'],
  setup() { return { ed: inject('ed') }; },
  data() { return { trabajando: false, progreso: 0, mensaje: '', hecho: null }; },
  computed: {
    hay() { return (tienda.estado && tienda.estado.word) || { docx: true, pandoc: true }; },
  },
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
        const t = await post(`api/proyectos/${this.ed.pid}/word`, {});
        const fin = await esperarTrabajo(t.id, { intervalo: 350, alCambiar: (x) => { this.progreso = x.progreso; if (x.mensaje) this.mensaje = x.mensaje; } });
        if (fin.estado === 'error') { avisar(fin.mensaje || 'No se pudo hacer el Word', { tipo: 'error', ms: 9000 }); return; }
        if (fin.estado !== 'terminado' || !fin.resultado) return;
        this.hecho = fin.resultado;
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
    <div class="dialogo medio dialogo-word" role="dialog" aria-modal="true" aria-labelledby="tit-docx">
      <header><div style="flex:1"><h2 id="tit-docx">Word</h2>
        <p>El documento como .docx para seguir trabajando en Word, LibreOffice o Google Docs, o para enviarlo a quien lo pida en Word.</p></div>
        <button class="btn icono fantasma" @click="$emit('cerrar')" :disabled="trabajando" aria-label="Cerrar"><icono n="cerrar"/></button></header>
      <div class="cuerpo">
        <div v-if="!hay.docx" class="mensaje error" style="grid-template-columns:1fr">
          <div>Falta el paquete de Python «python-docx». Instálalo en el entorno de DocsLab (<code>python -m pip install python-docx</code>) y reinicia DocsLab.</div>
        </div>
        <p class="ayuda">Todo se puede editar: los títulos usan los estilos «Título 1, 2, 3…» de Word, las listas y tablas son de Word, las figuras y tablas llevan su pie numerado y las citas y la bibliografía van en el estilo del proyecto. El índice, el índice de figuras y el de tablas se rellenan al abrirlo (Word pregunta si actualiza los campos: di que sí).</p>
        <p class="ayuda" v-if="hay.pandoc">Las fórmulas van como ecuaciones de Word, editables.</p>
        <p class="ayuda" v-else>Sin pandoc, las fórmulas van como imagen, con su código LaTeX como texto alternativo. Instala pandoc en el ordenador donde corre DocsLab para que sean ecuaciones de Word editables.</p>
        <p class="ayuda">El código LaTeX libre, los componentes propios y las imágenes anotadas van como imagen, tal como salen en el PDF. La maquetación no es idéntica a la del PDF: Word reparte el texto a su manera.</p>
      </div>
      <footer>
        <div class="izq progreso-imprenta" v-if="trabajando" role="status">
          <span class="ayuda">{{ mensaje }}</span>
          <div class="barra-progreso"><div :style="{width: Math.round(Math.max(0.06, progreso) * 100) + '%'}"></div></div>
        </div>
        <span v-else-if="hecho" class="izq ayuda">Listo: {{ tamano(hecho.bytes) }}<template v-if="hecho.imagenes">, {{ hecho.imagenes }} imágenes</template><template v-if="hecho.tablas">, {{ hecho.tablas }} tablas</template><template v-if="hecho.ecuaciones">, {{ hecho.ecuaciones }} fórmulas</template>.
          <button class="btn pequeno fantasma" @click="descargarOtraVez"><icono n="descargar"/>Descargar otra vez</button></span>
        <button class="btn" @click="$emit('cerrar')" :disabled="trabajando">Cerrar</button>
        <button class="btn primario" @click="generar" :disabled="trabajando || !hay.docx"><icono n="archivo"/>{{ trabajando ? 'Preparando…' : 'Preparar y descargar' }}</button>
      </footer>
    </div>
  </div>`,
};
