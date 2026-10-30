"""Figura 1.2 — Generación FV horaria en tres días representativos.

Muestra que días con energía parecida pueden tener perfiles muy
distintos: la energía total no basta para dimensionar un BESS.

Entrada:  51 series/df_series_todas_las_subestaciones.xlsx  (vía config.yaml)
Salida:   salida/capitulo_1/Tres_dias_horizontal.pdf

La generación se calcula con el MISMO modelo FV del pipeline
(``intermitencia.pv.generacion_mw`` con los parámetros de config.yaml),
para que la figura del capítulo 1 sea coherente con la metodología.
"""

from __future__ import annotations

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))          # para importar estilo.py

import pandas as pd
from matplotlib.ticker import FixedLocator

from intermitencia import Config, io_datos, pv

from estilo import crear_figura, etiqueta_panel, formatear_eje, guardar, holgura

SERIE = "Cuestesitas"
DIAS = ["2024-09-28", "2003-11-04", "2011-11-30"]
PANELES = ["(a)", "(b)", "(c)"]

LINEA = "#E39400"      # ámbar oscuro: buen contraste sobre blanco
RELLENO = "#FDB813"    # amarillo solar de la tesis (mismo de la fig. 1.1)
TINTA_SUAVE = "#4a4a4a"

MESES_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def imprimir_parametros(planta) -> None:
    """Datos de los módulos FV de la planta de referencia.

    Los valores salen de config.yaml (sección ``planta``), los mismos que
    usa el pipeline, para que el texto de la tesis y la figura coincidan.
    """
    # ==========================================================
    # 3. DATOS DE LOS MÓDULOS FV
    # ==========================================================
    mw_proyecto = planta.potencia_mw                    # 100 MW
    potencia_modulo_w = planta.modulo_potencia_w        # 550 W
    potencia_modulo_mw = potencia_modulo_w / 1_000_000

    num_modulos = mw_proyecto / potencia_modulo_mw      # 181 818 módulos

    area_modulo = planta.modulo_ancho_m * planta.modulo_alto_m   # 2.279 x 1.134 m
    area = num_modulos * area_modulo                    # área total de módulos

    print("==========================================")
    print("PARÁMETROS DEL PROYECTO")
    print("==========================================")
    print(f"Potencia planta: {mw_proyecto:.2f} MW")
    print(f"Potencia por módulo: {potencia_modulo_w:.0f} W")
    print(f"Número de módulos: {num_modulos:,.0f}")
    print(f"Área por módulo: {area_modulo:.3f} m²")
    print(f"Área total: {area:,.2f} m²  ({area / 10_000:,.1f} ha)")
    print(f"Eficiencia del módulo: {planta.eficiencia_modulo_real:.1%}")
    print(f"Performance ratio: {planta.performance_ratio:.2f}")


def imprimir_resumen_dias(generacion) -> None:
    """Energía, pico y rampa máxima de cada día graficado (para el texto)."""
    print("==========================================")
    print(f"DÍAS GRAFICADOS — serie {SERIE}")
    print("==========================================")
    for dia, panel in zip(DIAS, PANELES):
        datos = generacion.loc[dia]
        horas = datos.index.hour + 1
        print(f"{panel} {dia}: "
              f"E = {datos.sum():,.1f} MWh | "
              f"pico = {datos.max():.1f} MWh (hora {horas[datos.values.argmax()]}) | "
              f"rampa máx. = {datos.diff().abs().max():.1f} MWh/h")


def main() -> None:
    cfg = Config.cargar()
    imprimir_parametros(cfg.planta)

    ghi = io_datos.leer_series_horarias(cfg.rutas.series_51, cfg.rutas.cache)
    generacion = pv.generacion_mw(ghi[SERIE], cfg.planta)   # MW en 1 h = MWh
    imprimir_resumen_dias(generacion)

    # margen inferior mayor: ahí van "Hour" y las etiquetas (a), (b), (c)
    # margen superior mayor: ahí van la fecha y la energía de cada día
    fig, axes = crear_figura(ncols=3, margen_inf=0.77, margen_sup=0.45)

    for ax, dia, panel in zip(axes, DIAS, PANELES):
        datos = generacion.loc[dia]
        horas = datos.index.hour + 1                      # horas 1..24

        ax.fill_between(horas, datos.values, 0, color=RELLENO, alpha=0.30, lw=0)
        ax.plot(horas, datos.values, color=LINEA, lw=1.4, zorder=3)
        # puntos sólo en las horas con sol (los ceros nocturnos recargaban)
        sol = datos.values > 0
        ax.plot(horas[sol], datos.values[sol], ls="none", marker="o", ms=2.6,
                mfc=LINEA, mec="white", mew=0.4, zorder=4)

        # fecha y energía del día, encima del panel
        f = pd.Timestamp(dia)
        energia = datos.sum()
        sobre_panel = dict(xy=(0.5, 1.0), xycoords="axes fraction",
                           textcoords="offset points", ha="center", va="bottom")
        ax.annotate(rf"$E_d$ = {energia:,.0f} MWh", xytext=(0, 4),
                    fontsize=9, color=TINTA_SUAVE, **sobre_panel)

        # mayores en 1, 6, 12, 18, 24; una marca menor por cada hora (1..24)
        formatear_eje(ax, xlabel="Hour",
                      ylabel="Generation [MWh]" if ax is axes[0] else "",
                      menores_x=FixedLocator(range(1, 25)))
        etiqueta_panel(ax, panel, debajo=0.52)

    # espacio entre el marco y el inicio de los datos, en X y en Y
    holgura(axes, "x", ticks=[1, 6, 12, 18, 24])
    holgura(axes, "y")        # mismo rango para los 3 paneles

    guardar(fig, "capitulo_1", "Tres_dias_horizontal")


if __name__ == "__main__":
    main()
