// SPDX-License-Identifier: AGPL-3.0-only
// Utilidades sin dependencias.

export function retrasar(fn, ms) {
  let t = null;
  const envuelta = (...args) => {
    clearTimeout(t);
    t = setTimeout(() => { t = null; fn(...args); }, ms);
  };
  envuelta.cancelar = () => { clearTimeout(t); t = null; };
  envuelta.pendiente = () => t !== null;
  envuelta.ya = (...args) => { clearTimeout(t); t = null; fn(...args); };
  return envuelta;
}

export const clonar = (x) => JSON.parse(JSON.stringify(x));

export function nuevoId(prefijo = 'x') {
  const abc = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let s = '';
  const azar = crypto.getRandomValues(new Uint8Array(6));
  for (const b of azar) s += abc[b % abc.length];
  return `${prefijo}-${s}`;
}

export function fecha(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const hoy = new Date();
  const mismoDia = d.toDateString() === hoy.toDateString();
  const hora = d.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
  if (mismoDia) return `hoy, ${hora}`;
  const ayer = new Date(hoy); ayer.setDate(hoy.getDate() - 1);
  if (d.toDateString() === ayer.toDateString()) return `ayer, ${hora}`;
  return d.toLocaleDateString('es', { day: 'numeric', month: 'short', year: d.getFullYear() === hoy.getFullYear() ? undefined : 'numeric' });
}

export function tamano(bytes) {
  if (bytes == null) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// Longitudes: mm, cm, in, pt → puntos (pt de TeX, 72.27 por pulgada)
const PT = { pt: 1, mm: 72.27 / 25.4, cm: 72.27 / 2.54, in: 72.27, bp: 72.27 / 72, pc: 12, dd: 1238 / 1157, cc: 14856 / 1157 };
export function aPt(valor) {
  const m = /^\s*(-?\d*\.?\d+)\s*(pt|mm|cm|in|bp|pc|dd|cc)?\s*$/.exec(String(valor ?? ''));
  if (!m) return null;
  return parseFloat(m[1]) * (PT[m[2] || 'pt'] || 1);
}
export function aMm(valor) {
  const pt = aPt(valor);
  return pt == null ? null : pt / PT.mm;
}
export const esDimension = (v) => /^\s*-?\d*\.?\d+\s*(mm|cm|in|pt|em|ex|bp|pc|sp|dd|cc)\s*$/.test(String(v ?? ''));
export const esNumero = (v) => /^\s*-?\d*\.?\d+\s*$/.test(String(v ?? ''));

// Coordenadas de capa: fracción (0.25) o longitud (12cm) → fracción del lienzo
export function aFraccion(valor, referenciaPt) {
  if (valor === '' || valor == null) return null;
  if (esNumero(valor)) return parseFloat(valor);
  const pt = aPt(valor);
  return pt == null ? null : pt / referenciaPt;
}

export const redondear = (x, d = 4) => Math.round(x * 10 ** d) / 10 ** d;
export const limitar = (x, a, b) => Math.min(b, Math.max(a, x));

export function textoPlano(t, max = 60) {
  const s = String(t ?? '')
    .replace(/\{\{.*?\}\}/gs, '')
    .replace(/\*\*|\*|`|\^|~/g, '')
    .replace(/\\[a-zA-Z]+\*?(\[[^\]]*\])?/g, '')
    .replace(/[{}$]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  return s.length > max ? s.slice(0, max - 1) + '…' : s;
}

export function recortar(t, max = 32) {
  const s = String(t ?? '').trim();
  return s.length > max ? s.slice(0, max - 1).trimEnd() + '…' : s;
}

export function copiarTexto(texto) {
  if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(texto);
  const ta = document.createElement('textarea');
  ta.value = texto;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); } finally { ta.remove(); }
  return Promise.resolve();
}

export function nombreArchivo(ruta) {
  return String(ruta || '').split('/').pop();
}

// Proporción ancho/alto de un lienzo (para dibujar hojas proporcionales)
export function proporcion(ancho, alto) {
  const a = aPt(ancho), b = aPt(alto);
  return a && b ? a / b : 841 / 1189;
}
