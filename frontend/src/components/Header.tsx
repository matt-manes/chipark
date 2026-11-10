import { useCallback, useEffect, useRef, useState } from 'react'
import type { TicketNotification, User } from '../api/types'

interface HeaderProps {
  user: User | null
  notificationCount: number
  notifications: TicketNotification[]
  notificationsLoading: boolean
  notificationsError: string | null
  onNavigate: (path: string) => void
  onLogout: () => void
  onOpenInbox: () => void
  onCloseInbox: () => void
  onSelectNotification: (notification: TicketNotification) => void
}

export default function Header({
  user,
  notificationCount,
  notifications,
  notificationsLoading,
  notificationsError,
  onNavigate,
  onLogout,
  onOpenInbox,
  onCloseInbox,
  onSelectNotification
}: HeaderProps) {
  const [isInboxOpen, setIsInboxOpen] = useState(false)
  const inboxRef = useRef<HTMLDivElement>(null)

  const closeInbox = useCallback((): void => {
    if (!isInboxOpen) return
    setIsInboxOpen(false)
    onCloseInbox()
  }, [isInboxOpen, onCloseInbox])

  function toggleInbox(): void {
    if (isInboxOpen) {
      closeInbox()
      return
    }
    setIsInboxOpen(true)
    onOpenInbox()
  }

  useEffect(() => {
    if (!isInboxOpen) return

    function handlePointerDown(event: PointerEvent): void {
      if (
        event.target instanceof Node &&
        !inboxRef.current?.contains(event.target)
      ) {
        closeInbox()
      }
    }

    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === 'Escape') closeInbox()
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isInboxOpen, closeInbox])

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
        {user !== null && (
          <div className="notification-inbox" ref={inboxRef}>
            <button
              type="button"
              className={`notification-badge${notificationCount > 0 ? ' notification-badge-unread' : ''}`}
              title="Notification inbox"
              aria-label={`Notifications, ${notificationCount} unread`}
              aria-expanded={isInboxOpen}
              aria-controls="notification-inbox-panel"
              onClick={toggleInbox}
            >
              {notificationCount}
            </button>
            {isInboxOpen && (
              <section
                className="notification-inbox-panel"
                id="notification-inbox-panel"
                aria-label="Notification history"
              >
                <div className="notification-inbox-heading">
                  <div>
                    <p className="eyebrow">Updates</p>
                    <h2>Notification history</h2>
                  </div>
                  <button
                    type="button"
                    className="inbox-close-button"
                    aria-label="Close notification history"
                    onClick={closeInbox}
                  >
                    Close
                  </button>
                </div>
                {notificationsLoading ? (
                  <p className="inbox-state">Loading notifications...</p>
                ) : notificationsError !== null ? (
                  <p className="inbox-error" role="alert">{notificationsError}</p>
                ) : notifications.length === 0 ? (
                  <p className="inbox-state">No notifications yet.</p>
                ) : (
                  <ul className="notification-list">
                    {notifications.map(notification => (
                      <li
                        key={notification.notification_id}
                        className={notification.read_at === null ? 'notification-unread' : ''}
                      >
                        <button
                          type="button"
                          className="notification-item"
                          onClick={() => {
                            closeInbox()
                            onSelectNotification(notification)
                          }}
                        >
                          <strong>
                            Ticket #{notification.ticket_id} {formatEvent(notification.event_type)}
                          </strong>
                          <span>{notification.park_name}</span>
                          <p>{notification.issue}</p>
                          <time dateTime={notification.created_at}>
                            {new Date(notification.created_at).toLocaleString()}
                          </time>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            )}
          </div>
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

function formatEvent(eventType: string): string {
  const eventLabels: Record<string, string> = {
    ticket_updated: 'was updated',
    ticket_closed: 'was closed',
    ticket_reopened: 'was reopened',
    ticket_deleted: 'was deleted'
  }
  return eventLabels[eventType] ?? 'has a new update'
}
