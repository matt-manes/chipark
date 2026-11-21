import { useEffect, useMemo, useState } from 'react'
import { ApiErrorFormatter, type ChiparkApiClient } from '../api/ChiparkApiClient'
import type { AdminUser } from '../api/types'

export function useTicketSubmitters(api: ChiparkApiClient, enabled: boolean) {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [error, setError] = useState<string | null>(null)
  const [resolved, setResolved] = useState(false)

  useEffect(() => {
    if (!enabled) return

    const controller: AbortController = new AbortController()
    void api.getAdminUsers(controller.signal)
      .then(result => {
        if (controller.signal.aborted) return
        setUsers(result)
        setError(null)
        setResolved(true)
      })
      .catch(reason => {
        if (controller.signal.aborted) return
        setError(ApiErrorFormatter.getMessage(reason))
        setResolved(true)
      })
    return () => controller.abort()
  }, [api, enabled])

  const submitters: ReadonlyMap<number, string> = useMemo(
    () => new Map(users.map(user => [user.user_id, user.email])),
    [users]
  )

  return { submitters, error, loading: enabled && !resolved }
}
