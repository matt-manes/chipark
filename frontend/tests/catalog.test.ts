import assert from 'node:assert/strict'
import test from 'node:test'
import {
  AdminUserCatalog,
  ParkCatalog,
  TicketCatalog
} from '../src/utils/catalog.ts'
import type { AdminUser, Park, Ticket } from '../src/api/types.ts'

const parks: Park[] = [
  {
    park_no: '1',
    name: 'Lincoln Park',
    street: 'North Avenue',
    zip_code: '60614',
    acres: '10',
    ward: '43',
    park_class: 'REGIONAL',
    label: 'Lincoln',
    lat: 41,
    lon: -87,
    park_id: 1,
    conditions: null
  },
  {
    park_no: '2',
    name: 'Mason Park',
    street: 'South Street',
    zip_code: '60607',
    acres: '2',
    ward: '12',
    park_class: 'NEIGHBORHOOD',
    label: 'Mason',
    lat: 41,
    lon: -87,
    park_id: 2,
    conditions: null
  }
]

const tickets: Ticket[] = [
  {
    park_name: 'Lincoln Park',
    status: 1,
    file_date: '2026-01-02T10:00:00',
    estimated_hours: 5,
    issue: 'Repair broken bench',
    ticket_id: 2,
    user_id: 7
  },
  {
    park_name: 'Mason Park',
    status: 2,
    file_date: '2026-01-01T10:00:00',
    estimated_hours: 2,
    issue: 'Replace sign',
    ticket_id: 1,
    user_id: 7
  }
]

test('park catalog searches street and filters by ward', () => {
  const result = ParkCatalog.filterAndSort(parks, {
    search: 'north',
    ward: '43',
    zipCode: '',
    parkClass: '',
    minAcres: '',
    maxAcres: '',
    sortBy: 'name',
    reverse: false
  })

  assert.deepEqual(result.map(park => park.park_id), [1])
})

test('park catalog supports reversed acreage sorting', () => {
  const result = ParkCatalog.filterAndSort(parks, {
    search: '',
    ward: '',
    zipCode: '',
    parkClass: '',
    minAcres: '',
    maxAcres: '',
    sortBy: 'acres',
    reverse: true
  })

  assert.deepEqual(result.map(park => park.park_id), [1, 2])
})

test('ticket catalog searches issue text and filters status', () => {
  const result = TicketCatalog.filterAndSort(tickets, {
    search: 'bench',
    status: 1,
    sortBy: 'ticket_id',
    reverse: false
  })

  assert.deepEqual(result.map(ticket => ticket.ticket_id), [2])
})

const submitterTickets: Ticket[] = [
  { ...tickets[0], user_id: 1 },
  { ...tickets[1], user_id: 2 },
  { ...tickets[0], ticket_id: 3, user_id: null }
]
const submitters: ReadonlyMap<number, string> = new Map([
  [1, 'zara@example.com'],
  [2, 'alex@example.com']
])
const submitterFilters = {
  search: '',
  status: 'all' as const,
  sortBy: 'submitted_by' as const,
  reverse: false
}

test('ticket catalog searches submitter email case-insensitively', () => {
  const result = TicketCatalog.filterAndSort(
    submitterTickets,
    { ...submitterFilters, search: 'ALEX@' },
    submitters
  )

  assert.deepEqual(result.map(ticket => ticket.ticket_id), [1])
})

test('ticket catalog sorts by submitter including unknown submitters', () => {
  const result = TicketCatalog.filterAndSort(submitterTickets, submitterFilters, submitters)

  assert.deepEqual(result.map(ticket => ticket.ticket_id), [1, 3, 2])
})

test('ticket catalog reverses submitter sorting', () => {
  const result = TicketCatalog.filterAndSort(
    submitterTickets,
    { ...submitterFilters, reverse: true },
    submitters
  )

  assert.deepEqual(result.map(ticket => ticket.ticket_id), [2, 3, 1])
})

test('ticket catalog searches the displayed fallback for missing submitters', () => {
  const result = TicketCatalog.filterAndSort(
    submitterTickets,
    { ...submitterFilters, search: 'unknown' },
    submitters
  )

  assert.deepEqual(result.map(ticket => ticket.ticket_id), [3])
})

test('ticket catalog searches the displayed ID when an account is unavailable', () => {
  const result = TicketCatalog.filterAndSort(
    submitterTickets,
    { ...submitterFilters, search: 'user #1' },
    new Map()
  )

  assert.deepEqual(result.map(ticket => ticket.ticket_id), [2])
})

test('ticket catalog does not search submitter labels without admin data', () => {
  const result = TicketCatalog.filterAndSort(
    submitterTickets,
    { ...submitterFilters, search: 'user #1' }
  )

  assert.deepEqual(result, [])
})

const users: AdminUser[] = [
  { user_id: 1, email: 'zara@example.com', role: 'user', is_active: true },
  { user_id: 2, email: 'alex@example.com', role: 'admin', is_active: false }
]

test('admin user catalog searches email and role', () => {
  const result = AdminUserCatalog.filterAndSort(users, 'admin', 'email', false)

  assert.deepEqual(result.map(user => user.user_id), [2])
})

test('admin user catalog sorts and reverses account status', () => {
  const result = AdminUserCatalog.filterAndSort(users, '', 'is_active', true)

  assert.deepEqual(result.map(user => user.user_id), [1, 2])
})
