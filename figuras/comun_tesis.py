"""Utilidades comunes a las figuras de los capítulos 1 a 3 de la tesis.

Qué hay aquí
------------
* Rutas: agrega ``codigo/src/`` (paquete ``intermitencia``) y ``figuras/``
  (``estilo.py`` y ``sitios_ilustrativos.py``) al ``sys.path``,
  para que cada script se pueda correr solo, sin instalar nada.
* La misma paleta de las figuras del artículo 2.
* Funciones para dibujar ESQUEMAS (cajas y flechas) en un lienzo medido en
  pulgadas: así un esquema se edita cambiando coordenadas y textos en un
  diccionario al inicio de cada script, sin tocar el código de dibujo.

Todas las figuras se guardan con ``estilo.guardar`` en
``figuras/capitulo_N/``, junto al script que la hace (PDF para LaTeX y PNG para revisar).
"""

from __future__ import annotations

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent            # figuras/
RAIZ = AQUI.parent                                # raíz del repositorio
for ruta in (RAIZ / "codigo" / "src", AQUI):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

import matplotlib.pyplot as plt                   # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

import estilo                                     # noqa: E402
from estilo import guardar                        # noqa: E402,F401

# ---------------------------------------------------------------------
# Paleta (idéntica a sitios_ilustrativos.py)
# ---------------------------------------------------------------------
AZUL = "#2a78d6"
NARANJA = "#eb6834"
VERDE = "#1baf7a"
GRIS = "#6b6b6b"
SOLAR = "#FDB813"
SOLAR_LINEA = "#E39400"
ROJO = "#c8553d"
MORADO = "#7a5fb0"
TINTA = "#333333"
GRIS_CLARO = "#e9e9e9"


# =====================================================================
# ESQUEMAS
# =====================================================================
def lienzo(alto: float, ancho: float = estilo.ANCHO):
    """Figura con un único eje sin marco cuyas unidades son PULGADAS.

    ``(0, 0)`` es la esquina inferior izquierda y ``(ancho, alto)`` la
    superior derecha, así que las coordenadas de las cajas se leen
    directamente como distancias en la página.
    """
    estilo.aplicar_estilo()
    fig = plt.figure(figsize=(ancho, alto))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, ancho)
    ax.set_ylim(0, alto)
    ax.axis("off")
    return fig, ax


def caja(ax, x: float, y: float, w: float, h: float, texto: str = "",
         color: str = GRIS, relleno: float = 0.10, tam: float = 8.5,
         negrita: bool = False, lw: float = 1.1, alinear: str = "center",
         color_texto: str = TINTA):
    """Caja redondeada centrada en ``(x, y)`` con ancho ``w`` y alto ``h``.

    ``relleno`` es la opacidad del color de fondo (0 = sin relleno).
    """
    parche = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                            boxstyle="round,pad=0.02,rounding_size=0.07",
                            linewidth=lw, edgecolor=color,
                            facecolor=color if relleno > 0 else "none",
                            alpha=None)
    if relleno > 0:
        parche.set_facecolor((*_rgb(color), relleno))
    ax.add_patch(parche)
    if texto:
        xt = x if alinear == "center" else x - w / 2 + 0.08
        ax.text(xt, y, texto, ha=alinear, va="center", fontsize=tam,
                color=color_texto, fontweight="bold" if negrita else "normal",
                linespacing=1.25)
    return parche


def flecha(ax, puntos, color: str = GRIS, lw: float = 1.1, punta: bool = True,
           estilo_linea: str = "-"):
    """Polilínea entre ``puntos`` [(x, y), ...] con punta en el último."""
    for (x0, y0), (x1, y1) in zip(puntos[:-2], puntos[1:-1]):
        ax.plot([x0, x1], [y0, y1], color=color, lw=lw, ls=estilo_linea,
                solid_capstyle="butt")
    (x0, y0), (x1, y1) = puntos[-2], puntos[-1]
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1),
                                 arrowstyle="-|>" if punta else "-",
                                 mutation_scale=9, color=color, lw=lw,
                                 linestyle=estilo_linea, shrinkA=0, shrinkB=0))


def borde(x: float, y: float, w: float, h: float, lado: str) -> tuple[float, float]:
    """Punto medio de un lado de la caja centrada en (x, y)."""
    return {"arriba": (x, y + h / 2), "abajo": (x, y - h / 2),
            "izq": (x - w / 2, y), "der": (x + w / 2, y)}[lado]


def _rgb(color: str) -> tuple[float, float, float]:
    from matplotlib.colors import to_rgb
    return to_rgb(color)
