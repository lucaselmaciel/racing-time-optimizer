"""Modelo de veículo quasi-steady-state.

Fase 4: envelope GG dependente de velocidade via downforce — o grip escala
linearmente com a carga normal ``F_z = m·g + 0.5·ρ·Cl·A·v²``. Os limites
``a_*_max`` são o grip MECÂNICO (baixa velocidade); com ``cl_a = 0`` o modelo
volta a ser o GG constante da Fase 2.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

RHO_AIR = 1.225  # kg/m³
G = 9.81         # m/s²


@dataclass
class Vehicle:
    name: str
    mass: float            # kg
    power: float           # W (potência máxima na roda)
    a_accel_max: float     # m/s² — limite de tração longitudinal (grip mecânico)
    a_brake_max: float     # m/s² — limite de frenagem mecânico (positivo)
    a_lat_max: float       # m/s² — limite lateral mecânico
    cd_a: float = 0.0      # Cd·A em m² (arrasto)
    cl_a: float = 0.0      # Cl·A em m² (downforce)
    crr: float = 0.0       # coeficiente de resistência ao rolamento
    v_max: float = 100.0   # m/s — velocidade máxima absoluta

    def load_factor(self, v: np.ndarray) -> np.ndarray:
        """F_z(v) / F_z(0): quanto o downforce multiplica o grip."""
        return 1.0 + 0.5 * RHO_AIR * self.cl_a * np.asarray(v) ** 2 / (self.mass * G)

    def a_lat_at(self, v: np.ndarray) -> np.ndarray:
        """Limite lateral na velocidade v (GGV)."""
        return self.a_lat_max * self.load_factor(v)

    def _ellipse_factor(self, v: np.ndarray, a_y: np.ndarray) -> np.ndarray:
        """Fração do grip longitudinal disponível dado o a_y consumido:
        (a_x/a_x_max)² + (a_y/a_y_max)² ≤ 1, com limites avaliados em v."""
        ratio = np.clip(np.abs(a_y) / self.a_lat_at(v), 0.0, 1.0)
        return np.sqrt(1.0 - ratio**2)

    def drag_decel(self, v: np.ndarray) -> np.ndarray:
        """Desaceleração por arrasto + resistência ao rolamento (m/s²).
        O rolamento também cresce com a carga aerodinâmica."""
        v = np.asarray(v)
        return 0.5 * RHO_AIR * self.cd_a * v**2 / self.mass + self.crr * G * self.load_factor(v)

    def accel_available(self, v: np.ndarray, a_y: np.ndarray) -> np.ndarray:
        """Aceleração longitudinal disponível: menor entre grip (elipse, com
        carga aero) e potência, descontando arrasto e rolamento."""
        v = np.maximum(v, 1.0)  # evita divisão por zero na largada
        a_grip = self.a_accel_max * self.load_factor(v) * self._ellipse_factor(v, a_y)
        a_power = self.power / (self.mass * v)
        return np.maximum(np.minimum(a_grip, a_power) - self.drag_decel(v), 0.0)

    def brake_available(self, v: np.ndarray, a_y: np.ndarray) -> np.ndarray:
        """Desaceleração disponível em frenagem (o arrasto ajuda a frear)."""
        return self.a_brake_max * self.load_factor(v) * self._ellipse_factor(v, a_y) + self.drag_decel(v)
