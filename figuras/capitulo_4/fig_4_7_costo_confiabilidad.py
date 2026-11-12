"""Figura 4.7 — Cuánto cuesta cada punto de confiabilidad (resultado).

(a) Costo de cada punto porcentual de LPSP en los tramos 5→2 % y 2→1 %:
    aumento del costo anual de inversión y O&M (CAPEX anualizado + O&M,
    sin el VoLL) dividido por los puntos ganados, por sitio. Gris: planta
    común de 150 MW y solo batería. Azul: planta y batería ajustadas juntas.
(b) Costo marginal de la ENS evitada con batería, c_E·kappa/(LPSP·D),
    frente a la meta: mediana y rango intercuartílico de los 51 sitios.
    La línea horizontal es el VoLL. Por encima de ella, cada MWh evitado
    con batería cuesta más que lo que vale.
(c) Sustitución planta–batería a confiabilidad constante para el sitio
    de kappa mediano: batería mínima para cada potencia FV, con el punto
    de mínimo costo marcado.
(d) Potencia FV del sistema de mínimo costo por meta (distribución).

Datos: 10_costo_planta_comun.xlsx, 10_minimo_costo.xlsx, 10_sitios.xlsx,
10_sustitucion_planta_bateria.csv.gz. Salida: capitulo_4/fig_costo_confiabilidad.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # figuras/

import json

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FixedLocator, LogLocator, NullFormatter, NullLocator

from resultados import (AZUL, CFG, GRIS, NARANJA, RESULTADOS, VERDE, etiqueta_panel, formatear_eje,
                   guardar, leer_resultado, rejilla)

METAS = [(0.05, VERDE), (0.02, AZUL), (0.01, NARANJA)]
pct = lambda v, _: f"{v * 100:g}%"


def main() -> None:
    costos = leer_resultado("10_costo_planta_comun.xlsx")
    minimos = leer_resultado("10_minimo_costo.xlsx")
    sitios = leer_resultado("10_sitios.xlsx").set_index("Serie")
    sust = leer_resultado("10_sustitucion_planta_bateria.csv.gz")
    c_e = json.loads((RESULTADOS / "10_resumen.json").read_text())["c_E_usd_mwh_anio"]
    D = CFG.demanda_mw
    d_anual = D * 8760.0
    voll = CFG.economia.voll_usd_mwh

    fig, ejes = rejilla(2, 2, alto_ej=1.75, sep_v=0.85, y0=0.75, arriba=0.45)
    (ax_a, ax_b), (ax_c, ax_d) = ejes

    # (a) costo neto de cada punto porcentual, por tramo y por estrategia
    tramos = [(0.05, 0.02), (0.02, 0.01)]

    def por_pp(tabla, col_meta, col_costo):
        t = tabla.pivot_table(index="Serie", columns=col_meta, values=col_costo)
        return [(t[lo_] - t[hi_]) / (100 * (hi_ - lo_))
                for hi_, lo_ in tramos]

    # kUSD/año por MW de demanda firme
    escala = 1000.0 / CFG.demanda_mw
    comun_pp = [x * escala for x in por_pp(costos, "meta_lpsp", "costo_bess_musd_anio")]
    minimo_pp = [x * escala for x in por_pp(minimos, "objetivo_lpsp", "costo_capex_opex_musd")]
    pos_c, pos_m = [0.8, 2.8], [1.2, 3.2]
    for datos, pos, color, nombre in ((comun_pp, pos_c, GRIS, "Common plant (7.5$D$) + BESS"),
                                      (minimo_pp, pos_m, AZUL, "Least-cost PV + BESS")):
        bp = ax_a.boxplot([d.dropna() for d in datos], positions=pos, widths=0.35,
                          patch_artist=True, medianprops=dict(color="k"), flierprops=dict(ms=3))
        for caja in bp["boxes"]:
            caja.set_facecolor(color)
            caja.set_alpha(0.6)
        ax_a.plot([], [], "s", color=color, alpha=0.6, label=nombre)
    ax_a.set_yscale("log")
    ax_a.set_xticks([1, 3], ["5 % → 2 %", "2 % → 1 %"])
    formatear_eje(ax_a, xlabel="Reliability step", ylabel="Cost per point (kUSD/yr per MW)",
                  menores_x=NullLocator(), menores_y=LogLocator(subs="auto"))
    ax_a.tick_params(axis="x", which="both", top=False)
    fig.legend(*ax_a.get_legend_handles_labels(), loc="upper center", ncol=2, fontsize=7.5,
               bbox_to_anchor=(0.5, 1.0))
    etiqueta_panel(ax_a, "(a)", debajo=0.50)

    # (b) costo marginal frente a la meta, con el VoLL
    lp = np.logspace(np.log10(0.10), np.log10(0.005), 60)
    k = sitios.kappa_mwh.dropna().to_numpy()
    mc = c_e * k[:, None] / (lp[None, :] * d_anual)
    q25, q50, q75 = np.percentile(mc, [25, 50, 75], axis=0)
    ax_b.fill_between(lp, q25, q75, color=AZUL, alpha=0.25, lw=0)
    ax_b.plot(lp, q50, color=AZUL, lw=1.6)
    ax_b.axhline(voll, color=NARANJA, lw=1.2, ls="--")
    ax_b.text(0.0056, voll * 1.15, f"VoLL = {voll:.0f} USD/MWh", color=NARANJA, fontsize=7.5,
              ha="right", va="bottom")
    ax_b.set_xscale("log")
    ax_b.set_yscale("log")
    ax_b.set_xlim(0.10, 0.005)
    ax_b.xaxis.set_major_locator(FixedLocator([0.1, 0.05, 0.02, 0.01, 0.005]))
    ax_b.xaxis.set_major_formatter(plt.FuncFormatter(pct))
    ax_b.xaxis.set_minor_formatter(NullFormatter())
    formatear_eje(ax_b, xlabel="Reliability target LPSP$^*$",
                  ylabel="Marginal cost (USD/MWh ENS)",
                  menores_x=LogLocator(subs="auto"), menores_y=LogLocator(subs="auto"))
    etiqueta_panel(ax_b, "(b)", debajo=0.50)

    # (c) sustitución planta-batería, sitio de kappa mediano
    s_med = (sitios.kappa_mwh - sitios.kappa_mwh.median()).abs().idxmin()
    for meta, color in METAS:
        t = sust[(sust.Serie == s_med) & (sust.meta_lpsp == meta) & sust.alcanzable]
        ax_c.plot(t.e_bess_mwh / D, t.p_pv_mw / D, color=color, lw=1.4, label=f"{meta:.0%}")
        m = minimos[(minimos.Serie == s_med) & (minimos.objetivo_lpsp == meta)].iloc[0]
        ax_c.plot(m.e_bess_mwh / D, m.p_pv_mw / D, marker="*", ms=9, color=color, mec="k", mew=0.5)
    ax_c.axhline(float(CFG.sustituto["planta_referencia_mw"]) / D, color=GRIS, lw=0.8, ls="-.")
    ax_c.set_xscale("log")
    ax_c.set_xlim(10, 1000)
    ax_c.set_ylim(5, 20)
    formatear_eje(ax_c, xlabel="BESS capacity $E/D$ (h)", ylabel="PV power $P_{\\mathrm{PV}}/D$",
                  menores_x=LogLocator(subs="auto"))
    ax_c.set_title(f"{s_med} (median $\\kappa$)", fontsize=8.5)
    ax_c.legend(loc="upper right", fontsize=7, title="LPSP$^*$", title_fontsize=7)
    etiqueta_panel(ax_c, "(c)", debajo=0.50)

    # (d) potencia FV de mínimo costo por meta
    datos = [minimos[minimos.objetivo_lpsp == m].p_pv_mw.dropna() / D for m, _ in METAS]
    bp = ax_d.boxplot(datos, positions=[1, 2, 3], widths=0.5, patch_artist=True,
                      medianprops=dict(color="k"))
    for caja, (_, color) in zip(bp["boxes"], METAS):
        caja.set_facecolor(color)
        caja.set_alpha(0.6)
    ax_d.set_xticks([1, 2, 3], ["5%", "2%", "1%"])
    formatear_eje(ax_d, xlabel="Reliability target LPSP$^*$", ylabel="Least-cost $P_{\\mathrm{PV}}/D$",
                  menores_x=NullLocator())
    etiqueta_panel(ax_d, "(d)", debajo=0.50)
    guardar(fig, "capitulo_4", "fig_costo_confiabilidad")


if __name__ == "__main__":
    main()
