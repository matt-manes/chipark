from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..models.park import Park
from ..services.data_service import DataService

router: APIRouter = APIRouter(prefix="/parks", tags=["parks"])


@router.get("")
def get_parks(
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
) -> list[Park]:
    """
    Retrieve all parks.

    Parameters
    ----------
    data_service : DataService
        App-scoped service backed by the configured database.

    Returns
    -------
    list[Park]
        Parks ordered by their database identifiers.
    """
    return data_service.get_parks()


@router.get("/{park_id}")
def get_park(
    park_id: int,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
) -> Park:
    """
    Retrieve a park by its database identifier.

    Parameters
    ----------
    park_id : int
        Identifier of the requested park.
    data_service : DataService
        App-scoped service backed by the configured database.

    Returns
    -------
    Park
        Matching park.

    Raises
    ------
    HTTPException
        If the park does not exist.
    """
    try:
        return data_service.get_park(park_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
