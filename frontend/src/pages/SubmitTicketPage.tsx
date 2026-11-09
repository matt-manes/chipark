import { useEffect, useState, type FormEvent } from 'react'
import { ApiErrorFormatter, type ChiparkApiClient } from '../api/ChiparkApiClient'
import type { Park, User } from '../api/types'

interface SubmitTicketPageProps {
  api: ChiparkApiClient
  user: User
  initialParkId: number | null
  onComplete: () => void
}

export default function SubmitTicketPage({
  api,
  user,
  initialParkId,
  onComplete
}: SubmitTicketPageProps) {
  const [parks, setParks] = useState<Park[]>([])
  const [parkName, setParkName] = useState('')
  const [issue, setIssue] = useState('')
  const [estimatedHours, setEstimatedHours] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    const controller: AbortController = new AbortController()
    void api.getParks(controller.signal)
      .then(result => {
        if (controller.signal.aborted) return
        setParks(result)
        const selectedPark: Park | undefined = result.find(
          park => park.park_id === initialParkId
        )
        if (selectedPark !== undefined) setParkName(selectedPark.name)
      })
      .catch(reason => {
        if (!controller.signal.aborted) setError(ApiErrorFormatter.getMessage(reason))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [api, initialParkId])

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setError(null)
    setNotice(null)
    setSubmitting(true)
    try {
      await api.submitTicket({
        park_name: parkName,
        issue,
        ...(user.role === 'admin' && estimatedHours !== ''
          ? { estimated_hours: Number(estimatedHours) }
          : {})
      })
      setNotice('Your ticket was submitted.')
      setParkName('')
      setIssue('')
      setEstimatedHours('')
    } catch (reason) {
      setError(ApiErrorFormatter.getMessage(reason))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="page-section narrow-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Help care for your neighborhood</p>
          <h1>Submit a park issue</h1>
          <p className="muted">Tell us what needs attention and our team will follow up.</p>
        </div>
      </div>
      <form className="content-card form-card" onSubmit={event => void submit(event)}>
        {error !== null && <div className="alert alert-error" role="alert">{error}</div>}
        {notice !== null && <div className="alert alert-success" role="status">{notice}</div>}
        <label>
          Park
          <select required value={parkName} onChange={event => setParkName(event.target.value)}>
            <option value="">{loading ? 'Loading parks...' : 'Choose a park'}</option>
            {parks.map(park => <option key={park.park_id} value={park.name}>{park.name}</option>)}
          </select>
        </label>
        <label>
          What needs attention?
          <textarea
            required
            rows={5}
            maxLength={2000}
            value={issue}
            placeholder="Describe the issue and where it is in the park."
            onChange={event => setIssue(event.target.value)}
          />
        </label>
        {user.role === 'admin' && (
          <label>
            Estimated hours
            <input
              type="number"
              min="0"
              step="0.25"
              value={estimatedHours}
              onChange={event => setEstimatedHours(event.target.value)}
            />
          </label>
        )}
        <div className="form-actions">
          <button type="button" onClick={onComplete}>Cancel</button>
          <button className="button-primary" type="submit" disabled={loading || submitting}>
            {submitting ? 'Submitting...' : 'Submit ticket'}
          </button>
        </div>
      </form>
    </section>
  )
}
