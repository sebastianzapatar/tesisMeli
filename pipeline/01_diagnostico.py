"""Paso 1 — Diagnóstico de los datos y de la factibilidad del problema.

Corre esto primero. Verifica que los insumos estén sanos y responde la
pregunta que el modelo anterior nunca se hizo: **¿el problema planteado
tiene solución?**

Salidas:
    resultados/01_diagnostico_series.xlsx
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from _comun import cargar_balances, cronometro, guardar, preparar, subtitulo, titulo
from intermitencia import io_datos, pv
from intermitencia.almacenamiento import (
    NUMBA_ACTIVO,
    energia_requerida_pico_secuente,
)


def main() -> None:
    cfg = preparar()

    titulo("1. configuración")
    print(cfg.resumen())
    print()
    print(pv.describir_modelo(cfg.planta))
    print()
    print(f"Aceleración numba: {'ACTIVA' if NUMBA_ACTIVO else 'NO DISPONIBLE (lento)'}")

    titulo("2. lectura y validación de las series")
    with cronometro("lectura"):
        gen, balance = cargar_balances(cfg)
    ghi = gen / pv.factor_ghi_a_mw(cfg.planta)

    print(f"Series      : {gen.shape[1]}")
    print(f"Pasos        : {len(gen):,} horas")
    print(f"Periodo      : {gen.index.min():%Y-%m-%d} a {gen.index.max():%Y-%m-%d}")
    print(f"Años         : {len(gen) / 8760:.1f}")

    psh = io_datos.leer_psh(cfg.rutas.psh_51, cfg.rutas.cache)
    psh_calc = io_datos.psh_desde_series(ghi)
    dif = (psh - psh_calc).abs().max()
    print(f"\nPSH del archivo vs recalculada desde el GHI: máx |Δ| = {dif:.4f} h/día")
    if dif > 0.05:
        print("  ATENCIÓN: discrepancia alta. Revisa cuál de las dos es la buena.")

    titulo("3. factibilidad energética")
    subtitulo("¿Alcanza la generación para cubrir la demanda?")

    media = gen.mean().sort_values()
    fp = media / cfg.planta.potencia_mw

    print(f"Demanda plana                : {cfg.demanda_mw:.2f} MW")
    print(f"Generación media mínima      : {media.iloc[0]:.2f} MW  ({media.index[0]})")
    print(f"Generación media mediana     : {media.median():.2f} MW")
    print(f"Generación media máxima      : {media.iloc[-1]:.2f} MW  ({media.index[-1]})")
    print(f"Factor de planta mediano     : {fp.median():.3f}")

    deficitarias = int((media < cfg.demanda_mw).sum())
    print(f"\nSeries con generación media < demanda: {deficitarias} de {len(media)}")

    if deficitarias:
        p_min = cfg.demanda_mw / fp
        print(
            "\n  >>> El balance energético anual es NEGATIVO en esas series.\n"
            "      Ninguna capacidad de batería alcanza alta confiabilidad: el\n"
            "      almacenamiento mueve energía en el tiempo, no la crea.\n"
            f"      Potencia de planta necesaria solo para equilibrar la energía:\n"
            f"        mediana {p_min.median():.0f} MW   "
            f"máximo {p_min.max():.0f} MW  (hoy: {cfg.planta.potencia_mw:.0f} MW)\n"
            "      Y hace falta bastante más para tener excedente con el cual\n"
            "      cargar durante rachas nubladas y pagar las pérdidas.\n\n"
            "      >>> Por eso el problema debe resolverse en 2-D sobre\n"
            "          (P_pv, E_bess), no solo dimensionando la batería."
        )

    titulo("4. cota de almacenamiento por pico secuente (rippl)")
    print(
        "Capacidad que anularía la ENS sobre el registro, sin parámetros\n"
        "arbitrarios. Sustituye al heurístico 'conf_max * 0.99'.\n"
        "Con balance energético negativo esta cota diverge, que es\n"
        "precisamente el síntoma del problema anterior.\n"
    )

    filas = []
    for s in gen.columns:
        b = balance[s].to_numpy()
        e_planta_dia = float(psh[s] * pv.GHI_STC * pv.factor_ghi_a_mw(cfg.planta))
        anuales = [
            energia_requerida_pico_secuente(g.to_numpy())
            for _, g in balance[s].groupby(balance.index.year)
        ]
        filas.append(
            {
                "Serie": s,
                "PSH_h_dia": float(psh[s]),
                "gen_media_MW": float(gen[s].mean()),
                "factor_planta": float(fp[s]),
                "energia_planta_MWh_dia": e_planta_dia,
                "energia_deficit_total_MWh": float(-b[b < 0].sum()),
                "frac_horas_deficit": float((b < 0).mean()),
                "rippl_registro_MWh": energia_requerida_pico_secuente(b),
                "rippl_anual_p50_MWh": float(np.percentile(anuales, 50)),
                "rippl_anual_p90_MWh": float(np.percentile(anuales, 90)),
                "rippl_anual_max_MWh": float(np.max(anuales)),
            }
        )

    diag = pd.DataFrame(filas).sort_values("gen_media_MW", ascending=False)

    print(
        diag[
            [
                "Serie", "PSH_h_dia", "gen_media_MW", "factor_planta",
                "frac_horas_deficit", "rippl_anual_p50_MWh", "rippl_anual_p90_MWh",
            ]
        ]
        .head(10)
        .round(3)
        .to_string(index=False)
    )
    print(f"\n  ... ({len(diag)} series en total; la tabla completa va al Excel)")

    titulo("5. guardado")
    guardar(diag, cfg, "01_diagnostico_series.xlsx")

    print("\nListo. Siguiente paso:  pipeline/02_intermitencia.py")


if __name__ == "__main__":
    main()
