"""Paso 10 — Resultados del artículo 2 con las 51 series reales.

Reúne en un solo paso, con las decisiones del artículo (D1, D4, D5):

1. Métricas por sitio a la planta común P_ref (tarea A3): B y M diarios
   (y horarios, como contraste), indicadores simples (tarea A4) y la
   escala de difusión ln(sigma^2/2mu) del balance diario.
2. Curvas capacidad–confiabilidad LPSP(E) con un barrido fino, ajuste
   de la ley exponencial (kappa, L0, R², error estándar) y de la
   exponencial estirada (beta, ΔAIC) (tarea A6).
3. Capacidad necesaria E* para las metas de LPSP (5, 2 y 1 %), simulada
   por bisección y predicha por la ley.
4. Costo de cada punto de confiabilidad: a planta común (solo batería) y
   con planta y batería ajustadas juntas (sistema de mínimo costo).
5. Sensibilidad de B y M al tamaño de planta (tarea A3).

El análisis estadístico (valor incremental de B y M, bootstrap, VIF,
robustez a la ventana de ajuste) está en el paso 11, que solo lee estas
salidas y corre en segundos.

Salidas en resultados/articulo2/10_*.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from _comun import cronometro, subtitulo, titulo
from intermitencia import Config, io_datos
from intermitencia.confiabilidad import curva_capacidad, evaluar
from intermitencia.dimensionamiento import capacidad_para_lpsp, minimo_costo_para_lpsp
from intermitencia.economia import (
    HORAS_ANIO,
    costear,
    costo_anual_bess_por_mwh,
    costo_por_punto_lpsp,
    lpsp_optima_por_voll,
)
from intermitencia.eventos import (
    eventos_diarios_centrados,
    indicadores_simples,
    metricas_intermitencia,
)
from intermitencia.pv import GHI_STC
from intermitencia.sustituto import ajustar_kappa, ajustar_kappa_estirada, error_estandar_kappa


def balance_a(ghi: pd.Series, p_mw: float, cfg: Config) -> pd.Series:
    """Balance horario [MW] de una planta de p_mw con la demanda plana."""
    return ghi * p_mw * cfg.planta.performance_ratio / GHI_STC - cfg.demanda_mw


def metricas_sitio(ghi: pd.Series, bal: pd.Series, cfg: Config) -> dict:
    ic = cfg.intermitencia
    kw = dict(umbral=ic.umbral_mw, base=ic.base_evento, min_eventos=ic.min_eventos,
              corregir_tamano_finito=ic.corregir_tamano_finito, metodo_memory=ic.metodo_memory)
    d = metricas_intermitencia(eventos_diarios_centrados(bal), **kw)
    h = metricas_intermitencia(bal.to_numpy(), **kw)
    # Balance diario neto (energía generada - demandada) en días completos
    completos = bal.resample("D").count().eq(24)
    neto = bal.resample("D").sum()[completos]
    mu, sig = float(neto.mean()), float(neto.std(ddof=1))
    fila = {
        "B": d["B"], "M": d["M"], "n_eventos_dias": d["n_eventos"],
        "tau_medio_dias": d["tau_medio_h"], "tau_cv": d["tau_cv"],
        "duracion_media_dias": d["duracion_media_h"],
        "B_horaria": h["B"], "M_horaria": h["M"],
        "mu_balance_diario_mwh": mu, "sigma_balance_diario_mwh": sig,
        "ln_difusion": float(np.log(sig ** 2 / (2 * mu))) if mu > 0 else np.nan,
    }
    fila.update(indicadores_simples(ghi, bal))
    return fila


def main() -> None:
    cfg = Config.cargar()
    sc = cfg.sustituto
    cc = cfg.crudo["costo_confiabilidad"]
    salida = cfg.rutas.salida / "articulo2"
    salida.mkdir(parents=True, exist_ok=True)

    p_ref = float(sc["planta_referencia_mw"])
    metas = [float(x) for x in cc["metas_lpsp"]]
    caps = np.arange(0.0, float(sc["capacidad_max_mwh"]) + 1e-9, float(sc["capacidad_paso_mwh"]))
    potencias = np.arange(cc["potencia_pv_min_mw"], cc["potencia_pv_max_mw"] + 1e-9,
                          cc["potencia_pv_paso_mw"])
    c_e = costo_anual_bess_por_mwh(cfg.economia, cfg.bess.duracion_h)
    d_anual = cfg.demanda_mw * HORAS_ANIO

    titulo("resultados del artículo 2 (51 series reales)")
    print(f"Planta común         : {p_ref:.0f} MW   demanda plana {cfg.demanda_mw:.0f} MW")
    print(f"Barrido de capacidad : 0 a {caps[-1]:.0f} MWh cada {caps[1]:.0f} MWh ({caps.size} puntos)")
    print(f"Metas de LPSP        : {', '.join(f'{m:.0%}' for m in metas)}")
    print(f"Costo anual del BESS : {c_e:,.0f} USD por MWh-año (c_E)")

    with cronometro("lectura"):
        ghi = io_datos.leer_series_horarias(cfg.rutas.series_51, cfg.rutas.cache)
        psh = io_datos.leer_psh(cfg.rutas.psh_51, cfg.rutas.cache)
    psh_serie = io_datos.psh_desde_series(ghi)
    n_anios = len(ghi) / HORAS_ANIO

    sitios, curvas, costos, minimos, sustitucion, sens = [], [], [], [], [], []
    with cronometro("simulación de los 51 sitios"):
        for s in ghi.columns:
            g = ghi[s]
            bal = balance_a(g, p_ref, cfg)
            b = bal.to_numpy()

            fila = {"Serie": s, "PSH": float(psh[s]), "PSH_desde_serie": float(psh_serie[s])}
            fila.update(metricas_sitio(g, bal, cfg))

            # --- curva capacidad-confiabilidad y ley exponencial ----------
            cur = curva_capacidad(b, caps, cfg.bess, cfg.demanda_mw)
            lp = cur["lpsp"].to_numpy()
            aj = ajustar_kappa(caps, lp, sc["ajuste_lpsp_min"], sc["ajuste_lpsp_max"])
            est = ajustar_kappa_estirada(caps, lp, sc["ajuste_lpsp_min"], sc["ajuste_lpsp_max"])
            fila.update({
                "kappa_mwh": aj.kappa_mwh, "L0": aj.l0, "r2_ley": aj.r2,
                "n_puntos_ajuste": aj.n_puntos,
                "se_kappa_mwh": error_estandar_kappa(caps, lp, sc["ajuste_lpsp_min"], sc["ajuste_lpsp_max"]),
                "kappa_estirada_mwh": est.kappa_mwh, "beta_estirada": est.beta,
                "delta_aic_estirada": est.delta_aic,
                "lpsp_sin_bess": float(lp[0]),
                "frac_vertida_sin_bess": float(cur["frac_vertida"].iloc[0]),
            })
            curvas.append(pd.DataFrame({
                "Serie": s, "capacidad_mwh": caps, "lpsp": lp,
                "frac_vertida": cur["frac_vertida"].to_numpy(),
                "ciclos_por_anio": cur["ciclos_por_anio"].to_numpy(),
            }))

            # --- E* y costo a planta común --------------------------------
            prev = None
            for meta in metas:
                e_sim = capacidad_para_lpsp(b, meta, cfg.bess, cfg.demanda_mw)
                m = evaluar(b, e_sim, cfg.bess, cfg.demanda_mw)
                c = costear(p_ref, e_sim, e_sim / cfg.bess.duracion_h, m.ens_mwh / n_anios,
                            m.descarga_mwh / n_anios, m.vertimiento_mwh / n_anios, d_anual,
                            cfg.economia)
                reg = {
                    "Serie": s, "meta_lpsp": meta, "e_star_sim_mwh": e_sim,
                    "e_star_ley_mwh": aj.capacidad_para(meta),
                    "horas_de_demanda": e_sim / cfg.demanda_mw,
                    "costo_bess_musd_anio": c_e * e_sim / 1e6,
                    "costo_total_musd_anio": c.anual_total_usd / 1e6,
                    "lcoe_usd_mwh": c.lcoe_usd_mwh, "ciclos_por_anio": m.ciclos_por_anio,
                    "frac_vertida": m.frac_vertida,
                    "costo_marginal_usd_mwh_ens": float(costo_por_punto_lpsp(
                        aj.kappa_mwh, meta, cfg.economia, cfg.bess.duracion_h,
                        cfg.demanda_mw)["usd_por_mwh_ens_evitada"].iloc[0]),
                }
                if prev is not None:
                    dpp = 100 * (prev["meta_lpsp"] - meta)
                    reg["costo_por_pp_musd_anio"] = (reg["costo_bess_musd_anio"]
                                                     - prev["costo_bess_musd_anio"]) / dpp
                    reg["mwh_por_pp"] = (e_sim - prev["e_star_sim_mwh"]) / dpp
                costos.append(reg)
                prev = reg

            # --- sistema de mínimo costo (planta + batería) ----------------
            for meta in metas:
                mejor, tabla = minimo_costo_para_lpsp(g.to_numpy(), meta, potencias, cfg.planta,
                                                      cfg.bess, cfg.economia, cfg.demanda_mw)
                mejor["Serie"] = s
                minimos.append(mejor)
                tabla.insert(0, "Serie", s)
                tabla.insert(1, "meta_lpsp", meta)
                sustitucion.append(tabla)

            # --- sensibilidad de B y M al tamaño de planta (A3) ------------
            for p in sc["plantas_sensibilidad_mw"]:
                bp = balance_a(g, float(p), cfg)
                r = metricas_intermitencia(eventos_diarios_centrados(bp),
                                           min_eventos=cfg.intermitencia.min_eventos)
                sens.append({"Serie": s, "planta_mw": float(p), "B": r["B"], "M": r["M"],
                             "n_eventos_dias": r["n_eventos"]})

            sitios.append(fila)
            print(f"  {s:28s} PSH={fila['PSH']:.2f}  B={fila['B']:+.3f}  M={fila['M']:+.3f}  "
                  f"kappa={aj.kappa_mwh:7.0f}  R2={aj.r2:.3f}")

    df = pd.DataFrame(sitios).set_index("Serie")
    curvas = pd.concat(curvas, ignore_index=True)
    costos = pd.DataFrame(costos)
    minimos = pd.DataFrame(minimos)
    sustitucion = pd.concat(sustitucion, ignore_index=True)
    sens = pd.DataFrame(sens)

    # -----------------------------------------------------------------
    subtitulo("Ley exponencial")
    print(f"  R² mediano {df.r2_ley.median():.3f}  [{df.r2_ley.min():.3f}, {df.r2_ley.max():.3f}]  "
          f"R²>0.95: {(df.r2_ley > 0.95).sum()} de {len(df)}")
    print(f"  kappa mediana {df.kappa_mwh.median():.0f} MWh  [{df.kappa_mwh.min():.0f}, "
          f"{df.kappa_mwh.max():.0f}]  CV {df.kappa_mwh.std() / df.kappa_mwh.mean():.2f}")
    print(f"  beta estirada mediana {df.beta_estirada.median():.2f}; ΔAIC>2 en "
          f"{(df.delta_aic_estirada > 2).sum()} de {len(df)}")

    # -----------------------------------------------------------------
    subtitulo("Costo de la confiabilidad")
    lpsp_opt = lpsp_optima_por_voll(df.kappa_mwh, cfg.economia, cfg.bess.duracion_h, cfg.demanda_mw)
    df["lpsp_optima_voll"] = lpsp_opt
    print(costos.groupby("meta_lpsp")[["e_star_sim_mwh", "costo_bess_musd_anio",
                                       "costo_por_pp_musd_anio", "costo_marginal_usd_mwh_ens"]]
          .median().round(2).to_string())
    print(minimos.groupby("objetivo_lpsp")[["p_pv_mw", "e_bess_mwh", "costo_anual_musd",
                                            "lcoe_usd_mwh"]].median().round(2).to_string())

    # -----------------------------------------------------------------
    titulo("guardado")
    df.reset_index().to_excel(salida / "10_sitios.xlsx", index=False)
    curvas.to_csv(salida / "10_curvas.csv.gz", index=False)
    costos.to_excel(salida / "10_costo_planta_comun.xlsx", index=False)
    minimos.to_excel(salida / "10_minimo_costo.xlsx", index=False)
    sustitucion.to_csv(salida / "10_sustitucion_planta_bateria.csv.gz", index=False)
    sens.to_excel(salida / "10_sensibilidad_BM_planta.xlsx", index=False)
    resumen = {
        "planta_referencia_mw": p_ref, "c_E_usd_mwh_anio": c_e, "n_sitios": int(len(df)),
        "anios": n_anios, "metas_lpsp": metas,
    }
    (salida / "10_resumen.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    for f in sorted(salida.iterdir()):
        print(f"  -> {f.relative_to(cfg.rutas.salida.parent)}")
    print("\nListo. Siguiente paso:  pipeline/11_analisis_articulo2.py")


if __name__ == "__main__":
    main()
