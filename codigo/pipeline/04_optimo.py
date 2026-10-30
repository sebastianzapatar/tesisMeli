"""Paso 4 — Óptimo económico conjunto de planta y batería.

Esto es lo que reemplaza al heurístico `conf_max * 0.99`.

Sin costo el problema es degenerado: la confiabilidad crece de forma
monótona con la capacidad, así que "maximizar confiabilidad" siempre
responde "más grande". Con costo el óptimo es interior y único, y la
regla de parada es económica:

    d(CAPEX_anual)/dE = VoLL * |d(ENS)/dE|

Además se optimiza en 2-D sobre `(P_pv, E_bess)`, porque el paso 01
mostró que con la planta fija en 100 MW el problema no tiene solución de
alta confiabilidad.

Salidas:
    resultados/04_optimos.xlsx      un óptimo por serie
    resultados/04_grilla.xlsx       superficie LCOE(P_pv, E_bess) para el mapa
    resultados/04_pareto.xlsx       frente costo-confiabilidad
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from _comun import cargar_balances, cronometro, guardar, preparar, subtitulo, titulo
from intermitencia import io_datos, pv
from intermitencia.dimensionamiento import frente_pareto, optimizar_sistema

# Rangos de búsqueda. El paso 01 mostró que hacen falta ~115 MW solo para
# equilibrar la energía, así que el rango arranca en 100 y llega hasta 600.
RANGO_PV_MW = (100.0, 600.0)
RANGO_BESS_MWH = (0.0, 2500.0)
N_GRILLA = 14

# Series para las que se guarda la grilla completa (insumo del mapa de calor).
SERIES_MAPA = 3


def main() -> None:
    cfg = preparar()

    titulo("óptimo económico conjunto (planta + batería)")
    print(f"Rango de planta   : {RANGO_PV_MW[0]:.0f} a {RANGO_PV_MW[1]:.0f} MW")
    print(f"Rango de batería  : {RANGO_BESS_MWH[0]:.0f} a {RANGO_BESS_MWH[1]:.0f} MWh")
    print(f"Grilla            : {N_GRILLA} x {N_GRILLA}")
    print(f"VoLL              : {cfg.economia.voll_usd_mwh:,.0f} USD/MWh")
    print(f"WACC              : {cfg.economia.tasa_descuento:.1%}  "
          f"({cfg.economia.vida_proyecto_anios} años)")
    print("\nRECUERDA: los costos de config.yaml están marcados '# REVISAR'.")
    print("Reemplázalos por tus fuentes citadas antes de publicar.")

    with cronometro("lectura"):
        gen, balance = cargar_balances(cfg)
    ghi = gen / pv.factor_ghi_a_mw(cfg.planta)
    psh = io_datos.leer_psh(cfg.rutas.psh_51, cfg.rutas.cache)

    optimos, grillas, paretos = [], [], []

    with cronometro("optimización"):
        for i, s in enumerate(balance.columns):
            g = ghi[s].to_numpy()

            opt, grilla = optimizar_sistema(
                g, cfg.planta, cfg.bess, cfg.economia, cfg.demanda_mw,
                rango_pv_mw=RANGO_PV_MW,
                rango_bess_mwh=RANGO_BESS_MWH,
                n_grilla=N_GRILLA,
            )

            e_dia = float(pv.energia_diaria(psh[s], cfg.planta, base="generada"))
            fila = opt.__dict__.copy()
            fila["Serie"] = s
            fila["razon_sobredimension"] = opt.p_pv_mw / cfg.demanda_mw
            fila["bess_horas_de_demanda"] = opt.e_bess_mwh / cfg.demanda_mw
            # Porcentaje sobre la energía diaria de la planta ÓPTIMA
            e_dia_opt = e_dia * opt.p_pv_mw / cfg.planta.potencia_mw
            fila["bess_pct_energia_diaria"] = 100.0 * opt.e_bess_mwh / e_dia_opt
            optimos.append(fila)

            if i < SERIES_MAPA:
                grilla.insert(0, "Serie", s)
                grillas.append(grilla)

                pareto = frente_pareto(
                    (g * pv.factor_ghi_a_mw(cfg.planta)
                     * opt.p_pv_mw / cfg.planta.potencia_mw) - cfg.demanda_mw,
                    cfg.objetivos_lpsp, cfg.bess, cfg.demanda_mw,
                    cfg.planta, cfg.economia,
                )
                pareto.insert(0, "Serie", s)
                pareto["p_pv_mw"] = opt.p_pv_mw
                paretos.append(pareto)

    df = pd.DataFrame(optimos).set_index("Serie")

    titulo("óptimos por serie (primeras 12)")
    print(
        df[["p_pv_mw", "e_bess_mwh", "p_bess_mw", "lcoe_usd_mwh", "lpsp",
            "frac_vertida", "ciclos_por_anio"]]
        .head(12).round(3).to_string()
    )

    subtitulo("Resumen sobre las 51 series")
    for col, unidad, fmt in [
        ("p_pv_mw", "MW", ".0f"),
        ("e_bess_mwh", "MWh", ".0f"),
        ("bess_horas_de_demanda", "h de demanda", ".1f"),
        ("bess_pct_energia_diaria", "% energía diaria", ".1f"),
        ("lcoe_usd_mwh", "USD/MWh", ".1f"),
        ("lpsp", "-", ".4f"),
        ("frac_vertida", "-", ".3f"),
    ]:
        v = df[col]
        print(f"  {col:26s} p50 {v.median():>9{fmt}}   "
              f"[{v.min():{fmt}}, {v.max():{fmt}}]  {unidad}")

    print(f"\n  Convergió: {int(df['convergio'].sum())} de {len(df)}")
    print(f"  Evaluaciones por serie: {df['n_evaluaciones'].mean():.0f} en promedio")

    subtitulo("Contraste con el dimensionamiento anterior")
    print(f"  Planta anterior          : {cfg.planta.potencia_mw:.0f} MW (fija)")
    print(f"  Planta óptima (mediana)  : {df['p_pv_mw'].median():.0f} MW")
    print(f"  Sobredimensión implícita : "
          f"{df['p_pv_mw'].median() / cfg.planta.potencia_mw:.2f}x")
    print(f"\n  Batería óptima (mediana) : {df['e_bess_mwh'].median():.0f} MWh "
          f"= {df['bess_horas_de_demanda'].median():.1f} h de demanda")
    print(
        "\n  El modelo anterior buscaba la batería en 5-30 % de la energía\n"
        "  diaria con la planta fija. El óptimo económico dice otra cosa:\n"
        "  primero hay que sobredimensionar la planta, y solo entonces la\n"
        "  batería tiene excedente con el cual trabajar."
    )

    titulo("guardado")
    guardar(df.reset_index(), cfg, "04_optimos.xlsx")
    if grillas:
        guardar(pd.concat(grillas, ignore_index=True), cfg, "04_grilla.xlsx")
    if paretos:
        guardar(pd.concat(paretos, ignore_index=True), cfg, "04_pareto.xlsx")

    print("\nListo. Siguiente paso:  pipeline/05_sustituto.py")


if __name__ == "__main__":
    main()
