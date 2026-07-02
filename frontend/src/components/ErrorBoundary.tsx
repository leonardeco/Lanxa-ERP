import React from 'react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Captura errores de render de cualquier vista y muestra un mensaje
 * recuperable en lugar de dejar la pantalla en blanco.
 */
class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Error no capturado en la UI:', error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="empty-state fade-in" role="alert">
          <div className="empty-state-icon">⚠️</div>
          <div className="empty-state-text">Algo salió mal en esta pantalla</div>
          <div className="empty-state-sub">
            {this.state.error?.message || 'Error inesperado en la interfaz.'}
          </div>
          <button className="btn btn-primary" onClick={this.handleReset} style={{ marginTop: 16 }}>
            Reintentar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
