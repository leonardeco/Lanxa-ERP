import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import ErrorBoundary from './ErrorBoundary';

function Bomba({ explota }: { explota: boolean }) {
  if (explota) {
    throw new Error('falla controlada de prueba');
  }
  return <div>contenido sano</div>;
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // React loguea el error del boundary en consola — silenciarlo en el test
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('renderiza los hijos cuando no hay error', () => {
    render(
      <ErrorBoundary>
        <Bomba explota={false} />
      </ErrorBoundary>,
    );
    expect(screen.getByText('contenido sano')).toBeInTheDocument();
  });

  it('muestra el fallback con el mensaje del error cuando un hijo lanza', () => {
    render(
      <ErrorBoundary>
        <Bomba explota />
      </ErrorBoundary>,
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Algo salió mal en esta pantalla')).toBeInTheDocument();
    expect(screen.getByText('falla controlada de prueba')).toBeInTheDocument();
  });

  it('el botón Reintentar vuelve a montar los hijos', async () => {
    function Escenario() {
      const [explota, setExplota] = useState(true);
      return (
        <div>
          <button onClick={() => setExplota(false)}>arreglar</button>
          <ErrorBoundary>
            <Bomba explota={explota} />
          </ErrorBoundary>
        </div>
      );
    }
    const user = userEvent.setup();
    render(<Escenario />);

    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Se corrige la causa y se reintenta
    await user.click(screen.getByText('arreglar'));
    await user.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(screen.getByText('contenido sano')).toBeInTheDocument();
  });
});
