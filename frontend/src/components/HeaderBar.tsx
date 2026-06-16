import { useState, useEffect } from 'react'
import type { RolUsuario } from '../App'

interface HeaderBarProps {
  title: string
  role: RolUsuario
}

export default function HeaderBar({ title, role }: HeaderBarProps) {
  const [time, setTime] = useState(new Date())
  const [showNotifications, setShowNotifications] = useState(false)

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 60000)
    return () => clearInterval(timer)
  }, [])

  const notifications = [
    { id: 1, text: 'Fase 1 del ERP en progreso', type: 'info', time: 'Hoy' },
    { id: 2, text: 'Base de datos PostgreSQL configurada', type: 'success', time: 'Reciente' },
    { id: 3, text: 'Módulos Fase 2+ pendientes', type: 'warning', time: 'Pendiente' },
  ]

  return (
    <header className="header-bar" id="erp-header">
      <div className="header-left">
        <div className="header-title-group">
          <h2>{title}</h2>
          <span className="header-breadcrumb">
            <span className="breadcrumb-home">🏠</span>
            <span className="breadcrumb-sep">›</span>
            <span>Super Ozono</span>
            <span className="breadcrumb-sep">›</span>
            <span className="breadcrumb-current">{title}</span>
          </span>
        </div>
      </div>
      <div className="header-right">
        <div className="header-time">
          {time.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', hour12: true })}
        </div>
        <div className="header-nit">NIT: 901841798-5</div>

        {/* Notificaciones */}
        <div className="header-notifications-wrapper">
          <button
            className="header-notification-btn"
            onClick={() => setShowNotifications(!showNotifications)}
            title="Notificaciones"
          >
            🔔
            <span className="notification-badge">{notifications.length}</span>
          </button>
          {showNotifications && (
            <div className="notifications-dropdown fade-in">
              <div className="notifications-header">
                <span>Notificaciones</span>
                <button onClick={() => setShowNotifications(false)} className="notifications-close">✕</button>
              </div>
              {notifications.map((n) => (
                <div key={n.id} className={`notification-item ${n.type}`}>
                  <div className="notification-text">{n.text}</div>
                  <div className="notification-time">{n.time}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="header-status">
          <span className="status-dot" />
          {role}
        </div>
      </div>
    </header>
  )
}
