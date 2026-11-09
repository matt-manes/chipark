import { useEffect, useState, type FormEvent } from 'react'
import {
  ApiErrorFormatter,
  type ChiparkApiClient
} from '../api/ChiparkApiClient'
import { TicketStatusValue, type ProfileUpdate, type Ticket, type User } from '../api/types'
import TicketTable from '../components/TicketTable'

interface ProfilePageProps {
  api: ChiparkApiClient
  user: User
  onUserUpdated: (user: User) => void
  onParkSearch: (parkName: string) => void
  onEditTicket: (ticketId: number) => void
}

export default function ProfilePage({
  api,
  user,
  onUserUpdated,
  onParkSearch,
  onEditTicket
}: ProfilePageProps) {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [email, setEmail] = useState(user.email)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    const controller: AbortController = new AbortController()
    void api.getMyTickets(controller.signal)
      .then(result => {
        if (!controller.signal.aborted) setTickets(result)
      })
      .catch(reason => {
        if (!controller.signal.aborted) setError(ApiErrorFormatter.getMessage(reason))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [api])

  async function saveProfile(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const changes: ProfileUpdate = {}
      if (email !== user.email) changes.email = email
      if (newPassword !== '') {
        changes.current_password = currentPassword
        changes.new_password = newPassword
      }
      const updatedUser: User = await api.updateProfile(changes)
      onUserUpdated(updatedUser)
      setEmail(updatedUser.email)
      setCurrentPassword('')
      setNewPassword('')
      setNotice('Your profile was updated.')
    } catch (reason) {
      setError(ApiErrorFormatter.getMessage(reason))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="page-section">
      <div className="page-heading">
        <div><p className="eyebrow">Your ChiPark account</p><h1>Profile</h1></div>
        <span className="role-tag">{user.role}</span>
      </div>
      <div className="profile-grid">
        <form className="content-card form-card" onSubmit={event => void saveProfile(event)}>
          <div className="section-title"><div><p className="eyebrow">Account settings</p><h2>Personal details</h2></div></div>
          {error !== null && <div className="alert alert-error" role="alert">{error}</div>}
          {notice !== null && <div className="alert alert-success" role="status">{notice}</div>}
          {user.google_login_enabled ? (
            <div className="alert alert-info">Your account is linked to Google. Email and password changes are managed through Google.</div>
          ) : (
            <>
              <label>
                Email
                <input type="email" required value={email} onChange={event => setEmail(event.target.value)} />
              </label>
              <div className="form-divider" />
              <h3>Change password</h3>
              <label>
                Current password
                <input
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={event => setCurrentPassword(event.target.value)}
                />
              </label>
              <label>
                New password
                <input
                  type="password"
                  autoComplete="new-password"
                  minLength={6}
                  value={newPassword}
                  onChange={event => setNewPassword(event.target.value)}
                />
              </label>
              <p className="field-note">Leave password fields blank to keep your current password.</p>
              <button
                className="button-primary"
                type="submit"
                disabled={saving || (email === user.email && newPassword === '')}
              >
                {saving ? 'Saving...' : 'Save changes'}
              </button>
            </>
          )}
        </form>
        <section className="content-card profile-summary">
          <p className="eyebrow">Account overview</p>
          <h2>{user.email}</h2>
          <p className="muted">Member access - {user.role}</p>
          <div className="profile-stat"><strong>{tickets.length}</strong><span>tickets submitted</span></div>
          <div className="profile-stat"><strong>{tickets.filter(ticket => ticket.status === TicketStatusValue.OPEN).length}</strong><span>open reports</span></div>
        </section>
      </div>
      <section className="content-card">
        <div className="section-title"><div><p className="eyebrow">Your activity</p><h2>Submitted tickets</h2></div></div>
        {loading ? <div className="loading-state">Loading submitted tickets...</div> : (
          <TicketTable
            tickets={tickets}
            isAdmin={user.role === 'admin'}
            onParkClick={onParkSearch}
            onEdit={onEditTicket}
          />
        )}
      </section>
    </section>
  )
}
