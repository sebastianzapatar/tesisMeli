"""Figura 3.9 — Cómo se construyen las series de días barajados.

Para un sitio real (el de PSH mediana) se muestran los días de déficit de
dos años en tres versiones de la misma serie:
  * real;
  * días barajados dentro de cada mes (conserva estacionalidad y años secos);
  * todos los días barajados (solo conserva la distribución de los días).
Las tres tienen exactamente la misma PSH y los mismos días; solo cambia el
orden. A la derecha, B calculada sobre los 27 años de cada versión.

Datos: serie real del sitio + intermitencia.sinteticas.barajar_dias.
Salida: capitulo_3/Series_barajadas.pdf
Qué editar: SITIO (None = el de PSH mediana), ANIOS_MOSTRADOS, SEMILLA.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import comun_tesis  # noqa: E402,F401  (agrega src/ al path)
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import estilo  # noqa: E402
from estilo import guardar  # noqa: E402
from intermitencia import Config, io_datos  # noqa: E402
from intermitencia.eventos import eventos_diarios_centrados, metricas_intermitencia, serie_diaria_deficit  # noqa: E402
from intermitencia.pv import GHI_STC  # noqa: E402
from intermitencia.sinteticas import barajar_dias  # noqa: E402

SITIO = None
ANIOS_MOSTRADOS = (2015, 2016)       # incluye un año El Niño
SEMILLA = 7
VERSIONES = [("real", "Observed series", "#2A78D6"),
             ("mes", "Days shuffled within each month", "#EB6834"),
             ("todo", "All days shuffled", "#6b6b6b")]
ALTO_FRANJA, SEP = 0.42, 0.36


def main() -> None:
    estilo.aplicar_estilo()
    cfg = Config.cargar()
    ghi = io_datos.leer_series_horarias(cfg.rutas.series_51, cfg.rutas.cache)
    psh = ghi.sum() / 1000.0 / (len(ghi) / 24)
    sitio = SITIO or psh.sub(psh.median()).abs().idxmin()
    g = ghi[sitio]
    p_ref = float(cfg.sustituto["planta_referencia_mw"])
    rng = np.random.default_rng(SEMILLA)

    alto = 0.10 + len(VERSIONES) * (ALTO_FRANJA + SEP) + 0.45
    fig = plt.figure(figsize=(estilo.ANCHO, alto))
    ancho = estilo.ANCHO - estilo.MARGEN_IZQ - 0.95
    ax = fig.add_axes([estilo.MARGEN_IZQ / estilo.ANCHO, 0.45 / alto, ancho / estilo.ANCHO,
                       (alto - 0.45 - 0.12) / alto])
    for k, (amb, nombre, color) in enumerate(VERSIONES):
        serie = g if amb == "real" else barajar_dias(g, rng, amb)
        bal = serie * p_ref * cfg.planta.performance_ratio / GHI_STC - cfg.demanda_mw
        x = eventos_diarios_centrados(bal)
        b = metricas_intermitencia(x, min_eventos=cfg.intermitencia.min_eventos)["B"]
        fechas = serie_diaria_deficit(bal).index
        sel = np.isin(fechas.year, ANIOS_MOSTRADOS)
        ev = np.flatnonzero(x[sel] < 0)          # x < 0  <=>  d_j > media
        y = (len(VERSIONES) - 1 - k) * (ALTO_FRANJA + SEP)
        n = int(sel.sum())
        ax.broken_barh([(j, 1) for j in ev], (y, ALTO_FRANJA), facecolors=color, edgecolors="none")
        ax.broken_barh([(0, n)], (y, ALTO_FRANJA), facecolors="none", edgecolors="#c9c9c9", lw=0.5)
        ax.text(0, y + ALTO_FRANJA + 0.05, nombre, fontsize=8.5, color=color, va="bottom")
        ax.text(n + 8, y + ALTO_FRANJA / 2, rf"$B={b:.2f}$", fontsize=8.5, color=color, va="center")
    ax.set_xlim(0, n)
    ax.set_ylim(-0.05, len(VERSIONES) * (ALTO_FRANJA + SEP))
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.grid(False)
    inicio_mes = [j for j, f in enumerate(fechas[sel]) if f.day == 1 and f.month in (1, 4, 7, 10)]
    ax.set_xticks(inicio_mes + [n])
    ax.set_xticklabels([fechas[sel][j].strftime("%b %Y") if fechas[sel][j].month == 1
                        else fechas[sel][j].strftime("%b") for j in inicio_mes] + [""], fontsize=8)
    ax.tick_params(axis="x", direction="in", top=False)
    print(f"  sitio: {sitio}  PSH = {psh[sitio]:.2f} h/day")
    guardar(fig, "capitulo_3", "Series_barajadas")


if __name__ == "__main__":
    main()
