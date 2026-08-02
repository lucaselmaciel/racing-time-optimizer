from pydantic import BaseModel, Field


class ControlPoint(BaseModel):
    s: float = Field(description="posição na center line em metros")
    alpha: float = Field(description="offset lateral em metros (positivo = direita)")


class TrackSummary(BaseModel):
    id: int
    name: str
    length: float


class TrackDetail(BaseModel):
    id: int
    name: str
    length: float
    # Center line reamostrada para render: listas paralelas.
    x: list[float]
    y: list[float]
    s: list[float]
    w_right: list[float]
    w_left: list[float]
    normal_x: list[float]
    normal_y: list[float]


class VehicleIn(BaseModel):
    name: str
    mass: float = Field(gt=0)
    power: float = Field(gt=0, description="W")
    a_accel_max: float = Field(gt=0)
    a_brake_max: float = Field(gt=0)
    a_lat_max: float = Field(gt=0)
    cd_a: float = 0.0
    cl_a: float = 0.0
    crr: float = 0.0
    v_max: float = 100.0


class VehicleOut(VehicleIn):
    id: int

    model_config = {"from_attributes": True}


class LapRequest(BaseModel):
    track_id: int
    # Ou referencia um veículo salvo, ou envia os parâmetros inline (para o
    # painel reativo da UI, que recalcula sem persistir).
    vehicle_id: int | None = None
    vehicle: VehicleIn | None = None
    control_points: list[ControlPoint] = Field(min_length=3)
    n_samples: int = Field(default=600, ge=100, le=3000)


class LapResponse(BaseModel):
    lap_time: float
    length: float
    # Traçado discretizado e perfil de velocidade, para render.
    x: list[float]
    y: list[float]
    s: list[float]
    v: list[float]
    v_grip: list[float]


class OptimizeRequest(BaseModel):
    track_id: int
    vehicle_id: int | None = None
    vehicle: VehicleIn | None = None
    n_ctrl: int = Field(default=96, ge=12, le=300)
    margin: float = Field(default=1.0, ge=0.0, le=5.0)


class OptimizeResponse(BaseModel):
    control_points: list[ControlPoint]
    lap: LapResponse


class TrajectoryIn(BaseModel):
    name: str
    track_id: int
    control_points: list[ControlPoint] = Field(min_length=3)


class TrajectoryOut(TrajectoryIn):
    id: int

    model_config = {"from_attributes": True}
