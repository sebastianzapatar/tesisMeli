"""Búsqueda de tamaños óptimos de planta y batería.

Mejora algorítmica respecto al código anterior
----------------------------------------------
El código original barría una grilla de 26 capacidades (5 % a 30 % en
pasos de 1 %) y elegía el "codo" con un heurístico. Dos problemas:

1. El resultado dependía del extremo de la grilla, no de la física.
2. Barrer una grilla para encontrar la capacidad que alcanza un objetivo
   es innecesario: **la LPSP es monótona decreciente en la capacidad**
   (verificado en ``tests/test_almacenamiento.py``), así que se puede
   resolver ``LPSP(E) = objetivo`` por bisección con ~15 evaluaciones
   exactas en vez de 26 aproximadas.

Y como la simulación ahora está compilada, el barrido 2-D sobre
``(P_pv, E_bess)`` --- que es lo que realmente pide el problema de
"cuadrar los tamaños de planta y baterías" --- cuesta menos que el
barrido 1-D anterior.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import brentq, minimize

from .almacenamiento import simular_soc
from .config import Bess, Economia, Planta
from .confiabilidad import evaluar
from .economia import HORAS_ANIO, costear

__all__ = [
    "capacidad_para_lpsp",
    "frente_pareto",
    "OptimoEconomico",
    "optimizar_sistema",
]


def _lpsp(balance: np.ndarray, cap: float, bess: Bess, demanda_mw: float) -> float:
    if cap <= 0:
        res = simular_soc(balance, 0.0, bess)
        return float(res.ens_total / (demanda_mw * balance.size))
    return evaluar(balance, cap, bess, demanda_mw).lpsp


def capacidad_para_lpsp(
    balance: np.ndarray,
    objetivo_lpsp: float,
    bess: Bess,
    demanda_mw: float,
    cap_max_mwh: float | None = None,
    tol: float = 1e-4,
) -> float:
    """Capacidad mínima [MWh] que alcanza un objetivo de LPSP, por bisección.

    Devuelve ``inf`` si el objetivo no es alcanzable ni con una batería
    enorme (ocurre cuando la generación anual no alcanza la demanda: sin
    energía suficiente, ningún almacenamiento sirve).
    """
    balance = np.asarray(balance, dtype=np.float64)
    if not 0 < objetivo_lpsp < 1:
        raise ValueError(f"objetivo_lpsp={objetivo_lpsp} debe estar en (0, 1).")

    if _lpsp(balance, 0.0, bess, demanda_mw) <= objetivo_lpsp:
        return 0.0

    # Busca una cota superior duplicando hasta cumplir el objetivo.
    if cap_max_mwh is None:
        cap = max(demanda_mw * 24.0, 1.0)
        for _ in range(30):
            if _lpsp(balance, cap, bess, demanda_mw) <= objetivo_lpsp:
                break
            cap *= 2.0
        else:
            return float("inf")
        cap_max_mwh = cap
    elif _lpsp(balance, cap_max_mwh, bess, demanda_mw) > objetivo_lpsp:
        return float("inf")

    f = lambda c: _lpsp(balance, c, bess, demanda_mw) - objetivo_lpsp
    return float(brentq(f, 0.0, cap_max_mwh, xtol=tol * cap_max_mwh, rtol=1e-8))


def frente_pareto(
    balance: np.ndarray,
    objetivos_lpsp: list[float],
    bess: Bess,
    demanda_mw: float,
    planta: Planta,
    eco: Economia,
) -> pd.DataFrame:
    """Frente costo-confiabilidad: para cada objetivo de LPSP, su costo.

    Esta es la tabla que sostiene la figura clave de la tesis: cuánto
    cuesta cada punto porcentual de confiabilidad adicional.
    """
    balance = np.asarray(balance, dtype=np.float64)
    n_anios = balance.size / HORAS_ANIO
    demanda_anual = demanda_mw * HORAS_ANIO

    filas = []
    for objetivo in sorted(objetivos_lpsp, reverse=True):
        cap = capacidad_para_lpsp(balance, objetivo, bess, demanda_mw)
        if not np.isfinite(cap):
            filas.append({"objetivo_lpsp": objetivo, "alcanzable": False})
            continue

        m = evaluar(balance, cap, bess, demanda_mw)
        res = simular_soc(balance, cap, bess)
        c = costear(
            p_pv_mw=planta.potencia_mw,
            e_bess_mwh=cap,
            p_bess_mw=cap / bess.duracion_h,
            ens_mwh_anio=m.ens_mwh / n_anios,
            descarga_mwh_anio=m.descarga_mwh / n_anios,
            vertimiento_mwh_anio=m.vertimiento_mwh / n_anios,
            demanda_mwh_anio=demanda_anual,
            eco=eco,
        )
        filas.append(
            {
                "objetivo_lpsp": objetivo,
                "alcanzable": True,
                "capacidad_mwh": cap,
                "potencia_bess_mw": cap / bess.duracion_h,
                "lpsp": m.lpsp,
                "cobertura_deficit": m.cobertura_deficit,
                "lcoe_usd_mwh": c.lcoe_usd_mwh,
                "lcos_usd_mwh": c.lcos_usd_mwh,
                "capex_total_musd": c.capex_total_usd / 1e6,
                "ciclos_por_anio": m.ciclos_por_anio,
                "frac_vertida": m.frac_vertida,
            }
        )
    return pd.DataFrame(filas)


@dataclass(frozen=True)
class OptimoEconomico:
    p_pv_mw: float
    e_bess_mwh: float
    p_bess_mw: float
    lcoe_usd_mwh: float
    lpsp: float
    cobertura_deficit: float
    capex_total_musd: float
    ciclos_por_anio: float
    frac_vertida: float
    n_evaluaciones: int
    convergio: bool


def _lcoe_de(
    ghi: np.ndarray,
    p_pv_mw: float,
    e_bess_mwh: float,
    planta: Planta,
    bess: Bess,
    eco: Economia,
    demanda_mw: float,
) -> tuple[float, object]:
    """LCOE de una configuración, reescalando la generación al tamaño de planta."""
    from .pv import factor_ghi_a_mw

    # La generación escala linealmente con la potencia instalada.
    factor = factor_ghi_a_mw(planta) * (p_pv_mw / planta.potencia_mw)
    balance = ghi * factor - demanda_mw

    n_anios = balance.size / HORAS_ANIO
    m = evaluar(balance, e_bess_mwh, bess, demanda_mw)
    c = costear(
        p_pv_mw=p_pv_mw,
        e_bess_mwh=e_bess_mwh,
        p_bess_mw=e_bess_mwh / bess.duracion_h,
        ens_mwh_anio=m.ens_mwh / n_anios,
        descarga_mwh_anio=m.descarga_mwh / n_anios,
        vertimiento_mwh_anio=m.vertimiento_mwh / n_anios,
        demanda_mwh_anio=demanda_mw * HORAS_ANIO,
        eco=eco,
    )
    return c.lcoe_usd_mwh, m


def optimizar_sistema(
    ghi: np.ndarray,
    planta: Planta,
    bess: Bess,
    eco: Economia,
    demanda_mw: float,
    rango_pv_mw: tuple[float, float] = (40.0, 300.0),
    rango_bess_mwh: tuple[float, float] = (0.0, 1200.0),
    n_grilla: int = 12,
) -> tuple[OptimoEconomico, pd.DataFrame]:
    """Minimiza el LCOE sobre ``(P_pv, E_bess)``.

    Estrategia en dos etapas: una grilla gruesa para localizar la cuenca
    y un refinamiento Nelder-Mead. La grilla completa se devuelve además
    del óptimo, porque es exactamente el insumo del mapa de calor
    LCOE(P_pv, E_bess) con isolíneas de LPSP.
    """
    ghi = np.ascontiguousarray(np.asarray(ghi, dtype=np.float64))
    contador = {"n": 0}

    def objetivo(x: np.ndarray) -> float:
        p, e = float(x[0]), float(x[1])
        if not (rango_pv_mw[0] <= p <= rango_pv_mw[1]):
            return 1e12
        if not (rango_bess_mwh[0] <= e <= rango_bess_mwh[1]):
            return 1e12
        contador["n"] += 1
        lcoe, _ = _lcoe_de(ghi, p, e, planta, bess, eco, demanda_mw)
        return lcoe if np.isfinite(lcoe) else 1e12

    # --- etapa 1: grilla -------------------------------------------------
    pvs = np.linspace(*rango_pv_mw, n_grilla)
    bats = np.linspace(*rango_bess_mwh, n_grilla)

    filas = []
    for p in pvs:
        for e in bats:
            lcoe, m = _lcoe_de(ghi, p, e, planta, bess, eco, demanda_mw)
            contador["n"] += 1
            filas.append(
                {
                    "p_pv_mw": p,
                    "e_bess_mwh": e,
                    "lcoe_usd_mwh": lcoe,
                    "lpsp": m.lpsp,
                    "cobertura_deficit": m.cobertura_deficit,
                    "frac_vertida": m.frac_vertida,
                }
            )
    grilla = pd.DataFrame(filas)

    mejor = grilla.loc[grilla["lcoe_usd_mwh"].idxmin()]
    x0 = np.array([mejor["p_pv_mw"], mejor["e_bess_mwh"]])

    # --- etapa 2: refinamiento ------------------------------------------
    paso = np.array(
        [(rango_pv_mw[1] - rango_pv_mw[0]) / n_grilla,
         (rango_bess_mwh[1] - rango_bess_mwh[0]) / n_grilla]
    )
    simplex = np.vstack([x0, x0 + [paso[0], 0.0], x0 + [0.0, paso[1]]])
    r = minimize(
        objetivo, x0, method="Nelder-Mead",
        options={"initial_simplex": simplex, "xatol": 0.5, "fatol": 1e-4,
                 "maxiter": 400},
    )

    p_opt = float(np.clip(r.x[0], *rango_pv_mw))
    e_opt = float(np.clip(r.x[1], *rango_bess_mwh))
    lcoe_opt, m_opt = _lcoe_de(ghi, p_opt, e_opt, planta, bess, eco, demanda_mw)

    from .pv import factor_ghi_a_mw
    factor = factor_ghi_a_mw(planta) * (p_opt / planta.potencia_mw)
    n_anios = ghi.size / HORAS_ANIO
    c = costear(
        p_pv_mw=p_opt, e_bess_mwh=e_opt, p_bess_mw=e_opt / bess.duracion_h,
        ens_mwh_anio=m_opt.ens_mwh / n_anios,
        descarga_mwh_anio=m_opt.descarga_mwh / n_anios,
        vertimiento_mwh_anio=m_opt.vertimiento_mwh / n_anios,
        demanda_mwh_anio=demanda_mw * HORAS_ANIO, eco=eco,
    )

    optimo = OptimoEconomico(
        p_pv_mw=p_opt,
        e_bess_mwh=e_opt,
        p_bess_mw=e_opt / bess.duracion_h,
        lcoe_usd_mwh=lcoe_opt,
        lpsp=m_opt.lpsp,
        cobertura_deficit=m_opt.cobertura_deficit,
        capex_total_musd=c.capex_total_usd / 1e6,
        ciclos_por_anio=m_opt.ciclos_por_anio,
        frac_vertida=m_opt.frac_vertida,
        n_evaluaciones=contador["n"],
        convergio=bool(r.success),
    )
    return optimo, grilla
