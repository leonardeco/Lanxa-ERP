import { useState, useEffect } from 'react'

interface StatusBarProps {
  role: string
  userName: string
}

export default function StatusBar({ role, userName }: StatusBarProps) {
  const [time, setTime] = useState(new Date())
  const [dbStatus, setDbStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking')

  // Reloj en tiempo real
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Health check periódico
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('http://localhost:8000/health')
        const data = await res.json()
        setDbStatus(data.database === 'connected' ? 'connected' : 'disconnected')
      } catch {
        setDbStatus('disconnected')
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 30000) // cada 30s
    return () => clearInterval(interval)
  }, [])

  const formatTime = (d: Date) => {
    return d.toLocaleTimeString('es-CO', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    })
  }

  const formatDate = (d: Date) => {
    return d.toLocaleDateString('es-CO', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  }

  return (
    <footer className="status-bar" id="erp-status-bar">
      <div className="status-bar-left">
        <div className="status-bar-item">
          <span className={`status-bar-dot ${dbStatus}`} />
          <span>
            PostgreSQL {dbStatus === 'connected' ? 'Conectado' : dbStatus === 'checking' ? 'Verificando...' : 'Desconectado'}
          </span>
        </div>
        <div className="status-bar-divider" />
        <div className="status-bar-item">
          <span className="status-bar-icon">⚡</span>
          <span>v0.2.0</span>
        </div>
        <div className="status-bar-divider" />
        <div className="status-bar-item">
          <span className="status-bar-icon">🏢</span>
          <span>NIT: 901841798-5</span>
        </div>
      </div>
      <div className="status-bar-right">
        <div className="status-bar-item">
          <span className="status-bar-icon">👤</span>
          <span>{userName}</span>
          <span className="status-bar-role-badge">{role}</span>
        </div>
        <div className="status-bar-divider" />
        <div className="status-bar-item">
          <span className="status-bar-icon">📅</span>
          <span>{formatDate(time)}</span>
        </div>
        <div className="status-bar-divider" />
        <div className="status-bar-item status-bar-clock">
          <span>{formatTime(time)}</span>
        </div>
      </div>
    </footer>
  )
}
