from datetime import datetime
from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..models.ticket import Ticket, TicketStatus, TicketSubmission, TicketUpdate
from ..models.user import User
from ..services.auth_dependencies import AuthDependencies
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


@router.get("/mine")
def get_my_tickets(
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
    user: Annotated[User, Depends(AuthDependencies.require_user)],
) -> list[Ticket]:
    """Retrieve tickets submitted by the authenticated account.

    Parameters
    ----------
    data_service : DataService
        App-scoped service backed by the configured database.
    user : User
        Authenticated account.

    Returns
    -------
    list[Ticket]
        Tickets submitted by the current account.
    """
    return data_service.get_tickets_for_user(user.user_id)


@router.get("/parks/{park_id}/open")
def get_open_tickets_for_park(
    park_id: int,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
) -> list[Ticket]:
    """Retrieve open tickets for a park.

    Parameters
    ----------
    park_id : int
        Identifier of the park.
    data_service : DataService
        App-scoped service backed by the configured database.

    Returns
    -------
    list[Ticket]
        Open tickets associated with the park.

    Raises
    ------
    HTTPException
        If the park does not exist.
    """
    try:
        return data_service.get_open_tickets_for_park(park_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


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
    user: Annotated[User, Depends(AuthDependencies.require_user)],
) -> Ticket:
    """
    Create an open ticket after validating its park association.

    Parameters
    ----------
    ticket_submission : TicketSubmission
        User-submitted ticket details.
    data_service : DataService
        App-scoped service backed by the configured database.
    user : User
        Authenticated account submitting the ticket.

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
        user_id=user.user_id,
    )
    return data_service.add_ticket(ticket)


@router.patch("/{ticket_id}/close")
def close_ticket(
    ticket_id: int,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
    user: Annotated[User, Depends(AuthDependencies.require_admin)],
) -> Ticket:
    """
    Mark a ticket as closed.

    Parameters
    ----------
    ticket_id : int
        Identifier of the ticket to close.
    data_service : DataService
        App-scoped service backed by the configured database.
    user : User
        Administrator authenticated by the dependency.

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


@router.patch("/{ticket_id}/reopen")
def reopen_ticket(
    ticket_id: int,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
    user: Annotated[User, Depends(AuthDependencies.require_admin)],
) -> Ticket:
    """Reopen a ticket as an administrator.

    Parameters
    ----------
    ticket_id : int
        Identifier of the ticket to reopen.
    data_service : DataService
        App-scoped service backed by the configured database.
    user : User
        Administrator authenticated by the dependency.

    Returns
    -------
    Ticket
        Updated ticket with open status.

    Raises
    ------
    HTTPException
        If the ticket does not exist.
    """
    try:
        return data_service.reopen_ticket(ticket_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.patch("/{ticket_id}")
def update_ticket(
    ticket_id: int,
    changes: TicketUpdate,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
    user: Annotated[User, Depends(AuthDependencies.require_admin)],
) -> Ticket:
    """Update an existing ticket as an administrator.

    Parameters
    ----------
    ticket_id : int
        Identifier of the ticket to update.
    changes : TicketUpdate
        Fields to update.
    data_service : DataService
        Service used to access ticket persistence.
    user : User
        Administrator authenticated by the dependency.

    Returns
    -------
    Ticket
        Updated ticket.

    Raises
    ------
    HTTPException
        If the update is invalid or the ticket does not exist.
    """
    updates: dict[str, object] = changes.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="At least one field is required.")
    if "issue" in updates:
        issue: object = updates["issue"]
        if not isinstance(issue, str):
            raise HTTPException(status_code=422, detail="Ticket issue cannot be null.")
        updates["issue"] = escape(issue)
    try:
        return data_service.update_ticket(
            ticket_id, TicketUpdate.model_validate(updates)
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(
    ticket_id: int,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
    user: Annotated[User, Depends(AuthDependencies.require_admin)],
) -> None:
    """Delete an existing ticket as an administrator.

    Parameters
    ----------
    ticket_id : int
        Identifier of the ticket to delete.
    data_service : DataService
        Service used to access ticket persistence.
    user : User
        Administrator authenticated by the dependency.

    Raises
    ------
    HTTPException
        If the ticket does not exist.
    """
    try:
        data_service.delete_ticket(ticket_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
