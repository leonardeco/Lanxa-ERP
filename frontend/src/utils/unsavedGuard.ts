/**
 * Guard global de datos sin guardar (#17).
 *
 * Los formularios registran su estado "sucio" con useUnsavedChanges(); la
 * navegación (Sidebar, pestañas internas) consulta confirmarDescartar() antes
 * de desmontar la vista. El hook también activa el aviso nativo del navegador
 * (beforeunload) para cierre/refresh de la ventana.
 */

import { useEffect, useId } from 'react';

const formulariosSucios = new Set<string>();

export const MENSAJE_DESCARTAR = 'Hay datos sin guardar. ¿Salir y descartar los cambios?';

/** Registra este formulario como "con cambios sin guardar" mientras dirty sea true. */
export function useUnsavedChanges(dirty: boolean) {
  const id = useId();

  useEffect(() => {
    if (dirty) formulariosSucios.add(id);
    else formulariosSucios.delete(id);
    return () => { formulariosSucios.delete(id); };
  }, [id, dirty]);

  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);
}

/**
 * true si se puede navegar: no hay formularios sucios, o el usuario
 * confirmó que quiere descartar los cambios.
 */
export function confirmarDescartar(): boolean {
  if (formulariosSucios.size === 0) return true;
  return confirm(MENSAJE_DESCARTAR);
}
