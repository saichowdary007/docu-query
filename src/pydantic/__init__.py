from typing import Any

EmailStr = str

# Simple Field replacement that returns default value

def Field(default: Any = None, description: str | None = None, **kwargs: Any):
    return default

class BaseModel:
    def __init__(self, **data: Any):
        for key, value in data.items():
            setattr(self, key, value)

    def dict(self) -> dict:
        return self.__dict__
