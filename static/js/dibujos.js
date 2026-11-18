// Pequeños dibujos SVG que imitan los estilos de la plantilla (cajas, cabeceras, pósters).

const mezclar = (hexA, hexB, t) => {
  const a = parseInt(hexA, 16), b = parseInt(hexB, 16);
  const c = (s) => Math.round(((a >> s) & 255) * t + ((b >> s) & 255) * (1 - t));
  return ((c(16) << 16) | (c(8) << 8) | c(0)).toString(16).padStart(6, '0');
};
const H = (x) => '#' + String(x || '000000').replace('#', '');

export const NOMBRES_ESTILO = {
  barra: 'Barra', linea: 'Línea', caja: 'Etiqueta', simple: 'Simple', borde: 'Borde', sombra: 'Sombra',
  resaltado: 'Resaltado', invertido: 'Invertido', contorno: 'Contorno', cita: 'Cita', nota: 'Nota', ninguno: 'Ninguno',
};
export const NOMBRES_CABECERA = { banda: 'Banda', clara: 'Clara', minima: 'Mínima', degradado: 'Degradado', imagen: 'Imagen' };

// Caja de muestra (120 × 70) con los colores del tema
export function svgCaja(estilo, c, { titulo = true } = {}) {
  const P = H(c.primario), S = H(c.secundario), A = H(c.acento), F = H(c.fondo), B = H(c.fondo_bloque);
  const T = H(c.texto), K = H(c.contraste), tinte = '#' + mezclar(c.acento, c.fondo, 0.18);
  let fondo = '', cabeza = '', tituloColor = P, lineas = T, extra = '';
  const x = 6, y = 8, w = 108, h = 56;
  switch (estilo) {
    case 'barra': case 'sombra':
      fondo = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3" fill="${B}"/>`;
      if (titulo) cabeza = `<path d="M${x} ${y + 3}a3 3 0 0 1 3-3h${w - 6}a3 3 0 0 1 3 3v9h-${w}z" fill="${P}"/>`;
      tituloColor = K;
      if (estilo === 'sombra') extra = `<rect x="${x + 2}" y="${y + 3}" width="${w}" height="${h}" rx="3" fill="#000" opacity=".16"/>`;
      break;
    case 'linea':
      if (titulo) cabeza = `<path d="M${x} ${y + 15}h${w}" stroke="${A}" stroke-width="2"/>`;
      break;
    case 'caja':
      fondo = `<rect x="${x}" y="${y + 4}" width="${w}" height="${h - 4}" rx="3" fill="${F}" stroke="${P}" stroke-width="1.3"/>`;
      if (titulo) cabeza = `<rect x="${x + 8}" y="${y - 1}" width="46" height="11" rx="2.5" fill="${P}"/>`;
      tituloColor = K;
      break;
    case 'simple':
      fondo = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3" fill="${B}"/>`;
      break;
    case 'borde':
      fondo = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3" fill="${F}" stroke="${P}" stroke-width="1.3"/>`;
      if (titulo) cabeza = `<path d="M${x} ${y + 13}h${w}" stroke="${P}" stroke-width=".8"/>`;
      break;
    case 'resaltado':
      fondo = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3" fill="${tinte}"/>`;
      tituloColor = A;
      break;
    case 'invertido':
      fondo = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3" fill="${P}"/>`;
      tituloColor = K; lineas = K;
      break;
    case 'contorno':
      fondo = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3" fill="${F}" stroke="${S}" stroke-width="1.3"/>`;
      if (titulo) cabeza = `<path d="M${x} ${y + 3}a3 3 0 0 1 3-3h${w - 6}a3 3 0 0 1 3 3v9h-${w}z" fill="${S}"/>`;
      tituloColor = K;
      break;
    case 'cita':
      fondo = `<rect x="${x}" y="${y}" width="3" height="${h}" fill="${A}"/>`;
      tituloColor = A;
      break;
    case 'nota':
      fondo = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="2" fill="${B}"/><rect x="${x}" y="${y}" width="3" height="${h}" fill="${S}"/>`;
      tituloColor = S;
      break;
    default: // ninguno
      break;
  }
  const dx = estilo === 'cita' || estilo === 'nota' ? 10 : 8;
  const tit = titulo ? `<rect x="${x + dx + (estilo === 'caja' ? 4 : 0)}" y="${estilo === 'caja' ? y + 3 : y + 5}" width="${estilo === 'caja' ? 30 : 44}" height="${estilo === 'caja' ? 3.6 : 4.2}" rx="1.5" fill="${tituloColor}"/>` : '';
  const y0 = titulo ? y + (estilo === 'caja' ? 20 : 22) : y + 10;
  let cuerpo = '';
  for (let i = 0; i < 4; i++) {
    const yy = y0 + i * 8;
    if (yy > y + h - 6) break;
    const largo = i === 3 ? 52 : w - dx * 2;
    cuerpo += `<rect x="${x + dx}" y="${yy}" width="${largo}" height="2.6" rx="1.3" fill="${lineas}" opacity="${estilo === 'cita' ? 0.55 : 0.42}"${estilo === 'cita' ? ` transform="skewX(-12) translate(${yy * 0.2} 0)"` : ''}/>`;
  }
  return `<svg viewBox="0 0 120 72" xmlns="http://www.w3.org/2000/svg"><rect width="120" height="72" rx="4" fill="${F}"/>${extra}${fondo}${cabeza}${tit}${cuerpo}</svg>`;
}

// Esquema de un póster: proporción, cabecera, columnas y cajas
export function svgPoster({ ancho = 841, alto = 1189, columnas = 3, colores, estiloCaja = 'barra', cabecera = 'banda' }) {
  const W = 180, Hh = Math.round(W * alto / ancho);
  const m = 8, gap = 5;
  const P = H(colores.primario), S = H(colores.secundario), A = H(colores.acento), F = H(colores.fondo), B = H(colores.fondo_bloque);
  const K = H(colores.contraste), T = H(colores.texto);
  let s = `<svg viewBox="0 0 ${W} ${Hh}" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="dg" x1="0" x2="1"><stop offset="0" stop-color="${P}"/><stop offset="1" stop-color="${S}"/></linearGradient></defs>`;
  s += `<rect width="${W}" height="${Hh}" fill="${F}"/>`;
  const altoCab = Math.max(16, Math.round(Hh * 0.11));
  const cw = W - 2 * m;
  if (cabecera === 'banda' || cabecera === 'degradado' || cabecera === 'imagen') {
    const relleno = cabecera === 'degradado' ? 'url(#dg)' : cabecera === 'imagen' ? '#2b3138' : P;
    s += `<rect x="${m}" y="${m}" width="${cw}" height="${altoCab}" rx="2" fill="${relleno}"/>`;
    if (cabecera === 'imagen') s += `<path d="M${m} ${m + altoCab}l30-14 22 9 30-12 40 17z" fill="#55606b" opacity=".7"/>`;
    s += `<rect x="${W / 2 - 40}" y="${m + altoCab * 0.32}" width="80" height="5" rx="2" fill="${cabecera === 'imagen' ? '#fff' : K}"/>`;
    s += `<rect x="${W / 2 - 26}" y="${m + altoCab * 0.62}" width="52" height="3" rx="1.5" fill="${cabecera === 'imagen' ? '#fff' : K}" opacity=".75"/>`;
  } else {
    s += `<rect x="${W / 2 - 40}" y="${m + altoCab * 0.25}" width="80" height="5" rx="2" fill="${cabecera === 'minima' ? T : P}"/>`;
    s += `<rect x="${W / 2 - 26}" y="${m + altoCab * 0.58}" width="52" height="3" rx="1.5" fill="${T}" opacity=".6"/>`;
    s += `<path d="M${m} ${m + altoCab}h${cw}" stroke="${cabecera === 'minima' ? T : A}" stroke-width="${cabecera === 'minima' ? 0.6 : 1.6}" opacity="${cabecera === 'minima' ? 0.5 : 1}"/>`;
  }
  const n = Math.max(1, Math.min(6, columnas));
  const y0 = m + altoCab + gap;
  const pieAlto = 7;
  const yf = Hh - m - pieAlto - gap;
  const w = (cw - gap * (n - 1)) / n;
  for (let i = 0; i < n; i++) {
    const x = m + i * (w + gap);
    const bloques = [0.42, 0.33, 0.25].map((f) => f * (yf - y0));
    let y = y0;
    bloques.forEach((h, j) => {
      const hh = h - gap;
      const tinte = '#' + mezclar(colores.acento, colores.fondo, 0.18);
      if (estiloCaja === 'barra' || estiloCaja === 'sombra') {
        s += `<rect x="${x}" y="${y}" width="${w}" height="${hh}" rx="1.5" fill="${B}"/><rect x="${x}" y="${y}" width="${w}" height="5" rx="1.5" fill="${P}"/>`;
      } else if (estiloCaja === 'caja' || estiloCaja === 'borde') {
        s += `<rect x="${x}" y="${y}" width="${w}" height="${hh}" rx="1.5" fill="${F}" stroke="${P}" stroke-width=".7"/>`;
        if (estiloCaja === 'caja') s += `<rect x="${x + 3}" y="${y - 1.5}" width="${Math.min(22, w * 0.5)}" height="4" rx="1" fill="${P}"/>`;
      } else if (estiloCaja === 'contorno') {
        s += `<rect x="${x}" y="${y}" width="${w}" height="${hh}" rx="1.5" fill="${F}" stroke="${S}" stroke-width=".7"/><rect x="${x}" y="${y}" width="${w}" height="5" rx="1.5" fill="${S}"/>`;
      } else if (estiloCaja === 'invertido') {
        s += `<rect x="${x}" y="${y}" width="${w}" height="${hh}" rx="1.5" fill="${P}"/>`;
      } else if (estiloCaja === 'resaltado') {
        s += `<rect x="${x}" y="${y}" width="${w}" height="${hh}" rx="1.5" fill="${tinte}"/>`;
      } else if (estiloCaja === 'nota' || estiloCaja === 'simple') {
        s += `<rect x="${x}" y="${y}" width="${w}" height="${hh}" rx="1.5" fill="${B}"/>`;
        if (estiloCaja === 'nota') s += `<rect x="${x}" y="${y}" width="1.6" height="${hh}" fill="${S}"/>`;
      } else if (estiloCaja === 'linea') {
        s += `<path d="M${x} ${y + 6}h${w}" stroke="${A}" stroke-width="1"/>`;
      } else if (estiloCaja === 'cita') {
        s += `<rect x="${x}" y="${y}" width="1.6" height="${hh}" fill="${A}"/>`;
      }
      const lin = estiloCaja === 'invertido' ? K : T;
      for (let k = 0; k * 4 + 10 < hh - 2; k++) {
        s += `<rect x="${x + 3}" y="${y + 9 + k * 4}" width="${(k % 3 === 2 ? 0.55 : 1) * (w - 6)}" height="1.3" fill="${lin}" opacity=".35"/>`;
      }
      if (j === 0 && i === Math.floor(n / 2)) s += `<rect x="${x + 3}" y="${y + hh * 0.45}" width="${w - 6}" height="${hh * 0.42}" fill="${S}" opacity=".35"/>`;
      y += h;
    });
  }
  s += `<rect x="${m}" y="${Hh - m - pieAlto}" width="${cw}" height="${pieAlto}" rx="1.5" fill="${P}" opacity=".9"/>`;
  s += '</svg>';
  return s;
}

export function svgCabecera(estilo, c) {
  const P = H(c.primario), S = H(c.secundario), A = H(c.acento), K = H(c.contraste), T = H(c.texto);
  const g = `<defs><linearGradient id="gc${estilo}" x1="0" x2="1"><stop offset="0" stop-color="${P}"/><stop offset="1" stop-color="${S}"/></linearGradient></defs>`;
  const fondos = {
    banda: `<rect x="4" y="6" width="112" height="30" rx="3" fill="${P}"/>`,
    degradado: `<rect x="4" y="6" width="112" height="30" rx="3" fill="url(#gc${estilo})"/>`,
    imagen: `<rect x="4" y="6" width="112" height="30" rx="3" fill="#2b3138"/><path d="M4 36l26-12 18 7 26-11 42 16z" fill="#56616c"/>`,
    clara: `<path d="M4 37h112" stroke="${A}" stroke-width="2"/>`,
    minima: `<path d="M4 37h112" stroke="${T}" stroke-width=".8" opacity=".5"/>`,
  };
  const claro = ['banda', 'degradado', 'imagen'].includes(estilo);
  const col = claro ? (estilo === 'imagen' ? '#fff' : K) : (estilo === 'minima' ? T : P);
  return `<svg viewBox="0 0 120 42" xmlns="http://www.w3.org/2000/svg">${g}<rect width="120" height="42" rx="4" fill="${H(c.fondo)}"/>${fondos[estilo] || ''}<rect x="30" y="13" width="60" height="5" rx="2" fill="${col}"/><rect x="40" y="23" width="40" height="3" rx="1.5" fill="${col}" opacity=".7"/></svg>`;
}

// Vista previa del asistente para diapositivas y documentos
export function svgDiapositiva({ ancho = 338, alto = 190, colores, titulo = 'banda' }) {
  const W = 220, Hh = Math.round(W * alto / ancho);
  const P = H(colores.primario), A = H(colores.acento), F = H(colores.fondo), K = H(colores.contraste), T = H(colores.texto), B = H(colores.fondo_bloque);
  let s = `<svg viewBox="0 0 ${W} ${Hh}" xmlns="http://www.w3.org/2000/svg"><rect width="${W}" height="${Hh}" fill="${F}"/>`;
  if (titulo === 'banda') s += `<rect width="${W}" height="24" fill="${P}"/><rect x="12" y="9" width="92" height="6" rx="2" fill="${K}"/>`;
  else {
    s += `<rect x="12" y="11" width="92" height="6" rx="2" fill="${P}"/>`;
    if (titulo === 'linea') s += `<path d="M12 24h${W - 24}" stroke="${A}" stroke-width="1.6"/>`;
  }
  [0, 1, 2].forEach((i) => { s += `<circle cx="16" cy="${42 + i * 14}" r="2" fill="${A}"/><rect x="24" y="${40 + i * 14}" width="${70 - i * 12}" height="3.5" rx="1.5" fill="${T}" opacity=".7"/>`; });
  s += `<rect x="${W / 2 + 8}" y="36" width="${W / 2 - 20}" height="${Hh - 60}" rx="2" fill="${B}"/><path d="M${W / 2 + 14} ${Hh - 32}l18-20 14 12 16-22 22 30z" fill="${P}" opacity=".45"/>`;
  s += `<rect x="12" y="${Hh - 10}" width="46" height="2.5" rx="1" fill="${T}" opacity=".35"/><rect x="${W - 24}" y="${Hh - 10}" width="12" height="2.5" rx="1" fill="${T}" opacity=".35"/></svg>`;
  return s;
}
export function svgDocumento({ ancho = 210, alto = 297, colores, columnas = 1, clase = 'documento' }) {
  const W = 170, Hh = Math.round(W * alto / ancho);
  const P = H(colores.primario), A = H(colores.acento), F = H(colores.fondo), T = H(colores.texto);
  let s = `<svg viewBox="0 0 ${W} ${Hh}" xmlns="http://www.w3.org/2000/svg"><rect width="${W}" height="${Hh}" fill="${F}"/>`;
  const m = 18, cw = W - 2 * m;
  const lineas = (x, y, w, n, corta = true) => { let o = ''; for (let i = 0; i < n; i++) o += `<rect x="${x}" y="${y + i * 6}" width="${corta && i === n - 1 ? w * 0.6 : w}" height="2.2" rx="1" fill="${T}" opacity=".45"/>`; return o; };
  if (clase === 'tesis') {
    s += `<rect x="${W / 2 - 34}" y="30" width="68" height="3.5" rx="1.5" fill="${T}" opacity=".55"/><rect x="${W / 2 - 24}" y="39" width="48" height="2.5" rx="1" fill="${T}" opacity=".4"/>`;
    s += `<rect x="${W / 2 - 52}" y="${Hh * 0.36}" width="104" height="6.5" rx="2" fill="${P}"/><rect x="${W / 2 - 38}" y="${Hh * 0.36 + 12}" width="76" height="6.5" rx="2" fill="${P}"/>`;
    s += `<path d="M${W / 2 - 14} ${Hh * 0.36 + 28}h28" stroke="${A}" stroke-width="1.6"/>`;
    s += `<rect x="${W / 2 - 28}" y="${Hh * 0.6}" width="56" height="3.5" rx="1.5" fill="${T}" opacity=".6"/><rect x="${W / 2 - 20}" y="${Hh - 34}" width="40" height="2.5" rx="1" fill="${T}" opacity=".4"/></svg>`;
    return s;
  }
  s += `<rect x="${W / 2 - 46}" y="${m}" width="92" height="6" rx="2" fill="${P}"/><rect x="${W / 2 - 30}" y="${m + 11}" width="60" height="3" rx="1.5" fill="${T}" opacity=".55"/>`;
  let y = m + 24;
  if (clase === 'paper') { s += `<rect x="${m + 12}" y="${y}" width="24" height="3" rx="1" fill="${T}" opacity=".8"/>` + lineas(m + 12, y + 7, cw - 24, 4); y += 38; }
  const n = columnas === 2 ? 2 : 1, gap = 8, w = (cw - gap * (n - 1)) / n;
  for (let c = 0; c < n; c++) {
    const x = m + c * (w + gap);
    let yy = y;
    while (yy < Hh - m - 30) { s += `<rect x="${x}" y="${yy}" width="${Math.min(40, w * 0.6)}" height="3.5" rx="1.5" fill="${P}"/>` + lineas(x, yy + 8, w, 5); yy += 46; }
  }
  s += `<rect x="${W / 2 - 4}" y="${Hh - 11}" width="8" height="2.5" rx="1" fill="${T}" opacity=".4"/></svg>`;
  return s;
}
