import { useState } from 'react'
import { ApiErrorFormatter, type ChiparkApiClient } from '../api/ChiparkApiClient'
import type { AdminUser, UserRole } from '../api/types'

interface AdminUserActionsProps {
  api: ChiparkApiClient
  user: AdminUser
  onUpdated: (user: AdminUser) => void
  onError: (message: string | null) => void
}

export default function AdminUserActions({
  api,
  user,
  onUpdated,
  onError
}: AdminUserActionsProps) {
  const [updating, setUpdating] = useState(false)

  async function updateUser(update: () => Promise<AdminUser>): Promise<void> {
    setUpdating(true)
    onError(null)
    try {
      onUpdated(await update())
    } catch (reason) {
      onError(ApiErrorFormatter.getMessage(reason))
    } finally {
      setUpdating(false)
    }
  }

  function changeRole(): void {
    const role: UserRole = user.role === 'admin' ? 'user' : 'admin'
    void updateUser(() => api.updateUserRole(user.user_id, role))
  }

  function toggleActive(): void {
    void updateUser(() => api.setUserActive(user.user_id, !user.is_active))
  }

  return (
    <div className="action-cell">
      <button type="button" disabled={updating} onClick={changeRole}>
        {user.role === 'admin' ? 'Demote' : 'Make admin'}
      </button>
      <button type="button" disabled={updating} onClick={toggleActive}>
        {user.is_active ? 'Disable' : 'Enable'}
      </button>
    </div>
  )
}
