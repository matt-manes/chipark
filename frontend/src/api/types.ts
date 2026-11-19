export type UserRole = 'user' | 'admin'
export const TicketStatusValue = {
  OPEN: 1,
  CLOSED: 2
} as const
export type TicketStatus = typeof TicketStatusValue[keyof typeof TicketStatusValue]

export interface User {
  user_id: number
  email: string
  role: UserRole
  password_login_enabled: boolean
  google_login_enabled: boolean
  is_active: boolean
}

export interface AdminUser {
  user_id: number
  email: string
  role: UserRole
  is_active: boolean
}

export interface AuthenticatedUser {
  access_token: string
  token_type: string
  expires_at: string
  user: User
}

export interface Park {
  park_no: string
  name: string
  street: string | null
  zip_code: string | null
  acres: string
  ward: string
  park_class: string
  label: string
  lat: number
  lon: number
  park_id: number
  conditions: Conditions | null
}

export interface Conditions {
  last_updated: string
  temp_f: number
  condition: string
  wind_mph: number
  wind_dir: string
  precip_in: number
  humidity: number
  cloud: number
  feels_like_f: number
  heat_index_f: number
  uv: number
  chance_of_rain: number
  chance_of_snow: number
}

export interface Ticket {
  park_name: string
  status: TicketStatus
  file_date: string
  estimated_hours: number | null
  issue: string
  ticket_id: number
  user_id: number | null
}

export interface TicketSubmission {
  park_name: string
  estimated_hours?: number | null
  issue: string
}

export interface TicketUpdate {
  status?: TicketStatus
  estimated_hours?: number | null
  issue?: string
}

export interface ProfileUpdate {
  email?: string
  current_password?: string
  new_password?: string
}

export interface TicketNotification {
  notification_id: number
  event_type: string
  ticket_id: number
  park_name: string
  issue: string
  created_at: string
  read_at: string | null
}
