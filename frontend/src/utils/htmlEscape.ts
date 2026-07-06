/**
 * Escapa texto para interpolarlo con seguridad en el HTML que se inyecta con
 * document.write en las ventanas de impresión (#29).
 *
 * Los campos de negocio (razón social, observaciones, motivos, notas, etc.)
 * son texto libre digitado por el usuario; sin escapar, un valor con `<script>`
 * u otro markup se ejecutaría/renderizaría en la ventana de impresión (XSS
 * almacenado). Los números formateados con COP()/Number() son seguros y no
 * necesitan pasar por aquí.
 */
export function esc(value: unknown): string {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
