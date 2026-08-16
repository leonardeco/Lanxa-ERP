import { useState, useEffect } from 'react'
import { APP_VERSION, healthUrl } from '../config'

interface StatusBarProps {
  role: string
  userName: string
}

export default function StatusBar({ role, userName }: StatusBarProps) {
  const [time, setTime] = useState(new Date())
  const [apiStatus, setApiStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking')
  const [apiVersion, setApiVersion] = useState<string>(APP_VERSION)

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(healthUrl(), {
          // health es público; en LAN el cert puede ser la CA local
          // el navegador ya confía si se instaló superozono-ca.crt
        })
        if (!res.ok) {
          setApiStatus('disconnected')
          return
        }
        const data = await res.json()
        setApiStatus(data.status === 'ok' || data.database === 'connected' ? 'connected' : 'disconnected')
        if (data.version) setApiVersion(String(data.version))
      } catch {
        setApiStatus('disconnected')
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const formatTime = (d: Date) =>
    d.toLocaleTimeString('es-CO', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    })

  const formatDate = (d: Date) =>
    d.toLocaleDateString('es-CO', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })

  const apiLabel =
    apiStatus === 'connected' ? 'API conectada' : apiStatus === 'checking' ? 'Verificando…' : 'API desconectada'

  return (
    <footer className="status-bar" id="erp-status-bar">
      <div className="status-bar-left">
        <div className="status-bar-item">
          <span className={`status-bar-dot ${apiStatus === 'connected' ? 'connected' : apiStatus === 'checking' ? 'checking' : 'disconnected'}`} />
          <span>{apiLabel}</span>
        </div>
        <div className="status-bar-divider" />
        <div className="status-bar-item">
          <span className="status-bar-icon">⚡</span>
          <span>v{apiVersion}</span>
        </div>
        <div className="status-bar-divider" />
        <div className="status-bar-item">
          <span className="status-bar-icon">🏢</span>
          <span>LANXA S.A.S.</span>
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
          <span>
            {formatDate(time)} · {formatTime(time)}
          </span>
        </div>
      </div>
    </footer>
  )
}
