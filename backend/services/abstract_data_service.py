from abc import ABC, abstractmethod

from ..models.park import Park
from ..models.ticket import Ticket


class AbstractDataService(ABC):
    @abstractmethod
    def add_park(self, park: Park) -> Park:
        raise NotImplementedError()

    @abstractmethod
    def get_parks(self) -> list[Park]:
        raise NotImplementedError()

    @abstractmethod
    def get_ticket(self, ticket_id: int) -> Ticket:
        raise NotImplementedError()

    @abstractmethod
    def get_tickets(self) -> list[Ticket]:
        raise NotImplementedError()

    @abstractmethod
    def add_ticket(self, ticket: Ticket) -> Ticket:
        raise NotImplementedError()

    @abstractmethod
    def close_ticket(self, ticket_id: int) -> Ticket:
        raise NotImplementedError()
