import { useEffect, useState } from 'react'
import {
  ApiErrorFormatter,
  type ChiparkApiClient
} from '../api/ChiparkApiClient'
import type { AdminUser, Ticket, TicketStatus } from '../api/types'
import { TicketStatusValue } from '../api/types'
import TicketTable from '../components/TicketTable'

interface AdminUserDetailsPageProps {
  api: ChiparkApiClient
  userId: number
  onBack: () => void
  onParkName: (parkName: string) => void
  onEditTicket: (ticketId: number) => void
}

export default function AdminUserDetailsPage({
  api,
  userId,
  onBack,
  onParkName,
  onEditTicket
}: AdminUserDetailsPageProps) {
  const [account, setAccount] = useState<AdminUser | null>(null)
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [updatingTicketId, setUpdatingTicketId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller: AbortController = new AbortController()
    setLoading(true)
    setAccount(null)
    setTickets([])
    setError(null)
    void Promise.all([
      api.getAdminUser(userId, controller.signal),
      api.getTicketsForUser(userId, controller.signal)
    ])
      .then(([nextAccount, nextTickets]) => {
        if (controller.signal.aborted) return
        setAccount(nextAccount)
        setTickets(nextTickets)
      })
      .catch(reason => {
        if (!controller.signal.aborted) setError(ApiErrorFormatter.getMessage(reason))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [api, userId])

  async function changeTicketStatus(
    ticketId: number,
    status: TicketStatus
  ): Promise<void> {
    setUpdatingTicketId(ticketId)
    try {
      const updated: Ticket =
        status === TicketStatusValue.OPEN
          ? await api.reopenTicket(ticketId)
          : await api.closeTicket(ticketId)
      setTickets(current =>
        current.map(ticket => ticket.ticket_id === ticketId ? updated : ticket)
      )
    } catch (reason) {
      setError(ApiErrorFormatter.getMessage(reason))
    } finally {
      setUpdatingTicketId(null)
    }
  }

  if (loading) return <div className="loading-state">Loading user details...</div>
  if (account === null) {
    return (
      <section className="page-section">
        <button type="button" className="back-button" onClick={onBack}>
          Back to users
        </button>
        <div className="alert alert-error" role="alert">
          {error ?? 'User not found.'}
        </div>
      </section>
    )
  }

  return (
    <section className="page-section">
      <button type="button" className="back-button" onClick={onBack}>
        All users
      </button>
      {error !== null && <div className="alert alert-error" role="alert">{error}</div>}
      <div className="detail-hero card">
        <div>
          <p className="eyebrow">Registered account</p>
          <h1>{account.email}</h1>
          <p className="muted">
            {account.role} - {account.is_active ? 'Enabled' : 'Disabled'}
          </p>
        </div>
      </div>
      <section className="content-card">
        <div className="section-title">
          <div>
            <p className="eyebrow">Community reports</p>
            <h2>Submitted tickets</h2>
          </div>
          <span className="result-count">{tickets.length} tickets</span>
        </div>
        <TicketTable
          tickets={tickets}
          isAdmin
          onParkClick={onParkName}
          onClose={ticketId =>
            void changeTicketStatus(ticketId, TicketStatusValue.CLOSED)
          }
          onReopen={ticketId =>
            void changeTicketStatus(ticketId, TicketStatusValue.OPEN)
          }
          onEdit={onEditTicket}
          updatingTicketId={updatingTicketId}
        />
      </section>
    </section>
  )
}
