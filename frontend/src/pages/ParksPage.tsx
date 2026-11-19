import { useEffect, useMemo, useState } from 'react'
import { ApiErrorFormatter, type ChiparkApiClient } from '../api/ChiparkApiClient'
import type { Park } from '../api/types'
import Paginator from '../components/Paginator'
import { ParkCatalog, type ParkFilters, type ParkSortField } from '../utils/catalog'

const PAGE_SIZE: number = 50

interface ParksPageProps {
  api: ChiparkApiClient
  initialSearch: string
  onSelectPark: (parkId: number) => void
}

export default function ParksPage({
  api,
  initialSearch,
  onSelectPark
}: ParksPageProps) {
  const [parks, setParks] = useState<Park[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<ParkFilters>({
    search: initialSearch,
    ward: '',
    zipCode: '',
    parkClass: '',
    minAcres: '',
    maxAcres: '',
    sortBy: 'name',
    reverse: false
  })

  useEffect(() => {
    const controller: AbortController = new AbortController()
    void api.getParks(controller.signal)
      .then(result => {
        if (!controller.signal.aborted) setParks(result)
      })
      .catch(reason => {
        if (!controller.signal.aborted) setError(ApiErrorFormatter.getMessage(reason))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [api])

  const filteredParks: Park[] = useMemo(
    () => ParkCatalog.filterAndSort(parks, filters),
    [parks, filters]
  )
  const pageCount: number = Math.max(1, Math.ceil(filteredParks.length / PAGE_SIZE))
  const visibleParks: Park[] = filteredParks.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE
  )
  const wards: string[] = [...new Set(parks.map(park => park.ward))].sort()
  const zipCodes: string[] = [
    ...new Set(parks.map(park => park.zip_code).filter((value): value is string => value !== null))
  ].sort()
  const parkClasses: string[] = [...new Set(parks.map(park => park.park_class))].sort()

  function updateFilter<K extends keyof ParkFilters>(
    key: K,
    value: ParkFilters[K]
  ): void {
    setFilters(current => ({ ...current, [key]: value }))
    setPage(1)
  }

  return (
    <section className="page-section">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Explore Chicago</p>
          <h1>Find your next park</h1>
          <p className="muted">Browse parks and the places that make each neighborhood special.</p>
        </div>
        <span className="result-count">{filteredParks.length} parks</span>
      </div>

      <div className="filter-panel">
        <label className="search-field">
          Search parks
          <input
            type="search"
            value={filters.search}
            placeholder="Name, street, or label"
            onChange={event => updateFilter('search', event.target.value)}
          />
        </label>
        <label>
          Sort by
          <select
            value={filters.sortBy}
            onChange={event => updateFilter('sortBy', event.target.value as ParkSortField)}
          >
            <option value="name">Name</option>
            <option value="ward">Ward</option>
            <option value="zip_code">ZIP code</option>
            <option value="acres">Acreage</option>
          </select>
        </label>
        <label>
          Ward
          <select value={filters.ward} onChange={event => updateFilter('ward', event.target.value)}>
            <option value="">All wards</option>
            {wards.map(ward => <option key={ward} value={ward}>{ward}</option>)}
          </select>
        </label>
        <label>
          ZIP code
          <select value={filters.zipCode} onChange={event => updateFilter('zipCode', event.target.value)}>
            <option value="">All ZIP codes</option>
            {zipCodes.map(zip => <option key={zip} value={zip}>{zip}</option>)}
          </select>
        </label>
        <label>
          Park class
          <select value={filters.parkClass} onChange={event => updateFilter('parkClass', event.target.value)}>
            <option value="">All classes</option>
            {parkClasses.map(parkClass => <option key={parkClass} value={parkClass}>{parkClass}</option>)}
          </select>
        </label>
        <label>
          Minimum acres
          <input
            type="number"
            min="0"
            value={filters.minAcres}
            onChange={event => updateFilter('minAcres', event.target.value)}
          />
        </label>
        <label>
          Maximum acres
          <input
            type="number"
            min="0"
            value={filters.maxAcres}
            onChange={event => updateFilter('maxAcres', event.target.value)}
          />
        </label>
        <label className="check-field">
          <input
            type="checkbox"
            checked={filters.reverse}
            onChange={event => updateFilter('reverse', event.target.checked)}
          />
          Reverse order
        </label>
      </div>

      {error !== null && <div className="alert alert-error" role="alert">{error}</div>}
      {loading ? (
        <div className="loading-state">Loading parks...</div>
      ) : visibleParks.length === 0 ? (
        <div className="empty-state card">No parks match your search.</div>
      ) : (
        <div className="park-grid">
          {visibleParks.map(park => (
            <button
              type="button"
              className="park-card"
              key={park.park_id}
              onClick={() => onSelectPark(park.park_id)}
            >
              <span className="park-card-top">
                <span className="park-symbol" aria-hidden="true">+</span>
                <span className="class-tag">{park.park_class || 'Park'}</span>
              </span>
              <strong>{park.name}</strong>
              <span className="muted">{park.street ?? 'Street address unavailable'}</span>
              <span className="park-card-meta">
                <span>Ward {park.ward || '-'}</span>
                <span>{park.acres} acres</span>
                <span>{park.zip_code ?? 'ZIP unavailable'}</span>
              </span>
            </button>
          ))}
        </div>
      )}
      {!loading && (
        <Paginator
          page={page}
          pageCount={pageCount}
          itemCount={filteredParks.length}
          onChange={setPage}
        />
      )}
    </section>
  )
}
