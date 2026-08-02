from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas, services
from app.db import get_db

router = APIRouter(prefix="/api/tracks", tags=["tracks"])


@router.get("", response_model=list[schemas.TrackSummary])
def list_tracks(db: Session = Depends(get_db)):
    rows = db.scalars(select(models.Track).order_by(models.Track.name)).all()
    return [
        schemas.TrackSummary(id=r.id, name=r.name, length=services.get_engine_track(r).length)
        for r in rows
    ]


@router.get("/{track_id}", response_model=schemas.TrackDetail)
def get_track(track_id: int, db: Session = Depends(get_db)):
    row = db.get(models.Track, track_id)
    if row is None:
        raise HTTPException(404, "pista não encontrada")
    t = services.get_engine_track(row)
    return schemas.TrackDetail(
        id=row.id,
        name=row.name,
        length=t.length,
        x=t.x.tolist(),
        y=t.y.tolist(),
        s=t.s.tolist(),
        w_right=t.w_right.tolist(),
        w_left=t.w_left.tolist(),
        normal_x=t.normal_x.tolist(),
        normal_y=t.normal_y.tolist(),
    )
