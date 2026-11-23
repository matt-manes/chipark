import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import { ApiErrorFormatter, chiparkApi } from './api/ChiparkApiClient'
import type {
  AuthenticatedUser,
  TicketNotification,
  User
} from './api/types'
import AppContent from './components/AppContent'
import Header from './components/Header'
import { AuthTokenStore, BrowserRoute, type RouteState } from './navigation/BrowserRoute'

export default function App() {
  const [route, setRoute] = useState<RouteState>(() => BrowserRoute.current())
  const [accessToken, setAccessToken] = useState<string | null>(
    () => AuthTokenStore.getInitialToken()
  )
  const [user, setUser] = useState<User | null>(null)
  const [authResolvedToken, setAuthResolvedToken] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null)
  const [notifications, setNotifications] = useState<TicketNotification[]>([])
  const [notificationsLoading, setNotificationsLoading] = useState(false)
  const [notificationsError, setNotificationsError] = useState<string | null>(null)
  const latestEventId = useRef<number | null>(null)
  const authRequestController = useRef<AbortController | null>(null)
  const parkLookupController = useRef<AbortController | null>(null)
  const inboxRequestController = useRef<AbortController | null>(null)
  const notificationStreamController = useRef<AbortController | null>(null)
  const notificationCount: number = notifications.filter(
    notification => notification.read_at === null
  ).length
  const authLoading: boolean =
    accessToken !== null && authResolvedToken !== accessToken

  const navigate = useCallback((path: string): void => {
    parkLookupController.current?.abort()
    window.history.pushState(null, '', path)
    setRoute(BrowserRoute.current())
    setErrorMessage(null)
    setNoticeMessage(null)
  }, [])

  const clearSession = useCallback((): void => {
    AuthTokenStore.clear()
    chiparkApi.setAccessToken(null)
    setAccessToken(null)
    setUser(null)
    setAuthResolvedToken(null)
    authRequestController.current?.abort()
    authRequestController.current = null
    inboxRequestController.current?.abort()
    inboxRequestController.current = null
    notificationStreamController.current?.abort()
    notificationStreamController.current = null
    setNotificationsLoading(false)
    setNotifications([])
    setNotificationsError(null)
  }, [])

  useEffect(() => {
    chiparkApi.setAuthenticationFailureHandler(() => {
      clearSession()
      navigate('/parks')
      setNoticeMessage("You've been logged out. Please sign in again.")
    })
    return () => chiparkApi.setAuthenticationFailureHandler(null)
  }, [clearSession, navigate])

  useEffect(() => {
    const updateRoute = (): void => setRoute(BrowserRoute.current())
    window.addEventListener('popstate', updateRoute)
    return () => window.removeEventListener('popstate', updateRoute)
  }, [])

  useEffect(() => {
    chiparkApi.setAccessToken(accessToken)
    if (accessToken === null) return

    const controller: AbortController = new AbortController()
    authRequestController.current = controller
    void chiparkApi.getCurrentUser(controller.signal)
      .then(currentUser => {
        if (controller.signal.aborted) return
        setUser(currentUser)
        setAuthResolvedToken(accessToken)
        if (BrowserRoute.current().pathname === '/auth/callback') {
          const nextPath: string =
            window.sessionStorage.getItem('chipark_login_next') ?? '/parks'
          window.sessionStorage.removeItem('chipark_login_next')
          window.history.replaceState(null, '', nextPath)
          setRoute(BrowserRoute.current())
        }
      })
      .catch(reason => {
        if (
          controller.signal.aborted ||
          ApiErrorFormatter.isAuthenticationRequired(reason)
        ) return
        clearSession()
        setErrorMessage(ApiErrorFormatter.getMessage(reason))
      })
    return () => {
      controller.abort()
      if (authRequestController.current === controller) {
        authRequestController.current = null
      }
    }
  }, [accessToken, clearSession])

  useEffect(() => {
    if (accessToken === null) {
      latestEventId.current = null
      return
    }

    const controller: AbortController = new AbortController()
    notificationStreamController.current = controller
    let retryTimer: number | null = null
    latestEventId.current = null

    async function connectToNotifications(): Promise<void> {
      try {
        await chiparkApi.streamNotifications(
          controller.signal,
          latestEventId.current,
          (notification: TicketNotification) => {
            latestEventId.current = notification.notification_id
            setNotifications(current =>
              mergeNotifications(current, [notification])
            )
          }
        )
        if (!controller.signal.aborted) {
          retryTimer = window.setTimeout(() => void connectToNotifications(), 1500)
        }
      } catch (reason) {
        if (
          !controller.signal.aborted &&
          !ApiErrorFormatter.isAuthenticationRequired(reason)
        ) {
          console.warn('Notification stream failed; retrying.', reason)
          retryTimer = window.setTimeout(() => void connectToNotifications(), 3000)
        }
      }
    }

    void connectToNotifications()
    return () => {
      controller.abort()
      if (notificationStreamController.current === controller) {
        notificationStreamController.current = null
      }
      if (retryTimer !== null) window.clearTimeout(retryTimer)
    }
  }, [accessToken])

  function onAuthenticated(session: AuthenticatedUser, nextPath: string): void {
    AuthTokenStore.save(session.access_token)
    chiparkApi.setAccessToken(session.access_token)
    setUser(session.user)
    setAccessToken(session.access_token)
    setAuthResolvedToken(session.access_token)
    navigate(nextPath)
  }

  async function openNotificationInbox(): Promise<void> {
    inboxRequestController.current?.abort()
    const controller: AbortController = new AbortController()
    inboxRequestController.current = controller
    setNotificationsLoading(true)
    setNotificationsError(null)
    try {
      const history: TicketNotification[] = await chiparkApi.getNotifications(
        controller.signal
      )
      if (controller.signal.aborted) return
      setNotifications(current => mergeNotifications(current, history))
    } catch (reason) {
      if (!controller.signal.aborted) {
        setNotificationsError(ApiErrorFormatter.getMessage(reason))
      }
    } finally {
      if (!controller.signal.aborted) setNotificationsLoading(false)
    }
  }

  function closeNotificationInbox(): void {
    inboxRequestController.current?.abort()
    inboxRequestController.current = null
    setNotificationsLoading(false)

    const unreadNotifications: TicketNotification[] = notifications.filter(
      notification => notification.read_at === null
    )
    if (unreadNotifications.length === 0) return

    const readAt: string = new Date().toISOString()
    const unreadIds: Set<number> = new Set(
      unreadNotifications.map(notification => notification.notification_id)
    )
    setNotifications(current =>
      current.map(notification =>
        unreadIds.has(notification.notification_id)
          ? { ...notification, read_at: readAt }
          : notification
      )
    )
    void Promise.all(
      unreadNotifications.map(notification =>
        chiparkApi.markNotificationRead(notification.notification_id)
      )
    ).catch(reason => {
      setNotificationsError(ApiErrorFormatter.getMessage(reason))
    })
  }

  async function logout(): Promise<void> {
    let logoutError: string | null = null
    try {
      await chiparkApi.logout()
    } catch (reason) {
      if (ApiErrorFormatter.isAuthenticationRequired(reason)) return
      logoutError = ApiErrorFormatter.getMessage(reason)
    }
    clearSession()
    navigate('/parks')
    if (logoutError !== null) setErrorMessage(logoutError)
  }

  async function navigateToParkName(parkName: string): Promise<void> {
    parkLookupController.current?.abort()
    const controller: AbortController = new AbortController()
    parkLookupController.current = controller
    try {
      const parks = await chiparkApi.getParks(controller.signal)
      if (controller.signal.aborted) return
      const park = parks.find(item => item.name === parkName)
      if (park === undefined) {
        setErrorMessage(`Park "${parkName}" was not found.`)
        return
      }
      navigate(`/parks/${park.park_id}`)
    } catch (reason) {
      if (!controller.signal.aborted) {
        setErrorMessage(ApiErrorFormatter.getMessage(reason))
      }
    }
  }

  return (
    <div className="app-shell">
      <Header
        key={user?.user_id ?? 'signed-out'}
        user={user}
        notificationCount={notificationCount}
        notifications={notifications}
        notificationsLoading={notificationsLoading}
        notificationsError={notificationsError}
        onNavigate={navigate}
        onLogout={() => void logout()}
        onOpenInbox={() => void openNotificationInbox()}
        onCloseInbox={closeNotificationInbox}
        onSelectNotification={notification => {
          navigate(`/tickets?search=${encodeURIComponent(String(notification.ticket_id))}`)
        }}
      />
      {errorMessage !== null && (
        <div className="global-error alert alert-error" role="alert">
          <span>{errorMessage}</span>
          <button type="button" onClick={() => setErrorMessage(null)}>Dismiss</button>
        </div>
      )}
      {noticeMessage !== null && (
        <div className="global-error alert alert-info" role="status">
          <span>{noticeMessage}</span>
          <button type="button" onClick={() => setNoticeMessage(null)}>Dismiss</button>
        </div>
      )}
      <main>
        <AppContent
          api={chiparkApi}
          route={route}
          user={user}
          authLoading={authLoading}
          onNavigate={navigate}
          onAuthenticated={onAuthenticated}
          onUserUpdated={updatedUser => {
            setUser(current =>
              current?.user_id === updatedUser.user_id ? updatedUser : current
            )
          }}
          onParkName={parkName => void navigateToParkName(parkName)}
        />
      </main>
      <footer className="app-footer">
        <span>ChiPark</span>
      </footer>
    </div>
  )
}

function mergeNotifications(
  current: TicketNotification[],
  incoming: TicketNotification[]
): TicketNotification[] {
  const notificationsById: Map<number, TicketNotification> = new Map(
    current.map(notification => [notification.notification_id, notification])
  )
  for (const notification of incoming) {
    const existing: TicketNotification | undefined = notificationsById.get(
      notification.notification_id
    )
    notificationsById.set(
      notification.notification_id,
      existing !== undefined && existing.read_at !== null
        ? { ...notification, read_at: existing.read_at }
        : notification
    )
  }
  return [...notificationsById.values()]
    .sort((left, right) => right.notification_id - left.notification_id)
    .slice(0, 100)
}
