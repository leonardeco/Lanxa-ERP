/**
 * Estado de error compartido (#14): reemplaza los .catch(() => {}) silenciosos.
 * Muestra qué falló y ofrece reintentar, en vez de dejar un panel vacío
 * indistinguible de "no hay datos".
 */
export default function ErrorState({ mensaje, onRetry }: {
  mensaje?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="empty-state fade-in" role="alert">
      <div className="empty-state-icon">⚠️</div>
      <div className="empty-state-text">{mensaje ?? 'Error al cargar los datos'}</div>
      <div className="empty-state-sub">Revisa la conexión con el servidor e intenta de nuevo.</div>
      {onRetry && (
        <button className="btn-secondary" style={{ marginTop: 12 }} onClick={onRetry}>
          ↻ Reintentar
        </button>
      )}
    </div>
  );
}
