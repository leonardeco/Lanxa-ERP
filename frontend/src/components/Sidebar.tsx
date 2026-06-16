import { useState } from 'react'
import type { ViewId, RolUsuario } from '../App'

interface SidebarProps {
  activeView: ViewId
  activeRole: RolUsuario
  allowedViews: ViewId[]
  onViewChange: (view: ViewId) => void
  onLogout: () => void
  userName: string
}

const NAV_SECTIONS = [
  {
    title: 'General',
    items: [
      { id: 'dashboard' as ViewId, icon: '📊', label: 'Dashboard' },
    ],
  },
  {
    title: 'Contabilidad',
    items: [
      { id: 'puc' as ViewId, icon: '📋', label: 'Plan de Cuentas (PUC)', badge: '34' },
      { id: 'centros-costo' as ViewId, icon: '🏷️', label: 'Centros de Costo', badge: '12' },
      { id: 'periodos' as ViewId, icon: '📅', label: 'Períodos Contables' },
      { id: 'tributarios' as ViewId, icon: '🏛️', label: 'Params. Tributarios' },
      { id: 'nomina' as ViewId, icon: '💰', label: 'Params. Nómina' },
    ],
  },
  {
    title: 'Operaciones',
    items: [
      { id: 'ventas' as ViewId, icon: '🛒', label: 'Ventas & Comercial' },
      { id: 'inventario' as ViewId, icon: '📦', label: 'Inventario' },
      { id: 'rrhh' as ViewId, icon: '👥', label: 'Talento Humano' },
      { id: 'plataformas' as ViewId, icon: '🌐', label: 'Plataformas' },
      { id: 'reportes' as ViewId, icon: '📈', label: 'Reportes & BI' },
    ],
  },
  {
    title: 'Administración',
    items: [
      { id: 'usuarios' as ViewId, icon: '⚙️', label: 'Usuarios & Accesos' },
    ],
  },
]


export default function Sidebar({
  activeView,
  activeRole,
  allowedViews,
  onViewChange,
  onLogout,
  userName,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  // Obtener iniciales del nombre
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(w => w[0])
      .slice(0, 2)
      .join('')
      .toUpperCase()
  }

  return (
    <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`} id="erp-sidebar">
      {/* ── Logo & Brand ─────────────────────────────── */}
      <div className="sidebar-header">
        <div className="sidebar-logo" onClick={() => onViewChange('dashboard')} title="Super Ozono Global ERP">
          <svg viewBox="0 0 32 32" width="22" height="22" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="16" cy="16" r="14" stroke="white" strokeWidth="2" opacity="0.8"/>
            <circle cx="16" cy="16" r="8" stroke="white" strokeWidth="1.5" opacity="0.5"/>
            <circle cx="16" cy="16" r="3" fill="white"/>
            <path d="M16 2 L16 6" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M16 26 L16 30" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M2 16 L6 16" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M26 16 L30 16" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </div>
        {!collapsed && (
          <div className="sidebar-brand">
            <h1>Super Ozono</h1>
            <p>ERP — Sistema de Gestión</p>
          </div>
        )}
        <button
          className="sidebar-toggle"
          onClick={() => setCollapsed(!collapsed)}
          title={collapsed ? 'Expandir menú' : 'Colapsar menú'}
        >
          {collapsed ? '▸' : '◂'}
        </button>
      </div>

      {/* ── Navigation ───────────────────────────────── */}
      <div className="sidebar-scroll">
        {NAV_SECTIONS.map((section) => {
          const visibleItems = section.items.filter((item) =>
            allowedViews.includes(item.id)
          )
          if (visibleItems.length === 0) return null

          return (
            <div key={section.title}>
              {!collapsed && (
                <div className="sidebar-section">
                  <div className="sidebar-section-title">{section.title}</div>
                </div>
              )}
              <nav className="sidebar-nav">
                {visibleItems.map((item) => (
                  <button
                    key={item.id}
                    id={`nav-${item.id}`}
                    className={`nav-item ${activeView === item.id ? 'active' : ''}`}
                    onClick={() => onViewChange(item.id)}
                    title={collapsed ? item.label : undefined}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    {!collapsed && (
                      <>
                        <span className="nav-label">{item.label}</span>
                        {item.badge && <span className="nav-badge">{item.badge}</span>}
                      </>
                    )}
                  </button>
                ))}
              </nav>
            </div>
          )
        })}
      </div>

      {/* ── User Profile & Logout ──────────────────────── */}
      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-avatar">
            {getInitials(userName)}
          </div>
          {!collapsed && (
            <div className="sidebar-user-info">
              <div className="sidebar-user-name">{userName}</div>
              <div className="sidebar-user-role">
                <span className="role-dot" />
                {activeRole}
              </div>
            </div>
          )}
        </div>
        {!collapsed && (
          <button
            onClick={onLogout}
            className="sidebar-logout-btn"
            title="Cerrar Sesión"
          >
            <span>⏻</span> Cerrar Sesión
          </button>
        )}
        {collapsed && (
          <button
            onClick={onLogout}
            className="sidebar-logout-btn sidebar-logout-collapsed"
            title="Cerrar Sesión"
          >
            ⏻
          </button>
        )}
      </div>
    </aside>
  )
}
