from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import laptime, optimize, tracks, trajectories, vehicles

app = FastAPI(title="Racing Line Optimizer")

app.include_router(tracks.router)
app.include_router(vehicles.router)
app.include_router(laptime.router)
app.include_router(optimize.router)
app.include_router(trajectories.router)

_ui_dir = Path(__file__).resolve().parent.parent / "ui"
app.mount("/", StaticFiles(directory=_ui_dir, html=True), name="ui")
