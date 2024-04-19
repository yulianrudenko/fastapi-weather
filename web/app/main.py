from fastapi import (
    FastAPI,
    Path,
    Depends,
    status,
)
from sqlalchemy.orm import Session

from .db import get_db
from . import schemas, services, selectors, utils

app = FastAPI()


@app.post("/users", status_code=status.HTTP_201_CREATED)
def register(
    user_data: schemas.UserCreate, db: Session = Depends(get_db)
) -> schemas.UserOut:
    """
    Register a new user with username and password.
    """
    user = services.create_user(user_data=user_data, db=db)
    return user


@app.get("/users/{id}", status_code=status.HTTP_200_OK)
def get_user(
    user_id: int = Path(alias="id", title="User ID"),
    db: Session = Depends(get_db),
) -> schemas.UserOut:
    """Retrieve user data."""
    user_obj = selectors.get_user(user_id=user_id, db=db, raise_exception=True)
    return user_obj


@app.patch("/preferences/{user_id}", status_code=status.HTTP_200_OK)
def update_user_weather_preferences(
    preferences_data: schemas.UserWeatherPreferencesUpdate,
    user_id: int = Path(title="User ID"),
    db: Session = Depends(get_db),
) -> schemas.UserWeatherPreferencesOut:
    """
    Set weather preferences for a user
    (like preferred temperature range, weather conditions, etc.).
    """
    weather_preferences = services.update_weather_preferences(
        user_id, preferences_data, db=db
    )
    return weather_preferences


@app.get("/weather/{user_id}", status_code=status.HTTP_200_OK)
def get_current_weather(
    user_id: int = Path(title="User ID"),
    db: Session = Depends(get_db),
) -> schemas.WeatherForecast:
    """
    Fetch and display the weather based on the user's saved preferences.
    """
    weather_forecast = utils.get_current_weather_for_user(user_id=user_id, db=db)
    return weather_forecast


@app.get("/forecast/custom/{user_id}", status_code=status.HTTP_200_OK)
def get_recommended_forecast_weather(
    user_id: int = Path(title="User ID"),
    db: Session = Depends(get_db),
) -> schemas.WeatherForecast:
    """
    Fetch a 5-day weather forecast
    and apply the custom algorithm to recommend the best day based on user preferences.
    """
    weather_forecast = utils.get_5_day_weather_for_user(user_id=user_id, db=db)
    return weather_forecast
