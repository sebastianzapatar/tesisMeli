"""Paso 11 — Valor incremental de B y M sobre la PSH (criterio D5).

Lee las salidas del paso 10 (no simula) y responde la pregunta central
del artículo: ¿B y M explican kappa más allá de la PSH, y mejor que los
indicadores simples?

1. Modelos anidados de ln kappa: R², R²_LOO, RMSE_LOO, AIC, BIC y F
   parcial contra el modelo anidado (tarea A4).
2. Validación por bloques de sitios con clima común (tarea A5): como los
   datos no traen coordenadas, los bloques se forman agrupando los sitios
   por la correlación de sus anomalías diarias de GHI. Bootstrap de
   coeficientes por sitios y por bloques, y VIF.
3. Veredicto del criterio D5.
4. Robustez a la ventana de ajuste de kappa: se reajusta kappa con la
   cola de la curva (LPSP <= 10 % y <= 5 %) y se repite la comparación.
5. Efecto de B y M en almacenamiento y costo (contrafactual a PSH mediana).

Salidas en resultados/articulo2/11_*.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from _comun import subtitulo, titulo
from intermitencia import Config, io_datos
from intermitencia.economia import HORAS_ANIO, costo_anual_bess_por_mwh
from intermitencia.sustituto import (
    ajustar_kappa,
    bloques_por_correlacion,
    bootstrap_coeficientes,
    comparar_modelos,
    cv_por_bloques,
    vif,
)


def veredicto_d5(comp: pd.DataFrame, boot: pd.DataFrame, umbral: float,
                 cvb: pd.DataFrame) -> pd.DataFrame:
    """Evalúa, criterio por criterio, si B (y M) aportan sobre la PSH."""
    c = comp.set_index("modelo")
    b = boot[(boot.modelo == "PSH+B+M") & (boot.remuestreo == "sitios")].set_index("coeficiente")
    bb = boot[(boot.modelo == "PSH+B+M") & (boot.remuestreo == "bloques")].set_index("coeficiente")
    v = cvb.set_index("modelo")
    simples = [m for m in ("PSH+CV", "PSH+racha", "PSH+ac1kt") if m in c.index]
    mejor_simple = c.loc[simples, "r2_loo"].max() if simples else np.nan
    filas = [
        ("ΔR²_LOO(PSH+B vs PSH) >= umbral", c.loc["PSH+B", "delta_r2_loo"], c.loc["PSH+B", "delta_r2_loo"] >= umbral),
        ("F parcial de B (p < 0,05)", c.loc["PSH+B", "p_F"], c.loc["PSH+B", "p_F"] < 0.05),
        ("IC 95 % bootstrap de beta_B excluye 0 (sitios)", f"[{b.loc['B', 'ic_inf']:.2f}, {b.loc['B', 'ic_sup']:.2f}]", bool(b.loc["B", "excluye_cero"])),
        ("IC 95 % bootstrap de beta_B excluye 0 (bloques)", f"[{bb.loc['B', 'ic_inf']:.2f}, {bb.loc['B', 'ic_sup']:.2f}]", bool(bb.loc["B", "excluye_cero"])),
        ("R² por bloques: PSH+B > PSH", f"{v.loc['PSH+B', 'r2_bloques']:.3f} vs {v.loc['PSH', 'r2_bloques']:.3f}", v.loc["PSH+B", "r2_bloques"] > v.loc["PSH", "r2_bloques"]),
        ("R²_LOO(PSH+B) >= mejor indicador simple", f"{c.loc['PSH+B', 'r2_loo']:.3f} vs {mejor_simple:.3f}", c.loc["PSH+B", "r2_loo"] >= mejor_simple),
        ("M aporta dado B: F parcial (p < 0,05)", c.loc["PSH+B+M", "p_F"], c.loc["PSH+B+M", "p_F"] < 0.05),
        ("IC 95 % bootstrap de beta_M excluye 0", f"[{b.loc['M', 'ic_inf']:.2f}, {b.loc['M', 'ic_sup']:.2f}]", bool(b.loc["M", "excluye_cero"])),
    ]
    return pd.DataFrame(filas, columns=["criterio", "valor", "cumple"])


def main() -> None:
    cfg = Config.cargar()
    sc = cfg.sustituto
    carpeta = cfg.rutas.salida / "articulo2"
    sitios = pd.read_excel(carpeta / "10_sitios.xlsx").set_index("Serie")
    curvas = pd.read_csv(carpeta / "10_curvas.csv.gz")
    espec = {k: list(v) for k, v in sc["especificaciones"].items()}
    umbral = float(sc["umbral_delta_r2_loo"])

    titulo("valor incremental de b y m sobre la psh")
    comp = comparar_modelos(sitios, espec, objetivo="kappa_mwh")
    print(comp[["modelo", "r2", "r2_loo", "rmse_loo", "aic", "anidado_en", "delta_r2_loo",
                "F_parcial", "p_F"]].round(4).to_string(index=False))

    # Bloques de sitios con clima común (anomalías diarias de GHI correlacionadas)
    ghi = io_datos.leer_series_horarias(cfg.rutas.series_51, cfg.rutas.cache)
    diarias = ghi.resample("D").sum()[ghi.resample("D").count().eq(24).all(axis=1)]
    bloques = bloques_por_correlacion(diarias, int(sc["n_bloques"]))
    sitios["bloque"] = bloques
    subtitulo(f"Validación por {int(sc['n_bloques'])} bloques de clima común")
    print(bloques.value_counts().sort_index().to_string())
    filas_cvb = []
    for nombre, cols in espec.items():
        r = cv_por_bloques(sitios, cols, bloques)
        fila = {"modelo": nombre, "r2_bloques": r["r2_bloques"], "rmse_bloques": r["rmse_bloques"],
                "n_bloques": r["n_bloques"]}
        for c in cols:
            fila[f"coef_{c}_min"] = r["coef_min"][c]
            fila[f"coef_{c}_max"] = r["coef_max"][c]
        filas_cvb.append(fila)
    cvb = pd.DataFrame(filas_cvb)
    print(cvb.round(3).to_string(index=False))

    rep = int(sc["bootstrap_replicas"])
    boot = pd.concat([
        bootstrap_coeficientes(sitios, cols, replicas=rep, semilla=cfg.semilla,
                               grupos=g).assign(modelo=n, remuestreo=tipo)
        for n, cols in [("PSH+B+M", ["PSH", "B", "M"]), ("PSH+B", ["PSH", "B"]), ("PSH", ["PSH"])]
        for tipo, g in (("sitios", None), ("bloques", bloques))
    ], ignore_index=True)
    subtitulo(f"Bootstrap ({rep} réplicas, semilla {cfg.semilla})")
    print(boot.round(4).to_string(index=False))
    tabla_vif = vif(sitios, ["PSH", "B", "M"]).to_frame().reset_index(names="predictor")
    print(tabla_vif.round(2).to_string(index=False))

    subtitulo("Criterio D5")
    d5 = veredicto_d5(comp, boot, umbral, cvb)
    print(d5.to_string(index=False))

    # -----------------------------------------------------------------
    subtitulo("Robustez a la ventana de ajuste de kappa")
    rob = [comp.assign(ventana_lpsp_max=float(sc["ajuste_lpsp_max"]))]
    for hi in sc["ventanas_robustez_lpsp_max"]:
        d = sitios.copy()
        k, r2 = [], []
        for s in d.index:
            g = curvas[curvas.Serie == s]
            aj = ajustar_kappa(g.capacidad_mwh.to_numpy(), g.lpsp.to_numpy(),
                               sc["ajuste_lpsp_min"], float(hi))
            k.append(aj.kappa_mwh)
            r2.append(aj.r2)
        d["kappa_mwh"] = k
        print(f"  LPSP <= {hi:.0%}: R² ley mediano {np.nanmedian(r2):.3f}, "
              f"{int(np.sum(np.array(r2) > 0.95))} sitios con R² > 0,95, "
              f"{int(np.isfinite(k).sum())} sitios con kappa")
        rob.append(comparar_modelos(d, espec, objetivo="kappa_mwh").assign(ventana_lpsp_max=float(hi),
                                                                          r2_ley_mediano=np.nanmedian(r2)))
    rob = pd.concat(rob, ignore_index=True)
    print(rob[rob.modelo.isin(["PSH", "PSH+B", "PSH+B+M", "PSH+ac1kt"])]
          [["ventana_lpsp_max", "modelo", "n", "r2_loo", "delta_r2_loo", "p_F", "coef_B", "p_B"]]
          .round(4).to_string(index=False))

    # -----------------------------------------------------------------
    subtitulo("Efecto de B y M en almacenamiento y costo (PSH mediana)")
    c_e = costo_anual_bess_por_mwh(cfg.economia, cfg.bess.duracion_h)
    d_anual = cfg.demanda_mw * HORAS_ANIO
    mod = comp.set_index("modelo").loc["PSH+B+M"]
    filas = []
    for var in ("B", "M"):
        for q in (0.10, 0.50, 0.90):
            x = {"PSH": sitios.PSH.median(), "B": sitios.B.median(), "M": sitios.M.median()}
            x[var] = float(sitios[var].quantile(q))
            k = float(np.exp(mod["coef_intercepto"]
                             + sum(mod[f"coef_{c}"] * x[c] for c in ("PSH", "B", "M"))))
            filas.append({
                "variable": var, "percentil": q, "valor": x[var], "kappa_mwh": k,
                "mwh_de_5_a_1_pct": k * np.log(5.0),
                "costo_de_5_a_1_pct_musd_anio": c_e * k * np.log(5.0) / 1e6,
                "costo_por_pp_en_1pct_musd_anio": c_e * k / 1e6,
                "usd_por_mwh_ens_en_1pct": c_e * k / (0.01 * d_anual),
            })
    efecto = pd.DataFrame(filas)
    print(efecto.round(2).to_string(index=False))

    titulo("guardado")
    comp.to_excel(carpeta / "11_comparacion_modelos.xlsx", index=False)
    boot.to_excel(carpeta / "11_bootstrap_coeficientes.xlsx", index=False)
    tabla_vif.to_excel(carpeta / "11_vif.xlsx", index=False)
    cvb.to_excel(carpeta / "11_cv_bloques.xlsx", index=False)
    bloques.rename_axis("Serie").reset_index().to_excel(carpeta / "11_bloques.xlsx", index=False)
    d5.to_excel(carpeta / "11_criterio_D5.xlsx", index=False)
    rob.to_excel(carpeta / "11_robustez_ventana.xlsx", index=False)
    efecto.to_excel(carpeta / "11_efecto_BM.xlsx", index=False)
    for f in sorted(carpeta.glob("11_*")):
        print(f"  -> {f.relative_to(cfg.rutas.salida.parent)}")


if __name__ == "__main__":
    main()
