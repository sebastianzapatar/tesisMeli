"""Paso 5 — Ley exponencial de almacenamiento y modelo sustituto κ(B, M).

Dos preguntas, en orden:

1. ¿Se sostiene ``LPSP(E) ≈ L0·exp(-E/κ)``? Se responde mirando el R² del
   ajuste lineal de ``ln(LPSP)`` contra E, serie por serie.
2. Si se sostiene, ¿κ se explica con B, M, PSH y el factor de planta?
   Se responde con LOO-CV **contra un baseline explícito**.

Salidas:
    resultados/05_kappa.xlsx
    resultados/05_sustituto_coeficientes.xlsx
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from _comun import cargar_balances, cronometro, guardar, preparar, subtitulo, titulo
from intermitencia import io_datos, pv
from intermitencia.confiabilidad import curva_capacidad
from intermitencia.sustituto import ajustar_kappa, ajustar_sustituto


def main() -> None:
    cfg = preparar()
    sc = cfg.sustituto

    titulo("ley exponencial de almacenamiento")
    print("Hipótesis:  LPSP(E) = L0 · exp(-E/kappa)")
    print(f"Tramo de ajuste: LPSP entre {sc['ajuste_lpsp_min']} "
          f"y {sc['ajuste_lpsp_max']}")

    inter = pd.read_excel(cfg.rutas.salida / "02_intermitencia.xlsx").set_index("Serie")
    optimos = pd.read_excel(cfg.rutas.salida / "04_optimos.xlsx").set_index("Serie")
    diag = pd.read_excel(cfg.rutas.salida / "01_diagnostico_series.xlsx").set_index("Serie")

    with cronometro("lectura"):
        gen, _ = cargar_balances(cfg)
    ghi = gen / pv.factor_ghi_a_mw(cfg.planta)
    psh = io_datos.leer_psh(cfg.rutas.psh_51, cfg.rutas.cache)

    p_ref = float(sc["planta_referencia_mw"])
    print(f"Planta de referencia: {p_ref:.0f} MW, COMÚN a todas las series")
    print(
        "  (si kappa se calcula en la planta óptima de cada serie, el\n"
        "   dimensionamiento absorbe las diferencias de intermitencia y\n"
        "   kappa queda casi constante: el sustituto deja de tener señal)"
    )

    filas = []
    with cronometro("ajuste de kappa"):
        for s in ghi.columns:
            # Planta COMÚN: es la única forma de aislar el efecto de la
            # intermitencia. Sobredimensionar la planta es un sustituto de
            # tener almacenamiento, así que comparar cada serie en SU
            # planta óptima esconde justo lo que se quiere medir.
            factor = pv.factor_ghi_a_mw(cfg.planta) * p_ref / cfg.planta.potencia_mw
            balance = ghi[s].to_numpy() * factor - cfg.demanda_mw

            caps = np.linspace(0.0, 1200.0, 45)
            curva = curva_capacidad(balance, caps, cfg.bess, cfg.demanda_mw)

            aj = ajustar_kappa(
                curva["capacidad_mwh"].to_numpy(),
                curva["lpsp"].to_numpy(),
                lpsp_min=sc["ajuste_lpsp_min"],
                lpsp_max=sc["ajuste_lpsp_max"],
            )
            filas.append(
                {
                    "Serie": s,
                    "kappa_mwh": aj.kappa_mwh,
                    "L0": aj.l0,
                    "r2_ley_exponencial": aj.r2,
                    "n_puntos_ajuste": aj.n_puntos,
                    "p_pv_referencia_MW": p_ref,
                    "p_pv_optima_MW": float(optimos.loc[s, "p_pv_mw"]),
                    "e_bess_optima_MWh": float(optimos.loc[s, "e_bess_mwh"]),
                }
            )

    kappa = pd.DataFrame(filas).set_index("Serie")

    subtitulo("¿Se sostiene la ley exponencial?")
    r2 = kappa["r2_ley_exponencial"].dropna()
    print(f"  R² del ajuste lineal de ln(LPSP) en E, sobre {len(r2)} series:")
    print(f"    mediana {r2.median():.4f}   mínimo {r2.min():.4f}   máximo {r2.max():.4f}")
    print(f"    series con R² > 0.95: {int((r2 > 0.95).sum())} de {len(r2)}")
    if r2.median() > 0.95:
        print(
            "\n  >>> La ley se sostiene con precisión. Toda la curva de\n"
            "      confiabilidad queda resumida en UN parámetro físico."
        )
    elif r2.median() > 0.85:
        print(
            "\n  >>> Buena aproximación de primer orden, pero no exacta.\n"
            "      Reporta el R² junto con kappa; no la presentes como ley\n"
            "      exacta. La curvatura residual sugiere que una exponencial\n"
            "      estirada, exp(-(E/kappa)^beta), ajustaría mejor: vale la\n"
            "      pena probarla si necesitas más precisión."
        )
    else:
        print("\n  >>> La ley NO se sostiene. No uses esta parametrización.")

    k = kappa["kappa_mwh"].dropna()
    print(f"\n  kappa: mediana {k.median():.1f} MWh   "
          f"rango [{k.min():.1f}, {k.max():.1f}]   CV = {k.std() / k.mean():.3f}")
    print(
        "\n  Lectura de kappa: es el almacenamiento [MWh] que hay que agregar\n"
        "  para dividir la LPSP por e (~2.72). Cuanto mayor kappa, más cara\n"
        "  es la confiabilidad en ese sitio."
    )

    # ---------------------------------------------------------------
    # MODELO SUSTITUTO
    # ---------------------------------------------------------------
    titulo("modelo sustituto  ln(kappa) ~ b, m, psh, factor de planta")

    datos = kappa.join(inter[["B", "M"]]).join(diag[["PSH_h_dia", "factor_planta"]])
    datos = datos.rename(columns={"PSH_h_dia": "PSH"})

    mapa = {"B": "B", "M": "M", "PSH": "PSH", "factor_planta": "factor_planta"}
    predictores = [mapa[p] for p in sc["predictores"] if p in mapa]

    res = ajustar_sustituto(datos, predictores, objetivo="kappa_mwh")
    print(res.resumen())

    subtitulo("Correlaciones simples con ln(kappa)")
    d = datos[predictores + ["kappa_mwh"]].dropna()
    lk = np.log(d["kappa_mwh"])
    for p in predictores:
        r = np.corrcoef(d[p], lk)[0, 1]
        print(f"  {p:16s} r = {r:+.3f}")

    subtitulo("Advertencia sobre extrapolación")
    for p in predictores:
        v = d[p]
        print(f"  {p:16s} rango observado [{v.min():.3f}, {v.max():.3f}]")
    print(
        "\n  Solo predice dentro de estos rangos. El modelo anterior dibujaba\n"
        "  el mapa de calor sobre todo el cuadrado unitario de (B,M) aunque\n"
        "  los datos ocupaban una nube diminuta, y con d = -26 la superficie\n"
        "  es violenta fuera de esa nube."
    )

    titulo("guardado")
    guardar(datos.reset_index(), cfg, "05_kappa.xlsx")

    coef = res.coeficientes.rename("valor").to_frame()
    coef.loc["r2_loo", "valor"] = res.r2_loo
    coef.loc["rmse_loo", "valor"] = res.rmse_loo
    coef.loc["rmse_loo_baseline", "valor"] = res.rmse_loo_baseline_media
    coef.loc["mejora_sobre_baseline", "valor"] = res.mejora_sobre_baseline
    guardar(coef.reset_index(), cfg, "05_sustituto_coeficientes.xlsx")

    print("\nListo. Siguiente paso:  pipeline/06_figuras.py")


if __name__ == "__main__":
    main()
