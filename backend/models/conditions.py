from dataclasses import dataclass
from datetime import datetime


@dataclass
class Conditions:
    last_updated: datetime
    temp_f: float
    condition: str
    wind_mph: float
    wind_dir: str
    precip_in: float
    humidity: float
    cloud: float
    feels_like_f: float
    heat_index_f: float
    uv: float
    chance_of_rain: float
    chance_of_snow: float
