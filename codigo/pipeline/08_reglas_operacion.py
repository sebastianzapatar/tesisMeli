"""Paso 8 — Escenarios de operación del BESS (objetivo específico 3).

Toma el tamaño de BESS ya definido en el paso 04 (E_bess óptimo por
serie) y, SIN volver a cambiar ese tamaño, simula las cinco reglas de
despacho de la Sección 3.10 de la tesis sobre cada una de las series.
Responde la pregunta que los pasos 01-07 no responden: una vez que la
batería tiene un tamaño fijo, ¿cómo debería cargarse y descargarse
hora a hora?

Las cinco reglas comparten el mismo motor físico (límite de potencia,
eficiencias, ventana de SOC) que ya se usa en `03_curvas.py`; lo único
que cambia es la decisión de despacho (ver
`intermitencia/reglas_operacion.py`).

Además de la comparación principal (las 5 reglas, parámetros por
defecto, las 51 series), este paso corre el análisis de sensibilidad
un-parámetro-a-la-vez descrito en la Sección 3.10.4 de la tesis, para
las cuatro reglas que tienen un parámetro propio (R2-R5).

Salidas:
    resultados/08_reglas_operacion.xlsx           una fila por (serie, regla)
    resultados/08_reglas_operacion_resumen.xlsx    agregado por regla, con
                                                    distribución completa
                                                    (p10/p50/p90/min/max),
                                                    sobre las 51 series
    resultados/08_sensibilidad_detalle.xlsx        una fila por (serie, regla,
                                                    valor del parámetro)
    resultados/08_sensibilidad_resumen.xlsx        agregado por (regla, valor
                                                    del parámetro)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from _comun import cargar_balances, cronometro, guardar, preparar, subtitulo, titulo
from intermitencia.reglas_operacion import (
    NOMBRES_REGLAS,
    REGLAS_DISPONIBLES,
    comparar_reglas,
    simular_regla,
)

# Parámetros por defecto de las reglas con parámetro propio (R2-R5).
# Se fijan aquí, en un solo lugar, para que sea trivial correr después un
# análisis de sensibilidad variando uno a la vez (Sección 3.10.4 de la
# tesis). Ajústelos desde config.yaml si se agrega esa sección allí.
PARAMETROS_REGLAS = dict(
    soc_res=0.30,              # Regla 2: piso operativo de SOC
    ventana_horaria=(18, 22),  # Regla 3: horas de descarga habilitada
    ventana_suavizado_h=6,     # Regla 4: ancho de la media móvil, en horas
    l_min_h=3,                 # Regla 5: longitud mínima de bloque de excedente
)

# Grillas del análisis de sensibilidad: un parámetro a la vez, con los
# demás fijos en PARAMETROS_REGLAS (Sección 3.10.4 de la tesis).
# Grillas del análisis de sensibilidad: un parámetro a la vez, con los
# demás fijos en PARAMETROS_REGLAS (Sección 3.10.4 de la tesis). La de
# R2 se arma dentro de main(), porque depende del soc_min real de
# config.yaml (debe quedar estrictamente por encima de él).
GRILLA_SENSIBILIDAD_BASE = {
    "R3": ("ventana_horaria", [(20, 22), (18, 22), (15, 22), (10, 22), (0, 23)]),
    "R4": ("ventana_suavizado_h", [2, 4, 6, 12, 24]),
    "R5": ("l_min_h", [1, 2, 3, 6, 12]),
}

# El motor de simulación recorre cada serie hora por hora en Python puro
# (ver intermitencia/reglas_operacion.py), así que el análisis de
# sensibilidad completo (4 reglas x 5 valores x 51 series = 1020
# simulaciones sobre series de varios años) puede tardar bastante. Se
# corre sobre un subconjunto representativo de series, no las 51; la
# comparación principal de arriba sí usa las 51.
N_SERIES_SENSIBILIDAD = 10


def main() -> None:
    cfg = preparar()

    # --- Traducción de parámetros del BESS ya usados en el resto del
    #     pipeline (ver Sección "Supuestos principales" del cuaderno
    #     Modelo_intermitencia_explicado.ipynb) a los que necesita el
    #     motor de reglas_operacion.py ---
    #
    # cfg.bess.eff_roundtrip es la eficiencia de ciclo COMPLETO (ida y
    # vuelta). Como reglas_operacion.py separa carga y descarga, se
    # reparte en partes iguales: eff_roundtrip = eficiencia_carga *
    # eficiencia_descarga. Si su proyecto ya guarda las dos por
    # separado, reemplace estas dos líneas por esos atributos directos.
    EFICIENCIA_CARGA = float(np.sqrt(cfg.bess.eff_roundtrip))
    EFICIENCIA_DESCARGA = float(np.sqrt(cfg.bess.eff_roundtrip))

    # cfg.bess.soc_min_frac sí se confirmó en el cuaderno. No se
    # encontró un `soc_max_frac` equivalente en los insumos revisados;
    # se asume 0.95 y se avisa por consola para que se verifique contra
    # config.yaml antes de tomar los resultados como definitivos.
    SOC_MAX = float(getattr(cfg.bess, "soc_max_frac", 0.95))
    if not hasattr(cfg.bess, "soc_max_frac"):
        print(
            "  AVISO: cfg.bess no tiene 'soc_max_frac'; se usó 0.95 por defecto. "
            "Verifique el nombre real en config.yaml y ajuste SOC_MAX si difiere."
        )

    titulo("8. escenarios de operación del bess (objetivo específico 3)")
    print("Reglas evaluadas:")
    for r in REGLAS_DISPONIBLES:
        print(f"  {r}: {NOMBRES_REGLAS[r]}")
    print(f"\nParámetros por defecto: {PARAMETROS_REGLAS}")

    titulo("1. lectura de series y del dimensionamiento óptimo (paso 04)")
    with cronometro("lectura"):
        gen, balance = cargar_balances(cfg)

    ruta_optimos = cfg.rutas.salida / "04_optimos.xlsx"
    if not ruta_optimos.exists():
        raise FileNotFoundError(
            f"No se encontró {ruta_optimos}. Corra primero pipeline/04_optimo.py: "
            "este paso necesita el E_bess ya dimensionado, no vuelve a calcularlo."
        )
    optimos = pd.read_excel(ruta_optimos).set_index("Serie")

    titulo("2. simulación de las cinco reglas, por serie (las 51 series)")
    filas = []
    with cronometro("simulación"):
        for s in balance.columns:
            e_bess_mwh = float(optimos.loc[s, "e_bess_mwh"])
            p_bess_mw = float(optimos.loc[s, "p_bess_mw"])

            tabla_serie = comparar_reglas(
                balance[s].to_numpy(),
                e_bess_mwh=e_bess_mwh,
                p_bess_mw=p_bess_mw,
                demanda_mw=cfg.demanda_mw,
                horas_del_dia=balance.index.hour.to_numpy(),
                eficiencia_carga=EFICIENCIA_CARGA,
                eficiencia_descarga=EFICIENCIA_DESCARGA,
                soc_min=cfg.bess.soc_min_frac,
                soc_max=SOC_MAX,
                **PARAMETROS_REGLAS,
            )
            tabla_serie = tabla_serie.reset_index()
            tabla_serie.insert(0, "Serie", s)
            tabla_serie["e_bess_mwh"] = e_bess_mwh
            tabla_serie["p_bess_mw"] = p_bess_mw
            filas.append(tabla_serie)

    resultados = pd.concat(filas, ignore_index=True)

    subtitulo("Resultados por regla, primeras filas")
    cols_mostrar = ["Serie", "regla", "lpsp", "cobertura_deficit",
                     "frac_vertida", "ciclos_equivalentes", "suavidad_rampa_mw"]
    print(resultados[cols_mostrar].head(10).round(4).to_string(index=False))

    titulo("3. resumen agregado sobre las 51 series (distribución completa)")

    def _resumir(grupo: pd.DataFrame, col: str) -> pd.Series:
        return pd.Series({
            f"{col}_min": grupo[col].min(),
            f"{col}_p10": np.percentile(grupo[col], 10),
            f"{col}_p50": grupo[col].median(),
            f"{col}_p90": np.percentile(grupo[col], 90),
            f"{col}_max": grupo[col].max(),
        })

    columnas_indicador = ["lpsp", "cobertura_deficit", "frac_vertida",
                           "ciclos_equivalentes", "suavidad_rampa_mw"]
    piezas = []
    for col in columnas_indicador:
        piezas.append(
            resultados.groupby(["regla", "nombre_regla"])
            .apply(lambda g, c=col: _resumir(g, c))
        )
    resumen = pd.concat(piezas, axis=1).reset_index()

    subtitulo("Resumen (mediana) por regla")
    cols_p50 = ["regla", "nombre_regla"] + [f"{c}_p50" for c in columnas_indicador]
    print(resumen[cols_p50].round(4).to_string(index=False))

    subtitulo("Lectura de los resultados: cada regla frente a R1 (línea base)")
    r1 = resumen[resumen["regla"] == "R1"].iloc[0]
    for _, fila in resumen.iterrows():
        if fila["regla"] == "R1":
            continue
        d_lpsp = fila["lpsp_p50"] - r1["lpsp_p50"]
        d_cobertura = fila["cobertura_deficit_p50"] - r1["cobertura_deficit_p50"]
        d_vertida = fila["frac_vertida_p50"] - r1["frac_vertida_p50"]
        d_ciclos = fila["ciclos_equivalentes_p50"] - r1["ciclos_equivalentes_p50"]
        d_rampa = fila["suavidad_rampa_mw_p50"] - r1["suavidad_rampa_mw_p50"]
        print(
            f"  {fila['regla']} ({fila['nombre_regla']}):\n"
            f"    LPSP              {d_lpsp:+.4f}\n"
            f"    cobertura déficit {d_cobertura:+.4f}\n"
            f"    fracción vertida  {d_vertida:+.4f}\n"
            f"    ciclos equiv.     {d_ciclos:+.2f}\n"
            f"    suavidad rampa    {d_rampa:+.3f} MW"
        )
    print(
        "\n  No se espera que ninguna regla domine en todos los indicadores a la\n"
        "  vez (Sección 3.10.3 de la tesis): el objetivo es dejar explícito el\n"
        "  trade-off entre confiabilidad y desgaste de la batería, no declarar\n"
        "  una única 'ganadora'."
    )

    titulo("4. análisis de sensibilidad (un parámetro a la vez, Sección 3.10.4)")
    print(
        f"Corrido sobre {N_SERIES_SENSIBILIDAD} series representativas (no las "
        "51): el motor de simulación recorre cada serie hora por hora, y la "
        "grilla completa (4 reglas x 5 valores) sobre todas las series sería "
        "costosa. La comparación principal de la Sección 3 sí usa las 51."
    )
    series_sensibilidad = list(balance.columns[:N_SERIES_SENSIBILIDAD])

    soc_min = float(cfg.bess.soc_min_frac)
    grilla_soc_res = sorted({round(v, 3) for v in
                              [soc_min + 0.05, soc_min + 0.10, soc_min + 0.20,
                               soc_min + 0.30, soc_min + 0.40] if v < SOC_MAX})
    grilla_sensibilidad = {"R2": ("soc_res", grilla_soc_res), **GRILLA_SENSIBILIDAD_BASE}

    filas_sens = []
    with cronometro("sensibilidad"):
        for regla, (nombre_param, valores) in grilla_sensibilidad.items():
            for orden, valor in enumerate(valores):
                params = dict(PARAMETROS_REGLAS)
                params[nombre_param] = valor
                for s in series_sensibilidad:
                    e_bess_mwh = float(optimos.loc[s, "e_bess_mwh"])
                    p_bess_mw = float(optimos.loc[s, "p_bess_mw"])
                    r = simular_regla(
                        balance[s].to_numpy(), e_bess_mwh=e_bess_mwh, p_bess_mw=p_bess_mw,
                        regla=regla, demanda_mw=cfg.demanda_mw,
                        horas_del_dia=balance.index.hour.to_numpy(),
                        eficiencia_carga=EFICIENCIA_CARGA,
                        eficiencia_descarga=EFICIENCIA_DESCARGA,
                        soc_min=cfg.bess.soc_min_frac, soc_max=SOC_MAX,
                        **params,
                    )
                    fila = r.resumen()
                    fila["Serie"] = s
                    fila["parametro"] = nombre_param
                    if nombre_param == "ventana_horaria":
                        fila["valor_parametro"] = f"{valor[0]}-{valor[1]}"
                    else:
                        fila["valor_parametro"] = str(valor)
                    fila["orden_valor"] = orden
                    filas_sens.append(fila)

    sensibilidad = pd.DataFrame(filas_sens)
    resumen_sens = (
        sensibilidad.groupby(["regla", "nombre_regla", "parametro", "valor_parametro", "orden_valor"])
        .agg(
            lpsp_p50=("lpsp", "median"),
            cobertura_deficit_p50=("cobertura_deficit", "median"),
            frac_vertida_p50=("frac_vertida", "median"),
            ciclos_equivalentes_p50=("ciclos_equivalentes", "median"),
            suavidad_rampa_mw_p50=("suavidad_rampa_mw", "median"),
        )
        .reset_index()
        .sort_values(["regla", "orden_valor"])
    )


    subtitulo("Sensibilidad: mediana por valor del parámetro")
    print(resumen_sens.round(4).to_string(index=False))

    titulo("guardado")
    guardar(resultados, cfg, "08_reglas_operacion.xlsx")
    guardar(resumen, cfg, "08_reglas_operacion_resumen.xlsx")
    guardar(sensibilidad, cfg, "08_sensibilidad_detalle.xlsx")
    guardar(resumen_sens, cfg, "08_sensibilidad_resumen.xlsx")

    print("\nListo. Estos resultados alimentan la Sección de Resultados del "
          "objetivo específico 3 (Capítulo 4) y la Sección 8 del informe PDF "
          "(pipeline/07_informe.py).")


if __name__ == "__main__":
    main()
