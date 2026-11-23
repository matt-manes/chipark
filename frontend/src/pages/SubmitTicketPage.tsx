import { useEffect, useState, type FormEvent } from 'react'
import { ApiErrorFormatter, type ChiparkApiClient } from '../api/ChiparkApiClient'
import type { Park, User } from '../api/types'
import ValidatedField from '../components/ValidatedField'

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
  const [isParkListOpen, setIsParkListOpen] = useState(false)
  const [issue, setIssue] = useState('')
  const [estimatedHours, setEstimatedHours] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const matchingParks: Park[] = parks.filter(park =>
    park.name.toLocaleLowerCase().includes(parkName.trim().toLocaleLowerCase())
  )

  useEffect(() => {
    const controller: AbortController = new AbortController()
    void api.getParks(controller.signal)
      .then(result => {
        if (controller.signal.aborted) return
        const sortedParks: Park[] = [...result].sort((left, right) =>
          left.name.localeCompare(right.name, undefined, {
            numeric: true,
            sensitivity: 'base'
          })
        )
        setParks(sortedParks)
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
    if (!parks.some(park => park.name === parkName)) {
      setError('Choose a park from the list.')
      return
    }
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
        <ValidatedField label="Park" value={parkName}>
          {validation => (
            <>
              <input
                {...validation}
                type="text"
                required
                autoComplete="off"
                value={parkName}
                placeholder={loading ? 'Loading parks...' : 'Type to search parks'}
                disabled={loading}
                role="combobox"
                aria-autocomplete="list"
                aria-expanded={isParkListOpen}
                aria-controls="park-name-options"
                onFocus={() => setIsParkListOpen(true)}
                onClick={() => setIsParkListOpen(true)}
                onChange={event => {
                  setParkName(event.target.value)
                  setIsParkListOpen(true)
                }}
                onKeyDown={event => {
                  if (event.key === 'Escape') setIsParkListOpen(false)
                  if (event.key === 'Enter' && matchingParks.length > 0) {
                    event.preventDefault()
                    setParkName(matchingParks[0].name)
                    setIsParkListOpen(false)
                  }
                }}
                onBlur={() => {
                  window.setTimeout(() => setIsParkListOpen(false), 100)
                }}
              />
              {isParkListOpen && !loading && (
                <div className="park-picker-options" id="park-name-options" role="listbox">
                  {matchingParks.length > 0 ? matchingParks.map(park => (
                    <button
                      type="button"
                      key={park.park_id}
                      role="option"
                      aria-selected={park.name === parkName}
                      onMouseDown={event => event.preventDefault()}
                      onClick={() => {
                        setParkName(park.name)
                        setIsParkListOpen(false)
                      }}
                    >
                      {park.name}
                    </button>
                  )) : (
                    <span className="park-picker-empty">No parks match your search.</span>
                  )}
                </div>
              )}
            </>
          )}
        </ValidatedField>
        <ValidatedField label="What needs attention?" value={issue}>
          {validation => (
            <textarea
              {...validation}
              required
              rows={5}
              maxLength={2000}
              value={issue}
              placeholder="Describe the issue and where it is in the park."
              onChange={event => setIssue(event.target.value)}
            />
          )}
        </ValidatedField>
        {user.role === 'admin' && (
          <ValidatedField label="Estimated hours" value={estimatedHours}>
            {validation => (
              <input
                {...validation}
                type="number"
                min="0"
                step="0.25"
                value={estimatedHours}
                onChange={event => setEstimatedHours(event.target.value)}
              />
            )}
          </ValidatedField>
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
