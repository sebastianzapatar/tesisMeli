"""intermitencia/reglas_operacion.py

Simulación de la operación horaria del BESS bajo distintas reglas de
despacho (objetivo específico 3 de la tesis: "proponer un modelo de
simulación que considere distintos escenarios de operación del
almacenamiento"). Corresponde a la Sección 3.10 del capítulo de
Metodología.

Las cinco reglas (R1-R5) comparten exactamente el mismo motor físico
--- límite de potencia, eficiencias de carga/descarga y ventana de SOC
---; lo único que cambia entre ellas es la *decisión de despacho*, es
decir, cuánta potencia intenta cargar o descargar el BESS en cada hora
antes de aplicar los límites físicos. Esto garantiza que cualquier
diferencia observada entre reglas sea atribuible a la política de
despacho y no a inconsistencias en cómo se modela el BESS.

Uso típico
----------
    from intermitencia.reglas_operacion import simular_regla, comparar_reglas

    resultado = simular_regla(balance, e_bess_mwh=335.0, p_bess_mw=100.0,
                               regla="R2", soc_res=0.30)
    print(resultado.resumen())

    tabla = comparar_reglas(balance, e_bess_mwh=335.0, p_bess_mw=100.0,
                             demanda_mw=20.0)
    print(tabla)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd

REGLAS_DISPONIBLES: tuple[str, ...] = ("R1", "R2", "R3", "R4", "R5")

NOMBRES_REGLAS = {
    "R1": "Despacho directo (línea base)",
    "R2": "Reserva mínima de SOC",
    "R3": "Ventana horaria de descarga",
    "R4": "Aplanamiento del perfil de generación",
    "R5": "Carga priorizada por bloques continuos",
}


# ---------------------------------------------------------------------
# Resultado de una simulación
# ---------------------------------------------------------------------
@dataclass
class ResultadoSimulacion:
    """Series horarias completas más los indicadores agregados de la
    Sección 3.10.3 de la tesis, para una regla y una serie dadas."""

    regla: str
    soc: np.ndarray
    carga_mwh: np.ndarray
    descarga_mwh: np.ndarray
    vertimiento_mwh: np.ndarray
    ens_mwh: np.ndarray
    lpsp: float
    cobertura_deficit: float
    frac_vertida: float
    ciclos_equivalentes: float
    suavidad_rampa_mw: float
    parametros: dict = field(default_factory=dict)

    def resumen(self) -> dict:
        """Fila lista para construir la tabla comparativa de `comparar_reglas`."""
        fila = {
            "regla": self.regla,
            "nombre_regla": NOMBRES_REGLAS[self.regla],
            "lpsp": self.lpsp,
            "cobertura_deficit": self.cobertura_deficit,
            "frac_vertida": self.frac_vertida,
            "ciclos_equivalentes": self.ciclos_equivalentes,
            "suavidad_rampa_mw": self.suavidad_rampa_mw,
        }
        for k, v in self.parametros.items():
            fila[f"param_{k}"] = v
        return fila


# ---------------------------------------------------------------------
# Utilidades auxiliares
# ---------------------------------------------------------------------
def _longitudes_de_bloque(mascara: np.ndarray) -> np.ndarray:
    """Para cada posición True de `mascara`, devuelve la longitud (en
    pasos) de la corrida contigua de True a la que pertenece. Las
    posiciones False quedan en 0.

    Es la misma lógica de "corridas contiguas" usada en el Objetivo 1
    para definir los eventos de déficit (Sección 3.5.1); aquí se aplica
    a corridas de *excedente*, para la Regla 5.
    """
    n = len(mascara)
    longitudes = np.zeros(n, dtype=int)
    i = 0
    while i < n:
        if mascara[i]:
            j = i
            while j < n and mascara[j]:
                j += 1
            longitudes[i:j] = j - i
            i = j
        else:
            i += 1
    return longitudes


def _media_movil_centrada(x: np.ndarray, ventana: int) -> np.ndarray:
    """Media móvil centrada (usada por la Regla 4 como perfil objetivo)."""
    if ventana < 1:
        raise ValueError("ventana_suavizado_h debe ser >= 1")
    s = pd.Series(x)
    return s.rolling(window=ventana, center=True, min_periods=1).mean().to_numpy()


def _dentro_de_ventana(hora: int, h_ini: int, h_fin: int) -> bool:
    """True si `hora` cae en [h_ini, h_fin]; admite ventanas que cruzan
    la medianoche (p. ej. h_ini=22, h_fin=4)."""
    if h_ini <= h_fin:
        return h_ini <= hora <= h_fin
    return hora >= h_ini or hora <= h_fin


# ---------------------------------------------------------------------
# Decisión de despacho: la única función que distingue una regla de otra
# ---------------------------------------------------------------------
def _decision_despacho(regla: str, t: int, balance: np.ndarray,
                        horas_del_dia: np.ndarray, aux: dict) -> float:
    """Calcula la potencia de despacho DESEADA en el paso `t`, en MW,
    ANTES de aplicar los límites físicos (potencia nominal, excedente o
    déficit real disponible, espacio de SOC). Positivo = intención de
    cargar; negativo = intención de descargar.

    Ver Sección 3.10.2 de la tesis (Ecuaciones 3.4 a 3.8) para la
    formalización de cada regla.
    """
    d = balance[t]

    if regla == "R1":
        # Ecuación de referencia (despacho directo): reacciona 1:1 al
        # balance instantáneo.
        return d

    if regla == "R2":
        # La intención de carga es igual que R1; la reserva de SOC se
        # aplica más abajo, en simular_regla, limitando la ENERGÍA
        # disponible para descarga (Ecuación 3.4 de la tesis).
        return d

    if regla == "R3":
        # Ecuación 3.5: la descarga solo se habilita dentro de la
        # ventana horaria; la carga no tiene restricción de horario.
        if d >= 0:
            return d
        h_ini, h_fin = aux["ventana_horaria"]
        if _dentro_de_ventana(horas_del_dia[t], h_ini, h_fin):
            return d
        return 0.0

    if regla == "R4":
        # Ecuación 3.6: el objetivo es la desviación respecto de la
        # media móvil del balance, no el balance en sí. El signo de
        # d_deseado puede diferir del signo de balance[t]; simular_regla
        # se encarga de que la carga/descarga real nunca exceda lo
        # físicamente disponible.
        return d - aux["balance_suavizado"][t]

    if regla == "R5":
        # Ecuación 3.7: la descarga sigue la lógica base de R1; la carga
        # solo se habilita si la hora pertenece a una corrida de
        # excedente de longitud >= l_min.
        if d >= 0:
            longitud = aux["longitud_bloque_excedente"][t]
            return d if longitud >= aux["l_min"] else 0.0
        return d

    raise ValueError(f"Regla desconocida: '{regla}'. Use una de {REGLAS_DISPONIBLES}.")


# ---------------------------------------------------------------------
# Motor de simulación (común a las cinco reglas)
# ---------------------------------------------------------------------
def simular_regla(
    balance: Sequence[float],
    e_bess_mwh: float,
    p_bess_mw: float,
    regla: str = "R1",
    *,
    demanda_mw: float | Sequence[float] | None = None,
    eficiencia_carga: float = 0.95,
    eficiencia_descarga: float = 0.95,
    soc_min: float = 0.10,
    soc_max: float = 0.95,
    soc_inicial: float = 0.50,
    horas_del_dia: np.ndarray | None = None,
    soc_res: float = 0.30,
    ventana_horaria: tuple[int, int] = (18, 22),
    ventana_suavizado_h: int = 6,
    l_min_h: int = 3,
    dt_h: float = 1.0,
) -> ResultadoSimulacion:
    """Simula la operación horaria del BESS bajo una regla de despacho.

    Parameters
    ----------
    balance
        Serie horaria de generación menos demanda, en MW (positivo =
        excedente, negativo = déficit). Longitud T. Es la misma serie
        `balance` usada en el resto del pipeline (`_comun.cargar_balances`).
    e_bess_mwh, p_bess_mw
        Capacidad energética y potencia nominal del BESS ya
        dimensionado (objetivo específico 2 — salida de
        `pipeline/04_optimo.py`, columnas `e_bess_mwh` y `p_bess_mw` de
        `resultados/04_optimos.xlsx`).
    regla
        Una de "R1".."R5" (Sección 3.10.2 de la tesis; ver
        `NOMBRES_REGLAS`).
    demanda_mw
        Demanda horaria (escalar si es plana, o arreglo de longitud T).
        Necesaria para calcular la LPSP tal como se define en la
        Ecuación 2.1 (LPSP = ENS / demanda total). Si es None, se usa
        como aproximación la energía total en déficit del propio
        balance, lo que subestima levemente el denominador si la
        demanda excede la generación incluso en horas de excedente
        parcial; para reproducir exactamente la LPSP del resto del
        pipeline, provéala explícitamente.
    eficiencia_carga, eficiencia_descarga
        Eficiencias de ida y de vuelta del BESS.
    soc_min, soc_max
        Ventana física de SOC (fracción de `e_bess_mwh`), igual para
        las cinco reglas.
    soc_inicial
        SOC al inicio de la simulación (fracción).
    horas_del_dia
        Arreglo de longitud T con la hora del día (0-23) de cada paso.
        Requerido por la Regla 3. Si es None, se infiere asumiendo que
        el primer paso es la hora 0 y la resolución es horaria.
    soc_res
        Parámetro de la Regla 2: piso operativo de SOC (fracción),
        con soc_min < soc_res < soc_max.
    ventana_horaria
        Parámetro de la Regla 3: (h_inicio, h_fin), ambos incluidos;
        admite ventanas que cruzan la medianoche, p. ej. (22, 4).
    ventana_suavizado_h
        Parámetro W de la Regla 4: ancho de la media móvil centrada,
        en horas.
    l_min_h
        Parámetro L_min de la Regla 5: longitud mínima, en horas, de
        una corrida de excedente para que sea elegible para carga.
    dt_h
        Paso de tiempo de la simulación, en horas (1.0 para datos
        horarios).

    Returns
    -------
    ResultadoSimulacion
    """
    if regla not in REGLAS_DISPONIBLES:
        raise ValueError(f"Regla '{regla}' no reconocida; use una de {REGLAS_DISPONIBLES}")
    if not (0.0 <= soc_min < soc_max <= 1.0):
        raise ValueError("Se requiere 0 <= soc_min < soc_max <= 1")
    if regla == "R2" and not (soc_min < soc_res < soc_max):
        raise ValueError("Se requiere soc_min < soc_res < soc_max para la Regla 2")

    balance = np.asarray(balance, dtype=float)
    T = len(balance)

    if horas_del_dia is None:
        horas_del_dia = np.arange(T) % 24
    else:
        horas_del_dia = np.asarray(horas_del_dia)

    # --- insumos auxiliares específicos de cada regla, precalculados ---
    aux: dict = {"ventana_horaria": ventana_horaria, "l_min": l_min_h}
    if regla == "R4":
        aux["balance_suavizado"] = _media_movil_centrada(balance, ventana_suavizado_h)
    if regla == "R5":
        aux["longitud_bloque_excedente"] = _longitudes_de_bloque(balance > 0)

    # --- series de salida -------------------------------------------------
    soc = np.empty(T)
    carga_mwh = np.zeros(T)
    descarga_mwh = np.zeros(T)
    vertimiento_mwh = np.zeros(T)
    ens_mwh = np.zeros(T)

    soc_prev = soc_inicial

    for t in range(T):
        d_deseado = _decision_despacho(regla, t, balance, horas_del_dia, aux)

        p_carga_intento = max(0.0, d_deseado)
        p_descarga_intento = max(0.0, -d_deseado)

        # ---- carga: limitada por el excedente REAL disponible (nunca se
        #      puede cargar más de lo que realmente se está generando de
        #      más), la potencia nominal y el espacio libre de SOC ----
        excedente_real_mw = max(0.0, balance[t])
        p_carga = min(p_carga_intento, excedente_real_mw, p_bess_mw)
        espacio_disponible_mwh = max(0.0, (soc_max - soc_prev) * e_bess_mwh)
        energia_cargada = min(p_carga * dt_h * eficiencia_carga, espacio_disponible_mwh)

        # ---- descarga: limitada por el déficit REAL, la potencia
        #      nominal, el piso de SOC (soc_min, o soc_res bajo la
        #      Regla 2) y la eficiencia ----
        deficit_real_mw = max(0.0, -balance[t])
        piso_efectivo = soc_res if regla == "R2" else soc_min
        energia_disponible_mwh = max(0.0, (soc_prev - piso_efectivo) * e_bess_mwh)
        p_descarga = min(p_descarga_intento, deficit_real_mw, p_bess_mw)
        energia_retirada_mwh = min(p_descarga * dt_h / eficiencia_descarga, energia_disponible_mwh)
        energia_entregada_mwh = energia_retirada_mwh * eficiencia_descarga

        soc_actual = soc_prev + energia_cargada / e_bess_mwh - energia_retirada_mwh / e_bess_mwh
        soc[t] = float(np.clip(soc_actual, soc_min, soc_max))
        soc_prev = soc[t]

        carga_mwh[t] = energia_cargada
        descarga_mwh[t] = energia_entregada_mwh

        # ---- contabilidad de red: SIEMPRE respecto del balance real,
        #      independientemente de lo que la regla haya intentado ----
        vertimiento_mwh[t] = max(0.0, excedente_real_mw * dt_h - energia_cargada / eficiencia_carga)
        ens_mwh[t] = max(0.0, deficit_real_mw * dt_h - energia_entregada_mwh)

    # --- indicadores agregados (Sección 3.10.3 de la tesis) --------------
    energia_deficit_total_mwh = float(np.sum(np.where(balance < 0, -balance, 0.0)) * dt_h)
    energia_excedente_total_mwh = float(np.sum(np.where(balance > 0, balance, 0.0)) * dt_h)

    if demanda_mw is None:
        demanda_total_mwh = energia_deficit_total_mwh + float(np.sum(descarga_mwh))
        demanda_total_mwh = max(demanda_total_mwh, 1e-9)
    else:
        demanda_arr = np.broadcast_to(np.asarray(demanda_mw, dtype=float), (T,))
        demanda_total_mwh = float(np.sum(demanda_arr) * dt_h)

    lpsp = float(np.sum(ens_mwh) / demanda_total_mwh) if demanda_total_mwh > 0 else float("nan")
    cobertura_deficit = (
        1.0 - float(np.sum(ens_mwh) / energia_deficit_total_mwh)
        if energia_deficit_total_mwh > 0 else float("nan")
    )
    frac_vertida = (
        float(np.sum(vertimiento_mwh) / energia_excedente_total_mwh)
        if energia_excedente_total_mwh > 0 else 0.0
    )
    ciclos_equivalentes = float((np.sum(carga_mwh) + np.sum(descarga_mwh)) / (2.0 * e_bess_mwh))

    neto_tras_bess = balance + (descarga_mwh - carga_mwh) / dt_h
    rampas = np.diff(neto_tras_bess)
    suavidad_rampa_mw = float(np.std(rampas)) if len(rampas) > 1 else float("nan")

    parametros: dict = {}
    if regla == "R2":
        parametros["soc_res"] = soc_res
    elif regla == "R3":
        parametros["ventana_horaria"] = f"{ventana_horaria[0]}-{ventana_horaria[1]}"
    elif regla == "R4":
        parametros["ventana_suavizado_h"] = ventana_suavizado_h
    elif regla == "R5":
        parametros["l_min_h"] = l_min_h

    return ResultadoSimulacion(
        regla=regla, soc=soc, carga_mwh=carga_mwh, descarga_mwh=descarga_mwh,
        vertimiento_mwh=vertimiento_mwh, ens_mwh=ens_mwh, lpsp=lpsp,
        cobertura_deficit=cobertura_deficit, frac_vertida=frac_vertida,
        ciclos_equivalentes=ciclos_equivalentes, suavidad_rampa_mw=suavidad_rampa_mw,
        parametros=parametros,
    )


# ---------------------------------------------------------------------
# Comparación de las cinco reglas sobre una misma serie
# ---------------------------------------------------------------------
def comparar_reglas(
    balance: Sequence[float],
    e_bess_mwh: float,
    p_bess_mw: float,
    reglas: tuple[str, ...] = REGLAS_DISPONIBLES,
    **kwargs,
) -> pd.DataFrame:
    """Corre las reglas indicadas sobre la misma serie, a la misma
    capacidad ya dimensionada (E*), y devuelve una tabla comparativa
    (una fila por regla) con los indicadores de la Sección 3.10.3 de la
    tesis.

    Cualquier parámetro adicional (`demanda_mw`, `soc_res`,
    `ventana_horaria`, `ventana_suavizado_h`, `l_min_h`,
    `eficiencia_carga`, etc.) se reenvía a `simular_regla` y aplica por
    igual a todas las reglas para las que sea pertinente.
    """
    filas = [
        simular_regla(balance, e_bess_mwh, p_bess_mw, regla=regla, **kwargs).resumen()
        for regla in reglas
    ]
    return pd.DataFrame(filas).set_index("regla")


# ---------------------------------------------------------------------
# Autoprueba con datos sintéticos (no depende de módulos privados)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    rng = np.random.default_rng(7)
    horas = 24 * 30  # un mes, resolución horaria
    t = np.arange(horas)
    hora_del_dia = t % 24

    generacion = 16.0 * np.clip(np.sin((hora_del_dia - 6) / 24 * 2 * np.pi), 0, None)
    generacion *= 1.0 + 0.25 * rng.standard_normal(horas)  # nubosidad
    generacion = np.clip(generacion, 0, None)
    demanda = 8.0 * np.ones(horas)
    balance_demo = generacion - demanda

    tabla = comparar_reglas(
        balance_demo, e_bess_mwh=60.0, p_bess_mw=15.0, demanda_mw=demanda,
        soc_res=0.30, ventana_horaria=(18, 22), ventana_suavizado_h=6, l_min_h=3,
    )
    with pd.option_context("display.width", 120, "display.float_format", "{:.4f}".format):
        print(tabla[["nombre_regla", "lpsp", "cobertura_deficit", "frac_vertida",
                      "ciclos_equivalentes", "suavidad_rampa_mw"]])
