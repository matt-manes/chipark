import type { App } from '@modelcontextprotocol/ext-apps'
import { useApp } from '@modelcontextprotocol/ext-apps/react'
import type { CallToolResult } from '@modelcontextprotocol/client'
import { useCallback, useEffect, useState, type ReactElement } from 'react'
import { createRoot } from 'react-dom/client'

interface Park {
  park_id: number
  name: string
  street: string | null
  ward: string
  zip_code: string | null
  park_class: string
}

interface Ticket {
  ticket_id: number
  park_name: string
  issue: string
  status: number
  estimated_hours: number | null
}

type View = 'parks' | 'tickets'

function extractToolData<T>(result: CallToolResult): T[] {
  const content = result.content.find(item => item.type === 'text')
  if (content?.type !== 'text') return []
  try {
    const parsed: unknown = JSON.parse(content.text)
    return Array.isArray(parsed) ? parsed as T[] : []
  } catch {
    return []
  }
}

function isPark(value: unknown): value is Park {
  return typeof value === 'object' && value !== null && 'park_id' in value
}

function isTicket(value: unknown): value is Ticket {
  return typeof value === 'object' && value !== null && 'ticket_id' in value
}

function ParksList({ parks }: { parks: Park[] }): ReactElement {
  return (
    <ul>
      {parks.map(park => (
        <li key={park.park_id}>
          <strong>{park.name}</strong> — Ward {park.ward}
          <br />
          <small>{park.street ?? 'Address unavailable'} · {park.park_class}</small>
        </li>
      ))}
    </ul>
  )
}

function TicketsList({ tickets }: { tickets: Ticket[] }): ReactElement {
  return (
    <ul>
      {tickets.map(ticket => (
        <li key={ticket.ticket_id}>
          <strong>{ticket.park_name}</strong> — {ticket.issue}
          <br />
          <small>
            Status {ticket.status} · Estimated hours: {ticket.estimated_hours ?? 'n/a'}
          </small>
        </li>
      ))}
    </ul>
  )
}

function ChiparkMcpApp(): ReactElement {
  const [view, setView] = useState<View>('parks')
  const [parks, setParks] = useState<Park[]>([])
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { app, error: appError } = useApp({
    appInfo: { name: 'Chipark Explorer', version: '1.0.0' },
    capabilities: {},
    onAppCreated: instance => {
      instance.ontoolresult = async (result: CallToolResult) => {
        const values: unknown[] = extractToolData<unknown>(result)
        if (values.some(isPark)) setParks(values.filter(isPark))
        if (values.some(isTicket)) setTickets(values.filter(isTicket))
      }
      instance.onerror = reason => setError(reason.message)
    }
  })

  const loadData = useCallback(async (instance: App, nextView: View): Promise<void> => {
    setLoading(true)
    setError(null)
    try {
      const result: CallToolResult = await instance.callServerTool({
        name: nextView === 'parks' ? 'list_parks' : 'list_tickets',
        arguments: {}
      })
      if (result.isError) {
        setError('Chipark could not load that data.')
        return
      }
      if (nextView === 'parks') setParks(extractToolData<Park>(result))
      if (nextView === 'tickets') setTickets(extractToolData<Ticket>(result))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The MCP request failed.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (app) void loadData(app, view)
  }, [app, loadData, view])

  if (appError) return <p role="alert">MCP app error: {appError.message}</p>
  if (!app) return <p>Connecting to Chipark...</p>

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: 16 }}>
      <header>
        <h1>Chipark Explorer</h1>
        <p>Browse Chipark data through the connected MCP server.</p>
        <nav aria-label="Chipark data">
          <button type="button" onClick={() => setView('parks')}>Parks</button>
          <button type="button" onClick={() => setView('tickets')}>Tickets</button>
          <button type="button" onClick={() => void loadData(app, view)} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </nav>
      </header>
      {error !== null && <p role="alert">{error}</p>}
      {view === 'parks' ? <ParksList parks={parks} /> : <TicketsList tickets={tickets} />}
    </main>
  )
}

createRoot(document.getElementById('root')!).render(<ChiparkMcpApp />)
