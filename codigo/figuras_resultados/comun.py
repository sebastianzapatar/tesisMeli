"""Utilidades comunes a las figuras de metodología del artículo 2.

Qué hay aquí
------------
* Rutas e importaciones: el paquete ``intermitencia`` (``src/``) y el
  estilo de la tesis (``figuras/estilo.py``), para que las figuras
  del artículo usen la MISMA geometría, letra y colores que las de la tesis.
* Un generador de series SINTÉTICAS de GHI horaria con estructura diaria
  controlada (agrupamiento de días nublados). Las figuras de metodología
  son ilustrativas: muestran QUÉ miden B, M y PSH y CÓMO cambia la curva
  LPSP-E, sin adelantar resultados de las 51 series.
* Funciones que llaman al código del pipeline (eventos, simulador, ajuste
  de kappa) para que la figura y la metodología sean exactamente las mismas.

Todas las figuras se guardan en ``codigo/figuras_resultados/salida/`` (PDF para
LaTeX y PNG para revisar).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent                                   # carpeta codigo/
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ.parent / "figuras"))     # estilo.py

import estilo                                         # noqa: E402
from estilo import crear_figura, etiqueta_panel, formatear_eje, holgura  # noqa: E402,F401

from intermitencia import Config                      # noqa: E402
from intermitencia.confiabilidad import evaluar        # noqa: E402
from intermitencia.eventos import metricas_intermitencia  # noqa: E402
from intermitencia.sustituto import ajustar_kappa      # noqa: E402

SALIDA = AQUI / "salida"

# ---------------------------------------------------------------------
# Paleta (la misma validada en la BITÁCORA para las figuras del pipeline)
# ---------------------------------------------------------------------
AZUL = "#2a78d6"
NARANJA = "#eb6834"
VERDE = "#1baf7a"
GRIS = "#6b6b6b"
SOLAR = "#FDB813"
SOLAR_LINEA = "#E39400"
ROJO_SUAVE = "#f3c2b3"

CFG = Config.cargar()
DEMANDA_MW = CFG.demanda_mw                           # 20 MW planos
PR = CFG.planta.performance_ratio                     # 0.80
P_REF_MW = float(CFG.sustituto["planta_referencia_mw"])         # 150 MW (planta común)
BESS = CFG.bess


def guardar(fig, nombre: str, png: bool = True) -> Path:
    """Guarda en salida/<nombre>.pdf (y .png a 300 dpi para revisar)."""
    SALIDA.mkdir(parents=True, exist_ok=True)
    pdf = SALIDA / f"{nombre}.pdf"
    fig.savefig(pdf)
    if png:
        fig.savefig(SALIDA / f"{nombre}.png", dpi=300)
    import matplotlib.pyplot as plt
    plt.close(fig)
    print(f"  -> {pdf.relative_to(RAIZ)}")
    return pdf


# =====================================================================
# SERIES SINTÉTICAS
# =====================================================================
HORAS = np.arange(24)
# Perfil de cielo despejado simple (W/m2): 06:00-18:00, pico 1000 al mediodía.
CIELO_DESPEJADO = np.clip(np.sin(np.pi * (HORAS + 0.5 - 6.0) / 12.0), 0.0, None) * 1000.0


@dataclass(frozen=True)
class Sitio:
    """Parámetros de un sitio sintético.

    La secuencia de días nublados sigue un régimen oculto de dos estados
    (seco / húmedo) con probabilidad de permanencia ``q``. En el régimen
    húmedo un día es nublado con probabilidad ``f + delta`` y en el seco
    con ``f - delta``; así la fracción media de días nublados es ``f`` en
    todos los sitios (misma PSH) y solo cambia CÓMO se agrupan:

    * ``delta = 0``            -> días nublados independientes (Poisson, B ~ 0)
    * ``delta > 0``, ``q`` alto -> rachas largas de días nublados (B > 0, M > 0)
    * ``periodico = True``     -> un día nublado cada ~1/f días (B < 0)

    Es una versión simplificada de los generadores de radiación diaria con
    matrices de transición de Markov (Aguiar et al., 1988).
    """

    nombre: str
    f: float = 0.30          # fracción media de días nublados
    delta: float = 0.0       # diferencia de probabilidad entre regímenes
    q: float = 0.5           # persistencia del régimen
    kt_despejado: float = 0.78
    kt_nublado: float = 0.35
    periodico: bool = False


def dias_nublados(sitio: Sitio, n_dias: int, rng: np.random.Generator) -> np.ndarray:
    """Vector booleano de días nublados según el modelo del sitio."""
    if sitio.periodico:
        # Un día nublado cada ~1/f días, con un pequeño desfase aleatorio.
        periodo = 1.0 / sitio.f
        marcas = np.arange(0.0, n_dias, periodo) + rng.uniform(-0.6, 0.6, int(np.ceil(n_dias / periodo)))
        idx = np.clip(np.round(marcas).astype(int), 0, n_dias - 1)
        nub = np.zeros(n_dias, dtype=bool)
        nub[idx] = True
        return nub

    humedo = np.empty(n_dias, dtype=bool)
    humedo[0] = rng.random() < 0.5
    cambios = rng.random(n_dias) > sitio.q
    for d in range(1, n_dias):
        humedo[d] = (not humedo[d - 1]) if cambios[d] else humedo[d - 1]
    p = np.where(humedo, sitio.f + sitio.delta, sitio.f - sitio.delta)
    return rng.random(n_dias) < p


def ghi_sintetica(sitio: Sitio, anios: int = 10, semilla: int = 42) -> np.ndarray:
    """GHI horaria [W/m2] de ``anios`` años de 365 días."""
    rng = np.random.default_rng(semilla)
    n_dias = 365 * anios
    nub = dias_nublados(sitio, n_dias, rng)
    kt = np.where(nub,
                  rng.normal(sitio.kt_nublado, 0.07, n_dias),
                  rng.normal(sitio.kt_despejado, 0.05, n_dias))
    kt = np.clip(kt, 0.05, 1.0)
    return (kt[:, None] * CIELO_DESPEJADO[None, :]).ravel()


def psh(ghi: np.ndarray) -> float:
    """Horas solares pico [h/día] = irradiación diaria media / 1 kW/m2."""
    return float(ghi.sum() / 1000.0 / (ghi.size / 24))


def balance_mw(ghi: np.ndarray, p_pv_mw: float = P_REF_MW) -> np.ndarray:
    """Balance horario P(t) - D [MW] con el mismo modelo FV del pipeline."""
    return p_pv_mw * ghi / 1000.0 * PR - DEMANDA_MW


# =====================================================================
# MÉTRICAS (las mismas funciones del pipeline)
# =====================================================================
def deficit_diario(balance: np.ndarray) -> np.ndarray:
    """Energía de déficit de cada día [MWh/día] (igual que el pipeline)."""
    return (-np.clip(balance, None, 0.0)).reshape(-1, 24).sum(axis=1)


def eventos_diarios(balance: np.ndarray) -> dict:
    """B, M y eventos a resolución diaria, como ``02_intermitencia.py``.

    Un día es un evento de déficit cuando su déficit supera el déficit
    diario medio de la serie (la serie se centra antes de detectar).
    """
    d = deficit_diario(balance)
    serie = -(d - d.mean())
    m = metricas_intermitencia(
        serie,
        umbral=CFG.intermitencia.umbral_mw,
        base="deficit",
        min_eventos=CFG.intermitencia.min_eventos,
        corregir_tamano_finito=CFG.intermitencia.corregir_tamano_finito,
        metodo_memory=CFG.intermitencia.metodo_memory,
    )
    activo = serie < -CFG.intermitencia.umbral_mw
    borde = np.diff(activo.astype(np.int8))
    inicios = np.flatnonzero(borde == 1) + 1
    if activo[0]:
        inicios = np.r_[0, inicios]
    m["inicios"] = inicios
    m["taus"] = np.diff(inicios).astype(float)
    m["deficit_diario"] = d
    return m


def curva_lpsp(balance: np.ndarray, capacidades: np.ndarray) -> np.ndarray:
    """LPSP para cada capacidad de BESS [MWh] (simulador del pipeline)."""
    return np.array([evaluar(balance, float(e), BESS, DEMANDA_MW).lpsp for e in capacidades])


def kappa_de(balance: np.ndarray, capacidades: np.ndarray):
    """Curva LPSP-E y ajuste exponencial LPSP = L0·exp(-E/kappa)."""
    lpsp = curva_lpsp(balance, capacidades)
    ajuste = ajustar_kappa(capacidades, lpsp,
                           CFG.sustituto["ajuste_lpsp_min"], CFG.sustituto["ajuste_lpsp_max"])
    return lpsp, ajuste


# Sitios de referencia usados en varias figuras (misma PSH, distinto agrupamiento)
SITIOS = [
    Sitio("Regular", periodico=True),
    Sitio("Independent", delta=0.0),
    Sitio("Clustered", delta=0.25, q=0.97),
    Sitio("Strongly clustered", delta=0.29, q=0.98),
]
COLORES_SITIOS = [VERDE, GRIS, AZUL, NARANJA]


# =====================================================================
# RESULTADOS REALES (paso 10 del pipeline)
# =====================================================================
RESULTADOS = RAIZ / "resultados" / "articulo2"


def leer_resultado(nombre: str):
    """Lee una salida del paso 10 (``pipeline/10_resultados_articulo2.py``).

    Las figuras de resultados NO simulan: solo leen lo que dejó el
    pipeline, para que cada número de la figura sea el mismo del texto.
    """
    import pandas as pd

    ruta = RESULTADOS / nombre
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Corre primero: python pipeline/10_resultados_articulo2.py")
    if nombre.endswith(".xlsx"):
        return pd.read_excel(ruta)
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
