from fastapi import HTTPException
from pydantic import BaseModel


class RotateRequest(BaseModel):
    angle: int = 90

    @property
    def normalized(self) -> int:
        value = self.angle % 360
        if value < 0:
            value += 360
        return value


class RenameRequest(BaseModel):
    new_name: str

    def sanitized(self, sanitize_func) -> str:
        """Use provided sanitize function to validate filename."""
        candidate = self.new_name.strip()
        if not candidate:
            raise HTTPException(status_code=400, detail="New filename cannot be empty")
        if not candidate.lower().endswith(".svg"):
            candidate = f"{candidate}.svg"
        return sanitize_func(candidate)