from typing import Literal, Optional

from pydantic import BaseModel, Field


class DomainCreate(BaseModel):
    """Payload to create a new HTTP(s) domain monitor."""

    domain: str = Field(..., examples=["example.com"], description="Hostname to monitor, without scheme.")
    name: Optional[str] = Field(None, description="Display name in Uptime Kuma. Defaults to the domain.")
    scheme: Literal["http", "https"] = Field("https", description="URL scheme used to build the monitor URL.")
    interval: int = Field(60, ge=20, description="Check interval in seconds.")
    retry_interval: int = Field(60, ge=20, description="Interval between retries in seconds.")
    max_retries: int = Field(0, ge=0, description="Number of retries before the monitor is marked down.")
    resend_interval: int = Field(0, ge=0, description="Resend notification every N checks while down (0 = disabled).")
    upside_down: bool = Field(False, description="Invert the monitor status (down means reachable).")
    ignore_tls: bool = Field(False, description="Ignore invalid/expired TLS certificates.")
    accepted_statuscodes: list[str] = Field(default_factory=lambda: ["200-299"])
    notification_ids: list[int] = Field(default_factory=list, description="Uptime Kuma notification IDs to attach.")
    active: bool = Field(True, description="Whether the monitor starts enabled.")


class DomainUpdate(BaseModel):
    """Payload to update an existing domain monitor. Only set fields are changed."""

    domain: Optional[str] = None
    name: Optional[str] = None
    scheme: Optional[Literal["http", "https"]] = None
    interval: Optional[int] = Field(None, ge=20)
    retry_interval: Optional[int] = Field(None, ge=20)
    max_retries: Optional[int] = Field(None, ge=0)
    resend_interval: Optional[int] = Field(None, ge=0)
    upside_down: Optional[bool] = None
    ignore_tls: Optional[bool] = None
    accepted_statuscodes: Optional[list[str]] = None
    notification_ids: Optional[list[int]] = None
    active: Optional[bool] = None


class DomainOut(BaseModel):
    """A domain monitor as returned by the API."""

    id: int
    domain: str
    name: str
    url: str
    active: bool
    interval: int
    retry_interval: int
    max_retries: int
    resend_interval: int
    upside_down: bool
    ignore_tls: bool
    accepted_statuscodes: list[str]
    notification_ids: list[int]


class Message(BaseModel):
    message: str
