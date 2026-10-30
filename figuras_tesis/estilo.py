"""Estilo y geometría comunes a TODAS las figuras de la tesis.

Por qué existe este archivo
---------------------------
Antes cada figura tenía su propio ``figsize`` (10x4, 15x4), su propio
tamaño de letra (11, 12) y se guardaba con ``bbox_inches="tight"``. Ese
recorte automático deja un margen izquierdo distinto en cada figura
(depende del ancho de los números del eje Y), así que al ponerlas en
LaTeX con ``width=\\textwidth`` los ejes no quedan alineados y la letra
sale de tamaños distintos.

Aquí la geometría se fija en PULGADAS:

* Todas las figuras miden ``ANCHO`` de ancho (= ancho del texto en LaTeX),
  así que se insertan sin escalar y la letra mide lo mismo en todas.
* El espacio reservado para el eje Y (números + etiqueta) es siempre
  ``MARGEN_IZQ``: el eje empieza exactamente en el mismo punto en todas.
* El título del eje Y queda a ``SEP_YLABEL`` puntos de los números del
  eje, en todas las figuras.
* Hay un margen blanco fijo entre el borde de la figura y los ejes en
  los cuatro lados.
* NO se usa ``bbox_inches="tight"`` (desharía todo lo anterior).

Uso::

    from estilo import crear_figura, formatear_eje, guardar
    fig, axes = crear_figura(ncols=3)
    ...
    guardar(fig, "capitulo_1", "Tres_dias_horizontal")
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
from matplotlib.ticker import AutoMinorLocator
import numpy as np

# =====================================================================
# GEOMETRÍA FIJA (pulgadas) — cambiar aquí cambia TODAS las figuras
# =====================================================================
ANCHO = 6.3          # ancho total de la figura (~16 cm = \textwidth en A4)
ALTO_EJES = 2.3      # alto del área de los ejes

MARGEN_IZQ = 0.70    # borde izquierdo -> eje Y (números + etiqueta Y)
MARGEN_DER = 0.25    # eje -> borde derecho (espacio en blanco)
MARGEN_SUP = 0.15    # borde superior -> eje (espacio en blanco)
MARGEN_INF = 0.50    # eje -> borde inferior (números + etiqueta X)

SEP_YLABEL = 4       # pt entre los números del eje Y y su título
SEP_PANELES = 0.30   # separación horizontal entre subpaneles
HOLGURA = 0.07       # espacio entre el marco y el inicio de los datos (fracción del rango)

# =====================================================================
# TIPOGRAFÍA Y TICKS
# =====================================================================
TAM_LETRA = 10       # pt (igual que el cuerpo de la tesis)

# Fuente igual a la de LaTeX (Computer Modern). La trae matplotlib, así que
# se ve igual en cualquier computador. False = fuente por defecto (sans).
FUENTE_LATEX = False
GRIS_REJILLA = "#b0b0b0"     # gris por defecto de matplotlib
GROSOR_REJILLA = 0.6        # grosor de la rejilla (X y Y), sin transparencia

SALIDA = Path(__file__).resolve().parent / "salida"


def aplicar_estilo() -> None:
    """Estilo de la tesis: ticks hacia adentro en los 4 lados, rejilla."""
    if FUENTE_LATEX:
        mpl.rcParams.update(
            {
                "font.family": "serif",
                "font.serif": ["cmr10"],
                "mathtext.fontset": "cm",
                "axes.formatter.use_mathtext": True,   # signo menos correcto
                "axes.unicode_minus": False,
            }
        )
    mpl.rcParams.update(
        {
            "font.size": TAM_LETRA,
            "axes.labelsize": TAM_LETRA,
            "xtick.labelsize": TAM_LETRA,
            "ytick.labelsize": TAM_LETRA,
            "legend.fontsize": TAM_LETRA,
            "legend.frameon": False,
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "axes.axisbelow": "line",   # rejilla encima del relleno, debajo de las curvas
            "grid.color": GRIS_REJILLA,
            "grid.alpha": 1.0,          # sin transparencia
            "grid.linewidth": GROSOR_REJILLA,
            "lines.linewidth": 1.6,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.top": True,
            "ytick.right": True,
            "xtick.major.size": 5,
            "ytick.major.size": 5,
            "xtick.minor.size": 3,
            "ytick.minor.size": 3,
            "savefig.bbox": None,      # nada de recorte automático
            "savefig.pad_inches": 0.0,
            "pdf.fonttype": 42,        # texto editable/seleccionable en el PDF
        }
    )


def crear_figura(
    ncols: int = 1,
    margen_inf: float = MARGEN_INF,
    alto_ejes: float = ALTO_EJES,
    sharey: bool = True,
    margen_sup: float = MARGEN_SUP,
):
    """Crea una figura con márgenes fijos en pulgadas.

    ``margen_inf`` / ``margen_sup`` se pueden aumentar cuando debajo o
    encima del eje va texto (leyenda, (a)(b)(c), títulos de panel); el
    margen IZQUIERDO nunca cambia.
    Devuelve ``(fig, ax)`` si ncols == 1, o ``(fig, [ax1, ax2, ...])``.
    """
    aplicar_estilo()
    alto = margen_sup + alto_ejes + margen_inf
    fig = plt.figure(figsize=(ANCHO, alto))

    ancho_util = ANCHO - MARGEN_IZQ - MARGEN_DER
    ancho_panel = (ancho_util - SEP_PANELES * (ncols - 1)) / ncols

    axes = []
    for i in range(ncols):
        x0 = MARGEN_IZQ + i * (ancho_panel + SEP_PANELES)
        rect = [x0 / ANCHO, margen_inf / alto, ancho_panel / ANCHO, alto_ejes / alto]
        compartir = axes[0] if (axes and sharey) else None
        ax = fig.add_axes(rect, sharey=compartir)
        if compartir is not None:
            ax.tick_params(labelleft=False)
        axes.append(ax)

    return (fig, axes[0]) if ncols == 1 else (fig, axes)


def formatear_eje(ax, xlabel: str = "", ylabel: str = "",
                  menores_x=2, menores_y=2) -> None:
    """Ticks menores, etiquetas y posición FIJA de la etiqueta Y.

    ``menores_x`` / ``menores_y``: número de subdivisiones entre marcas
    mayores (AutoMinorLocator(n)) o un Locator de matplotlib.
    """
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
        # x en coordenadas de figura (fijo), y en coordenadas del eje (centro)
        ax.yaxis.labelpad = SEP_YLABEL   # título pegado a los números
    for eje_obj, n in ((ax.xaxis, menores_x), (ax.yaxis, menores_y)):
        eje_obj.set_minor_locator(AutoMinorLocator(n) if isinstance(n, int) else n)
    ax.tick_params(axis="both", which="both", direction="in", top=True, right=True)


def holgura(axes, eje: str = "y", frac: float = HOLGURA, ticks=None) -> None:
    """Deja un espacio en blanco entre el marco y donde empiezan los datos.

    El eje va exactamente del mínimo al máximo de los datos, más un
    margen de ``frac`` del rango a cada lado. No se redondea a valores
    "bonitos" (no se agrega ningún otro espacio). Con ejes compartidos,
    pasar la lista de ejes para que el rango cubra todos los paneles.

    ``ticks``: marcas mayores fijas (opcional); si no, matplotlib las
    elige dentro del rango.
    """
    axes = list(np.atleast_1d(axes))
    i = 0 if eje == "x" else 1
    lo = min(a.dataLim.get_points()[0][i] for a in axes)
    hi = max(a.dataLim.get_points()[1][i] for a in axes)
    pad = frac * (hi - lo)

    for a in axes:
        if eje == "x":
            if ticks is not None:
                a.set_xticks(ticks)
            a.set_xlim(lo - pad, hi + pad)
        else:
            if ticks is not None:
                a.set_yticks(ticks)
            a.set_ylim(lo - pad, hi + pad)


def etiqueta_panel(ax, texto: str, debajo: float = 0.50) -> None:
    """Etiqueta (a), (b), (c) centrada a ``debajo`` pulgadas bajo el panel."""
    alto_ax = ax.get_position().height * ax.figure.get_figheight()
    # negrilla vía mathtext: funciona también con la fuente de LaTeX
    ax.text(0.5, -debajo / alto_ax, rf"$\mathbf{{{texto}}}$", transform=ax.transAxes,
            ha="center", va="top")


def guardar(fig, capitulo: str, nombre: str, png: bool = True) -> Path:
    """Guarda en salida/<capitulo>/<nombre>.pdf (y .png para revisar)."""
    destino = SALIDA / capitulo
    destino.mkdir(parents=True, exist_ok=True)
    pdf = destino / f"{nombre}.pdf"
    fig.savefig(pdf)
    if png:
        fig.savefig(destino / f"{nombre}.png", dpi=300)
    plt.close(fig)
    print(f"  -> {pdf.relative_to(SALIDA.parent)}")
    return pdf
