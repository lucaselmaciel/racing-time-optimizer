from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Track(Base):
    """Pista: center line crua (lista de [x, y, w_right, w_left]) em metros."""

    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    points: Mapped[list] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trajectories: Mapped[list["Trajectory"]] = relationship(back_populates="track", cascade="all, delete-orphan")


class Vehicle(Base):
    """Setup de veículo com envelope GG constante (unidades SI)."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    mass: Mapped[float] = mapped_column(Float)
    power: Mapped[float] = mapped_column(Float)
    a_accel_max: Mapped[float] = mapped_column(Float)
    a_brake_max: Mapped[float] = mapped_column(Float)
    a_lat_max: Mapped[float] = mapped_column(Float)
    cd_a: Mapped[float] = mapped_column(Float, default=0.0)
    cl_a: Mapped[float] = mapped_column(Float, default=0.0)
    crr: Mapped[float] = mapped_column(Float, default=0.0)
    v_max: Mapped[float] = mapped_column(Float, default=100.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Trajectory(Base):
    """Traçado salvo pelo usuário: pontos de controle [{s, alpha}] sobre uma pista."""

    __tablename__ = "trajectories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"))
    control_points: Mapped[list] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    track: Mapped[Track] = relationship(back_populates="trajectories")
