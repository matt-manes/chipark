from dataclasses import dataclass
from datetime import datetime


@dataclass
class Conditions:
    """Represent current weather conditions reported for a location.

    Attributes
    ----------
    last_updated : datetime
        Time at which the weather provider last updated this observation, in UTC.
    temp_f : float
        Current temperature in degrees Fahrenheit.
    condition : str
        Text description of current weather.
    wind_mph : float
        Wind speed in miles per hour.
    wind_dir : str
        Cardinal direction of the wind.
    precip_in : float
        Precipitation in inches.
    humidity : float
        Relative humidity percentage.
    cloud : float
        Cloud cover percentage.
    feels_like_f : float
        Feels-like temperature in degrees Fahrenheit.
    heat_index_f : float
        Heat index in degrees Fahrenheit.
    uv : float
        Ultraviolet index.
    chance_of_rain : float
        Chance of rain as a percentage.
    chance_of_snow : float
        Chance of snow as a percentage.
    """

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
