"""Figura 1.4 — Mismo mes, misma energía, distinto agrupamiento de los días nublados.

Ilustra el problema de investigación: dos meses de 30 días con exactamente
10 días nublados y, por lo tanto, la MISMA energía mensual y el mismo
promedio que usa la regulación para la energía firme. En (a) los días
nublados están dispersos (uno cada tres días); en (b) están seguidos.
La misma batería, operada con despacho directo, cubre el primer mes y
falla en el segundo.

Paneles
  (a), (b)  energía FV diaria frente a la demanda diaria
  (c), (d)  estado de carga de la batería y energía no suministrada acumulada

Salida: capitulo_1/Mismo_mes_agrupamiento.pdf
Datos SINTÉTICOS (perfil de cielo despejado con índice de claridad fijo).
Editar en PARÁMETROS: planta, demanda, batería e índices de claridad.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

import estilo  # noqa: E402
from comun_tesis import AZUL, GRIS, NARANJA, ROJO, SOLAR, SOLAR_LINEA, guardar  # noqa: E402
from estilo import etiqueta_panel, formatear_eje  # noqa: E402

# ----------------------------- PARÁMETROS -----------------------------
DEMANDA_MW = 20.0
P_PV_MW = 150.0            # planta común de 7.5 veces la demanda
PR = 0.80
KT_DESPEJADO = 0.78
KT_NUBLADO = 0.40
N_DIAS = 30
DIAS_NUBLADOS_DISPERSOS = list(range(1, 30, 3))      # 10 días: 2, 5, 8, ..., 29
DIAS_NUBLADOS_SEGUIDOS = list(range(10, 20))         # 10 días seguidos
E_HORAS = 27.0             # batería en horas de demanda (540 MWh; 432 MWh útiles con 10–90 %)
E_P = 4.0                  # relación energía/potencia [h]
ETA = 0.922                # eficiencia de carga = de descarga (ida y vuelta 0.85)
SOC_MIN = 0.10             # fracción de E (ventana de operación 10–90 %)
SOC_MAX = 0.90
SOC_INICIAL = SOC_MAX      # el mes empieza con la batería llena
# ----------------------------------------------------------------------

HORAS = np.arange(24)
CIELO = np.clip(np.sin(np.pi * (HORAS + 0.5 - 6.0) / 12.0), 0.0, None) * 1000.0


def generacion(dias_nublados: list[int]) -> np.ndarray:
    kt = np.full(N_DIAS, KT_DESPEJADO)
    kt[dias_nublados] = KT_NUBLADO
    ghi = (kt[:, None] * CIELO[None, :]).ravel()
    return P_PV_MW * ghi / 1000.0 * PR


def simular(gen: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Despacho directo hora a hora; mismas ecuaciones del capítulo 3."""
    e = E_HORAS * DEMANDA_MW
    pmax = e / E_P
    s = SOC_INICIAL * e
    soc, ens = np.empty(gen.size), np.empty(gen.size)
    for t, p in enumerate(gen):
        if p >= DEMANDA_MW:
            s = min(s + ETA * min(p - DEMANDA_MW, pmax), SOC_MAX * e)
            ens[t] = 0.0
        else:
            falta = DEMANDA_MW - p
            entrega = min(falta, pmax, (s - SOC_MIN * e) * ETA)
            s -= entrega / ETA
            ens[t] = falta - entrega
        soc[t] = s / e
    return soc, np.cumsum(ens)


def main() -> None:
    import matplotlib.pyplot as plt

    estilo.aplicar_estilo()
    alto_ej, sep_v, y0, arriba = 1.45, 0.75, 0.95, 0.15
    alto = y0 + 2 * alto_ej + sep_v + arriba
    util = estilo.ANCHO - estilo.MARGEN_IZQ - 0.62   # margen derecho mayor: eje de ENS
    sep_h = 0.30
    w = (util - sep_h) / 2
    fig = plt.figure(figsize=(estilo.ANCHO, alto))

    def eje(f, c, compartir=None):
        x = estilo.MARGEN_IZQ + c * (w + sep_h)
        y = y0 + (1 - f) * (alto_ej + sep_v)
        return fig.add_axes([x / estilo.ANCHO, y / alto, w / estilo.ANCHO, alto_ej / alto],
                            sharey=compartir)

    casos = [("Scattered cloudy days", DIAS_NUBLADOS_DISPERSOS),
             ("Consecutive cloudy days", DIAS_NUBLADOS_SEGUIDOS)]
    dias = np.arange(1, N_DIAS + 1)
    t_dias = np.arange(N_DIAS * 24) / 24.0
    arriba_ax, abajo_ax = [], []
    for c, (titulo, nublados) in enumerate(casos):
        gen = generacion(nublados)
        e_dia = gen.reshape(-1, 24).sum(axis=1)
        soc, ens = simular(gen)
        print(f"  {titulo}: energía del mes = {e_dia.sum():.0f} MWh, "
              f"ENS = {ens[-1]:.0f} MWh, LPSP del mes = {ens[-1] / (DEMANDA_MW * gen.size):.1%}")

        a = eje(0, c, arriba_ax[0] if arriba_ax else None)
        colores = [SOLAR if d not in nublados else GRIS for d in range(N_DIAS)]
        a.bar(dias, e_dia, width=0.8, color=colores, edgecolor="none")
        a.axhline(DEMANDA_MW * 24, color=ROJO, lw=1.2, ls="--")
        a.text(N_DIAS + 0.4, DEMANDA_MW * 24 + 15, "Demand", ha="right", va="bottom",
               fontsize=8, color=ROJO)
        a.set_title(titulo, fontsize=9, pad=3)
        formatear_eje(a, "", "PV energy [MWh/day]" if c == 0 else "")
        a.set_xlim(0.3, N_DIAS + 0.7)
        if c:
            a.tick_params(labelleft=False)
        etiqueta_panel(a, "(a)" if c == 0 else "(b)", debajo=0.30)
        arriba_ax.append(a)

        b = eje(1, c, abajo_ax[0] if abajo_ax else None)
        b.plot(t_dias, 100 * soc, color=AZUL, lw=1.0)
        b.set_ylim(0, 105)
        b.set_xlim(0, N_DIAS)
        formatear_eje(b, "Day of the month", "State of charge [%]" if c == 0 else "")
        if c:
            b.tick_params(labelleft=False)
        b2 = b.twinx()
        b2.plot(t_dias, ens, color=NARANJA, lw=1.4)
        b2.set_ylim(0, 1400)
        b2.set_yticks([0, 400, 800, 1200])
        b2.grid(False)
        b2.tick_params(axis="y", direction="in", labelsize=8, colors=NARANJA)
        if c == 1:
            b2.set_ylabel("Cumulative ENS [MWh]", color=NARANJA, fontsize=9)
        else:
            b2.tick_params(labelright=False)
        etiqueta_panel(b, "(c)" if c == 0 else "(d)", debajo=0.52)
        abajo_ax.append(b)

    guardar(fig, "capitulo_1", "Mismo_mes_agrupamiento")


if __name__ == "__main__":
    main()
