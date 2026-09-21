from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CustomerResponse(BaseModel):
    id: int
    name: str
    phone_number: str
    email: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)