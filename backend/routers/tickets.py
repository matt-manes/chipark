from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..models.ticket import Ticket, TicketStatus, TicketSubmission
from ..services.data_service import DataService

router: APIRouter = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("")
def get_tickets(
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
) -> list[Ticket]:
    return data_service.get_tickets()


@router.get("/{ticket_id}")
def get_ticket(
    ticket_id: int,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
) -> Ticket:
    try:
        return data_service.get_ticket(ticket_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("", status_code=201)
def add_ticket(
    ticket_submission: TicketSubmission,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
) -> Ticket:
    park_exists: bool = any(
        park.name == ticket_submission.park_name for park in data_service.get_parks()
    )
    if not park_exists:
        raise HTTPException(
            status_code=422,
            detail=f"Park '{ticket_submission.park_name}' was not found",
        )

    ticket: Ticket = Ticket(
        park_name=ticket_submission.park_name,
        status=TicketStatus.OPEN,
        file_date=ticket_submission.file_date,
        estimated_hours=ticket_submission.estimated_hours,
        issue=escape(ticket_submission.issue),
    )
    return data_service.add_ticket(ticket)


@router.patch("/{ticket_id}/close")
def close_ticket(
    ticket_id: int,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
) -> Ticket:
    try:
        return data_service.close_ticket(ticket_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
