from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db

router = APIRouter(prefix="/api/trajectories", tags=["trajectories"])


def _to_out(row: models.Trajectory) -> schemas.TrajectoryOut:
    return schemas.TrajectoryOut(
        id=row.id,
        name=row.name,
        track_id=row.track_id,
        control_points=[schemas.ControlPoint(**cp) for cp in row.control_points],
    )


@router.get("", response_model=list[schemas.TrajectoryOut])
def list_trajectories(track_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.Trajectory).order_by(models.Trajectory.updated_at.desc())
    if track_id is not None:
        query = query.where(models.Trajectory.track_id == track_id)
    return [_to_out(r) for r in db.scalars(query).all()]


@router.post("", response_model=schemas.TrajectoryOut, status_code=201)
def create_trajectory(payload: schemas.TrajectoryIn, db: Session = Depends(get_db)):
    if db.get(models.Track, payload.track_id) is None:
        raise HTTPException(404, "pista não encontrada")
    row = models.Trajectory(
        name=payload.name,
        track_id=payload.track_id,
        control_points=[cp.model_dump() for cp in payload.control_points],
    )
    db.add(row)
    db.commit()
    return _to_out(row)


@router.put("/{trajectory_id}", response_model=schemas.TrajectoryOut)
def update_trajectory(trajectory_id: int, payload: schemas.TrajectoryIn, db: Session = Depends(get_db)):
    row = db.get(models.Trajectory, trajectory_id)
    if row is None:
        raise HTTPException(404, "traçado não encontrado")
    row.name = payload.name
    row.track_id = payload.track_id
    row.control_points = [cp.model_dump() for cp in payload.control_points]
    db.commit()
    return _to_out(row)


@router.delete("/{trajectory_id}", status_code=204)
def delete_trajectory(trajectory_id: int, db: Session = Depends(get_db)):
    row = db.get(models.Trajectory, trajectory_id)
    if row is None:
        raise HTTPException(404, "traçado não encontrado")
    db.delete(row)
    db.commit()
