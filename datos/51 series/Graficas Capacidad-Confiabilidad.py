import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator

# ==========================================================
# ARCHIVO DE RESULTADOS
# ==========================================================
RUTA_RESULTADOS = "51 series/resultados_20MW_Todas (1).xlsx"

# ==========================================================
# LEER RESULTADOS
# ==========================================================
df_curvas = pd.read_excel(RUTA_RESULTADOS, sheet_name="Curvas_confiabilidad")
df_tienda = pd.read_excel(RUTA_RESULTADOS, sheet_name="Cuenta_tienda")
df_parametros = pd.read_excel(RUTA_RESULTADOS, sheet_name="Parametros")

# ==========================================================
# FIGURA
# ==========================================================
fig, ax = plt.subplots(figsize=(5, 3.5))

# ==========================================================
# CURVAS DE CONFIABILIDAD
# ==========================================================
for serie in df_curvas["Serie"].unique():

    grupo = df_curvas[df_curvas["Serie"] == serie].sort_values(
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

    punto = df_tienda[df_tienda["Serie"] == serie]

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
# ETIQUETAS
# ==========================================================
ax.set_xlabel("Capacidad BESS [% de la energía diaria]", fontsize=10)
ax.set_ylabel("Confiabilidad", fontsize=10)

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
ax.grid(color="grey", alpha=0.8)

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
