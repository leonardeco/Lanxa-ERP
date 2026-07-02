import type { CSSProperties } from 'react'

interface SkeletonProps {
  /** Forma del placeholder: texto, tarjeta o fila de tabla */
  variant?: 'text' | 'card' | 'row'
  width?: string | number
  height?: string | number
  /** Cuántos placeholders repetir (útil para listas/tablas) */
  count?: number
  style?: CSSProperties
}

/**
 * Placeholder animado (shimmer) para estados de carga.
 * Evita el "salto" de layout que produce el spinner y mejora la
 * percepción de velocidad. aria-hidden porque es puramente decorativo;
 * el contenedor debería exponer aria-busy="true".
 */
export default function Skeleton({ variant = 'text', width, height, count = 1, style }: SkeletonProps) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <span
          key={i}
          className={`skeleton skeleton-${variant}`}
          style={{ width, height, ...style }}
          aria-hidden="true"
        />
      ))}
    </>
  )
}
