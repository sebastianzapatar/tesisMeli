"""intermitencia/operacion_creg.py

Modelo de operación del BESS bajo los escenarios regulatorios de la
Resolución CREG 101 113 de 2026 ("Por la cual se definen los mecanismos
para incorporar sistemas de almacenamiento de energía eléctrica con
baterías -SAEB- en el Sistema Interconectado Nacional").

Objetivo específico 3 de la tesis: *proponer un modelo de simulación
que considere distintos escenarios de operación del almacenamiento*.

Diseño
------
Un escenario de operación es la combinación de dos cosas independientes:

1. **Modalidad regulatoria** (qué puede hacer el SAEB según la CREG):

   =====  ==========================================================
   M0     Referencia técnica: PV + BESS atendiendo una demanda, sin
          capa regulatoria. Es el caso de los pasos 03-05 y reproduce
          exactamente `almacenamiento.simular_soc` con la regla R1.
   M1     Recurso de generación híbrido (Título III, arts. 61-68):
          una sola frontera de generación; potencia máxima declarada
          para el conjunto PV+SAEB (art. 61 parág.; art. 70); el SAEB
          SOLO se carga con la planta, nunca desde la red (art. 66);
          el SAEB no aumenta la ENFICC (art. 65); reserva de regulación
          primaria >= 3 % de la potencia del inversor durante >= 1 min
          (art. 71 b.15; arts. 62-63 parág.: las solares híbridas
          pierden la excepción de regulación primaria).
   M2     SAEB independiente (Título II, arts. 44-60): >= 5 MW, no
          comparte conexión con la planta; fronteras separadas de carga
          y descarga (art. 52); la carga se compra en bolsa a precio
          horario (art. 47); la descarga se oferta como planta
          despachada centralmente (arts. 44a, 59); tolerancia de
          desviación 0 % (art. 50); regulación primaria obligatoria en
          carga y descarga (art. 48); sin cargo por confiabilidad
          (art. 44).
   M3     SAEB como activo de red (Título I, arts. 4-21): remuneración
          regulada; disponibilidad = min(potencia disponible / nominal,
          energía utilizable / energía requerida por la función)
          (art. 15), sin contar la capacidad restringida por estado de
          carga; máximo 175 h/año de indisponibilidad en ventana móvil
          de 12 meses (art. 16); eficiencia mínima de ciclo completo
          verificada con balance mensual del ASIC (arts. 6, 20).
   =====  ==========================================================

2. **Política de despacho** (cómo decide hora a hora):

   =====  ==========================================================
   R1-R5  Las reglas de la Sección 3.10 (mismo significado que en
          `reglas_operacion.py`).
   P1     Arbitraje por horas declaradas (art. 59 c-ii): cada día se
          carga en las k horas más baratas y se descarga en las k más
          caras del precio de bolsa.
   LP     Programa óptimo con horizonte rodante (art. 59 c-i y d: el
          modelo de despacho decide las horas de carga y el día t tiene
          en cuenta las condiciones del día t-1). Es la cota superior
          (información perfecta dentro de la ventana) contra la que se
          mide cuánto valor deja sobre la mesa cada regla.
   =====  ==========================================================

Todas las combinaciones comparten un único motor físico (límite de
potencia, eficiencias, ventana de SOC, autodescarga), igual al de
`almacenamiento.py`, de modo que cualquier diferencia entre escenarios
es atribuible a la regulación o a la política, no a la física.

Convenciones: paso de 1 h (MW = MWh por paso); carga > 0; descarga > 0;
precios en USD/MWh (ver `cargar_precios_bolsa` para COP/kWh de XM).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Sequence

import numpy as np
import pandas as pd

__all__ = [
    "MODALIDADES",
    "POLITICAS",
    "ParametrosBESS",
    "ParametrosRegulatorios",
    "ResultadoEscenario",
    "simular_escenario",
    "optimizar_escenario",
    "correr_escenario",
    "cargar_precios_bolsa",
    "alinear_precios",
]

MODALIDADES = {
    "M0": "Referencia técnica (sin capa regulatoria)",
    "M1": "Recurso de generación híbrido (CREG 101 113, Tít. III)",
    "M2": "SAEB independiente (CREG 101 113, Tít. II)",
    "M3": "SAEB como activo de red (CREG 101 113, Tít. I)",
}

POLITICAS = {
    "R1": "Despacho directo (línea base)",
    "R2": "Reserva mínima de SOC",
    "R3": "Ventana horaria de descarga",
    "R4": "Aplanamiento del perfil",
    "R5": "Carga priorizada por bloques",
    "P1": "Arbitraje por horas declaradas (art. 59 c-ii)",
    "LP": "Óptimo con horizonte rodante (art. 59 c-i)",
}

_EPS = 1e-12


# ---------------------------------------------------------------------
# Parámetros
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class ParametrosBESS:
    """Física del BESS. Mismos significados que `config.Bess`."""

    e_mwh: float
    p_mw: float
    eff_carga: float = 0.95
    eff_descarga: float = 0.95
    soc_min_frac: float = 0.10
    soc_max_frac: float = 1.00
    soc_inicial_frac: float = 0.50
    autodescarga_frac_h: float = 0.0
    consumo_aux_frac: float = 0.0   # consumo auxiliar, fracción de P nominal por hora en operación

    @classmethod
    def desde_config(cls, bess_cfg, e_mwh: float, p_mw: float | None = None,
                     consumo_aux_frac: float = 0.0) -> "ParametrosBESS":
        """Construye los parámetros a partir de `cfg.bess` del proyecto."""
        if p_mw is None:
            p_mw = e_mwh / bess_cfg.duracion_h
        return cls(
            e_mwh=float(e_mwh), p_mw=float(p_mw),
            eff_carga=float(bess_cfg.eff_carga),
            eff_descarga=float(bess_cfg.eff_descarga),
            soc_min_frac=float(bess_cfg.soc_min_frac),
            soc_max_frac=float(bess_cfg.soc_max_frac),
            soc_inicial_frac=float(bess_cfg.soc_inicial_frac),
            autodescarga_frac_h=float(bess_cfg.autodescarga_frac_h),
            consumo_aux_frac=float(consumo_aux_frac),
        )


@dataclass(frozen=True)
class ParametrosRegulatorios:
    """Parámetros que traducen la Resolución CREG 101 113 de 2026.

    Los valores por defecto son los numéricos que fija la propia
    resolución cuando los fija; los demás (marcados REVISAR) dependen de
    la UPME, el CNO o del caso de estudio y deben justificarse.
    """

    modalidad: str = "M0"

    # --- Regulación primaria de frecuencia (art. 71 b.15; art. 48) ----
    rpf_activa: bool | None = None      # None = según modalidad (M1, M2, M3: sí; M0: no)
    rpf_frac: float = 0.03              # >= 3 % de la potencia nominal del inversor
    rpf_duracion_h: float = 1.0 / 60.0  # sostenible al menos 1 minuto

    # --- M1: recurso híbrido -------------------------------------------
    p_max_declarada_mw: float | None = None   # potencia máxima del conjunto en la frontera (art. 61 parág.)
    precio_contrato_usd_mwh: float = 0.0      # REVISAR: precio del contrato que respalda D(t)

    # --- M3: activo de red ---------------------------------------------
    e_funcion_mwh: float | None = None        # energía requerida por la función comprometida (art. 15). REVISAR
    eficiencia_minima: float = 0.85           # REVISAR: la fija la UPME para STN/STR (art. 6)
    max_horas_indisp: float = 175.0           # art. 16
    limite_importacion_mw: float = 0.0        # capacidad de la red hacia el nodo (art. 4 d, e). REVISAR
    ventana_recarga_red: tuple[int, int] | None = None  # horas en que se permite recargar desde la red

    # --- Valoración ------------------------------------------------------
    voll_usd_mwh: float = 600.0               # REVISAR: costo incremental de racionamiento (UPME/CREG)
    costo_degradacion_usd_mwh: float = 0.0    # por MWh de throughput (carga + descarga)

    def rpf_aplica(self) -> bool:
        if self.rpf_activa is not None:
            return bool(self.rpf_activa)
        return self.modalidad in ("M1", "M2", "M3")


# ---------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------
@dataclass
class ResultadoEscenario:
    modalidad: str
    politica: str
    series: pd.DataFrame
    indicadores: dict
    parametros: dict = field(default_factory=dict)

    def resumen(self) -> dict:
        fila = {"modalidad": self.modalidad,
                "nombre_modalidad": MODALIDADES[self.modalidad],
                "politica": self.politica,
                "nombre_politica": POLITICAS[self.politica]}
        fila.update(self.indicadores)
        return fila


# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------
def _longitudes_de_bloque(mascara: np.ndarray) -> np.ndarray:
    n = len(mascara)
    out = np.zeros(n, dtype=int)
    i = 0
    while i < n:
        if mascara[i]:
            j = i
            while j < n and mascara[j]:
                j += 1
            out[i:j] = j - i
            i = j
        else:
            i += 1
    return out


def _en_ventana(h: int, ventana: tuple[int, int] | None) -> bool:
    if ventana is None:
        return False
    a, b = ventana
    return (a <= h <= b) if a <= b else (h >= a or h <= b)


def _rangos_horas_declaradas(precios: np.ndarray, dias: np.ndarray, k: int):
    """Para la política P1: máscaras de horas de carga (k más baratas
    del día) y de descarga (k más caras del día)."""
    carga = np.zeros(len(precios), dtype=bool)
    descarga = np.zeros(len(precios), dtype=bool)
    for d in np.unique(dias):
        idx = np.flatnonzero(dias == d)
        if len(idx) < 2 * k:
            continue
        orden = idx[np.argsort(precios[idx], kind="stable")]
        carga[orden[:k]] = True
        descarga[orden[-k:]] = True
    return carga, descarga


def _limites_fisicos(b: ParametrosBESS, reg: ParametrosRegulatorios):
    """Potencia y ventana de SOC efectivas una vez reservada la banda de
    regulación primaria (art. 71 b.15): la reserva se resta de la
    potencia en ambos sentidos y se guarda la energía para sostenerla
    durante `rpf_duracion_h` hacia arriba (descarga) y hacia abajo
    (carga)."""
    r = reg.rpf_frac * b.p_mw if reg.rpf_aplica() else 0.0
    p_lim = max(0.0, b.p_mw - r)
    e_res = r * reg.rpf_duracion_h
    piso = b.soc_min_frac * b.e_mwh + e_res / max(b.eff_descarga, _EPS)
    techo = b.soc_max_frac * b.e_mwh - e_res * b.eff_carga
    if techo < piso:
        techo = piso
    return p_lim, piso, techo, r


# ---------------------------------------------------------------------
# Motor de simulación con políticas heurísticas (R1-R5, P1)
# ---------------------------------------------------------------------
def simular_escenario(
    generacion_mw: Sequence[float],
    demanda_mw: float | Sequence[float],
    bess: ParametrosBESS,
    reg: ParametrosRegulatorios,
    politica: str = "R1",
    *,
    precios_usd_mwh: Sequence[float] | None = None,
    indice: pd.DatetimeIndex | None = None,
    soc_res: float = 0.30,
    ventana_horaria: tuple[int, int] = (18, 22),
    ventana_suavizado_h: int = 6,
    l_min_h: int = 3,
    k_horas_arbitraje: int = 4,
) -> ResultadoEscenario:
    """Simula hora a hora una combinación (modalidad, política).

    Parameters
    ----------
    generacion_mw
        Generación PV horaria P(t) en la planta ya dimensionada
        (P_PV* del paso 04, NO la planta de 100 MW de `config.yaml`).
    demanda_mw
        Compromiso D(t): demanda a atender (M0, M3) o energía
        comprometida en contrato en la frontera (M1) o perfil de la
        cartera virtual PV+SAEB (M2).
    precios_usd_mwh
        Precio de bolsa horario alineado con `generacion_mw`. Necesario
        para P1 y para los indicadores económicos.
    indice
        DatetimeIndex horario; se usa para horas del día, días y meses.
    """
    if politica not in POLITICAS or politica == "LP":
        raise ValueError(f"Política '{politica}' no válida aquí (use optimizar_escenario para LP).")
    if reg.modalidad not in MODALIDADES:
        raise ValueError(f"Modalidad '{reg.modalidad}' no reconocida.")

    P = np.asarray(generacion_mw, dtype=float)
    T = len(P)
    D = np.broadcast_to(np.asarray(demanda_mw, dtype=float), (T,)).astype(float)
    if indice is None:
        indice = pd.date_range("2001-01-01", periods=T, freq="h")
    hora = indice.hour.to_numpy()
    dia = pd.factorize(indice.normalize())[0]
    pi = (np.zeros(T) if precios_usd_mwh is None
          else np.asarray(precios_usd_mwh, dtype=float))
    if len(pi) != T:
        raise ValueError("precios_usd_mwh debe tener la misma longitud que la generación.")
    if politica == "P1" and precios_usd_mwh is None:
        raise ValueError("La política P1 necesita precios de bolsa.")

    mod = reg.modalidad
    v = P - D                                   # balance de la cartera

    # --- insumos de las reglas -----------------------------------------
    if politica == "R4":
        tendencia = pd.Series(v).rolling(ventana_suavizado_h, center=True,
                                         min_periods=1).mean().to_numpy()
    if politica == "R5":
        bloque = _longitudes_de_bloque(v > 0)
    if politica == "P1":
        m_carga, m_desc = _rangos_horas_declaradas(pi, dia, k_horas_arbitraje)

    p_lim, piso, techo, r_rpf = _limites_fisicos(bess, reg)
    piso_desc = max(piso, soc_res * bess.e_mwh) if politica == "R2" else piso
    e_func = (reg.e_funcion_mwh if reg.e_funcion_mwh is not None
              else bess.p_mw * 2.0)            # REVISAR: 2 h de potencia nominal por defecto
    p_max = (reg.p_max_declarada_mw if reg.p_max_declarada_mw is not None else np.inf)
    aux = bess.consumo_aux_frac * bess.p_mw

    # --- series de salida -----------------------------------------------
    c_pv = np.zeros(T); g = np.zeros(T); d = np.zeros(T); s = np.zeros(T)
    u = np.zeros(T); sh = np.zeros(T); ex = np.zeros(T); imp = np.zeros(T)
    disp = np.ones(T)

    soc = float(np.clip(bess.soc_inicial_frac * bess.e_mwh, piso, techo))
    for t in range(T):
        if bess.autodescarga_frac_h > 0:
            soc -= max(0.0, soc - bess.soc_min_frac * bess.e_mwh) * bess.autodescarga_frac_h

        # ---------- 1. intención de la política (MW; + carga, - descarga) ----
        vt = v[t]
        if politica in ("R1", "R2"):
            a = vt
        elif politica == "R3":
            a = vt if (vt >= 0 or _en_ventana(hora[t], ventana_horaria)) else 0.0
        elif politica == "R4":
            a = vt - tendencia[t]
        elif politica == "R5":
            a = vt if vt < 0 else (vt if bloque[t] >= l_min_h else 0.0)
        else:  # P1
            a = p_lim if m_carga[t] else (-p_lim if m_desc[t] else 0.0)
            # En M0/M1/M3 la confiabilidad manda: un déficit se cubre aunque
            # no sea hora "cara"; en M2 el SAEB solo sigue al mercado.
            if mod != "M2" and vt < 0 and a >= 0:
                a = vt

        # ---------- 2. carga ----------------------------------------------
        espacio = max(0.0, techo - soc) / bess.eff_carga      # MW AC que caben
        if a > 0:
            if mod == "M2":
                gt = min(a, p_lim, espacio)                  # desde la red (art. 47)
                g[t] = gt
            else:
                # M0, M3: solo con excedente local; M1: con la propia planta
                # (art. 66); con P1 en M1 puede cargar aunque P < D.
                fuente = P[t] if (mod == "M1" and politica == "P1") else max(0.0, vt)
                c_pv[t] = min(a, fuente, p_lim, espacio)
            soc += (c_pv[t] + g[t]) * bess.eff_carga

        # ---------- 2b. M3: recarga desde la red en la ventana permitida ----
        if mod == "M3" and reg.ventana_recarga_red is not None \
                and _en_ventana(hora[t], reg.ventana_recarga_red) and vt <= 0:
            objetivo = min(techo, piso + e_func)
            falta = max(0.0, objetivo - soc) / bess.eff_carga
            cupo = max(0.0, reg.limite_importacion_mw - max(0.0, -vt))
            gt = min(falta, cupo, p_lim - c_pv[t])
            if gt > 0:
                g[t] += gt
                soc += gt * bess.eff_carga

        # ---------- 3. descarga --------------------------------------------
        if a < 0:
            disponible = max(0.0, soc - piso_desc) * bess.eff_descarga
            if mod == "M2":
                tope = p_lim
            elif mod == "M1" and politica == "P1":
                tope = p_lim                                 # puede exportar por encima de D
            else:
                tope = max(0.0, -vt)                         # solo cubre déficit
            d[t] = min(-a, tope, p_lim, disponible)
            soc -= d[t] / bess.eff_descarga

        soc = min(max(soc, min(piso, piso_desc)), techo)
        s[t] = soc

        # ---------- 4. contabilidad en la frontera / nodo ------------------
        if mod == "M0":
            servido = min(D[t], P[t] - c_pv[t] + d[t])
            sh[t] = D[t] - servido
            u[t] = max(0.0, P[t] - c_pv[t] + d[t] - D[t])
        elif mod == "M1":
            x = P[t] - c_pv[t] + d[t]
            u[t] = max(0.0, x - p_max)                       # recorte por potencia declarada
            x -= u[t]
            sh[t] = max(0.0, D[t] - x)
            ex[t] = max(0.0, x - D[t])
        elif mod == "M2":
            x = P[t] + d[t] - g[t]                           # cartera virtual
            sh[t] = max(0.0, D[t] - x)
            ex[t] = max(0.0, x - D[t])
        else:  # M3
            neto = P[t] - c_pv[t] + d[t] - D[t]
            if neto < 0:
                cupo = max(0.0, reg.limite_importacion_mw - g[t])
                imp[t] = min(-neto, cupo)
                sh[t] = -neto - imp[t]
            else:
                u[t] = neto
            # Disponibilidad (art. 15): mínimo entre potencia y energía
            # utilizable frente a la energía requerida por la función.
            e_util = max(0.0, soc - piso) * bess.eff_descarga
            disp[t] = min(1.0, e_util / e_func if e_func > 0 else 1.0)

    series = pd.DataFrame({
        "generacion_mw": P, "demanda_mw": D, "precio_usd_mwh": pi,
        "carga_pv_mwh": c_pv, "carga_red_mwh": g, "descarga_mwh": d,
        "soc_mwh": s, "vertimiento_mwh": u, "faltante_mwh": sh,
        "excedente_vendido_mwh": ex, "importacion_mwh": imp,
        "disponibilidad": disp,
    }, index=indice)
    ind = _indicadores(series, bess, reg, aux)
    params = {"soc_res": soc_res, "ventana_horaria": f"{ventana_horaria[0]}-{ventana_horaria[1]}",
              "ventana_suavizado_h": ventana_suavizado_h, "l_min_h": l_min_h,
              "k_horas_arbitraje": k_horas_arbitraje, "p_lim_mw": p_lim,
              "reserva_rpf_mw": r_rpf}
    return ResultadoEscenario(mod, politica, series, ind, params)


# ---------------------------------------------------------------------
# Indicadores (técnicos, regulatorios y económicos)
# ---------------------------------------------------------------------
def _indicadores(df: pd.DataFrame, b: ParametrosBESS, reg: ParametrosRegulatorios,
                 aux_mw: float) -> dict:
    P, D = df["generacion_mw"].to_numpy(), df["demanda_mw"].to_numpy()
    c_in = (df["carga_pv_mwh"] + df["carga_red_mwh"]).to_numpy()
    d = df["descarga_mwh"].to_numpy()
    sh = df["faltante_mwh"].to_numpy()
    pi = df["precio_usd_mwh"].to_numpy()
    v = P - D
    deficit = np.clip(-v, 0, None).sum()
    excedente = np.clip(v, 0, None).sum()
    D_tot = D.sum()

    # Rampas del perfil neto entregado
    neto = P - df["carga_pv_mwh"].to_numpy() + d - df["carga_red_mwh"].to_numpy()
    rampa = np.diff(neto)

    n_anios = len(df) / 8760.0
    e_util = b.e_mwh * (b.soc_max_frac - b.soc_min_frac)
    out = {
        # ---- técnicos (comparables con la Sección 3.10.3) ----
        "lpsp": sh.sum() / D_tot if D_tot > 0 else np.nan,
        "cobertura_deficit": 1.0 - sh.sum() / deficit if deficit > 0 else np.nan,
        "frac_vertida": df["vertimiento_mwh"].sum() / excedente if excedente > 0 else 0.0,
        "ciclos_equivalentes_anio": (d.sum() / e_util / n_anios) if e_util > 0 else 0.0,
        "suavidad_rampa_mw": float(np.std(rampa)) if len(rampa) > 1 else np.nan,
        "horas_con_faltante": int((sh > 1e-9).sum()),
        "frac_carga_desde_red": (df["carga_red_mwh"].sum() / c_in.sum()) if c_in.sum() > 0 else 0.0,
        # ---- económicos ----
        "ingreso_excedentes_usd": float((pi * df["excedente_vendido_mwh"].to_numpy()).sum()),
        "costo_faltantes_bolsa_usd": float((pi * sh).sum()),
        "costo_carga_red_usd": float((pi * df["carga_red_mwh"].to_numpy()).sum()),
        "ingreso_descarga_usd": float((pi * d).sum()),
        "costo_ens_voll_usd": float(reg.voll_usd_mwh * sh.sum()),
        "costo_degradacion_usd": float(reg.costo_degradacion_usd_mwh * (c_in.sum() + d.sum())),
    }
    out["margen_arbitraje_usd"] = out["ingreso_descarga_usd"] - out["costo_carga_red_usd"]
    for k in [k for k in out if k.endswith("_usd")]:
        out[k.replace("_usd", "_usd_anio")] = out.pop(k) / n_anios

    # ---- regulatorios ----
    idx = df.index
    # Eficiencia mensual medida en el punto de conexión (arts. 6, 20)
    e_aux = aux_mw * np.ones(len(df))
    mensual = pd.DataFrame({"entrada": c_in + e_aux, "salida": d}, index=idx) \
        .resample("MS").sum()
    activos = mensual["entrada"] > 1e-6
    eff_m = (mensual.loc[activos, "salida"] / mensual.loc[activos, "entrada"])
    falt_eff = (reg.eficiencia_minima * mensual["entrada"] - mensual["salida"]).clip(lower=0)
    out["eficiencia_mensual_min"] = float(eff_m.min()) if len(eff_m) else np.nan
    out["eficiencia_mensual_p50"] = float(eff_m.median()) if len(eff_m) else np.nan
    out["meses_bajo_eficiencia_minima"] = int((eff_m < reg.eficiencia_minima).sum())
    out["energia_faltante_eficiencia_mwh_anio"] = float(falt_eff.sum() / n_anios)

    # Indisponibilidad (arts. 15-16): horas con disponibilidad < 1,
    # máximo en ventana móvil de 12 meses.
    indisp = (df["disponibilidad"].to_numpy() < 1.0 - 1e-9).astype(float)
    movil = pd.Series(indisp, index=idx).rolling(8760, min_periods=min(8760, len(df))).sum()
    out["horas_indisp_anio_p50"] = float(pd.Series(indisp, index=idx).resample("YS").sum().median())
    out["horas_indisp_max_12m"] = float(movil.max()) if movil.notna().any() else float(indisp.sum())
    out["cumple_175h"] = bool(out["horas_indisp_max_12m"] <= reg.max_horas_indisp) \
        if reg.modalidad == "M3" else np.nan
    out["disponibilidad_media"] = float(df["disponibilidad"].mean())

    # Desviaciones frente al compromiso (art. 50: tolerancia 0 %)
    out["horas_desviacion"] = out["horas_con_faltante"]
    return out


# ---------------------------------------------------------------------
# Programa óptimo con horizonte rodante (LP)
# ---------------------------------------------------------------------
def optimizar_escenario(
    generacion_mw: Sequence[float],
    demanda_mw: float | Sequence[float],
    bess: ParametrosBESS,
    reg: ParametrosRegulatorios,
    *,
    precios_usd_mwh: Sequence[float] | None = None,
    indice: pd.DatetimeIndex | None = None,
    horizonte_h: int = 48,
    compromiso_h: int = 24,
    peso_funcion_usd_mwh: float = 50.0,
    valor_terminal_usd_mwh: float | None = None,
) -> ResultadoEscenario:
    """Despacho óptimo por programación lineal, resuelto día a día con
    `horizonte_h` horas de visión y `compromiso_h` horas comprometidas
    (art. 59 c-i y d). Requiere `scipy` (HiGHS).

    Variables por hora: c (carga desde la planta/excedente local),
    g (carga desde la red), d (descarga), s (SOC), u (vertimiento),
    sh (faltante frente a D), ex (excedente vendido), m (importación, M3),
    f (déficit de energía para la función, M3).

    Objetivo (minimizar), según modalidad:
      M0  VoLL·sh + c_deg·(c+d)
      M1  VoLL·sh − π·ex + c_deg·(c+d)
      M2  π·g − π·d + c_deg·(g+d)               (el SAEB solo ve el mercado)
      M3  VoLL·sh + π·(g+m) + w·f + c_deg·(c+g+d)
    menos un valor terminal por la energía que queda en el SOC al final
    de cada ventana (evita que el horizonte rodante vacíe la batería por
    miopía). Por defecto: 0.5·VoLL·η_d (M0, M1, M3) o la mediana del
    precio de la ventana·η_d (M2).
    """
    from scipy.optimize import linprog
    from scipy.sparse import lil_matrix

    P = np.asarray(generacion_mw, dtype=float)
    T = len(P)
    D = np.broadcast_to(np.asarray(demanda_mw, dtype=float), (T,)).astype(float)
    if indice is None:
        indice = pd.date_range("2001-01-01", periods=T, freq="h")
    pi = np.zeros(T) if precios_usd_mwh is None else np.asarray(precios_usd_mwh, dtype=float)
    mod = reg.modalidad
    if mod in ("M1", "M2") and precios_usd_mwh is None:
        raise ValueError(f"La modalidad {mod} con LP necesita precios de bolsa.")

    p_lim, piso, techo, r_rpf = _limites_fisicos(bess, reg)
    e_func = reg.e_funcion_mwh if reg.e_funcion_mwh is not None else bess.p_mw * 2.0
    p_max = reg.p_max_declarada_mw if reg.p_max_declarada_mw is not None else 1e9
    ec, ed, sig = bess.eff_carga, bess.eff_descarga, bess.autodescarga_frac_h
    cdeg, voll = reg.costo_degradacion_usd_mwh, reg.voll_usd_mwh
    hora = indice.hour.to_numpy()

    NV = 9   # c g d s u sh ex m f
    out = {k: np.zeros(T) for k in ["c", "g", "d", "s", "u", "sh", "ex", "m", "f"]}
    soc0 = float(np.clip(bess.soc_inicial_frac * bess.e_mwh, piso, techo))

    t0 = 0
    while t0 < T:
        H = min(horizonte_h, T - t0)
        K = min(compromiso_h, H)
        sl = slice(t0, t0 + H)
        Pw, Dw, pw = P[sl], D[sl], pi[sl]
        iv = lambda k, h: k * H + h  # noqa: E731
        n = NV * H
        cost = np.zeros(n)
        lb = np.zeros(n)
        ub = np.full(n, np.inf)
        for h in range(H):
            # cotas
            ub[iv(0, h)] = p_lim if mod != "M2" else 0.0
            ub[iv(1, h)] = p_lim if mod in ("M2", "M3") else 0.0
            if mod == "M3" and reg.ventana_recarga_red is not None \
                    and not _en_ventana(hora[t0 + h], reg.ventana_recarga_red):
                ub[iv(1, h)] = 0.0
            ub[iv(2, h)] = p_lim
            lb[iv(3, h)], ub[iv(3, h)] = piso, techo
            ub[iv(6, h)] = 0.0 if mod in ("M0", "M3") else np.inf
            ub[iv(7, h)] = reg.limite_importacion_mw if mod == "M3" else 0.0
            ub[iv(8, h)] = e_func if mod == "M3" else 0.0
            if mod in ("M0", "M3"):
                ub[iv(0, h)] = min(p_lim, max(0.0, Pw[h] - Dw[h]))  # solo excedente local
            elif mod == "M1":
                ub[iv(0, h)] = min(p_lim, Pw[h])                          # art. 66
            # costos
            if mod == "M2":
                cost[iv(1, h)] = pw[h] + cdeg
                cost[iv(2, h)] = -pw[h] + cdeg
            else:
                cost[iv(0, h)] = cdeg
                cost[iv(2, h)] = cdeg
                cost[iv(5, h)] = voll
                if mod == "M1":
                    cost[iv(6, h)] = -pw[h]
                if mod == "M3":
                    cost[iv(1, h)] = pw[h] + cdeg
                    cost[iv(7, h)] = pw[h]
                    cost[iv(8, h)] = peso_funcion_usd_mwh
        # valor terminal de la energía almacenada al final de la ventana
        if valor_terminal_usd_mwh is not None:
            vt_val = valor_terminal_usd_mwh
        elif mod == "M2":
            vt_val = float(np.median(pw)) * ed
        else:
            vt_val = 0.5 * voll * ed
        cost[iv(3, H - 1)] -= vt_val
        # igualdades: SOC y balance en la frontera
        Aeq = lil_matrix((2 * H, n)); beq = np.zeros(2 * H)
        for h in range(H):
            r = h
            Aeq[r, iv(3, h)] = 1.0
            Aeq[r, iv(0, h)] = -ec
            Aeq[r, iv(1, h)] = -ec
            Aeq[r, iv(2, h)] = 1.0 / ed
            if h == 0:
                beq[r] = soc0 * (1 - sig)
            else:
                Aeq[r, iv(3, h - 1)] = -(1 - sig)
            r = H + h
            if mod == "M2":
                # cartera virtual: P + d - g - u + sh - ex = D
                Aeq[r, iv(2, h)] = 1.0; Aeq[r, iv(1, h)] = -1.0
            else:
                # P - c + d (+ m) - u + sh - ex = D
                Aeq[r, iv(0, h)] = -1.0; Aeq[r, iv(2, h)] = 1.0
                if mod == "M3":
                    Aeq[r, iv(7, h)] = 1.0
            Aeq[r, iv(4, h)] = -1.0
            Aeq[r, iv(5, h)] = 1.0
            Aeq[r, iv(6, h)] = -1.0
            beq[r] = Dw[h] - Pw[h]
        # desigualdades
        Aub = lil_matrix((3 * H, n)); bub = np.zeros(3 * H)
        for h in range(H):
            # potencia combinada de carga
            Aub[h, iv(0, h)] = 1.0; Aub[h, iv(1, h)] = 1.0; bub[h] = p_lim
            # M1: potencia máxima declarada del conjunto en la frontera
            r = H + h
            if mod == "M1":
                Aub[r, iv(0, h)] = -1.0; Aub[r, iv(2, h)] = 1.0; Aub[r, iv(4, h)] = -1.0
                bub[r] = p_max - Pw[h]
            # M3: importación + carga de red <= límite;  s + f >= piso + E_func
            if mod == "M3":
                Aub[r, iv(1, h)] = 1.0; Aub[r, iv(7, h)] = 1.0
                bub[r] = reg.limite_importacion_mw
                r2 = 2 * H + h
                Aub[r2, iv(3, h)] = -1.0; Aub[r2, iv(8, h)] = -1.0
                bub[r2] = -min(techo, piso + e_func)
        res = linprog(cost, A_ub=Aub.tocsr(), b_ub=bub, A_eq=Aeq.tocsr(), b_eq=beq,
                      bounds=list(zip(lb, ub)), method="highs")
        if res.status != 0:
            raise RuntimeError(f"LP sin solución en t={t0}: {res.message}")
        x = res.x
        for k, nombre in enumerate(["c", "g", "d", "s", "u", "sh", "ex", "m", "f"]):
            out[nombre][t0:t0 + K] = x[k * H: k * H + K]
        soc0 = out["s"][t0 + K - 1]
        t0 += K

    # Las holguras sh/ex pueden quedar degeneradas (costo cero en M2);
    # se recalculan a partir de los flujos físicos para que los
    # indicadores sean únicos.
    if mod in ("M1", "M2"):
        if mod == "M1":
            x = P - out["c"] + out["d"] - out["u"]
        else:
            x = P + out["d"] - out["g"]
            out["u"][:] = 0.0
        out["sh"] = np.clip(D - x, 0, None)
        out["ex"] = np.clip(x - D, 0, None)

    disp = np.ones(T)
    if mod == "M3":
        e_util = np.clip(out["s"] - piso, 0, None) * ed
        disp = np.minimum(1.0, e_util / e_func) if e_func > 0 else disp
    series = pd.DataFrame({
        "generacion_mw": P, "demanda_mw": D, "precio_usd_mwh": pi,
        "carga_pv_mwh": out["c"], "carga_red_mwh": out["g"], "descarga_mwh": out["d"],
        "soc_mwh": out["s"], "vertimiento_mwh": out["u"], "faltante_mwh": out["sh"],
        "excedente_vendido_mwh": out["ex"], "importacion_mwh": out["m"],
        "disponibilidad": disp,
    }, index=indice)
    ind = _indicadores(series, bess, reg, bess.consumo_aux_frac * bess.p_mw)
    return ResultadoEscenario(mod, "LP", series, ind,
                              {"horizonte_h": horizonte_h, "compromiso_h": compromiso_h,
                               "p_lim_mw": p_lim, "reserva_rpf_mw": r_rpf})


def correr_escenario(generacion_mw, demanda_mw, bess, reg, politica, **kw) -> ResultadoEscenario:
    """Punto de entrada único: despacha a la heurística o al LP."""
    if politica == "LP":
        claves_lp = {"precios_usd_mwh", "indice", "horizonte_h", "compromiso_h",
                     "peso_funcion_usd_mwh", "valor_terminal_usd_mwh"}
        return optimizar_escenario(generacion_mw, demanda_mw, bess, reg,
                                   **{k: v for k, v in kw.items() if k in claves_lp})
    claves = {"precios_usd_mwh", "indice", "soc_res", "ventana_horaria",
              "ventana_suavizado_h", "l_min_h", "k_horas_arbitraje"}
    return simular_escenario(generacion_mw, demanda_mw, bess, reg, politica,
                             **{k: v for k, v in kw.items() if k in claves})


# ---------------------------------------------------------------------
# Precios de bolsa (XM)
# ---------------------------------------------------------------------
def cargar_precios_bolsa(ruta, columna_fecha: str = "Fecha",
                         columna_precio: str | None = None,
                         unidad: str = "COP/kWh", trm_cop_usd: float | None = None) -> pd.Series:
    """Lee un archivo de precio de bolsa nacional horario de XM.

    Acepta el formato ancho de Sinergox (una fila por día, columnas
    "0".."23" u "Hora 1".."Hora 24") o el formato largo (Fecha-hora,
    precio). Devuelve una Serie horaria en USD/MWh.

    unidad: "COP/kWh" (lo que publica XM) o "USD/MWh".
    """
    from pathlib import Path
    ruta = Path(ruta)
    df = pd.read_csv(ruta) if ruta.suffix.lower() == ".csv" else pd.read_excel(ruta)
    cols_hora = [c for c in df.columns if str(c).strip().lower().replace("hora", "").strip().isdigit()]
    if len(cols_hora) >= 24:
        df[columna_fecha] = pd.to_datetime(df[columna_fecha])
        largo = df.melt(id_vars=[columna_fecha], value_vars=cols_hora[:24],
                        var_name="h", value_name="precio")
        h = largo["h"].astype(str).str.lower().str.replace("hora", "").str.strip().astype(int)
        if h.min() == 1:
            h = h - 1
        largo["ts"] = largo[columna_fecha] + pd.to_timedelta(h, unit="h")
        serie = largo.set_index("ts")["precio"].sort_index()
    else:
        col = columna_precio or [c for c in df.columns if c != columna_fecha][0]
        serie = pd.Series(df[col].to_numpy(),
                          index=pd.to_datetime(df[columna_fecha])).sort_index()
    serie = pd.to_numeric(serie, errors="coerce").astype(float)
    if unidad == "COP/kWh":
        if not trm_cop_usd:
            raise ValueError("Para convertir COP/kWh a USD/MWh indique trm_cop_usd.")
        serie = serie * 1000.0 / trm_cop_usd
    serie.name = "precio_usd_mwh"
    return serie


def alinear_precios(indice_gen: pd.DatetimeIndex, precios: pd.Series,
                    modo: str = "perfil_anual", anios: Sequence[int] | None = None) -> np.ndarray:
    """Pone el precio de bolsa sobre el índice horario de la generación.

    modo
      "mismo_instante" : unión exacta por fecha-hora (solo si los
                         registros se solapan).
      "perfil_anual"   : precio típico por (mes, día de la semana, hora)
                         de los `anios` elegidos; útil porque las series
                         de irradiancia (1998-2022) no coinciden con el
                         mercado actual. Para escenarios de hidrología
                         use `anios` de una sola fase ENSO (p. ej. 2024
                         Niño; 2022 Niña).
    """
    if modo == "mismo_instante":
        al = precios.reindex(indice_gen)
        if al.isna().any():
            raise ValueError(f"{int(al.isna().sum())} horas sin precio; use modo='perfil_anual'.")
        return al.to_numpy()
    p = precios.copy()
    if anios is not None:
        p = p[p.index.year.isin(list(anios))]
    tabla = p.groupby([p.index.month, p.index.dayofweek, p.index.hour]).mean()
    claves = list(zip(indice_gen.month, indice_gen.dayofweek, indice_gen.hour))
    vals = tabla.reindex(claves).to_numpy()
    if np.isnan(vals).any():
        respaldo = p.groupby(p.index.hour).mean()
        faltan = np.isnan(vals)
        vals[faltan] = respaldo.reindex(indice_gen.hour[faltan]).to_numpy()
    return vals
