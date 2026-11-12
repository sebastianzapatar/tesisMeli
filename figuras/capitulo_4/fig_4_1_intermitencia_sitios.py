"""Figura 4.1 — Intermitencia de los 51 sitios: B y M de los eventos diarios de déficit.

(a) B diaria frente a la PSH. La franja gris es el rango de B cuando se barajan
    todos los días de cada sitio (sin agrupamiento): toda serie observada
    queda por encima.
(b) M frente a B: las dos medidas están correlacionadas.
(c) B calculada con eventos HORARIOS frente a la PSH: repite el ciclo día-noche
    y la cantidad de sol (por eso la tesis usa eventos diarios).
(d) Robustez a la planta: B con plantas de 5D, 6,25D y 10D frente a B con la
    planta común de 7,5D (150 MW).

Datos: codigo/resultados/articulo2/10_sitios.xlsx, 10_sensibilidad_BM_planta.xlsx
y 14_sustitutos_sitios.xlsx (pasos 10 y 14 del pipeline). NO simula.
Salida: capitulo_4/Intermitencia_sitios.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # figuras/

import numpy as np  # noqa: E402
from matplotlib.ticker import FormatStrFormatter  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from resultados import (AZUL, GRIS, NARANJA, VERDE, barra_color, etiqueta_panel,  # noqa: E402
                        formatear_eje, guardar, leer_resultado, rejilla)

PLANTAS = [(100, VERDE, "5D"), (125, AZUL, "6.25D"), (200, NARANJA, "10D")]


def main() -> None:
    s = leer_resultado("10_sitios.xlsx")
    sens = leer_resultado("10_sensibilidad_BM_planta.xlsx")
    sust = leer_resultado("14_sustitutos_sitios.xlsx")
    b_todo = sust[sust.tipo == "todo"].groupby("Serie").B.mean()

    ancho = (6.3 - 0.70 - 0.25 - 0.85) / 2
    fig, ejes = rejilla(2, 2, alto_ej=1.75, sep_v=0.85, y0=0.75, arriba=0.15,
                        anchos=[ancho - 0.45, ancho])
    (ax_a, ax_b), (ax_c, ax_d) = ejes

    # (a) B frente a PSH, con la franja de las series barajadas
    ax_a.axhspan(b_todo.min(), b_todo.max(), color=GRIS, alpha=0.25, lw=0)
    ax_a.text(0.03, (b_todo.min() + b_todo.max()) / 2, "all days shuffled", fontsize=7,
              color="0.35", va="center", transform=ax_a.get_yaxis_transform())
    sc = ax_a.scatter(s.PSH, s.B, c=s.M, cmap="viridis", s=16, edgecolor="k", lw=0.3, zorder=3)
    ax_a.text(0.04, 0.95, f"r = {s.B.corr(s.PSH):.2f}", transform=ax_a.transAxes, va="top",
              fontsize=7.5)
    formatear_eje(ax_a, xlabel="PSH (h/day)", ylabel="Burstiness $B$ (daily)")
    cb = barra_color(fig, ax_a, sc, "")
    cb.ax.set_title("$M$", fontsize=8, pad=3)
    cb.ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    etiqueta_panel(ax_a, "(a)")

    # (b) M frente a B
    ax_b.axhline(0, color=GRIS, lw=0.6, ls=":")
    ax_b.scatter(s.B, s.M, s=16, color=AZUL, edgecolor="k", lw=0.3)
    ax_b.text(0.04, 0.95, f"r = {s.B.corr(s.M):.2f}", transform=ax_b.transAxes, va="top",
              fontsize=7.5)
    formatear_eje(ax_b, xlabel="Burstiness $B$", ylabel="Memory $M$")
    etiqueta_panel(ax_b, "(b)")

    # (c) B horaria frente a PSH
    ax_c.scatter(s.PSH, s.B_horaria, s=16, color=NARANJA, edgecolor="k", lw=0.3)
    ax_c.text(0.97, 0.95, f"r = {s.B_horaria.corr(s.PSH):.2f}", transform=ax_c.transAxes,
              ha="right", va="top", fontsize=7.5)
    formatear_eje(ax_c, xlabel="PSH (h/day)", ylabel="$B$ with hourly events")
    etiqueta_panel(ax_c, "(c)")

    # (d) robustez a la planta
    base = s.set_index("Serie").B
    lim = [base.min() - 0.03, base.max() + 0.05]
    ax_d.plot(lim, lim, color=GRIS, lw=0.8)
    for p, color, nombre in PLANTAS:
        g = sens[sens.planta_mw == p].set_index("Serie").B.reindex(base.index)
        rho = spearmanr(base, g).correlation
        ax_d.scatter(base, g, s=12, color=color, edgecolor="k", lw=0.25,
                     label=f"{nombre} ($\\rho$ = {rho:.2f})")
    ax_d.set_xlim(lim)
    ax_d.set_ylim(lim)
    formatear_eje(ax_d, xlabel="$B$ with plant 7.5D", ylabel="$B$ with other plant")
    ax_d.legend(loc="lower right", fontsize=7, handletextpad=0.2, frameon=True,
                framealpha=0.9, edgecolor="none")
    etiqueta_panel(ax_d, "(d)")
    guardar(fig, "capitulo_4", "Intermitencia_sitios")


if __name__ == "__main__":
    main()
