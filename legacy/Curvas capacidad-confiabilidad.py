import numpy as np
import pandas as pd

# ==========================================================
# CONFIGURACIÓN
# ==========================================================
demandaplana = 20
mw_proyecto = 100
eficiencia = 0.17
DURACION_BESS = 4
PORCENTAJE_MIN = 0.05
PORCENTAJE_MAX = 0.30
PASO_PORCENTAJE = 0.01

# ==========================================================
# ARCHIVOS
# ==========================================================
RUTA_SERIES = "df_series_todas_las_subestaciones.xlsx"
RUTA_PSH = "PSH_resultados.xlsx"
RUTA_SALIDA_EXCEL = "resultados_20MW_Todas.xlsx"

# ==========================================================
# DATOS DE LOS MÓDULOS FV
# ==========================================================
potencia_modulo_w = 550
potencia_modulo_mw = potencia_modulo_w / 1_000_000
num_modulos = mw_proyecto / potencia_modulo_mw
area_modulo = 2.279 * 1.134
area = num_modulos * area_modulo

# ==========================================================
# LEER DATOS
# ==========================================================
df_series = pd.read_excel(RUTA_SERIES, index_col=0)
df_series.index = pd.to_datetime(df_series.index)
df_series = df_series.sort_index()

df_psh = pd.read_excel(RUTA_PSH, index_col=0)
df_psh.index = df_psh.index.astype(str)

# ==========================================================
# GENERACIÓN Y BALANCE
# ==========================================================
df_generacion = pd.DataFrame(index=df_series.index)
df_balance = pd.DataFrame(index=df_series.index)

for serie in df_series.columns:
    generacion = df_series[serie] * area / 1_000_000 * eficiencia
    balance = generacion - demandaplana
    df_generacion[serie] = generacion
    df_balance[serie] = balance

# ==========================================================
# SIMULACIÓN DEL BESS
# ==========================================================
def simular_soc(balance, capacidad, soc_inicial_frac=0.0, eff_carga=1.0, eff_descarga=1.0):
    n = len(balance)
    soc = np.zeros(n)
    ens = np.zeros(n)
    soc_actual = capacidad * soc_inicial_frac

    for i, valor in enumerate(balance):
        if valor >= 0:
            energia_cargable = valor * eff_carga
            soc_actual = min(capacidad, soc_actual + energia_cargable)
        else:
            deficit = -valor
            energia_disponible = soc_actual * eff_descarga
            energia_entregada = min(deficit, energia_disponible)
            soc_actual -= energia_entregada / eff_descarga
            ens[i] = deficit - energia_entregada
        soc[i] = soc_actual

    return soc, ens

# ==========================================================
# CONFIABILIDAD
# ==========================================================
def calcular_confiabilidad(balance, capacidad):
    soc, ens = simular_soc(balance, capacidad)
    deficit = balance[balance < 0]
    energia_deficit = -deficit.sum()
    ENS = ens.sum()

    if energia_deficit <= 0:
        LPSP = 0.0
    else:
        LPSP = ENS / energia_deficit

    confiabilidad = np.clip(1 - LPSP, 0, 1)
    return confiabilidad, LPSP, ENS

# ==========================================================
# PROCESAMIENTO
# ==========================================================
resultados = []
resultados_tienda = []

for serie in df_series.columns:

    try:
        PSH = float(df_psh.loc[str(serie), "PSH promedio [h/día]"])
    except Exception:
        continue

    energia_planta = mw_proyecto * PSH

    porcentajes = np.arange(
        PORCENTAJE_MIN,
        PORCENTAJE_MAX + PASO_PORCENTAJE / 2,
        PASO_PORCENTAJE
    )

    capacidades = energia_planta * porcentajes
    potencias = capacidades / DURACION_BESS
    balance = df_balance[serie].to_numpy()

    # ==========================================================
    # CUENTA DE TIENDA
    # ==========================================================
    df_h = pd.DataFrame({
        "Fecha": df_series.index,
        "Generacion": df_generacion[serie],
        "Balance": df_balance[serie]
    })

    df_h["Hora"] = df_h["Fecha"].dt.hour

    promedio_horario = (
        df_h.groupby("Hora", as_index=False)
        .mean(numeric_only=True)
    )

    Solar_capacity_AC = promedio_horario["Generacion"].max()
    Potencia_BESS_tienda = max(Solar_capacity_AC - demandaplana, 0)
    Energia_BESS_tienda = Potencia_BESS_tienda * PSH

    # ==========================================================
    # CONFIABILIDAD CUENTA DE TIENDA
    # ==========================================================
    confiabilidad_tienda, LPSP_tienda, ENS_tienda = calcular_confiabilidad(
        balance,
        Energia_BESS_tienda
    )

    porcentaje_tienda = Energia_BESS_tienda / energia_planta

    resultados_tienda.append({
        "Serie": serie,
        "PSH [h/día]": PSH,
        "Energía planta [MWh/día]": energia_planta,
        "Potencia AC máxima promedio [MW]": Solar_capacity_AC,
        "Potencia BESS cuenta tienda [MW]": Potencia_BESS_tienda,
        "Energía BESS cuenta tienda [MWh]": Energia_BESS_tienda,
        "Cuenta tienda [% energía]": porcentaje_tienda * 100,
        "Confiabilidad cuenta tienda": confiabilidad_tienda,
        "Confiabilidad cuenta tienda [%]": confiabilidad_tienda * 100,
        "LPSP cuenta tienda": LPSP_tienda,
        "ENS cuenta tienda [MWh]": ENS_tienda
    })

    # ==========================================================
    # SIMULACIÓN DE CADA CAPACIDAD
    # ==========================================================
    for porcentaje, capacidad, potencia in zip(porcentajes, capacidades, potencias):

        confiabilidad, LPSP, ENS = calcular_confiabilidad(
            balance,
            capacidad
        )

        resultados.append({
            "Serie": serie,
            "PSH [h/día]": PSH,
            "Energía planta [MWh/día]": energia_planta,
            "BESS [% energía diaria]": porcentaje * 100,
            "Capacidad BESS [MWh]": capacidad,
            "Potencia BESS [MW]": potencia,
            "Duración BESS [h]": DURACION_BESS,
            "Confiabilidad": confiabilidad,
            "Confiabilidad [%]": confiabilidad * 100,
            "LPSP": LPSP,
            "ENS [MWh]": ENS,
            "Potencia AC máxima promedio [MW]": Solar_capacity_AC,
            "Potencia BESS cuenta tienda [MW]": Potencia_BESS_tienda,
            "Energía BESS cuenta tienda [MWh]": Energia_BESS_tienda,
            "Cuenta tienda [% energía]": porcentaje_tienda * 100,
            "Confiabilidad cuenta tienda": confiabilidad_tienda,
            "Confiabilidad cuenta tienda [%]": confiabilidad_tienda * 100,
            "LPSP cuenta tienda": LPSP_tienda,
            "ENS cuenta tienda [MWh]": ENS_tienda
        })

# ==========================================================
# DATAFRAMES FINALES
# ==========================================================
df_curvas = pd.DataFrame(resultados)
df_curvas = df_curvas.sort_values(
    ["Serie", "Capacidad BESS [MWh]"]
).reset_index(drop=True)

df_tienda = pd.DataFrame(resultados_tienda)

# ==========================================================
# DATAFRAMES HORARIOS
# ==========================================================
df_generacion_export = df_generacion.copy()
df_generacion_export.insert(0, "Fecha", df_generacion_export.index)

df_balance_export = df_balance.copy()
df_balance_export.insert(0, "Fecha", df_balance_export.index)

# ==========================================================
# TABLA DE PARÁMETROS
# ==========================================================
df_parametros = pd.DataFrame({
    "Parámetro": [
        "Demanda [MW]",
        "Potencia planta [MW]",
        "Eficiencia FV",
        "Duración BESS [h]",
        "Potencia módulo [W]",
        "Número de módulos",
        "Área módulo [m²]",
        "Área total [m²]",
        "Porcentaje mínimo",
        "Porcentaje máximo",
        "Paso porcentaje"
    ],
    "Valor": [
        demandaplana,
        mw_proyecto,
        eficiencia,
        DURACION_BESS,
        potencia_modulo_w,
        num_modulos,
        area_modulo,
        area,
        PORCENTAJE_MIN * 100,
        PORCENTAJE_MAX * 100,
        PASO_PORCENTAJE * 100
    ]
})

# ==========================================================
# EXPORTAR RESULTADOS
# ==========================================================
with pd.ExcelWriter(RUTA_SALIDA_EXCEL, engine="openpyxl") as writer:
    df_curvas.to_excel(writer, sheet_name="Curvas_confiabilidad", index=False)
    df_tienda.to_excel(writer, sheet_name="Cuenta_tienda", index=False)
    df_generacion_export.to_excel(writer, sheet_name="Generacion_horaria", index=False)
    df_balance_export.to_excel(writer, sheet_name="Balance_horario", index=False)
    df_parametros.to_excel(writer, sheet_name="Parametros", index=False)

# ==========================================================
# PROCESO TERMINADO
# ==========================================================
print(f"Proceso terminado. Archivo generado: {RUTA_SALIDA_EXCEL}")