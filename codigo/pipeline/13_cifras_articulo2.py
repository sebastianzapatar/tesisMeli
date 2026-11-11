"""Paso 13 — Cifras que cita la Sección 4 del artículo 2.

Imprime, a partir de las salidas de los pasos 10 a 12, cada número que
aparece en el texto de resultados, para poder verificarlo o actualizarlo
si cambia un supuesto. No simula. Guarda resultados/articulo2/13_cifras.json.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from intermitencia import Config
from intermitencia.economia import lpsp_optima_por_voll


def main() -> None:
    cfg = Config.cargar()
    c = cfg.rutas.salida / "articulo2"
    s = pd.read_excel(c / "10_sitios.xlsx").set_index("Serie")
    co = pd.read_excel(c / "10_costo_planta_comun.xlsx")
    mi = pd.read_excel(c / "10_minimo_costo.xlsx")
    sens = pd.read_excel(c / "10_sensibilidad_BM_planta.xlsx")
    comp = pd.read_excel(c / "11_comparacion_modelos.xlsx").set_index("modelo")
    cvb = pd.read_excel(c / "11_cv_bloques.xlsx").set_index("modelo")
    boot = pd.read_excel(c / "11_bootstrap_coeficientes.xlsx")
    rob = pd.read_excel(c / "11_robustez_ventana.xlsx")
    ef = pd.read_excel(c / "11_efecto_BM.xlsx")
    resumen = json.loads((c / "10_resumen.json").read_text())

    f = {}
    q = lambda x: [float(np.nanmin(x)), float(np.nanmedian(x)), float(np.nanmax(x))]
    f["n_sitios"] = len(s)
    f["B_min_med_max"], f["M_min_med_max"] = q(s.B), q(s.M)
    f["B_mayor_0"], f["M_mayor_0"] = int((s.B > 0).sum()), int((s.M > 0).sum())
    f["n_eventos_min_med_max"] = q(s.n_eventos_dias)
    f["tau_medio_dias_min_med_max"] = q(s.tau_medio_dias)
    f["duracion_media_dias_min_med_max"] = q(s.duracion_media_dias)
    f["r_B_PSH"] = float(np.corrcoef(s.B, s.PSH)[0, 1])
    f["r_M_PSH"] = float(np.corrcoef(s.M, s.PSH)[0, 1])
    f["r_B_M"] = float(np.corrcoef(s.B, s.M)[0, 1])
    f["r_Bhoraria_PSH"] = float(np.corrcoef(s.B_horaria, s.PSH)[0, 1])
    f["r_lnk_PSH"] = float(np.corrcoef(np.log(s.kappa_mwh), s.PSH)[0, 1])
    f["r_lnk_B"] = float(np.corrcoef(np.log(s.kappa_mwh), s.B)[0, 1])
    f["r_lnk_Bhoraria"] = float(np.corrcoef(np.log(s.kappa_mwh), s.B_horaria)[0, 1])
    piv = sens.pivot_table(index="Serie", columns="planta_mw", values="B")
    pivm = sens.pivot_table(index="Serie", columns="planta_mw", values="M")
    f["sens_B_spearman_vs_150"] = {str(k): float(piv[k].corr(piv[150.0], method="spearman")) for k in piv}
    f["sens_M_spearman_vs_150"] = {str(k): float(pivm[k].corr(pivm[150.0], method="spearman")) for k in pivm}
    f["sens_B_mediana"] = {str(k): float(piv[k].median()) for k in piv}
    f["lpsp_sin_bess_min_max"] = [float(s.lpsp_sin_bess.min()), float(s.lpsp_sin_bess.max())]
    f["vertido_sin_bess_min_med_max"] = q(s.frac_vertida_sin_bess)
    f["kappa_min_med_max"] = q(s.kappa_mwh)
    f["kappa_p25_p75"] = [float(s.kappa_mwh.quantile(0.25)), float(s.kappa_mwh.quantile(0.75))]
    f["r2_ley_min_med_max"] = q(s.r2_ley)
    f["r2_ley_mayor_095"] = int((s.r2_ley > 0.95).sum())
    f["r2_ley_mayor_090"] = int((s.r2_ley > 0.90).sum())
    f["beta_estirada_min_med_max"] = q(s.beta_estirada)
    f["dAIC_mayor_2"] = int((s.delta_aic_estirada > 2).sum())
    f["L0_mayor_1"] = int((s.L0 > 1).sum())
    for m in (0.05, 0.02, 0.01):
        g = co[np.isclose(co.meta_lpsp, m)]
        k = f"meta_{m:g}"
        f[k + "_Esim_min_med_max"] = q(g.e_star_sim_mwh)
        f[k + "_Esim_p25_p75"] = [float(g.e_star_sim_mwh.quantile(.25)), float(g.e_star_sim_mwh.quantile(.75))]
        f[k + "_horas_med"] = float(g.horas_de_demanda.median())
        f[k + "_sitios_E_mayor_1000"] = int((g.e_star_sim_mwh > 1000).sum())
        f[k + "_err_ley_rel_med"] = float(((g.e_star_ley_mwh - g.e_star_sim_mwh) / g.e_star_sim_mwh).abs().median())
        f[k + "_costo_bess_med"] = float(g.costo_bess_musd_anio.median())
        f[k + "_mc_med_p25_p75"] = [float(g.costo_marginal_usd_mwh_ens.median()), float(g.costo_marginal_usd_mwh_ens.quantile(.25)), float(g.costo_marginal_usd_mwh_ens.quantile(.75))]
        f[k + "_ciclos_med"] = float(g.ciclos_por_anio.median())
        f[k + "_vertido_med"] = float(g.frac_vertida.median())
        h = mi[np.isclose(mi.objetivo_lpsp, m)]
        f[k + "_min_P_med_p25_p75"] = [float(h.p_pv_mw.median()), float(h.p_pv_mw.quantile(.25)), float(h.p_pv_mw.quantile(.75))]
        f[k + "_min_E_med_p25_p75"] = [float(h.e_bess_mwh.median()), float(h.e_bess_mwh.quantile(.25)), float(h.e_bess_mwh.quantile(.75))]
        f[k + "_min_costo_med"] = float(h.costo_anual_musd.median())
        f[k + "_min_capex_opex_med"] = float(h.costo_capex_opex_musd.median())
        f[k + "_min_lcoe_med_p25_p75"] = [float(h.lcoe_usd_mwh.median()), float(h.lcoe_usd_mwh.quantile(.25)), float(h.lcoe_usd_mwh.quantile(.75))]
        f[k + "_min_vertido_med"] = float(h.frac_vertida.median())
        f[k + "_comun_lcoe_med"] = float(g.lcoe_usd_mwh.median())
        f[k + "_comun_costo_total_med"] = float(g.costo_total_musd_anio.median())
    pc = co.pivot_table(index="Serie", columns="meta_lpsp", values="costo_bess_musd_anio")
    pm = mi.pivot_table(index="Serie", columns="objetivo_lpsp", values="costo_capex_opex_musd")
    for nombre, t in (("comun", pc), ("minimo", pm)):
        a = (t[0.02] - t[0.05]) / 3
        b = (t[0.01] - t[0.02]) / 1
        f[f"pp_{nombre}_5a2_med_p25_p75"] = [float(a.median()), float(a.quantile(.25)), float(a.quantile(.75))]
        f[f"pp_{nombre}_2a1_med_p25_p75"] = [float(b.median()), float(b.quantile(.25)), float(b.quantile(.75))]
    f["c_E"] = resumen["c_E_usd_mwh_anio"]
    lo = lpsp_optima_por_voll(s.kappa_mwh, cfg.economia, cfg.bess.duracion_h, cfg.demanda_mw)
    f["lpsp_voll_min_med_max"] = q(lo)
    f["voll"] = cfg.economia.voll_usd_mwh
    for m in ("PSH", "PSH+B", "PSH+M", "PSH+B+M", "PSH+CV", "PSH+racha", "PSH+ac1kt", "PSH+B+M+ac1kt",
              "difusion", "difusion+B+M"):
        f[f"modelo_{m}"] = {k: (None if pd.isna(v) else (float(v) if isinstance(v, (int, float, np.floating)) else v))
                            for k, v in comp.loc[m, ["r2", "r2_loo", "rmse_loo", "aic", "delta_r2_loo", "F_parcial", "p_F"]].items()}
        f[f"modelo_{m}"]["r2_bloques"] = float(cvb.loc[m, "r2_bloques"])
    f["coef_PSH+B+M"] = {k: float(comp.loc["PSH+B+M", f"coef_{k}"]) for k in ("intercepto", "PSH", "B", "M")}
    f["p_PSH+B+M"] = {k: float(comp.loc["PSH+B+M", f"p_{k}"]) for k in ("PSH", "B", "M")}
    f["coef_PSH+B"] = {k: float(comp.loc["PSH+B", f"coef_{k}"]) for k in ("intercepto", "PSH", "B")}
    f["cvb_coef_B_PSH+B"] = [float(cvb.loc["PSH+B", "coef_B_min"]), float(cvb.loc["PSH+B", "coef_B_max"])]
    bt = boot.set_index(["modelo", "remuestreo", "coeficiente"])
    for mod in ("PSH+B+M", "PSH+B"):
        for r in ("sitios", "bloques"):
            for k in ("PSH", "B", "M"):
                if (mod, r, k) in bt.index:
                    x = bt.loc[(mod, r, k)]
                    f[f"boot_{mod}_{r}_{k}"] = [float(x.estimado), float(x.ic_inf), float(x.ic_sup),
                                                float(x.efecto_1sd), float(x.efecto_1sd_ic_inf), float(x.efecto_1sd_ic_sup)]
    f["vif"] = pd.read_excel(c / "11_vif.xlsx").set_index("predictor").VIF.to_dict()
    f["robustez"] = rob[rob.modelo.isin(["PSH", "PSH+B", "PSH+B+M"])][
        ["ventana_lpsp_max", "modelo", "n", "r2_loo", "delta_r2_loo", "p_F", "coef_B"]].to_dict("records")
    f["efecto"] = ef.to_dict("records")
    f["bloques_tamanos"] = pd.read_excel(c / "11_bloques.xlsx").bloque.value_counts().sort_index().tolist()
    if (c / "12_reglas_resumen.xlsx").exists():
        f["reglas"] = pd.read_excel(c / "12_reglas_resumen.xlsx").to_dict("records")
        f["reglas_vs_BM"] = pd.read_excel(c / "12_reglas_vs_BM.xlsx").to_dict("records")
        lp = pd.read_excel(c / "12_cota_lp.xlsx")
        f["lp"] = {"ventanas": len(lp), "ens_R1_total": float(lp.ens_R1_mwh.sum()),
                   "brecha_max_mwh": float(lp.brecha_mwh.max()), "brecha_rel_max": float((lp.brecha_mwh / lp.ens_R1_mwh.where(lp.ens_R1_mwh > 0)).max())}
    # Unidades normalizadas por la demanda (las que usa el artículo): el modelo
    # es lineal en D, P_pv y E, así que energías en horas de demanda (MWh/D),
    # potencias como múltiplo de D y costos por MW de demanda firme.
    D = cfg.demanda_mw
    n = {"D_referencia_mw": D, "planta_comun_xD": float(cfg.sustituto["planta_referencia_mw"]) / D}
    n["kappa_h_min_med_max"] = [x / D for x in f["kappa_min_med_max"]]
    n["kappa_h_p25_p75"] = [x / D for x in f["kappa_p25_p75"]]
    for m in (0.05, 0.02, 0.01):
        k = f"meta_{m:g}"
        n[k + "_E_h_min_med_max"] = [x / D for x in f[k + "_Esim_min_med_max"]]
        n[k + "_E_h_p25_p75"] = [x / D for x in f[k + "_Esim_p25_p75"]]
        n[k + "_costo_bess_musd_por_MW"] = f[k + "_costo_bess_med"] / D
        n[k + "_min_P_xD_med_p25_p75"] = [x / D for x in f[k + "_min_P_med_p25_p75"]]
        n[k + "_min_E_h_med_p25_p75"] = [x / D for x in f[k + "_min_E_med_p25_p75"]]
    for clave in ("pp_comun_5a2_med_p25_p75", "pp_comun_2a1_med_p25_p75",
                  "pp_minimo_5a2_med_p25_p75", "pp_minimo_2a1_med_p25_p75"):
        n[clave + "_kusd_por_MW"] = [x * 1000 / D for x in f[clave]]
    n["efecto_h"] = [{"variable": r["variable"], "percentil": r["percentil"],
                      "kappa_h": r["kappa_mwh"] / D, "E_5a1_h": r["mwh_de_5_a_1_pct"] / D,
                      "costo_5a1_musd_por_MW": r["costo_de_5_a_1_pct_musd_anio"] / D}
                     for r in f["efecto"]]
    n["intercepto_lnkappa_h"] = f["coef_PSH+B+M"]["intercepto"] - float(np.log(D))
    f["normalizado"] = n
    (c / "13_cifras.json").write_text(json.dumps(f, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(f, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
