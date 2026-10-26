from datetime import datetime

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ..models.ticket import TicketStatus


class Base(DeclarativeBase):
    pass


class ParkRecord(Base):
    __tablename__: str = "parks"

    park_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    park_no: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    street: Mapped[str] = mapped_column(String, nullable=False)
    zip_code: Mapped[str] = mapped_column(String, nullable=False)
    acres: Mapped[str] = mapped_column(String, nullable=False)
    ward: Mapped[str] = mapped_column(String, nullable=False)
    park_class: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)


class TicketRecord(Base):
    __tablename__: str = "tickets"

    ticket_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    park_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        SqlEnum(TicketStatus, native_enum=False), nullable=False
    )
    file_date: Mapped[datetime] = mapped_column(nullable=False)
    estimated_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    issue: Mapped[str] = mapped_column(String, nullable=False)
