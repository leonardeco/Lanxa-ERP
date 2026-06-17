import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import HeaderBar from './components/HeaderBar'
import StatusBar from './components/StatusBar'
import DashboardView from './views/DashboardView'
import PucView from './views/PucView'
import CentrosCostoView from './views/CentrosCostoView'
import PeriodosView from './views/PeriodosView'
import TributariosView from './views/TributariosView'
import NominaView from './views/NominaView'
import VentasView from './views/VentasView'
import UsuariosView from './views/UsuariosView'
import CarteraView from './views/CarteraView'
import ComprasView from './views/ComprasView'
import InventarioView from './views/InventarioView'
import LoginView from './views/LoginView'
import { useAuth } from './contexts/AuthContext'

export type ViewId =
  | 'dashboard'
  | 'puc'
  | 'centros-costo'
  | 'periodos'
  | 'tributarios'
  | 'usuarios'
  | 'cartera'
  | 'nomina'
  | 'ventas'
  | 'compras'
  | 'inventario'
  | 'rrhh'
  | 'plataformas'
  | 'reportes'

export type RolUsuario =
  | 'Admin'
  | 'Administradora'
  | 'Auxiliar'

const VIEW_TITLES: Record<ViewId, string> = {
  dashboard: 'Dashboard General',
  puc: 'Plan Único de Cuentas (PUC)',
  'centros-costo': 'Centros de Costo — Marcas',
  periodos: 'Períodos Contables',
  tributarios: 'Parámetros Tributarios',
  nomina: 'Parámetros de Nómina',
  ventas: 'Ventas & Comercial',
  compras: 'Compras & Proveedores',
  cartera: 'Cartera — CxC & CxP',
  inventario: 'Inventario & Logística',
  rrhh: 'Talento Humano',
  plataformas: 'Plataformas & Marketing',
  reportes: 'Reportes & BI',
  usuarios: 'Gestión de Usuarios',
}

// Qué módulos puede ver cada rol
const ROLE_VIEWS: Record<RolUsuario, ViewId[]> = {
  Admin: ['dashboard', 'puc', 'centros-costo', 'periodos', 'tributarios', 'nomina', 'ventas', 'compras', 'cartera', 'inventario', 'rrhh', 'plataformas', 'reportes', 'usuarios'],
  Administradora: ['dashboard', 'puc', 'centros-costo', 'periodos', 'tributarios', 'nomina', 'ventas', 'compras', 'cartera'],
  Auxiliar: ['dashboard', 'ventas', 'compras', 'cartera'],
}

function App() {
  const { user, logout, isLoading } = useAuth()
  const [activeView, setActiveView] = useState<ViewId>('dashboard')

  // Efecto para redirigir si el rol no permite la vista actual
  useEffect(() => {
    if (user) {
      const role = user.rol as RolUsuario;
      const allowed = ROLE_VIEWS[role] || ['dashboard'];
      if (!allowed.includes(activeView)) {
        setActiveView('dashboard');
      }
    }
  }, [user, activeView]);

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        <div className="loading-text">Cargando Super Ozono ERP...</div>
        <div className="loading-sub">Conectando con el sistema</div>
      </div>
    )
  }

  if (!user) {
    return <LoginView />
  }

  const activeRole = (user.rol as RolUsuario) || 'Solo lectura'
  const allowedViews = ROLE_VIEWS[activeRole] || ['dashboard']
  const userName = user.nombre_completo || 'Usuario'

  const handleViewChange = (view: ViewId) => {
    if (allowedViews.includes(view)) {
      setActiveView(view)
    }
  }

  const renderView = () => {
    switch (activeView) {
      case 'dashboard':
        return <DashboardView />
      case 'puc':
        return <PucView />
      case 'centros-costo':
        return <CentrosCostoView />
      case 'periodos':
        return <PeriodosView />
      case 'tributarios':
        return <TributariosView />
      case 'nomina':
        return <NominaView />
      case 'ventas':
        return <VentasView />
      case 'compras':
        return <ComprasView />
      case 'cartera':
        return <CarteraView />
      case 'usuarios':
        return <UsuariosView />
      case 'inventario':
        return <InventarioView />
      case 'rrhh':
      case 'plataformas':
      case 'reportes':
        return (
          <div className="empty-state fade-in">
            <div className="empty-state-icon">🚧</div>
            <div className="empty-state-text">Módulo en desarrollo — Fase 2+</div>
            <div className="empty-state-sub">Este módulo se habilitará en las siguientes fases del proyecto.</div>
          </div>
        )
      default:
        return <DashboardView />
    }
  }

  return (
    <div className="app-layout fade-in">
      <Sidebar
        activeView={activeView}
        activeRole={activeRole}
        allowedViews={allowedViews}
        onViewChange={handleViewChange}
        onLogout={logout}
        userName={userName}
      />
      <div className="main-content">
        <HeaderBar
          title={VIEW_TITLES[activeView]}
          role={activeRole}
        />
        <div className="page-content">
          {renderView()}
        </div>
        <StatusBar role={activeRole} userName={userName} />
      </div>
    </div>
  )
}

export default App
