import type { Park, Ticket, TicketStatus } from '../api/types'

export type ParkSortField = 'name' | 'ward' | 'zip_code' | 'acres'
export type TicketSortField =
  | 'ticket_id'
  | 'park_name'
  | 'file_date'
  | 'estimated_hours'

export interface ParkFilters {
  search: string
  ward: string
  zipCode: string
  parkClass: string
  minAcres: string
  maxAcres: string
  sortBy: ParkSortField
  reverse: boolean
}

export interface TicketFilters {
  search: string
  status: 'all' | TicketStatus
  sortBy: TicketSortField
  reverse: boolean
}

export class ParkCatalog {
  static filterAndSort(parks: Park[], filters: ParkFilters): Park[] {
    const search: string = filters.search.trim().toLocaleLowerCase()
    const minimum: number | null = ParkCatalog.parseNumber(filters.minAcres)
    const maximum: number | null = ParkCatalog.parseNumber(filters.maxAcres)
    const matches: Park[] = parks.filter(park => {
      const textMatches: boolean =
        search.length === 0 ||
        [park.name, park.street ?? '', park.label].some(value =>
          value.toLocaleLowerCase().includes(search)
        )
      const acres: number = ParkCatalog.parseNumber(park.acres) ?? 0
      return (
        textMatches &&
        (filters.ward === '' || park.ward === filters.ward) &&
        (filters.zipCode === '' || park.zip_code === filters.zipCode) &&
        (filters.parkClass === '' || park.park_class === filters.parkClass) &&
        (minimum === null || acres >= minimum) &&
        (maximum === null || acres <= maximum)
      )
    })

    return matches.sort((left, right) => {
      const result: number =
        filters.sortBy === 'acres'
          ? (ParkCatalog.parseNumber(left.acres) ?? 0) -
            (ParkCatalog.parseNumber(right.acres) ?? 0)
          : String(left[filters.sortBy] ?? '').localeCompare(
              String(right[filters.sortBy] ?? ''),
              undefined,
              {
                numeric: filters.sortBy === 'ward' || filters.sortBy === 'zip_code',
                sensitivity: 'base'
              }
            )
      return filters.reverse ? -result : result
    })
  }

  private static parseNumber(value: string): number | null {
    if (value.trim() === '') return null
    const parsed: number = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
}

export class TicketCatalog {
  static filterAndSort(tickets: Ticket[], filters: TicketFilters): Ticket[] {
    const search: string = filters.search.trim().toLocaleLowerCase()
    const matches: Ticket[] = tickets.filter(ticket => {
      const textMatches: boolean =
        search.length === 0 ||
        [ticket.park_name, String(ticket.ticket_id), ticket.issue].some(value =>
          value.toLocaleLowerCase().includes(search)
        )
      return (
        textMatches &&
        (filters.status === 'all' || ticket.status === filters.status)
      )
    })

    return matches.sort((left, right) => {
      let result: number
      switch (filters.sortBy) {
        case 'ticket_id':
          result = left.ticket_id - right.ticket_id
          break
        case 'file_date':
          result =
            new Date(left.file_date).getTime() -
            new Date(right.file_date).getTime()
          break
        case 'estimated_hours':
          result = TicketCatalog.compareEstimatedHours(
            left.estimated_hours,
            right.estimated_hours
          )
          break
        case 'park_name':
          result = left.park_name.localeCompare(right.park_name)
          break
      }
      return filters.reverse ? -result : result
    })
  }

  private static compareEstimatedHours(
    left: number | null,
    right: number | null
  ): number {
    if (left === null && right === null) return 0
    if (left === null) return 1
    if (right === null) return -1
    return left - right
  }
}
