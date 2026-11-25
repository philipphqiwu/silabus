"""HTTP API. `/health` works; `/gap` is a stub until there is data to answer from."""

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from silabus import __version__
from silabus.config import get_settings

app = FastAPI(
    title="Silabus",
    version=__version__,
    description="Skill demand and skill-gap queries over Indonesian tech job postings.",
)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    env: str
    version: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe used by the acceptance test and the deploy platform."""
    settings = get_settings()
    return HealthResponse(status="ok", env=settings.env, version=__version__)


@app.post("/gap", status_code=501)
def gap() -> None:
    """Skill gap for a target role. Not built yet."""
    raise HTTPException(status_code=501, detail="not implemented yet")
