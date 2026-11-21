import { useEffect, useMemo, useState } from 'react'
import {
  ApiErrorFormatter,
  type ChiparkApiClient
} from '../api/ChiparkApiClient'
import type { AdminUser } from '../api/types'
import AdminUserActions from '../components/AdminUserActions'
import Paginator from '../components/Paginator'
import {
  AdminUserCatalog,
  type AdminUserSortField
} from '../utils/catalog'

const PAGE_SIZE: number = 50
const DEFAULT_SORT: AdminUserSortField = 'email'
const DEFAULT_REVERSE: boolean = false

interface AdminUsersPageProps {
  api: ChiparkApiClient
  onSelectUser: (userId: number) => void
  onUserUpdated: (user: AdminUser) => void
}

export default function AdminUsersPage({
  api,
  onSelectUser,
  onUserUpdated
}: AdminUsersPageProps) {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<AdminUserSortField>(DEFAULT_SORT)
  const [reverse, setReverse] = useState(DEFAULT_REVERSE)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller: AbortController = new AbortController()
    void api.getAdminUsers(controller.signal)
      .then(result => {
        if (!controller.signal.aborted) setUsers(result)
      })
      .catch(reason => {
        if (!controller.signal.aborted) setError(ApiErrorFormatter.getMessage(reason))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [api])

  const filteredUsers: AdminUser[] = useMemo(
    () => AdminUserCatalog.filterAndSort(users, search, sortBy, reverse),
    [users, search, sortBy, reverse]
  )
  const pageCount: number = Math.max(1, Math.ceil(filteredUsers.length / PAGE_SIZE))
  const visibleUsers: AdminUser[] = filteredUsers.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE
  )

  function updateSearch(value: string): void {
    setSearch(value)
    setPage(1)
  }

  function resetFilters(): void {
    setSearch('')
    setSortBy(DEFAULT_SORT)
    setReverse(DEFAULT_REVERSE)
    setPage(1)
  }

  function updateUser(updatedUser: AdminUser): void {
    setUsers(current =>
      current.map(user => user.user_id === updatedUser.user_id ? updatedUser : user)
    )
    onUserUpdated(updatedUser)
  }

  return (
    <section className="page-section">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Administration</p>
          <h1>Registered users</h1>
          <p className="muted">Manage account roles and access.</p>
        </div>
        <span className="result-count">{filteredUsers.length} users</span>
      </div>
      <div className="filter-panel user-filters">
        <label className="search-field">
          Search users
          <input
            type="search"
            value={search}
            placeholder="Email or role"
            onChange={event => updateSearch(event.target.value)}
          />
        </label>
        <label>
          Sort by
          <select
            value={sortBy}
            onChange={event => {
              setSortBy(event.target.value as AdminUserSortField)
              setPage(1)
            }}
          >
            <option value="email">Email</option>
            <option value="role">Role</option>
            <option value="is_active">Account status</option>
          </select>
        </label>
        <label className="check-field">
          <input
            type="checkbox"
            checked={reverse}
            onChange={event => {
              setReverse(event.target.checked)
              setPage(1)
            }}
          />
          Reverse order
        </label>
        <button type="button" onClick={resetFilters}>Reset</button>
      </div>
      {error !== null && <div className="alert alert-error" role="alert">{error}</div>}
      {loading ? (
        <div className="loading-state">Loading users...</div>
      ) : (
        <div className="content-card">
          {visibleUsers.length === 0 ? (
            <p className="empty-state">No users match this search.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Account</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleUsers.map(user => (
                    <tr key={user.user_id}>
                      <td>
                        <button
                          type="button"
                          className="text-button"
                          onClick={() => onSelectUser(user.user_id)}
                        >
                          {user.email}
                        </button>
                      </td>
                      <td>{user.role}</td>
                      <td>{user.is_active ? 'Enabled' : 'Disabled'}</td>
                      <td>
                        <AdminUserActions
                          api={api}
                          user={user}
                          onUpdated={updateUser}
                          onError={setError}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
      {!loading && (
        <Paginator
          page={page}
          pageCount={pageCount}
          itemCount={filteredUsers.length}
          onChange={setPage}
        />
      )}
    </section>
  )
}
