import { useEffect } from 'react'

interface ToastProps {
  message: string
  type: 'success' | 'error'
  onClose: () => void
}

/**
 * Toast de notificación compartido. Se cierra solo a los 3.5s.
 * role="status" + aria-live para que los lectores de pantalla lo anuncien.
 */
export default function Toast({ message, type, onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3500)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className={`toast toast-${type} fade-in`} role="status" aria-live="polite">
      <span aria-hidden="true">{type === 'success' ? '✅' : '❌'}</span>
      <span>{message}</span>
      <button className="toast-close" onClick={onClose} aria-label="Cerrar notificación">
        ×
      </button>
    </div>
  )
}
