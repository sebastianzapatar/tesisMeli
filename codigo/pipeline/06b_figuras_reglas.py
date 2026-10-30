"""Paso 6b — Figuras F8 y F9 (objetivo 3, reglas de operación).

Script independiente: no requiere modificar 06_figuras.py. Lee los
resultados del paso 08 y genera las dos figuras que necesita la
Sección 7 del informe (07_informe.py).

Requiere haber corrido antes pipeline/08_reglas_operacion.py.

Salidas:
    resultados/figuras/F8_comparacion_reglas_operacion.png
    resultados/figuras/F9_sensibilidad_reglas_operacion.png
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from _comun import preparar, titulo

try:
    from intermitencia import viz
    from intermitencia.viz import AZUL, GRIS, NARANJA, VERDE
    _HAY_VIZ = True
except Exception:  # noqa: BLE001
    _HAY_VIZ = False
    AZUL, NARANJA, VERDE, GRIS = "#2a78d6", "#eb6834", "#2e8b57", "#6f6f6a"

MORADO = "#7B4B94"


def _eje(ax, xlabel, ylabel, title=None):
    if _HAY_VIZ:
        viz.eje(ax, xlabel, ylabel, title) if title else viz.eje(ax, xlabel, ylabel)
    else:
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if title:
            ax.set_title(title, fontsize=9)
        ax.grid(axis="y", alpha=0.25)


def _guardar(fig, carpeta: Path, nombre: str) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(carpeta / f"{nombre}.{ext}", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"  ok  {carpeta / (nombre + '.png')}")


def fig_comparacion_reglas(cfg, reglas_resumen: pd.DataFrame) -> None:
    """F8 — Las cinco reglas, mediana y rango p10-p90 entre series."""
    reglas = ["R1", "R2", "R3", "R4", "R5"]
    colores = [GRIS, AZUL, NARANJA, VERDE, MORADO]
    r = reglas_resumen.set_index("regla").loc[reglas]

    fig, axes = plt.subplots(2, 2, figsize=(9.2, 7.2))
    paneles = [
        (axes[0, 0], "lpsp", "LPSP"),
        (axes[0, 1], "cobertura_deficit", "Cobertura de déficit"),
        (axes[1, 0], "frac_vertida", "Fracción vertida"),
        (axes[1, 1], "ciclos_equivalentes", "Ciclos equivalentes"),
    ]
    for ax, col, etq in paneles:
        p50 = r[f"{col}_p50"].to_numpy()
        abajo = np.clip(p50 - r[f"{col}_p10"].to_numpy(), 0, None)
        arriba = np.clip(r[f"{col}_p90"].to_numpy() - p50, 0, None)
        ax.bar(reglas, p50, color=colores, zorder=3)
        ax.errorbar(reglas, p50, yerr=[abajo, arriba], fmt="none",
                    ecolor="#333333", elinewidth=1.1, capsize=3, zorder=4)
        _eje(ax, "", etq)

    fig.suptitle(
        "Comparación de las cinco reglas de despacho, a la capacidad ya optimizada\n"
        "(mediana y rango p10\u2013p90 entre series)",
        x=0.02, ha="left", fontsize=10,
    )
    fig.tight_layout()
    _guardar(fig, cfg.rutas.figuras, "F8_comparacion_reglas_operacion")


def fig_sensibilidad_reglas(cfg, resumen_sens: pd.DataFrame) -> None:
    """F9 — Cada regla frente a su propio parámetro."""
    especificacion = [
        ("R2", "soc_res", "lpsp", "SOC de reserva", "LPSP", AZUL),
        ("R3", "ventana_horaria", "lpsp", "Ventana horaria", "LPSP", NARANJA),
        ("R4", "ventana_suavizado_h", "suavidad_rampa_mw", "W [h]",
         "Suavidad de rampa [MW]", VERDE),
        ("R5", "l_min_h", "ciclos_equivalentes", "L_min [h]",
         "Ciclos equivalentes", MORADO),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(9.2, 7.2))
    for ax, (regla, parametro, col, etq_x, etq_y, color) in zip(axes.flat, especificacion):
        sub = (resumen_sens[(resumen_sens["regla"] == regla)
                            & (resumen_sens["parametro"] == parametro)]
               .sort_values("orden_valor"))
        x = np.arange(len(sub))
        ax.plot(x, sub[f"{col}_p50"], "o-", color=color, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(sub["valor_parametro"], fontsize=8)
        _eje(ax, etq_x, etq_y, regla)

    fig.suptitle(
        "Sensibilidad de cada regla a su propio parámetro\n"
        "(mediana sobre las series evaluadas; los demás parámetros quedan en su valor por defecto)",
        x=0.02, ha="left", fontsize=10,
    )
    fig.tight_layout()
    _guardar(fig, cfg.rutas.figuras, "F9_sensibilidad_reglas_operacion")


def main() -> None:
    cfg = preparar()
    sal = cfg.rutas.salida
    titulo("figuras F8 y F9 (reglas de operación)")

    for nombre in ("08_reglas_operacion_resumen.xlsx", "08_sensibilidad_resumen.xlsx"):
        if not (sal / nombre).exists():
            raise FileNotFoundError(
                f"Falta {sal / nombre}. Corra primero pipeline/08_reglas_operacion.py."
            )

    reglas_resumen = pd.read_excel(sal / "08_reglas_operacion_resumen.xlsx")
    sens_resumen = pd.read_excel(sal / "08_sensibilidad_resumen.xlsx")

    fig_comparacion_reglas(cfg, reglas_resumen)
    fig_sensibilidad_reglas(cfg, sens_resumen)

    print("\nListo. Ahora puede correr:  python pipeline/07_informe.py")


if __name__ == "__main__":
    main()
