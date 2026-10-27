from dataclasses import dataclass


@dataclass
class Park:
    """
    Represent a park.

    Attributes
    ----------
    park_no : str
        Source park identifier.
    name : str
        Park name.
    street : str
        Street address or location description.
    zip_code : str
        Postal code.
    acres : str
        Park area in acres.
    ward : str
        City ward identifier.
    park_class : str
        Park classification.
    label : str
        Display label for the park.
    lat : float
        Latitude.
    lon : float
        Longitude.
    park_id : int, default=-1
        Database identifier; negative values indicate an unpersisted park.
    """

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
    park_id: int = -1
