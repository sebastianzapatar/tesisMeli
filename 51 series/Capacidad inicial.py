import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator

# ================================================================
# CONFIGURACIÓN
# ================================================================
RUTA_SERIES = "51 series/df_series_todas_las_subestaciones.xlsx"
RUTA_PSH = "PSH/PSH_resultados.xlsx"
DEMANDA_MW = 20
POTENCIA_PLANTA_MW = 100
EFICIENCIA = 0.17
POTENCIA_MODULO_W = 550
AREA_MODULO_M2 = 2.279 * 1.134
PORCENTAJE_MIN = 0.25
PORCENTAJE_MAX = 0.40

# ================================================================
# LECTURA DE DATOS
# ================================================================
df_series = pd.read_excel(RUTA_SERIES, index_col=0)
df_psh = pd.read_excel(RUTA_PSH, index_col=0)

# ================================================================
# PARÁMETROS DE LA PLANTA
# ================================================================
potencia_modulo_mw = POTENCIA_MODULO_W / 1_000_000
num_modulos = POTENCIA_PLANTA_MW / potencia_modulo_mw
area_total_m2 = num_modulos * AREA_MODULO_M2

# ================================================================
# PROCESAMIENTO DE LAS SERIES
# ================================================================
resultados = []

for serie in df_series.columns:

    # PSH
    PSH = df_psh.loc[serie, "PSH promedio [h/día]"]

    # Generación horaria [MW]
    generacion = df_series[serie] * area_total_m2 / 1_000_000 * EFICIENCIA

    # Balance horario [MW]
    balance = generacion - DEMANDA_MW

    # Excedentes positivos
    excedentes = balance.clip(lower=0)

    # Excedente diario [MWh]
    excedente_diario = excedentes.resample("D").sum()

    # P75 mensual
    resumen_mensual = excedente_diario.groupby(excedente_diario.index.month).quantile(0.75)

    # P75 global
    p75_global = excedente_diario.quantile(0.75)

    # Límites P75 mensual
    limite_inferior = resumen_mensual.min()
    limite_superior = resumen_mensual.max()

    # ============================================================
    # CUENTA DE TIENDA
    # ============================================================
    df_horario = pd.DataFrame({"Generacion": generacion})
    df_horario["Hora"] = df_horario.index.hour

    # Generación promedio por hora
    promedio_horario = df_horario.groupby("Hora")["Generacion"].mean()

    # Potencia solar AC máxima promedio [MW]
    potencia_solar_ac = promedio_horario.max()

    # Potencia BESS [MW]
    potencia_bess = max(potencia_solar_ac - DEMANDA_MW, 0)

    # Energía BESS [MWh]
    energia_bess = potencia_bess * PSH

    # Cuenta de tienda como % de la energía diaria
    porcentaje_planta = energia_bess / (POTENCIA_PLANTA_MW * PSH) * 100

    # Guardar resultados
    resultados.append({
        "Serie": serie,
        "PSH [h/día]": PSH,
        "P75 mensual mínimo [MWh]": limite_inferior,
        "P75 mensual máximo [MWh]": limite_superior,
        "P75 global [MWh]": p75_global,
        "Potencia solar AC [MW]": potencia_solar_ac,
        "Potencia BESS [MW]": potencia_bess,
        "Cuenta de tienda [MWh]": energia_bess,
        "% planta Cuenta de tienda": porcentaje_planta
    })

# ================================================================
# DATAFRAME FINAL
# ================================================================
df_resultados = pd.DataFrame(resultados)

# ================================================================
# GRÁFICA
# ================================================================
fig, ax1 = plt.subplots(figsize=(7, 3.5))

x = np.arange(len(df_resultados))
valores_porcentaje = df_resultados["% planta Cuenta de tienda"].values
valores_mwh = df_resultados["Cuenta de tienda [MWh]"].values

# Barras — eje izquierdo
ax1.bar(x, valores_porcentaje, color="grey", width=0.75)
ax1.set_ylabel("Cuenta base [%]", fontsize=10)

# Eje X
ax1.set_xticks(x)
ax1.set_xticklabels(df_resultados["Serie"], rotation=90, ha="right", fontsize=8)
ax1.tick_params(axis="x", which="both", length=0)

# Eje Y izquierdo
max_porcentaje = valores_porcentaje.max()
ax1.set_ylim(0, max_porcentaje * 1.20)
ax1.yaxis.set_minor_locator(AutoMinorLocator(2))
ax1.yaxis.set_ticks_position("both")
ax1.tick_params(axis="y", which="major", direction="in", labelsize=10, width=1.0, length=7)
ax1.tick_params(axis="y", which="minor", direction="in", width=1.0, length=3.5)
ax1.grid(axis="y", alpha=0.8)

# Eje Y derecho
ax2 = ax1.twinx()
max_mwh = valores_mwh.max()
ax2.set_ylim(0, max_mwh * 1.20)
ax2.set_ylabel("Capacidad base [MWh]", fontsize=10)
ax2.yaxis.set_minor_locator(AutoMinorLocator(2))
ax2.yaxis.set_ticks_position("right")
ax2.tick_params(axis="y", which="major", direction="in", labelsize=10, width=1.0, length=7)
ax2.tick_params(axis="y", which="minor", direction="in", width=1.0, length=3.5)

plt.tight_layout()
plt.show()

# ==========================================================
# HISTOGRAMA DE FRECUENCIAS
# CUENTA DE TIENDA — % DE LA ENERGÍA DIARIA
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator

# Datos
valores_porcentaje = df_resultados["% planta Cuenta de tienda"].dropna().values

# Figura
fig, ax = plt.subplots(figsize=(5, 3.5))

# Intervalos
bins = np.arange(0, 50, 5)

# Histograma
ax.hist(valores_porcentaje, bins=bins, color="grey", alpha=0.65,
        edgecolor="black", linewidth=0.8)

# Etiquetas
ax.set_xlabel("Capacidad base [% de la energía diaria]", fontsize=10)
ax.set_ylabel("Frecuencia", fontsize=10)

# Ticks menores
ax.xaxis.set_minor_locator(AutoMinorLocator(2))
ax.yaxis.set_minor_locator(AutoMinorLocator(2))

# Grid
ax.grid(color="grey", alpha=0.8)

# Ticks principales
ax.tick_params(direction="in", axis="both", which="major",
               labelsize=10, width=1.0, length=7)

# Ticks menores
ax.tick_params(direction="in", axis="both", which="minor",
               width=1.0, length=3.5)

# Ticks en ambos lados
ax.yaxis.set_ticks_position("both")
ax.xaxis.set_ticks_position("both")

# Ajuste
plt.tight_layout()
# Mostrar
plt.show()

# ==========================================================
# HISTOGRAMA DE FRECUENCIAS
# CUENTA DE TIENDA — CAPACIDAD [MWh]
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator

# Datos
valores_mwh = df_resultados["Cuenta de tienda [MWh]"].dropna().values

# Figura
fig, ax = plt.subplots(figsize=(5, 3.5))

# Intervalos
bins = np.arange(0, 300, 25)

# Histograma
ax.hist(valores_mwh, bins=bins, color="grey", alpha=0.65,
        edgecolor="black", linewidth=0.8)

# Etiquetas
ax.set_xlabel("Capacidad base [MWh]", fontsize=10)
ax.set_ylabel("Frecuencia", fontsize=10)

# Ticks menores
ax.xaxis.set_minor_locator(AutoMinorLocator(2))
ax.yaxis.set_minor_locator(AutoMinorLocator(2))

# Grid
ax.grid(color="grey", alpha=0.8)

# Ticks principales
ax.tick_params(direction="in", axis="both", which="major",
               labelsize=10, width=1.0, length=7)

# Ticks menores
ax.tick_params(direction="in", axis="both", which="minor",
               width=1.0, length=3.5)

# Ticks en ambos lados
ax.yaxis.set_ticks_position("both")
ax.xaxis.set_ticks_position("both")

# Ajuste
plt.tight_layout()

# Mostrar
plt.show()