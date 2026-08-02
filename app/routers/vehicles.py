from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])


@router.get("", response_model=list[schemas.VehicleOut])
def list_vehicles(db: Session = Depends(get_db)):
    return db.scalars(select(models.Vehicle).order_by(models.Vehicle.name)).all()


@router.get("/{vehicle_id}", response_model=schemas.VehicleOut)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    row = db.get(models.Vehicle, vehicle_id)
    if row is None:
        raise HTTPException(404, "veículo não encontrado")
    return row


@router.post("", response_model=schemas.VehicleOut, status_code=201)
def create_vehicle(payload: schemas.VehicleIn, db: Session = Depends(get_db)):
    row = models.Vehicle(**payload.model_dump())
    db.add(row)
    db.commit()
    return row


@router.put("/{vehicle_id}", response_model=schemas.VehicleOut)
def update_vehicle(vehicle_id: int, payload: schemas.VehicleIn, db: Session = Depends(get_db)):
    row = db.get(models.Vehicle, vehicle_id)
    if row is None:
        raise HTTPException(404, "veículo não encontrado")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return row
