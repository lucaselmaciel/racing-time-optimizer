import numpy as np
import pytest

from engine import build_track


@pytest.fixture
def circle_track():
    """Pista circular de raio 100 m, largura 5 m para cada lado."""
    theta = np.linspace(0.0, 2.0 * np.pi, 200, endpoint=False)
    radius = 100.0
    x = radius * np.cos(theta)
    y = radius * np.sin(theta)
    w = np.full_like(x, 5.0)
    return build_track(x, y, w, w, n_samples=500)
