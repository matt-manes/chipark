import type { ReactNode } from 'react'
import type { ChiparkApiClient } from '../api/ChiparkApiClient'
import type { AuthenticatedUser, User } from '../api/types'
import type { RouteState } from '../navigation/BrowserRoute'
import { RouteParameters } from '../navigation/BrowserRoute'
import AccountAccessPage from '../pages/AccountAccessPage'
import EditTicketPage from '../pages/EditTicketPage'
import ParkDetailsPage from '../pages/ParkDetailsPage'
import ParksPage from '../pages/ParksPage'
import ProfilePage from '../pages/ProfilePage'
import SubmitTicketPage from '../pages/SubmitTicketPage'
import TicketsPage from '../pages/TicketsPage'

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
  const query: URLSearchParams = new URLSearchParams(route.search)
  const nextPath: string = RouteParameters.getNextPath(route.search)
  const parkId: number | null = RouteParameters.getIdFromPath(
    route.pathname,
    /^\/parks\/(\d+)$/
  )
  const editTicketId: number | null = RouteParameters.getIdFromPath(
    route.pathname,
    /^\/tickets\/(\d+)\/edit$/
  )
  const requestedParkValue: string | null = query.get('parkId')
  const requestedParkId: number | null =
    requestedParkValue === null ? null : Number(requestedParkValue)
  const isEditRoute: boolean = editTicketId !== null
  const loginRequiredPath: string | null =
    route.pathname === '/tickets/new' ||
    route.pathname === '/profile' ||
    isEditRoute
      ? `${route.pathname}${route.search}`
      : null

  let page: ReactNode
  if (authLoading) {
    page = <div className="loading-state">Checking your account...</div>
  } else if (loginRequiredPath !== null && user === null) {
    page = (
      <AccountAccessPage
        api={api}
        mode="login"
        nextPath={loginRequiredPath}
        message={
          route.pathname === '/tickets/new'
            ? 'Please sign in before submitting a ticket.'
            : 'Please sign in to access your account.'
        }
        onAuthenticated={onAuthenticated}
        onNavigate={onNavigate}
      />
    )
  } else if (isEditRoute && user?.role !== 'admin') {
    page = (
      <section className="page-section">
        <div className="alert alert-error" role="alert">
          Only administrators can edit tickets.
        </div>
        <button type="button" onClick={() => onNavigate('/tickets')}>
          Browse tickets
        </button>
      </section>
    )
  } else if (
    route.pathname === '/login' ||
    (route.pathname === '/tickets/new' && user === null)
  ) {
    page = (
      <AccountAccessPage
        api={api}
        mode="login"
        nextPath={
          route.pathname === '/tickets/new'
            ? `${route.pathname}${route.search}`
            : nextPath
        }
        message={
          query.get('required') === '1' || route.pathname === '/tickets/new'
            ? 'Please sign in before submitting a ticket.'
            : null
        }
        onAuthenticated={onAuthenticated}
        onNavigate={onNavigate}
      />
    )
  } else if (route.pathname === '/register') {
    page = (
      <AccountAccessPage
        api={api}
        mode="register"
        nextPath={nextPath}
        message={null}
        onAuthenticated={onAuthenticated}
        onNavigate={onNavigate}
      />
    )
  } else if (route.pathname === '/auth/callback') {
    page = (
      <section className="page-section">
        <div className="alert alert-error" role="alert">
          Google sign-in did not return an access token. Please sign in again.
        </div>
        <button type="button" onClick={() => onNavigate('/login')}>
          Return to sign in
        </button>
      </section>
    )
  } else if (parkId !== null) {
    page = (
      <ParkDetailsPage
        api={api}
        parkId={parkId}
        user={user}
        onBack={() => onNavigate('/parks')}
        onSubmitTicket={id => onNavigate(`/tickets/new?parkId=${id}`)}
        onParkClick={onParkName}
        onEditTicket={id => onNavigate(`/tickets/${id}/edit`)}
      />
    )
  } else if (route.pathname === '/tickets/new' && user !== null) {
    page = (
      <SubmitTicketPage
        api={api}
        user={user}
        initialParkId={
          requestedParkId !== null && Number.isSafeInteger(requestedParkId)
            ? requestedParkId
            : null
        }
        onComplete={() => onNavigate('/tickets')}
      />
    )
  } else if (editTicketId !== null && user?.role === 'admin') {
    page = (
      <EditTicketPage
        api={api}
        ticketId={editTicketId}
        onBack={() => onNavigate('/tickets')}
        onSaved={() => onNavigate('/tickets')}
      />
    )
  } else if (route.pathname === '/tickets') {
    page = (
      <TicketsPage
        key={`${route.pathname}${route.search}`}
        api={api}
        user={user}
        initialSearch={query.get('search') ?? ''}
        onSelectPark={id => onNavigate(`/parks/${id}`)}
        onEditTicket={id => onNavigate(`/tickets/${id}/edit`)}
      />
    )
  } else if (route.pathname === '/profile' && user !== null) {
    page = (
      <ProfilePage
        api={api}
        user={user}
        onUserUpdated={onUserUpdated}
        onParkSearch={name => onNavigate(`/parks?search=${encodeURIComponent(name)}`)}
        onEditTicket={id => onNavigate(`/tickets/${id}/edit`)}
      />
    )
  } else {
    page = (
      <ParksPage
        key={`${route.pathname}${route.search}`}
        api={api}
        initialSearch={query.get('search') ?? ''}
        onSelectPark={id => onNavigate(`/parks/${id}`)}
      />
    )
  }

  return page
}
