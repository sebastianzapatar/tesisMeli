import pandas as pd

# ==========================================================
# LEER ARCHIVO DE CURVAS
# ==========================================================

df_curvas = pd.read_excel(
    "51 series/resultados_20MW_Todas (1).xlsx", sheet_name="Curvas_confiabilidad"
)

# ==========================================================
# 2. LEER ARCHIVO CON B Y M PROMEDIO
# ==========================================================

df_BM = pd.read_excel(
    "51 series/promedio_BM_por_serie.xlsx"
)

# ==========================================================
# 7. HACER EL MERGE
# ==========================================================

df_curvas = pd.merge(
    df_curvas,
    df_BM,
    on="Serie"
)


# ==========================================================
# 9. GUARDAR RESULTADO
# ==========================================================

df_curvas.to_excel(
    "51 series/curvas_con_BM2.xlsx",
    index=False
)