from datetime import datetime
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
    """
    Retrieve all tickets.

    Parameters
    ----------
    data_service : DataService
        App-scoped service backed by the configured database.

    Returns
    -------
    list[Ticket]
        Tickets ordered by their database identifiers.
    """
    return data_service.get_tickets()


@router.get("/{ticket_id}")
def get_ticket(
    ticket_id: int,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
) -> Ticket:
    """
    Retrieve a ticket by its database identifier.

    Parameters
    ----------
    ticket_id : int
        Identifier of the requested ticket.
    data_service : DataService
        App-scoped service backed by the configured database.

    Returns
    -------
    Ticket
        Matching ticket.

    Raises
    ------
    HTTPException
        If the ticket does not exist.
    """
    try:
        return data_service.get_ticket(ticket_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("", status_code=201)
def add_ticket(
    ticket_submission: TicketSubmission,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
) -> Ticket:
    """
    Create an open ticket after validating its park association.

    Parameters
    ----------
    ticket_submission : TicketSubmission
        User-submitted ticket details.
    data_service : DataService
        App-scoped service backed by the configured database.

    Returns
    -------
    Ticket
        Newly created ticket with an escaped issue description.

    Raises
    ------
    HTTPException
        If the submitted park name does not match an existing park.
    """
    if not data_service.park_exists(ticket_submission.park_name):
        raise HTTPException(
            status_code=422,
            detail=f"Park '{ticket_submission.park_name}' was not found",
        )

    ticket: Ticket = Ticket(
        park_name=ticket_submission.park_name,
        status=TicketStatus.OPEN,
        file_date=datetime.now(),
        estimated_hours=ticket_submission.estimated_hours,
        issue=escape(ticket_submission.issue),
    )
    return data_service.add_ticket(ticket)


@router.patch("/{ticket_id}/close")
def close_ticket(
    ticket_id: int,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
) -> Ticket:
    """
    Mark a ticket as closed.

    Parameters
    ----------
    ticket_id : int
        Identifier of the ticket to close.
    data_service : DataService
        App-scoped service backed by the configured database.

    Returns
    -------
    Ticket
        Updated ticket with closed status.

    Raises
    ------
    HTTPException
        If the ticket does not exist.
    """
    try:
        return data_service.close_ticket(ticket_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
