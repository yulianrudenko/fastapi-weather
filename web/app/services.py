from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from . import models, schemas, selectors
from .utils import hash_password


def create_user(user_data: schemas.UserCreate, db: Session) -> models.User:
    """
    Creates user instance and weather preferences for it.
    Raises `HTTP_409_CONFLICT` if user with provided username already exists.
    """
    if db.query(models.User).filter(models.User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this username already exists.",
        )

    # Hash password
    user_data.password = hash_password(user_data.password)

    user = models.User(**user_data.model_dump())
    db.add(user)

    weather_preferences = models.UserWeatherPreferences(user=user)
    db.add(weather_preferences)

    db.commit()
    db.refresh(user)
    return user


def update_weather_preferences(
    user_id: int, preferences: schemas.UserWeatherPreferencesUpdate, db: Session
) -> models.UserWeatherPreferences:
    """Updates user weather preferences with provided data."""
    user = selectors.get_user(user_id=user_id, db=db, raise_exception=True)
    user.weather_preferences.update(**preferences.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(user.weather_preferences)
    return user.weather_preferences
