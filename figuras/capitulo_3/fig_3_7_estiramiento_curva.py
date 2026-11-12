"""Figura 3.7 — Cómo la intermitencia "estira" la curva capacidad–confiabilidad.

(a) LPSP frente a la capacidad del BESS (eje log) para cuatro sitios con la
    MISMA PSH y distinto agrupamiento de los días de déficit. En escala log
    cada curva es casi una recta, LPSP = L0·exp(-E/kappa): más agrupamiento
    (B y M mayores) => pendiente menor => kappa mayor => la curva se estira.
(b) La misma información leída al revés: capacidad necesaria E* para cada
    meta de LPSP. Como E* = kappa·ln(L0/LPSP*), kappa es la pendiente.
(c) Mismo agrupamiento, distinta PSH: el recurso desplaza la curva.
(d) kappa frente a B en un conjunto de sitios sintéticos, coloreados por M.

Inspirada en las curvas de confiabilidad de Kebede et al. (2021, Figs. 9, 11 y 13).
Datos: sitios sintéticos de sitios_ilustrativos.py (ilustrativos, NO resultados de las 51 series).
Salida: capitulo_3/fig_estiramiento_curva.pdf y figuras/capitulo_3/datos_estiramiento.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # figuras/

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FixedLocator, LogLocator, NullFormatter, ScalarFormatter

from sitios_ilustrativos import (AZUL, DEMANDA_MW, COLORES_SITIOS, GRIS, SALIDA, SITIOS, Sitio, balance_mw, estilo,
                   etiqueta_panel, eventos_diarios, formatear_eje, ghi_sintetica, guardar,
                   kappa_de, psh)

CAPACIDADES = np.arange(0.0, 6001.0, 75.0)      # MWh
CAPS_CONJUNTO = np.arange(0.0, 6001.0, 150.0)
META = 0.01                                      # LPSP* marcada en (a)
METAS = np.logspace(-1, -3, 25)                  # metas para el panel (b)
ANIOS = 27
ANIOS_CONJUNTO = 15


def e_para(lpsp_curva: np.ndarray, capacidades: np.ndarray, meta: float) -> float:
    """Capacidad mínima simulada que alcanza la meta (interpolación en log)."""
    ok = lpsp_curva > 0
    y = np.log(np.maximum(lpsp_curva, 1e-12))
    if lpsp_curva[ok].min() > meta:
        return np.nan
    i = np.argmax(lpsp_curva <= meta)
    if i == 0:
        return float(capacidades[0])
    y0, y1 = y[i - 1], y[i]
    return float(capacidades[i - 1] + (np.log(meta) - y0) / (y1 - y0) * (capacidades[i] - capacidades[i - 1]))


def main() -> None:
    estilo.aplicar_estilo()
    alto_ej, sep_v, y0, sep_h = 1.75, 0.95, 0.80, 0.85
    alto = y0 + 2 * alto_ej + sep_v + 0.55
    util = estilo.ANCHO - estilo.MARGEN_IZQ - estilo.MARGEN_DER - sep_h
    w = util / 2
    fig = plt.figure(figsize=(estilo.ANCHO, alto))

    def eje(col, fila, ancho=w):
        x = estilo.MARGEN_IZQ + col * (w + sep_h)
        y = y0 + (1 - fila) * (alto_ej + sep_v)
        return fig.add_axes([x / estilo.ANCHO, y / alto, ancho / estilo.ANCHO, alto_ej / alto])

    ax_a, ax_b, ax_c = eje(0, 0), eje(1, 0), eje(0, 1)
    ax_d = eje(1, 1, ancho=w - 0.55)
    filas = []

    # ---------------- (a) y (b): misma PSH, distinto agrupamiento ----------
    for sitio, color in zip(SITIOS, COLORES_SITIOS):
        g = ghi_sintetica(sitio, anios=ANIOS)
        b = balance_mw(g)
        ev = eventos_diarios(b)
        lpsp, aj = kappa_de(b, CAPACIDADES)
        ax_a.plot(CAPACIDADES / DEMANDA_MW, lpsp, color=color, lw=1.5,
                  label=f"{sitio.nombre} ($B={ev['B']:+.2f}$, $M={ev['M']:+.2f}$)")
        e_fit = np.linspace(aj.e_min, aj.e_max, 50)
        ax_a.plot(e_fit / DEMANDA_MW, aj.l0 * np.exp(-e_fit / aj.kappa_mwh), color="k", lw=0.7, ls="--")
        e_star = e_para(lpsp, CAPACIDADES, META)
        if np.isfinite(e_star):
            ax_a.plot([e_star / DEMANDA_MW], [META], marker="o", ms=4, color=color, mec="k", mew=0.5, zorder=5)

        e_sim = np.array([e_para(lpsp, CAPACIDADES, m) for m in METAS])
        ax_b.plot(METAS, e_sim / DEMANDA_MW, color=color, lw=1.5)
        ax_b.plot(METAS, aj.kappa_mwh / DEMANDA_MW * np.log(aj.l0 / METAS), color=color, lw=0.8, ls="--")
        ax_b.text(1.2e-3, aj.kappa_mwh / DEMANDA_MW * np.log(aj.l0 / 1.2e-3), f"$\\kappa$={aj.kappa_mwh / DEMANDA_MW:.1f} h",
                  color=color, fontsize=7.5, va="bottom", ha="right")

        filas.append(dict(panel="a-b", sitio=sitio.nombre, PSH=psh(g), B=ev["B"], M=ev["M"],
                          kappa_mwh=aj.kappa_mwh, L0=aj.l0, r2=aj.r2, E_1pct_sim_mwh=e_star,
                          E_1pct_exp_mwh=aj.capacidad_para(META)))

    ax_a.axhline(META, color=GRIS, lw=0.8, ls=":")
    ax_a.set_yscale("log")
    ax_a.set_ylim(1e-4, 1)
    ax_a.set_xlim(0, CAPACIDADES[-1] / DEMANDA_MW)
    ax_a.set_xticks([0, 100, 200, 300])
    formatear_eje(ax_a, xlabel="BESS capacity $E/D$ (h)", ylabel="LPSP", menores_y=LogLocator(subs="auto"))
    fig.legend(*ax_a.get_legend_handles_labels(), loc="upper center", ncol=2, fontsize=7.5,
               bbox_to_anchor=(0.5, 1.0), columnspacing=1.2)
    etiqueta_panel(ax_a, "(a)", debajo=0.45)

    ax_b.set_xscale("log")
    ax_b.set_xlim(0.1, 1e-3)                     # metas más exigentes a la derecha
    ax_b.set_ylim(0, 300)
    ax_b.xaxis.set_major_locator(FixedLocator([0.1, 0.01, 0.001]))
    ax_b.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:g}%"))
    formatear_eje(ax_b, xlabel="Reliability target LPSP$^*$", ylabel="Required $E^*/D$ (h)",
                  menores_x=LogLocator(subs="auto"))
    ax_b.xaxis.set_minor_formatter(NullFormatter())
    ax_b.text(0.04, 0.95, "solid: simulated\ndashed: $\\kappa\\,\\ln(L_0/\\mathrm{LPSP}^*)$",
              transform=ax_b.transAxes, fontsize=7, va="top")
    etiqueta_panel(ax_b, "(b)", debajo=0.45)

    # ---------------- (c) mismo agrupamiento, distinta PSH -----------------
    tonos = ["#9ecae1", AZUL, "#08306b"]
    for kt, tono in zip((0.70, 0.78, 0.86), tonos):
        sitio = Sitio(f"Clustered, kt={kt}", delta=0.25, q=0.97, kt_despejado=kt)
        g = ghi_sintetica(sitio, anios=ANIOS)
        b = balance_mw(g)
        ev = eventos_diarios(b)
        lpsp, aj = kappa_de(b, CAPACIDADES)
        ax_c.plot(CAPACIDADES / DEMANDA_MW, lpsp, color=tono, lw=1.5,
                  label=f"PSH = {psh(g):.1f} h, $\\kappa$ = {aj.kappa_mwh / DEMANDA_MW:.1f} h")
        filas.append(dict(panel="c", sitio=sitio.nombre, PSH=psh(g), B=ev["B"], M=ev["M"],
                          kappa_mwh=aj.kappa_mwh, L0=aj.l0, r2=aj.r2,
                          E_1pct_sim_mwh=e_para(lpsp, CAPACIDADES, META),
                          E_1pct_exp_mwh=aj.capacidad_para(META)))
    ax_c.axhline(META, color=GRIS, lw=0.8, ls=":")
    ax_c.set_yscale("log")
    ax_c.set_ylim(1e-4, 1)
    ax_c.set_xlim(0, CAPACIDADES[-1] / DEMANDA_MW)
    ax_c.set_xticks([0, 100, 200, 300])
    formatear_eje(ax_c, xlabel="BESS capacity $E/D$ (h)", ylabel="LPSP", menores_y=LogLocator(subs="auto"))
    ax_c.legend(loc="upper right", fontsize=7, handlelength=1.2)
    etiqueta_panel(ax_c, "(c)", debajo=0.45)

    # ---------------- (d) kappa frente a B, coloreado por M ----------------
    bs, ms, ks = [], [], []
    combinaciones = [(d, q) for d in (0.0, 0.1, 0.18, 0.25, 0.29) for q in (0.8, 0.9, 0.95, 0.98, 0.99)]
    for k, (d, q) in enumerate(combinaciones):
        g = ghi_sintetica(Sitio("e", delta=d, q=q), anios=ANIOS_CONJUNTO, semilla=100 + k)
        b = balance_mw(g)
        ev = eventos_diarios(b)
        _, aj = kappa_de(b, CAPS_CONJUNTO)
        bs.append(ev["B"])
        ms.append(ev["M"])
        ks.append(aj.kappa_mwh / DEMANDA_MW)
        filas.append(dict(panel="d", sitio=f"delta={d}, q={q}", PSH=psh(g), B=ev["B"], M=ev["M"],
                          kappa_mwh=aj.kappa_mwh, L0=aj.l0, r2=aj.r2, E_1pct_sim_mwh=np.nan,
                          E_1pct_exp_mwh=aj.capacidad_para(META)))
    sc = ax_d.scatter(bs, ks, c=ms, cmap="viridis", s=20, edgecolor="k", lw=0.3, vmin=-0.05, vmax=0.30)
    ax_d.set_yscale("log")
    ax_d.yaxis.set_major_locator(FixedLocator([10, 20, 50, 100]))
    ax_d.yaxis.set_major_formatter(ScalarFormatter())
    formatear_eje(ax_d, xlabel="Burstiness $B$", ylabel="$\\kappa/D$ (h)", menores_y=LogLocator(subs="auto"))
    ax_d.yaxis.set_minor_formatter(NullFormatter())
    pos = ax_d.get_position()
    cax = fig.add_axes([pos.x1 + 0.10 / estilo.ANCHO, pos.y0, 0.08 / estilo.ANCHO, pos.height])
    cb = fig.colorbar(sc, cax=cax)
    cb.set_label("Memory $M$", fontsize=8)
    cb.ax.tick_params(labelsize=7, direction="in")
    etiqueta_panel(ax_d, "(d)", debajo=0.45)

    guardar(fig, "capitulo_3", "fig_estiramiento_curva")
    df = pd.DataFrame(filas)
    df.to_csv(SALIDA / "capitulo_3" / "datos_estiramiento.csv", index=False)
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
