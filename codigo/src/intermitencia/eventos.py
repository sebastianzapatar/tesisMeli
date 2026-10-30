"""Métricas de intermitencia: eventos, burstiness (B) y memory (M).

Por qué se rehízo el cálculo
----------------------------
El ``ByM.py`` original construía los "eventos" como los cruces de la
**suma acumulada de excedentes** por múltiplos de ``a_mu = P25(x)``.
Eso tiene tres problemas, en orden de gravedad:

1. **Error de categoría.** La burstiness está definida para procesos
   puntuales con periodos de silencio y ráfagas. Una suma acumulada de
   una cantidad siempre positiva es monótona creciente: no tiene
   silencios, es un reloj cuantizado. Lo que ``B`` terminaba midiendo era
   la forma de la distribución del excedente diario, no su agrupamiento
   temporal.

2. **Intervalos nulos.** Como ``Accum`` es monótona, ``posiciony`` es
   ``[j0, j0+1, ...]``. Si un día cruzaba dos o más umbrales se hacía
   ``append`` del mismo índice varias veces, produciendo ``tau = 0``. Con
   ``a_mu`` en el percentil 25 se cruzaba ~1.25 umbrales por día, así que
   los ceros eran frecuentes: inflaban sigma y empujaban B hacia +1.

3. **Umbral dependiente de la serie.** ``a_mu`` se recalculaba por serie
   y por hora, de modo que cada sitio usaba una unidad de energía
   distinta y los B/M no eran comparables entre sitios.

Además el doble bucle era O(n·m) con n~9 800 días y m~12 000 umbrales,
o sea ~120 M de iteraciones por hora y por serie. Aquí el mismo cálculo
se hace con ``np.searchsorted`` en O(n log m).

Qué se hace ahora
-----------------
Un **evento** es una corrida contigua de déficit (``balance < -umbral``).
Eso sí tiene silencios (días despejados) y ráfagas (rachas nubladas), que
es exactamente el régimen para el que B y M fueron diseñadas --- y
exactamente lo que obliga a poner más batería.

* ``B`` con la corrección de tamaño finito de Kim & Jo (2016). Importa:
  el número de eventos varía muchísimo entre sitios y horas, y la B
  clásica está sesgada por ``n``, así que compararla entre sitios es
  comparar sesgos.
* ``M`` de Goh & Barabási (2008): correlación de lag-1 con medias y
  desviaciones separadas para las dos subsecuencias.
* Agregación entre horas por transformada de Fisher, no media
  aritmética: M es un coeficiente de correlación y promediarlo
  aritméticamente está mal.

Referencias
-----------
Goh, K.-I. & Barabási, A.-L. (2008). *Burstiness and memory in complex
systems*. EPL 81(4), 48002.

Kim, E.-K. & Jo, H.-H. (2016). *Measuring burstiness for finite event
sequences*. Physical Review E 94, 032311.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

__all__ = [
    "Eventos",
    "detectar_eventos",
    "burstiness",
    "memory",
    "metricas_intermitencia",
    "agregar_memory_fisher",
    "burstiness_legacy_cruces",
]


@dataclass(frozen=True)
class Eventos:
    """Conjunto de eventos de déficit (o de excedente) de una serie."""

    inicios: np.ndarray      # índice de inicio de cada evento
    duraciones: np.ndarray   # número de pasos de cada evento
    severidades: np.ndarray  # energía del evento [MWh]
    n_pasos: int             # longitud de la serie original

    @property
    def n_eventos(self) -> int:
        return int(self.inicios.size)

    @property
    def taus(self) -> np.ndarray:
        """Tiempos entre inicios de eventos consecutivos [pasos]."""
        return np.diff(self.inicios).astype(np.float64)

    @property
    def tasa(self) -> float:
        """Eventos por paso de tiempo."""
        return self.n_eventos / self.n_pasos if self.n_pasos else 0.0


def detectar_eventos(
    serie: np.ndarray, umbral: float = 0.0, base: str = "deficit"
) -> Eventos:
    """Detecta corridas contiguas de déficit (o de excedente).

    Parameters
    ----------
    serie
        Balance horario [MW].
    umbral
        Un evento de déficit ocurre cuando ``serie < -umbral``; uno de
        excedente cuando ``serie > umbral``.
    base
        ``"deficit"`` o ``"excedente"``.
    """
    x = np.asarray(serie, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError(f"Se esperaba una serie 1-D, llegó {x.shape}.")

    if base == "deficit":
        activo = x < -umbral
        magnitud = np.where(activo, -x, 0.0)
    elif base == "excedente":
        activo = x > umbral
        magnitud = np.where(activo, x, 0.0)
    else:
        raise ValueError(f"base='{base}' no es válida.")

    if not activo.any():
        vacio = np.array([], dtype=np.int64)
        return Eventos(vacio, vacio, np.array([]), x.size)

    # Fronteras de las corridas mediante diferencias sobre la máscara.
    borde = np.diff(activo.astype(np.int8))
    inicios = np.flatnonzero(borde == 1) + 1
    finales = np.flatnonzero(borde == -1) + 1
    if activo[0]:
        inicios = np.r_[0, inicios]
    if activo[-1]:
        finales = np.r_[finales, activo.size]

    duraciones = finales - inicios

    # Severidad = energía acumulada de cada corrida, vía suma acumulada.
    acum = np.r_[0.0, np.cumsum(magnitud)]
    severidades = acum[finales] - acum[inicios]

    return Eventos(
        inicios=inicios.astype(np.int64),
        duraciones=duraciones.astype(np.int64),
        severidades=severidades,
        n_pasos=int(x.size),
    )


def burstiness(taus: np.ndarray, corregir_tamano_finito: bool = True) -> float:
    """Coeficiente de burstiness B a partir de los tiempos entre eventos.

    Con ``corregir_tamano_finito=False`` devuelve la definición clásica de
    Goh & Barabási::

        B = (sigma - mu) / (sigma + mu) = (r - 1) / (r + 1),   r = sigma/mu

    Con ``True`` (por defecto) devuelve la versión corregida de Kim & Jo
    (2016), que elimina el sesgo por número finito de eventos::

        A_n(r) = (sqrt(n+1)·r - sqrt(n-1)) /
                 ((sqrt(n+1) - 2)·r + sqrt(n-1))

    donde ``n`` es el número de eventos (``len(taus) + 1``). Ambas viven
    en [-1, 1]: -1 = perfectamente regular, 0 = Poisson, +1 = muy bursty.
    """
    t = np.asarray(taus, dtype=np.float64)
    t = t[np.isfinite(t)]
    if t.size < 2:
        return float("nan")

    mu = t.mean()
    if mu <= 0:
        return float("nan")

    sigma = t.std(ddof=0)  # el paper usa la desviación poblacional
    r = sigma / mu

    if not corregir_tamano_finito:
        return float((r - 1.0) / (r + 1.0))

    n = float(t.size + 1)  # número de eventos
    if n < 3:
        return float("nan")

    raiz_mas = np.sqrt(n + 1.0)
    raiz_menos = np.sqrt(n - 1.0)
    numerador = raiz_mas * r - raiz_menos
    denominador = (raiz_mas - 2.0) * r + raiz_menos
    if abs(denominador) < 1e-12:
        return float("nan")
    return float(np.clip(numerador / denominador, -1.0, 1.0))


def memory(taus: np.ndarray, metodo: str = "pearson") -> float:
    """Coeficiente de memoria M: correlación de lag-1 entre tiempos de espera.

    Definición de Goh & Barabási (2008)::

        M = (1/(n-1)) * sum_i (tau_i - mu_1)(tau_{i+1} - mu_2) / (sigma_1 sigma_2)

    donde ``mu_1, sigma_1`` son de ``tau_1..tau_{n-1}`` y ``mu_2, sigma_2``
    de ``tau_2..tau_n`` --- medias y desviaciones **separadas**, no
    compartidas.

    ``metodo="spearman"`` usa rangos en lugar de valores. Es más robusto a
    colas pesadas, pero deja de ser la M de la literatura, así que hay que
    declararlo explícitamente en el texto.
    """
    t = np.asarray(taus, dtype=np.float64)
    t = t[np.isfinite(t)]
    if t.size < 3:
        return float("nan")

    a, b = t[:-1], t[1:]

    if metodo == "spearman":
        if np.all(a == a[0]) or np.all(b == b[0]):
            return float("nan")
        rho, _ = stats.spearmanr(a, b)
        return float(rho)

    if metodo != "pearson":
        raise ValueError(f"metodo='{metodo}' no es válido.")

    s1, s2 = a.std(ddof=0), b.std(ddof=0)
    if s1 < 1e-12 or s2 < 1e-12:
        return float("nan")
    return float(np.clip(np.mean((a - a.mean()) * (b - b.mean())) / (s1 * s2), -1.0, 1.0))


def agregar_memory_fisher(valores: np.ndarray, n_obs: np.ndarray) -> float:
    """Promedia coeficientes de correlación con la transformada de Fisher.

    Promediar correlaciones aritméticamente (lo que hacía
    ``groupby("Serie")[["B","M"]].mean()``) está mal: la distribución
    muestral de r es asimétrica. Se transforma con artanh, se promedia
    ponderando por ``n - 3``, y se devuelve con tanh.
    """
    v = np.asarray(valores, dtype=np.float64)
    n = np.asarray(n_obs, dtype=np.float64)
    ok = np.isfinite(v) & np.isfinite(n) & (n > 3) & (np.abs(v) < 1.0)
    if not ok.any():
        return float("nan")
    z = np.arctanh(v[ok])
    w = n[ok] - 3.0
    return float(np.tanh(np.sum(w * z) / np.sum(w)))


def metricas_intermitencia(
    balance: np.ndarray,
    umbral: float = 0.0,
    base: str = "deficit",
    min_eventos: int = 30,
    corregir_tamano_finito: bool = True,
    metodo_memory: str = "pearson",
) -> dict[str, float]:
    """Calcula B, M y los estadísticos de severidad de una serie.

    Devuelve también las severidades por cuantil, que son un criterio de
    dimensionamiento directo e interpretable: ``S_p90`` es la energía que
    cubre el 90 % de los eventos de déficit de un solo golpe.
    """
    ev = detectar_eventos(balance, umbral=umbral, base=base)

    base_dict: dict[str, float] = {
        "n_eventos": float(ev.n_eventos),
        "tasa_eventos_por_dia": ev.tasa * 24.0,
        "B": float("nan"),
        "M": float("nan"),
        "tau_medio_h": float("nan"),
        "tau_cv": float("nan"),
        "duracion_media_h": float("nan"),
        "duracion_p95_h": float("nan"),
        "severidad_media_mwh": float("nan"),
        "severidad_p50_mwh": float("nan"),
        "severidad_p90_mwh": float("nan"),
        "severidad_p99_mwh": float("nan"),
        "severidad_max_mwh": float("nan"),
        "energia_deficit_total_mwh": float(ev.severidades.sum()),
    }

    if ev.n_eventos < min_eventos:
        return base_dict

    taus = ev.taus
    mu = taus.mean()

    base_dict.update(
        {
            "B": burstiness(taus, corregir_tamano_finito),
            "M": memory(taus, metodo_memory),
            "tau_medio_h": float(mu),
            "tau_cv": float(taus.std(ddof=0) / mu) if mu > 0 else float("nan"),
            "duracion_media_h": float(ev.duraciones.mean()),
            "duracion_p95_h": float(np.percentile(ev.duraciones, 95)),
            "severidad_media_mwh": float(ev.severidades.mean()),
            "severidad_p50_mwh": float(np.percentile(ev.severidades, 50)),
            "severidad_p90_mwh": float(np.percentile(ev.severidades, 90)),
            "severidad_p99_mwh": float(np.percentile(ev.severidades, 99)),
            "severidad_max_mwh": float(ev.severidades.max()),
        }
    )
    return base_dict


# =====================================================================
# REPRODUCCIÓN DEL MÉTODO ANTIGUO
# =====================================================================

def burstiness_legacy_cruces(
    x: np.ndarray, percentil: float = 25.0, corregir_tamano_finito: bool = False
) -> dict[str, float]:
    """Reimplementa el método de cruces del ``ByM.py`` original.

    Se conserva **solo** para poder cuantificar en la tesis cuánto cambian
    B y M al corregir la metodología. No debe usarse para resultados
    nuevos: mide la forma de la distribución del excedente, no su
    agrupamiento temporal (ver la nota del módulo).

    La diferencia de implementación es que los cruces se localizan con
    ``np.searchsorted`` en O(n log m) en vez del doble bucle O(n·m)
    original, pero la secuencia ``tk`` resultante es la misma ---
    incluyendo los ``tau = 0`` que son el defecto del método.
    """
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]

    fuera = {"B_legacy": float("nan"), "M_legacy": float("nan"),
             "frac_tau_cero": float("nan"), "n_tau_legacy": 0.0}
    if x.size < 5 or x.sum() <= 0:
        return fuera

    a_mu = float(np.percentile(x, percentil))
    if a_mu <= 0:
        return fuera

    acum = np.cumsum(x)
    n_umbrales = int(acum[-1] / a_mu)
    if n_umbrales < 3:
        return fuera

    umbrales = a_mu * np.arange(1, n_umbrales + 1, dtype=np.float64)

    # Esto es exactamente lo que hacía el doble bucle: para cada umbral,
    # el primer índice donde la acumulada lo alcanza. Los umbrales que se
    # cruzan el mismo día comparten índice -> tau = 0.
    tk = np.searchsorted(acum, umbrales, side="left").astype(np.float64)
    taus = np.diff(tk)
    if taus.size < 2:
        return fuera

    return {
        "B_legacy": burstiness(taus, corregir_tamano_finito),
        "M_legacy": memory(taus, "spearman"),
        "frac_tau_cero": float(np.mean(taus == 0.0)),
        "n_tau_legacy": float(taus.size),
    }


def serie_diaria_deficit(balance: pd.Series) -> pd.Series:
    """Agrega el déficit horario a déficit diario [MWh/día].

    Trabajar en resolución diaria elimina el ciclo diurno determinista, de
    modo que B y M miden variabilidad meteorológica (rachas nubladas) y no
    la salida y puesta del sol.
    """
    if not isinstance(balance.index, pd.DatetimeIndex):
        raise TypeError("Se requiere índice temporal.")
    return (-balance.clip(upper=0.0)).resample("D").sum()
