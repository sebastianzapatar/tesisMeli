"""Estilo de figuras y paleta validada.

Estilo
------
Se conserva el estilo de la tesis: ticks hacia adentro en los cuatro
lados, marco completo, rejilla discreta, tipografía de 10 pt. Es
coherente con lo ya escrito y apropiado para publicación.

Paleta
------
Los colores del gráfico de B y M original (``#fee08b`` amarillo y
``#abd9e9`` azul claro) **reprueban** la validación de accesibilidad:

* ambos fuera de la banda de luminancia (0.913 y 0.858 vs 0.43-0.77);
* el azul cae por debajo del piso de croma: lee como gris;
* contraste contra el fondo de 1.26:1 y 1.48:1, por debajo del mínimo
  de 3:1.

Además son dos extremos de una paleta **divergente** (RdYlBu) usados para
dos series **categóricas**, que es un uso incorrecto: una paleta
divergente codifica polaridad respecto de un punto medio neutro, no
identidad.

Los reemplazos de abajo pasan las seis verificaciones (ΔE 24.7 con
protanopia, 33.6 en visión normal, contraste sobre 3:1).

Reglas que se siguen
--------------------
* Nunca dos ejes Y. ``Capacidad inicial.py`` tenía uno, y ahí era además
  incorrecto: la conversión % <-> MWh depende de la PSH, que varía por
  serie, así que el eje derecho no era una reetiquetación lineal.
* Secuencial = un solo tono claro->oscuro para magnitud.
* Divergente = dos tonos con **gris neutro** en el medio, solo para
  cantidades con signo.
* Leyenda siempre presente con dos o más series.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import AutoMinorLocator

__all__ = ["aplicar_estilo", "eje", "guardar", "AZUL", "NARANJA", "VERDE", "GRIS"]

# --- paleta categórica validada --------------------------------------
AZUL = "#2a78d6"
NARANJA = "#eb6834"
VERDE = "#1baf7a"
GRIS = "#8a8a85"
TINTA = "#1a1a19"

CATEGORICA = [AZUL, NARANJA, VERDE]

# Secuencial de un solo tono (magnitud) y divergente con centro neutro.
SECUENCIAL = "viridis"
DIVERGENTE = "RdBu_r"


def aplicar_estilo() -> None:
    """Aplica el estilo de la tesis a matplotlib."""
    mpl.rcParams.update(
        {
            "figure.dpi": 130,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 10,
            "legend.fontsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRIS,
            "grid.alpha": 0.30,
            "grid.linewidth": 0.6,
            "lines.linewidth": 2.0,
            "lines.markersize": 5,
            "legend.frameon": False,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.top": True,
            "ytick.right": True,
            "xtick.major.size": 6,
            "ytick.major.size": 6,
            "xtick.minor.size": 3,
            "ytick.minor.size": 3,
            "axes.prop_cycle": mpl.cycler(color=CATEGORICA),
            "text.color": TINTA,
            "axes.labelcolor": TINTA,
            "xtick.color": TINTA,
            "ytick.color": TINTA,
        }
    )


def eje(ax, xlabel: str = "", ylabel: str = "", titulo: str = "") -> None:
    """Aplica los ticks menores y las etiquetas de forma consistente."""
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if titulo:
        ax.set_title(titulo, loc="left", pad=8)
    if ax.get_xscale() == "linear":
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    if ax.get_yscale() == "linear":
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))


def guardar(fig, destino: Path, nombre: str) -> Path:
    """Guarda en PNG (para revisar) y PDF (para LaTeX)."""
    destino.mkdir(parents=True, exist_ok=True)
    png = destino / f"{nombre}.png"
    fig.savefig(png)
    fig.savefig(destino / f"{nombre}.pdf")
    plt.close(fig)
    return png


def anotar_ajuste(ax, x, y, color: str = NARANJA, etiqueta: str | None = None):
    """Dibuja una recta de mínimos cuadrados con su R² anotado."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 3:
        return
    m, b = np.polyfit(x[ok], y[ok], 1)
    r = np.corrcoef(x[ok], y[ok])[0, 1]
    xx = np.linspace(x[ok].min(), x[ok].max(), 50)
    ax.plot(xx, m * xx + b, color=color, lw=1.8, ls="--",
            label=etiqueta or f"ajuste ($r={r:+.2f}$)")
    return r
