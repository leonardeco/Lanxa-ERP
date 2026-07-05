import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Modal from './Modal';

describe('Modal', () => {
  it('renderiza título, contenido y atributos de accesibilidad', () => {
    render(
      <Modal title="Editar producto" onClose={vi.fn()}>
        <p>contenido del modal</p>
      </Modal>,
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByText('Editar producto')).toBeInTheDocument();
    expect(screen.getByText('contenido del modal')).toBeInTheDocument();
  });

  it('cierra con Escape', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <Modal title="X" onClose={onClose}>
        <button>ok</button>
      </Modal>,
    );
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('cierra al hacer clic en el overlay pero no dentro de la tarjeta', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    const { container } = render(
      <Modal title="X" onClose={onClose}>
        <p>contenido</p>
      </Modal>,
    );
    await user.click(screen.getByText('contenido'));
    expect(onClose).not.toHaveBeenCalled();

    await user.click(container.querySelector('.modal-overlay')!);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('cierra con el botón × y pone el foco inicial dentro del modal', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <Modal title="X" onClose={onClose}>
        <input placeholder="campo" />
      </Modal>,
    );
    // El foco inicial cae en el primer elemento enfocable (el botón ×)
    expect(document.activeElement?.closest('[role="dialog"]')).not.toBeNull();

    await user.click(screen.getByRole('button', { name: 'Cerrar' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  describe('confirmDiscard (#17 — datos sin guardar)', () => {
    it('con confirmDiscard, pide confirmación antes de cerrar y respeta "Cancelar"', async () => {
      const onClose = vi.fn();
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
      const user = userEvent.setup();
      render(
        <Modal title="X" onClose={onClose} confirmDiscard>
          <input placeholder="campo" />
        </Modal>,
      );

      await user.click(screen.getByRole('button', { name: 'Cerrar' }));
      expect(confirmSpy).toHaveBeenCalledTimes(1);
      expect(onClose).not.toHaveBeenCalled(); // el usuario canceló → sigue abierto

      confirmSpy.mockReturnValue(true);
      await user.keyboard('{Escape}');
      expect(onClose).toHaveBeenCalledTimes(1); // confirmó → se cierra

      confirmSpy.mockRestore();
    });

    it('sin confirmDiscard cierra directo, sin preguntar', async () => {
      const onClose = vi.fn();
      const confirmSpy = vi.spyOn(window, 'confirm');
      const user = userEvent.setup();
      render(
        <Modal title="X" onClose={onClose}>
          <input placeholder="campo" />
        </Modal>,
      );
      await user.keyboard('{Escape}');
      expect(confirmSpy).not.toHaveBeenCalled();
      expect(onClose).toHaveBeenCalledTimes(1);
      confirmSpy.mockRestore();
    });
  });
});
