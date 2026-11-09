import { useEffect, useState } from 'react'
import { ApiErrorFormatter, type ChiparkApiClient } from '../api/ChiparkApiClient'
import type { Conditions, Park, Ticket, User } from '../api/types'
import TicketTable from '../components/TicketTable'

interface ParkDetailsPageProps {
  api: ChiparkApiClient
  parkId: number
  user: User | null
  onBack: () => void
  onSubmitTicket: (parkId: number) => void
  onParkClick: (parkName: string) => void
  onEditTicket: (ticketId: number) => void
}

export default function ParkDetailsPage({
  api,
  parkId,
  user,
  onBack,
  onSubmitTicket,
  onParkClick,
  onEditTicket
}: ParkDetailsPageProps) {
  const [park, setPark] = useState<Park | null>(null)
  const [conditions, setConditions] = useState<Conditions | null>(null)
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updatingTicketId, setUpdatingTicketId] = useState<number | null>(null)

  useEffect(() => {
    const controller: AbortController = new AbortController()
    setLoading(true)
    setError(null)
    void Promise.all([
      api.getPark(parkId, controller.signal),
      api.getConditions(parkId, controller.signal),
      api.getOpenTicketsForPark(parkId, controller.signal)
    ])
      .then(([nextPark, nextConditions, nextTickets]) => {
        if (controller.signal.aborted) return
        setPark(nextPark)
        setConditions(nextConditions)
        setTickets(nextTickets)
      })
      .catch(reason => {
        if (!controller.signal.aborted) setError(ApiErrorFormatter.getMessage(reason))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [api, parkId])

  async function closeTicket(ticketId: number): Promise<void> {
    setUpdatingTicketId(ticketId)
    try {
      await api.closeTicket(ticketId)
      setTickets(current => current.filter(ticket => ticket.ticket_id !== ticketId))
    } catch (reason) {
      setError(ApiErrorFormatter.getMessage(reason))
    } finally {
      setUpdatingTicketId(null)
    }
  }

  if (loading) return <div className="loading-state">Loading park details...</div>
  if (park === null) {
    return (
      <section className="page-section">
        <button type="button" className="back-button" onClick={onBack}>Back to parks</button>
        <div className="alert alert-error" role="alert">{error ?? 'Park not found.'}</div>
      </section>
    )
  }

  return (
    <section className="page-section">
      <button type="button" className="back-button" onClick={onBack}>All parks</button>
      {error !== null && <div className="alert alert-error" role="alert">{error}</div>}
      <div className="detail-hero card">
        <div>
          <p className="eyebrow">{park.park_class || 'Chicago park'}</p>
          <h1>{park.name}</h1>
          <p className="muted">{park.street ?? 'Street address unavailable'} - Ward {park.ward}</p>
        </div>
        <button className="button-primary" type="button" onClick={() => onSubmitTicket(park.park_id)}>
          Report an issue
        </button>
      </div>
      <div className="park-facts">
        <div className="fact-card"><span>Area</span><strong>{park.acres} acres</strong></div>
        <div className="fact-card"><span>ZIP code</span><strong>{park.zip_code ?? 'Unavailable'}</strong></div>
        <div className="fact-card"><span>Park number</span><strong>{park.park_no.replace(/\.0$/, '')}</strong></div>
      </div>
      <section className="content-card">
        <div className="section-title">
          <div><p className="eyebrow">Right now</p><h2>Current conditions</h2></div>
          {conditions !== null && <span className="muted">Updated {new Date(conditions.last_updated).toLocaleString()}</span>}
        </div>
        {conditions === null ? (
          <p className="muted">Weather conditions are currently unavailable.</p>
        ) : (
          <div className="weather-grid">
            <div className="weather-main"><strong>{Math.round(conditions.temp_f)} deg F</strong><span>{conditions.condition}</span></div>
            <div><span>Feels like</span><strong>{Math.round(conditions.feels_like_f)} deg F</strong></div>
            <div><span>Wind</span><strong>{conditions.wind_mph} mph {conditions.wind_dir}</strong></div>
            <div><span>Humidity</span><strong>{conditions.humidity}%</strong></div>
            <div><span>Chance of rain</span><strong>{conditions.chance_of_rain}%</strong></div>
            <div><span>UV index</span><strong>{conditions.uv}</strong></div>
          </div>
        )}
      </section>
      <section className="content-card">
        <div className="section-title">
          <div><p className="eyebrow">Community reports</p><h2>Open tickets</h2></div>
          <span className="result-count">{tickets.length} open</span>
        </div>
        <TicketTable
          tickets={tickets}
          isAdmin={user?.role === 'admin'}
          onParkClick={onParkClick}
          onClose={user?.role === 'admin' ? closeTicket : undefined}
          onEdit={user?.role === 'admin' ? onEditTicket : undefined}
          updatingTicketId={updatingTicketId}
        />
      </section>
    </section>
  )
}
