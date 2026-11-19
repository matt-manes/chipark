import type { AuthenticatedUser, User } from '../api/types'
import type { ChiparkApiClient } from '../api/ChiparkApiClient'
import type { RouteState } from '../navigation/BrowserRoute'
import { AppRouteResolver } from '../navigation/AppRoute'
import AccountAccessPage from '../pages/AccountAccessPage'
import AppPage from './AppPage'

interface AppContentProps {
  api: ChiparkApiClient
  route: RouteState
  user: User | null
  authLoading: boolean
  onNavigate: (path: string) => void
  onAuthenticated: (session: AuthenticatedUser, nextPath: string) => void
  onUserUpdated: (user: User) => void
  onParkName: (parkName: string) => void
}

export default function AppContent({
  api,
  route,
  user,
  authLoading,
  onNavigate,
  onAuthenticated,
  onUserUpdated,
  onParkName
}: AppContentProps) {
  const appRoute = AppRouteResolver.resolve(route)

  if (authLoading) {
    return <div className="loading-state">Checking your account...</div>
  }
  if (appRoute.access !== 'public' && user === null) {
    const nextPath: string = `${route.pathname}${route.search}`
    const message: string =
      appRoute.type === 'submit-ticket'
        ? 'Please sign in before submitting a ticket.'
        : 'Please sign in to access your account.'
    return (
      <AccountAccessPage
        api={api}
        mode="login"
        nextPath={nextPath}
        message={message}
        onAuthenticated={onAuthenticated}
        onNavigate={onNavigate}
      />
    )
  }
  if (appRoute.access === 'admin' && user?.role !== 'admin') {
    const isEditRoute: boolean = appRoute.type === 'edit-ticket'
    return (
      <section className="page-section">
        <div className="alert alert-error" role="alert">
          {isEditRoute
            ? 'Only administrators can edit tickets.'
            : 'Only administrators can manage registered users.'}
        </div>
        <button
          type="button"
          onClick={() => onNavigate(isEditRoute ? '/tickets' : '/parks')}
        >
          Browse {isEditRoute ? 'tickets' : 'parks'}
        </button>
      </section>
    )
  }

  return (
    <AppPage
      api={api}
      route={appRoute}
      user={user}
      onNavigate={onNavigate}
      onAuthenticated={onAuthenticated}
      onUserUpdated={onUserUpdated}
      onParkName={onParkName}
    />
  )
}
