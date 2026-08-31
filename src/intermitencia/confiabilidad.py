"""Métricas de confiabilidad.

El problema de nombres del código anterior
------------------------------------------
``Modelo.py`` calculaba::

    deficit = balance[balance < 0]
    LPSP = ENS / (-deficit.sum())
    confiabilidad = 1 - LPSP

El denominador estándar de la LPSP (*loss of power supply probability*,
en su versión energética) es la **demanda total**, no la energía de
déficit. Lo que ese código calcula es la fracción del déficit que la
batería NO alcanzó a cubrir --- una métrica de cobertura perfectamente
válida, pero con otro nombre y otra escala: su denominador es mucho
menor, así que arroja números mucho peores que la LPSP estándar y no es
comparable con la literatura.

Aquí se reportan **las dos, con nombres distintos**:

* ``lpsp``            = ENS / demanda total          (estándar, comparable)
* ``cobertura_deficit`` = 1 - ENS / energía de déficit  (lo que antes se
  llamaba, incorrectamente, "confiabilidad")
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import numpy as np
import pandas as pd

from .almacenamiento import ResultadoSOC, simular_soc
from .config import Bess

__all__ = ["Metricas", "evaluar", "evaluar_por_periodo", "curva_capacidad"]


@dataclass(frozen=True)
class Metricas:
    """Resumen de desempeño de una configuración sobre un registro."""

    capacidad_mwh: float
    potencia_mw: float

    energia_demandada_mwh: float
    energia_generada_mwh: float
    energia_deficit_mwh: float

    ens_mwh: float
    vertimiento_mwh: float
    descarga_mwh: float

    lpsp: float                 # ENS / demanda total   <- definición estándar
    cobertura_deficit: float    # 1 - ENS / energía de déficit
    lolh_frac: float            # fracción de horas con energía no servida

    ciclos_por_anio: float
    frac_tiempo_lleno: float
    frac_vertida: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluar(
    balance: np.ndarray,
    capacidad_mwh: float,
    bess: Bess,
    demanda_mw: float,
    potencia_mw: float | None = None,
    resultado: ResultadoSOC | None = None,
) -> Metricas:
    """Calcula todas las métricas de confiabilidad de una configuración.

    Si ya se corrió la simulación se puede pasar en ``resultado`` para no
    repetirla.
    """
    balance = np.asarray(balance, dtype=np.float64)
    n = balance.shape[0]
    if n == 0:
        raise ValueError("El balance está vacío.")

    if resultado is None:
        resultado = simular_soc(balance, capacidad_mwh, bess, potencia_mw)

    energia_demandada = demanda_mw * n
    energia_generada = float((balance + demanda_mw).sum())
    energia_deficit = float(-balance[balance < 0].sum())

    ens = resultado.ens_total

    lpsp = ens / energia_demandada if energia_demandada > 0 else 0.0
    cobertura = 1.0 - ens / energia_deficit if energia_deficit > 0 else 1.0

    return Metricas(
        capacidad_mwh=float(capacidad_mwh),
        potencia_mw=resultado.potencia_mw,
        energia_demandada_mwh=float(energia_demandada),
        energia_generada_mwh=energia_generada,
        energia_deficit_mwh=energia_deficit,
        ens_mwh=ens,
        vertimiento_mwh=resultado.vertimiento_total,
        descarga_mwh=resultado.descarga_total,
        lpsp=float(np.clip(lpsp, 0.0, 1.0)),
        cobertura_deficit=float(np.clip(cobertura, 0.0, 1.0)),
        lolh_frac=float(np.mean(resultado.ens > 1e-9)),
        ciclos_por_anio=resultado.ciclos_por_anio(n),
        frac_tiempo_lleno=resultado.fraccion_tiempo_lleno(),
        frac_vertida=(
            resultado.vertimiento_total / energia_generada
            if energia_generada > 0
            else 0.0
        ),
    )


def evaluar_por_periodo(
    balance: pd.Series,
    capacidad_mwh: float,
    bess: Bess,
    demanda_mw: float,
    periodo: str = "YE",
    potencia_mw: float | None = None,
) -> pd.DataFrame:
    """Evalúa la confiabilidad periodo a periodo (por defecto, año a año).

    El código anterior reportaba **un solo número sobre 27 años**, lo que
    esconde por completo la variabilidad interanual. Como la tesis madre
    trata precisamente sobre ENSO y variabilidad climática, la
    confiabilidad tiene que reportarse como distribución: mediana, P10,
    P90 y peor año.

    La simulación se corre **una sola vez sobre todo el registro** y luego
    se particiona, de modo que el SOC no se reinicia artificialmente en
    cada frontera de año (reiniciarlo sesgaría el resultado).
    """
    if not isinstance(balance.index, pd.DatetimeIndex):
        raise TypeError("Se requiere un índice temporal para agrupar por periodo.")

    valores = balance.to_numpy(dtype=np.float64)
    res = simular_soc(valores, capacidad_mwh, bess, potencia_mw)

    detalle = pd.DataFrame(
        {
            "balance": valores,
            "ens": res.ens,
            "vertimiento": res.vertimiento,
            "descarga": res.descarga,
        },
        index=balance.index,
    )

    filas = []
    for etiqueta, grupo in detalle.resample(periodo):
        if grupo.empty:
            continue
        n = len(grupo)
        dem = demanda_mw * n
        defi = float(-grupo["balance"][grupo["balance"] < 0].sum())
        ens = float(grupo["ens"].sum())
        filas.append(
            {
                "periodo": etiqueta,
                "n_horas": n,
                "energia_demandada_mwh": dem,
                "energia_deficit_mwh": defi,
                "ens_mwh": ens,
                "vertimiento_mwh": float(grupo["vertimiento"].sum()),
                "descarga_mwh": float(grupo["descarga"].sum()),
                "lpsp": ens / dem if dem > 0 else 0.0,
                "cobertura_deficit": 1.0 - ens / defi if defi > 0 else 1.0,
                "lolh_frac": float((grupo["ens"] > 1e-9).mean()),
            }
        )

    return pd.DataFrame(filas).set_index("periodo")


def curva_capacidad(
    balance: np.ndarray,
    capacidades_mwh: np.ndarray,
    bess: Bess,
    demanda_mw: float,
) -> pd.DataFrame:
    """Curva capacidad -> confiabilidad para una lista de capacidades."""
    filas = []
    for cap in np.asarray(capacidades_mwh, dtype=float):
        m = evaluar(balance, float(cap), bess, demanda_mw)
        filas.append(m.to_dict())
    return pd.DataFrame(filas)


def resumen_interanual(df_periodos: pd.DataFrame) -> dict[str, float]:
    """P50/P90/peor año a partir de la salida de ``evaluar_por_periodo``."""
    lpsp = df_periodos["lpsp"]
    return {
        "lpsp_p50": float(lpsp.median()),
        "lpsp_p90": float(lpsp.quantile(0.90)),
        "lpsp_peor": float(lpsp.max()),
        "lpsp_mejor": float(lpsp.min()),
        "lpsp_media": float(lpsp.mean()),
        "razon_peor_vs_mediana": (
            float(lpsp.max() / lpsp.median()) if lpsp.median() > 0 else float("inf")
        ),
    }
