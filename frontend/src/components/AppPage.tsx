import type { AuthenticatedUser, User } from '../api/types'
import type { ChiparkApiClient } from '../api/ChiparkApiClient'
import type { AppRoute } from '../navigation/AppRoute'
import AccountAccessPage from '../pages/AccountAccessPage'
import AdminUserDetailsPage from '../pages/AdminUserDetailsPage'
import AdminUsersPage from '../pages/AdminUsersPage'
import EditTicketPage from '../pages/EditTicketPage'
import ParkDetailsPage from '../pages/ParkDetailsPage'
import ParksPage from '../pages/ParksPage'
import ProfilePage from '../pages/ProfilePage'
import SubmitTicketPage from '../pages/SubmitTicketPage'
import TicketsPage from '../pages/TicketsPage'

interface AppPageProps {
  api: ChiparkApiClient
  route: AppRoute
  user: User | null
  onNavigate: (path: string) => void
  onAuthenticated: (session: AuthenticatedUser, nextPath: string) => void
  onUserUpdated: (user: User) => void
  onParkName: (parkName: string) => void
}

export default function AppPage({
  api,
  route,
  user,
  onNavigate,
  onAuthenticated,
  onUserUpdated,
  onParkName
}: AppPageProps) {
  switch (route.type) {
    case 'login':
      return (
        <AccountAccessPage
          api={api}
          mode="login"
          nextPath={route.nextPath}
          message={route.message}
          onAuthenticated={onAuthenticated}
          onNavigate={onNavigate}
        />
      )
    case 'register':
      return (
        <AccountAccessPage
          api={api}
          mode="register"
          nextPath={route.nextPath}
          message={null}
          onAuthenticated={onAuthenticated}
          onNavigate={onNavigate}
        />
      )
    case 'auth-callback':
      return (
        <section className="page-section">
          <div className="alert alert-error" role="alert">
            Google sign-in did not return an access token. Please sign in again.
          </div>
          <button type="button" onClick={() => onNavigate('/login')}>
            Return to sign in
          </button>
        </section>
      )
    case 'park-details':
      return (
        <ParkDetailsPage
          key={route.parkId}
          api={api}
          parkId={route.parkId}
          user={user}
          onBack={() => onNavigate('/parks')}
          onSubmitTicket={parkId => onNavigate(`/tickets/new?parkId=${parkId}`)}
          onParkClick={onParkName}
          onEditTicket={ticketId => onNavigate(`/tickets/${ticketId}/edit`)}
        />
      )
    case 'submit-ticket':
      if (user === null) return null
      return (
        <SubmitTicketPage
          api={api}
          user={user}
          initialParkId={route.parkId}
          onComplete={() => onNavigate('/tickets')}
        />
      )
    case 'edit-ticket':
      return (
        <EditTicketPage
          api={api}
          ticketId={route.ticketId}
          onBack={() => onNavigate('/tickets')}
          onSaved={() => onNavigate('/tickets')}
        />
      )
    case 'admin-user-details':
      return (
        <AdminUserDetailsPage
          key={route.userId}
          api={api}
          userId={route.userId}
          onBack={() => onNavigate('/admin/users')}
          onParkName={onParkName}
          onEditTicket={ticketId => onNavigate(`/tickets/${ticketId}/edit`)}
        />
      )
    case 'admin-users':
      return (
        <AdminUsersPage
          api={api}
          onSelectUser={userId => onNavigate(`/admin/users/${userId}`)}
        />
      )
    case 'tickets':
      return (
        <TicketsPage
          key={route.key}
          api={api}
          user={user}
          initialSearch={route.search}
          onSelectPark={parkId => onNavigate(`/parks/${parkId}`)}
          onEditTicket={ticketId => onNavigate(`/tickets/${ticketId}/edit`)}
        />
      )
    case 'profile':
      if (user === null) return null
      return (
        <ProfilePage
          api={api}
          user={user}
          onUserUpdated={onUserUpdated}
          onParkSearch={name =>
            onNavigate(`/parks?search=${encodeURIComponent(name)}`)
          }
          onEditTicket={ticketId => onNavigate(`/tickets/${ticketId}/edit`)}
        />
      )
    case 'parks':
      return (
        <ParksPage
          key={route.key}
          api={api}
          initialSearch={route.search}
          onSelectPark={parkId => onNavigate(`/parks/${parkId}`)}
        />
      )
  }
}
