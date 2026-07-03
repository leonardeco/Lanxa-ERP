import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Toast from './Toast';

describe('Toast', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('renderiza el mensaje con role=status y estilo según el tipo', () => {
    const { container } = render(
      <Toast message="Guardado correctamente" type="success" onClose={vi.fn()} />,
    );
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Guardado correctamente')).toBeInTheDocument();
    expect(container.querySelector('.toast-success')).not.toBeNull();

    render(<Toast message="Algo falló" type="error" onClose={vi.fn()} />);
    expect(screen.getByText('Algo falló')).toBeInTheDocument();
  });

  it('se cierra solo a los 3.5 segundos', () => {
    vi.useFakeTimers();
    const onClose = vi.fn();
    render(<Toast message="auto" type="success" onClose={onClose} />);

    act(() => {
      vi.advanceTimersByTime(3400);
    });
    expect(onClose).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('el botón de cerrar dispara onClose de inmediato', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<Toast message="manual" type="error" onClose={onClose} />);

    await user.click(screen.getByRole('button', { name: 'Cerrar notificación' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
