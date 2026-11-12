"""Figura 3.3 — Curvas de isoconfiabilidad en el plano (E, P_pv): por qué se usa una planta común.

Para dos sitios con la misma PSH (independiente y agrupado) se simula la LPSP
en una grilla de potencia FV y capacidad de BESS, y se trazan las curvas de
igual LPSP (1 %, 2 % y 5 %). Sobredimensionar la planta sustituye parte del
almacenamiento: si cada sitio usara su planta óptima, esa sustitución
absorbería la diferencia de intermitencia. Comparar a la planta común
P_ref (línea horizontal) aísla el efecto de B y M sobre kappa.

Estilo inspirado en la Fig. 9 de Kebede et al. (2021) (frentes de Pareto
área FV–número de baterías con isolíneas de LPSP).
Datos: sitios sintéticos de sitios_ilustrativos.py (ilustrativos).
Salida: capitulo_3/fig_sustitucion_planta.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # figuras/

import matplotlib.pyplot as plt
import numpy as np

from sitios_ilustrativos import (DEMANDA_MW, COLORES_SITIOS, GRIS, P_REF_MW, SITIOS, balance_mw, curva_lpsp, estilo,
                   etiqueta_panel, formatear_eje, ghi_sintetica, guardar)

POTENCIAS = np.arange(110.0, 261.0, 10.0)      # MW
CAPACIDADES = np.arange(0.0, 6001.0, 150.0)    # MWh
NIVELES = [0.01, 0.02, 0.05]
ESTILOS = [":", "--", "-"]
ANIOS = 15


def main() -> None:
    estilo.aplicar_estilo()
    fig, axes = estilo.crear_figura(ncols=2, sharey=True, margen_inf=0.85, margen_sup=0.45)
    for ax, i, panel in zip(axes, (1, 2), ("(a)", "(b)")):
        sitio = SITIOS[i]
        ghi = ghi_sintetica(sitio, anios=ANIOS)
        z = np.array([curva_lpsp(balance_mw(ghi, p), CAPACIDADES) for p in POTENCIAS])
        cs = ax.contour(CAPACIDADES / DEMANDA_MW, POTENCIAS / DEMANDA_MW, z, levels=NIVELES, colors=COLORES_SITIOS[i],
                        linestyles=ESTILOS, linewidths=1.4)
        ax.clabel(cs, fmt={n: f"{n:.0%}" for n in NIVELES}, fontsize=7.5, inline=True)
        ax.axhline(P_REF_MW / DEMANDA_MW, color=GRIS, lw=1.0, ls="-.")
        ax.text(CAPACIDADES[-1] / DEMANDA_MW * 0.98, P_REF_MW / DEMANDA_MW + 0.15, "common plant $P_{\\mathrm{ref}}$",
                ha="right", va="bottom", fontsize=7.5, color=GRIS)
        ax.set_title(f"{sitio.nombre} site", fontsize=9)
        formatear_eje(ax, xlabel="BESS capacity $E/D$ (h)",
                      ylabel="PV power $P_{\\mathrm{PV}}/D$" if i == 1 else "")
        ax.set_xlim(0, CAPACIDADES[-1] / DEMANDA_MW)
        ax.set_xticks([0, 100, 200, 300])
        ax.set_ylim(POTENCIAS[0] / DEMANDA_MW, POTENCIAS[-1] / DEMANDA_MW)
        etiqueta_panel(ax, panel, debajo=0.55)
    guardar(fig, "capitulo_3", "fig_sustitucion_planta")


if __name__ == "__main__":
    main()
