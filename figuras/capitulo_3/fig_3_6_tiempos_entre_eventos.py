"""Figura 3.6 — Qué miden B y M sobre los tiempos entre eventos de déficit.

(a) Función de supervivencia (CCDF) de tau para cuatro sitios con la misma
    PSH y distinto agrupamiento de días nublados. Inspirada en la Fig. 10 de
    Kebede et al. (2021), que compara distribuciones de tiempos entre fallas.
(b) Mapa de retorno tau_k frente a tau_{k+1}: la nube se alinea con la
    diagonal cuando hay memoria (M > 0). Inspirada en la Fig. 5 de Kebede.
(c) Plano B–M: los sitios de (a) y un conjunto de sitios sintéticos que
    barren el agrupamiento.

Datos: sitios sintéticos de sitios_ilustrativos.py (ilustrativos, 27 años).
Salida: capitulo_3/fig_tiempos_entre_eventos.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # figuras/

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import LogLocator

from sitios_ilustrativos import (COLORES_SITIOS, GRIS, SITIOS, Sitio, balance_mw, estilo, etiqueta_panel,
                   eventos_diarios, formatear_eje, ghi_sintetica, guardar)

ANIOS = 27


def ejes(fig, n: int, alto_fig: float, alto_ej: float, y0: float, sep: float = 0.72):
    ancho_util = estilo.ANCHO - estilo.MARGEN_IZQ - estilo.MARGEN_DER
    w = (ancho_util - sep * (n - 1)) / n
    return [fig.add_axes([(estilo.MARGEN_IZQ + i * (w + sep)) / estilo.ANCHO, y0 / alto_fig,
                          w / estilo.ANCHO, alto_ej / alto_fig]) for i in range(n)]


def main() -> None:
    estilo.aplicar_estilo()
    alto_ej, y0 = 1.85, 0.88
    alto = y0 + alto_ej + 0.45
    fig = plt.figure(figsize=(estilo.ANCHO, alto))
    ax_a, ax_b, ax_c = ejes(fig, 3, alto, alto_ej, y0)

    res = []
    for sitio, color in zip(SITIOS, COLORES_SITIOS):
        ev = eventos_diarios(balance_mw(ghi_sintetica(sitio, anios=ANIOS)))
        res.append(ev)
        tau = np.sort(ev["taus"])
        ccdf = 1.0 - np.arange(tau.size) / tau.size
        ax_a.step(tau, ccdf, where="post", color=color, lw=1.4,
                  label=f"{sitio.nombre}")

    ax_a.set_yscale("log")
    ax_a.set_xlim(0, 120)
    ax_a.set_ylim(1e-3, 1.2)
    formatear_eje(ax_a, xlabel="$\\tau$ (days)", ylabel="$P(\\tau_k \\geq \\tau)$", menores_y=LogLocator(subs="auto"))
    etiqueta_panel(ax_a, "(a)", debajo=0.45)

    # (b) mapa de retorno: independiente frente a fuertemente agrupado
    rng = np.random.default_rng(1)
    for i in (1, 3):
        t = res[i]["taus"]
        jit = lambda v: v * np.exp(rng.normal(0, 0.06, v.size))   # noqa: E731 (solo visual)
        ax_b.scatter(jit(t[:-1]), jit(t[1:]), s=3, alpha=0.35, color=COLORES_SITIOS[i], lw=0,
                     label=f"{SITIOS[i].nombre} ($M={res[i]['M']:+.2f}$)")
    ax_b.plot([1, 200], [1, 200], color="k", lw=0.7, ls="--")
    ax_b.set_xscale("log")
    ax_b.set_yscale("log")
    ax_b.set_xlim(1.5, 150)
    ax_b.set_ylim(1.5, 150)
    formatear_eje(ax_b, xlabel="$\\tau_k$ (days)", ylabel="$\\tau_{k+1}$ (days)", menores_x=LogLocator(subs="auto"), menores_y=LogLocator(subs="auto"))
    for k, i in enumerate((1, 3)):
        ax_b.text(0.04, 0.95 - 0.11 * k, f"$M={res[i]['M']:+.2f}$", transform=ax_b.transAxes,
                  color=COLORES_SITIOS[i], fontsize=8, va="top", fontweight="bold",
                  bbox=dict(fc="white", ec="none", pad=0.5))
    etiqueta_panel(ax_b, "(b)", debajo=0.45)

    # (c) plano B–M con un conjunto de sitios sintéticos
    bs, ms = [], []
    for k, (d, q) in enumerate([(d, q) for d in (0.0, 0.1, 0.18, 0.25, 0.29)
                                for q in (0.8, 0.9, 0.95, 0.98, 0.99)]):
        ev = eventos_diarios(balance_mw(ghi_sintetica(Sitio("e", delta=d, q=q), anios=ANIOS, semilla=100 + k)))
        bs.append(ev["B"])
        ms.append(ev["M"])
    ax_c.scatter(bs, ms, s=12, color="#bdbdbd", lw=0, zorder=4)
    for ev, sitio, color in zip(res, SITIOS, COLORES_SITIOS):
        ax_c.scatter(ev["B"], ev["M"], s=34, color=color, edgecolor="k", lw=0.5, zorder=5)
    ax_c.axhline(0, color=GRIS, lw=0.8)
    ax_c.axvline(0, color=GRIS, lw=0.8)
    ax_c.set_xlim(-1, 1)
    ax_c.set_ylim(-0.75, 0.75)
    ax_c.set_yticks([-0.5, 0.0, 0.5])
    ax_c.set_xticks([-1, -0.5, 0, 0.5, 1])
    caja = dict(fc="white", ec="none", pad=0.6)
    ax_c.text(-0.94, 0.70, "regular,\npersistent", fontsize=7, va="top", bbox=caja)
    ax_c.text(0.94, 0.70, "bursty,\npersistent", fontsize=7, va="top", ha="right", bbox=caja)
    ax_c.text(-0.94, -0.70, "regular,\nalternating", fontsize=7, va="bottom", bbox=caja)
    ax_c.text(0.94, -0.70, "bursty,\nalternating", fontsize=7, va="bottom", ha="right", bbox=caja)
    formatear_eje(ax_c, xlabel="Burstiness $B$", ylabel="Memory $M$")
    etiqueta_panel(ax_c, "(c)", debajo=0.45)

    fig.legend(*ax_a.get_legend_handles_labels(), loc="upper center", ncol=4,
               bbox_to_anchor=(0.5, 1.0), fontsize=8.5)
    guardar(fig, "capitulo_3", "fig_tiempos_entre_eventos")
    for sitio, ev in zip(SITIOS, res):
        print(f"  {sitio.nombre:18s} B = {ev['B']:+.3f}  M = {ev['M']:+.3f}  eventos = {ev['n_eventos']:.0f}")


if __name__ == "__main__":
    main()
