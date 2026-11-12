"""Figura 3.4 — La muestra: recurso solar de los 51 sitios y de las 5 zonas.

Para cada sitio: PSH media (punto) y rango entre los percentiles 10 y 90 de
la PSH diaria (barra), ordenados de menor a mayor PSH media. Las 5 zonas de
aplicación se muestran a la derecha con un marcador distinto.

DATOS REALES:
  * 51 sitios: hoja "PSH diarias" de PSH_resultados.xlsx (rutas.psh_51)
  * 5 zonas:   GHI horaria de "5 series GHI juntas.xlsx" (rutas.series_5)

Salida: capitulo_3/Muestra_PSH.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import comun_tesis  # noqa: E402,F401  (agrega src/ al path)
from comun_tesis import AZUL, NARANJA, SOLAR_LINEA, guardar  # noqa: E402
from estilo import crear_figura, formatear_eje  # noqa: E402
from intermitencia import Config  # noqa: E402

P_BAJO, P_ALTO = 10, 90


def psh_51(cfg) -> pd.DataFrame:
    diarias = pd.read_excel(cfg.rutas.psh_51, sheet_name="PSH diarias", index_col=0)
    return pd.DataFrame({"media": diarias.mean(), "p_bajo": diarias.quantile(P_BAJO / 100),
                         "p_alto": diarias.quantile(P_ALTO / 100)})


def psh_zonas(cfg) -> pd.DataFrame:
    ghi = pd.read_excel(cfg.rutas.series_5)
    ghi = ghi.set_index(pd.to_datetime(ghi.pop("fecha")))
    diarias = ghi.resample("D").sum() / 1000.0
    diarias = diarias[~((diarias.index.month == 2) & (diarias.index.day == 29))]
    return pd.DataFrame({"media": diarias.mean(), "p_bajo": diarias.quantile(P_BAJO / 100),
                         "p_alto": diarias.quantile(P_ALTO / 100)})


def main() -> None:
    cfg = Config.cargar()
    sitios = psh_51(cfg).sort_values("media")
    zonas = psh_zonas(cfg).sort_values("media")
    print(f"  51 sitios: PSH media de {sitios.media.min():.2f} a {sitios.media.max():.2f} h/día")
    print(f"  5 zonas:   PSH media de {zonas.media.min():.2f} a {zonas.media.max():.2f} h/día")

    fig, ax = crear_figura(margen_inf=0.62, alto_ejes=2.2)
    x = np.arange(len(sitios))
    ax.vlines(x, sitios.p_bajo, sitios.p_alto, color=AZUL, lw=1.6, alpha=0.35)
    ax.plot(x, sitios.media, "o", ms=3.2, color=AZUL, label="51 substations (sample)")
    xz = len(sitios) + 2 + np.arange(len(zonas)) * 1.6
    ax.vlines(xz, zonas.p_bajo, zonas.p_alto, color=NARANJA, lw=1.6, alpha=0.35)
    ax.plot(xz, zonas.media, "D", ms=3.6, color=NARANJA, label="5 application zones")
    ax.axvline(len(sitios) + 0.5, color=SOLAR_LINEA, lw=0.8, ls=":")
    ax.set_xlim(-1.5, xz[-1] + 1.5)
    ax.set_xticks([])
    ax.set_ylim(0, 8)
    formatear_eje(ax, "Sites ordered by mean PSH", "Daily PSH [h/day]", menores_x=1)
    ax.tick_params(axis="x", which="both", bottom=False, top=False)
    ax.legend(loc="upper left", fontsize=8, handlelength=1.0, ncol=2)
    ax.text(0.99, 0.05, f"dots: mean; bars: P{P_BAJO}–P{P_ALTO} of daily PSH",
            transform=ax.transAxes, ha="right", fontsize=7.5)
    guardar(fig, "capitulo_3", "Muestra_PSH")


if __name__ == "__main__":
    main()
