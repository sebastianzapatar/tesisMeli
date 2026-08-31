"""Utilidades compartidas por los scripts del pipeline."""

from __future__ import annotations

import time
import warnings
from contextlib import contextmanager

import pandas as pd

from intermitencia import Config
from intermitencia import io_datos, pv

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

ANCHO = 70


def titulo(texto: str) -> None:
    print("\n" + "=" * ANCHO)
    print(texto.upper())
    print("=" * ANCHO)


def subtitulo(texto: str) -> None:
    print("\n" + "-" * ANCHO)
    print(texto)
    print("-" * ANCHO)


@contextmanager
def cronometro(etiqueta: str):
    t0 = time.time()
    yield
    print(f"  [{etiqueta}: {time.time() - t0:.1f} s]")


def preparar() -> Config:
    """Carga la configuración, valida las entradas y crea los directorios."""
    cfg = Config.cargar()
    cfg.rutas.verificar_entradas()
    cfg.rutas.crear_directorios()
    return cfg


def cargar_balances(cfg: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (generación [MW], balance [MW]) de las 51 series."""
    ghi = io_datos.leer_series_horarias(cfg.rutas.series_51, cfg.rutas.cache)
    gen = pv.generacion_mw(ghi, cfg.planta)
    return gen, gen - cfg.demanda_mw


def guardar(df: pd.DataFrame, cfg: Config, nombre: str, indice: bool = False) -> None:
    """Guarda un resultado en Excel y avisa dónde quedó."""
    destino = cfg.rutas.salida / nombre
    df.to_excel(destino, index=indice)
    print(f"  -> {destino.relative_to(cfg.rutas.salida.parent)}  ({len(df)} filas)")
