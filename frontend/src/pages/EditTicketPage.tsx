import { useEffect, useState, type FormEvent } from 'react'
import { ApiErrorFormatter, type ChiparkApiClient } from '../api/ChiparkApiClient'
import { TicketStatusValue, type Ticket, type TicketStatus } from '../api/types'
import TicketSubmitter from '../components/TicketSubmitter'
import { useTicketSubmitters } from '../hooks/useTicketSubmitters'

interface EditTicketPageProps {
  api: ChiparkApiClient
  ticketId: number
  onBack: () => void
  onSaved: () => void
  onSelectUser: (userId: number) => void
}

export default function EditTicketPage({
  api,
  ticketId,
  onBack,
  onSaved,
  onSelectUser
}: EditTicketPageProps) {
  const [ticket, setTicket] = useState<Ticket | null>(null)
  const [issue, setIssue] = useState('')
  const [hours, setHours] = useState('')
  const [status, setStatus] = useState<TicketStatus>(TicketStatusValue.OPEN)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { submitters, error: submittersError } = useTicketSubmitters(
    api,
    ticket !== null && ticket.user_id !== null
  )

  useEffect(() => {
    const controller: AbortController = new AbortController()
    void api.getTicket(ticketId, controller.signal)
      .then(result => {
        if (controller.signal.aborted) return
        setTicket(result)
        setIssue(result.issue)
        setHours(result.estimated_hours === null ? '' : String(result.estimated_hours))
        setStatus(result.status)
      })
      .catch(reason => {
        if (!controller.signal.aborted) setError(ApiErrorFormatter.getMessage(reason))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [api, ticketId])

  async function save(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api.updateTicket(ticketId, {
        issue,
        status,
        estimated_hours: hours === '' ? null : Number(hours)
      })
      onSaved()
    } catch (reason) {
      setError(ApiErrorFormatter.getMessage(reason))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="loading-state">Loading ticket...</div>
  if (ticket === null) {
    return <section className="page-section"><div className="alert alert-error">{error ?? 'Ticket not found.'}</div></section>
  }

  return (
    <section className="page-section narrow-page">
      <button type="button" className="back-button" onClick={onBack}>Back to tickets</button>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Ticket #{ticket.ticket_id} - {ticket.park_name}</p>
          <h1>Edit ticket</h1>
          <p>
            Submitted by{' '}
            <TicketSubmitter
              userId={ticket.user_id}
              submitters={submitters}
              onSelectUser={onSelectUser}
            />
          </p>
        </div>
      </div>
      {submittersError !== null && (
        <div className="alert alert-error" role="alert">
          Could not load ticket submitter: {submittersError}
        </div>
      )}
      <form className="content-card form-card" onSubmit={event => void save(event)}>
        {error !== null && <div className="alert alert-error" role="alert">{error}</div>}
        <label>
          Issue
          <textarea required rows={5} value={issue} onChange={event => setIssue(event.target.value)} />
        </label>
        <label>
          Estimated hours
          <input
            type="number"
            min="0"
            step="0.25"
            value={hours}
            onChange={event => setHours(event.target.value)}
          />
        </label>
        <label>
          Status
          <select value={status} onChange={event => setStatus(Number(event.target.value) as TicketStatus)}>
            <option value={TicketStatusValue.OPEN}>Open</option>
            <option value={TicketStatusValue.CLOSED}>Closed</option>
          </select>
        </label>
        <div className="form-actions">
          <button type="button" onClick={onBack}>Cancel</button>
          <button className="button-primary" type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save changes'}
          </button>
        </div>
      </form>
    </section>
  )
}
