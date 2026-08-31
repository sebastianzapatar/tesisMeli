"""Lectura robusta de los insumos, con validación y caché.

Corrige de raíz los problemas de lectura del código anterior:

* `Modelo.py` leía las series sin `index_col` y sin `pd.to_datetime`, así
  que `sort_values("fecha")` podía ordenar lexicográficamente. La
  simulación de SOC depende del orden, de modo que eso corrompe todos
  los resultados aguas abajo, en silencio.
* `calculo_psh.py` hacía `df["date"] = pd.to_datetime(df["fecha"])` y
  después indexaba por `"fecha"` SIN convertir: la columna convertida
  quedaba muerta y el índice podía no ser un DatetimeIndex.
* Cada script asumía un working directory distinto.
* Los nombres de serie no se normalizaban, así que ' Ancón Sur' y
  'Ancón Sur' eran series distintas al hacer merge.

Aquí todo eso se hace una sola vez, se valida, y se cachea: leer el
Excel de 53 MB tarda ~40 s, leer el caché tarda ~0.3 s.
"""

from __future__ import annotations

import hashlib
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Config

__all__ = [
    "leer_series_horarias",
    "leer_psh",
    "leer_cuenta_tienda_5",
    "normalizar_nombre",
]


def normalizar_nombre(s: str) -> str:
    """Normaliza un nombre de serie para que los merges no fallen.

    Hace dos cosas:

    1. Colapsa espacios (había series con espacios sobrantes, de modo que
       ' Ancón Sur' y 'Ancón Sur' eran claves distintas en un merge).
    2. Normaliza Unicode a **NFC**. Los archivos vienen de macOS con las
       tildes en forma descompuesta (NFD): ``'Chinu' + U+0301`` en vez de
       ``'Chinú'``. Ambas se ven idénticas en pantalla pero no son
       iguales como cadenas, así que un ``merge`` entre un archivo NFD y
       uno NFC descarta en silencio todas las series con tilde --- 21 de
       las 51 en este proyecto.
    """
    return unicodedata.normalize("NFC", " ".join(str(s).split()).strip())


def _clave_cache(ruta: Path, sufijo: str) -> str:
    st = ruta.stat()
    firma = f"{ruta.resolve()}|{st.st_size}|{int(st.st_mtime)}|{sufijo}"
    return hashlib.sha1(firma.encode("utf-8")).hexdigest()[:16]


def _leer_excel_cacheado(
    ruta: Path, cache_dir: Path, sufijo: str = "", **kwargs
) -> pd.DataFrame:
    """Lee un Excel usando un caché en disco invalidado por tamaño+mtime."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    destino = cache_dir / f"{ruta.stem[:40]}_{_clave_cache(ruta, sufijo)}.pkl"
    if destino.is_file():
        return pd.read_pickle(destino)
    df = pd.read_excel(ruta, **kwargs)
    df.to_pickle(destino)
    return df


def _validar_indice_temporal(idx: pd.Index, nombre: str) -> pd.DatetimeIndex:
    if not isinstance(idx, pd.DatetimeIndex):
        raise TypeError(
            f"[{nombre}] El índice no es temporal (es {type(idx).__name__}). "
            "La simulación de SOC depende del orden cronológico."
        )
    if not idx.is_monotonic_increasing:
        raise ValueError(f"[{nombre}] El índice temporal no está ordenado.")
    if idx.has_duplicates:
        n = int(idx.duplicated().sum())
        raise ValueError(f"[{nombre}] Hay {n} marcas de tiempo duplicadas.")
    return idx


def leer_series_horarias(
    ruta: Path,
    cache_dir: Path,
    columna_fecha: str = "fecha",
    prefijo_a_quitar: str | None = None,
) -> pd.DataFrame:
    """Lee un Excel de series horarias de GHI y devuelve un DataFrame limpio.

    Devuelve un DataFrame indexado por tiempo (DatetimeIndex ordenado,
    sin duplicados, paso horario verificado) con una columna float por
    serie y los nombres normalizados.

    Parameters
    ----------
    prefijo_a_quitar
        Si se pasa (p. ej. ``"GHI "``), se elimina de los nombres de las
        columnas. El archivo de PSH usa ``"GHI Ancón Sur"`` mientras que
        el de las 51 series usa ``"Ancón Sur"``; esto los reconcilia.
    """
    df = _leer_excel_cacheado(ruta, cache_dir)

    if columna_fecha not in df.columns:
        raise KeyError(
            f"[{ruta.name}] No existe la columna '{columna_fecha}'. "
            f"Columnas disponibles: {list(df.columns)[:6]}..."
        )

    df[columna_fecha] = pd.to_datetime(df[columna_fecha])
    df = df.sort_values(columna_fecha).set_index(columna_fecha)
    df.index.name = "fecha"

    if prefijo_a_quitar:
        df.columns = [
            c.replace(prefijo_a_quitar, "").replace(" [W/m2]", "") for c in df.columns
        ]
    df.columns = [normalizar_nombre(c) for c in df.columns]

    if len(set(df.columns)) != len(df.columns):
        dup = pd.Index(df.columns)[pd.Index(df.columns).duplicated()].tolist()
        raise ValueError(f"[{ruta.name}] Nombres de serie duplicados: {dup}")

    _validar_indice_temporal(df.index, ruta.name)

    paso = df.index.to_series().diff().mode()
    if len(paso) and paso.iloc[0] != pd.Timedelta(hours=1):
        raise ValueError(
            f"[{ruta.name}] La resolución modal es {paso.iloc[0]}, se esperaba 1 h. "
            "El resto del modelo asume pasos horarios (1 MW durante 1 h = 1 MWh)."
        )

    df = df.astype("float64")

    if df.isna().any().any():
        n = int(df.isna().sum().sum())
        raise ValueError(
            f"[{ruta.name}] Hay {n} valores faltantes de GHI. Decide una política "
            "de relleno explícita antes de simular; rellenar en silencio sesga "
            "la confiabilidad."
        )
    if (df < 0).any().any():
        raise ValueError(f"[{ruta.name}] Hay valores de GHI negativos.")

    return df


def leer_psh(ruta: Path, cache_dir: Path) -> pd.Series:
    """Lee la PSH promedio [h/día] por serie desde PSH_resultados.xlsx."""
    df = _leer_excel_cacheado(ruta, cache_dir, sufijo="Resumen",
                              sheet_name="Resumen", index_col=0)
    col = "PSH promedio [h/día]"
    if col not in df.columns:
        raise KeyError(
            f"[{ruta.name}] Falta la columna '{col}'. Hay: {list(df.columns)}"
        )
    psh = df[col].copy()
    psh.index = [normalizar_nombre(i) for i in psh.index]
    psh.index.name = "Serie"
    if psh.isna().any():
        raise ValueError(f"[{ruta.name}] Hay PSH faltantes.")
    if (psh <= 0).any():
        raise ValueError(f"[{ruta.name}] Hay PSH <= 0.")
    return psh.astype(float)


def leer_cuenta_tienda_5(ruta: Path, cache_dir: Path) -> pd.DataFrame:
    """Lee la hoja de cuenta de tienda de las 5 zonas."""
    df = _leer_excel_cacheado(ruta, cache_dir)
    df["Serie"] = df["Serie"].map(normalizar_nombre)
    requeridas = {"Serie", "PSH [h/día]", "Cuenta de tienda [MWh]"}
    faltan = requeridas - set(df.columns)
    if faltan:
        raise KeyError(f"[{ruta.name}] Faltan columnas: {sorted(faltan)}")
    return df.set_index("Serie")


def psh_desde_series(ghi: pd.DataFrame) -> pd.Series:
    """Calcula la PSH promedio [h/día] directamente desde el GHI horario.

    Solo cuenta días con las 24 horas presentes: sin ese filtro los días
    incompletos (la serie omite los 29 de febrero) aparecerían como días
    con PSH = 0 y distorsionarían mínimos y percentiles.
    """
    suma = ghi.resample("D").sum()
    horas = ghi.resample("D").count()
    psh_diaria = (suma / 1000.0).where(horas.eq(24)).dropna(how="all")
    return psh_diaria.mean()


def resumen_series(ghi: pd.DataFrame) -> pd.DataFrame:
    """Tabla descriptiva de las series, útil para la tesis y para auditar."""
    anios = ghi.index.year
    return pd.DataFrame(
        {
            "n_horas": len(ghi),
            "inicio": ghi.index.min(),
            "fin": ghi.index.max(),
            "anios_completos": int(np.unique(anios).size),
            "GHI_medio_wm2": ghi.mean(),
            "GHI_max_wm2": ghi.max(),
        }
    )
