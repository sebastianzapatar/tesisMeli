"""Paso 3 — Curvas capacidad-confiabilidad y costo marginal.

Reemplaza a `Curvas capacidad-confiabilidad.py`. Diferencias:

* Simulador corregido (potencia, eficiencias, DoD, vertimiento, ciclos).
* Se reportan LPSP estándar **y** cobertura de déficit, con nombres
  distintos.
* Se agrega el costo marginal de la ENS evitada, que es lo que define el
  óptimo económico sin heurísticos.
* Confiabilidad año por año, no un solo número sobre 27 años.

Salidas:
    resultados/03_curvas.xlsx
    resultados/03_marginal.xlsx
    resultados/03_interanual.xlsx
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from _comun import cargar_balances, cronometro, guardar, preparar, subtitulo, titulo
from intermitencia import io_datos, pv
from intermitencia.confiabilidad import (
    curva_capacidad,
    evaluar_por_periodo,
    resumen_interanual,
)
from intermitencia.economia import HORAS_ANIO, costo_marginal_ens_evitada


def main() -> None:
    cfg = preparar()

    titulo("curvas capacidad - confiabilidad")
    with cronometro("lectura"):
        gen, balance = cargar_balances(cfg)
    psh = io_datos.leer_psh(cfg.rutas.psh_51, cfg.rutas.cache)

    n_anios = len(balance) / HORAS_ANIO
    porcentajes = np.arange(
        cfg.barrido.pct_min,
        cfg.barrido.pct_max + cfg.barrido.pct_paso / 2,
        cfg.barrido.pct_paso,
    )
    print(f"Barrido: {porcentajes[0]:.0%} a {porcentajes[-1]:.0%} "
          f"en pasos de {cfg.barrido.pct_paso:.0%}  ({len(porcentajes)} puntos)")
    print(f"Series: {balance.shape[1]}   Años: {n_anios:.1f}")

    curvas, marginales = [], []

    with cronometro("simulación"):
        for s in balance.columns:
            b = balance[s].to_numpy()
            # Base de porcentaje: energía que la planta REALMENTE genera.
            e_dia = float(pv.energia_diaria(psh[s], cfg.planta, base="generada"))
            caps = porcentajes * e_dia

            df = curva_capacidad(b, caps, cfg.bess, cfg.demanda_mw)
            df.insert(0, "Serie", s)
            df.insert(1, "pct_energia_diaria", porcentajes * 100)
            df["energia_planta_MWh_dia"] = e_dia
            curvas.append(df)

            mg = costo_marginal_ens_evitada(
                caps, df["ens_mwh"].to_numpy() / n_anios,
                cfg.economia, cfg.bess.duracion_h,
            )
            mg.insert(0, "Serie", s)
            marginales.append(mg)

    curvas = pd.concat(curvas, ignore_index=True)
    marginales = pd.concat(marginales, ignore_index=True)

    subtitulo("Techo de confiabilidad alcanzable (planta fija)")
    techo = (
        curvas.groupby("Serie")
        .agg(lpsp_min=("lpsp", "min"),
             cobertura_max=("cobertura_deficit", "max"),
             vertida_max=("frac_vertida", "max"))
        .sort_values("lpsp_min")
    )
    print(techo.head(8).round(4).to_string())
    print(f"\nLPSP mínima alcanzable: mejor {techo['lpsp_min'].min():.3f}, "
          f"mediana {techo['lpsp_min'].median():.3f}")
    print(
        f"\n  Con la planta en {cfg.planta.potencia_mw:.0f} MW, ni la batería más\n"
        f"  grande del barrido baja la LPSP de ~{techo['lpsp_min'].median():.0%}.\n"
        "  Es el mismo síntoma del paso 1: falta energía, no almacenamiento.\n"
        "  El paso 04 resuelve el tamaño de planta junto con el de batería."
    )

    subtitulo("Costo marginal de la ENS evitada")
    print(f"VoLL configurado: {cfg.economia.voll_usd_mwh:,.0f} USD/MWh\n")
    finito = marginales[np.isfinite(marginales["mcae_usd_mwh"])]
    print(f"MCAE mediano en el primer tramo del barrido: "
          f"{finito.groupby('Serie')['mcae_usd_mwh'].first().median():,.0f} USD/MWh")
    print(f"MCAE mediano en el último tramo           : "
          f"{finito.groupby('Serie')['mcae_usd_mwh'].last().median():,.0f} USD/MWh")
    rentables = finito[~finito["supera_voll"]]
    print(f"\nTramos donde agregar batería aún es rentable (MCAE < VoLL): "
          f"{len(rentables):,} de {len(finito):,}")

    subtitulo("Variabilidad interanual (a 25 % de la energía diaria)")
    filas = []
    for s in balance.columns:
        e_dia = float(pv.energia_diaria(psh[s], cfg.planta, base="generada"))
        por_anio = evaluar_por_periodo(
            balance[s], 0.25 * e_dia, cfg.bess, cfg.demanda_mw, periodo="YE"
        )
        r = resumen_interanual(por_anio)
        r["Serie"] = s
        filas.append(r)
    interanual = pd.DataFrame(filas).set_index("Serie")

    print(interanual[["lpsp_p50", "lpsp_p90", "lpsp_peor",
                      "razon_peor_vs_mediana"]].head(8).round(4).to_string())
    print(
        f"\nRazón peor año / año mediano: mediana {interanual['razon_peor_vs_mediana'].median():.2f}x"
        f",  máximo {interanual['razon_peor_vs_mediana'].max():.2f}x"
    )
    print(
        "  El modelo anterior reportaba UN número sobre 27 años y perdía por\n"
        "  completo esta dispersión. Dimensionar al año mediano deja el peor\n"
        "  año sin cubrir, que es justo el caso que importa."
    )

    titulo("guardado")
    guardar(curvas, cfg, "03_curvas.xlsx")
    guardar(marginales, cfg, "03_marginal.xlsx")
    guardar(interanual.reset_index(), cfg, "03_interanual.xlsx")

    print("\nListo. Siguiente paso:  pipeline/04_optimo.py")


if __name__ == "__main__":
    main()
