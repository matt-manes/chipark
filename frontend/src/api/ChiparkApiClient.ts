import axios, { type AxiosInstance } from 'axios'
import { Config } from '../config.ts'
import type {
  AdminUser,
  AuthenticatedUser,
  Conditions,
  Park,
  ProfileUpdate,
  Ticket,
  TicketNotification,
  TicketSubmission,
  TicketUpdate,
  User
} from './types'

export class ChiparkApiClient {
  private readonly client: AxiosInstance
  private accessToken: string | null = null
  private authenticationFailureHandler: (() => void) | null = null

  constructor (baseUrl: string = Config.API_BASE_URL) {
    this.client = axios.create({ baseURL: baseUrl })
    this.client.interceptors.request.use(config => {
      if (this.accessToken !== null) {
        config.headers.set('Authorization', `Bearer ${this.accessToken}`)
      }
      return config
    })
    this.client.interceptors.response.use(undefined, (error: unknown) => {
      if (axios.isAxiosError(error) && error.response?.status === 401) {
        const path: string | undefined = error.config?.url
        const authorization = error.config?.headers.get('Authorization')
        if (path !== '/auth/login' && path !== '/auth/register') {
          this.handleAuthenticationFailure(authorization)
        }
      }
      return Promise.reject(error)
    })
  }

  setAccessToken (token: string | null): void {
    this.accessToken = token
  }

  setAuthenticationFailureHandler (handler: (() => void) | null): void {
    this.authenticationFailureHandler = handler
  }

  private handleAuthenticationFailure (authorization: unknown): void {
    if (
      this.accessToken !== null &&
      authorization === `Bearer ${this.accessToken}`
    ) {
      this.authenticationFailureHandler?.()
    }
  }

  getGoogleLoginUrl (): string {
    return `${this.client.defaults.baseURL}/auth/google`
  }

  async login (email: string, password: string): Promise<AuthenticatedUser> {
    const response = await this.client.post<AuthenticatedUser>('/auth/login', {
      email,
      password
    })
    return response.data
  }

  async register (email: string, password: string): Promise<AuthenticatedUser> {
    const response = await this.client.post<AuthenticatedUser>(
      '/auth/register',
      {
        email,
        password
      }
    )
    return response.data
  }

  async logout (): Promise<void> {
    await this.client.post('/auth/logout')
  }

  async getCurrentUser (signal?: AbortSignal): Promise<User> {
    const response = await this.client.get<User>('/auth/me', { signal })
    return response.data
  }

  async updateProfile (changes: ProfileUpdate): Promise<User> {
    const response = await this.client.patch<User>('/auth/me', changes)
    return response.data
  }

  async getAdminUsers (signal?: AbortSignal): Promise<AdminUser[]> {
    const response = await this.client.get<AdminUser[]>('/admin/users', {
      signal
    })
    return response.data
  }

  async getAdminUser (userId: number, signal?: AbortSignal): Promise<AdminUser> {
    const response = await this.client.get<AdminUser>(
      `/admin/users/${userId}`,
      {
        signal
      }
    )
    return response.data
  }

  async getTicketsForUser (
    userId: number,
    signal?: AbortSignal
  ): Promise<Ticket[]> {
    const response = await this.client.get<Ticket[]>(
      `/admin/users/${userId}/tickets`,
      { signal }
    )
    return response.data
  }

  async updateUserRole (userId: number, role: User['role']): Promise<AdminUser> {
    const response = await this.client.patch<AdminUser>(
      `/admin/users/${userId}/role`,
      { role }
    )
    return response.data
  }

  async setUserActive (userId: number, isActive: boolean): Promise<AdminUser> {
    const response = await this.client.patch<AdminUser>(
      `/admin/users/${userId}/status`,
      { is_active: isActive }
    )
    return response.data
  }

  async getParks (signal?: AbortSignal): Promise<Park[]> {
    const response = await this.client.get<Park[]>('/parks', { signal })
    return response.data
  }

  async getPark (parkId: number, signal?: AbortSignal): Promise<Park> {
    const response = await this.client.get<Park>(`/parks/${parkId}`, { signal })
    return response.data
  }

  async getConditions (
    parkId: number,
    signal?: AbortSignal
  ): Promise<Conditions | null> {
    const response = await this.client.get<Conditions | null>(
      `/parks/${parkId}/conditions`,
      { signal }
    )
    return response.data
  }

  async getOpenTicketsForPark (
    parkId: number,
    signal?: AbortSignal
  ): Promise<Ticket[]> {
    const response = await this.client.get<Ticket[]>(
      `/tickets/parks/${parkId}/open`,
      { signal }
    )
    return response.data
  }

  async getTickets (signal?: AbortSignal): Promise<Ticket[]> {
    const response = await this.client.get<Ticket[]>('/tickets', { signal })
    return response.data
  }

  async getTicket (ticketId: number, signal?: AbortSignal): Promise<Ticket> {
    const response = await this.client.get<Ticket>(`/tickets/${ticketId}`, {
      signal
    })
    return response.data
  }

  async getMyTickets (signal?: AbortSignal): Promise<Ticket[]> {
    const response = await this.client.get<Ticket[]>('/tickets/mine', {
      signal
    })
    return response.data
  }

  async getNotifications (
    signal?: AbortSignal,
    limit: number = 100
  ): Promise<TicketNotification[]> {
    const response = await this.client.get<TicketNotification[]>(
      '/notifications',
      { params: { limit }, signal }
    )
    return response.data
  }

  async markNotificationRead (
    notificationId: number
  ): Promise<TicketNotification> {
    const response = await this.client.patch<TicketNotification>(
      `/notifications/${notificationId}/read`
    )
    return response.data
  }

  async submitTicket (ticket: TicketSubmission): Promise<Ticket> {
    const response = await this.client.post<Ticket>('/tickets', ticket)
    return response.data
  }

  async updateTicket (ticketId: number, changes: TicketUpdate): Promise<Ticket> {
    const response = await this.client.patch<Ticket>(
      `/tickets/${ticketId}`,
      changes
    )
    return response.data
  }

  async closeTicket (ticketId: number): Promise<Ticket> {
    const response = await this.client.patch<Ticket>(
      `/tickets/${ticketId}/close`
    )
    return response.data
  }

  async reopenTicket (ticketId: number): Promise<Ticket> {
    const response = await this.client.patch<Ticket>(
      `/tickets/${ticketId}/reopen`
    )
    return response.data
  }

  async streamNotifications (
    signal: AbortSignal,
    lastEventId: number | null,
    onNotification: (notification: TicketNotification) => void
  ): Promise<void> {
    if (this.accessToken === null) {
      throw new Error('Sign in is required to receive notifications.')
    }

    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.accessToken}`
    }
    if (lastEventId !== null) {
      headers['Last-Event-ID'] = String(lastEventId)
    }

    const response = await fetch(
      `${this.client.defaults.baseURL}/notifications/stream`,
      { headers, signal }
    )
    if (response.status === 401 && !signal.aborted) {
      this.handleAuthenticationFailure(headers.Authorization)
      throw new AuthenticationRequiredError()
    }
    if (!response.ok || response.body === null) {
      throw new Error(
        `Notification stream failed with status ${response.status}.`
      )
    }

    const reader: ReadableStreamDefaultReader<Uint8Array> =
      response.body.getReader()
    const decoder: InstanceType<typeof TextDecoder> = new TextDecoder()
    let pendingText: string = ''
    let currentId: number | null = null
    let currentData: string[] = []

    while (!signal.aborted) {
      const { done, value } = await reader.read()
      if (done) return
      pendingText += decoder.decode(value, { stream: true })
      const lines: string[] = pendingText.split(/\r?\n/)
      pendingText = lines.pop() ?? ''
      for (const line of lines) {
        if (line === '') {
          if (currentId !== null && currentData.length > 0) {
            const notification: TicketNotification = JSON.parse(
              currentData.join('\n')
            ) as TicketNotification
            onNotification({ ...notification, notification_id: currentId })
          }
          currentId = null
          currentData = []
          continue
        }
        if (line.startsWith('id:')) {
          const parsedId: number = Number(line.slice(3).trim())
          currentId = Number.isSafeInteger(parsedId) ? parsedId : null
        } else if (line.startsWith('data:')) {
          currentData.push(line.slice(5).trimStart())
        }
      }
    }
  }
}

export class AuthenticationRequiredError extends Error {
  constructor () {
    super('Authentication is required.')
    this.name = 'AuthenticationRequiredError'
  }
}

export class ApiErrorFormatter {
  static isAuthenticationRequired (error: unknown): boolean {
    return error instanceof AuthenticationRequiredError ||
      (axios.isAxiosError(error) && error.response?.status === 401)
  }

  static getMessage (error: unknown): string {
    if (axios.isAxiosError<{ detail?: unknown }>(error)) {
      const detail: unknown = error.response?.data?.detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail)) {
        const messages: string[] = detail
          .filter((item: unknown): item is { msg: string } =>
            typeof item === 'object' && item !== null &&
            'msg' in item && typeof item.msg === 'string'
          )
          .map(item => item.msg)
        if (messages.length > 0) return messages.join('\n')
      }
      if (detail !== undefined) {
        return (
          JSON.stringify(detail) ?? 'The server returned invalid error details.'
        )
      }
      return error.message
    }
    return error instanceof Error
      ? error.message
      : 'An unexpected error occurred.'
  }
}

export const chiparkApi: ChiparkApiClient = new ChiparkApiClient()
