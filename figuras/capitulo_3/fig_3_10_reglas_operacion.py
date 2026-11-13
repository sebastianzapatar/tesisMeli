"""Figura 3.10 — Reglas de operación del BESS durante una racha de días de déficit.

(a) Estado de carga con despacho directo (R1), reserva mínima de SOC (R2) y
    ventana de descarga de 18:00 a 22:00 (R3), para la misma batería.
    Los días de evento de déficit están sombreados.
(b) Energía no suministrada acumulada en la misma ventana.

Usa el motor de ``intermitencia.reglas_operacion`` (el mismo del paso 08 del
pipeline). Datos: sitio sintético "Clustered" de sitios_ilustrativos.py (ilustrativo).
Salida: capitulo_3/fig_reglas_operacion.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # figuras/

import matplotlib.pyplot as plt
import numpy as np

from sitios_ilustrativos import (AZUL, BESS, DEMANDA_MW, GRIS, NARANJA, SITIOS, VERDE, balance_mw, estilo,
                   etiqueta_panel, eventos_diarios, formatear_eje, ghi_sintetica, guardar)
from intermitencia.reglas_operacion import simular_regla

SITIO = SITIOS[2]           # "Clustered"
E_MWH = 1000.0              # capacidad fija del BESS para la comparación
DIA_INICIO, N_DIAS = 1145, 21
SOC_RES = 0.40
VENTANA = (18, 22)
# (regla, etiqueta, color, estilo de línea, grosor): R1 va más gruesa debajo
# para que se vea cuando coincide con R2.
REGLAS = [("R1", "R1: direct dispatch", AZUL, "-", 2.4),
          ("R2", f"R2: SOC reserve ({SOC_RES:.0%})", NARANJA, "-", 1.2),
          ("R3", f"R3: discharge window {VENTANA[0]}:00–{VENTANA[1]}:00", VERDE, "--", 1.2)]


def main() -> None:
    estilo.aplicar_estilo()
    bal = balance_mw(ghi_sintetica(SITIO, anios=10))
    ev = eventos_diarios(bal)
    d = ev["deficit_diario"]

    comunes = dict(demanda_mw=DEMANDA_MW, eficiencia_carga=BESS.eff_carga,
                   eficiencia_descarga=BESS.eff_descarga, soc_min=BESS.soc_min_frac,
                   soc_max=BESS.soc_max_frac, soc_inicial=BESS.soc_inicial_frac,
                   soc_res=SOC_RES, ventana_horaria=VENTANA)
    res = {r: simular_regla(bal, E_MWH, E_MWH / BESS.duracion_h, r, **comunes) for r, *_ in REGLAS}

    alto_a, alto_b, sep, y_b = 1.65, 1.35, 0.62, 0.95
    alto = y_b + alto_b + sep + alto_a + 0.50
    fig = plt.figure(figsize=(estilo.ANCHO, alto))
    w = (estilo.ANCHO - estilo.MARGEN_IZQ - estilo.MARGEN_DER) / estilo.ANCHO
    x0 = estilo.MARGEN_IZQ / estilo.ANCHO
    ax_a = fig.add_axes([x0, (y_b + alto_b + sep) / alto, w, alto_a / alto])
    ax_b = fig.add_axes([x0, y_b / alto, w, alto_b / alto], sharex=ax_a)

    h0, n = DIA_INICIO * 24, N_DIAS * 24
    t = np.arange(n) / 24.0
    for k in range(N_DIAS):
        if d[DIA_INICIO + k] > d.mean():
            for ax in (ax_a, ax_b):
                ax.axvspan(k, k + 1, color=AZUL, alpha=0.08, lw=0)

    for r, etiqueta, color, ls, lw in REGLAS:
        x = res[r]
        ax_a.plot(t, 100 * x.soc[h0:h0 + n], color=color, lw=lw * 0.8, ls=ls, label=etiqueta)
        ax_b.plot(t, np.cumsum(x.ens_mwh[h0:h0 + n]) / DEMANDA_MW, color=color, lw=lw, ls=ls)
        print(f"  {r}: LPSP = {x.lpsp:.4f}  ciclos eq. = {x.ciclos_equivalentes:.0f}  "
              f"vertido = {x.frac_vertida:.3f}")
    ax_a.axhline(100 * SOC_RES, color=NARANJA, lw=0.8, ls=":")
    ax_a.axhline(100 * BESS.soc_min_frac, color=GRIS, lw=0.8, ls=":")
    ax_a.set_ylim(0, 105)
    ax_a.set_xlim(0, N_DIAS)
    formatear_eje(ax_a, ylabel="State of charge (%)")
    ax_a.tick_params(labelbottom=False)
    ax_a.axvspan(0, 0, color=AZUL, alpha=0.08, lw=0, label="Deficit event day")
    ax_a.legend(loc="upper center", bbox_to_anchor=(0.5, 1.33), ncol=2, fontsize=8)
    etiqueta_panel(ax_a, "(a)", debajo=0.18)

    formatear_eje(ax_b, xlabel="Day", ylabel="Cumulative ENS / $D$ (h)")
    etiqueta_panel(ax_b, "(b)", debajo=0.55)
    guardar(fig, "capitulo_3", "fig_reglas_operacion")


if __name__ == "__main__":
    main()
