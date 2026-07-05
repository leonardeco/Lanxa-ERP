import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useUnsavedChanges, confirmarDescartar } from './unsavedGuard';

afterEach(() => vi.restoreAllMocks());

describe('unsavedGuard (#17)', () => {
  it('sin formularios sucios permite navegar sin preguntar', () => {
    const confirmSpy = vi.spyOn(window, 'confirm');
    expect(confirmarDescartar()).toBe(true);
    expect(confirmSpy).not.toHaveBeenCalled();
  });

  it('con un formulario sucio pregunta, y devuelve lo que responda el usuario', () => {
    const { unmount } = renderHook(() => useUnsavedChanges(true));

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    expect(confirmarDescartar()).toBe(false);
    confirmSpy.mockReturnValue(true);
    expect(confirmarDescartar()).toBe(true);
    expect(confirmSpy).toHaveBeenCalledTimes(2);

    // Al desmontar el formulario, se desregistra y ya no pregunta
    unmount();
    confirmSpy.mockClear();
    expect(confirmarDescartar()).toBe(true);
    expect(confirmSpy).not.toHaveBeenCalled();
  });

  it('un formulario limpio (dirty=false) no bloquea la navegación', () => {
    renderHook(() => useUnsavedChanges(false));
    const confirmSpy = vi.spyOn(window, 'confirm');
    expect(confirmarDescartar()).toBe(true);
    expect(confirmSpy).not.toHaveBeenCalled();
  });
});
