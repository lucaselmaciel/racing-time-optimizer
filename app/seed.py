"""Cria as tabelas e popula os dados iniciais (pista + veículos + traçado padrão).

Uso: python -m app.seed
"""
from pathlib import Path

import numpy as np
from sqlalchemy import select, text

from app import models, services
from app.db import Base, SessionLocal, engine

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "tracks"

# Limites a_*_max são o grip MECÂNICO (baixa velocidade); o downforce (cl_a)
# multiplica o grip com a velocidade via GGV.
VEHICLES = [
    dict(
        name="Fórmula (alto grip)",
        mass=750.0,
        power=520_000.0,
        a_accel_max=13.0,
        a_brake_max=20.0,
        a_lat_max=17.0,
        cd_a=1.2,
        cl_a=3.5,
        crr=0.012,
        v_max=95.0,
    ),
    dict(
        name="GT (grip moderado)",
        mass=1300.0,
        power=370_000.0,
        a_accel_max=9.0,
        a_brake_max=14.0,
        a_lat_max=13.0,
        cd_a=1.0,
        cl_a=1.2,
        crr=0.012,
        v_max=85.0,
    ),
    dict(
        name="IndyCar",
        mass=760.0,
        power=520_000.0,
        a_accel_max=12.0,
        a_brake_max=18.0,
        a_lat_max=15.0,
        cd_a=1.1,
        cl_a=3.0,
        crr=0.012,
        v_max=93.0,
    ),
    dict(
        name="Protótipo LMP (Hypercar)",
        mass=1030.0,
        power=500_000.0,
        a_accel_max=11.0,
        a_brake_max=18.0,
        a_lat_max=14.0,
        cd_a=1.0,
        cl_a=3.0,
        crr=0.012,
        v_max=92.0,
    ),
    dict(
        name="Fórmula E",
        mass=900.0,
        power=350_000.0,
        a_accel_max=10.0,
        a_brake_max=16.0,
        a_lat_max=13.0,
        cd_a=1.1,
        cl_a=1.5,
        crr=0.012,
        v_max=78.0,
    ),
    dict(
        name="Fórmula 4",
        mass=570.0,
        power=118_000.0,
        a_accel_max=7.0,
        a_brake_max=14.0,
        a_lat_max=13.0,
        cd_a=0.9,
        cl_a=1.0,
        crr=0.012,
        v_max=58.0,
    ),
    dict(
        name="Stock Car Brasil",
        mass=1250.0,
        power=245_000.0,
        a_accel_max=7.0,
        a_brake_max=12.0,
        a_lat_max=11.0,
        cd_a=0.9,
        cl_a=0.5,
        crr=0.013,
        v_max=75.0,
    ),
    dict(
        name="Turismo (TCR)",
        mass=1285.0,
        power=260_000.0,
        a_accel_max=6.5,
        a_brake_max=12.0,
        a_lat_max=11.0,
        cd_a=0.85,
        cl_a=0.4,
        crr=0.013,
        v_max=72.0,
    ),
    dict(
        name="MotoGP",
        mass=230.0,
        power=220_000.0,
        a_accel_max=9.0,
        a_brake_max=15.0,
        a_lat_max=15.0,
        cd_a=0.35,
        cl_a=0.1,
        crr=0.015,
        v_max=100.0,
    ),
    dict(
        name="Kart (racing)",
        mass=165.0,
        power=22_000.0,
        a_accel_max=8.0,
        a_brake_max=13.0,
        a_lat_max=18.0,
        cd_a=0.6,
        cl_a=0.0,
        crr=0.015,
        v_max=40.0,
    ),
    dict(
        name="Esportivo de rua",
        mass=1500.0,
        power=400_000.0,
        a_accel_max=8.0,
        a_brake_max=11.0,
        a_lat_max=11.0,
        cd_a=0.85,
        cl_a=0.3,
        crr=0.012,
        v_max=92.0,
    ),
    dict(
        name="Hatch esportivo de rua",
        mass=1400.0,
        power=180_000.0,
        a_accel_max=5.0,
        a_brake_max=10.0,
        a_lat_max=9.5,
        cd_a=0.75,
        cl_a=0.0,
        crr=0.013,
        v_max=69.0,
    ),
]


def migrate() -> None:
    """Migrações idempotentes para bancos criados antes de colunas novas."""
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS cl_a DOUBLE PRECISION NOT NULL DEFAULT 0"
        ))


def seed() -> None:
    Base.metadata.create_all(engine)
    migrate()
    db = SessionLocal()
    try:
        for csv_path in sorted(DATA_DIR.glob("*.csv")):
            name = csv_path.stem.replace("_", " ").title()
            if db.scalar(select(models.Track).where(models.Track.name == name)):
                print(f"pista já existe: {name}")
                continue
            data = np.genfromtxt(csv_path, delimiter=",", comments="#")
            track_row = models.Track(name=name, points=data[:, :4].tolist())
            db.add(track_row)
            db.flush()
            print(f"pista criada: {name} ({len(data)} pontos)")

            # Traçado padrão: 24 pontos de controle na center line (alpha = 0).
            engine_track = services.get_engine_track(track_row)
            s_ctrl = np.linspace(0.0, engine_track.length, 24, endpoint=False)
            db.add(
                models.Trajectory(
                    name=f"{name} — center line",
                    track_id=track_row.id,
                    control_points=[{"s": float(s), "alpha": 0.0} for s in s_ctrl],
                )
            )

        for vehicle in VEHICLES:
            row = db.scalar(select(models.Vehicle).where(models.Vehicle.name == vehicle["name"]))
            if row is not None:
                # Mantém os veículos de referência alinhados ao modelo atual.
                for key, value in vehicle.items():
                    setattr(row, key, value)
                print(f"veículo atualizado: {vehicle['name']}")
            else:
                db.add(models.Vehicle(**vehicle))
                print(f"veículo criado: {vehicle['name']}")

        db.commit()
        print("seed concluído.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
