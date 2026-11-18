// Acceso al servidor. Todas las rutas son relativas para que la aplicación
// funcione también detrás del proxy de Google Colab.

export class ErrorApi extends Error {
  constructor(mensaje, estado) { super(mensaje); this.estado = estado; }
}

export async function api(ruta, { metodo = 'GET', json, cuerpo, texto = false, senal } = {}) {
  const init = { method: metodo, headers: {}, signal: senal, cache: 'no-store' };
  if (json !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(json);
  } else if (cuerpo !== undefined) {
    init.body = cuerpo;
  }
  let r;
  try {
    r = await fetch(ruta, init);
  } catch (e) {
    if (e.name === 'AbortError') throw e;
    throw new ErrorApi('No hay conexión con el servidor de DocsLab. ¿Sigue en marcha?', 0);
  }
  if (!r.ok) {
    let mensaje = `El servidor respondió con el código ${r.status}`;
    try { const d = await r.json(); if (d && d.error) mensaje = d.error; } catch { /* sin cuerpo JSON */ }
    throw new ErrorApi(mensaje, r.status);
  }
  if (texto) return r.text();
  const tipo = r.headers.get('content-type') || '';
  return tipo.includes('application/json') ? r.json() : r.text();
}

export const get = (ruta, op) => api(ruta, op);
export const post = (ruta, json) => api(ruta, { metodo: 'POST', json: json ?? {} });
export const patch = (ruta, json) => api(ruta, { metodo: 'PATCH', json });
export const put = (ruta, json) => api(ruta, { metodo: 'PUT', json });
export const borrar = (ruta) => api(ruta, { metodo: 'DELETE' });

// Subida con progreso (los CSV de datos pueden pesar decenas de MB).
export function subir(ruta, campos, { alProgreso } = {}) {
  return new Promise((resolver, rechazar) => {
    const fd = new FormData();
    for (const [clave, valor] of Object.entries(campos)) {
      if (Array.isArray(valor)) valor.forEach((v) => fd.append(clave, v));
      else if (valor !== undefined && valor !== null) fd.append(clave, valor);
    }
    const xhr = new XMLHttpRequest();
    xhr.open('POST', ruta);
    if (alProgreso) xhr.upload.onprogress = (e) => { if (e.lengthComputable) alProgreso(e.loaded / e.total); };
    xhr.onload = () => {
      let datos = null;
      try { datos = JSON.parse(xhr.responseText); } catch { /* respuesta vacía */ }
      if (xhr.status >= 200 && xhr.status < 300) resolver(datos);
      else rechazar(new ErrorApi((datos && datos.error) || `Error ${xhr.status} al subir`, xhr.status));
    };
    xhr.onerror = () => rechazar(new ErrorApi('No se pudo subir el archivo (conexión interrumpida)', 0));
    xhr.send(fd);
  });
}

export function descargar(url) {
  const a = document.createElement('a');
  a.href = url;
  a.download = '';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// Espera a que termine un trabajo en segundo plano (compilar, ejecutar un cuaderno).
export async function esperarTrabajo(id, { alCambiar, intervalo = 450, registro = false, senal } = {}) {
  for (;;) {
    if (senal && senal.aborted) throw new DOMException('cancelado', 'AbortError');
    const t = await api(`api/trabajos/${id}?registro=${registro ? 1 : 0}`);
    if (alCambiar) alCambiar(t);
    if (['terminado', 'error', 'cancelado'].includes(t.estado)) return t;
    await new Promise((r) => setTimeout(r, intervalo));
  }
}
