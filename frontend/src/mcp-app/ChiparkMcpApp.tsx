import type { App } from '@modelcontextprotocol/ext-apps'
import { useApp } from '@modelcontextprotocol/ext-apps/react'
import type { CallToolResult } from '@modelcontextprotocol/client'
import { useEffect, useState, type ReactElement } from 'react'

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

async function fetchView(instance: App, view: View): Promise<CallToolResult> {
  return instance.callServerTool({
    name: view === 'parks' ? 'list_parks' : 'list_tickets',
    arguments: {}
  })
}

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

export default function ChiparkMcpApp(): ReactElement {
  const [view, setView] = useState<View>('parks')
  const [parks, setParks] = useState<Park[]>([])
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)
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

  useEffect(() => {
    if (!app) return

    let active = true
    void fetchView(app, view)
      .then(result => {
        if (!active) return
        if (result.isError) {
          setError('Chipark could not load that data.')
          return
        }
        if (view === 'parks') setParks(extractToolData<Park>(result))
        if (view === 'tickets') setTickets(extractToolData<Ticket>(result))
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : 'The MCP request failed.')
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [app, view, refreshVersion])

  function selectView(nextView: View): void {
    if (nextView === view) return
    setLoading(true)
    setError(null)
    setView(nextView)
  }

  function refresh(): void {
    setLoading(true)
    setError(null)
    setRefreshVersion(version => version + 1)
  }

  if (appError) return <p role="alert">MCP app error: {appError.message}</p>
  if (!app) return <p>Connecting to Chipark...</p>

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: 16 }}>
      <header>
        <h1>Chipark Explorer</h1>
        <p>Browse Chipark data through the connected MCP server.</p>
        <nav aria-label="Chipark data">
          <button type="button" onClick={() => selectView('parks')}>Parks</button>
          <button type="button" onClick={() => selectView('tickets')}>Tickets</button>
          <button type="button" onClick={refresh} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </nav>
      </header>
      {error !== null && <p role="alert">{error}</p>}
      {view === 'parks' ? <ParksList parks={parks} /> : <TicketsList tickets={tickets} />}
    </main>
  )
}
