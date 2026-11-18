// SPDX-License-Identifier: AGPL-3.0-only
// Foco en los diálogos modales (WCAG 2.4.3 «Orden del foco»), para todos los diálogos a la vez:
//  · al abrirse, el foco entra en el diálogo (si el propio diálogo no lo ha puesto ya en un campo);
//  · Tab y Mayús+Tab dan la vuelta dentro del diálogo de encima, sin salir a la página de detrás;
//  · al cerrarse, el foco vuelve al elemento que lo tenía antes de abrirlo.
// Un diálogo es cualquier elemento con role="dialog" y aria-modal="true".

const SELECTOR_DIALOGO = '[role="dialog"][aria-modal="true"]';
const ENFOCABLES = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), '
  + 'textarea:not([disabled]), iframe, [tabindex]:not([tabindex="-1"]), [contenteditable="true"]';

function enfocables(dlg) {
  return [...dlg.querySelectorAll(ENFOCABLES)].filter((e) => e.getClientRects().length > 0);
}

export function instalarFocoModal(raiz = document) {
  const pila = [];                      // [{ dlg, antes }] en el orden en que se abrieron
  let ultimoFuera = null;               // último elemento con foco fuera de cualquier diálogo

  raiz.addEventListener('focusin', (ev) => {
    if (!(ev.target instanceof Element) || !ev.target.closest(SELECTOR_DIALOGO)) ultimoFuera = ev.target;
  }, true);

  const revisar = () => {
    for (let i = pila.length - 1; i >= 0; i--) {
      if (pila[i].dlg.isConnected) continue;
      const { antes } = pila.splice(i, 1)[0];
      const activo = document.activeElement;
      const perdido = !activo || activo === document.body || !activo.isConnected;
      if (perdido && antes && antes.isConnected) antes.focus({ preventScroll: true });
    }
    for (const dlg of raiz.querySelectorAll(SELECTOR_DIALOGO)) {
      if (pila.some((p) => p.dlg === dlg)) continue;
      pila.push({ dlg, antes: ultimoFuera });
      requestAnimationFrame(() => {
        if (!dlg.isConnected || dlg.contains(document.activeElement)) return;
        const primero = enfocables(dlg)[0];
        if (primero) primero.focus();
        else { if (!dlg.hasAttribute('tabindex')) dlg.setAttribute('tabindex', '-1'); dlg.focus(); }
      });
    }
  };
  new MutationObserver(revisar).observe(raiz.body || raiz, { childList: true, subtree: true });

  raiz.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Tab' || !pila.length) return;
    const { dlg } = pila[pila.length - 1];
    if (!dlg.isConnected) return;
    const lista = enfocables(dlg);
    if (!lista.length) { ev.preventDefault(); return; }
    const primero = lista[0], ultimo = lista[lista.length - 1], activo = document.activeElement;
    if (activo && activo.closest && activo.closest('.CodeMirror')) return;   // ahí Tab sangra el código
    if (!dlg.contains(activo)) { ev.preventDefault(); (ev.shiftKey ? ultimo : primero).focus(); }
    else if (ev.shiftKey && activo === primero) { ev.preventDefault(); ultimo.focus(); }
    else if (!ev.shiftKey && activo === ultimo) { ev.preventDefault(); primero.focus(); }
  }, true);
}
