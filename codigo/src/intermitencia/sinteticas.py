"""Series sintéticas para aislar y verificar el efecto de la intermitencia.

Dos herramientas:

1. **Series sustitutas por barajado de días** (``barajar_dias``).
   Reordenan al azar los días completos de una serie horaria real. Cada día
   conserva su perfil horario, así que la serie sustituta tiene EXACTAMENTE
   la misma PSH, la misma distribución de energía diaria y el mismo ciclo
   diario que la real; lo único que cambia es el ORDEN de los días.

   * ``ambito="todo"``: baraja todos los días de la serie. Destruye el
     agrupamiento de corto plazo, la estacionalidad y la variación entre
     años (incluidos los años El Niño / La Niña).
   * ``ambito="mes"``: baraja los días solo dentro de cada mes de cada año.
     Conserva la energía de cada mes (estacionalidad y años secos o
     húmedos) y destruye solo el agrupamiento de días dentro del mes
     (rachas de días nublados de escala sinóptica).

   Comparar la serie real con las dos sustitutas descompone el
   almacenamiento necesario en tres partes: el que exige la distribución de
   los días sin importar su orden, el que añade la estacionalidad y la
   variación entre años, y el que añaden las rachas de corto plazo.

2. **Secuencias de eventos con B y M conocidos** (``secuencia_renovacion``).
   Tiempos entre eventos log-normales con un coeficiente de variación ``cv``
   dado y correlación entre intervalos consecutivos inducida por una cópula
   gaussiana AR(1) de parámetro ``rho``. Para n -> infinito:

       B = (cv - 1)/(cv + 1)
       M = (exp(s2·rho) - 1)/(exp(s2) - 1),   s2 = ln(1 + cv²)

   Sirven para verificar que :func:`eventos.burstiness` y
   :func:`eventos.memory` recuperan los valores verdaderos y para medir su
   sesgo y dispersión según el número de eventos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------
# 1. Series sustitutas por barajado de días
# ---------------------------------------------------------------------

AMBITOS = ("todo", "mes")


def barajar_dias(serie: pd.Series, rng: np.random.Generator, ambito: str = "todo") -> pd.Series:
    """Serie sustituta: los mismos días completos en otro orden.

    Parameters
    ----------
    serie : serie horaria con índice temporal y días completos de 24 h.
    rng : generador aleatorio (fijar la semilla para reproducir).
    ambito : ``"todo"`` (todos los días) o ``"mes"`` (dentro de cada mes de cada año).

    Returns
    -------
    pd.Series con el MISMO índice que ``serie`` y los días reordenados.
    """
    if ambito not in AMBITOS:
        raise ValueError(f"ambito debe ser uno de {AMBITOS}")
    if not isinstance(serie.index, pd.DatetimeIndex):
        raise TypeError("Se requiere índice temporal.")
    valores = serie.to_numpy(dtype=np.float64)
    if valores.size % 24:
        raise ValueError("La serie debe tener días completos de 24 horas.")
    dias = valores.reshape(-1, 24)
    n = dias.shape[0]

    if ambito == "todo":
        orden = rng.permutation(n)
    else:
        fechas = serie.index[::24]
        claves = fechas.year * 100 + fechas.month
        orden = np.arange(n)
        for c in np.unique(claves):
            idx = np.flatnonzero(claves == c)
            orden[idx] = rng.permutation(idx)
    return pd.Series(dias[orden].ravel(), index=serie.index, name=serie.name)


# ---------------------------------------------------------------------
# 2. Secuencias de eventos con burstiness y memoria conocidas
# ---------------------------------------------------------------------

def b_teorica(cv: float) -> float:
    """Burstiness de Goh y Barabási para un coeficiente de variación dado."""
    return (cv - 1.0) / (cv + 1.0)


def m_teorica(cv: float, rho: float) -> float:
    """Memoria (correlación de Pearson) de la log-normal con cópula AR(1)."""
    s2 = np.log(1.0 + cv ** 2)
    return float(np.expm1(s2 * rho) / np.expm1(s2))


def secuencia_renovacion(n_eventos: int, cv: float, rho: float,
                         rng: np.random.Generator) -> np.ndarray:
    """Tiempos entre eventos log-normales con CV ``cv`` y memoria por ``rho``.

    Devuelve ``n_eventos - 1`` intervalos (media 1).
    """
    n = n_eventos - 1
    s = np.sqrt(np.log(1.0 + cv ** 2))
    z = np.empty(n)
    z[0] = rng.standard_normal()
    e = rng.standard_normal(n) * np.sqrt(1.0 - rho ** 2)
    for k in range(1, n):
        z[k] = rho * z[k - 1] + e[k]
    return np.exp(-0.5 * s ** 2 + s * z)
