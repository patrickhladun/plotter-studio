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


class PlotRequest(BaseModel):
    page: str = "a5"
    s_down: int = 30
    s_up: int = 70
    p_down: int = 40
    p_up: int = 70
    handling: int = 1
    speed: int = 70
    brushless: bool = False
    penlift: int | None = None
    no_homing: bool = False
    model: str | None = None
    layer: str | None = None

    @property
    def penlift_value(self) -> int | None:
        if self.penlift in {1, 2, 3}:
            return self.penlift
        if self.brushless:
            return 3
        return None

