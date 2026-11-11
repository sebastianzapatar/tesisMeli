"""Pruebas de intermitencia.sinteticas."""

import numpy as np
import pandas as pd
import pytest

from intermitencia.eventos import burstiness, memory
from intermitencia.sinteticas import (b_teorica, barajar_dias, m_teorica,
                                      secuencia_renovacion)


def _serie(dias: int = 365 * 3, semilla: int = 0) -> pd.Series:
    rng = np.random.default_rng(semilla)
    idx = pd.date_range("2001-01-01", periods=dias * 24, freq="h")
    perfil = np.clip(np.sin(np.pi * (np.arange(24) - 6) / 12), 0, None)
    kt = rng.uniform(0.2, 0.9, dias)
    return pd.Series((kt[:, None] * perfil * 1000).ravel(), index=idx)


@pytest.mark.parametrize("ambito", ["todo", "mes"])
def test_barajado_conserva_los_dias(ambito):
    s = _serie()
    b = barajar_dias(s, np.random.default_rng(1), ambito)
    assert b.index.equals(s.index)
    original = np.sort(s.to_numpy().reshape(-1, 24), axis=0)
    barajada = np.sort(b.to_numpy().reshape(-1, 24), axis=0)
    np.testing.assert_allclose(original, barajada)          # mismos días
    assert np.isclose(b.sum(), s.sum())                       # misma PSH
    assert not np.allclose(b.to_numpy(), s.to_numpy())        # otro orden


def test_barajado_por_mes_conserva_energia_mensual():
    s = _serie()
    b = barajar_dias(s, np.random.default_rng(2), "mes")
    pd.testing.assert_series_equal(s.resample("MS").sum(), b.resample("MS").sum())


def test_barajado_exige_dias_completos():
    s = _serie().iloc[:-3]
    with pytest.raises(ValueError):
        barajar_dias(s, np.random.default_rng(0))


@pytest.mark.parametrize("cv,rho", [(0.6, 0.0), (1.0, 0.3), (2.0, 0.6)])
def test_secuencia_recupera_b_y_m(cv, rho):
    t = secuencia_renovacion(200_000, cv, rho, np.random.default_rng(3))
    assert burstiness(t, corregir_tamano_finito=False) == pytest.approx(b_teorica(cv), abs=0.02)
    assert memory(t) == pytest.approx(m_teorica(cv, rho), abs=0.03)
