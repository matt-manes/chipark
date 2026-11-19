import { useEffect, useMemo, useState } from 'react'
import { ApiErrorFormatter, type ChiparkApiClient } from '../api/ChiparkApiClient'
import { TicketStatusValue, type Park, type Ticket, type TicketStatus, type User } from '../api/types'
import Paginator from '../components/Paginator'
import TicketTable from '../components/TicketTable'
import { TicketCatalog, type TicketFilters, type TicketSortField } from '../utils/catalog'

const PAGE_SIZE: number = 50

interface TicketsPageProps {
  api: ChiparkApiClient
  user: User | null
  initialSearch: string
  onSelectPark: (parkId: number) => void
  onEditTicket: (ticketId: number) => void
}

export default function TicketsPage({
  api,
  user,
  initialSearch,
  onSelectPark,
  onEditTicket
}: TicketsPageProps) {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [parks, setParks] = useState<Park[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)
  const [updatingTicketId, setUpdatingTicketId] = useState<number | null>(null)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<TicketFilters>({
    search: initialSearch,
    status: 'all',
    sortBy: 'ticket_id',
    reverse: true
  })

  useEffect(() => {
    const controller: AbortController = new AbortController()
    void Promise.all([
      api.getTickets(controller.signal),
      api.getParks(controller.signal)
    ])
      .then(([nextTickets, nextParks]) => {
        if (controller.signal.aborted) return
        setTickets(nextTickets)
        setParks(nextParks)
      })
      .catch(reason => {
        if (!controller.signal.aborted) setError(ApiErrorFormatter.getMessage(reason))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [api, refreshVersion])

  const filteredTickets: Ticket[] = useMemo(
    () => TicketCatalog.filterAndSort(tickets, filters),
    [tickets, filters]
  )
  const pageCount: number = Math.max(1, Math.ceil(filteredTickets.length / PAGE_SIZE))
  const visibleTickets: Ticket[] = filteredTickets.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE
  )

  function updateFilter<K extends keyof TicketFilters>(
    key: K,
    value: TicketFilters[K]
  ): void {
    setFilters(current => ({ ...current, [key]: value }))
    setPage(1)
  }

  function visitPark(parkName: string): void {
    const park: Park | undefined = parks.find(item => item.name === parkName)
    if (park !== undefined) onSelectPark(park.park_id)
    else setError(`Park "${parkName}" was not found.`)
  }

  async function changeStatus(ticketId: number, status: TicketStatus): Promise<void> {
    setUpdatingTicketId(ticketId)
    setError(null)
    try {
      if (status === TicketStatusValue.OPEN) await api.reopenTicket(ticketId)
      else await api.closeTicket(ticketId)
      setLoading(true)
      setError(null)
      setRefreshVersion(version => version + 1)
    } catch (reason) {
      setError(ApiErrorFormatter.getMessage(reason))
    } finally {
      setUpdatingTicketId(null)
    }
  }

  return (
    <section className="page-section">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Maintenance board</p>
          <h1>Park tickets</h1>
          <p className="muted">Track reports from across the city and follow their progress.</p>
        </div>
        <span className="result-count">{filteredTickets.length} tickets</span>
      </div>
      <div className="filter-panel ticket-filters">
        <label className="search-field">
          Search tickets
          <input
            type="search"
            value={filters.search}
            placeholder="Park, ticket number, or issue"
            onChange={event => updateFilter('search', event.target.value)}
          />
        </label>
        <label>
          Status
          <select
            value={filters.status}
            onChange={event => updateFilter(
              'status',
              event.target.value === 'all' ? 'all' : Number(event.target.value) as TicketStatus
            )}
          >
            <option value="all">All statuses</option>
            <option value={TicketStatusValue.OPEN}>Open</option>
            <option value={TicketStatusValue.CLOSED}>Closed</option>
          </select>
        </label>
        <label>
          Sort by
          <select
            value={filters.sortBy}
            onChange={event => updateFilter('sortBy', event.target.value as TicketSortField)}
          >
            <option value="ticket_id">Ticket number</option>
            <option value="park_name">Park</option>
            <option value="file_date">Date filed</option>
            <option value="estimated_hours">Estimated hours</option>
          </select>
        </label>
        <label className="check-field">
          <input
            type="checkbox"
            checked={filters.reverse}
            onChange={event => updateFilter('reverse', event.target.checked)}
          />
          Reverse order
        </label>
      </div>
      {error !== null && <div className="alert alert-error" role="alert">{error}</div>}
      {loading ? (
        <div className="loading-state">Loading tickets...</div>
      ) : (
        <div className="content-card">
          <TicketTable
            tickets={visibleTickets}
            isAdmin={user?.role === 'admin'}
            onParkClick={visitPark}
            onClose={ticketId => void changeStatus(ticketId, TicketStatusValue.CLOSED)}
            onReopen={ticketId => void changeStatus(ticketId, TicketStatusValue.OPEN)}
            onEdit={onEditTicket}
            updatingTicketId={updatingTicketId}
          />
        </div>
      )}
      {!loading && (
        <Paginator
          page={page}
          pageCount={pageCount}
          itemCount={filteredTickets.length}
          onChange={setPage}
        />
      )}
    </section>
  )
}
