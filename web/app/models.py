from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.orm import relationship, mapped_column, Mapped

from .db import Base


class ModelUpdateMixin:
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class User(Base, ModelUpdateMixin):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),  # pylint:disable=not-callable
    )

    weather_preferences: Mapped["UserWeatherPreferences"] = relationship(
        back_populates="user"
    )


class UserWeatherPreferences(Base, ModelUpdateMixin):
    __tablename__ = "user_weather_preferences"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    temp_min = Column(Integer, nullable=True)
    temp_max = Column(Integer, nullable=True)
    likes_rain = Column(Boolean, nullable=True)
    likes_sun = Column(Boolean, nullable=True)
    likes_wind = Column(Boolean, nullable=True)
    likes_fog = Column(Boolean, nullable=True)
    likes_snow = Column(Boolean, nullable=True)

    user: Mapped["User"] = relationship(back_populates="weather_preferences")
