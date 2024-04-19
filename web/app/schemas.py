from typing import Optional, Any
from copy import deepcopy
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, create_model, validator
from pydantic.fields import FieldInfo
from pydantic_extra_types.coordinate import Latitude, Longitude

# pylint: disable=no-self-argument


def partial_model(model: type[BaseModel]):
    def make_field_optional(
        field: FieldInfo, default: Any = None
    ) -> tuple[Any, FieldInfo]:
        new = deepcopy(field)
        new.default = default
        new.annotation = Optional[field.annotation]  # type: ignore
        return new.annotation, new

    return create_model(
        model.__name__,
        __base__=model,
        __module__=model.__module__,
        **{
            field_name: make_field_optional(field_info)
            for field_name, field_info in model.model_fields.items()
        }
    )


class BaseUserWeatherPreferences(BaseModel):
    latitude: Latitude | None
    longitude: Longitude | None
    temp_min: int | None = Field(ge=-60, le=60)
    temp_max: int | None = Field(ge=-60, le=60)
    likes_rain: bool | None
    likes_sun: bool | None
    likes_wind: bool | None
    likes_fog: bool | None
    likes_snow: bool | None

    @validator("temp_max")
    def temp_max_must_be_greater_than_temp_min(cls, temp_max, values):
        temp_min = values.get("temp_min", None)
        if temp_max is not None and temp_min is not None:
            if temp_max < values.get("temp_min"):
                raise ValueError(
                    "Max temperature must be greater than or equal to minimal temperature."
                )
        return temp_max


class UserWeatherPreferencesOut(BaseUserWeatherPreferences):
    pass


@partial_model
class UserWeatherPreferencesUpdate(BaseUserWeatherPreferences):
    pass


class WeatherForecast(BaseModel):
    weather_id: int
    current_temp: float
    feels_like: float
    image_url: AnyUrl
    description: str
    wind_speed: float = Field(description="Wind speed (m/s)")
    humidity: float =  Field(description="Humidity (percentage)")
    visibility: float = Field(description="Visibility (meters)")
    pressure: float = Field(description="Pressure (hPa)")
    dt: datetime


class UserBase(BaseModel):
    username: str = Field(min_length=4, max_length=50)


class UserCreate(UserBase):
    password: str = Field(min_length=5, max_length=50)


class UserOut(UserBase):
    id: int
    weather_preferences: UserWeatherPreferencesOut

    class Config:
        from_attributes = True
