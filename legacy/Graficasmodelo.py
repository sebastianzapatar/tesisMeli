# ================================================================
# MAPA DE CALOR DEL MODELO LOGÍSTICO GANADOR Phi(B,M)
# PORCENTAJE DE PLANTA
# ================================================================

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator


# ================================================================
# MODELO LOGÍSTICO GANADOR
# ================================================================

# Coeficientes estimados
a = -3.7991
b = 5.5261
c = 14.2735
d = -26.1268

# Límites de la función logística
LI = 0.30
LS = 0.50


# ================================================================
# 1. CREAR MALLA DE B_norm Y M_norm
# ================================================================

B = np.linspace(0, 1, 200)
M = np.linspace(0, 1, 200)

B_grid, M_grid = np.meshgrid(B, M)


# ================================================================
# 2. ARGUMENTO DE LA FUNCIÓN LOGÍSTICA
# ================================================================

z = (
    a
    + b * B_grid
    + c * M_grid
    + d * B_grid * M_grid
)


# ================================================================
# 3. CALCULAR Phi(B,M)
# ================================================================

Phi = LI + (LS - LI) / (1 + np.exp(-z))


# ================================================================
# 4. CONVERTIR A PORCENTAJE
# ================================================================

Phi_pct = Phi * 100


# ================================================================
# 5. MAPA DE CALOR
# ================================================================

fig, ax = plt.subplots(
    figsize=(5, 4)
)

contour = ax.contourf(
    B_grid,
    M_grid,
    Phi_pct,
    levels=20,
    cmap="viridis"
)


# ================================================================
# 6. LÍNEAS DE NIVEL
# ================================================================

lines = ax.contour(
    B_grid,
    M_grid,
    Phi_pct,
    levels=10,
    colors="black",
    linewidths=0.5,
    alpha=0.5
)

ax.clabel(
    lines,
    inline=True,
    fontsize=7,
    fmt="%.1f%%"
)


# ================================================================
# 7. PUNTOS REALES
# ================================================================

if "df_resumen" in globals():

    datos = df_resumen[
        ["Serie", "B_norm", "M_norm"]
    ].dropna()

    ax.scatter(
        datos["B_norm"],
        datos["M_norm"],
        s=25,
        facecolors="white",
        edgecolors="black",
        linewidths=0.9,
        zorder=10,
        label="Subestaciones/proyectos de ISA"
    )


# ================================================================
# 8. ETIQUETAS DE LOS EJES
# ================================================================

ax.set_xlabel(
    "Burstiness normalizado ($B_{norm}$)",
    fontsize=10
)

ax.set_ylabel(
    "Memory normalizado ($M_{norm}$)",
    fontsize=10
)


# ================================================================
# 9. LÍMITES DE LOS EJES
# ================================================================

ax.set_xlim(0, 1)
ax.set_ylim(0, 1)


# ================================================================
# 10. TICKS MENORES
# ================================================================

ax.xaxis.set_minor_locator(
    AutoMinorLocator(2)
)

ax.yaxis.set_minor_locator(
    AutoMinorLocator(2)
)


# ================================================================
# 11. TICKS PRINCIPALES HACIA ADENTRO
# ================================================================

ax.tick_params(
    axis="both",
    which="major",
    direction="in",
    length=5,
    width=0.8,
    labelsize=10,
    top=True,
    right=True
)


# ================================================================
# 12. TICKS MENORES HACIA ADENTRO
# ================================================================

ax.tick_params(
    axis="both",
    which="minor",
    direction="in",
    length=3,
    width=0.6,
    top=True,
    right=True
)


# ================================================================
# 13. TICKS EN AMBOS LADOS
# ================================================================

ax.xaxis.set_ticks_position("both")
ax.yaxis.set_ticks_position("both")


# ================================================================
# 14. BORDES
# ================================================================

for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_linewidth(0.8)


# ================================================================
# 15. BARRA DE COLOR
# ================================================================

cbar = fig.colorbar(
    contour,
    ax=ax
)

cbar.set_label(
    "Porcentaje de planta [%]",
    fontsize=10
)

cbar.ax.tick_params(
    labelsize=10,
    length=5
)


# ================================================================
# 16. LEYENDA
# ================================================================

if "df_resumen" in globals():

    ax.legend(
        frameon=False,
        fontsize=10,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=1
    )


# ================================================================
# 17. AJUSTE FINAL
# ================================================================

plt.tight_layout()


# ================================================================
# 18. MOSTRAR
# ================================================================

plt.show()

import numpy as np 
import pandas as pd 
import matplotlib.pyplot as plt 
from matplotlib.ticker import AutoMinorLocator 
 
# ========================================================== 
# ARCHIVOS DE RESULTADOS 
# ========================================================== 
RUTA_RESULTADOS = "51 series/resultados_20MW_Todas (1).xlsx"
RUTA_VERIFICACION = "51 series/df_verificacion.xlsx"
 
# ========================================================== 
# LEER RESULTADOS 
# ========================================================== 
df_curvas = pd.read_excel(
    RUTA_RESULTADOS, 
    sheet_name="Curvas_confiabilidad"
)

df_tienda = pd.read_excel(
    RUTA_RESULTADOS, 
    sheet_name="Cuenta_tienda"
)

df_parametros = pd.read_excel(
    RUTA_RESULTADOS, 
    sheet_name="Parametros"
)

# ==========================================================
# LEER DF_VERIFICACION
# ==========================================================
df_verificacion = pd.read_excel(RUTA_VERIFICACION)

# ==========================================================
# VERIFICAR COLUMNAS
# ==========================================================
print("\nColumnas de df_verificacion:")
print(df_verificacion.columns.tolist())

# ========================================================== 
# FIGURA 
# ========================================================== 
fig, ax = plt.subplots(figsize=(5, 3.5)) 
 
# ========================================================== 
# CURVAS DE CONFIABILIDAD 
# ========================================================== 
for serie in df_curvas["Serie"].unique(): 
 
    grupo = df_curvas[
        df_curvas["Serie"] == serie
    ].sort_values(
        "BESS [% energía diaria]"
    )
 
    ax.plot(
        grupo["BESS [% energía diaria]"],
        grupo["Confiabilidad"],
        color="grey",
        alpha=0.35,
        linewidth=1.2,
        zorder=1
    )
 
    # ------------------------------------------------------
    # PUNTO CUENTA DE TIENDA
    # ------------------------------------------------------
    punto = df_tienda[
        df_tienda["Serie"] == serie
    ]
 
    if not punto.empty:
        ax.scatter(
            punto["Cuenta tienda [% energía]"].iloc[0],
            punto["Confiabilidad cuenta tienda"].iloc[0],
            color="black",
            edgecolor="black",
            s=15,
            zorder=2
        )

# ==========================================================
# PUNTOS CORREGIDOS DEL MODELO
# ==========================================================

for serie in df_verificacion["Serie"].unique():

    punto_corr = df_verificacion[
        df_verificacion["Serie"] == serie
    ]

    if not punto_corr.empty:

        ax.scatter(
            punto_corr["Cap_corregida_%"].iloc[0],
            punto_corr["Confiabilidad_corregida_%"].iloc[0] / 100,
            color="red",
            edgecolor="black",
            s=20,
            zorder=3
        )

# ========================================================== 
# ETIQUETAS 
# ========================================================== 
ax.set_xlabel(
    "Capacidad BESS [% de la energía diaria]",
    fontsize=10
)

ax.set_ylabel(
    "Confiabilidad",
    fontsize=10
)
 
# ========================================================== 
# LÍMITES 
# ========================================================== 
ax.set_xlim(15, 55)
 
# ========================================================== 
# TICKS 
# ========================================================== 
ax.xaxis.set_minor_locator(AutoMinorLocator(2))
ax.yaxis.set_minor_locator(AutoMinorLocator(2))

ax.xaxis.set_ticks_position("both")
ax.yaxis.set_ticks_position("both")
 
# ========================================================== 
# GRID 
# ========================================================== 
ax.grid(
    color="grey",
    alpha=0.8
)
 
# ========================================================== 
# FORMATO DE TICKS 
# ========================================================== 
ax.tick_params(
    direction="in",
    axis="both",
    which="major",
    labelsize=10,
    width=1.0,
    length=7
)
 
ax.tick_params(
    direction="in",
    axis="both",
    which="minor",
    width=1.0,
    length=3.5
)
 
# ========================================================== 
# MOSTRAR 
# ========================================================== 
plt.tight_layout()
plt.show()