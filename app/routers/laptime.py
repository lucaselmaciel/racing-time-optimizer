from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from engine import Vehicle

from app import models, schemas, services
from app.db import get_db

router = APIRouter(prefix="/api/laptime", tags=["laptime"])


@router.post("", response_model=schemas.LapResponse)
def compute_laptime(payload: schemas.LapRequest, db: Session = Depends(get_db)):
    track_row = db.get(models.Track, payload.track_id)
    if track_row is None:
        raise HTTPException(404, "pista não encontrada")

    if payload.vehicle is not None:
        vehicle = Vehicle(**payload.vehicle.model_dump())
    elif payload.vehicle_id is not None:
        vehicle_row = db.get(models.Vehicle, payload.vehicle_id)
        if vehicle_row is None:
            raise HTTPException(404, "veículo não encontrado")
        vehicle = services.vehicle_from_row(vehicle_row)
    else:
        raise HTTPException(422, "informe vehicle_id ou vehicle")

    track = services.get_engine_track(track_row)
    try:
        raceline, result = services.compute_lap(
            track, vehicle, payload.control_points, n_samples=payload.n_samples
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    return schemas.LapResponse(
        lap_time=result.lap_time,
        length=raceline.length,
        x=raceline.x.tolist(),
        y=raceline.y.tolist(),
        s=raceline.s.tolist(),
        v=result.v.tolist(),
        v_grip=result.v_grip.tolist(),
    )
