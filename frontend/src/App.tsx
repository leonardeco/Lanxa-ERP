import { useState, useEffect, lazy, Suspense } from 'react'
import Sidebar from './components/Sidebar'
import HeaderBar from './components/HeaderBar'
import StatusBar from './components/StatusBar'
import ErrorBoundary from './components/ErrorBoundary'
import DashboardView from './views/DashboardView'
import LoginView from './views/LoginView'
import { useAuth } from './contexts/auth'
import { confirmarDescartar } from './utils/unsavedGuard'

// Vistas con code splitting: cada una baja en su propio chunk al abrirla,
// en vez de inflar el bundle inicial (Dashboard y Login quedan eager
// porque son la primera pantalla).
const PucView = lazy(() => import('./views/PucView'))
const CentrosCostoView = lazy(() => import('./views/CentrosCostoView'))
const PeriodosView = lazy(() => import('./views/PeriodosView'))
const TributariosView = lazy(() => import('./views/TributariosView'))
const NominaView = lazy(() => import('./views/NominaView'))
const VentasView = lazy(() => import('./views/VentasView'))
const VentasDiariasView = lazy(() => import('./views/VentasDiariasView'))
const UsuariosView = lazy(() => import('./views/UsuariosView'))
const CarteraView = lazy(() => import('./views/CarteraView'))
const ComprasView = lazy(() => import('./views/ComprasView'))
const InventarioView = lazy(() => import('./views/InventarioView'))
const ReportesView = lazy(() => import('./views/ReportesView'))

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
  | 'ventas-diarias'
  | 'compras'
  | 'inventario'
  | 'rrhh'
  | 'plataformas'
  | 'reportes'

export type RolUsuario =
  | 'Superusuario'
  | 'Directora'
  | 'CEO'
  | 'Contador'
  | 'Auxiliar Contable'

const VIEW_TITLES: Record<ViewId, string> = {
  dashboard: 'Dashboard General',
  puc: 'Plan Único de Cuentas (PUC)',
  'centros-costo': 'Centros de Costo — Marcas',
  periodos: 'Períodos Contables',
  tributarios: 'Parámetros Tributarios',
  nomina: 'Parámetros de Nómina',
  ventas: 'Ventas & Comercial',
  'ventas-diarias': 'Ventas Diarias (Perú)',
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
  Superusuario: [
    'dashboard', 'puc', 'centros-costo', 'periodos', 'tributarios', 'nomina',
    'ventas', 'ventas-diarias', 'compras', 'cartera', 'inventario', 'rrhh', 'plataformas', 'reportes', 'usuarios',
  ],
  // Dirección operativa (antes Administradora)
  Directora: [
    'dashboard', 'puc', 'centros-costo', 'periodos', 'tributarios', 'nomina',
    'ventas', 'ventas-diarias', 'compras', 'cartera', 'inventario', 'reportes',
  ],
  // CEO: dashboards, reportes y consulta de operación
  CEO: ['dashboard', 'reportes', 'ventas', 'ventas-diarias', 'compras', 'cartera', 'inventario'],
  Contador: [
    'dashboard', 'puc', 'centros-costo', 'periodos', 'tributarios',
    'cartera', 'reportes', 'ventas', 'ventas-diarias', 'compras',
  ],
  'Auxiliar Contable': [
    'dashboard', 'puc', 'centros-costo', 'periodos', 'tributarios',
    'ventas', 'ventas-diarias', 'compras', 'cartera', 'reportes',
  ],
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
      // #17: no descartar formularios con datos sin guardar al cambiar de módulo
      if (view !== activeView && !confirmarDescartar()) return
      setActiveView(view)
    }
  }

  const handleLogout = () => {
    // #26: cerrar sesión también pasa por el guard de datos sin guardar
    if (!confirmarDescartar()) return
    logout()
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
      case 'ventas-diarias':
        return <VentasDiariasView />
      case 'compras':
        return <ComprasView />
      case 'cartera':
        return <CarteraView />
      case 'usuarios':
        return <UsuariosView />
      case 'inventario':
        return <InventarioView />
      case 'reportes':
        return <ReportesView />
      case 'rrhh':
      case 'plataformas':
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
        onLogout={handleLogout}
        userName={userName}
      />
      <div className="main-content">
        <HeaderBar
          title={VIEW_TITLES[activeView]}
          role={activeRole}
        />
        <div className="page-content">
          <ErrorBoundary>
            <Suspense
              fallback={
                <div className="loading-screen">
                  <div className="loading-spinner" />
                  <div className="loading-text">Cargando módulo...</div>
                </div>
              }
            >
              {renderView()}
            </Suspense>
          </ErrorBoundary>
        </div>
        <StatusBar role={activeRole} userName={userName} />
      </div>
    </div>
  )
}

export default App
