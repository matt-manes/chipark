import { useEffect, useRef, useState } from 'react'
import './App.css'
import { ApiErrorFormatter, chiparkApi } from './api/ChiparkApiClient'
import type { AuthenticatedUser, TicketNotification, User } from './api/types'
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
  const [notificationCount, setNotificationCount] = useState(0)
  const [notificationMessage, setNotificationMessage] = useState<string | null>(null)
  const latestEventId = useRef<number | null>(null)
  const parkLookupController = useRef<AbortController | null>(null)
  const authLoading: boolean =
    accessToken !== null && authResolvedToken !== accessToken

  function navigate(path: string): void {
    parkLookupController.current?.abort()
    window.history.pushState(null, '', path)
    setRoute(BrowserRoute.current())
    setErrorMessage(null)
  }

  useEffect(() => {
    const updateRoute = (): void => setRoute(BrowserRoute.current())
    window.addEventListener('popstate', updateRoute)
    return () => window.removeEventListener('popstate', updateRoute)
  }, [])

  useEffect(() => {
    chiparkApi.setAccessToken(accessToken)
    if (accessToken === null) return

    const controller: AbortController = new AbortController()
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
        if (controller.signal.aborted) return
        AuthTokenStore.clear()
        chiparkApi.setAccessToken(null)
        setAccessToken(null)
        setUser(null)
        setErrorMessage(ApiErrorFormatter.getMessage(reason))
      })
    return () => controller.abort()
  }, [accessToken])

  useEffect(() => {
    if (accessToken === null) {
      latestEventId.current = null
      return
    }

    const controller: AbortController = new AbortController()
    let retryTimer: number | null = null
    latestEventId.current = null

    async function connectToNotifications(): Promise<void> {
      try {
        await chiparkApi.streamNotifications(
          controller.signal,
          latestEventId.current,
          (notification: TicketNotification) => {
            latestEventId.current = notification.notification_id
            setNotificationCount(count => count + 1)
            setNotificationMessage(
              `Ticket #${notification.ticket_id} was ${notification.event_type.replaceAll('_', ' ')}.`
            )
          }
        )
        if (!controller.signal.aborted) {
          retryTimer = window.setTimeout(() => void connectToNotifications(), 1500)
        }
      } catch (reason) {
        if (!controller.signal.aborted) {
          setErrorMessage(`Notification connection: ${ApiErrorFormatter.getMessage(reason)}`)
          retryTimer = window.setTimeout(() => void connectToNotifications(), 3000)
        }
      }
    }

    void connectToNotifications()
    return () => {
      controller.abort()
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

  async function logout(): Promise<void> {
    let logoutError: string | null = null
    try {
      await chiparkApi.logout()
    } catch (reason) {
      logoutError = ApiErrorFormatter.getMessage(reason)
    } finally {
      AuthTokenStore.clear()
      chiparkApi.setAccessToken(null)
      setAccessToken(null)
      setUser(null)
      setAuthResolvedToken(null)
      setNotificationCount(0)
      setNotificationMessage(null)
      navigate('/parks')
      if (logoutError !== null) setErrorMessage(logoutError)
    }
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
        user={user}
        notificationCount={notificationCount}
        onNavigate={navigate}
        onLogout={() => void logout()}
      />
      {notificationMessage !== null && (
        <div className="notification-banner" role="status">
          <span>{notificationMessage}</span>
          <button type="button" aria-label="Dismiss notification" onClick={() => setNotificationMessage(null)}>Dismiss</button>
        </div>
      )}
      {errorMessage !== null && (
        <div className="global-error alert alert-error" role="alert">
          <span>{errorMessage}</span>
          <button type="button" onClick={() => setErrorMessage(null)}>Dismiss</button>
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
          onUserUpdated={setUser}
          onParkName={parkName => void navigateToParkName(parkName)}
        />
      </main>
      <footer className="app-footer">
        <span>ChiPark</span>
      </footer>
    </div>
  )
}
