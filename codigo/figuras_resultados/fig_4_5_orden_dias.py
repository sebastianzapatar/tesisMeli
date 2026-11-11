"""Figura 4.5 — Cuánto almacenamiento se debe al orden de los días (series barajadas).

(a) Capacidad para LPSP = 1 % de cada sitio con la serie observada, con los
    días barajados dentro de cada mes y con todos los días barajados
    (media de 6 realizaciones), sitios ordenados por PSH.
(b) Parte de la capacidad observada que se debe al orden de los días, por
    meta: estacionalidad y años (mes - todo) y rachas dentro del mes
    (observada - mes). Barras: mediana de los 51 sitios; puntos: cada sitio
    (orden total = observada - todo).

Datos: resultados/articulo2/14_sustitutos_sitios.xlsx (pipeline/14_series_sinteticas.py)
Salida: salida/capitulo_4/Orden_dias.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # comun.py (agrega codigo/src y figuras/)

import comun  # noqa: E402,F401
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FixedLocator, NullFormatter  # noqa: E402

import estilo  # noqa: E402
from comun import guardar  # noqa: E402
from estilo import etiqueta_panel, formatear_eje  # noqa: E402
from intermitencia import Config  # noqa: E402

COL = {"real": "#2A78D6", "mes": "#EB6834", "todo": "#6b6b6b"}
NOMBRE = {"real": "Observed", "mes": "Shuffled within month", "todo": "All days shuffled"}
METAS = ["5%", "2%", "1%"]
ALTO, Y0, SEP_H = 2.45, 0.62, 0.85


def main() -> None:
    estilo.aplicar_estilo()
    cfg = Config.cargar()
    d = pd.read_excel(cfg.rutas.salida / "articulo2" / "14_sustitutos_sitios.xlsx")
    m = d.groupby(["Serie", "tipo"]).mean(numeric_only=True).unstack("tipo")
    m = m.sort_values(("PSH", "real"), ascending=False)

    alto = Y0 + ALTO + 0.12
    fig = plt.figure(figsize=(estilo.ANCHO, alto))
    util = estilo.ANCHO - estilo.MARGEN_IZQ - estilo.MARGEN_DER
    wa = util * 0.60
    wb = util - wa - SEP_H
    ax = fig.add_axes([estilo.MARGEN_IZQ / estilo.ANCHO, Y0 / alto, wa / estilo.ANCHO, ALTO / alto])
    bx = fig.add_axes([(estilo.MARGEN_IZQ + wa + SEP_H) / estilo.ANCHO, Y0 / alto,
                       wb / estilo.ANCHO, ALTO / alto])

    # (a)
    x = np.arange(len(m)) + 1
    for t in ("todo", "mes", "real"):
        ax.semilogy(x, m[("E_1%_h", t)], "o", ms=3.2 if t == "real" else 2.6, color=COL[t],
                    markeredgewidth=0, label=NOMBRE[t], zorder=3 if t == "real" else 2)
    ax.set_xlim(0, len(m) + 1)
    ax.set_ylim(15, 4e4)
    ax.yaxis.set_major_locator(FixedLocator([20, 50, 100, 1000, 10000]))
    ax.set_yticklabels(["20", "50", "100", r"$10^3$", r"$10^4$"])
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks([1, 10, 20, 30, 40, 51])
    formatear_eje(ax, "Site (ordered by decreasing PSH)", r"$E^*$ for LPSP = 1% (h)")
    ax.legend(loc="upper left", fontsize=8, frameon=False, handletextpad=0.2)

    # (b)
    for k, meta in enumerate(METAS):
        c = f"E_{meta}_h"
        r, me, to = m[(c, "real")], m[(c, "mes")], m[(c, "todo")]
        est = 100 * ((me - to) / r).median()
        rac = 100 * ((r - me) / r).median()
        bx.bar(k, est, 0.55, color=COL["mes"], alpha=0.85, label="Season and year" if k == 0 else None)
        bx.bar(k, rac, 0.55, bottom=est, color=COL["real"], alpha=0.85,
               label="Runs in month" if k == 0 else None)
        tot = 100 * (r - to) / r
        jit = np.random.default_rng(k).uniform(-0.18, 0.18, len(tot))
        bx.plot(k + jit, tot.clip(upper=70), ".", ms=2.5, color="black", alpha=0.45)
    bx.set_xticks(range(len(METAS)))
    bx.set_xticklabels(METAS)
    bx.set_xlim(-0.6, len(METAS) - 0.4)
    bx.set_ylim(-2, 70)
    formatear_eje(bx, "LPSP target", r"Share of $E^*$ due to order (%)")
    bx.legend(loc="upper left", fontsize=7.5, frameon=False, handlelength=1.0)
    etiqueta_panel(ax, "(a)", debajo=0.48)
    etiqueta_panel(bx, "(b)", debajo=0.48)
    guardar(fig, "Orden_dias")


if __name__ == "__main__":
    main()
