import { TicketCatalog } from '../utils/catalog'

interface TicketSubmitterProps {
  userId: number | null
  submitters: ReadonlyMap<number, string>
  onSelectUser: (userId: number) => void
}

export default function TicketSubmitter({
  userId,
  submitters,
  onSelectUser
}: TicketSubmitterProps) {
  if (userId === null) return <>Unknown</>

  return (
    <button
      type="button"
      className="text-button"
      onClick={() => onSelectUser(userId)}
    >
      {TicketCatalog.getSubmitterLabel(userId, submitters)}
    </button>
  )
}
