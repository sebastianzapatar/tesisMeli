"""Figura 4.2 — Curvas capacidad–confiabilidad de los 51 sitios (resultado).

(a) LPSP frente a la capacidad del BESS para los 51 sitios, a la planta
    común de 150 MW, coloreadas por PSH. Las líneas horizontales marcan
    las metas de 5, 2 y 1 %.
(b) Capacidad necesaria E* para cada meta frente a kappa: E* escala con
    kappa, como predice E* = kappa·ln(L0/LPSP*).

Datos: pipeline/10_resultados_articulo2.py (10_curvas.csv.gz,
10_sitios.xlsx, 10_costo_planta_comun.xlsx). NO simula.
Salida: capitulo_4/fig_curvas_reales.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # figuras/

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.ticker import LogLocator, NullFormatter, ScalarFormatter

from resultados import (AZUL, DEMANDA_MW, GRIS, NARANJA, VERDE, barra_color, etiqueta_panel, formatear_eje,
                   leer_resultado, rejilla, guardar)

METAS = [(0.05, VERDE, "5 %"), (0.02, AZUL, "2 %"), (0.01, NARANJA, "1 %")]
E_MAX = 150.0          # horas de demanda


def main() -> None:
    curvas = leer_resultado("10_curvas.csv.gz")
    sitios = leer_resultado("10_sitios.xlsx").set_index("Serie")
    costos = leer_resultado("10_costo_planta_comun.xlsx")

    fig, ejes = rejilla(1, 2, alto_ej=2.3, y0=0.85, arriba=0.25, sep_h=1.35,
                        anchos=[(6.3 - 0.70 - 0.25 - 1.35) / 2 - 0.05, None])
    ax_a, ax_b = ejes[0]

    norma = Normalize(sitios.PSH.min(), sitios.PSH.max())
    cmap = plt.get_cmap("viridis")
    for s, g in curvas.groupby("Serie"):
        g = g[g.capacidad_mwh / DEMANDA_MW <= E_MAX]
        ax_a.plot(g.capacidad_mwh / DEMANDA_MW, np.maximum(g.lpsp, 1e-5), color=cmap(norma(sitios.loc[s, "PSH"])),
                  lw=0.8, alpha=0.9)
    for meta, color, _ in METAS:
        ax_a.axhline(meta, color=color, lw=0.9, ls="--")
    ax_a.set_yscale("log")
    ax_a.set_ylim(1e-4, 1)
    ax_a.set_xlim(0, E_MAX)
    ax_a.set_xticks([0, 50, 100, 150])
    formatear_eje(ax_a, xlabel="BESS capacity $E/D$ (h)", ylabel="LPSP",
                  menores_y=LogLocator(subs="auto"))
    sm = plt.cm.ScalarMappable(norm=norma, cmap=cmap)
    barra_color(fig, ax_a, sm, "PSH (h/day)")
    etiqueta_panel(ax_a, "(a)", debajo=0.55)

    k = sitios["kappa_mwh"] / DEMANDA_MW
    for meta, color, etiqueta in METAS:
        c = costos[costos.meta_lpsp == meta].set_index("Serie")
        ax_b.scatter(k.loc[c.index], c.e_star_sim_mwh / DEMANDA_MW, s=12, color=color, edgecolor="k", lw=0.3,
                     label=f"LPSP$^*$ = {etiqueta}", zorder=3)
    ax_b.set_xscale("log")
    ax_b.set_yscale("log")
    ax_b.xaxis.set_major_formatter(ScalarFormatter())
    ax_b.xaxis.set_minor_formatter(NullFormatter())
    formatear_eje(ax_b, xlabel=r"$\kappa/D$ (h)", ylabel="Required $E^*/D$ (h)",
                  menores_x=LogLocator(subs="auto"), menores_y=LogLocator(subs="auto"))
    ax_b.legend(loc="upper left", fontsize=7.5, handletextpad=0.3)
    etiqueta_panel(ax_b, "(b)", debajo=0.55)
    guardar(fig, "capitulo_4", "fig_curvas_reales")


if __name__ == "__main__":
    main()
