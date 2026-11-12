"""Utilidades comunes a las figuras de RESULTADOS (capítulo 4).

Las figuras del capítulo 4 NO simulan: leen las tablas que deja el pipeline
en ``codigo/resultados/articulo2/`` (pasos 10 a 15), para que cada número
de la figura sea el mismo del texto. Paleta, constantes y estilo son los de
``sitios_ilustrativos.py`` y ``estilo.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent              # figuras/
sys.path.insert(0, str(AQUI))

import estilo                                         # noqa: E402
from estilo import etiqueta_panel, formatear_eje, guardar  # noqa: E402,F401
from sitios_ilustrativos import (AZUL, BESS, CFG, DEMANDA_MW, GRIS, NARANJA,  # noqa: E402,F401
                                 P_REF_MW, PR, ROJO_SUAVE, SOLAR, VERDE)

RESULTADOS = AQUI.parent / "codigo" / "resultados" / "articulo2"


def leer_resultado(nombre: str):
    """Lee una tabla de ``codigo/resultados/articulo2/`` (.xlsx, .csv o .csv.gz)."""
    import pandas as pd

    ruta = RESULTADOS / nombre
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Corre primero el paso del pipeline que la genera "
            "(codigo/pipeline/10 a 15).")
    if nombre.endswith(".xlsx"):
        return pd.read_excel(ruta)
    if nombre.endswith(".json"):
        import json
        return json.loads(ruta.read_text(encoding="utf-8"))
    return pd.read_csv(ruta)


def rejilla(filas: int, cols: int, alto_ej: float = 1.75, sep_v: float = 0.95,
            sep_h: float = 0.85, y0: float = 0.80, arriba: float = 0.30,
            anchos: list[float] | None = None):
    """Figura con una rejilla de ejes de tamaño fijo en pulgadas.

    Devuelve ``(fig, ejes)`` con ``ejes[fila][col]``. ``anchos`` permite
    recortar el ancho de un panel (p. ej. para dejar sitio a una barra de color).
    """
    import matplotlib.pyplot as plt

    estilo.aplicar_estilo()
    alto = y0 + filas * alto_ej + (filas - 1) * sep_v + arriba
    util = estilo.ANCHO - estilo.MARGEN_IZQ - estilo.MARGEN_DER - (cols - 1) * sep_h
    w = util / cols
    fig = plt.figure(figsize=(estilo.ANCHO, alto))
    ejes = []
    for f in range(filas):
        fila = []
        for c in range(cols):
            ancho = w if (anchos is None or anchos[c] is None) else anchos[c]
            x = estilo.MARGEN_IZQ + c * (w + sep_h)
            y = y0 + (filas - 1 - f) * (alto_ej + sep_v)
            fila.append(fig.add_axes([x / estilo.ANCHO, y / alto, ancho / estilo.ANCHO,
                                      alto_ej / alto]))
        ejes.append(fila)
    return fig, ejes


def barra_color(fig, ax, mapeable, etiqueta: str):
    """Barra de color delgada pegada a la derecha de ``ax``."""
    pos = ax.get_position()
    cax = fig.add_axes([pos.x1 + 0.08 / estilo.ANCHO, pos.y0, 0.08 / estilo.ANCHO, pos.height])
    cb = fig.colorbar(mapeable, cax=cax)
    cb.set_label(etiqueta, fontsize=8)
    cb.ax.tick_params(labelsize=7, direction="in")
    return cb
