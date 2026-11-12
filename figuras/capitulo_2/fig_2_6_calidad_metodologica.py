"""Figura 2.6 — Evaluación de calidad metodológica de los 36 estudios (Q1–Q10).

Barras apiladas con el porcentaje de estudios que cumplen (Yes), cumplen
parcialmente (Partial) o no cumplen (No) cada criterio, agrupadas por
dimensión. Cifras de Tuirán et al. (2026), tabla de calidad metodológica.

Salida: capitulo_2/Calidad_metodologica.pdf
Para corregir una cifra, editar CRITERIOS (número de estudios: sí, parcial, no).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt  # noqa: E402

import estilo  # noqa: E402
from comun_tesis import GRIS, NARANJA, ROJO, VERDE, guardar  # noqa: E402

TOTAL = 36
# (código, texto corto, dimensión, sí, parcial, no)
CRITERIOS = [
    ("Q1", "Defines the PV phenomenon", "Conceptual clarity", 35, 1, 0),
    ("Q2", "Distinguishes intermittency", "Conceptual clarity", 4, 23, 9),
    ("Q3", "Reproducible representation", "Intermittency representation", 36, 0, 0),
    ("Q4", "Adequate data and resolution", "Intermittency representation", 12, 24, 0),
    ("Q5", "Scenario or stochastic framework", "Intermittency representation", 34, 2, 0),
    ("Q6", "Justified assumptions", "Methodological rigor", 34, 2, 0),
    ("Q7", "Impact on reliability indicators", "Methodological rigor", 34, 2, 0),
    ("Q8", "Methods consistent with aims", "Methodological rigor", 36, 0, 0),
    ("Q9", "Conclusions supported", "Validation and comparison", 36, 0, 0),
    ("Q10", "Comparable detail", "Validation and comparison", 35, 1, 0),
]
COLORES = {"Yes": VERDE, "Partial": NARANJA, "No": ROJO}
IZQ = 2.30


def main() -> None:
    estilo.aplicar_estilo()
    n = len(CRITERIOS)
    alto_ej = 0.24 * n
    alto = 0.30 + alto_ej + 0.80
    fig = plt.figure(figsize=(estilo.ANCHO, alto))
    ax = fig.add_axes([IZQ / estilo.ANCHO, 0.80 / alto,
                       (estilo.ANCHO - IZQ - 0.30) / estilo.ANCHO, alto_ej / alto])
    ys = list(range(n))[::-1]
    for y, (cod, texto, _dim, si, par, no) in zip(ys, CRITERIOS):
        izq = 0.0
        for etiqueta, v in (("Yes", si), ("Partial", par), ("No", no)):
            pct = 100 * v / TOTAL
            ax.barh(y, pct, left=izq, color=COLORES[etiqueta], height=0.70,
                    label=etiqueta if y == ys[0] else None)
            if pct >= 9:
                ax.text(izq + pct / 2, y, f"{pct:.0f}", ha="center", va="center",
                        fontsize=7.5, color="white")
            izq += pct
    ax.set_yticks(ys, [f"{c[0]}  {c[1]}" for c in CRITERIOS], fontsize=8)
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xlabel("Share of the 36 studies [%]", fontsize=9)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0, right=False)
    ax.tick_params(axis="x", labelsize=8, top=False)
    # Separadores entre dimensiones
    dims = [c[2] for c in CRITERIOS]
    for i in range(1, n):
        if dims[i] != dims[i - 1]:
            ax.axhline(ys[i] + 0.5, color=GRIS, lw=0.8)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=3, frameon=False,
              fontsize=8, handlelength=1.2)
    guardar(fig, "capitulo_2", "Calidad_metodologica")


if __name__ == "__main__":
    main()
