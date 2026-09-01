from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Uptime Kuma instance this service talks to via Socket.IO.
    uptime_kuma_url: str
    uptime_kuma_username: str
    uptime_kuma_password: str

    # API key clients (e.g. the CRM) must send in the "X-API-Key" header.
    api_key: str

    # Default values used when a domain is created without an explicit override.
    default_scheme: str = "https"
    default_interval: int = 60
    default_retry_interval: int = 60
    default_max_retries: int = 0

    # Timeout (seconds) for the Socket.IO connection to Uptime Kuma.
    uptime_kuma_timeout: float = 15.0


settings = Settings()
