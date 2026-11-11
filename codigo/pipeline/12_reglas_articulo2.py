"""Paso 12 — Reglas de operación del BESS dimensionado (artículo 2, §3.10).

Para cada sitio y cada meta de LPSP, toma la capacidad E* que la cumple
con despacho directo (R1, paso 10) y simula el mismo BESS con la reserva
mínima de SOC (R2) y con la ventana de descarga vespertina (R3). Reporta
LPSP, cobertura del déficit, fracción vertida, ciclos equivalentes y
suavidad de rampa, y relaciona la ganancia de cada regla frente a R1 con
B y M (correlación de Spearman entre sitios).

Cota de previsión perfecta (tarea C3): en ventanas aleatorias de cada
sitio se resuelve por programación lineal el despacho que minimiza la
ENS conociendo el futuro, y se compara con R1 en la misma ventana.

Salidas: resultados/articulo2/12_reglas.xlsx, 12_reglas_resumen.xlsx,
12_reglas_vs_BM.xlsx, 12_cota_lp.xlsx.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd
from scipy import stats

from _comun import cronometro, subtitulo, titulo
from intermitencia import Config, io_datos
from intermitencia.almacenamiento import ens_minima_prevision_perfecta, simular_soc
from intermitencia.pv import GHI_STC
from intermitencia.reglas_operacion import simular_regla


def main() -> None:
    cfg = Config.cargar()
    ra = cfg.crudo["reglas_articulo2"]
    carpeta = cfg.rutas.salida / "articulo2"
    costos = pd.read_excel(carpeta / "10_costo_planta_comun.xlsx")
    sitios = pd.read_excel(carpeta / "10_sitios.xlsx").set_index("Serie")
    p_ref = float(cfg.sustituto["planta_referencia_mw"])
    b = cfg.bess

    titulo("reglas de operación a la capacidad E* de cada meta")
    ghi = io_datos.leer_series_horarias(cfg.rutas.series_51, cfg.rutas.cache)
    horas = ghi.index.hour.to_numpy()
    comunes = dict(demanda_mw=cfg.demanda_mw, eficiencia_carga=b.eff_carga,
                   eficiencia_descarga=b.eff_descarga, soc_min=b.soc_min_frac,
                   soc_max=b.soc_max_frac, soc_inicial=b.soc_inicial_frac,
                   horas_del_dia=horas, soc_res=float(ra["soc_res"]),
                   ventana_horaria=tuple(ra["ventana_horaria"]))
    filas = []
    with cronometro("simulación"):
        for _, c in costos.iterrows():
            e = float(c.e_star_sim_mwh)
            if not np.isfinite(e) or e <= 0:
                continue
            bal = ghi[c.Serie].to_numpy() * p_ref * cfg.planta.performance_ratio / GHI_STC - cfg.demanda_mw
            for regla in ra["reglas"]:
                r = simular_regla(bal, e, e / b.duracion_h, regla, **comunes)
                fila = {"Serie": c.Serie, "meta_lpsp": c.meta_lpsp, "e_star_mwh": e}
                fila.update(r.resumen())
                filas.append(fila)
    df = pd.DataFrame(filas)
    base = df[df.regla == "R1"].set_index(["Serie", "meta_lpsp"])["lpsp"]
    df["lpsp_R1"] = df.set_index(["Serie", "meta_lpsp"]).index.map(base)
    df["razon_lpsp_vs_R1"] = df.lpsp / df.lpsp_R1

    resumen = (df.groupby(["meta_lpsp", "regla"])
               [["lpsp", "razon_lpsp_vs_R1", "cobertura_deficit", "frac_vertida",
                 "ciclos_equivalentes", "suavidad_rampa_mw"]].median().reset_index())
    subtitulo("Medianas de los 51 sitios")
    print(resumen.round(4).to_string(index=False))

    filas_bm = []
    for (meta, regla), g in df[df.regla != "R1"].groupby(["meta_lpsp", "regla"]):
        g = g.set_index("Serie").join(sitios[["B", "M", "PSH"]])
        for v in ("B", "M", "PSH"):
            rho, p = stats.spearmanr(g[v], g.razon_lpsp_vs_R1)
            filas_bm.append({"meta_lpsp": meta, "regla": regla, "variable": v, "rho": rho, "p": p})
    bm = pd.DataFrame(filas_bm)
    subtitulo("Ganancia frente a R1 vs B, M y PSH (Spearman)")
    print(bm.round(3).to_string(index=False))

    subtitulo("Cota de previsión perfecta (programación lineal) frente a R1")
    rng = np.random.default_rng(cfg.semilla)
    largo = int(ra["lp_dias_por_ventana"]) * 24
    filas_lp = []
    with cronometro("programación lineal"):
        sel = costos[np.isclose(costos.meta_lpsp, float(ra["lp_meta_lpsp"]))]
        for _, c in sel.iterrows():
            e = float(c.e_star_sim_mwh)
            bal = ghi[c.Serie].to_numpy() * p_ref * cfg.planta.performance_ratio / GHI_STC - cfg.demanda_mw
            for _ in range(int(ra["lp_ventanas_por_sitio"])):
                i0 = int(rng.integers(0, bal.size - largo))
                w = bal[i0:i0 + largo]
                r1 = simular_soc(w, e, b).ens_total
                lp = ens_minima_prevision_perfecta(w, e, b)
                filas_lp.append({"Serie": c.Serie, "e_star_mwh": e, "inicio_h": i0,
                                 "ens_R1_mwh": r1, "ens_lp_mwh": lp, "brecha_mwh": r1 - lp})
    lpdf = pd.DataFrame(filas_lp)
    print(f"  {len(lpdf)} ventanas de {largo // 24} días; ENS de R1 en ellas: "
          f"{lpdf.ens_R1_mwh.sum():,.0f} MWh; brecha máxima R1 - LP: {lpdf.brecha_mwh.max():.2e} MWh")

    titulo("guardado")
    lpdf.to_excel(carpeta / "12_cota_lp.xlsx", index=False)
    df.to_excel(carpeta / "12_reglas.xlsx", index=False)
    resumen.to_excel(carpeta / "12_reglas_resumen.xlsx", index=False)
    bm.to_excel(carpeta / "12_reglas_vs_BM.xlsx", index=False)
    for f in sorted(carpeta.glob("12_*")):
        print(f"  -> {f.relative_to(cfg.rutas.salida.parent)}")


if __name__ == "__main__":
    main()
