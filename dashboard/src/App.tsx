import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import { RealtimeProvider } from '@/context/RealtimeContext'
import { NotificationsProvider } from '@/context/NotificationsContext'
import { Sidebar } from '@/components/Sidebar'
import { TopBar } from '@/components/TopBar'
import { OnboardingWizard } from '@/components/OnboardingWizard'
import Dashboard from '@/pages/Dashboard'
import Pipelines from '@/pages/Pipelines'
import Nodes from '@/pages/Nodes'
import Marketplace from '@/pages/Marketplace'
import Settings from '@/pages/Settings'
import LivePipeline from '@/pages/LivePipeline'
import Pricing from '@/pages/Pricing'
import Billing from '@/pages/Billing'
import Xerebro from '@/pages/Xerebro'
import PipelineBuilder from '@/pages/PipelineBuilder'
import Login from '@/pages/Login'

function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 ml-60">
          <TopBar />
          <main className="p-6">{children}</main>
        </div>
      </div>
      <OnboardingWizard />
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      {/* One shared WebSocket for the whole app: notifications + activity feed */}
      <RealtimeProvider>
        <NotificationsProvider>
          <AuthProvider>
          <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedLayout>
                <Dashboard />
              </ProtectedLayout>
            }
          />
          <Route
            path="/pipelines/live"
            element={
              <ProtectedLayout>
                <LivePipeline />
              </ProtectedLayout>
            }
          />
          <Route
            path="/pipelines/builder"
            element={
              <ProtectedLayout>
                <PipelineBuilder />
              </ProtectedLayout>
            }
          />
          <Route
            path="/pipelines"
            element={
              <ProtectedLayout>
                <Pipelines />
              </ProtectedLayout>
            }
          />
          <Route
            path="/nodes"
            element={
              <ProtectedLayout>
                <Nodes />
              </ProtectedLayout>
            }
          />
          <Route
            path="/marketplace"
            element={
              <ProtectedLayout>
                <Marketplace />
              </ProtectedLayout>
            }
          />
          <Route
            path="/xerebro"
            element={
              <ProtectedLayout>
                <Xerebro />
              </ProtectedLayout>
            }
          />
          <Route
                        path="/pricing"
                        element={
                          <ProtectedLayout>
                            <Pricing />
                          </ProtectedLayout>
                        }
                      />
                      <Route
                        path="/settings/billing"
                        element={
                          <ProtectedLayout>
                            <Billing />
                          </ProtectedLayout>
                        }
                      />
                      <Route
                        path="/settings"
                        element={
                          <ProtectedLayout>
                            <Settings />
                          </ProtectedLayout>
                        }
                      />
                      <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
          </AuthProvider>
        </NotificationsProvider>
      </RealtimeProvider>
    </BrowserRouter>
  )
}
