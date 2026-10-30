"""Modelo de generación fotovoltaica y balance con la demanda.

Sobre el factor de conversión GHI -> potencia
--------------------------------------------
El código anterior usaba::

    generacion_mw = GHI * area_total_m2 * 0.17 / 1e6

con ``area_total_m2 = 469 888``. Ese factor vale 0.0798796 MW por cada
W/m2, o sea **79.88 MW de pico a 1000 W/m2**, no los 100 MW nominales.

La causa es una inconsistencia entre dos supuestos: un módulo de 550 W
con 2.279 x 1.134 m tiene una eficiencia real de **21.3 %**, no de 17 %.
Al multiplicar el área física de los módulos por 0.17 se subestima la
potencia pico en un 20 %.

Ese 20 % de subestimación es numéricamente casi idéntico a aplicar un
performance ratio de 0.799 sobre los 100 MW nominales, así que los
resultados antiguos no son "incorrectos" en magnitud --- simplemente
tenían un supuesto de pérdidas escondido dentro de una eficiencia mal
puesta. Aquí se hace explícito::

    generacion_mw = potencia_mw * (GHI / 1000) * performance_ratio

Con ``performance_ratio = 0.80`` los resultados coinciden con los
anteriores dentro del 0.15 %, pero ahora el supuesto es declarable y
citable en la tesis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Config, Planta

__all__ = [
    "factor_ghi_a_mw",
    "generacion_mw",
    "balance_mw",
    "energia_diaria",
    "factor_planta",
]

#: Irradiancia en condiciones estándar de prueba [W/m2]
GHI_STC = 1000.0


def factor_ghi_a_mw(planta: Planta) -> float:
    """MW de salida por cada W/m2 de GHI."""
    if planta.modelo_legacy:
        return planta.factor_legacy_mw_por_wm2
    return planta.potencia_mw * planta.performance_ratio / GHI_STC


def generacion_mw(ghi: pd.DataFrame | pd.Series, planta: Planta):
    """Convierte GHI [W/m2] a generación AC [MW]."""
    return ghi * factor_ghi_a_mw(planta)


def balance_mw(ghi: pd.DataFrame | pd.Series, planta: Planta, demanda_mw: float):
    """Balance horario = generación - demanda [MW].

    Positivo = excedente disponible para cargar la batería.
    Negativo = déficit que la batería debe cubrir.
    """
    return generacion_mw(ghi, planta) - demanda_mw


def energia_diaria(
    psh: pd.Series | float, planta: Planta, base: str = "generada"
) -> pd.Series | float:
    """Energía diaria de la planta [MWh/día], usada como base de los porcentajes.

    Parameters
    ----------
    base
        ``"generada"``  -> ``P_nom * PSH * PR``: la energía que la planta
        realmente produce. Es la base físicamente correcta.

        ``"nominal"``   -> ``P_nom * PSH``: la convención del código
        anterior. Como la planta antigua producía un 20 % menos que su
        nominal, los porcentajes calculados sobre esta base son un ~20 %
        menores que sobre la energía realmente generada. Se conserva
        para poder comparar con los resultados previos.
    """
    if base == "generada":
        # PSH [h/día] = suma diaria de GHI / 1000, así que la energía diaria
        # es exactamente PSH * 1000 * (MW por W/m2).
        return psh * GHI_STC * factor_ghi_a_mw(planta)
    if base == "nominal":
        return psh * planta.potencia_mw
    raise ValueError(f"base='{base}' no es válida (usa 'generada' o 'nominal').")


def factor_planta(gen_mw: pd.Series, planta: Planta) -> float:
    """Factor de planta = energía generada / (P_nom * horas)."""
    horas = len(gen_mw)
    if horas == 0:
        return float("nan")
    return float(gen_mw.sum() / (planta.potencia_mw * horas))


def describir_modelo(planta: Planta) -> str:
    f = factor_ghi_a_mw(planta)
    return "\n".join(
        [
            f"Modelo FV {'LEGACY' if planta.modelo_legacy else 'explícito'}",
            f"  factor GHI->MW    : {f:.7f} MW por W/m2",
            f"  pico a 1000 W/m2  : {f * GHI_STC:.2f} MW "
            f"(nominal {planta.potencia_mw:.0f} MW)",
            f"  PR implícito      : {f * GHI_STC / planta.potencia_mw:.4f}",
            f"  eficiencia módulo : {planta.eficiencia_modulo_real*100:.2f} % real "
            f"vs 17.00 % usado en el código antiguo",
            f"  área total        : {planta.area_total_m2:,.0f} m2",
        ]
    )
