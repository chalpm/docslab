// SPDX-License-Identifier: AGPL-3.0-only
// Estado global: servidor, catálogo de variantes, avisos y diálogos.
import { api } from './api.js';

const { reactive } = Vue;

export const tienda = reactive({
  estado: null,          // /api/estado
  catalogo: null,        // /api/variantes
  avisos: [],
  dialogo: null,         // diálogo de confirmación o de texto
  ruta: { vista: 'inicio', pid: null, cid: null },
  componentes: {},       // componentes propios del documento abierto (modelo.componentes)
  biblioteca: null,      // resumen de los componentes del Lab (api/componentes)
  borradorLab: null,     // componente nuevo que se abre en el Lab sin guardar
  volverA: null,         // documento desde el que se abrió el Lab
});

let contador = 0;
export function avisar(texto, { tipo = 'info', ms = 3600, accion = null } = {}) {
  const id = ++contador;
  tienda.avisos.push({ id, texto, tipo, accion });
  if (ms) setTimeout(() => cerrarAviso(id), ms);
  return id;
}
export function cerrarAviso(id) {
  const i = tienda.avisos.findIndex((a) => a.id === id);
  if (i >= 0) tienda.avisos.splice(i, 1);
}
export function avisarError(e) {
  if (e && e.name === 'AbortError') return;
  console.error(e);
  avisar(e && e.message ? e.message : String(e), { tipo: 'error', ms: 7000 });
}

// Diálogos que devuelven una promesa
export function confirmar({ titulo, texto = '', aceptar = 'Aceptar', cancelar = 'Cancelar', peligro = false }) {
  return new Promise((resolver) => {
    tienda.dialogo = { tipo: 'confirmar', titulo, texto, aceptar, cancelar, peligro, resolver };
  });
}
export function preguntar({ titulo, texto = '', etiqueta = '', valor = '', aceptar = 'Aceptar', multilinea = false, ayuda = '' }) {
  return new Promise((resolver) => {
    tienda.dialogo = { tipo: 'preguntar', titulo, texto, etiqueta, valor, aceptar, multilinea, ayuda, resolver };
  });
}
export function cerrarDialogo(valor) {
  const d = tienda.dialogo;
  tienda.dialogo = null;
  if (d && d.resolver) d.resolver(valor);
}

export async function cargarEstado() {
  tienda.estado = await api('api/estado');
  return tienda.estado;
}
export async function cargarCatalogo() {
  if (!tienda.catalogo) {
    const c = await api('api/variantes');
    c.porClave = Object.fromEntries(c.variantes.map((v) => [v.clave, v]));
    tienda.catalogo = c;
  }
  return tienda.catalogo;
}

export function ir(ruta) {
  if (location.hash !== ruta) location.hash = ruta;
}
export function leerRuta() {
  const h = location.hash.replace(/^#/, '');
  const m = /^\/p\/(p-[a-z0-9]+)/.exec(h);
  if (m) { tienda.ruta = { vista: 'editor', pid: m[1], cid: null }; return; }
  const l = /^\/lab(?:\/(k-[a-z0-9]+|nuevo))?\/?$/.exec(h);
  if (l) { tienda.ruta = { vista: 'lab', pid: null, cid: l[1] || null }; return; }
  tienda.ruta = { vista: 'inicio', pid: null, cid: null };
}

export async function cargarBiblioteca() {
  try { tienda.biblioteca = await api('api/componentes'); } catch { tienda.biblioteca = tienda.biblioteca || []; }
  return tienda.biblioteca;
}
