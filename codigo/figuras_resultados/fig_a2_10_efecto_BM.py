"""Figura — Valor incremental de B y M sobre la PSH (resultado).

(a) R² leave-one-out de cada especificación de ln kappa (criterio D5):
    PSH sola, PSH con B y/o M, y PSH con los indicadores simples. La
    línea punteada es R²_LOO(PSH) + 0,05 (umbral de valor práctico).
(b) Efecto estandarizado sobre ln kappa (cambio por una desviación
    estándar del predictor) en el modelo PSH + B + M, con su intervalo
    bootstrap del 95 % (línea continua: remuestreo de sitios; punteada:
    remuestreo de bloques de clima común).
(c) Lo que significa en almacenamiento: batería adicional para pasar de
    LPSP = 5 % a 1 % (kappa·ln 5) en un sitio de PSH mediana, con B y M
    en sus percentiles 10, 50 y 90.

Datos: 11_comparacion_modelos.xlsx, 11_bootstrap_coeficientes.xlsx,
11_efecto_BM.xlsx. Salida: salida/fig_efecto_BM.pdf
"""

from __future__ import annotations

import numpy as np
from matplotlib.ticker import NullLocator

from comun import (AZUL, DEMANDA_MW, CFG, GRIS, NARANJA, VERDE, etiqueta_panel, formatear_eje, guardar,
                   leer_resultado, rejilla)

ORDEN = ["PSH", "PSH+CV", "PSH+racha", "PSH+ac1kt", "PSH+M", "PSH+B", "PSH+B+M", "PSH+B+M+ac1kt"]
ETIQUETAS = {"PSH": "PSH", "PSH+CV": "+CV$_E$", "PSH+racha": "+run$_{max}$",
             "PSH+ac1kt": "+ac1($k_t$)", "PSH+M": "+$M$", "PSH+B": "+$B$",
             "PSH+B+M": "+$B$+$M$", "PSH+B+M+ac1kt": "+$B$+$M$\n+ac1"}


def main() -> None:
    comp = leer_resultado("11_comparacion_modelos.xlsx").set_index("modelo")
    boot = leer_resultado("11_bootstrap_coeficientes.xlsx")
    efecto = leer_resultado("11_efecto_BM.xlsx")
    umbral = float(CFG.sustituto["umbral_delta_r2_loo"])

    ancho_total = 6.3 - 0.70 - 0.25
    fig, ejes = rejilla(2, 2, alto_ej=1.6, sep_v=0.85, y0=0.75, arriba=0.15)
    (ax_a, ax_x), (ax_b, ax_c) = ejes
    pos = ax_a.get_position()
    ax_x.remove()
    ax_a.set_position([pos.x0, pos.y0, ancho_total / 6.3, pos.height])

    modelos = [m for m in ORDEN if m in comp.index]
    r2 = comp.loc[modelos, "r2_loo"].to_numpy()
    colores = [GRIS if m == "PSH" else (AZUL if ("B" in m or "M" in m) else VERDE) for m in modelos]
    ax_a.bar(np.arange(len(modelos)), r2, color=colores, edgecolor="k", lw=0.4, width=0.65)
    base = comp.loc["PSH", "r2_loo"]
    ax_a.axhline(base + umbral, color=NARANJA, lw=1, ls="--")
    for i, v in enumerate(r2):
        ax_a.text(i, v + 0.008, f"{v:.3f}", ha="center", va="bottom", fontsize=7)
    ax_a.set_xticks(np.arange(len(modelos)), [ETIQUETAS[m] for m in modelos], fontsize=7.5)
    ax_a.set_ylim(max(0, r2.min() - 0.15), min(1, r2.max() + 0.06))
    formatear_eje(ax_a, ylabel="$R^2_{\\mathrm{LOO}}$ of $\\ln\\kappa$", menores_x=NullLocator())
    ax_a.tick_params(axis="x", which="both", top=False)
    etiqueta_panel(ax_a, "(a)", debajo=0.60)

    sel = boot[(boot.modelo == "PSH+B+M") & (boot.coeficiente != "intercepto")]
    b = sel[sel.remuestreo == "sitios"].set_index("coeficiente")
    bb = sel[sel.remuestreo == "bloques"].set_index("coeficiente")
    nombres = ["PSH", "B", "M"]
    y = np.arange(len(nombres))[::-1]
    for yi, c, color in zip(y, nombres, (GRIS, AZUL, NARANJA)):
        r, rb = b.loc[c], bb.loc[c]
        ax_b.plot([rb.efecto_1sd_ic_inf, rb.efecto_1sd_ic_sup], [yi - 0.12] * 2, color=color, lw=1,
                  ls=":")
        ax_b.plot([r.efecto_1sd_ic_inf, r.efecto_1sd_ic_sup], [yi, yi], color=color, lw=2)
        ax_b.plot(r.efecto_1sd, yi, "o", color=color, mec="k", mew=0.5, ms=6)
    ax_b.text(0.03, 0.03, "solid: sites resampled\ndotted: climate blocks resampled",
              transform=ax_b.transAxes, fontsize=6.5, va="bottom")
    ax_b.axvline(0, color="k", lw=0.8)
    ax_b.set_yticks(y, ["PSH", "$B$", "$M$"])
    ax_b.set_ylim(-0.6, len(nombres) - 0.4)
    formatear_eje(ax_b, xlabel="Effect of +1 SD on $\\ln\\kappa$", menores_y=NullLocator())
    ax_b.tick_params(axis="y", which="both", right=False)
    etiqueta_panel(ax_b, "(b)", debajo=0.50)

    ancho = 0.35
    for k, (var, color) in enumerate((("B", AZUL), ("M", NARANJA))):
        t = efecto[efecto.variable == var].sort_values("percentil")
        x = np.arange(len(t)) + (k - 0.5) * ancho
        ax_c.bar(x, t.mwh_de_5_a_1_pct / DEMANDA_MW, width=ancho, color=color, edgecolor="k", lw=0.4,
                 label=f"${var}$ varies")
    ax_c.set_xticks(np.arange(3), ["P10", "P50", "P90"])
    formatear_eje(ax_c, xlabel="Percentile of $B$ or $M$ (PSH at median)",
                  ylabel="$E/D$ from 5 % to 1 % (h)", menores_x=NullLocator())
    ax_c.tick_params(axis="x", which="both", top=False)
    ax_c.legend(loc="upper left", fontsize=7.5)
    etiqueta_panel(ax_c, "(c)", debajo=0.50)
    guardar(fig, "fig_efecto_BM")


if __name__ == "__main__":
    main()
