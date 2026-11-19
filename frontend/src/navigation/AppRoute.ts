import type { RouteState } from './BrowserRoute'
import { RouteParameters } from './BrowserRoute'

export type AppRoute =
  | {
      type: 'login'
      access: 'public'
      nextPath: string
      message: string | null
    }
  | {
      type: 'register'
      access: 'public'
      nextPath: string
    }
  | { type: 'auth-callback'; access: 'public' }
  | { type: 'park-details'; access: 'public'; parkId: number }
  | {
      type: 'submit-ticket'
      access: 'authenticated'
      parkId: number | null
    }
  | { type: 'edit-ticket'; access: 'admin'; ticketId: number }
  | { type: 'admin-user-details'; access: 'admin'; userId: number }
  | { type: 'admin-users'; access: 'admin' }
  | { type: 'tickets'; access: 'public'; key: string; search: string }
  | { type: 'profile'; access: 'authenticated' }
  | { type: 'parks'; access: 'public'; key: string; search: string }

export class AppRouteResolver {
  static resolve(route: RouteState): AppRoute {
    const query: URLSearchParams = new URLSearchParams(route.search)
    const nextPath: string = RouteParameters.getNextPath(route.search)
    const parkId: number | null = RouteParameters.getIdFromPath(
      route.pathname,
      /^\/parks\/(\d+)$/
    )
    const editTicketId: number | null = RouteParameters.getIdFromPath(
      route.pathname,
      /^\/tickets\/(\d+)\/edit$/
    )
    const adminUserId: number | null = RouteParameters.getIdFromPath(
      route.pathname,
      /^\/admin\/users\/(\d+)$/
    )

    if (route.pathname === '/login') {
      return {
        type: 'login',
        access: 'public',
        nextPath,
        message:
          query.get('required') === '1'
            ? 'Please sign in before submitting a ticket.'
            : null
      }
    }
    if (route.pathname === '/register') {
      return { type: 'register', access: 'public', nextPath }
    }
    if (route.pathname === '/auth/callback') {
      return { type: 'auth-callback', access: 'public' }
    }
    if (parkId !== null) {
      return { type: 'park-details', access: 'public', parkId }
    }
    if (route.pathname === '/tickets/new') {
      const requestedParkId: number | null = AppRouteResolver.getRequestedParkId(
        query.get('parkId')
      )
      return {
        type: 'submit-ticket',
        access: 'authenticated',
        parkId: requestedParkId
      }
    }
    if (editTicketId !== null) {
      return { type: 'edit-ticket', access: 'admin', ticketId: editTicketId }
    }
    if (adminUserId !== null) {
      return {
        type: 'admin-user-details',
        access: 'admin',
        userId: adminUserId
      }
    }
    if (route.pathname === '/admin/users') {
      return { type: 'admin-users', access: 'admin' }
    }
    if (route.pathname === '/tickets') {
      return {
        type: 'tickets',
        access: 'public',
        key: `${route.pathname}${route.search}`,
        search: query.get('search') ?? ''
      }
    }
    if (route.pathname === '/profile') {
      return { type: 'profile', access: 'authenticated' }
    }
    return {
      type: 'parks',
      access: 'public',
      key: `${route.pathname}${route.search}`,
      search: query.get('search') ?? ''
    }
  }

  private static getRequestedParkId(value: string | null): number | null {
    if (value === null) return null
    const parkId: number = Number(value)
    return Number.isSafeInteger(parkId) ? parkId : null
  }
}
