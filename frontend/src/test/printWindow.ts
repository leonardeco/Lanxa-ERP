import { vi } from 'vitest';

/**
 * Utilidades de test para las funciones de impresión (`printFactura`, etc.).
 *
 * Todas siguen el mismo patrón: arman un HTML y lo escriben en una ventana
 * abierta con `window.open`; si el navegador bloquea el popup, hacen `alert`
 * y retornan sin escribir nada. Estos helpers mockean ese contrato para poder
 * capturar el HTML generado o verificar la rama de popup bloqueado.
 */

export interface MockPrintWindow {
  /** Spy sobre `window.open`. */
  openSpy: ReturnType<typeof vi.spyOn>;
  /** Spy sobre `document.write` de la ventana emergente. */
  write: ReturnType<typeof vi.fn>;
  /** Spy sobre `document.close` de la ventana emergente. */
  close: ReturnType<typeof vi.fn>;
  /** Devuelve el HTML escrito en la ventana (primera llamada a `write`). */
  html: () => string;
}

/** `window.open` devuelve una ventana falsa que captura el HTML escrito. */
export function mockPrintWindow(): MockPrintWindow {
  const write = vi.fn();
  const close = vi.fn();
  const fakeWin = { document: { write, close } } as unknown as Window;
  const openSpy = vi.spyOn(window, 'open').mockReturnValue(fakeWin);
  return {
    openSpy,
    write,
    close,
    html: () => String(write.mock.calls[0]?.[0] ?? ''),
  };
}

/** `window.open` devuelve `null` (popup bloqueado) y `alert` queda mockeado. */
export function mockBlockedPopup() {
  const openSpy = vi.spyOn(window, 'open').mockReturnValue(null);
  const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
  return { openSpy, alertSpy };
}
