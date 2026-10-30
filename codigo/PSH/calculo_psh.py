import pandas as pd
import matplotlib.pyplot as plt

ARCHIVO = "PSH/df_series_todas_las_subestaciones con GHI.xlsx"

"""## 1. Carga y preparación de datos"""

df = pd.read_excel(ARCHIVO)
df["date"] = pd.to_datetime(df["fecha"])
df = df.set_index("fecha").sort_index()

# Detectar columnas de GHI y renombrarlas al nombre del sitio
cols_ghi = [c for c in df.columns if "GHI" in c]
sitios = {c: c.replace("GHI ", "").replace(" [W/m2]", "") for c in cols_ghi}
ghi = df[cols_ghi].rename(columns=sitios)

# Verificación de resolución horaria
paso = ghi.index.to_series().diff().mode()[0]
assert paso == pd.Timedelta(hours=1), f"Resolución inesperada: {paso}"

print(f"Registros: {len(ghi):,}  |  Período: {ghi.index.min()} → {ghi.index.max()}")
ghi.describe().round(1)

"""## 2. PSH diarias

Solo se aceptan días con las 24 horas presentes. La serie omite los 29 de febrero, y sin este filtro esos huecos aparecerían como días con PSH = 0, distorsionando mínimos y percentiles.
"""

suma_dia = ghi.resample("D").sum()
horas_dia = ghi.resample("D").count()
psh_diaria = (suma_dia / 1000.0).where(horas_dia.eq(24))  # [h/día]
psh_diaria = psh_diaria.dropna(how="all")

print(f"Días válidos: {len(psh_diaria):,}")
psh_diaria.head()

"""## 3. Resumen por sitio"""

resumen = pd.DataFrame({
    "PSH promedio [h/día]": psh_diaria.mean(),
    "PSH mediana [h/día]": psh_diaria.median(),
    "PSH P90 diario [h/día]": psh_diaria.quantile(0.10),  # excedido el 90% de los días
    "PSH mín. día [h/día]": psh_diaria.min(),
    "PSH máx. día [h/día]": psh_diaria.max(),
    "GHI anual promedio [kWh/m²/año]": psh_diaria.resample("YE").sum().mean(),
})
resumen.round(2)

"""## 4. Climatología mensual

Promedio de la PSH diaria por mes calendario sobre los 27 años. Es el insumo típico para dimensionamiento.
"""

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

psh_mensual = psh_diaria.groupby(psh_diaria.index.month).mean()
psh_mensual.index = MESES
psh_mensual.round(2)

fig, ax = plt.subplots(figsize=(9, 4.5))
for sitio in psh_mensual.columns:
    ax.plot(psh_mensual.index, psh_mensual[sitio], marker="o", label=sitio)
ax.set_ylabel("PSH promedio [h/día]")
ax.set_title("Climatología mensual de PSH (1998–2024)")
ax.legend()
ax.grid(alpha=0.3)
plt.tight_layout()
plt.show()

"""## 5. Promedio anual por año

Útil para ver variabilidad interanual (p. ej. efecto ENSO).
"""

psh_anual = psh_diaria.resample("YE").mean()
psh_anual.index = psh_anual.index.year
psh_anual.index.name = "Año"

fig, ax = plt.subplots(figsize=(9, 4.5))
psh_anual.plot(ax=ax, marker="o")
ax.set_ylabel("PSH promedio [h/día]")
ax.set_title("PSH promedio anual por sitio")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.show()

psh_anual.round(2).tail(10)

"""## 6. Exportar resultados a Excel"""

with pd.ExcelWriter("PSH/PSH_resultados.xlsx", engine="openpyxl") as writer:
    resumen.round(2).to_excel(writer, sheet_name="Resumen")
    psh_mensual.round(2).to_excel(writer, sheet_name="Climatología mensual")
    psh_anual.round(2).to_excel(writer, sheet_name="Promedio anual")
    psh_diaria.round(3).to_excel(writer, sheet_name="PSH diarias")

print("Archivo generado: PSH_resultados.xlsx")