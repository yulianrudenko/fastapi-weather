from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str
    DB_URL: str
    OPENWEATHERMAP_API_KEY: str

settings = Settings()
