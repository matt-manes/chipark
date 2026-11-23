import { useState, type FormEvent } from 'react'
import {
  ApiErrorFormatter,
  type ChiparkApiClient
} from '../api/ChiparkApiClient'
import type { AuthenticatedUser } from '../api/types'
import ValidatedField from '../components/ValidatedField'

interface AccountAccessPageProps {
  api: ChiparkApiClient
  mode: 'login' | 'register'
  nextPath: string
  message: string | null
  onAuthenticated: (session: AuthenticatedUser, nextPath: string) => void
  onNavigate: (path: string) => void
}

export default function AccountAccessPage({
  api,
  mode,
  nextPath,
  message,
  onAuthenticated,
  onNavigate
}: AccountAccessPageProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isRegister = mode === 'register'

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const session: AuthenticatedUser = isRegister
        ? await api.register(email, password)
        : await api.login(email, password)
      onAuthenticated(session, nextPath)
    } catch (reason) {
      setError(ApiErrorFormatter.getMessage(reason))
    } finally {
      setSubmitting(false)
    }
  }

  function beginGoogleLogin(): void {
    sessionStorage.setItem('chipark_login_next', nextPath)
    window.location.assign(api.getGoogleLoginUrl())
  }

  return (
    <section className="auth-layout">
      <div className="auth-story">
        <p className="eyebrow">Good parks make great neighborhoods</p>
        <h1>Help keep Chicago green.</h1>
        <p>Report an issue, follow park improvements, and stay connected to the places you love.</p>
      </div>
      <form className="auth-card" onSubmit={event => void submit(event)}>
        <p className="eyebrow">{isRegister ? 'Join the community' : 'Welcome back'}</p>
        <h2>{isRegister ? 'Create your account' : 'Sign in to ChiPark'}</h2>
        {message !== null && <div className="alert alert-info" role="status">{message}</div>}
        {error !== null && <div className="alert alert-error" role="alert">{error}</div>}
        <ValidatedField label="Email" value={email}>
          {validation => (
            <input
              {...validation}
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={event => setEmail(event.target.value)}
            />
          )}
        </ValidatedField>
        <ValidatedField label="Password" value={password}>
          {validation => (
            <input
              {...validation}
              type="password"
              autoComplete={isRegister ? 'new-password' : 'current-password'}
              minLength={isRegister ? 6 : undefined}
              required
              value={password}
              onChange={event => setPassword(event.target.value)}
            />
          )}
        </ValidatedField>
        <button className="button-primary auth-submit" type="submit" disabled={submitting}>
          {submitting ? 'Please wait...' : isRegister ? 'Create account' : 'Sign in'}
        </button>
        <div className="auth-divider"><span>or</span></div>
        <button type="button" className="google-button" onClick={beginGoogleLogin}>
          Continue with Google
        </button>
        <p className="auth-switch">
          {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            type="button"
            className="text-button"
            onClick={() => onNavigate(isRegister ? '/login' : `/register?next=${encodeURIComponent(nextPath)}`)}
          >
            {isRegister ? 'Sign in' : 'Register here'}
          </button>
        </p>
      </form>
    </section>
  )
}
