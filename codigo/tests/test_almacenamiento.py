"""Tests del simulador de SOC contra casos con solución analítica."""

from __future__ import annotations

import numpy as np
import pytest

from intermitencia.almacenamiento import (
    energia_requerida_pico_secuente,
    simular_soc,
)
from intermitencia.config import Bess


def hacer_bess(**kwargs) -> Bess:
    base = dict(
        duracion_h=4.0,
        limitar_potencia=True,
        eff_carga=1.0,
        eff_descarga=1.0,
        soc_min_frac=0.0,
        soc_max_frac=1.0,
        soc_inicial_frac=0.0,
        autodescarga_frac_h=0.0,
    )
    base.update(kwargs)
    return Bess(**base)


def test_bateria_vacia_no_cubre_nada():
    """Sin capacidad, toda la energía de déficit es ENS."""
    balance = np.array([-5.0, -5.0, -5.0])
    r = simular_soc(balance, 0.0, hacer_bess())
    assert r.ens_total == pytest.approx(15.0)
    assert r.descarga_total == pytest.approx(0.0)


def test_ciclo_ideal_sin_perdidas():
    """Carga 10 MWh y los devuelve completos si no hay pérdidas."""
    balance = np.array([10.0, -10.0])
    r = simular_soc(balance, 10.0, hacer_bess(limitar_potencia=False))
    assert r.carga_total == pytest.approx(10.0)
    assert r.descarga_total == pytest.approx(10.0)
    assert r.ens_total == pytest.approx(0.0)
    assert r.vertimiento_total == pytest.approx(0.0)


def test_eficiencia_roundtrip_se_aplica():
    """Con round-trip 0.81 solo vuelve el 81 % de lo cargado."""
    b = hacer_bess(eff_carga=0.9, eff_descarga=0.9, limitar_potencia=False)
    balance = np.array([10.0, -10.0])
    r = simular_soc(balance, 100.0, b)
    # Entra 10 MWh AC -> 9 MWh al SOC -> salen 9*0.9 = 8.1 MWh AC
    assert r.descarga_total == pytest.approx(8.1)
    assert r.ens_total == pytest.approx(10.0 - 8.1)


def test_limite_de_potencia_recorta_la_carga():
    """Este es el bug que tenía el código anterior: la potencia no se usaba."""
    # 100 MWh de capacidad, 4 h de duración -> 25 MW de límite
    b = hacer_bess(duracion_h=4.0, limitar_potencia=True)
    balance = np.array([80.0])  # excedente de 80 MW en una hora

    r_con = simular_soc(balance, 100.0, b)
    assert r_con.carga_total == pytest.approx(25.0)
    assert r_con.vertimiento_total == pytest.approx(55.0)

    r_sin = simular_soc(balance, 100.0, hacer_bess(limitar_potencia=False))
    assert r_sin.carga_total == pytest.approx(80.0)
    assert r_sin.vertimiento_total == pytest.approx(0.0)

    # El simulador antiguo daba el resultado optimista
    assert r_con.carga_total < r_sin.carga_total


def test_vertimiento_se_contabiliza():
    """El excedente que no cabe se registra en vez de perderse en silencio."""
    balance = np.array([50.0])
    r = simular_soc(balance, 10.0, hacer_bess(limitar_potencia=False))
    assert r.carga_total == pytest.approx(10.0)
    assert r.vertimiento_total == pytest.approx(40.0)
    # Conservación de energía
    assert r.carga_total + r.vertimiento_total == pytest.approx(50.0)


def test_soc_minimo_reserva_energia():
    """Con DoD del 80 % solo se puede usar el 80 % de la capacidad."""
    b = hacer_bess(soc_min_frac=0.2, soc_inicial_frac=1.0, limitar_potencia=False)
    balance = np.array([-100.0])
    r = simular_soc(balance, 100.0, b)
    assert r.descarga_total == pytest.approx(80.0)
    assert r.ens_total == pytest.approx(20.0)


def test_soc_respeta_los_limites_siempre():
    rng = np.random.default_rng(0)
    balance = rng.normal(0.0, 20.0, size=5000)
    b = hacer_bess(soc_min_frac=0.1, soc_max_frac=0.95, eff_carga=0.95,
                   eff_descarga=0.95, soc_inicial_frac=0.5)
    cap = 200.0
    r = simular_soc(balance, cap, b)
    assert r.soc.min() >= 0.1 * cap - 1e-9
    assert r.soc.max() <= 0.95 * cap + 1e-9


def test_conservacion_de_energia():
    """Excedente = carga + vertimiento;  déficit = descarga + ENS."""
    rng = np.random.default_rng(1)
    balance = rng.normal(0.0, 15.0, size=3000)
    b = hacer_bess(eff_carga=0.92, eff_descarga=0.92, soc_min_frac=0.05,
                   soc_inicial_frac=0.5)
    r = simular_soc(balance, 150.0, b)

    excedente = balance[balance >= 0].sum()
    deficit = -balance[balance < 0].sum()

    assert r.carga_total + r.vertimiento_total == pytest.approx(excedente, rel=1e-9)
    assert r.descarga_total + r.ens_total == pytest.approx(deficit, rel=1e-9)


def test_monotonia_capacidad_reduce_ens():
    """Más capacidad nunca puede aumentar la ENS: la curva es monótona.

    Esta propiedad es la que habilita usar bisección en vez de barrer una
    grilla para encontrar la capacidad que alcanza un objetivo de LPSP.
    """
    rng = np.random.default_rng(2)
    balance = rng.normal(-1.0, 18.0, size=8000)
    b = hacer_bess(eff_carga=0.95, eff_descarga=0.95, soc_inicial_frac=0.5)
    caps = [0.0, 25.0, 50.0, 100.0, 200.0, 400.0, 800.0]
    ens = [simular_soc(balance, c, b).ens_total for c in caps]
    assert all(ens[i] >= ens[i + 1] - 1e-6 for i in range(len(ens) - 1)), ens


def test_pico_secuente_caso_conocido():
    """Rippl: la capacidad para ENS=0 es el máximo drawdown acumulado."""
    # Déficit de 3, luego 2, luego superávit de 4 -> pico = 5
    balance = np.array([-3.0, -2.0, 4.0, -1.0])
    assert energia_requerida_pico_secuente(balance) == pytest.approx(5.0)


def test_pico_secuente_es_cota_inferior():
    """Con esa capacidad y sin pérdidas ni límite de potencia, ENS = 0."""
    rng = np.random.default_rng(3)
    balance = rng.normal(2.0, 20.0, size=4000)
    e_req = energia_requerida_pico_secuente(balance)
    b = hacer_bess(soc_inicial_frac=1.0, limitar_potencia=False)
    r = simular_soc(balance, e_req, b)
    assert r.ens_total == pytest.approx(0.0, abs=1e-6)
