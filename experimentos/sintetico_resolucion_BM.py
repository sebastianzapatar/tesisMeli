"""Experimento sintético: ¿qué mide B a resolución horaria y a resolución diaria?

Genera sitios con distinta claridad media (kt -> PSH) y distinta persistencia
de los días nublados (phi, AR(1) diario). La persistencia es lo que define el
almacenamiento necesario (Rippl); la claridad media solo cambia el nivel.

Resultado esperado (semilla 0):
  * B horaria cambia con kt (PSH) y casi nada con phi  -> confundida con PSH.
  * B diaria cambia con phi y casi nada con kt          -> mide persistencia.

Uso:
    ./.venv/bin/python experimentos/sintetico_resolucion_BM.py
"""

import numpy as np

from intermitencia.almacenamiento import energia_requerida_pico_secuente
from intermitencia.eventos import metricas_intermitencia

DIAS = 365 * 20
DEMANDA_MW = 20.0
SOBREDIMENSION = 1.15  # planta que genera 1.15 veces la energía demandada

rng = np.random.default_rng(0)
horas = np.arange(24)
cielo_despejado = np.clip(np.sin(np.pi * (horas - 6) / 12), 0, None) * 1000.0


def ghi_sitio(kt_medio: float, phi: float, sd: float = 0.18) -> np.ndarray:
    z = np.zeros(DIAS)
    e = rng.normal(0.0, sd * np.sqrt(1 - phi**2), DIAS)
    for d in range(1, DIAS):
        z[d] = phi * z[d - 1] + e[d]
    kt = np.clip(kt_medio + z, 0.05, 1.0)
    return (kt[:, None] * cielo_despejado[None, :]).ravel()


def main() -> None:
    print(f"{'kt':>5}{'phi':>6}{'PSH':>6} | {'B_hor':>7}{'M_hor':>7} | "
          f"{'B_dia':>7}{'M_dia':>7} | {'E_Rippl_MWh':>12}")
    for kt in (0.55, 0.65, 0.75):
        for phi in (0.0, 0.5, 0.8):
            ghi = ghi_sitio(kt, phi)
            psh = ghi.sum() / 1000.0 / DIAS
            p_mw = DEMANDA_MW * 24 / (psh * 0.8) * SOBREDIMENSION
            balance = ghi / 1000.0 * 0.8 * p_mw - DEMANDA_MW

            hor = metricas_intermitencia(balance)

            # Igual que pipeline/02_intermitencia.py con resolucion: "diaria"
            deficit_diario = (-np.clip(balance, None, 0)).reshape(DIAS, 24).sum(1)
            serie = -deficit_diario
            dia = metricas_intermitencia(serie - serie.mean())

            print(f"{kt:5.2f}{phi:6.1f}{psh:6.2f} | {hor['B']:7.3f}{hor['M']:7.3f} | "
                  f"{dia['B']:7.3f}{dia['M']:7.3f} | "
                  f"{energia_requerida_pico_secuente(balance):12.0f}")


if __name__ == "__main__":
    main()
