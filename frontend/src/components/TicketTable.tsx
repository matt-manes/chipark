import type { ChiparkApiClient } from '../api/ChiparkApiClient'
import { TicketStatusValue, type Ticket, type TicketStatus } from '../api/types'
import { useTicketSubmitters } from '../hooks/useTicketSubmitters'
import TicketSubmitter from './TicketSubmitter'

interface TicketTableProps {
  api: ChiparkApiClient
  tickets: Ticket[]
  isAdmin: boolean
  onParkClick: (parkName: string) => void
  onSelectUser: (userId: number) => void
  submitterData?: {
    submitters: ReadonlyMap<number, string>
    error: string | null
  }
  onClose?: (ticketId: number) => void
  onReopen?: (ticketId: number) => void
  onEdit?: (ticketId: number) => void
  updatingTicketId?: number | null
}

function getStatusLabel(status: TicketStatus): string {
  return status === TicketStatusValue.OPEN ? 'Open' : 'Closed'
}

export default function TicketTable({
  api,
  tickets,
  isAdmin,
  onParkClick,
  onSelectUser,
  submitterData,
  onClose,
  onReopen,
  onEdit,
  updatingTicketId = null
}: TicketTableProps) {
  const localSubmitterData = useTicketSubmitters(
    api,
    submitterData === undefined &&
      isAdmin && tickets.some(ticket => ticket.user_id !== null)
  )
  const { submitters, error } = submitterData ?? localSubmitterData

  if (tickets.length === 0) {
    return (
      <>
        {isAdmin && error !== null && (
          <div className="alert alert-error" role="alert">
            Could not load ticket submitters: {error}
          </div>
        )}
        <p className="empty-state">No tickets match these filters.</p>
      </>
    )
  }

  return (
    <>
      {isAdmin && error !== null && (
        <div className="alert alert-error" role="alert">
          Could not load ticket submitters: {error}
        </div>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Ticket</th>
              <th>Park</th>
              <th>Filed</th>
              <th>Issue</th>
              <th>Estimate</th>
              <th>Status</th>
              {isAdmin && <th>Submitted by</th>}
              {isAdmin && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {tickets.map(ticket => (
              <tr key={ticket.ticket_id}>
                <td>#{ticket.ticket_id}</td>
                <td>
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => onParkClick(ticket.park_name)}
                  >
                    {ticket.park_name}
                  </button>
                </td>
                <td>{new Date(ticket.file_date).toLocaleDateString()}</td>
                <td className="issue-cell">{ticket.issue}</td>
                <td>{ticket.estimated_hours === null ? '-' : `${ticket.estimated_hours} hrs`}</td>
                <td>
                  <span className={`status-pill ${ticket.status === TicketStatusValue.OPEN ? 'status-open' : 'status-closed'}`}>
                    {getStatusLabel(ticket.status)}
                  </span>
                </td>
                {isAdmin && (
                  <td>
                    <TicketSubmitter
                      userId={ticket.user_id}
                      submitters={submitters}
                      onSelectUser={onSelectUser}
                    />
                  </td>
                )}
                {isAdmin && (
                  <td className="action-cell">
                    <div className="ticket-actions">
                      {onEdit !== undefined && (
                        <button type="button" onClick={() => onEdit(ticket.ticket_id)}>Edit</button>
                      )}
                      {ticket.status === TicketStatusValue.OPEN && onClose !== undefined && (
                        <button
                          type="button"
                          disabled={updatingTicketId === ticket.ticket_id}
                          onClick={() => onClose(ticket.ticket_id)}
                        >
                          Close
                        </button>
                      )}
                      {ticket.status === TicketStatusValue.CLOSED && onReopen !== undefined && (
                        <button
                          type="button"
                          disabled={updatingTicketId === ticket.ticket_id}
                          onClick={() => onReopen(ticket.ticket_id)}
                        >
                          Reopen
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
