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
from scipy import optimize, stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

__all__ = [
    "AjusteKappa",
    "ajustar_kappa",
    "ResultadoSustituto",
    "ajustar_sustituto",
    "validar_loo",
    "error_estandar_kappa",
    "AjusteEstirado",
    "ajustar_kappa_estirada",
    "ols",
    "comparar_modelos",
    "bootstrap_coeficientes",
    "vif",
    "bloques_por_correlacion",
    "cv_por_bloques",
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


# =====================================================================
# INCERTIDUMBRE DE KAPPA Y EXPONENCIAL ESTIRADA (tarea A6)
# =====================================================================

def error_estandar_kappa(capacidades_mwh: np.ndarray, lpsp: np.ndarray,
                         lpsp_min: float = 1e-3, lpsp_max: float = 0.30) -> float:
    """Error estándar de kappa por propagación del error de la pendiente.

    Con ``ln LPSP = a + b E`` y ``kappa = -1/b``: ``se(kappa) = se(b)/b^2``.
    Es un error de ajuste (los puntos de la curva no son independientes),
    así que sirve para comparar sitios, no como intervalo de confianza.
    """
    e = np.asarray(capacidades_mwh, float)
    y = np.asarray(lpsp, float)
    ok = np.isfinite(e) & np.isfinite(y) & (y >= lpsp_min) & (y <= lpsp_max) & (y > 0)
    if ok.sum() < 4:
        return float("nan")
    coef, cov = np.polyfit(e[ok], np.log(y[ok]), 1, cov=True)
    b = coef[0]
    if b >= 0:
        return float("nan")
    return float(np.sqrt(cov[0, 0]) / b ** 2)


@dataclass(frozen=True)
class AjusteEstirado:
    """Ajuste de ``LPSP(E) = L0 * exp(-(E/kappa)^beta)`` y su comparación con
    la exponencial simple (``beta = 1``) por AIC sobre los mismos puntos."""

    kappa_mwh: float
    l0: float
    beta: float
    aic_estirada: float
    aic_exponencial: float
    n_puntos: int

    @property
    def delta_aic(self) -> float:
        """AIC(exponencial) - AIC(estirada). Positivo favorece la estirada."""
        return self.aic_exponencial - self.aic_estirada


def ajustar_kappa_estirada(capacidades_mwh: np.ndarray, lpsp: np.ndarray,
                           lpsp_min: float = 1e-3, lpsp_max: float = 0.30) -> AjusteEstirado:
    """Ajusta la exponencial estirada en escala logarítmica.

    ``ln LPSP = ln L0 - (E/kappa)^beta`` por mínimos cuadrados no lineales,
    con el mismo tramo de LPSP que :func:`ajustar_kappa`. ``beta < 1``
    indica una cola más pesada que la exponencial (la curva se aplana a
    capacidades grandes); ``beta > 1``, una más liviana.
    """
    e = np.asarray(capacidades_mwh, float)
    y = np.asarray(lpsp, float)
    ok = np.isfinite(e) & np.isfinite(y) & (y >= lpsp_min) & (y <= lpsp_max) & (y > 0)
    n = int(ok.sum())
    nan = AjusteEstirado(np.nan, np.nan, np.nan, np.nan, np.nan, n)
    if n < 5:
        return nan
    e_ok, ln_y = e[ok], np.log(y[ok])

    b, a = np.polyfit(e_ok, ln_y, 1)
    if b >= 0:
        return nan
    rss_exp = float(np.sum((ln_y - (a + b * e_ok)) ** 2))

    def modelo(x, ln_l0, ln_k, beta):
        return ln_l0 - (x / np.exp(ln_k)) ** beta

    try:
        p, _ = optimize.curve_fit(modelo, e_ok, ln_y, p0=[a, np.log(-1.0 / b), 1.0],
                                  bounds=([-20, -10, 0.05], [5, 20, 5]), maxfev=20000)
    except (RuntimeError, ValueError):
        return nan
    rss_est = float(np.sum((ln_y - modelo(e_ok, *p)) ** 2))
    piso = 1e-300
    aic = lambda rss, k: n * np.log(max(rss, piso) / n) + 2 * k
    return AjusteEstirado(
        kappa_mwh=float(np.exp(p[1])), l0=float(np.exp(p[0])), beta=float(p[2]),
        aic_estirada=float(aic(rss_est, 3)), aic_exponencial=float(aic(rss_exp, 2)),
        n_puntos=n,
    )


# =====================================================================
# VALOR INCREMENTAL DE B Y M (tareas A4 y A5)
# =====================================================================

def ols(X: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray | float]:
    """Mínimos cuadrados con intercepto, sin dependencias externas.

    Devuelve coeficientes (intercepto primero), errores estándar, valores
    p, RSS, AIC gaussiano, R² y el R² leave-one-out exacto vía la matriz
    sombrero (PRESS): ``e_loo = e / (1 - h)``.
    """
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    y = np.asarray(y, float)
    n = len(y)
    Z = np.column_stack([np.ones(n), X])
    k = Z.shape[1]
    zz_inv = np.linalg.pinv(Z.T @ Z)
    beta = zz_inv @ Z.T @ y
    res = y - Z @ beta
    rss = float(res @ res)
    tss = float(((y - y.mean()) ** 2).sum())
    gl = n - k
    s2 = rss / gl if gl > 0 else np.nan
    se = np.sqrt(np.diag(zz_inv) * s2)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = beta / se
    p = 2 * stats.t.sf(np.abs(t), gl) if gl > 0 else np.full(k, np.nan)
    h = np.einsum("ij,jk,ik->i", Z, zz_inv, Z)
    e_loo = res / (1.0 - h)
    press = float(e_loo @ e_loo)
    return {
        "beta": beta, "se": se, "p": p, "rss": rss, "n": n, "k": k,
        "r2": 1 - rss / tss, "r2_adj": 1 - (rss / gl) / (tss / (n - 1)) if gl > 0 else np.nan,
        "r2_loo": 1 - press / tss, "rmse_loo": float(np.sqrt(press / n)),
        "aic": float(n * np.log(rss / n) + 2 * k),
        "bic": float(n * np.log(rss / n) + k * np.log(n)),
        "pred_loo": y - e_loo,
    }


def _preparar(df: pd.DataFrame, columnas: list[str], objetivo: str,
              log_objetivo: bool) -> pd.DataFrame:
    d = df[columnas + [objetivo]].replace([np.inf, -np.inf], np.nan).dropna()
    if log_objetivo:
        d = d[d[objetivo] > 0].copy()
        d[objetivo] = np.log(d[objetivo])
    return d


def comparar_modelos(
    df: pd.DataFrame,
    especificaciones: dict[str, list[str]],
    objetivo: str = "kappa_mwh",
    log_objetivo: bool = True,
) -> pd.DataFrame:
    """Compara especificaciones de ``ln(kappa)`` sobre la MISMA muestra.

    Para cada especificación reporta R², R²_LOO, RMSE_LOO, AIC y BIC, y
    una prueba F parcial contra la especificación anidada más grande de la
    lista (la de más predictores cuyo conjunto está contenido en esta).
    Todas usan las filas sin faltantes en la unión de predictores, para
    que los AIC sean comparables.
    """
    todas = sorted({c for cols in especificaciones.values() for c in cols})
    d = _preparar(df, todas, objetivo, log_objetivo)
    y = d[objetivo].to_numpy(float)

    ajustes = {nombre: ols(d[cols].to_numpy(float), y)
               for nombre, cols in especificaciones.items()}
    filas = []
    for nombre, cols in especificaciones.items():
        r = ajustes[nombre]
        # anidado: el subconjunto estricto con más predictores; ante empate,
        # el primero de la lista (así el orden de la configuración decide,
        # p. ej. PSH+B+M se prueba contra PSH+B y no contra PSH+M).
        orden = list(especificaciones)
        candidatos = [(len(c2), -orden.index(n2), n2) for n2, c2 in especificaciones.items()
                      if set(c2) < set(cols)]
        fila = {
            "modelo": nombre, "predictores": " + ".join(cols), "n": r["n"],
            "k": r["k"], "r2": r["r2"], "r2_adj": r["r2_adj"], "r2_loo": r["r2_loo"],
            "rmse_loo": r["rmse_loo"], "aic": r["aic"], "bic": r["bic"],
            "anidado_en": None, "delta_r2_loo": np.nan, "F_parcial": np.nan, "p_F": np.nan,
        }
        if candidatos:
            _, _, base = max(candidatos)
            rb = ajustes[base]
            q = r["k"] - rb["k"]
            gl = r["n"] - r["k"]
            F = ((rb["rss"] - r["rss"]) / q) / (r["rss"] / gl)
            fila.update(anidado_en=base, delta_r2_loo=r["r2_loo"] - rb["r2_loo"],
                        F_parcial=F, p_F=float(stats.f.sf(F, q, gl)))
        for c, b, se, p in zip(["intercepto"] + cols, r["beta"], r["se"], r["p"]):
            fila[f"coef_{c}"] = b
            fila[f"se_{c}"] = se
            fila[f"p_{c}"] = p
        filas.append(fila)
    return pd.DataFrame(filas)


def bootstrap_coeficientes(
    df: pd.DataFrame, predictores: list[str], objetivo: str = "kappa_mwh",
    replicas: int = 2000, semilla: int = 42, log_objetivo: bool = True,
    nivel: float = 0.95, grupos: pd.Series | None = None,
) -> pd.DataFrame:
    """Intervalos bootstrap (percentil) de los coeficientes, remuestreando sitios.

    Además del coeficiente bruto reporta el estandarizado (cambio de
    ``ln kappa`` por una desviación estándar del predictor), que es el
    que permite comparar el efecto de B, M y PSH entre sí.

    Con ``grupos`` (bloque de cada sitio, indexado como ``df``) se remuestrean
    bloques completos en vez de sitios (bootstrap por conglomerados): así
    el intervalo respeta que los sitios vecinos comparten el clima.
    """
    d = _preparar(df, predictores, objetivo, log_objetivo)
    X = d[predictores].to_numpy(float)
    y = d[objetivo].to_numpy(float)
    n = len(y)
    rng = np.random.default_rng(semilla)
    base = ols(X, y)["beta"]
    muestras = np.empty((replicas, len(predictores) + 1))
    if grupos is not None:
        g = grupos.reindex(d.index).to_numpy()
        unicos = np.unique(g)
        miembros = [np.flatnonzero(g == u) for u in unicos]
    for i in range(replicas):
        if grupos is None:
            idx = rng.integers(0, n, n)
        else:
            idx = np.concatenate([miembros[j] for j in rng.integers(0, len(unicos), len(unicos))])
        muestras[i] = ols(X[idx], y[idx])["beta"]
    a = (1 - nivel) / 2
    sd = np.r_[np.nan, X.std(axis=0, ddof=1)]
    filas = []
    for j, c in enumerate(["intercepto"] + predictores):
        m = muestras[:, j]
        lo, hi = np.nanquantile(m, [a, 1 - a])
        filas.append({
            "coeficiente": c, "estimado": base[j], "se_bootstrap": float(np.nanstd(m, ddof=1)),
            "ic_inf": lo, "ic_sup": hi, "excluye_cero": bool(lo > 0 or hi < 0),
            "sd_predictor": sd[j], "efecto_1sd": base[j] * sd[j],
            "efecto_1sd_ic_inf": lo * sd[j], "efecto_1sd_ic_sup": hi * sd[j],
        })
    return pd.DataFrame(filas)


def vif(df: pd.DataFrame, predictores: list[str]) -> pd.Series:
    """Factor de inflación de la varianza de cada predictor."""
    d = df[predictores].replace([np.inf, -np.inf], np.nan).dropna()
    out = {}
    for c in predictores:
        otros = [o for o in predictores if o != c]
        if not otros:
            out[c] = 1.0
            continue
        r2 = ols(d[otros].to_numpy(float), d[c].to_numpy(float))["r2"]
        out[c] = float(1.0 / (1.0 - r2)) if r2 < 1 else np.inf
    return pd.Series(out, name="VIF")


def bloques_por_correlacion(diarias: pd.DataFrame, n_bloques: int) -> pd.Series:
    """Agrupa sitios que comparten el clima, sin necesitar coordenadas.

    ``diarias`` tiene una columna por sitio (p. ej. GHI diaria). Se quita la
    climatología de cada día del año, se calcula la correlación entre las
    anomalías de los sitios y se agrupa por enlace promedio con distancia
    ``1 - r``. Dos sitios con anomalías muy correlacionadas están bajo los
    mismos sistemas de tiempo; dejarlos en bloques distintos de la
    validación es lo que hace optimista a la LOO (Roberts et al., 2017).
    """
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    doy = diarias.index.dayofyear
    anom = diarias - diarias.groupby(doy).transform("mean")
    r = anom.corr().to_numpy()
    dist = np.clip(1.0 - r, 0.0, None)
    np.fill_diagonal(dist, 0.0)
    z = linkage(squareform(dist, checks=False), method="average")
    etiquetas = fcluster(z, t=n_bloques, criterion="maxclust")
    return pd.Series(etiquetas, index=diarias.columns, name="bloque")


def cv_por_bloques(df: pd.DataFrame, predictores: list[str], grupos: pd.Series,
                   objetivo: str = "kappa_mwh", log_objetivo: bool = True) -> dict:
    """Validación cruzada dejando fuera un bloque completo cada vez.

    Devuelve R² y RMSE fuera de muestra y los coeficientes de cada pliegue
    (para ver si el signo de B se sostiene al quitar cada región).
    """
    d = _preparar(df, predictores, objetivo, log_objetivo)
    g = grupos.reindex(d.index).to_numpy()
    X = d[predictores].to_numpy(float)
    y = d[objetivo].to_numpy(float)
    pred = np.empty_like(y)
    coefs = []
    for u in np.unique(g):
        prueba = g == u
        r = ols(X[~prueba], y[~prueba])
        pred[prueba] = np.column_stack([np.ones(prueba.sum()), X[prueba]]) @ r["beta"]
        coefs.append(r["beta"])
    tss = float(((y - y.mean()) ** 2).sum())
    res = y - pred
    coefs = np.array(coefs)
    return {
        "r2_bloques": 1 - float(res @ res) / tss,
        "rmse_bloques": float(np.sqrt(np.mean(res ** 2))),
        "n_bloques": int(len(np.unique(g))),
        "coef_min": dict(zip(["intercepto"] + predictores, coefs.min(axis=0))),
        "coef_max": dict(zip(["intercepto"] + predictores, coefs.max(axis=0))),
    }
