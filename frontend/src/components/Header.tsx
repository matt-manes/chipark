import type { User } from '../api/types'

interface HeaderProps {
  user: User | null
  notificationCount: number
  onNavigate: (path: string) => void
  onLogout: () => void
}

export default function Header({
  user,
  notificationCount,
  onNavigate,
  onLogout
}: HeaderProps) {
  return (
    <header className="app-header">
      <a
        className="brand"
        href="/parks"
        onClick={event => {
          event.preventDefault()
          onNavigate('/parks')
        }}
      >
        <span className="brand-mark" aria-hidden="true">C</span>
        <span>
          <strong>ChiPark</strong>
        </span>
      </a>
      <nav className="main-nav" aria-label="Main navigation">
        <button type="button" onClick={() => onNavigate('/parks')}>Parks</button>
        <button type="button" onClick={() => onNavigate('/tickets')}>Tickets</button>
        <button type="button" onClick={() => onNavigate('/tickets/new')}>Submit a ticket</button>
        {user !== null && (
          <button type="button" onClick={() => onNavigate('/profile')}>Profile</button>
        )}
      </nav>
      <div className="account-actions">
        {user !== null && notificationCount > 0 && (
          <span className="notification-badge" title="New ticket notifications">
            {notificationCount}
          </span>
        )}
        {user === null ? (
          <button className="button-primary" type="button" onClick={() => onNavigate('/login')}>
            Log in
          </button>
        ) : (
          <>
            <span className="account-email">{user.email}</span>
            <button type="button" onClick={onLogout}>Log out</button>
          </>
        )}
      </div>
    </header>
  )
}
