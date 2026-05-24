from pydantic import BaseModel
from typing import Optional


class UserRegisterRequest(BaseModel):

    phone_number: str
    name: str
    age: int
    gender: str
    pincode: str
    language: str = "en"


class UserResponse(BaseModel):

    id: Optional[int] = None
    phone_number: str
    name: str
    age: int
    gender: str
    pincode: str
    location_area: Optional[str] = None
    language: str