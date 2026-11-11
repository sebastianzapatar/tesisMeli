"""Figura — Qué explica kappa en los 51 sitios (resultado).

(a) ln kappa frente a la PSH, coloreado por B: la PSH fija el nivel.
(b) Predicción leave-one-out frente a kappa simulado, con PSH sola y
    con PSH + B + M.
(c) Residuo parcial de ln kappa frente a B (controlando PSH y M).
(d) Residuo parcial frente a M (controlando PSH y B).

Residuo parcial: e + beta_j·x_j, con e el residuo del modelo completo;
su pendiente es el coeficiente de x_j en la regresión múltiple.
Datos: 10_sitios.xlsx. Salida: salida/fig_kappa_predictores.pdf
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from comun import (AZUL, DEMANDA_MW, GRIS, NARANJA, barra_color, etiqueta_panel, formatear_eje, guardar,
                   leer_resultado, rejilla)
from intermitencia.sustituto import ols


def main() -> None:
    d = leer_resultado("10_sitios.xlsx").dropna(subset=["kappa_mwh", "PSH", "B", "M"])
    y = np.log(d.kappa_mwh.to_numpy() / DEMANDA_MW)       # kappa en horas de demanda
    X = d[["PSH", "B", "M"]].to_numpy()
    completo = ols(X, y)
    solo_psh = ols(d[["PSH"]].to_numpy(), y)
    e = y - np.column_stack([np.ones(len(y)), X]) @ completo["beta"]

    ancho = (6.3 - 0.70 - 0.25 - 0.85) / 2
    fig, ejes = rejilla(2, 2, alto_ej=1.75, sep_v=0.85, y0=0.75, arriba=0.15,
                        anchos=[ancho - 0.35, ancho])
    (ax_a, ax_d), (ax_b, ax_c) = ejes

    sc = ax_a.scatter(d.PSH, y, c=d.B, cmap="viridis", s=16, edgecolor="k", lw=0.3)
    xs = np.linspace(d.PSH.min(), d.PSH.max(), 50)
    ax_a.plot(xs, solo_psh["beta"][0] + solo_psh["beta"][1] * xs, color=GRIS, lw=1, ls="--")
    formatear_eje(ax_a, xlabel="PSH (h/day)", ylabel=r"$\ln\kappa$")
    barra_color(fig, ax_a, sc, "Burstiness $B$")
    etiqueta_panel(ax_a, "(a)", debajo=0.50)

    for ax, j, nombre, color, panel in ((ax_b, 2, "Burstiness $B$", AZUL, "(c)"),
                                        (ax_c, 3, "Memory $M$", NARANJA, "(d)")):
        x = X[:, j - 1]
        parcial = e + completo["beta"][j] * x
        ax.scatter(x, parcial, s=14, color=color, edgecolor="k", lw=0.3)
        xs = np.linspace(x.min(), x.max(), 20)
        ax.plot(xs, completo["beta"][j] * xs, color="k", lw=1)
        pv = completo["p"][j]
        txt_p = "p < 0.001" if pv < 0.001 else f"p = {pv:.2f}"
        ax.text(0.04, 0.95, f"$\\beta$ = {completo['beta'][j]:+.2f}  ({txt_p})",
                transform=ax.transAxes, va="top", fontsize=7.5)
        formatear_eje(ax, xlabel=nombre, ylabel="Partial residual" if j == 2 else "")
        etiqueta_panel(ax, panel, debajo=0.50)

    lim = [y.min() - 0.2, y.max() + 0.2]
    ax_d.plot(lim, lim, color=GRIS, lw=0.8)
    ax_d.scatter(y, solo_psh["pred_loo"], s=12, facecolor="none", edgecolor=GRIS, lw=0.8,
                 label=f"PSH ($R^2_{{LOO}}$ = {solo_psh['r2_loo']:.2f})")
    ax_d.scatter(y, completo["pred_loo"], s=12, color=AZUL, edgecolor="k", lw=0.3,
                 label=f"PSH + B + M ($R^2_{{LOO}}$ = {completo['r2_loo']:.2f})")
    ax_d.set_xlim(lim)
    ax_d.set_ylim(lim)
    formatear_eje(ax_d, xlabel=r"Simulated $\ln\kappa$", ylabel=r"LOO prediction")
    ax_d.legend(loc="upper left", fontsize=7, handletextpad=0.2)
    etiqueta_panel(ax_d, "(b)", debajo=0.50)
    guardar(fig, "fig_kappa_predictores")


if __name__ == "__main__":
    main()
