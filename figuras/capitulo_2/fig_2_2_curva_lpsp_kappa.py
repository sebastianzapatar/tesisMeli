"""Figura 2.2 — Forma de la curva capacidad–confiabilidad y significado de κ.

(a) LPSP(E) = L0·exp(−E/κ) en escala LINEAL, como la presentan Carlsson y
    Redner (2023): la LPSP cae rápido con las primeras horas de batería y
    cada hora adicional rinde cada vez menos. Se marca κ en la curva central
    (la LPSP cae a L0/e).
(b) Las mismas curvas en escala semilogarítmica: rectas de pendiente −1/κ;
    los puntos marcan la capacidad que cumple cada meta.
(c) Capacidad requerida E* = κ·ln(L0/LPSP*) en función de la meta: rectas
    cuya pendiente es κ.

Curvas ANALÍTICAS (no son resultados).
Salida: capitulo_2/Curva_LPSP_kappa.pdf
Editar L0, KAPPAS y METAS.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from matplotlib.ticker import LogLocator, NullLocator  # noqa: E402

from comun_tesis import AZUL, GRIS, NARANJA, VERDE, guardar  # noqa: E402
from estilo import etiqueta_panel, formatear_eje  # noqa: E402

L0 = 0.30                          # LPSP sin almacenamiento adicional
KAPPAS = [(6.0, VERDE), (12.0, AZUL), (24.0, NARANJA)]   # h de demanda
METAS = [0.05, 0.02, 0.01]
K_MARCA = 12.0                     # curva en la que se marca κ en el panel (a)


def main() -> None:
    import matplotlib.pyplot as plt
    import estilo
    estilo.aplicar_estilo()
    # Geometría en pulgadas: fila superior (a) a todo el ancho; fila inferior (b) y (c).
    alto_ej, abajo, entre, arriba, sep = 1.9, 0.95, 0.95, 0.15, 0.85
    alto = abajo + alto_ej + entre + alto_ej + arriba
    util = estilo.ANCHO - estilo.MARGEN_IZQ - estilo.MARGEN_DER
    w = (util - sep) / 2
    fig = plt.figure(figsize=(estilo.ANCHO, alto))
    y_sup = (abajo + alto_ej + entre) / alto
    a = fig.add_axes([estilo.MARGEN_IZQ / estilo.ANCHO, y_sup, util / estilo.ANCHO, alto_ej / alto])
    b, c = (fig.add_axes([(estilo.MARGEN_IZQ + i * (w + sep)) / estilo.ANCHO, abajo / alto,
                          w / estilo.ANCHO, alto_ej / alto]) for i in range(2))

    # (a) forma de la curva en escala lineal
    e = np.linspace(0, 140, 500)
    for k, color in KAPPAS:
        a.plot(e, L0 * np.exp(-e / k), color=color, lw=1.6, label=f"$\\kappa$ = {k:.0f} h")
    y_k = L0 / np.e
    a.plot([K_MARCA, K_MARCA], [0, y_k], color=GRIS, lw=0.9, ls="--")
    a.plot([0, K_MARCA], [y_k, y_k], color=GRIS, lw=0.9, ls="--")
    a.annotate("$E=\\kappa$: LPSP falls to $L_0/e$", (K_MARCA, y_k), xytext=(30, 0.20),
               fontsize=8, arrowprops=dict(arrowstyle="->", color=GRIS, lw=0.8))
    a.text(0.97, 0.80, "$\\mathrm{LPSP}(E)=L_0\\,e^{-E/\\kappa}$", transform=a.transAxes,
           ha="right", fontsize=10)
    a.set_xlim(0, 140)
    a.set_ylim(0, 0.32)
    formatear_eje(a, "Storage $E$ [h of demand]", "LPSP")
    a.legend(loc="center right", fontsize=8, handlelength=1.4)

    # (b) escala semilogarítmica
    for k, color in KAPPAS:
        b.plot(e, L0 * np.exp(-e / k), color=color)
        for meta in METAS:
            b.plot(k * np.log(L0 / meta), meta, "o", ms=3.5, color=color)
    for meta in METAS:
        b.axhline(meta, color=GRIS, lw=0.8, ls=":")
    b.set_yscale("log")
    b.set_ylim(0.004, 0.4)
    b.set_xlim(0, 140)
    formatear_eje(b, "Storage $E$ [h of demand]", "LPSP", menores_y=LogLocator(subs=np.arange(2, 10)))

    # (c) capacidad requerida frente a la meta
    for k, color in KAPPAS:
        metas = np.logspace(np.log10(0.005), np.log10(0.2), 50)
        c.plot(metas * 100, k * np.log(L0 / metas), color=color)
    c.set_xscale("log")
    c.set_xlim(20, 0.5)              # metas más exigentes a la derecha
    c.set_ylim(0, 130)
    c.set_xticks([20, 10, 5, 2, 1, 0.5], ["20", "10", "5", "2", "1", "0.5"])
    c.minorticks_off()
    formatear_eje(c, "Reliability target LPSP* [%]", "Required storage $E^*$ [h]",
                  menores_x=NullLocator())
    c.text(0.30, 0.80, "slope = $\\kappa$ per\nfactor $e$ of LPSP*", transform=c.transAxes,
           fontsize=8, ha="center")
    etiqueta_panel(a, "(a)", debajo=0.55)
    etiqueta_panel(b, "(b)", debajo=0.55)
    etiqueta_panel(c, "(c)", debajo=0.55)
    guardar(fig, "capitulo_2", "Curva_LPSP_kappa")


if __name__ == "__main__":
    main()
