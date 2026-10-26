from dataclasses import dataclass


@dataclass
class Park:
    park_no: str
    name: str
    street: str
    zip_code: str
    acres: str
    ward: str
    park_class: str
    label: str
    lat: float
    lon: float
