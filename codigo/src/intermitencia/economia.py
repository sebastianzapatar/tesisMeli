"""Modelo de costos: CRF, LCOE, LCOS y costo marginal de la confiabilidad.

Por qué esto es lo que faltaba
------------------------------
El código anterior no tenía ningún costo. Sin costo, el problema de
dimensionamiento es **degenerado**: la confiabilidad crece de forma
monótona con la capacidad, así que "maximizar confiabilidad" siempre
responde "más grande". Por eso hubo que inventar el heurístico de
``conf_max * 0.99``, que depende por completo del extremo superior de la
grilla de barrido (``PORCENTAJE_MAX = 0.30``) y no de la física.

Con costo el óptimo se vuelve **interior** y único, y la regla de parada
deja de ser arbitraria:

.. math::

    \\frac{\\partial\\,\\mathrm{CAPEX}_{anual}}{\\partial E_{bess}}
    = \\mathrm{VoLL} \\cdot
      \\left|\\frac{\\partial\\,\\mathrm{ENS}}{\\partial E_{bess}}\\right|

es decir: se agrega batería mientras el costo marginal de la energía no
suministrada que se evita sea menor que el valor de esa energía.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import Economia

__all__ = [
    "crf",
    "CostoSistema",
    "costear",
    "costo_marginal_ens_evitada",
    "costo_anual_bess_por_mwh",
    "costo_por_punto_lpsp",
    "lpsp_optima_por_voll",
]

HORAS_ANIO = 8760.0


def crf(tasa: float, anios: int) -> float:
    """Factor de recuperación de capital.

    .. math:: \\mathrm{CRF} = \\frac{r(1+r)^N}{(1+r)^N - 1}
    """
    if anios <= 0:
        raise ValueError("anios debe ser > 0.")
    if tasa == 0:
        return 1.0 / anios
    f = (1.0 + tasa) ** anios
    return tasa * f / (f - 1.0)


def _factor_reemplazos(vida_componente: int, vida_proyecto: int, tasa: float) -> float:
    """Multiplicador de CAPEX que incluye los reemplazos descontados.

    Si el BESS dura 12 años y el proyecto 25, hay un reemplazo en el año
    12 (y el residual del segundo no se acredita, criterio conservador).
    Devuelve ``1 + sum(1/(1+r)^{k*vida})`` para los reemplazos que caen
    dentro del horizonte.
    """
    if vida_componente <= 0:
        raise ValueError("vida_componente debe ser > 0.")
    factor = 1.0
    k = 1
    while k * vida_componente < vida_proyecto:
        factor += 1.0 / (1.0 + tasa) ** (k * vida_componente)
        k += 1
    return factor


@dataclass(frozen=True)
class CostoSistema:
    """Desglose anualizado de costos de una configuración."""

    p_pv_mw: float
    e_bess_mwh: float
    p_bess_mw: float

    capex_pv_usd: float
    capex_bess_usd: float
    capex_total_usd: float

    anual_capex_usd: float
    anual_opex_usd: float
    anual_ens_usd: float
    anual_vertimiento_usd: float
    anual_total_usd: float

    energia_servida_mwh_anio: float
    ens_mwh_anio: float
    descarga_mwh_anio: float

    lcoe_usd_mwh: float
    lcos_usd_mwh: float

    def to_dict(self) -> dict[str, float]:
        return {k: float(v) for k, v in self.__dict__.items()}


def costear(
    p_pv_mw: float,
    e_bess_mwh: float,
    p_bess_mw: float,
    ens_mwh_anio: float,
    descarga_mwh_anio: float,
    vertimiento_mwh_anio: float,
    demanda_mwh_anio: float,
    eco: Economia,
) -> CostoSistema:
    """Calcula el costo anualizado y el LCOE de una configuración.

    Todas las energías son **por año**; usa
    ``total_del_registro / numero_de_anios`` para pasarlas.
    """
    factor = crf(eco.tasa_descuento, eco.vida_proyecto_anios)

    capex_pv = eco.capex_pv_usd_kw * p_pv_mw * 1000.0

    reemplazo = _factor_reemplazos(
        eco.vida_bess_anios, eco.vida_proyecto_anios, eco.tasa_descuento
    )
    capex_bess = reemplazo * (
        eco.capex_bess_energia_usd_kwh * e_bess_mwh * 1000.0
        + eco.capex_bess_potencia_usd_kw * p_bess_mw * 1000.0
    )

    capex_total = capex_pv + capex_bess
    anual_capex = capex_total * factor

    anual_opex = (
        eco.opex_pv_usd_kw_anio * p_pv_mw * 1000.0
        + eco.opex_bess_usd_kwh_anio * e_bess_mwh * 1000.0
    )

    anual_ens = eco.voll_usd_mwh * ens_mwh_anio
    anual_vert = eco.costo_vertimiento_usd_mwh * vertimiento_mwh_anio
    anual_total = anual_capex + anual_opex + anual_ens + anual_vert

    servida = demanda_mwh_anio - ens_mwh_anio
    lcoe = anual_total / servida if servida > 0 else float("inf")

    # LCOS: costo por MWh que efectivamente pasa por la batería.
    anual_bess = capex_bess * factor + eco.opex_bess_usd_kwh_anio * e_bess_mwh * 1000.0
    lcos = anual_bess / descarga_mwh_anio if descarga_mwh_anio > 0 else float("inf")

    return CostoSistema(
        p_pv_mw=p_pv_mw,
        e_bess_mwh=e_bess_mwh,
        p_bess_mw=p_bess_mw,
        capex_pv_usd=capex_pv,
        capex_bess_usd=capex_bess,
        capex_total_usd=capex_total,
        anual_capex_usd=anual_capex,
        anual_opex_usd=anual_opex,
        anual_ens_usd=anual_ens,
        anual_vertimiento_usd=anual_vert,
        anual_total_usd=anual_total,
        energia_servida_mwh_anio=servida,
        ens_mwh_anio=ens_mwh_anio,
        descarga_mwh_anio=descarga_mwh_anio,
        lcoe_usd_mwh=lcoe,
        lcos_usd_mwh=lcos,
    )


def costo_marginal_ens_evitada(
    capacidades_mwh: np.ndarray,
    ens_mwh_anio: np.ndarray,
    eco: Economia,
    duracion_h: float,
) -> pd.DataFrame:
    """Costo marginal de la ENS evitada [USD/MWh] a lo largo de la curva.

    Se agrega batería mientras el MCAE esté **por debajo** del VoLL. El
    cruce ``MCAE = VoLL`` es el óptimo económico, y sustituye al
    heurístico ``conf_max * 0.99``.
    """
    caps = np.asarray(capacidades_mwh, dtype=float)
    ens = np.asarray(ens_mwh_anio, dtype=float)
    if caps.shape != ens.shape:
        raise ValueError("capacidades y ENS deben tener la misma forma.")

    orden = np.argsort(caps)
    caps, ens = caps[orden], ens[orden]

    factor = crf(eco.tasa_descuento, eco.vida_proyecto_anios)
    reemplazo = _factor_reemplazos(
        eco.vida_bess_anios, eco.vida_proyecto_anios, eco.tasa_descuento
    )
    # Costo anualizado por MWh de capacidad, incluyendo el PCS asociado.
    costo_por_mwh = (
        reemplazo
        * (
            eco.capex_bess_energia_usd_kwh * 1000.0
            + eco.capex_bess_potencia_usd_kw * 1000.0 / duracion_h
        )
        * factor
        + eco.opex_bess_usd_kwh_anio * 1000.0
    )

    d_cap = np.diff(caps)
    d_ens = -np.diff(ens)  # positivo = ENS evitada

    with np.errstate(divide="ignore", invalid="ignore"):
        mcae = np.where(d_ens > 1e-9, costo_por_mwh * d_cap / d_ens, np.inf)

    return pd.DataFrame(
        {
            "capacidad_mwh": caps[1:],
            "delta_capacidad_mwh": d_cap,
            "ens_evitada_mwh_anio": d_ens,
            "mcae_usd_mwh": mcae,
            "supera_voll": mcae > eco.voll_usd_mwh,
        }
    )


def capacidad_optima_por_voll(mcae: pd.DataFrame, eco: Economia) -> float:
    """Primera capacidad donde el costo marginal supera el VoLL."""
    supera = mcae[mcae["supera_voll"]]
    if supera.empty:
        return float(mcae["capacidad_mwh"].max())
    return float(supera.iloc[0]["capacidad_mwh"])


# =====================================================================
# COSTO DE CADA PUNTO DE CONFIABILIDAD (artículo 2)
# =====================================================================

def costo_anual_bess_por_mwh(eco: Economia, duracion_h: float) -> float:
    """Costo anualizado [USD/año] de 1 MWh de BESS, con su conversión de potencia.

    Incluye el reemplazo dentro de la vida del proyecto, el CRF y el O&M
    fijo: es la pendiente ``c_E`` del costo del almacenamiento en E.
    """
    factor = crf(eco.tasa_descuento, eco.vida_proyecto_anios)
    reemplazo = _factor_reemplazos(eco.vida_bess_anios, eco.vida_proyecto_anios,
                                   eco.tasa_descuento)
    return float(
        reemplazo * (eco.capex_bess_energia_usd_kwh * 1000.0
                     + eco.capex_bess_potencia_usd_kw * 1000.0 / duracion_h) * factor
        + eco.opex_bess_usd_kwh_anio * 1000.0
    )


def costo_por_punto_lpsp(kappa_mwh, lpsp, eco: Economia, duracion_h: float,
                         demanda_mw: float) -> pd.DataFrame:
    """Costo marginal de la confiabilidad implícito en la ley exponencial.

    Con ``E* = kappa ln(L0/LPSP)``, ``dE*/dLPSP = -kappa/LPSP``. Entonces:

    * almacenamiento adicional por punto porcentual de LPSP:
      ``0.01 * kappa / LPSP``  [MWh/pp]
    * costo anual por punto porcentual: ``c_E * 0.01 * kappa / LPSP``
    * costo por MWh de ENS evitada: ``c_E * kappa / (LPSP * D_anual)``,
      que se compara directamente con el VoLL.

    ``L0`` no aparece: el costo del siguiente punto depende solo de kappa
    y del punto en el que se está. Por eso kappa es el parámetro económico.
    """
    k = np.asarray(kappa_mwh, float)
    l = np.asarray(lpsp, float)
    c_e = costo_anual_bess_por_mwh(eco, duracion_h)
    d_anual = demanda_mw * HORAS_ANIO
    mwh_pp = 0.01 * k / l
    return pd.DataFrame({
        "kappa_mwh": np.broadcast_to(k, np.broadcast(k, l).shape).ravel(),
        "lpsp": np.broadcast_to(l, np.broadcast(k, l).shape).ravel(),
        "mwh_por_pp": np.ravel(mwh_pp),
        "usd_anio_por_pp": np.ravel(c_e * mwh_pp),
        "usd_por_mwh_ens_evitada": np.ravel(c_e * k / (l * d_anual)),
    })


def lpsp_optima_por_voll(kappa_mwh, eco: Economia, duracion_h: float,
                         demanda_mw: float):
    """LPSP donde el costo marginal del almacenamiento iguala el VoLL.

    Igualando ``c_E kappa / (LPSP D_anual) = VoLL`` se obtiene
    ``LPSP_opt = c_E kappa / (VoLL D_anual)``. Por debajo de esa LPSP,
    cada MWh de ENS evitado con batería cuesta más que su valor.
    """
    c_e = costo_anual_bess_por_mwh(eco, duracion_h)
    return np.asarray(kappa_mwh, float) * c_e / (eco.voll_usd_mwh * demanda_mw * HORAS_ANIO)
