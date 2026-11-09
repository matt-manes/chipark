interface PaginatorProps {
  page: number
  pageCount: number
  itemCount: number
  onChange: (page: number) => void
}

export default function Paginator({
  page,
  pageCount,
  itemCount,
  onChange
}: PaginatorProps) {
  if (pageCount <= 1) return null

  return (
    <div className="pagination">
      <span>{itemCount} results - page {page} of {pageCount}</span>
      <div>
        <button type="button" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          Previous
        </button>
        <button type="button" disabled={page >= pageCount} onClick={() => onChange(page + 1)}>
          Next
        </button>
      </div>
    </div>
  )
}
