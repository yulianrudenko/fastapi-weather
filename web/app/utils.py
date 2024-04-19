from datetime import datetime, timezone

import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from . import selectors, schemas, models
from .config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
OPENWEATHERMAP_API_KEY = settings.OPENWEATHERMAP_API_KEY
OPENWEATHERMAP_BASE_URL = "https://api.openweathermap.org"
OPENWEATHERMAP_CURRENT_WEATHER_URL = f"{OPENWEATHERMAP_BASE_URL}/data/2.5/weather"
OPENWEATHERMAP_FORECAST_URL = f"{OPENWEATHERMAP_BASE_URL}/data/2.5/forecast"


def raise_openweather_exception(message: str = None):
    if message is None:
        message = "OpenWeather error, please try again."
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message)


def hash_password(password: str) -> str:
    """Hash user password"""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify user password"""
    return pwd_context.verify(secret=plain, hash=hashed)


def extract_weather_data(data: dict) -> schemas.WeatherForecast:
    """
    Extracts and returns necessary weather data from provided response data.
    """
    try:
        main_data = data["main"]
        weather_data = {
            "weather_id": data["weather"][0]["id"],
            "current_temp": main_data["temp"],
            "feels_like": main_data["feels_like"],
            "image_url": f"http://openweathermap.org/img/w/{data['weather'][0]['icon']}.png",
            "description": data["weather"][0]["description"].capitalize(),
            "wind_speed": data["wind"]["speed"],
            "humidity": main_data["humidity"],
            "visibility": data["visibility"],
            "pressure": main_data["pressure"],
            "dt": datetime.fromtimestamp(data["dt"]).astimezone(timezone.utc),
        }
    except (KeyError, IndexError):
        raise_openweather_exception()

    return weather_data


def get_current_weather_for_user(user_id: int, db: Session) -> schemas.WeatherForecast:
    """
    Gets current weather forecast for user.
    Performs checks if API responded successfully, raises `HTTPException` if any error.
    """
    user = selectors.get_user(user_id=user_id, db=db, raise_exception=True)
    lat = user.weather_preferences.latitude
    lon = user.weather_preferences.longitude
    if lat is None or lon is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Please set both latitude and longitude."
        )

    response = requests.get(
        OPENWEATHERMAP_CURRENT_WEATHER_URL,
        params={
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHERMAP_API_KEY,
            "units": "metric",
        },
    )
    if response.status_code != 200:
        raise_openweather_exception()

    response = response.json()
    if int(response.get("cod", 0)) != 200:
        raise_openweather_exception()

    weather_data = extract_weather_data(data=response)
    return schemas.WeatherForecast(**weather_data)


def get_5_day_weather_for_user(user_id: int, db: Session) -> schemas.WeatherForecast:
    """
    Gets 5-day weather forecast for user based on his personal preferences.
    Response represents weather forecasts for 5 days with data every 3 hours.
    Therefore filtering only one weather item per day is required.

    Performs checks if API responded successfully, raises `HTTPException` if any error.
    """
    user = selectors.get_user(user_id=user_id, db=db, raise_exception=True)
    lat = user.weather_preferences.latitude
    lon = user.weather_preferences.longitude
    if lat is None or lon is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Please set both latitude and longitude."
        )

    response = requests.get(
        OPENWEATHERMAP_FORECAST_URL,
        params={
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHERMAP_API_KEY,
            "units": "metric",
        },
    )
    if response.status_code != 200:
        raise_openweather_exception()

    response = response.json()
    if int(response.get("cod", 0)) != 200:
        raise_openweather_exception()
    if not response.get("list"):
        raise_openweather_exception(
            message="OpenWeather couldn't provide future weather for this location."
        )

    # Extract only one unique forecast per day from list of forecasts
    # By filtering based on weather datetime (`dt_txt` value)
    # First forecast = today's forecast
    date_today = datetime.today().date()
    forecasts_data: list[schemas.WeatherForecast] = []
    for index, weather_forecast in enumerate(response["list"]):
        if index != 0:  # "Closest" forecast comes first by default
            weather_dt = datetime.strptime(
                weather_forecast["dt_txt"], "%Y-%m-%d %H:%M:%S"
            )
            # Consider only 12am forecasts
            if weather_dt.hour != 12 or weather_dt.date() == date_today:
                continue
        parsed_forecast_data = extract_weather_data(data=weather_forecast)
        parsed_forecast_data = schemas.WeatherForecast(**parsed_forecast_data)
        forecasts_data.append(parsed_forecast_data)
        # Limit to 5 forecasts (5 days)
        if len(forecasts_data) >= 5:
            break

    best_forecast = pick_best_forecast_for_user(forecasts=forecasts_data, user=user)
    return best_forecast


def pick_best_forecast_for_user(
    forecasts: list[schemas.WeatherForecast], user: models.User
) -> schemas.WeatherForecast:
    """Picks the best forecast from list of forecasts based on user preferences."""
    user_prefs = user.weather_preferences
    forecasts_score: dict[int, int] = {}

    for forecast_index, forecast in enumerate(forecasts):
        score = 0

        # Temperature preference
        temp = forecast.current_temp
        if user_prefs.temp_min is not None:
            if temp < user_prefs.temp_min:
                score -= 7.5
            else:
                score += 7.5
        if score >= 0:
            if user_prefs.temp_max is not None:
                if temp > user_prefs.temp_max:
                    score -= 7.5
                else:
                    score += 7.5

        # Filtering based on weather condition preference
        weather_id = str(forecast.weather_id)

        # Group 2xx: Thunderstorm, Group 3xx: Drizzle, Group 5xx: Rain
        is_raining = weather_id[0] in ["2", "3", "5"]
        if is_raining:
            if user_prefs.likes_rain is True:
                score += 10
            elif user_prefs.likes_rain is False:
                score -= 10

        # Sun and clouds
        elif weather_id.startswith("8"):
            is_clear = weather_id in ["800", "801"]  # Clear, Few clouds
            is_cloudy = weather_id in ["802", "803", "804"]  # Clouds
            if user_prefs.likes_sun is True:
                if is_clear:
                    score += 10
                elif is_cloudy:
                    score -= 10
            if user_prefs.likes_sun is False:
                if is_clear:
                    score -= 10
                elif is_cloudy:
                    score += 10

        # Snow
        elif weather_id.startswith("6"):
            if user_prefs.likes_snow is True:
                score += 10
            if user_prefs.likes_snow is False:
                score -= 10

        # Fog
        elif weather_id in ["701", "711", "721", "741"]:
            if user_prefs.likes_fog is True:
                score += 10
            if user_prefs.likes_fog is False:
                score -= 10

        # Additional wind check
        if forecast.wind_speed > 6:
            # Windy
            if user_prefs.likes_wind is True:
                score += 3
            elif user_prefs.likes_wind is False:
                score -= 3
        else:
            # Not windy
            if user_prefs.likes_wind is True:
                score -= 3
            elif user_prefs.likes_wind is False:
                score += 3

        forecasts_score[forecast_index] = score

    sorted_forecasts: list[tuple[int]] = sorted(
        forecasts_score.items(), key=lambda x: x[1], reverse=True
    )

    # for ind, score in sorted_forecasts:
    #     print({**forecasts[ind].model_dump(), "SCORE": score})

    best_forcasts = [sorted_forecasts[0]]
    best_score = sorted_forecasts[0][1]
    for forecast_index, score in sorted_forecasts:
        if score != best_score:
            break
        best_forcasts.append((forecast_index, score))

    return forecasts[best_forcasts[0][0]]
