"""Pruebas del modelo de operación regulatorio (CREG 101 113 de 2026)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from intermitencia.almacenamiento import simular_soc
from intermitencia.config import Bess
from intermitencia.operacion_creg import (
    ParametrosBESS,
    ParametrosRegulatorios,
    _limites_fisicos,
    alinear_precios,
    correr_escenario,
    optimizar_escenario,
    simular_escenario,
)


def _datos(dias: int = 60, semilla: int = 3):
    rng = np.random.default_rng(semilla)
    idx = pd.date_range("2015-01-01", periods=24 * dias, freq="h")
    h = idx.hour.to_numpy()
    gen = 60.0 * np.clip(np.sin((h - 6) / 12 * np.pi), 0, None)
    nub = np.repeat(rng.uniform(0.3, 1.1, dias), 24)      # días nublados
    gen = np.clip(gen * nub, 0, None)
    # precio: barato al mediodía (solar), caro en la noche
    precio = 80 + 60 * (h >= 18) * (h <= 22) - 30 * ((h >= 10) & (h <= 15))
    return idx, gen, 20.0, precio.astype(float)


def test_m0_r1_reproduce_motor_del_pipeline():
    """M0 + R1 sin reserva de RPF debe ser idéntico a almacenamiento.simular_soc."""
    idx, gen, dem, _ = _datos()
    cfg = Bess(duracion_h=4.0, limitar_potencia=True, eff_carga=0.95, eff_descarga=0.95,
               soc_min_frac=0.1, soc_max_frac=1.0, soc_inicial_frac=0.5,
               autodescarga_frac_h=0.0)
    ref = simular_soc(gen - dem, 200.0, cfg)
    b = ParametrosBESS.desde_config(cfg, e_mwh=200.0)
    r = simular_escenario(gen, dem, b, ParametrosRegulatorios("M0"), "R1", indice=idx)
    assert r.series["faltante_mwh"].sum() == pytest.approx(ref.ens_total, rel=1e-9)
    assert r.series["vertimiento_mwh"].sum() == pytest.approx(ref.vertimiento_total, rel=1e-9)
    np.testing.assert_allclose(r.series["soc_mwh"].to_numpy(), ref.soc, rtol=1e-9)


@pytest.mark.parametrize("mod", ["M0", "M1", "M2", "M3"])
@pytest.mark.parametrize("pol", ["R1", "R2", "R3", "R4", "R5", "P1"])
def test_conservacion_de_energia(mod, pol):
    idx, gen, dem, precio = _datos()
    b = ParametrosBESS(e_mwh=150.0, p_mw=40.0)
    reg = ParametrosRegulatorios(mod, p_max_declarada_mw=50.0, limite_importacion_mw=10.0,
                                 ventana_recarga_red=(0, 5))
    r = simular_escenario(gen, dem, b, reg, pol, precios_usd_mwh=precio, indice=idx)
    s = r.series
    entra = (s["carga_pv_mwh"] + s["carga_red_mwh"]).sum() * b.eff_carga
    sale = s["descarga_mwh"].sum() / b.eff_descarga
    _, piso, techo, _ = _limites_fisicos(b, reg)
    soc_ini = float(np.clip(b.soc_inicial_frac * b.e_mwh, piso, techo))
    assert s["soc_mwh"].iloc[-1] - soc_ini == pytest.approx(entra - sale, abs=1e-6)
    assert (s["soc_mwh"] >= piso - 1e-9).all() and (s["soc_mwh"] <= techo + 1e-9).all()
    assert (s["faltante_mwh"] >= -1e-9).all()


def test_m1_no_carga_desde_la_red_y_respeta_potencia_declarada():
    idx, gen, dem, precio = _datos()
    b = ParametrosBESS(e_mwh=150.0, p_mw=40.0)
    reg = ParametrosRegulatorios("M1", p_max_declarada_mw=35.0)
    for pol in ["R1", "P1"]:
        s = simular_escenario(gen, dem, b, reg, pol, precios_usd_mwh=precio, indice=idx).series
        assert s["carga_red_mwh"].sum() == 0.0                       # art. 66
        assert (s["carga_pv_mwh"] <= s["generacion_mw"] + 1e-9).all()
        x = s["generacion_mw"] - s["carga_pv_mwh"] + s["descarga_mwh"] - s["vertimiento_mwh"]
        assert (x <= 35.0 + 1e-9).all()                              # art. 61 parág.


def test_reserva_rpf_reduce_potencia_util():
    idx, gen, dem, _ = _datos()
    b = ParametrosBESS(e_mwh=150.0, p_mw=40.0)
    r = simular_escenario(gen, dem, b, ParametrosRegulatorios("M1"), "R1", indice=idx)
    assert r.parametros["reserva_rpf_mw"] == pytest.approx(1.2)        # 3 % de 40 MW
    assert r.series["descarga_mwh"].max() <= 40.0 - 1.2 + 1e-9


def test_m2_carga_solo_desde_la_red():
    idx, gen, dem, precio = _datos()
    b = ParametrosBESS(e_mwh=100.0, p_mw=25.0)
    s = simular_escenario(gen, dem, b, ParametrosRegulatorios("M2"), "P1",
                          precios_usd_mwh=precio, indice=idx).series
    assert s["carga_pv_mwh"].sum() == 0.0
    assert s["carga_red_mwh"].sum() > 0.0


def test_m3_disponibilidad_y_horas_indisponibles():
    idx, gen, dem, _ = _datos()
    b = ParametrosBESS(e_mwh=100.0, p_mw=25.0)
    sin_red = simular_escenario(gen, dem, b, ParametrosRegulatorios("M3", e_funcion_mwh=50.0),
                                "R1", indice=idx)
    con_red = simular_escenario(gen, dem, b, ParametrosRegulatorios(
        "M3", e_funcion_mwh=50.0, limite_importacion_mw=30.0, ventana_recarga_red=(0, 5)),
        "R1", indice=idx)
    assert 0.0 <= sin_red.indicadores["disponibilidad_media"] <= 1.0
    # recargar desde la red en la madrugada debe reducir la indisponibilidad
    assert con_red.indicadores["horas_indisp_max_12m"] <= sin_red.indicadores["horas_indisp_max_12m"]


def test_lp_m2_supera_heuristica_en_margen():
    idx, gen, dem, precio = _datos(dias=20)
    b = ParametrosBESS(e_mwh=100.0, p_mw=25.0)
    reg = ParametrosRegulatorios("M2")
    heur = simular_escenario(gen, dem, b, reg, "P1", precios_usd_mwh=precio, indice=idx)
    lp = optimizar_escenario(gen, dem, b, reg, precios_usd_mwh=precio, indice=idx)
    assert lp.indicadores["margen_arbitraje_usd_anio"] >= \
        heur.indicadores["margen_arbitraje_usd_anio"] - 1e-6


def test_lp_m0_no_peor_que_r1_en_ens():
    idx, gen, dem, _ = _datos(dias=20)
    b = ParametrosBESS(e_mwh=150.0, p_mw=40.0)
    reg = ParametrosRegulatorios("M0")
    r1 = simular_escenario(gen, dem, b, reg, "R1", indice=idx)
    lp = correr_escenario(gen, dem, b, reg, "LP", indice=idx, horizonte_h=48)
    assert lp.indicadores["lpsp"] <= r1.indicadores["lpsp"] + 1e-6


def test_alinear_precios_perfil_anual():
    p_idx = pd.date_range("2023-01-01", periods=24 * 365, freq="h")
    precios = pd.Series(100 + p_idx.hour.to_numpy(), index=p_idx, dtype=float)
    g_idx = pd.date_range("1999-03-01", periods=24 * 10, freq="h")
    al = alinear_precios(g_idx, precios)
    np.testing.assert_allclose(al, 100 + g_idx.hour.to_numpy())
