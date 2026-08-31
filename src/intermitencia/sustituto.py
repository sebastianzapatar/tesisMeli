"""Modelo sustituto: la ley exponencial de almacenamiento y κ(B, M).

La idea
-------
En vez de regresar la capacidad contra (B, M) con una logística de cuatro
parámetros sobre un objetivo artificial --- que es lo que hacía
``Modelo.py`` --- se propone una forma funcional con estructura física.

**Hipótesis.** La curva de confiabilidad es aproximadamente exponencial:

.. math::

    \\mathrm{LPSP}(E) \\approx L_0 \\, e^{-E/\\kappa}
    \\quad\\Longleftrightarrow\\quad
    E^*(\\mathrm{LPSP}^*) = \\kappa \\ln\\frac{L_0}{\\mathrm{LPSP}^*}

No es arbitraria: para un proceso de renovación de eventos de déficit, el
almacenamiento necesario para atravesar rachas se comporta como el máximo
de una caminata aleatoria, cuya cola es exponencial (cota de
Cramér--Lundberg). La lectura es limpia:

> el almacenamiento requerido crece **logarítmicamente** con la meta de
> confiabilidad, con una pendiente κ fijada por la intermitencia.

Si la hipótesis se sostiene, todo el comportamiento de una serie se
resume en **un solo parámetro físico** κ [MWh], en lugar de cuatro
coeficientes sobre un blanco sin significado. El modelo sustituto es
entonces:

.. math::

    \\ln \\kappa = \\beta_0 + \\beta_1 B + \\beta_2 M
                  + \\beta_3 \\mathrm{PSH} + \\beta_4 \\mathrm{FC}

que se ajusta donde sí se puede simular y se aplica a sitios nuevos donde
solo se conocen B, M y PSH.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

__all__ = [
    "AjusteKappa",
    "ajustar_kappa",
    "ResultadoSustituto",
    "ajustar_sustituto",
    "validar_loo",
]


@dataclass(frozen=True)
class AjusteKappa:
    """Ajuste de ``LPSP(E) = L0 * exp(-E/kappa)`` para una serie."""

    kappa_mwh: float
    l0: float
    r2: float
    n_puntos: int
    e_min: float
    e_max: float

    def capacidad_para(self, objetivo_lpsp: float) -> float:
        """Capacidad predicha para un objetivo de LPSP, por la ley exponencial."""
        if objetivo_lpsp <= 0 or self.l0 <= 0:
            return float("inf")
        return float(self.kappa_mwh * np.log(self.l0 / objetivo_lpsp))


def ajustar_kappa(
    capacidades_mwh: np.ndarray,
    lpsp: np.ndarray,
    lpsp_min: float = 1e-3,
    lpsp_max: float = 0.30,
) -> AjusteKappa:
    """Ajusta la ley exponencial por regresión lineal de ``ln(LPSP)`` en E.

    Se usa solo el tramo con ``lpsp_min <= LPSP <= lpsp_max``: fuera de
    él la curva se aplana (saturación por falta de energía en un extremo,
    ruido numérico en el otro) y la ley exponencial no aplica.
    """
    e = np.asarray(capacidades_mwh, dtype=float)
    y = np.asarray(lpsp, dtype=float)

    ok = np.isfinite(e) & np.isfinite(y) & (y >= lpsp_min) & (y <= lpsp_max) & (y > 0)
    nan = AjusteKappa(np.nan, np.nan, np.nan, int(ok.sum()), np.nan, np.nan)
    if ok.sum() < 4:
        return nan

    e_ok, y_ok = e[ok], y[ok]
    ln_y = np.log(y_ok)

    # ln(LPSP) = ln(L0) - E/kappa  ->  pendiente = -1/kappa
    pendiente, intercepto = np.polyfit(e_ok, ln_y, 1)
    if pendiente >= 0:
        return nan  # la LPSP no decrece: la ley no aplica

    pred = intercepto + pendiente * e_ok
    ss_res = float(np.sum((ln_y - pred) ** 2))
    ss_tot = float(np.sum((ln_y - ln_y.mean()) ** 2))

    return AjusteKappa(
        kappa_mwh=float(-1.0 / pendiente),
        l0=float(np.exp(intercepto)),
        r2=float(1.0 - ss_res / ss_tot) if ss_tot > 0 else np.nan,
        n_puntos=int(ok.sum()),
        e_min=float(e_ok.min()),
        e_max=float(e_ok.max()),
    )


@dataclass
class ResultadoSustituto:
    """Regresión de ``ln(kappa)`` contra los predictores de intermitencia."""

    modelo: LinearRegression
    predictores: list[str]
    coeficientes: pd.Series
    r2_insample: float
    r2_loo: float
    rmse_loo: float
    mae_loo: float
    rmse_loo_baseline_media: float
    predicciones_loo: np.ndarray
    y: np.ndarray

    @property
    def mejora_sobre_baseline(self) -> float:
        """Reducción relativa de RMSE frente a predecir la media."""
        if self.rmse_loo_baseline_media <= 0:
            return np.nan
        return 1.0 - self.rmse_loo / self.rmse_loo_baseline_media

    def predecir_kappa(self, X: pd.DataFrame) -> np.ndarray:
        return np.exp(self.modelo.predict(X[self.predictores].to_numpy(float)))

    def resumen(self) -> str:
        lineas = [
            "ln(kappa) = "
            + " + ".join(
                [f"{self.coeficientes['intercepto']:+.4f}"]
                + [f"{self.coeficientes[p]:+.4f}·{p}" for p in self.predictores]
            ),
            "",
            f"  R2 in-sample            : {self.r2_insample:.4f}",
            f"  R2 LOO                  : {self.r2_loo:.4f}",
            f"  RMSE LOO                : {self.rmse_loo:.4f}  (en ln kappa)",
            f"  MAE  LOO                : {self.mae_loo:.4f}",
            f"  RMSE LOO baseline media : {self.rmse_loo_baseline_media:.4f}",
            f"  Mejora sobre baseline   : {self.mejora_sobre_baseline:+.1%}",
        ]
        if self.mejora_sobre_baseline <= 0:
            lineas.append(
                "\n  >>> El modelo NO le gana a predecir la media. Los\n"
                "      predictores no aportan; no reportes esto como modelo."
            )
        return "\n".join(lineas)


def validar_loo(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Predicciones leave-one-out del modelo lineal y del baseline de la media.

    El código anterior comparaba cuatro modelos por LOO-CV **sin baseline**,
    de modo que siempre "ganaba" alguno aunque ninguno sirviera. Aquí el
    baseline es explícito.
    """
    n = len(y)
    pred = np.empty(n)
    base = np.empty(n)
    for i in range(n):
        m = np.ones(n, dtype=bool)
        m[i] = False
        pred[i] = LinearRegression().fit(X[m], y[m]).predict(X[i : i + 1])[0]
        base[i] = y[m].mean()
    return pred, base


def ajustar_sustituto(
    df: pd.DataFrame, predictores: list[str], objetivo: str = "kappa_mwh"
) -> ResultadoSustituto:
    """Ajusta ``ln(kappa) ~ predictores`` con validación LOO y baseline."""
    faltan = [c for c in predictores + [objetivo] if c not in df.columns]
    if faltan:
        raise KeyError(f"Faltan columnas en el DataFrame: {faltan}")

    d = df[predictores + [objetivo]].replace([np.inf, -np.inf], np.nan).dropna()
    d = d[d[objetivo] > 0]
    if len(d) < len(predictores) + 3:
        raise ValueError(
            f"Solo quedan {len(d)} observaciones válidas para "
            f"{len(predictores)} predictores. Insuficiente."
        )

    X = d[predictores].to_numpy(float)
    y = np.log(d[objetivo].to_numpy(float))

    modelo = LinearRegression().fit(X, y)
    pred_loo, base_loo = validar_loo(X, y)

    coefs = pd.Series(
        {"intercepto": modelo.intercept_,
         **dict(zip(predictores, modelo.coef_))}
    )

    return ResultadoSustituto(
        modelo=modelo,
        predictores=predictores,
        coeficientes=coefs,
        r2_insample=float(modelo.score(X, y)),
        r2_loo=float(r2_score(y, pred_loo)),
        rmse_loo=float(np.sqrt(mean_squared_error(y, pred_loo))),
        mae_loo=float(mean_absolute_error(y, pred_loo)),
        rmse_loo_baseline_media=float(np.sqrt(mean_squared_error(y, base_loo))),
        predicciones_loo=pred_loo,
        y=y,
    )
