"""Figura 1.1 — Participación de las renovables en la generación eléctrica.

Fuente: IEA (2025), hoja "Generacion" de Inversiones.xlsx.
Entrada:  capitulo_1/datos/Inversiones.xlsx
Salida:   salida/capitulo_1/Generation.pdf   (\\includegraphics en el cap. 1)
"""

from __future__ import annotations

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))          # para importar estilo.py

import pandas as pd
from matplotlib.ticker import MultipleLocator

from estilo import crear_figura, formatear_eje, guardar, holgura

DATOS = AQUI / "datos" / "Inversiones.xlsx"
ANIO_INICIO = 2014

COLORES = {
    "Solar PV": "#FDB813",
    "Eólica": "#4CAF50",
    "Hidroeléctrica": "#1E88E5",
    "Otras": "#7E57C2",
}
ETIQUETAS = {
    "Solar PV": "Solar PV",
    "Eólica": "Wind",
    "Hidroeléctrica": "Hydropower",
    "Otras": "Other",
}


def main() -> None:
    df = pd.read_excel(DATOS, sheet_name="Generacion")
    df = df[df["Año"] >= ANIO_INICIO]

    # margen inferior mayor: ahí van los años, "Year" y la leyenda
    fig, ax = crear_figura(ncols=1, margen_inf=0.85)

    for col in df.columns[1:]:
        color = COLORES.get(col)
        # una bolita en cada año (mismo estilo que la figura de los tres días)
        ax.plot(df["Año"], df[col], label=ETIQUETAS.get(col, col), color=color,
                marker="o", ms=3.5, mfc=color, mec="white", mew=0.5, zorder=3)
        ax.fill_between(df["Año"], df[col], 0, color=color, alpha=0.12)

    # X: marcas mayores cada 5 años y 5 subdivisiones -> una marca menor por año
    ax.xaxis.set_major_locator(MultipleLocator(5))
    formatear_eje(ax, xlabel="Year", ylabel="Electricity generation [%]", menores_x=5)
    holgura(ax, "x")          # espacio entre el marco y el inicio de los datos
    holgura(ax, "y")

    ax.legend(ncol=4, loc="upper center",
              bbox_to_anchor=(0.5, -0.19), borderaxespad=0)

    guardar(fig, "capitulo_1", "Generation")


if __name__ == "__main__":
    main()
