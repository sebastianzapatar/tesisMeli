"""Tests de detección de eventos y de las métricas B y M."""

from __future__ import annotations

import numpy as np
import pytest

from intermitencia.eventos import (
    burstiness,
    burstiness_legacy_cruces,
    detectar_eventos,
    memory,
    metricas_intermitencia,
    agregar_memory_fisher,
)


# ---------------------------------------------------------------------
# DETECCIÓN DE EVENTOS
# ---------------------------------------------------------------------

def test_detecta_corridas_contiguas():
    # dos corridas de déficit: pasos 1-2 y 5-7
    balance = np.array([1.0, -2.0, -3.0, 1.0, 1.0, -1.0, -1.0, -2.0, 5.0])
    ev = detectar_eventos(balance, base="deficit")
    assert ev.n_eventos == 2
    assert list(ev.inicios) == [1, 5]
    assert list(ev.duraciones) == [2, 3]
    assert ev.severidades == pytest.approx([5.0, 4.0])


def test_evento_al_inicio_y_al_final():
    balance = np.array([-1.0, 2.0, -3.0])
    ev = detectar_eventos(balance)
    assert ev.n_eventos == 2
    assert list(ev.inicios) == [0, 2]
    assert list(ev.duraciones) == [1, 1]


def test_sin_eventos():
    ev = detectar_eventos(np.ones(10))
    assert ev.n_eventos == 0
    assert ev.taus.size == 0


def test_taus_son_diferencias_de_inicios():
    balance = np.zeros(20) + 1.0
    balance[[2, 7, 15]] = -1.0
    ev = detectar_eventos(balance)
    assert list(ev.taus) == [5.0, 8.0]


# ---------------------------------------------------------------------
# BURSTINESS
# ---------------------------------------------------------------------

def test_burstiness_serie_perfectamente_regular():
    """Intervalos idénticos -> sigma = 0 -> B = -1."""
    taus = np.full(50, 7.0)
    assert burstiness(taus, corregir_tamano_finito=False) == pytest.approx(-1.0)


def test_burstiness_clasica_es_funcion_del_cv():
    """B = (r-1)/(r+1) con r = sigma/mu."""
    rng = np.random.default_rng(0)
    taus = rng.gamma(2.0, 3.0, size=500)
    r = taus.std(ddof=0) / taus.mean()
    esperado = (r - 1) / (r + 1)
    assert burstiness(taus, corregir_tamano_finito=False) == pytest.approx(esperado)


def test_poisson_da_burstiness_cercana_a_cero():
    """Un proceso de Poisson tiene intervalos exponenciales -> CV = 1 -> B = 0."""
    rng = np.random.default_rng(1)
    taus = rng.exponential(10.0, size=20000)
    assert abs(burstiness(taus, corregir_tamano_finito=False)) < 0.02


def test_correccion_kim_jo_reduce_el_sesgo_por_n():
    """El punto de la corrección: B no debe depender del número de eventos.

    Con la B clásica, muestras cortas de un mismo proceso dan valores
    sistemáticamente distintos que muestras largas. La corregida no.
    """
    rng = np.random.default_rng(2)
    largo = rng.exponential(10.0, size=100_000)

    b_clasica_larga = burstiness(largo, corregir_tamano_finito=False)
    b_corr_larga = burstiness(largo, corregir_tamano_finito=True)

    cortas_clasica, cortas_corr = [], []
    for s in range(200):
        r = np.random.default_rng(1000 + s)
        m = r.exponential(10.0, size=30)
        cortas_clasica.append(burstiness(m, corregir_tamano_finito=False))
        cortas_corr.append(burstiness(m, corregir_tamano_finito=True))

    sesgo_clasico = abs(np.mean(cortas_clasica) - b_clasica_larga)
    sesgo_corregido = abs(np.mean(cortas_corr) - b_corr_larga)
    assert sesgo_corregido < sesgo_clasico


def test_burstiness_en_rango_valido():
    rng = np.random.default_rng(3)
    for _ in range(50):
        taus = rng.lognormal(0.0, rng.uniform(0.1, 2.0), size=rng.integers(10, 500))
        b = burstiness(taus)
        assert -1.0 <= b <= 1.0


# ---------------------------------------------------------------------
# MEMORY
# ---------------------------------------------------------------------

def test_memory_independientes_es_cero():
    rng = np.random.default_rng(4)
    taus = rng.exponential(5.0, size=50_000)
    assert abs(memory(taus)) < 0.02


def test_memory_detecta_correlacion_positiva():
    """Serie con persistencia -> M > 0."""
    rng = np.random.default_rng(5)
    n = 20_000
    taus = np.empty(n)
    taus[0] = 5.0
    for i in range(1, n):
        taus[i] = 0.7 * taus[i - 1] + rng.exponential(1.5)
    assert memory(taus) > 0.4


def test_memory_detecta_alternancia():
    """Corto-largo-corto-largo -> M fuertemente negativa."""
    taus = np.tile([1.0, 20.0], 500)
    assert memory(taus) < -0.9


def test_memory_usa_medias_separadas():
    """Verifica la fórmula de Goh & Barabási explícitamente."""
    taus = np.array([1.0, 5.0, 2.0, 8.0, 3.0, 9.0, 4.0])
    a, b = taus[:-1], taus[1:]
    esperado = np.mean((a - a.mean()) * (b - b.mean())) / (a.std(ddof=0) * b.std(ddof=0))
    assert memory(taus) == pytest.approx(esperado)


def test_memory_constante_es_nan():
    assert np.isnan(memory(np.full(20, 3.0)))


# ---------------------------------------------------------------------
# AGREGACIÓN DE FISHER
# ---------------------------------------------------------------------

def test_fisher_difiere_de_la_media_aritmetica():
    """Con correlaciones altas la diferencia es material."""
    valores = np.array([0.90, 0.95, 0.85])
    n = np.array([100.0, 100.0, 100.0])
    fisher = agregar_memory_fisher(valores, n)
    assert fisher > valores.mean()  # Fisher pondera más las colas


def test_fisher_pondera_por_tamano():
    valores = np.array([0.1, 0.9])
    casi_todo_en_el_primero = agregar_memory_fisher(valores, np.array([10_000.0, 5.0]))
    assert casi_todo_en_el_primero == pytest.approx(0.1, abs=0.02)


# ---------------------------------------------------------------------
# MÉTODO ANTIGUO: demostración del defecto
# ---------------------------------------------------------------------

def test_metodo_legacy_produce_taus_cero():
    """Demuestra el defecto central del ByM.py original.

    Con umbrales en el percentil 25 de una serie siempre positiva, muchos
    pasos cruzan más de un umbral, produciendo tau = 0 --- intervalos
    entre eventos de duración nula, que no tienen sentido físico e
    inflan artificialmente la burstiness.
    """
    rng = np.random.default_rng(6)
    excedente = rng.gamma(3.0, 15.0, size=2000)  # siempre positivo
    r = burstiness_legacy_cruces(excedente, percentil=25.0)
    assert r["frac_tau_cero"] > 0.3, (
        f"Se esperaban muchos tau=0, hubo {r['frac_tau_cero']:.1%}"
    )


def test_metodo_legacy_da_B_muy_distinta_de_la_correcta():
    """El método viejo y el nuevo no miden lo mismo, y se puede cuantificar."""
    rng = np.random.default_rng(7)
    excedente = rng.gamma(3.0, 15.0, size=3000)
    legacy = burstiness_legacy_cruces(excedente)
    # Sobre la misma serie, tratada como proceso puntual de "días buenos"
    balance = excedente - np.percentile(excedente, 60)
    correcto = metricas_intermitencia(balance, min_eventos=10)
    assert not np.isclose(legacy["B_legacy"], correcto["B"], atol=0.1)


# ---------------------------------------------------------------------
# MÉTRICAS COMPLETAS
# ---------------------------------------------------------------------

def test_metricas_respeta_min_eventos():
    balance = np.array([1.0, -1.0, 1.0, -1.0, 1.0])
    m = metricas_intermitencia(balance, min_eventos=30)
    assert m["n_eventos"] == 2
    assert np.isnan(m["B"]) and np.isnan(m["M"])


def test_severidades_son_cuantiles_de_los_eventos():
    rng = np.random.default_rng(8)
    balance = rng.normal(0.0, 10.0, size=20_000)
    m = metricas_intermitencia(balance, min_eventos=10)
    assert m["severidad_p50_mwh"] <= m["severidad_p90_mwh"]
    assert m["severidad_p90_mwh"] <= m["severidad_p99_mwh"]
    assert m["severidad_p99_mwh"] <= m["severidad_max_mwh"]
