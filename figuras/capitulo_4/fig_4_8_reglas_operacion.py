"""Figura 4.8 — Resultados de las reglas de operación en los 51 sitios.

(a) LPSP que deja cada regla con la batería E* de R1, dividida por la de R1,
    para las metas de 5, 2 y 1 %: puntos = sitios, barra = mediana.
    R1 despacho directo; R2 reserva de 30 % del SOC; R3 descarga solo de
    18:00 a 22:00.
(b) Penalidad de R2 al 5 % frente a la burstiness B de cada sitio.
(c) Energía no servida con R1 frente a la del programa lineal con previsión
    perfecta, en las 306 ventanas de 60 días: coinciden (R1 es óptima).

Datos: codigo/resultados/articulo2/12_reglas.xlsx, 12_cota_lp.xlsx y
10_sitios.xlsx (paso 12 del pipeline). NO simula.
Salida: capitulo_4/Reglas_resultados.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # figuras/

import numpy as np  # noqa: E402
from matplotlib.ticker import NullLocator  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from resultados import (AZUL, GRIS, NARANJA, VERDE, etiqueta_panel, formatear_eje,  # noqa: E402
                        guardar, leer_resultado, rejilla)

METAS = [(0.05, "5 %"), (0.02, "2 %"), (0.01, "1 %")]
REGLAS = [("R2", AZUL, "R2 reserve"), ("R3", NARANJA, "R3 evening window")]


def main() -> None:
    r = leer_resultado("12_reglas.xlsx")
    lp = leer_resultado("12_cota_lp.xlsx")
    s = leer_resultado("10_sitios.xlsx").set_index("Serie")
    rng = np.random.default_rng(3)

    fig, ejes = rejilla(1, 3, alto_ej=1.85, y0=0.85, arriba=0.15, sep_h=0.80)
    ax_a, ax_b, ax_c = ejes[0]

    for k, (regla, color, nombre) in enumerate(REGLAS):
        for j, (meta, _) in enumerate(METAS):
            v = r[(r.regla == regla) & np.isclose(r.meta_lpsp, meta)].razon_lpsp_vs_R1
            xpos = j + (k - 0.5) * 0.34
            ax_a.scatter(xpos + rng.uniform(-0.08, 0.08, len(v)), v, s=5, color=color, alpha=0.6, lw=0)
            ax_a.plot([xpos - 0.13, xpos + 0.13], [v.median()] * 2, color="k", lw=1.4)
        ax_a.scatter([], [], s=12, color=color, label=nombre)
    ax_a.axhline(1, color=GRIS, lw=0.8, ls="--")
    ax_a.set_yscale("log")
    ax_a.set_xticks(range(len(METAS)), [m[1] for m in METAS])
    formatear_eje(ax_a, xlabel="LPSP target", ylabel="LPSP / LPSP of R1", menores_x=NullLocator(), menores_y=NullLocator())
    ax_a.legend(fontsize=6.5, loc="upper left", handletextpad=0.1)
    etiqueta_panel(ax_a, "(a)")

    g = r[(r.regla == "R2") & np.isclose(r.meta_lpsp, 0.05)].set_index("Serie")
    b = s.B.reindex(g.index)
    ax_b.scatter(b, g.razon_lpsp_vs_R1, s=14, color=AZUL, edgecolor="k", lw=0.3)
    rho = spearmanr(b, g.razon_lpsp_vs_R1).correlation
    ax_b.text(0.96, 0.25, f"$\\rho$ = {rho:.2f}", transform=ax_b.transAxes, ha="right", fontsize=7.5)
    formatear_eje(ax_b, xlabel="Burstiness $B$", ylabel="R2 penalty at 5 %")
    etiqueta_panel(ax_b, "(b)")

    lim = [0, max(lp.ens_R1_mwh.max(), lp.ens_lp_mwh.max()) * 1.05 / 1000]
    ax_c.plot(lim, lim, color=GRIS, lw=0.8)
    ax_c.scatter(lp.ens_lp_mwh / 1000, lp.ens_R1_mwh / 1000, s=8, color=VERDE, edgecolor="k", lw=0.2)
    ax_c.text(0.04, 0.95, f"{len(lp)} windows\nmax. gap {lp.brecha_mwh.abs().max():.0e} MWh",
              transform=ax_c.transAxes, va="top", fontsize=7)
    ax_c.set_xlim(lim)
    ax_c.set_ylim(lim)
    formatear_eje(ax_c, xlabel="ENS, LP optimum (GWh)", ylabel="ENS, R1 (GWh)")
    etiqueta_panel(ax_c, "(c)")
    guardar(fig, "capitulo_4", "Reglas_resultados")


if __name__ == "__main__":
    main()
