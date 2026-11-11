"""Paso 2 — Métricas de intermitencia B y M para las 51 series.

Calcula B y M con la metodología corregida y, en paralelo, reproduce el
método antiguo para poder cuantificar en la tesis cuánto cambian.

Salidas:
    resultados/02_intermitencia.xlsx        (B y M nuevos, por serie)
    resultados/02_comparacion_metodos.xlsx  (nuevo vs antiguo)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from _comun import cargar_balances, cronometro, guardar, preparar, subtitulo, titulo
from intermitencia import pv
from intermitencia.eventos import (
    agregar_memory_fisher,
    burstiness_legacy_cruces,
    eventos_diarios_centrados,
    indicadores_simples,
    metricas_intermitencia,
)


def metricas_legacy_por_serie(balance: pd.Series, percentil: float = 25.0) -> dict:
    """Reproduce el flujo del ByM.py original: por hora del día, y promedia.

    El original: excedentes -> pivote día x hora -> B y M por hora ->
    media aritmética entre horas. Se replica igual para que la
    comparación sea justa, incluyendo el promedio aritmético de M (que es
    uno de los defectos).
    """
    excedente = balance.clip(lower=0.0)
    horas = excedente.index.hour

    bs, ms, ns, ceros = [], [], [], []
    for h in range(24):
        x = excedente[horas == h].to_numpy()
        if x.size < 5 or x.sum() == 0:
            continue
        r = burstiness_legacy_cruces(x, percentil=percentil)
        if np.isnan(r["B_legacy"]):
            continue
        bs.append(r["B_legacy"])
        ms.append(r["M_legacy"])
        ns.append(r["n_tau_legacy"])
        ceros.append(r["frac_tau_cero"])

    if not bs:
        return {"B_legacy": np.nan, "M_legacy": np.nan,
                "frac_tau_cero_legacy": np.nan, "horas_usadas_legacy": 0}

    return {
        "B_legacy": float(np.mean(bs)),
        "M_legacy": float(np.mean(ms)),          # media aritmética, como el original
        "frac_tau_cero_legacy": float(np.mean(ceros)),
        "horas_usadas_legacy": len(bs),
    }


def main() -> None:
    cfg = preparar()
    ic = cfg.intermitencia

    titulo("métricas de intermitencia b y m")
    print(f"Base del evento      : {ic.base_evento}")
    print(f"Resolución           : {ic.resolucion}")
    print(f"Mínimo de eventos    : {ic.min_eventos}")
    print(f"Corrección Kim & Jo  : {'sí' if ic.corregir_tamano_finito else 'no'}")
    print(f"Método de memoria    : {ic.metodo_memory}")

    with cronometro("lectura"):
        gen, balance = cargar_balances(cfg)
    ghi = gen / pv.factor_ghi_a_mw(cfg.planta)

    # Tarea A3: B y M con la MISMA planta que kappa (configurable).
    if ic.planta_eventos == "referencia":
        p_ev = float(cfg.sustituto["planta_referencia_mw"])
        balance = ghi * pv.factor_ghi_a_mw(cfg.planta) * p_ev / cfg.planta.potencia_mw - cfg.demanda_mw
    else:
        p_ev = cfg.planta.potencia_mw
    print(f"Planta de los eventos: {p_ev:.0f} MW ({ic.planta_eventos})")

    filas = []
    with cronometro("cálculo"):
        for s in balance.columns:
            b = balance[s]

            kw = dict(umbral=ic.umbral_mw, base=ic.base_evento,
                      min_eventos=ic.min_eventos,
                      corregir_tamano_finito=ic.corregir_tamano_finito,
                      metodo_memory=ic.metodo_memory)

            # --- las dos resoluciones se calculan siempre (tarea A1) -------
            # Diaria: déficit diario centrado; elimina el ciclo diurno, de
            # modo que B y M miden rachas meteorológicas, no la noche.
            m_d = metricas_intermitencia(eventos_diarios_centrados(b), **kw)
            m_h = metricas_intermitencia(b.to_numpy(), **kw)
            m = m_d if ic.resolucion == "diaria" else m_h
            m = dict(m)
            m["B_diaria"], m["M_diaria"] = m_d["B"], m_d["M"]
            m["n_eventos_diaria"] = m_d["n_eventos"]
            m["B_horaria"], m["M_horaria"] = m_h["B"], m_h["M"]
            m["n_eventos_horaria"] = m_h["n_eventos"]
            m.update(indicadores_simples(ghi[s], b))

            # --- B y M por hora del día: solo tiene sentido en modo horario
            b_h, m_hh, n_h = [], [], []
            if ic.resolucion == "horaria":
                horas = b.index.hour
                for h in range(24):
                    r = metricas_intermitencia(b[horas == h].to_numpy(), **kw)
                    if not np.isnan(r["B"]):
                        b_h.append(r["B"])
                        m_hh.append(r["M"])
                        n_h.append(r["n_eventos"])

            m["B_horario_medio"] = float(np.mean(b_h)) if b_h else np.nan
            # M se agrega por Fisher, no aritméticamente
            m["M_horario_fisher"] = (
                agregar_memory_fisher(np.array(m_hh), np.array(n_h))
                if m_hh else np.nan
            )
            m["horas_validas"] = len(b_h)
            m["planta_eventos_mw"] = p_ev

            # --- método antiguo, para comparar ---------------------------
            m.update(metricas_legacy_por_serie(b))
            m["Serie"] = s
            filas.append(m)

    df = pd.DataFrame(filas).set_index("Serie")
    cols = ["B", "M", "n_eventos", "tau_medio_h", "duracion_media_h",
            "severidad_p50_mwh", "severidad_p90_mwh", "severidad_max_mwh",
            "B_horario_medio", "M_horario_fisher", "horas_validas",
            "B_legacy", "M_legacy", "frac_tau_cero_legacy"]
    df = df[cols + [c for c in df.columns if c not in cols]]

    titulo("resultados (primeras 12 series)")
    print(
        df[["B", "M", "n_eventos", "severidad_p90_mwh",
            "B_legacy", "M_legacy", "frac_tau_cero_legacy"]]
        .head(12).round(4).to_string()
    )

    subtitulo("Comparación de metodologías, sobre las 51 series")

    b_n, b_l = df["B"].dropna(), df["B_legacy"].dropna()
    m_n, m_l = df["M"].dropna(), df["M_legacy"].dropna()

    print(f"{'':22s} {'nuevo':>18s} {'antiguo':>18s}")
    print(f"{'B  media':22s} {b_n.mean():>18.4f} {b_l.mean():>18.4f}")
    print(f"{'B  rango':22s} "
          f"{f'[{b_n.min():.3f}, {b_n.max():.3f}]':>18s} "
          f"{f'[{b_l.min():.3f}, {b_l.max():.3f}]':>18s}")
    print(f"{'M  media':22s} {m_n.mean():>18.4f} {m_l.mean():>18.4f}")
    print(f"{'M  rango':22s} "
          f"{f'[{m_n.min():.3f}, {m_n.max():.3f}]':>18s} "
          f"{f'[{m_l.min():.3f}, {m_l.max():.3f}]':>18s}")

    comun = df[["B", "M", "B_legacy", "M_legacy"]].dropna()
    if len(comun) > 2:
        rb = np.corrcoef(comun["B"], comun["B_legacy"])[0, 1]
        rm = np.corrcoef(comun["M"], comun["M_legacy"])[0, 1]
        print(f"\nCorrelación entre métodos:   B: r = {rb:+.3f}    M: r = {rm:+.3f}")
        print(
            "  Una correlación baja significa que el método antiguo y el nuevo\n"
            "  NO ordenan las series igual: los B y M publicados hasta ahora no\n"
            "  son un proxy del comportamiento real de intermitencia."
        )

    cambio_signo_m = int((np.sign(comun["M"]) != np.sign(comun["M_legacy"])).sum())
    print(f"\nSeries donde M CAMBIA DE SIGNO: {cambio_signo_m} de {len(comun)}")
    print(f"Fracción media de tau = 0 en el método antiguo: "
          f"{df['frac_tau_cero_legacy'].mean():.1%}")
    print("  (los tau = 0 no tienen sentido físico: son el defecto central\n"
          "   del método de cruces sobre una suma acumulada monótona)")

    titulo("guardado")
    guardar(df.reset_index(), cfg, "02_intermitencia.xlsx")
    guardar(
        df[["B", "M", "B_legacy", "M_legacy", "frac_tau_cero_legacy"]].reset_index(),
        cfg, "02_comparacion_metodos.xlsx",
    )

    print("\nListo. Siguiente paso:  pipeline/03_curvas.py")


if __name__ == "__main__":
    main()
