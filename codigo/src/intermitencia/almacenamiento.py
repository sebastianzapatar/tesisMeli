"""Simulación horaria del estado de carga (SOC) del BESS.

Qué cambia respecto al simulador anterior
-----------------------------------------
El ``simular_soc`` original (duplicado en ``Modelo.py`` y en
``Curvas capacidad-confiabilidad.py``, con firmas distintas) era
sistemáticamente optimista:

===========================  ==================================================
Ausente                      Consecuencia
===========================  ==================================================
Límite de potencia           ``Curvas...py`` calculaba ``capacidades/4 h`` y
                             nunca lo usaba. La batería absorbía cualquier
                             potencia en una hora, sobrestimando la carga.
Eficiencias                  Estaban en 1.0. Round-trip real: 0.85-0.92.
SOC mínimo / DoD             Usaba el 100 % del rango, no el 80-90 % usable.
Autodescarga                 No modelada.
Vertimiento                  ``min(capacidad, ...)`` botaba el excedente en
                             silencio, así que no se podía valorar.
Conteo de ciclos             Sin ciclos no hay vida útil ni augmentation.
===========================  ==================================================

Además era un bucle de Python sobre ~236 000 pasos x 26 capacidades x 51
series ~ 313 M iteraciones. Aquí se compila con numba (~100x) y se cae
con elegancia a NumPy puro si numba no está disponible.

Convención de unidades
----------------------
El paso es de 1 hora, así que 1 MW durante un paso = 1 MWh. Los arreglos
de balance están en MW y los de energía en MWh, y son intercambiables
numéricamente. Si algún día se usan pasos distintos de 1 h, hay que
introducir ``dt`` explícitamente en todo el módulo.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import Bess

__all__ = ["ResultadoSOC", "simular_soc", "NUMBA_ACTIVO"]


try:  # pragma: no cover - depende del entorno
    from numba import njit

    NUMBA_ACTIVO = True
except ImportError:  # pragma: no cover
    NUMBA_ACTIVO = False

    def njit(*args, **kwargs):  # type: ignore[misc]
        def envoltura(fn):
            return fn

        if args and callable(args[0]):
            return args[0]
        return envoltura


@njit(cache=True, fastmath=False)
def _nucleo_soc(
    balance: np.ndarray,
    capacidad: float,
    potencia: float,
    eff_carga: float,
    eff_descarga: float,
    soc_min: float,
    soc_max: float,
    soc_inicial: float,
    autodescarga: float,
):
    """Bucle de simulación. Solo tipos numéricos, para que numba lo compile.

    Devuelve (soc, ens, vertimiento, carga, descarga), todos en MWh.
    """
    n = balance.shape[0]
    soc = np.empty(n, dtype=np.float64)
    ens = np.zeros(n, dtype=np.float64)
    vertimiento = np.zeros(n, dtype=np.float64)
    carga = np.zeros(n, dtype=np.float64)
    descarga = np.zeros(n, dtype=np.float64)

    s = soc_inicial

    for i in range(n):
        # --- autodescarga -------------------------------------------------
        if autodescarga > 0.0:
            perdida = (s - soc_min) * autodescarga
            if perdida > 0.0:
                s -= perdida

        v = balance[i]

        if v >= 0.0:
            # --- EXCEDENTE: cargar ---------------------------------------
            # El límite de potencia actúa del lado AC (lo que la batería
            # puede tomar de la planta), antes de la eficiencia de carga.
            p_ac = v
            if p_ac > potencia:
                p_ac = potencia

            espacio = soc_max - s              # MWh que caben todavía
            e_entra = p_ac * eff_carga         # MWh que llegarían al SOC

            if e_entra > espacio:
                e_entra = espacio

            s += e_entra
            tomado = e_entra / eff_carga       # MWh consumidos del excedente
            carga[i] = tomado
            vertimiento[i] = v - tomado        # excedente que se pierde

        else:
            # --- DÉFICIT: descargar --------------------------------------
            deficit = -v

            p_ac = deficit
            if p_ac > potencia:
                p_ac = potencia

            # Energía entregable al lado AC dada la reserva utilizable
            entregable = (s - soc_min) * eff_descarga
            if entregable < 0.0:
                entregable = 0.0

            entregada = p_ac
            if entregada > entregable:
                entregada = entregable

            s -= entregada / eff_descarga
            descarga[i] = entregada
            ens[i] = deficit - entregada       # lo que no se pudo cubrir

        # Guarda numérica contra deriva por punto flotante
        if s < soc_min:
            s = soc_min
        elif s > soc_max:
            s = soc_max

        soc[i] = s

    return soc, ens, vertimiento, carga, descarga


@dataclass(frozen=True)
class ResultadoSOC:
    """Salida completa de una simulación de BESS.

    Todas las energías en MWh. ``soc`` es el estado de carga absoluto
    (MWh), no una fracción.
    """

    soc: np.ndarray
    ens: np.ndarray
    vertimiento: np.ndarray
    carga: np.ndarray
    descarga: np.ndarray
    capacidad_mwh: float
    potencia_mw: float

    # --- agregados baratos y de uso frecuente ---------------------------
    @property
    def ens_total(self) -> float:
        return float(self.ens.sum())

    @property
    def vertimiento_total(self) -> float:
        return float(self.vertimiento.sum())

    @property
    def descarga_total(self) -> float:
        return float(self.descarga.sum())

    @property
    def carga_total(self) -> float:
        return float(self.carga.sum())

    @property
    def ciclos_equivalentes(self) -> float:
        """Ciclos equivalentes completos sobre todo el registro."""
        if self.capacidad_mwh <= 0:
            return 0.0
        return self.descarga_total / self.capacidad_mwh

    def ciclos_por_anio(self, n_horas: int | None = None) -> float:
        n = n_horas if n_horas is not None else len(self.soc)
        anios = n / 8760.0
        return self.ciclos_equivalentes / anios if anios > 0 else 0.0

    def fraccion_tiempo_lleno(self, umbral: float = 0.99) -> float:
        """Proxy de curtailment: fracción del tiempo con el SOC saturado."""
        if self.capacidad_mwh <= 0:
            return 0.0
        return float(np.mean(self.soc >= umbral * self.capacidad_mwh))


def simular_soc(
    balance: np.ndarray,
    capacidad_mwh: float,
    bess: Bess,
    potencia_mw: float | None = None,
) -> ResultadoSOC:
    """Simula el BESS sobre una serie de balance horario.

    Parameters
    ----------
    balance
        Balance horario generación - demanda [MW]; con paso de 1 h
        equivale a MWh.
    capacidad_mwh
        Capacidad nominal instalada. La ventana realmente utilizable es
        ``[soc_min_frac, soc_max_frac] * capacidad_mwh``.
    bess
        Parámetros del almacenamiento.
    potencia_mw
        Límite de potencia. Si es None se deriva de la duración
        (``capacidad / duracion_h``). Si ``bess.limitar_potencia`` es
        False el límite se vuelve infinito, lo que reproduce el
        comportamiento del código anterior.
    """
    balance = np.ascontiguousarray(np.asarray(balance, dtype=np.float64))
    if balance.ndim != 1:
        raise ValueError(f"El balance debe ser 1-D, llegó con forma {balance.shape}.")
    if not np.isfinite(balance).all():
        raise ValueError("El balance contiene NaN o inf.")
    if capacidad_mwh < 0:
        raise ValueError(f"capacidad_mwh={capacidad_mwh} no puede ser negativa.")

    if potencia_mw is None:
        potencia_mw = capacidad_mwh / bess.duracion_h
    if not bess.limitar_potencia:
        potencia_mw = np.inf

    soc_min = bess.soc_min_frac * capacidad_mwh
    soc_max = bess.soc_max_frac * capacidad_mwh
    soc_ini = np.clip(bess.soc_inicial_frac * capacidad_mwh, soc_min, soc_max)

    soc, ens, vert, carga, desc = _nucleo_soc(
        balance,
        float(capacidad_mwh),
        float(potencia_mw),
        float(bess.eff_carga),
        float(bess.eff_descarga),
        float(soc_min),
        float(soc_max),
        float(soc_ini),
        float(bess.autodescarga_frac_h),
    )

    return ResultadoSOC(
        soc=soc,
        ens=ens,
        vertimiento=vert,
        carga=carga,
        descarga=desc,
        capacidad_mwh=float(capacidad_mwh),
        potencia_mw=float(potencia_mw),
    )


@njit(cache=True)
def _nucleo_pico_secuente(deficit: np.ndarray) -> float:
    s = 0.0
    smax = 0.0
    for i in range(deficit.shape[0]):
        s += deficit[i]
        if s < 0.0:
            s = 0.0
        if s > smax:
            smax = s
    return smax


def energia_requerida_pico_secuente(balance: np.ndarray) -> float:
    """Capacidad necesaria para ENS = 0, por el algoritmo de pico secuente.

    Es el método clásico de dimensionamiento de embalses (Rippl, 1883):

        S_t = max(0, S_{t-1} + demanda_t - generacion_t)
        E_req = max_t S_t

    Da la capacidad exacta que anula la energía no suministrada sobre el
    registro, **sin ningún parámetro arbitrario**. Sustituye al heurístico
    ``conf_max * 0.99`` del código anterior, que dependía por completo del
    extremo superior de la grilla de barrido.

    Notas
    -----
    Supone eficiencia perfecta y potencia ilimitada, así que es una **cota
    inferior** de la capacidad realmente necesaria. Aplicado año por año
    da una distribución de capacidad requerida, y de ahí un P50 y un P90.
    """
    balance = np.ascontiguousarray(np.asarray(balance, dtype=np.float64))
    return float(_nucleo_pico_secuente(-balance))
