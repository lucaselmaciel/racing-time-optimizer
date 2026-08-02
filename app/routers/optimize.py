from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from engine import Vehicle, optimize_min_curvature
from app import models, schemas, services
from app.db import get_db

router = APIRouter(prefix="/api/optimize", tags=["optimize"])


@router.post("", response_model=schemas.OptimizeResponse)
def optimize_trajectory(payload: schemas.OptimizeRequest, db: Session = Depends(get_db)):
    """Traçado de curvatura mínima (QP) + lap time do resultado."""
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
    s_ctrl, alphas = optimize_min_curvature(track, n_ctrl=payload.n_ctrl, margin=payload.margin)
    control_points = [
        schemas.ControlPoint(s=float(s), alpha=float(a)) for s, a in zip(s_ctrl, alphas)
    ]
    raceline, result = services.compute_lap(track, vehicle, control_points)

    return schemas.OptimizeResponse(
        control_points=control_points,
        lap=schemas.LapResponse(
            lap_time=result.lap_time,
            length=raceline.length,
            x=raceline.x.tolist(),
            y=raceline.y.tolist(),
            s=raceline.s.tolist(),
            v=result.v.tolist(),
            v_grip=result.v_grip.tolist(),
        ),
    )
