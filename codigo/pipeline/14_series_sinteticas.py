"""Paso 14 — Series sintéticas: verificación de B y M y series sustitutas.

Parte A. VERIFICACIÓN DE LAS MÉTRICAS
    Secuencias de eventos con B y M conocidos (sinteticas.secuencia_renovacion).
    Para cada combinación de CV, rho y número de eventos n se calcula el sesgo
    y la dispersión de B (clásica y corregida por Kim y Jo) y de M.
    Pregunta: ¿las métricas recuperan los valores verdaderos con el número de
    eventos que tienen las 51 series?

Parte B. SERIES SUSTITUTAS DE LAS 51 SERIES
    Para cada sitio se compara la serie real con series del mismo sitio cuyos
    días se barajaron (sinteticas.barajar_dias):
      * "mes":  días barajados dentro de cada mes de cada año
                (conserva estacionalidad y años secos/húmedos);
      * "todo": todos los días barajados (solo conserva la distribución).
    En todas: misma PSH y misma distribución de energía diaria. Se calcula
    B, M, kappa y la capacidad E* para LPSP = 1 %, 2 % y 5 %.
    Pregunta: ¿cuánto del almacenamiento se debe al ORDEN de los días?

Salidas en resultados/articulo2/:
    14_verificacion_BM.xlsx      sesgo y dispersión de B y M (Parte A)
    14_sustitutos_sitios.xlsx    una fila por sitio y tipo de serie (Parte B)
    14_sustitutos_resumen.json   cifras para el texto

Uso (desde codigo/):
    python pipeline/14_series_sinteticas.py              # todo
    python pipeline/14_series_sinteticas.py --solo A     # solo verificación (segundos)
    python pipeline/14_series_sinteticas.py --solo B     # solo sustitutos (~30 min)
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from _comun import cronometro, subtitulo, titulo
from intermitencia import Config, io_datos
from intermitencia.confiabilidad import curva_capacidad
from intermitencia.dimensionamiento import capacidad_para_lpsp
from intermitencia.eventos import burstiness, eventos_diarios_centrados, memory, metricas_intermitencia
from intermitencia.pv import GHI_STC
from intermitencia.sinteticas import (b_teorica, barajar_dias, m_teorica,
                                      secuencia_renovacion)
from intermitencia.sustituto import ajustar_kappa

# ----------------------------------------------------------------- PARÁMETROS
SEMILLA = 2026
# Parte A
CVS = [0.6, 1.0, 1.5, 2.0]            # B verdadera: -0.25, 0, 0.20, 0.33
RHOS = [0.0, 0.3, 0.6]
NS = [30, 50, 100, 300, 1000]
REPETICIONES = 1000
# Parte B
REALIZACIONES = 6                      # series sustitutas por sitio y tipo
PASO_CURVA_MWH = 20.0                  # paso del barrido de capacidad
METAS = [0.05, 0.02, 0.01]
PROCESOS = 2                           # procesos en paralelo (núcleos)


# ===================================================================== A
def parte_a(salida: Path) -> pd.DataFrame:
    titulo("A. verificación de B y M con secuencias de valores conocidos")
    rng = np.random.default_rng(SEMILLA)
    filas = []
    for cv in CVS:
        for rho in RHOS:
            b_v, m_v = b_teorica(cv), m_teorica(cv, rho)
            for n in NS:
                bc, bk, mm = [], [], []
                for _ in range(REPETICIONES):
                    t = secuencia_renovacion(n, cv, rho, rng)
                    bc.append(burstiness(t, corregir_tamano_finito=False))
                    bk.append(burstiness(t, corregir_tamano_finito=True))
                    mm.append(memory(t))
                bc, bk, mm = map(np.asarray, (bc, bk, mm))
                filas.append({
                    "cv": cv, "rho": rho, "n_eventos": n, "B_verdadera": b_v, "M_verdadera": m_v,
                    "B_clasica_media": bc.mean(), "B_clasica_sesgo": bc.mean() - b_v,
                    "B_corregida_media": bk.mean(), "B_corregida_sesgo": bk.mean() - b_v,
                    "B_corregida_de": bk.std(ddof=1),
                    "M_media": mm.mean(), "M_sesgo": mm.mean() - m_v, "M_de": mm.std(ddof=1),
                })
    df = pd.DataFrame(filas)
    df.to_excel(salida / "14_verificacion_BM.xlsx", index=False)

    subtitulo("Sesgo medio absoluto según el número de eventos (todas las combinaciones)")
    t = df.groupby("n_eventos")[["B_clasica_sesgo", "B_corregida_sesgo", "M_sesgo"]].agg(
        lambda x: np.abs(x).mean())
    t["B_corregida_de"] = df.groupby("n_eventos")["B_corregida_de"].mean()
    t["M_de"] = df.groupby("n_eventos")["M_de"].mean()
    print(t.round(3).to_string())
    return df


# ===================================================================== B
def balance_a(ghi: pd.Series, p_mw: float, cfg: Config) -> pd.Series:
    return ghi * p_mw * cfg.planta.performance_ratio / GHI_STC - cfg.demanda_mw


def evaluar_serie(ghi: pd.Series, cfg: Config, caps: np.ndarray, p_ref: float) -> dict:
    ic, sc = cfg.intermitencia, cfg.sustituto
    bal = balance_a(ghi, p_ref, cfg)
    r = metricas_intermitencia(eventos_diarios_centrados(bal), umbral=ic.umbral_mw,
                               base=ic.base_evento, min_eventos=ic.min_eventos,
                               corregir_tamano_finito=ic.corregir_tamano_finito,
                               metodo_memory=ic.metodo_memory)
    lp = curva_capacidad(bal.to_numpy(), caps, cfg.bess, cfg.demanda_mw)["lpsp"].to_numpy()
    aj = ajustar_kappa(caps, lp, sc["ajuste_lpsp_min"], sc["ajuste_lpsp_max"])
    fila = {"B": r["B"], "M": r["M"], "n_eventos": r["n_eventos"],
            "kappa_h": aj.kappa_mwh / cfg.demanda_mw, "L0": aj.l0, "r2_ley": aj.r2}
    b = bal.to_numpy()
    for m in METAS:   # capacidad exacta por bisección sobre el simulador
        fila[f"E_{m:.0%}_h"] = capacidad_para_lpsp(b, m, cfg.bess, cfg.demanda_mw) / cfg.demanda_mw
    return fila


_G: dict = {}


def _iniciar(ghi, caps, p_ref):
    _G.update(ghi=ghi, caps=caps, p_ref=p_ref, cfg=Config.cargar())


def _sitio(tarea):
    """Serie real y sus sustitutas para un sitio (semilla propia por sitio)."""
    i, s = tarea
    g, caps, p_ref, cfg = _G["ghi"][s], _G["caps"], _G["p_ref"], _G["cfg"]
    rng = np.random.default_rng([SEMILLA, i])
    psh = float(g.sum() / 1000.0 / (len(g) / 24))
    filas = [{"Serie": s, "tipo": "real", "realizacion": 0, "PSH": psh,
              **evaluar_serie(g, cfg, caps, p_ref)}]
    for amb in ("mes", "todo"):
        for k in range(REALIZACIONES):
            filas.append({"Serie": s, "tipo": amb, "realizacion": k + 1, "PSH": psh,
                          **evaluar_serie(barajar_dias(g, rng, amb), cfg, caps, p_ref)})
    d = pd.DataFrame(filas).groupby("tipo").mean(numeric_only=True)
    print(f"  {s:28s} B {d.loc['real','B']:+.2f} {d.loc['mes','B']:+.2f} {d.loc['todo','B']:+.2f} | "
          f"kappa {d.loc['real','kappa_h']:5.1f} {d.loc['mes','kappa_h']:5.1f} {d.loc['todo','kappa_h']:5.1f} h | "
          f"E*1% {d.loc['real','E_1%_h']:6.1f} {d.loc['mes','E_1%_h']:6.1f} {d.loc['todo','E_1%_h']:6.1f} h",
          flush=True)
    return filas


def parte_b(salida: Path, cfg: Config) -> pd.DataFrame:
    titulo("B. series sustitutas de las 51 series (días barajados)")
    sc = cfg.sustituto
    p_ref = float(sc["planta_referencia_mw"])
    caps = np.arange(0.0, float(sc["capacidad_max_mwh"]) + 1e-9, PASO_CURVA_MWH)
    print(f"Planta común {p_ref:.0f} MW · {REALIZACIONES} realizaciones por sitio y tipo · "
          f"barrido 0–{caps[-1]:.0f} MWh cada {PASO_CURVA_MWH:.0f} MWh")
    ghi = io_datos.leer_series_horarias(cfg.rutas.series_51, cfg.rutas.cache)
    tareas = [(i, s) for i, s in enumerate(ghi.columns)]
    with cronometro("simulación"):
        with ProcessPoolExecutor(max_workers=PROCESOS, initializer=_iniciar,
                                 initargs=(ghi, caps, p_ref)) as ex:
            bloques = list(ex.map(_sitio, tareas))
    filas = [f for b in bloques for f in b]
    df = pd.DataFrame(filas)
    df.to_excel(salida / "14_sustitutos_sitios.xlsx", index=False)
    return df


def resumen_b(df: pd.DataFrame, salida: Path) -> dict:
    subtitulo("Descomposición del almacenamiento necesario")
    m = df.groupby(["Serie", "tipo"]).mean(numeric_only=True).unstack("tipo")
    res = {"n_sitios": int(m.shape[0]), "realizaciones": REALIZACIONES}
    for v in ["B", "M", "kappa_h"] + [f"E_{x:.0%}_h" for x in METAS]:
        for t in ("real", "mes", "todo"):
            res[f"{v}_{t}_mediana"] = float(m[(v, t)].median())
    for x in METAS:
        c = f"E_{x:.0%}_h"
        real, mes, todo = m[(c, "real")], m[(c, "mes")], m[(c, "todo")]
        res[f"{c}_frac_orden_total_mediana"] = float(((real - todo) / real).median())
        res[f"{c}_frac_rachas_corto_plazo_mediana"] = float(((real - mes) / real).median())
        res[f"{c}_razon_real_todo_mediana"] = float((real / todo).median())
        res[f"{c}_sitios_real_mayor_que_todo"] = int((real > todo).sum())
    res["kappa_razon_real_todo_mediana"] = float((m[("kappa_h", "real")] / m[("kappa_h", "todo")]).median())
    res["kappa_razon_real_mes_mediana"] = float((m[("kappa_h", "real")] / m[("kappa_h", "mes")]).median())
    dk = np.log(m[("kappa_h", "real")]) - np.log(m[("kappa_h", "todo")])
    db = m[("B", "real")] - m[("B", "todo")]
    res["corr_deltaB_deltalnkappa"] = float(np.corrcoef(db, dk)[0, 1])
    for k, v in res.items():
        print(f"  {k:45s} {v:.3f}" if isinstance(v, float) else f"  {k:45s} {v}")
    (salida / "14_sustitutos_resumen.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", choices=["A", "B"])
    a = ap.parse_args()
    cfg = Config.cargar()
    salida = cfg.rutas.salida / "articulo2"
    salida.mkdir(parents=True, exist_ok=True)
    if a.solo in (None, "A"):
        parte_a(salida)
    if a.solo in (None, "B"):
        resumen_b(parte_b(salida, cfg), salida)


if __name__ == "__main__":
    main()
