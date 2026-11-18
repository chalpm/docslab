// SPDX-License-Identifier: AGPL-3.0-only
// Ayudas para recorrer y modificar el modelo del póster en el navegador.
import { nuevoId, clonar, textoPlano, nombreArchivo } from './util.js';
import { tienda } from './tienda.js';

// Índice id → { tipo, obj, lista, i, padre, ... }
export function indexar(m) {
  const idx = new Map();
  idx.set('poster', { tipo: 'poster', obj: m });
  idx.set('cabecera', { tipo: 'cabecera', obj: m.cabecera, titulo: m.clase === 'presentacion' ? 'Portada: título y autores' : esFlujo(m) ? 'Título y autores' : '' });
  // los logos se eligen y se estiran en la vista previa
  idx.set('cabecera-logo-izq', { tipo: 'logo', obj: m.cabecera, clave: 'tam_logo_izquierdo', lado: 'izquierdo' });
  idx.set('cabecera-logo-der', { tipo: 'logo', obj: m.cabecera, clave: 'tam_logo_derecho', lado: 'derecho' });
  idx.set('pie', { tipo: 'pie', obj: m.pie });
  idx.set('documento', { tipo: 'documento', obj: m.documento, tesis: m.clase === 'tesis' });
  const cuenta = {};
  const paginas = m.clase === 'presentacion' ? (m.paginas || []) : [];
  const porId = new Map();
  paginas.forEach((pg, i) => { idx.set(pg.id, { tipo: 'pagina', obj: pg, lista: m.paginas, i }); porId.set(pg.id, pg); });
  (m.filas || []).forEach((f, i) => {
    const n = cuenta[f.pag || ''] = (cuenta[f.pag || ''] ?? -1) + 1;
    idx.set(f.id, { tipo: 'fila', obj: f, lista: m.filas, i, n, pagina: porId.get(f.pag) });
    (f.columnas || []).forEach((c, j) => {
      idx.set(c.id, { tipo: 'columna', obj: c, lista: f.columnas, i: j, padre: f, fila: f, pagina: porId.get(f.pag) });
      (c.bloques || []).forEach((b, k) => {
        idx.set(b.id, { tipo: 'bloque', obj: b, lista: c.bloques, i: k, padre: c, fila: f, columna: c, pagina: porId.get(f.pag) });
        (b.elementos || []).forEach((e, l) => {
          idx.set(e.id, { tipo: 'elemento', obj: e, lista: b.elementos, i: l, padre: b, fila: f, columna: c, bloque: b, pagina: porId.get(f.pag) });
        });
      });
    });
  });
  (m.capas || []).forEach((capa, i) => {
    idx.set(capa.id, { tipo: 'capa', obj: capa, lista: m.capas, i });
    (capa.elementos || []).forEach((it, j) => {
      idx.set(it.id, { tipo: 'item', obj: it, lista: capa.elementos, i: j, padre: capa, capa });
    });
  });
  return idx;
}

export function ancestros(info) {
  if (!info) return [];
  return [info.pagina, info.fila, info.columna, info.bloque, info.capa].filter(Boolean).map((o) => o.id);
}

// ---------------------------------------------------------------- fábricas
export function nuevoElemento(clave) {
  const v = tienda.catalogo.porClave[clave];
  const e = { id: nuevoId('e'), tipo: clave, visible: true };
  for (const c of v.campos) e[c.nombre] = c.defecto !== undefined ? clonar(c.defecto) : '';
  return e;
}
// Elemento de un componente propio (Componente Lab) con sus valores iniciales
export function nuevoElementoComponente(c) {
  const e = { id: nuevoId('e'), tipo: `cmp:${c.id}`, visible: true };
  for (const campo of c.campos || []) e[campo.nombre] = campo.defecto !== undefined ? clonar(campo.defecto) : '';
  return e;
}
export function nuevoBloque(titulo = 'Sección nueva', conTexto = true) {
  const b = { id: nuevoId('b'), visible: true, titulo, mostrar_titulo: true, estilo: '', numero: '', estirar: false,
    opciones: {}, elementos: [] };
  if (conTexto) {
    const e = nuevoElemento('txtJustificado');
    e.texto = 'Escribe aquí el texto de la sección.';
    b.elementos.push(e);
  }
  return b;
}
export function nuevaColumna(conBloque = true) {
  return { id: nuevoId('c'), abarca: 1, distribucion: 'repartir', bloques: conBloque ? [nuevoBloque()] : [] };
}
export function nuevaFila(n = 2) {
  return { id: nuevoId('f'), visible: true, alto: 'auto', rejilla: n, separacion: '', despues: '', igualar: true,
    columnas: Array.from({ length: n }, () => nuevaColumna()) };
}
// Diapositiva nueva (presentaciones)
export function nuevaPagina(nombre = 'Diapositiva nueva', diseno = 'contenido') {
  return { ...clonar(tienda.catalogo.pagina_defecto || {}), id: nuevoId('p'), nombre, diseno };
}
// Caja suelta de la cuadrícula: se coloca en cualquier punto de la página
export function nuevoBloqueLibre(que = 'texto') {
  const b = nuevoBloque(que === 'caja' ? 'Caja nueva' : '', false);
  Object.assign(b, { libre: true, ...clonar(tienda.catalogo.libre_defecto || { x: 0.1, y: 0.15, ancho: 0.3 }) });
  if (que !== 'caja') { b.mostrar_titulo = false; b.estilo = 'ninguno'; b.opciones = { relleno: '0pt' }; }
  const e = nuevoElemento(que === 'imagen' ? 'imgAncho' : 'txtJustificado');
  if (que !== 'imagen') e.texto = 'Texto nuevo';
  b.elementos.push(e);
  return b;
}
// Sección nueva de un documento, artículo o tesis
export function nuevaSeccion(nivel = 1, titulo = 'Sección nueva') {
  const b = nuevoBloque(titulo, true);
  b.nivel = nivel;
  return b;
}
export const NOMBRES_CLASE = { poster: 'Póster', presentacion: 'Presentación', documento: 'Documento', paper: 'Artículo', tesis: 'Tesis', latex: 'Código LaTeX' };
export const ARTICULO_CLASE = { poster: 'el póster', presentacion: 'la presentación', documento: 'el documento', paper: 'el artículo', tesis: 'la tesis', latex: 'el documento' };
export const NOMBRES_DISENO = { contenido: 'Título y contenido', portada: 'Portada', seccion: 'Título de sección', vacia: 'En blanco' };
export const esFlujo = (m) => ['documento', 'paper', 'tesis'].includes(m && m.clase);
export function nombreNivel(m, nivel) {
  const n = (tienda.catalogo.niveles || {})[m.clase] || ['Sección', 'Subsección', 'Apartado'];
  return n[Math.max(1, Math.min(n.length, Number(nivel) || 1)) - 1];
}

export function nuevaCapa(nombre = 'Capa nueva', z = 5) {
  return { id: nuevoId('capa'), nombre, z, visible: true, opacidad: 1, elementos: [] };
}
export function nuevoItem(tipo = 'texto') {
  const base = { id: nuevoId('a'), visible: true, tipo, x: 0.5, y: 0.5, ancla: 'center', ancho: '', alto: '',
    rotacion: 0, opacidad: 1, pagina: '' };
  const extra = clonar((tienda.catalogo.item_tipos || {})[tipo] || {});
  const it = { ...base, ...extra };
  if (tipo === 'texto') { it.texto = 'Texto nuevo'; it.escala = 2; }
  if (tipo === 'forma') { it.fondo = 'acento!25'; }
  if (tipo === 'latex') { it.codigo = '\\textbf{LaTeX}'; }
  return it;
}

// Copia profunda con ids nuevos (para duplicar)
export function conIdsNuevos(obj) {
  const c = clonar(obj);
  const renovar = (o) => {
    if (Array.isArray(o)) { o.forEach(renovar); return; }
    if (o && typeof o === 'object') {
      if (typeof o.id === 'string' && /^[a-z]+-[a-z0-9]+$/.test(o.id) && !['fondo', 'frente'].includes(o.id)) {
        o.id = nuevoId(o.id.split('-')[0]);
      }
      Object.values(o).forEach(renovar);
    }
  };
  renovar(c);
  return c;
}

// ---------------------------------------------------------------- nombres
const NOMBRES_ITEM = { imagen: 'Imagen', texto: 'Texto', forma: 'Forma', latex: 'Código LaTeX' };
const NOMBRES_FORMA = { rectangulo: 'Rectángulo', circulo: 'Círculo', elipse: 'Elipse', linea: 'Línea', flecha: 'Flecha' };

export function variante(e) {
  const tipo = e && typeof e.tipo === 'string' ? e.tipo : '';
  if (tipo.startsWith('cmp:')) {
    const c = (tienda.componentes || {})[tipo.slice(4)];
    if (!c) return null;
    return { clave: tipo, codigo: 'C', grupo: 'componente', nombre: c.nombre || 'Componente', nota: c.descripcion || '',
      campos: c.campos || [], componente: c };
  }
  return tienda.catalogo && tienda.catalogo.porClave[tipo];
}

export function nombreNodo(info) {
  if (!info) return '';
  const o = info.obj;
  switch (info.tipo) {
    case 'poster': return NOMBRES_CLASE[o.clase] || 'Póster';
    case 'documento': return o.portada && info.tesis ? 'Portada, resumen e índices' : 'Resumen e índices';
    case 'pagina': return `${info.i + 1}. ${textoPlano(o.nombre, 40) || NOMBRES_DISENO[o.diseno] || 'Diapositiva'}`;
    case 'cabecera': return info.titulo || 'Cabecera';
    case 'logo': return `Logo ${info.lado}`;
    case 'pie': return 'Pie del póster';
    case 'fila': return `Fila ${(info.n ?? info.i) + 1}`;
    case 'columna': return `Columna ${info.i + 1}`;
    case 'bloque': {
      const t = textoPlano(o.titulo, 48);
      if (t) return t;
      if (o.libre && (o.elementos || []).length === 1) {          // un texto o una imagen sueltos
        const e = o.elementos[0], v = variante(e);
        if (v && v.grupo === 'imagen') return e.archivo ? nombreArchivo(e.archivo) : 'Imagen suelta';
        return textoPlano(e.texto || (Array.isArray(e.items) ? e.items[0] : ''), 40) || (v ? v.nombre : 'Caja suelta');
      }
      return o.libre ? 'Caja suelta' : 'Caja sin título';
    }
    case 'elemento': { const v = variante(o); return v ? v.nombre : (String(o.tipo).startsWith('cmp:') ? 'Componente que falta' : o.tipo); }
    case 'capa': return o.nombre || o.id;
    case 'item':
      if (o.tipo === 'imagen') return o.archivo ? nombreArchivo(o.archivo) : 'Imagen sin elegir';
      if (o.tipo === 'texto') return textoPlano(o.texto, 40) || 'Texto';
      if (o.tipo === 'forma') return NOMBRES_FORMA[o.forma] || 'Forma';
      return NOMBRES_ITEM[o.tipo] || o.tipo;
    default: return '';
  }
}

export function detalleNodo(info) {
  const o = info.obj;
  switch (info.tipo) {
    case 'fila': {
      const n = (o.columnas || []).length;
      const alto = o.alto === 'llenar' ? ', llena el alto' : (o.alto && o.alto !== 'auto' ? `, ${o.alto}` : '');
      return `${n} ${n === 1 ? 'columna' : 'columnas'}${alto}`;
    }
    case 'columna': return (o.abarca || 1) > 1 ? `ocupa ${o.abarca}` : '';
    case 'pagina': return o.libre ? 'lienzo libre' : (o.diseno !== 'contenido' ? (NOMBRES_DISENO[o.diseno] || '').toLowerCase() : '');
    case 'bloque': return o.libre ? 'suelta' : (o.estilo ? o.estilo : '');
    case 'elemento': {
      const t = o.texto || o.pie || o.titulo || o.cita || o.entradilla || o.cifra || o.codigo || (Array.isArray(o.items) ? o.items[0] : '') || '';
      return textoPlano(t, 38);
    }
    default: return '';
  }
}

export function iconoNodo(info) {
  switch (info.tipo) {
    case 'poster': return 'hoja';
    case 'documento': return 'libro';
    case 'pagina': return 'diapositiva';
    case 'cabecera': return 'cabecera';
    case 'pie': return 'pie';
    case 'fila': return 'fila';
    case 'columna': return 'columna';
    case 'bloque': return 'caja';
    case 'capa': return 'capas';
    case 'elemento': {
      const v = variante(info.obj);
      if (!v) return 'texto';
      if (v.grupo === 'imagen') return 'imagen';
      if (v.grupo === 'caja') return 'caja';
      if (v.clave === 'latex') return 'codigo';
      if (v.grupo === 'componente') return 'pieza';
      return 'texto';
    }
    case 'item': return { imagen: 'imagen', texto: 'texto', forma: 'forma', latex: 'codigo' }[info.obj.tipo] || 'texto';
    default: return 'info';
  }
}

// ¿El elemento es una caja de texto con título opcional?
export function tieneTitulo(e) {
  const v = variante(e);
  return !!(v && v.campos.some((c) => c.nombre === 'mostrar_titulo'));
}

// Campos de imagen de un elemento
export function camposImagen(e) {
  const v = variante(e);
  return v ? v.campos.filter((c) => c.tipo === 'imagen').map((c) => c.nombre) : [];
}

// Mover un nodo a otra lista (arrastrar y soltar)
export function mover(listaOrigen, iOrigen, listaDestino, iDestino) {
  const [obj] = listaOrigen.splice(iOrigen, 1);
  let destino = iDestino;
  if (listaOrigen === listaDestino && iOrigen < iDestino) destino -= 1;
  listaDestino.splice(Math.max(0, Math.min(destino, listaDestino.length)), 0, obj);
  return obj;
}
