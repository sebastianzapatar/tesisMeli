"""Paso 9 — Escenarios de operación regulatorios (CREG 101 113 de 2026).

Objetivo específico 3. Toma el sistema ya dimensionado en el paso 04
(P_PV*, E_BESS*, P_BESS* por serie) y, SIN cambiar su tamaño, lo opera
bajo la combinación de:

  * modalidad regulatoria  M0 (técnica), M1 (recurso híbrido),
                           M2 (SAEB independiente), M3 (activo de red);
  * política de despacho   R1-R5 (Sección 3.10), P1 (horas declaradas)
                           y LP (óptimo con horizonte rodante);
  * escenario de precio    perfiles de bolsa por fase ENSO;
  * potencia declarada     (solo M1) fracción de P_PV*.

Diferencia importante con el paso 08: aquí la generación se escala a la
planta óptima P_PV* de cada serie. El paso 08 simula sobre la planta de
100 MW de config.yaml con la batería dimensionada para ~151 MW, lo que
mezcla dos tamaños de planta (ver BITACORA).

Salidas
  resultados/09_escenarios_creg.xlsx          una fila por combinación
  resultados/09_escenarios_creg_resumen.xlsx  medianas y p10/p90 por escenario
  resultados/09_sensibilidad_intermitencia.xlsx
        correlación de Spearman de cada indicador con B, M y PSH
        (cierra el ciclo con el objetivo 1: ¿la intermitencia explica
        cómo le va a cada modalidad?)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd
import yaml

from _comun import cargar_balances, cronometro, guardar, preparar, subtitulo, titulo
from intermitencia.config import raiz_proyecto
from intermitencia.operacion_creg import (
    MODALIDADES,
    POLITICAS,
    ParametrosBESS,
    ParametrosRegulatorios,
    alinear_precios,
    cargar_precios_bolsa,
    correr_escenario,
)

INDICADORES = ["lpsp", "cobertura_deficit", "frac_vertida", "ciclos_equivalentes_anio",
               "suavidad_rampa_mw", "frac_carga_desde_red", "horas_desviacion",
               "ingreso_excedentes_usd_anio", "margen_arbitraje_usd_anio",
               "costo_ens_voll_usd_anio", "horas_indisp_max_12m",
               "eficiencia_mensual_min", "energia_faltante_eficiencia_mwh_anio"]


def _leer_escenarios() -> dict:
    ruta = raiz_proyecto() / "escenarios_creg.yaml"
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _precios(esc: dict, indice: pd.DatetimeIndex) -> dict[str, np.ndarray]:
    """Devuelve {nombre_escenario: precio alineado}. Vacío si no hay archivo."""
    pc = esc["precios"]
    ruta = raiz_proyecto() / pc["ruta"]
    if not ruta.exists():
        print(f"  AVISO: no se encontró {ruta}.\n"
              "  Se correrán solo los escenarios que no necesitan precio "
              "(M0 y M3 con R1-R5).")
        return {}
    serie = cargar_precios_bolsa(ruta, columna_fecha=pc["columna_fecha"],
                                 unidad=pc["unidad"], trm_cop_usd=pc.get("trm_cop_usd"))
    return {nombre: alinear_precios(indice, serie, "perfil_anual", anios)
            for nombre, anios in pc["escenarios_precio"].items()}


def main() -> None:
    cfg = preparar()
    esc = _leer_escenarios()
    rg, rr, lp = esc["regulatorio"], esc["reglas"], esc["lp"]

    titulo("9. escenarios de operación regulatorios (CREG 101 113 de 2026)")
    for k, v in MODALIDADES.items():
        print(f"  {k}: {v}")
    for k, v in POLITICAS.items():
        print(f"  {k}: {v}")

    titulo("1. lectura de series, dimensionamiento (paso 04) e intermitencia (paso 02)")
    with cronometro("lectura"):
        gen_ref, _ = cargar_balances(cfg)
    optimos = pd.read_excel(cfg.rutas.salida / "04_optimos.xlsx").set_index("Serie")
    series = esc.get("series") or list(gen_ref.columns)
    idx = gen_ref.index
    precios = _precios(esc, idx)
    escenarios_precio = list(precios) or ["sin_precio"]

    # Costo de degradación por MWh de throughput: CAPEX de energía
    # repartido en los ciclos de vida (carga + descarga = 2 E por ciclo).
    e = cfg.economia
    c_deg = (getattr(e, "capex_bess_energia_usd_kwh", 250.0) * 1000.0
             / (2.0 * getattr(e, "ciclos_vida", 6000)))
    voll = getattr(e, "voll_usd_mwh", 600.0)
    print(f"  costo de degradación = {c_deg:.1f} USD/MWh de throughput; VoLL = {voll:.0f} USD/MWh")

    titulo("2. simulación de escenarios")
    filas = []
    series_lp = series[: int(lp["n_series"])]
    mascara_lp = idx.year.isin(lp["anios"])
    with cronometro("escenarios"):
        for s in series:
            p_pv = float(optimos.loc[s, "p_pv_mw"])
            e_b = float(optimos.loc[s, "e_bess_mwh"])
            p_b = float(optimos.loc[s, "p_bess_mw"])
            gen = gen_ref[s].to_numpy() * p_pv / cfg.planta.potencia_mw
            bess = ParametrosBESS.desde_config(cfg.bess, e_b, p_b,
                                               consumo_aux_frac=rg["consumo_aux_frac"])
            for nombre_p in escenarios_precio:
                pi = precios.get(nombre_p)
                for mod in esc["modalidades"]:
                    fr_decl = rg["p_max_declarada_frac_ppv"] if mod == "M1" else [None]
                    for fr in fr_decl:
                        reg = ParametrosRegulatorios(
                            modalidad=mod,
                            rpf_frac=rg["rpf_frac"],
                            rpf_duracion_h=rg["rpf_duracion_min"] / 60.0,
                            p_max_declarada_mw=(fr * p_pv) if fr is not None else None,
                            precio_contrato_usd_mwh=rg["precio_contrato_usd_mwh"],
                            e_funcion_mwh=rg["e_funcion_horas"] * p_b,
                            eficiencia_minima=rg["eficiencia_minima"],
                            max_horas_indisp=rg["max_horas_indisp"],
                            limite_importacion_mw=rg["limite_importacion_frac_demanda"] * cfg.demanda_mw,
                            ventana_recarga_red=tuple(rg["ventana_recarga_red"]),
                            voll_usd_mwh=voll,
                            costo_degradacion_usd_mwh=c_deg,
                        )
                        for pol in esc["politicas"]:
                            if pi is None and (pol == "P1" or mod in ("M1", "M2")):
                                continue
                            # Periodos: el completo (todas las políticas menos LP) y,
                            # para las series del subconjunto LP, el mismo periodo
                            # corto para TODAS las políticas, de modo que la
                            # comparación contra la cota LP sea pareada.
                            periodos = []
                            if pol != "LP":
                                periodos.append("completo")
                            if s in series_lp:
                                periodos.append("LP-subconjunto")
                            for periodo in periodos:
                                if periodo == "LP-subconjunto":
                                    g_, i_ = gen[mascara_lp], idx[mascara_lp]
                                    p_ = pi[mascara_lp] if pi is not None else None
                                else:
                                    g_, i_, p_ = gen, idx, pi
                                r = correr_escenario(
                                    g_, cfg.demanda_mw, bess, reg, pol,
                                    precios_usd_mwh=p_, indice=i_,
                                    soc_res=rr["soc_res"],
                                    ventana_horaria=tuple(rr["ventana_horaria"]),
                                    ventana_suavizado_h=rr["ventana_suavizado_h"],
                                    l_min_h=rr["l_min_h"],
                                    k_horas_arbitraje=rr["k_horas_arbitraje"],
                                    horizonte_h=lp["horizonte_h"], compromiso_h=lp["compromiso_h"],
                                    peso_funcion_usd_mwh=lp["peso_funcion_usd_mwh"],
                                )
                                fila = r.resumen()
                                fila.update({"Serie": s, "escenario_precio": nombre_p,
                                             "p_max_decl_frac": fr, "p_pv_mw": p_pv,
                                             "e_bess_mwh": e_b, "p_bess_mw": p_b,
                                             "periodo": periodo})
                                filas.append(fila)
            print(f"  {s}: listo")

    res = pd.DataFrame(filas)
    guardar(res, cfg, "09_escenarios_creg.xlsx")

    titulo("3. resumen por escenario (mediana y p10-p90 sobre las series)")
    claves = ["escenario_precio", "modalidad", "p_max_decl_frac", "politica", "periodo"]
    res["p_max_decl_frac"] = res["p_max_decl_frac"].fillna(-1)
    agg = res.groupby(claves)[INDICADORES].agg(
        [lambda x: x.quantile(0.1), "median", lambda x: x.quantile(0.9)])
    agg.columns = [f"{c}_{q}" for c, q in zip(agg.columns.get_level_values(0),
                                             ["p10", "p50", "p90"] * len(INDICADORES))]
    agg = agg.reset_index()
    guardar(agg, cfg, "09_escenarios_creg_resumen.xlsx")
    subtitulo("Medianas (LPSP, ciclos/año, horas indisp. 12 m)")
    print(agg[claves + ["lpsp_p50", "ciclos_equivalentes_anio_p50",
                        "horas_indisp_max_12m_p50"]].round(3).to_string(index=False))

    titulo("4. ¿la intermitencia explica el desempeño regulatorio? (Spearman)")
    inter = pd.read_excel(cfg.rutas.salida / "02_intermitencia.xlsx").set_index("Serie")[["B", "M"]]
    diag = pd.read_excel(cfg.rutas.salida / "01_diagnostico_series.xlsx").set_index("Serie")[["PSH_h_dia"]]
    datos = res[res["periodo"] == "completo"].join(inter.join(diag), on="Serie")
    filas_c = []
    for clave, g in datos.groupby(["escenario_precio", "modalidad", "p_max_decl_frac", "politica"]):
        if len(g) < 8:
            continue
        for ind in INDICADORES:
            if g[ind].nunique() < 3:
                continue
            for x in ["B", "M", "PSH_h_dia"]:
                rho = g[[ind, x]].corr(method="spearman").iloc[0, 1]
                filas_c.append(dict(zip(["escenario_precio", "modalidad", "p_max_decl_frac",
                                         "politica"], clave), indicador=ind, variable=x,
                                    spearman=rho, n=len(g)))
    guardar(pd.DataFrame(filas_c), cfg, "09_sensibilidad_intermitencia.xlsx")


if __name__ == "__main__":
    main()
