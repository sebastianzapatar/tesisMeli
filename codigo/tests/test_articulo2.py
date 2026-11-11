"""Tests de las funciones agregadas para el artículo 2.

Cubren: eventos diarios centrados, indicadores simples, incertidumbre de
kappa, exponencial estirada, comparación de modelos anidados, bootstrap,
VIF, costo de cada punto de confiabilidad y sistema de mínimo costo.
Donde se puede, el valor esperado es analítico.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from intermitencia.config import Bess, Economia, Planta
from intermitencia.dimensionamiento import capacidad_para_lpsp, minimo_costo_para_lpsp
from intermitencia.economia import (
    HORAS_ANIO,
    costo_anual_bess_por_mwh,
    costo_por_punto_lpsp,
    crf,
    lpsp_optima_por_voll,
)
from intermitencia.eventos import (
    eventos_diarios_centrados,
    indicadores_simples,
    indice_claridad_diario,
    metricas_intermitencia,
    racha_maxima,
)
from intermitencia.sustituto import (
    ajustar_kappa_estirada,
    bloques_por_correlacion,
    bootstrap_coeficientes,
    comparar_modelos,
    cv_por_bloques,
    error_estandar_kappa,
    ols,
    vif,
)

BESS = Bess(duracion_h=4.0, limitar_potencia=True, eff_carga=0.922, eff_descarga=0.922,
            soc_min_frac=0.10, soc_max_frac=1.0, soc_inicial_frac=0.5, autodescarga_frac_h=0.0)
ECO = Economia(tasa_descuento=0.115, vida_proyecto_anios=25, capex_pv_usd_kw=1560.0,
               capex_bess_energia_usd_kwh=241.0, capex_bess_potencia_usd_kw=372.0,
               opex_pv_usd_kw_anio=22.0, opex_bess_usd_kwh_anio=13.36, vida_bess_anios=15,
               ciclos_vida=5475, voll_usd_mwh=546.3, costo_vertimiento_usd_mwh=0.0)
PLANTA = Planta(potencia_mw=100.0, performance_ratio=0.8, modelo_legacy=False,
                modulo_potencia_w=550.0, modulo_ancho_m=2.279, modulo_alto_m=1.134)


def _ghi_markov(n_dias: int, persistencia: float, semilla: int = 0) -> pd.Series:
    """GHI horaria con días claros/nublados de una cadena de Markov simétrica."""
    rng = np.random.default_rng(semilla)
    estado = np.empty(n_dias, dtype=int)
    estado[0] = 0
    for j in range(1, n_dias):
        estado[j] = estado[j - 1] if rng.random() < persistencia else 1 - estado[j - 1]
    kt = np.where(estado == 0, 0.75, 0.35) * (1 + 0.03 * rng.standard_normal(n_dias))
    h = np.arange(24)
    perfil = np.clip(np.sin(np.pi * (h - 6) / 12), 0, None) * 1000.0
    ghi = (kt[:, None] * perfil[None, :]).ravel()
    idx = pd.date_range("2000-01-01", periods=n_dias * 24, freq="h")
    return pd.Series(ghi, index=idx)


# ---------------------------------------------------------------- eventos
def test_eventos_diarios_centrados_marca_dias_sobre_la_media():
    idx = pd.date_range("2000-01-01", periods=4 * 24, freq="h")
    deficit_diario = np.array([10.0, 30.0, 0.0, 40.0])        # media 20
    bal = np.zeros(4 * 24)
    for j, d in enumerate(deficit_diario):
        bal[j * 24] = -d                                       # todo el déficit en una hora
    x = eventos_diarios_centrados(pd.Series(bal, index=idx))
    np.testing.assert_allclose(x, -(deficit_diario - 20.0))
    assert list(x < 0) == [False, True, False, True]


def test_racha_maxima():
    assert racha_maxima(np.array([0, 1, 1, 0, 1, 1, 1, 0], bool)) == 3
    assert racha_maxima(np.zeros(5, bool)) == 0
    assert racha_maxima(np.ones(4, bool)) == 4


def test_indice_claridad_recupera_kt_relativo():
    ghi = _ghi_markov(3 * 365, 0.5, semilla=1)
    kt = indice_claridad_diario(ghi, percentil=100.0)
    # el cielo despejado es el día más claro de la ventana: kt <= 1 y los
    # días nublados quedan cerca de 0.35/0.75
    assert kt.max() <= 1.0 + 1e-12
    assert kt.median() < 1.0
    assert 0.35 / 0.75 * 0.85 < kt.min() < 0.35 / 0.75 * 1.1


def test_b_diaria_crece_con_la_persistencia_de_los_dias_nublados():
    """Aceptación de A1: con kt fijo, B diaria crece con la persistencia."""
    bs = []
    for phi in (0.5, 0.8, 0.95):
        ghi = _ghi_markov(30 * 365, phi, semilla=3)
        bal = ghi * 0.12 - 20.0
        m = metricas_intermitencia(eventos_diarios_centrados(bal), min_eventos=30)
        bs.append(m["B"])
    assert bs[0] < bs[1] < bs[2]


def test_indicadores_simples_ordenan_la_persistencia():
    a = indicadores_simples(_ghi_markov(20 * 365, 0.5, 2), _ghi_markov(20 * 365, 0.5, 2) * 0.12 - 20)
    b = indicadores_simples(_ghi_markov(20 * 365, 0.95, 2), _ghi_markov(20 * 365, 0.95, 2) * 0.12 - 20)
    assert b["ac1_kt"] > a["ac1_kt"] + 0.5
    assert b["racha_max_deficit_dias"] > a["racha_max_deficit_dias"]


# ---------------------------------------------------------------- kappa
def test_estirada_recupera_beta_y_exponencial_tiene_beta_1():
    e = np.linspace(0, 3000, 300)
    est = ajustar_kappa_estirada(e, 0.4 * np.exp(-(e / 400.0) ** 0.7))
    assert est.beta == pytest.approx(0.7, rel=1e-3)
    assert est.kappa_mwh == pytest.approx(400.0, rel=1e-3)
    assert est.delta_aic > 10
    exp_ = ajustar_kappa_estirada(e, 0.4 * np.exp(-e / 400.0))
    assert exp_.beta == pytest.approx(1.0, abs=1e-3)


def test_error_estandar_kappa_cero_sin_ruido_y_positivo_con_ruido():
    e = np.linspace(0, 2000, 100)
    assert error_estandar_kappa(e, 0.3 * np.exp(-e / 300)) == pytest.approx(0.0, abs=1e-6)
    rng = np.random.default_rng(0)
    y = 0.3 * np.exp(-e / 300 + 0.05 * rng.standard_normal(e.size))
    assert error_estandar_kappa(e, y) > 0


# ---------------------------------------------------------------- regresión
def test_ols_coincide_con_lstsq_y_loo_con_fuerza_bruta():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(30, 2))
    y = 1 + X @ [2.0, -1.0] + 0.3 * rng.normal(size=30)
    r = ols(X, y)
    Z = np.column_stack([np.ones(30), X])
    np.testing.assert_allclose(r["beta"], np.linalg.lstsq(Z, y, rcond=None)[0])
    pred = np.empty(30)
    for i in range(30):
        m = np.arange(30) != i
        b = np.linalg.lstsq(Z[m], y[m], rcond=None)[0]
        pred[i] = Z[i] @ b
    np.testing.assert_allclose(r["pred_loo"], pred)


def test_comparar_modelos_detecta_predictor_relevante_e_irrelevante():
    rng = np.random.default_rng(2)
    n = 60
    df = pd.DataFrame({"PSH": rng.normal(5, 0.4, n), "B": rng.normal(0, 0.1, n),
                       "M": rng.normal(0, 0.05, n)})
    df["kappa_mwh"] = np.exp(15 - 2 * df.PSH + 4 * df.B + 0.05 * rng.normal(size=n))
    t = comparar_modelos(df, {"PSH": ["PSH"], "PSH+B": ["PSH", "B"],
                              "PSH+B+M": ["PSH", "B", "M"]}).set_index("modelo")
    assert t.loc["PSH+B", "anidado_en"] == "PSH"
    assert t.loc["PSH+B", "p_F"] < 1e-6
    assert t.loc["PSH+B", "delta_r2_loo"] > 0.05
    assert t.loc["PSH+B+M", "anidado_en"] == "PSH+B"
    assert t.loc["PSH+B+M", "p_F"] > 0.01
    assert t.loc["PSH+B", "coef_B"] == pytest.approx(4.0, abs=0.3)


def test_bootstrap_ic_contiene_el_valor_verdadero_y_vif():
    rng = np.random.default_rng(3)
    n = 80
    df = pd.DataFrame({"PSH": rng.normal(5, 0.4, n), "B": rng.normal(0, 0.1, n)})
    df["kappa_mwh"] = np.exp(15 - 2 * df.PSH + 4 * df.B + 0.1 * rng.normal(size=n))
    bt = bootstrap_coeficientes(df, ["PSH", "B"], replicas=500, semilla=1).set_index("coeficiente")
    assert bt.loc["B", "ic_inf"] < 4.0 < bt.loc["B", "ic_sup"]
    assert bt.loc["B", "excluye_cero"]
    assert bt.loc["B", "efecto_1sd"] == pytest.approx(bt.loc["B", "estimado"] * df.B.std(), rel=1e-9)
    v = vif(df, ["PSH", "B"])
    assert (v < 1.2).all()


# ---------------------------------------------------------------- economía
def test_costo_anual_bess_por_mwh_a_mano():
    f = crf(0.115, 25)
    reemplazo = 1 + 1 / 1.115 ** 15
    esperado = reemplazo * (241e3 + 372e3 / 4) * f + 13.36e3
    assert costo_anual_bess_por_mwh(ECO, 4.0) == pytest.approx(esperado)


def test_costo_por_punto_coincide_con_diferencia_finita_de_la_ley():
    kappa, l0, lpsp = 300.0, 0.4, 0.02
    e = lambda l: kappa * np.log(l0 / l)
    mwh_pp = (e(lpsp - 0.00005) - e(lpsp + 0.00005)) / 0.01   # MWh por punto porcentual
    t = costo_por_punto_lpsp(kappa, lpsp, ECO, 4.0, 20.0)
    assert t["mwh_por_pp"].iloc[0] == pytest.approx(mwh_pp, rel=1e-5)
    c_e = costo_anual_bess_por_mwh(ECO, 4.0)
    assert t["usd_por_mwh_ens_evitada"].iloc[0] == pytest.approx(
        c_e * mwh_pp / (0.01 * 20 * HORAS_ANIO), rel=1e-5)


def test_lpsp_optima_iguala_costo_marginal_y_voll():
    lo = lpsp_optima_por_voll(300.0, ECO, 4.0, 20.0)
    t = costo_por_punto_lpsp(300.0, lo, ECO, 4.0, 20.0)
    assert t["usd_por_mwh_ens_evitada"].iloc[0] == pytest.approx(ECO.voll_usd_mwh)


def test_minimo_costo_cumple_la_meta_y_es_el_minimo_de_la_tabla():
    ghi = _ghi_markov(3 * 365, 0.8, semilla=4).to_numpy()
    mejor, tabla = minimo_costo_para_lpsp(ghi, 0.05, [120, 160, 200, 240], PLANTA, BESS, ECO, 20.0)
    ok = tabla[tabla.alcanzable]
    assert mejor["costo_anual_musd"] == pytest.approx(ok.costo_anual_musd.min())
    assert (ok.lpsp <= 0.05 + 1e-3).all()
    # más planta nunca exige más batería para la misma meta
    assert np.all(np.diff(ok.e_bess_mwh.to_numpy()) <= 1e-6 * ok.e_bess_mwh.max() + 1e-6)
    bal = ghi * mejor["p_pv_mw"] * 0.8 / 1000 - 20
    assert capacidad_para_lpsp(bal, 0.05, BESS, 20.0) == pytest.approx(mejor["e_bess_mwh"])


def test_anidado_desempata_por_orden_de_la_lista():
    rng = np.random.default_rng(5)
    n = 40
    df = pd.DataFrame({"PSH": rng.normal(5, 0.4, n), "B": rng.normal(0, 0.1, n),
                       "M": rng.normal(0, 0.05, n)})
    df["kappa_mwh"] = np.exp(10 - df.PSH + 0.1 * rng.normal(size=n))
    t = comparar_modelos(df, {"PSH": ["PSH"], "PSH+B": ["PSH", "B"], "PSH+M": ["PSH", "M"],
                              "PSH+B+M": ["PSH", "B", "M"]}).set_index("modelo")
    assert t.loc["PSH+B+M", "anidado_en"] == "PSH+B"


def test_bloques_por_correlacion_separa_dos_climas():
    rng = np.random.default_rng(6)
    idx = pd.date_range("2000-01-01", periods=3 * 365, freq="D")
    a, b = rng.normal(size=idx.size), rng.normal(size=idx.size)
    diarias = pd.DataFrame({f"a{i}": a + 0.3 * rng.normal(size=idx.size) for i in range(4)}
                           | {f"b{i}": b + 0.3 * rng.normal(size=idx.size) for i in range(3)},
                           index=idx)
    g = bloques_por_correlacion(diarias, 2)
    assert g[[f"a{i}" for i in range(4)]].nunique() == 1
    assert g[[f"b{i}" for i in range(3)]].nunique() == 1
    assert g["a0"] != g["b0"]


def test_cv_por_bloques_y_bootstrap_por_conglomerados():
    rng = np.random.default_rng(7)
    n = 60
    df = pd.DataFrame({"PSH": rng.normal(5, 0.4, n), "B": rng.normal(0, 0.1, n)})
    df["kappa_mwh"] = np.exp(15 - 2 * df.PSH + 4 * df.B + 0.1 * rng.normal(size=n))
    grupos = pd.Series(np.arange(n) % 6, index=df.index)
    r = cv_por_bloques(df, ["PSH", "B"], grupos)
    assert r["n_bloques"] == 6
    assert r["r2_bloques"] > 0.8
    assert r["coef_min"]["B"] > 2 and r["coef_max"]["B"] < 6
    bt = bootstrap_coeficientes(df, ["PSH", "B"], replicas=300, semilla=1,
                                grupos=grupos).set_index("coeficiente")
    assert bt.loc["B", "ic_inf"] < 4.0 < bt.loc["B", "ic_sup"]


def test_despacho_directo_iguala_la_cota_de_prevision_perfecta():
    from intermitencia.almacenamiento import ens_minima_prevision_perfecta, simular_soc
    ghi = _ghi_markov(60, 0.85, semilla=8).to_numpy()
    bal = ghi * 0.12 - 20.0
    for e in (150.0, 400.0, 800.0):
        greedy = simular_soc(bal, e, BESS).ens_total
        assert ens_minima_prevision_perfecta(bal, e, BESS) == pytest.approx(greedy, rel=1e-6, abs=1e-6)
