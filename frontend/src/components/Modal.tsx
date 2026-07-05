import { useEffect, useRef, useId, type ReactNode } from 'react'
import { useUnsavedChanges, MENSAJE_DESCARTAR } from '../utils/unsavedGuard'

interface ModalProps {
  title: string
  onClose: () => void
  children: ReactNode
  /** Usa el ancho amplio (modal-wide) para formularios grandes */
  wide?: boolean
  /**
   * Si es true, cerrar el modal (X, overlay, Escape) pide confirmación
   * antes de descartar. Pasar el estado "dirty" del formulario.
   */
  confirmDiscard?: boolean
}

/**
 * Modal accesible compartido por todas las vistas.
 * - Cierra al hacer clic en el overlay o pulsar Escape.
 * - role="dialog" + aria-modal + aria-labelledby con el título.
 * - Atrapa el foco dentro del modal y lo restaura al cerrar.
 * - Con confirmDiscard, protege datos sin guardar (confirmación + beforeunload).
 */
export default function Modal({ title, onClose, children, wide, confirmDiscard }: ModalProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const titleId = useId()

  // Aviso nativo del navegador si intentan cerrar/recargar con datos sin guardar
  useUnsavedChanges(!!confirmDiscard)

  // requestClose vive en un ref para que el efecto de foco/teclado no se
  // re-ejecute (y robe el foco) cada vez que cambia el estado dirty del padre.
  // Se actualiza en un efecto (sin deps) para mantener la última closure.
  const requestCloseRef = useRef(() => {})
  useEffect(() => {
    requestCloseRef.current = () => {
      if (confirmDiscard && !confirm(MENSAJE_DESCARTAR)) return
      onClose()
    }
  })
  const requestClose = () => requestCloseRef.current()

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null

    const getFocusable = () =>
      Array.from(
        cardRef.current?.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        ) ?? []
      ).filter((el) => !el.hasAttribute('disabled') && el.offsetParent !== null)

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        requestCloseRef.current()
        return
      }
      if (e.key === 'Tab') {
        const focusable = getFocusable()
        if (focusable.length === 0) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    // Foco inicial: primer elemento enfocable o la tarjeta
    const focusable = getFocusable()
    ;(focusable[0] ?? cardRef.current)?.focus()

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      previouslyFocused?.focus?.()
    }
  }, [])

  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) requestClose()
      }}
    >
      <div
        ref={cardRef}
        className={`modal-card fade-in ${wide ? 'modal-wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
      >
        <div className="modal-header">
          <h3 id={titleId}>{title}</h3>
          <button className="modal-close" onClick={requestClose} aria-label="Cerrar">
            ×
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}
