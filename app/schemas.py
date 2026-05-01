import re
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


StoreType = Literal["flagship", "regular", "outlet", "express"]
StoreStatus = Literal["active", "inactive", "temporarily_closed"]
ServiceKey = Literal[
    "pharmacy",
    "pickup",
    "returns",
    "optical",
    "photo_printing",
    "gift_wrapping",
    "automotive",
    "garden_center",
]

DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
HOURS_PATTERN = re.compile(r"^(closed|([01][0-9]|2[0-3]):[0-5][0-9]-([01][0-9]|2[0-4]):[0-5][0-9])$")


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    role: str
    status: str
    must_change_password: bool


class MessageResponse(BaseModel):
    message: str


class AdminUserCreate(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8)
    role: Literal["admin", "marketer", "viewer"]
    status: Literal["active", "inactive"] = "active"
    must_change_password: bool = True


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["admin", "marketer", "viewer"] | None = None
    status: Literal["active", "inactive"] | None = None
    must_change_password: bool | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "AdminUserUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self


class UserListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[UserResponse]


class StoreHours(BaseModel):
    mon: str
    tue: str
    wed: str
    thu: str
    fri: str
    sat: str
    sun: str

    @field_validator("*")
    @classmethod
    def validate_hours(cls, value: str) -> str:
        if not HOURS_PATTERN.match(value):
            raise ValueError('hours must be "closed" or HH:MM-HH:MM')
        if value == "closed":
            return value

        open_time, close_time = value.split("-")
        open_hour, open_minute = [int(part) for part in open_time.split(":")]
        close_hour, close_minute = [int(part) for part in close_time.split(":")]
        if (close_hour, close_minute) <= (open_hour, open_minute):
            raise ValueError("close time must be after open time")
        return value


class StoreBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    store_type: StoreType
    status: StoreStatus
    latitude: Decimal = Field(ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal = Field(ge=-180, le=180, max_digits=9, decimal_places=6)
    address_street: str = Field(min_length=1, max_length=255)
    address_city: str = Field(min_length=1, max_length=120)
    address_state: str = Field(pattern=r"^[A-Z]{2}$")
    address_postal_code: str = Field(pattern=r"^[0-9]{5}$")
    address_country: str = Field(default="USA", pattern=r"^[A-Z]{3}$")
    phone: str = Field(pattern=r"^[0-9]{3}-[0-9]{3}-[0-9]{4}$")
    services: list[ServiceKey] = Field(default_factory=list)
    hours: StoreHours


class StoreCreate(StoreBase):
    store_id: str = Field(pattern=r"^S[0-9]{4}$")


class StoreUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, pattern=r"^[0-9]{3}-[0-9]{3}-[0-9]{4}$")
    services: list[ServiceKey] | None = None
    status: StoreStatus | None = None
    hours: StoreHours | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "StoreUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self


class StoreResponse(StoreBase):
    model_config = ConfigDict(from_attributes=True)

    store_id: str


class StoreListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[StoreResponse]


class StoreSearchRequest(BaseModel):
    address: str | None = None
    postal_code: str | None = Field(default=None, pattern=r"^[0-9]{5}$")
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_digits=9, decimal_places=6)

    @model_validator(mode="after")
    def require_one_location_type(self) -> "StoreSearchRequest":
        has_coordinates = self.latitude is not None or self.longitude is not None
        if has_coordinates and (self.latitude is None or self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")

        provided = sum(
            [
                bool(self.address),
                bool(self.postal_code),
                self.latitude is not None and self.longitude is not None,
            ]
        )
        if provided != 1:
            raise ValueError("provide exactly one of address, postal_code, or latitude/longitude")
        return self


class SearchLocation(BaseModel):
    latitude: float
    longitude: float
    source: Literal["coordinates", "address", "postal_code"]
    query: str | None = None


class SearchMetadata(BaseModel):
    location: SearchLocation
    radius_miles: float
    services: list[ServiceKey]
    store_types: list[StoreType]
    open_now: bool
    result_count: int


class StoreSearchResult(StoreResponse):
    distance_miles: float
    is_open_now: bool


class StoreSearchResponse(BaseModel):
    metadata: SearchMetadata
    results: list[StoreSearchResult]


class ImportFailure(BaseModel):
    row_number: int
    store_id: str | None = None
    errors: list[str]


class StoreImportReport(BaseModel):
    total_rows_processed: int
    successfully_created: int
    successfully_updated: int
    failed: list[ImportFailure]
