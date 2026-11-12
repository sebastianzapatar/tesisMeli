"""Figura 3.5 — Definición de los eventos de déficit a resolución diaria.

(a) Generación FV horaria frente a la demanda plana: con demanda constante,
    TODAS las noches son déficit, por eso los eventos no se definen hora a hora.
(b) Déficit diario d_j y su media: un día es evento cuando d_j > media.
    Los tiempos entre inicios de eventos consecutivos, tau_k, son la entrada
    de B y M. Estilo inspirado en la Fig. 8 de Kebede et al. (2021).

Datos: sitio sintético "Clustered" de sitios_ilustrativos.py (ilustrativo).
Salida: capitulo_3/fig_eventos_deficit.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # figuras/

import matplotlib.pyplot as plt
import numpy as np

from sitios_ilustrativos import (AZUL, DEMANDA_MW, GRIS, NARANJA, ROJO_SUAVE, SITIOS, SOLAR, SOLAR_LINEA,
                   balance_mw, estilo, etiqueta_panel, eventos_diarios, formatear_eje,
                   ghi_sintetica, guardar)

SITIO = SITIOS[2]          # "Clustered"
DIA_INICIO = 1140          # ventana mostrada (días desde el inicio de la serie)
N_DIAS = 45
DIAS_HORARIO = 12         # días mostrados en el panel (a)


def main() -> None:
    estilo.aplicar_estilo()
    ghi = ghi_sintetica(SITIO, anios=27)
    bal = balance_mw(ghi)
    ev = eventos_diarios(bal)
    d = ev["deficit_diario"]
    d_media = d.mean()

    alto_a, alto_b, sep = 1.55, 1.75, 0.70
    y_b = 1.05                       # espacio para la leyenda y la etiqueta (b)
    alto = y_b + alto_b + sep + alto_a + 0.45
    fig = plt.figure(figsize=(estilo.ANCHO, alto))
    ancho_ej = estilo.ANCHO - estilo.MARGEN_IZQ - estilo.MARGEN_DER
    y_a = y_b + alto_b + sep
    ax_a = fig.add_axes([estilo.MARGEN_IZQ / estilo.ANCHO, y_a / alto, ancho_ej / estilo.ANCHO, alto_a / alto])
    ax_b = fig.add_axes([estilo.MARGEN_IZQ / estilo.ANCHO, y_b / alto, ancho_ej / estilo.ANCHO, alto_b / alto])

    # ---------------- (a) horario -----------------------------------
    h0 = DIA_INICIO * 24
    t = np.arange(DIAS_HORARIO * 24) / 24.0
    p = (bal[h0:h0 + t.size] + DEMANDA_MW) / DEMANDA_MW      # múltiplo de D
    ax_a.fill_between(t, p, color=SOLAR, alpha=0.55, lw=0, step="mid", label="PV generation $P(t)$")
    ax_a.plot(t, p, color=SOLAR_LINEA, lw=0.9, drawstyle="steps-mid")
    ax_a.axhline(1.0, color="k", lw=1.2, ls="--", label="Demand $D$")
    ax_a.fill_between(t, p, 1.0, where=p < 1.0, color=ROJO_SUAVE, lw=0, step="mid",
                      label="Hourly deficit")
    ax_a.set_xlim(0, DIAS_HORARIO)
    ax_a.set_ylim(0, 1.08 * p.max())
    formatear_eje(ax_a, xlabel="Day", ylabel="Power ($\\times D$)")
    ax_a.axvspan(0, 0, color=AZUL, alpha=0.10, lw=0, label="Event day")
    ax_a.legend(loc="upper center", bbox_to_anchor=(0.5, 1.30), ncol=4, fontsize=8.5)
    etiqueta_panel(ax_a, "(a)", debajo=0.42)

    # ---------------- (b) diario -------------------------------------
    j = np.arange(DIA_INICIO, DIA_INICIO + N_DIAS)
    anom = (d[j] - d_media) / DEMANDA_MW      # anomalía del déficit diario [h de demanda]
    evento = anom > 0
    x = j - DIA_INICIO
    ax_b.bar(x[~evento], anom[~evento], width=0.8, color="#c9c9c9", label="Day without event")
    ax_b.bar(x[evento], anom[evento], width=0.8, color=AZUL, label="Deficit event ($d_j>\\bar d$)")
    ax_b.axhline(0, color="k", lw=0.8)

    inicios = [k for k in range(N_DIAS) if evento[k] and (k == 0 or not evento[k - 1])]
    y_tau = anom.max() * 1.18
    for k0, k1 in zip(inicios[:-1], inicios[1:]):
        ax_b.annotate("", xy=(k1, y_tau), xytext=(k0, y_tau),
                      arrowprops=dict(arrowstyle="<->", lw=0.8, color=GRIS, shrinkA=0, shrinkB=0))
        ax_b.text((k0 + k1) / 2, y_tau + 0.03 * (anom.max() - anom.min()), f"{k1 - k0}",
                  ha="center", va="bottom", fontsize=7.5)
    for k in inicios:
        ax_b.plot([k, k], [0, y_tau], color=GRIS, lw=0.6, ls=":")
    ax_b.text(N_DIAS - 0.6, y_tau, "$\\tau_k$ (days)", ha="right", va="center", fontsize=8,
              bbox=dict(fc="white", ec="none", pad=1))
    ax_b.set_xlim(-0.8, N_DIAS - 0.2)
    ax_b.set_ylim(anom.min() * 1.25, y_tau + 0.16 * (anom.max() - anom.min()))
    formatear_eje(ax_b, xlabel="Day", ylabel="$(d_j-\\bar d)/D$ (h)")
    ax_b.grid(axis="x", visible=False)
    ax_b.legend(loc="upper center", bbox_to_anchor=(0.5, -0.30), ncol=2, fontsize=8.5)
    etiqueta_panel(ax_b, "(b)", debajo=0.80)

    # Sombrea en (a) los días que son evento
    for k in range(DIAS_HORARIO):
        if d[DIA_INICIO + k] > d_media:
            ax_a.axvspan(k, k + 1, color=AZUL, alpha=0.10, lw=0)

    guardar(fig, "capitulo_3", "fig_eventos_deficit")
    print(f"  sitio {SITIO.nombre}: B = {ev['B']:+.3f}, M = {ev['M']:+.3f}, eventos = {ev['n_eventos']:.0f}")


if __name__ == "__main__":
    main()
