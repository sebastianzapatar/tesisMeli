"""Figura 4.6 — Aplicación del modelo a cinco zonas que no se usaron para ajustarlo.

(a) kappa simulado frente a kappa predicho por el modelo con solo PSH (círculos
    vacíos) y con PSH + B (círculos llenos), con los coeficientes del paso 11
    sin reajustar. La línea es la igualdad; las flechas muestran cuánto se
    acerca cada zona al agregar B.
(b) Capacidad necesaria de cada zona para LPSP = 5, 2 y 1 %, simulada.

Datos: codigo/resultados/articulo2/15_zonas.xlsx (paso 15 del pipeline). NO simula.
Salida: capitulo_4/Zonas_aplicacion.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # figuras/

import numpy as np  # noqa: E402
from matplotlib.ticker import NullLocator  # noqa: E402

from resultados import (AZUL, GRIS, NARANJA, VERDE, etiqueta_panel, formatear_eje,  # noqa: E402
                        guardar, leer_resultado, rejilla)

METAS = [("E_5%_h", VERDE, "5 %"), ("E_2%_h", AZUL, "2 %"), ("E_1%_h", NARANJA, "1 %")]


def rmse(e):
    return float(np.sqrt(np.mean(np.asarray(e) ** 2)))


def main() -> None:
    z = leer_resultado("15_zonas.xlsx").sort_values("PSH", ascending=False)
    fig, ejes = rejilla(1, 2, alto_ej=2.3, y0=0.85, arriba=0.15, sep_h=0.85)
    ax_a, ax_b = ejes[0]
    # panel (a) cuadrado y estrecho; (b) más ancho para los nombres de las zonas
    pa, pb = ax_a.get_position(), ax_b.get_position()
    ancho_a = 1.85 / 6.3
    ax_a.set_position([pa.x0, pa.y0, ancho_a, pa.height])
    x0b = pa.x0 + ancho_a + 0.75 / 6.3
    ax_b.set_position([x0b, pb.y0, pb.x1 - x0b, pb.height])

    lim = [3, 100]
    ax_a.plot(lim, lim, color=GRIS, lw=0.8)
    for _, r in z.iterrows():
        ax_a.annotate("", xy=(r["kappa_pred_PSH+B_h"], r.kappa_h), xytext=(r.kappa_pred_PSH_h, r.kappa_h),
                      arrowprops=dict(arrowstyle="->", color=GRIS, lw=0.7))
        izq = min(r.kappa_pred_PSH_h, r["kappa_pred_PSH+B_h"])
        der = max(r.kappa_pred_PSH_h, r["kappa_pred_PSH+B_h"])
        if r.Zona in ("Suroccidente", "Oriente"):   # a la derecha, para no chocar
            ax_a.annotate(r.Zona, (der, r.kappa_h), xytext=(6, 0), textcoords="offset points",
                          fontsize=7, va="center", ha="left")
        elif r.Zona == "Caribe":          # debajo, junto al eje
            ax_a.annotate(r.Zona, (izq, r.kappa_h), xytext=(2, -10), textcoords="offset points",
                          fontsize=7, va="center", ha="center")
        else:
            ax_a.annotate(r.Zona, (izq, r.kappa_h), xytext=(-6, 0), textcoords="offset points",
                          fontsize=7, va="center", ha="right")
    ax_a.scatter(z.kappa_pred_PSH_h, z.kappa_h, s=24, facecolor="white", edgecolor=GRIS, lw=1, zorder=3,
                 label=f"PSH (RMSE ln$\\kappa$ = {rmse(z.error_ln_PSH):.2f})")
    ax_a.scatter(z["kappa_pred_PSH+B_h"], z.kappa_h, s=24, color=AZUL, edgecolor="k", lw=0.4, zorder=4,
                 label=f"PSH + B (RMSE = {rmse(z['error_ln_PSH+B']):.2f})")
    ax_a.set_xscale("log")
    ax_a.set_yscale("log")
    ax_a.set_xlim(lim)
    ax_a.set_ylim(lim)
    formatear_eje(ax_a, xlabel=r"Predicted $\kappa$ (h)", ylabel=r"Simulated $\kappa$ (h)",
                  menores_x=NullLocator(), menores_y=NullLocator())
    ax_a.legend(loc="upper left", fontsize=6.5, handletextpad=0.2)
    etiqueta_panel(ax_a, "(a)", debajo=0.62)

    x = np.arange(len(z))
    w = 0.26
    for k, (col, color, nombre) in enumerate(METAS):
        ax_b.bar(x + (k - 1) * w, z[col], width=w, color=color, edgecolor="k", lw=0.3, label=nombre)
    ax_b.set_xticks(x, [f"{n}\n{p:.2f}" for n, p in zip(z.Zona, z.PSH)], fontsize=6.5)
    formatear_eje(ax_b, xlabel="Zone and PSH (h/day)", ylabel="Required storage $E^*$ (h)",
                  menores_x=NullLocator())
    ax_b.legend(title="LPSP target", fontsize=7, title_fontsize=7, loc="upper left")
    etiqueta_panel(ax_b, "(b)", debajo=0.62)
    guardar(fig, "capitulo_4", "Zonas_aplicacion")


if __name__ == "__main__":
    main()
