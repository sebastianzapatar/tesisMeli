"""Figura 2.4 — Cómo la intermitencia cambia la curva capacidad–confiabilidad.

Dos sitios sintéticos con la MISMA PSH y el mismo número medio de días
nublados; solo cambia cómo se agrupan esos días:

(a) Los días de déficit de un año en cada sitio. Arriba, días independientes
    (B ~ 0); abajo, días agrupados en rachas (B > 0).
(b) Curva capacidad–confiabilidad de los dos sitios (LPSP en escala log).
    En esa escala cada curva es casi una recta, LPSP = L0·exp(-E/kappa):
    el agrupamiento aplana la recta (kappa mayor), y para la misma meta
    (1 %) el sitio agrupado necesita más almacenamiento (flecha).
(c) La misma información leída al revés: almacenamiento E* para cada meta.
    Como E* = kappa·ln(L0/LPSP*), kappa es la pendiente, y la diferencia
    entre los sitios crece a medida que la meta es más exigente.

Datos: sitios sintéticos de sitios_ilustrativos.py simulados con el MISMO
simulador del pipeline (27 años, planta común 7.5D, demanda plana). Son
ilustrativos: NO son resultados de las 51 series.

Salida: capitulo_2/Efecto_intermitencia_curva.pdf
Qué editar: SITIOS_FIG (parámetros de agrupamiento), META, ANIO_MOSTRADO,
textos de las anotaciones.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import comun_tesis  # noqa: E402,F401  (agrega src/ al path)
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.ticker import FixedLocator, LogLocator, NullFormatter  # noqa: E402

import estilo  # noqa: E402
from sitios_ilustrativos import (AZUL, DEMANDA_MW, GRIS, Sitio, balance_mw, eventos_diarios,  # noqa: E402
                   ghi_sintetica, kappa_de, psh)
from estilo import etiqueta_panel, formatear_eje, guardar  # noqa: E402

# ----------------------------------------------------------------- PARÁMETROS
SITIOS_FIG = [
    (Sitio("Scattered", delta=0.0), "Scattered", GRIS),
    (Sitio("Clustered", delta=0.25, q=0.97), "Clustered", AZUL),
]
ANIOS = 27
SEMILLA = 42
CAPACIDADES = np.arange(0.0, 6001.0, 75.0)     # MWh (se muestran en h de demanda)
META = 0.01                                     # LPSP* marcada en (b)
METAS = np.logspace(np.log10(0.10), np.log10(0.005), 30)
ANIO_MOSTRADO = 3                               # año que se dibuja en (a)

# ----------------------------------------------------------------- GEOMETRÍA (pulgadas)
ALTO_A, ALTO_BC = 1.10, 2.05
Y_BC, SEP_V, ARRIBA = 0.74, 0.80, 0.10
SEP_H = 0.80


def e_para(lpsp: np.ndarray, cap_h: np.ndarray, meta: float) -> float:
    """Capacidad [h] que alcanza la meta, interpolando en log(LPSP)."""
    y = np.log(np.maximum(lpsp, 1e-12))
    i = int(np.argmax(lpsp <= meta))
    if i == 0:
        return float(cap_h[0])
    x0, x1, y0, y1 = cap_h[i - 1], cap_h[i], y[i - 1], y[i]
    return float(x0 + (np.log(meta) - y0) * (x1 - x0) / (y1 - y0))


def main() -> None:
    estilo.aplicar_estilo()
    cap_h = CAPACIDADES / DEMANDA_MW
    datos = []
    for sitio, nombre, color in SITIOS_FIG:
        ghi = ghi_sintetica(sitio, anios=ANIOS, semilla=SEMILLA)
        bal = balance_mw(ghi)
        ev = eventos_diarios(bal)
        lpsp, aj = kappa_de(bal, CAPACIDADES)
        kappa_h = aj.kappa_mwh / DEMANDA_MW
        l0 = aj.l0
        datos.append(dict(nombre=nombre, color=color, psh=psh(ghi), ev=ev, lpsp=lpsp,
                          kappa=kappa_h, l0=l0, e_meta=e_para(lpsp, cap_h, META)))
        print(f"  {nombre}: PSH={psh(ghi):.2f}  B={ev['B']:.2f}  M={ev['M']:.2f}  "
              f"kappa={kappa_h:.1f} h  E*(1%)={datos[-1]['e_meta']:.1f} h")

    alto = Y_BC + ALTO_BC + SEP_V + ALTO_A + ARRIBA
    fig = plt.figure(figsize=(estilo.ANCHO, alto))
    ancho_util = estilo.ANCHO - estilo.MARGEN_IZQ - estilo.MARGEN_DER
    w = (ancho_util - SEP_H) / 2
    ax_a = fig.add_axes([estilo.MARGEN_IZQ / estilo.ANCHO, (Y_BC + ALTO_BC + SEP_V) / alto,
                         ancho_util / estilo.ANCHO, ALTO_A / alto])
    ax_b = fig.add_axes([estilo.MARGEN_IZQ / estilo.ANCHO, Y_BC / alto, w / estilo.ANCHO, ALTO_BC / alto])
    ax_c = fig.add_axes([(estilo.MARGEN_IZQ + w + SEP_H) / estilo.ANCHO, Y_BC / alto,
                         w / estilo.ANCHO, ALTO_BC / alto])

    # ---------------------------------------------------------- (a) días de déficit
    d0 = 365 * ANIO_MOSTRADO
    for k, dd in enumerate(datos):
        y = 1 - k
        d = dd["ev"]["deficit_diario"][d0:d0 + 365]
        media = dd["ev"]["deficit_diario"].mean()
        evento = d > media
        ax_a.broken_barh([(j, 1) for j in np.flatnonzero(evento)], (y - 0.32, 0.64),
                         facecolors=dd["color"], edgecolors="none")
        ax_a.broken_barh([(0, 365)], (y - 0.32, 0.64), facecolors="none",
                         edgecolors="#c9c9c9", linewidth=0.5)
        ax_a.text(0, y + 0.36, rf"{dd['nombre']} deficit days ($B={dd['ev']['B']:.2f}$)",
                  va="bottom", ha="left", fontsize=8.5, color=dd["color"])
    ax_a.set_xlim(0, 365)
    ax_a.set_ylim(-0.4, 1.75)
    ax_a.set_yticks([])
    ax_a.set_xticks([0, 60, 120, 180, 240, 300, 365])
    ax_a.tick_params(axis="y", length=0)
    ax_a.tick_params(axis="x", direction="in", top=False)
    for s in ("top", "right", "left"):
        ax_a.spines[s].set_visible(False)
    ax_a.grid(False)
    ax_a.set_xlabel("Day of the year")
    ax_a.text(365, 1.36, f"same PSH: {datos[0]['psh']:.2f} and {datos[1]['psh']:.2f} h/day",
              fontsize=8, color="black", va="bottom", ha="right")

    # ---------------------------------------------------------- (b) curvas LPSP(E)
    for dd in datos:
        ax_b.semilogy(cap_h, dd["lpsp"] * 100, "o", ms=2.6, color=dd["color"],
                      markeredgewidth=0, label=rf"{dd['nombre']}, $\kappa={dd['kappa']:.0f}$ h")
        e = np.linspace(0, cap_h.max(), 200)
        ax_b.semilogy(e, dd["l0"] * np.exp(-e / dd["kappa"]) * 100, "--", lw=0.9,
                      color=dd["color"])
    ax_b.axhline(META * 100, color="black", lw=0.7, ls=":")
    ax_b.text(cap_h.max() * 0.98, META * 100 * 0.8, "target 1 %", ha="right", va="top", fontsize=8)
    e1, e2 = datos[0]["e_meta"], datos[1]["e_meta"]
    for dd in datos:
        ax_b.plot([dd["e_meta"]] * 2, [0.05, META * 100], color=dd["color"], lw=0.8)
    ax_b.annotate("", xy=(e2, META * 100), xytext=(e1, META * 100),
                  arrowprops=dict(arrowstyle="-|>", lw=1.3, color="black", mutation_scale=9))
    ax_b.text(e2 + 5, 0.13, rf"$\times{e2 / e1:.1f}$" "\nstorage", ha="left", va="center", fontsize=8.5)
    ax_b.set_xlim(0, cap_h.max())
    ax_b.set_ylim(0.05, 60)
    ax_b.yaxis.set_major_locator(FixedLocator([0.1, 1, 10]))
    ax_b.set_yticklabels(["0.1", "1", "10"])
    ax_b.yaxis.set_minor_locator(LogLocator(subs=np.arange(2, 10)))
    ax_b.yaxis.set_minor_formatter(NullFormatter())
    formatear_eje(ax_b, "BESS capacity E (h of demand)", "LPSP (%)", menores_y=ax_b.yaxis.get_minor_locator())
    ax_b.legend(loc="upper right", fontsize=8, frameon=False, handlelength=1.2)

    # ---------------------------------------------------------- (c) E* frente a la meta
    for dd in datos:
        e_star = np.array([e_para(dd["lpsp"], cap_h, m) for m in METAS])
        ax_c.semilogx(METAS * 100, e_star, "o", ms=2.6, color=dd["color"], markeredgewidth=0)
        ax_c.semilogx(METAS * 100, dd["kappa"] * np.log(dd["l0"] / METAS), "--", lw=0.9,
                      color=dd["color"])
    ax_c.invert_xaxis()
    ax_c.set_ylim(0, None)
    ax_c.xaxis.set_major_locator(FixedLocator([10, 5, 2, 1, 0.5]))
    ax_c.set_xticklabels(["10", "5", "2", "1", "0.5"])
    ax_c.xaxis.set_minor_formatter(NullFormatter())
    formatear_eje(ax_c, r"Reliability target LPSP$^*$ (%)", r"Required storage $E^*$ (h)",
                  menores_x=LogLocator(subs=np.arange(2, 10)))
    ax_c.text(0.04, 0.93, r"$E^*=\kappa\,\ln(L_0/\mathrm{LPSP}^*)$" "\n" r"slope $=\kappa$",
              transform=ax_c.transAxes, va="top", fontsize=8.5)

    etiqueta_panel(ax_a, "(a)", debajo=0.48)
    etiqueta_panel(ax_b, "(b)", debajo=0.48)
    etiqueta_panel(ax_c, "(c)", debajo=0.48)
    guardar(fig, "capitulo_2", "Efecto_intermitencia_curva")


if __name__ == "__main__":
    main()
