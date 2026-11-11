"""Paso 15 — Aplicación del modelo sustituto a las 5 zonas que no se usaron para ajustarlo.

Para cada zona (GHI horaria 1998–2025, rutas.series_5):
  1. PSH, B y M con la misma planta común, definición de eventos y estimadores
     que las 51 series;
  2. kappa y E* (5, 2 y 1 %) simulados con el mismo simulador (la referencia);
  3. kappa PREDICHO con los modelos ajustados en las 51 series (paso 11):
     [PSH], [PSH, B] y [PSH, B, M], sin volver a ajustarlos.
El error de predicción en ln(kappa) es una validación fuera de muestra en
sitios nuevos.

Salidas: resultados/articulo2/15_zonas.xlsx y 15_zonas_resumen.json
Uso (desde codigo/):  python pipeline/15_zonas_aplicacion.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from _comun import titulo
from intermitencia import Config
from intermitencia.confiabilidad import curva_capacidad
from intermitencia.dimensionamiento import capacidad_para_lpsp
from intermitencia.eventos import eventos_diarios_centrados, metricas_intermitencia
from intermitencia.pv import GHI_STC
from intermitencia.sustituto import ajustar_kappa

METAS = [0.05, 0.02, 0.01]
MODELOS = ["PSH", "PSH+B", "PSH+B+M"]


def coeficientes(salida: Path) -> dict[str, dict[str, float]]:
    """Coeficientes de ln(kappa [MWh]) ajustados en las 51 series (paso 11)."""
    t = pd.read_excel(salida / "11_comparacion_modelos.xlsx").set_index("modelo")
    out = {}
    for m in MODELOS:
        f = t.loc[m]
        out[m] = {k: float(f[f"coef_{k}"]) for k in ("intercepto", "PSH", "B", "M")
                  if pd.notna(f.get(f"coef_{k}"))}
    return out


def main() -> None:
    cfg = Config.cargar()
    sc, ic = cfg.sustituto, cfg.intermitencia
    salida = cfg.rutas.salida / "articulo2"
    p_ref = float(sc["planta_referencia_mw"])
    caps = np.arange(0.0, float(sc["capacidad_max_mwh"]) + 1e-9, float(sc["capacidad_paso_mwh"]))
    coefs = coeficientes(salida)

    titulo("aplicación del modelo a las 5 zonas")
    ghi = pd.read_excel(cfg.rutas.series_5)
    ghi = ghi.set_index(pd.to_datetime(ghi.pop("fecha"))).astype(float)
    filas = []
    for z in ghi.columns:
        g = ghi[z]
        psh = float(g.sum() / 1000.0 / (len(g) / 24))
        bal = g * p_ref * cfg.planta.performance_ratio / GHI_STC - cfg.demanda_mw
        r = metricas_intermitencia(eventos_diarios_centrados(bal), umbral=ic.umbral_mw,
                                   base=ic.base_evento, min_eventos=ic.min_eventos,
                                   corregir_tamano_finito=ic.corregir_tamano_finito,
                                   metodo_memory=ic.metodo_memory)
        b = bal.to_numpy()
        lp = curva_capacidad(b, caps, cfg.bess, cfg.demanda_mw)["lpsp"].to_numpy()
        aj = ajustar_kappa(caps, lp, sc["ajuste_lpsp_min"], sc["ajuste_lpsp_max"])
        fila = {"Zona": z, "PSH": psh, "B": r["B"], "M": r["M"], "n_eventos": r["n_eventos"],
                "kappa_h": aj.kappa_mwh / cfg.demanda_mw, "L0": aj.l0, "r2_ley": aj.r2}
        x = {"PSH": psh, "B": r["B"], "M": r["M"]}
        for m in MODELOS:
            c = coefs[m]
            lk = c["intercepto"] + sum(c[k] * x[k] for k in c if k != "intercepto")
            fila[f"kappa_pred_{m}_h"] = float(np.exp(lk)) / cfg.demanda_mw
            fila[f"error_ln_{m}"] = float(lk - np.log(aj.kappa_mwh))
        for meta in METAS:
            fila[f"E_{meta:.0%}_h"] = capacidad_para_lpsp(b, meta, cfg.bess, cfg.demanda_mw) / cfg.demanda_mw
        filas.append(fila)
        print(f"  {z:14s} PSH={psh:.2f}  B={r['B']:+.3f}  M={r['M']:+.3f}  kappa={fila['kappa_h']:6.1f} h  "
              f"pred PSH={fila['kappa_pred_PSH_h']:6.1f}  PSH+B={fila['kappa_pred_PSH+B_h']:6.1f}  "
              f"E*1%={fila['E_1%_h']:6.1f} h")
    df = pd.DataFrame(filas)
    df.to_excel(salida / "15_zonas.xlsx", index=False)
    res = {f"rmse_ln_{m}": float(np.sqrt(np.mean(df[f"error_ln_{m}"] ** 2))) for m in MODELOS}
    res.update({f"error_abs_mediano_ln_{m}": float(df[f"error_ln_{m}"].abs().median()) for m in MODELOS})
    print(json.dumps(res, indent=2))
    (salida / "15_zonas_resumen.json").write_text(json.dumps(res, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
