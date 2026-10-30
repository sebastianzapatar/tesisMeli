"""Dimensionamiento de plantas PV + BESS con métricas de intermitencia.

Uso típico::

    from intermitencia import Config, io_datos, pv, confiabilidad

    cfg = Config.cargar()
    ghi = io_datos.leer_series_horarias(cfg.rutas.series_51, cfg.rutas.cache)
    balance = pv.balance_mw(ghi["Chinú"], cfg.planta, cfg.demanda_mw)
    m = confiabilidad.evaluar(balance.to_numpy(), 150.0, cfg.bess, cfg.demanda_mw)
"""

from .config import Config, raiz_proyecto

__all__ = ["Config", "raiz_proyecto", "__version__"]
__version__ = "0.1.0"
