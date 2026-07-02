import { useEffect, useRef, useId, type ReactNode } from 'react'

interface ModalProps {
  title: string
  onClose: () => void
  children: ReactNode
  /** Usa el ancho amplio (modal-wide) para formularios grandes */
  wide?: boolean
}

/**
 * Modal accesible compartido por todas las vistas.
 * - Cierra al hacer clic en el overlay o pulsar Escape.
 * - role="dialog" + aria-modal + aria-labelledby con el título.
 * - Atrapa el foco dentro del modal y lo restaura al cerrar.
 */
export default function Modal({ title, onClose, children, wide }: ModalProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const titleId = useId()

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
        onClose()
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
  }, [onClose])

  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
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
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}
