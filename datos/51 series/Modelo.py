import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import (
    RBF,
    ConstantKernel,
    WhiteKernel
)

from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score
)

from scipy.optimize import curve_fit

# ==========================================================
# CONFIGURACIÓN
# ==========================================================
demandaplana = 20  # MW
# Factor de conversión de irradiancia a generación
factor_generacion = (469888 / 1000000) * 0.17

# ==========================================================
# LEER EXCEL
# ==========================================================
df = pd.read_excel("51 series/df_series_todas_las_subestaciones.xlsx")

# ==========================================================
# CALCULAR BALANCE
# ==========================================================
df_balance = df.copy()
for serie_nombre in df.columns:
    if serie_nombre == "fecha":
        continue
    # ------------------------------------------------------
    # Generación
    # ------------------------------------------------------
    generacion = (
        df[serie_nombre]
        * factor_generacion
    )
    # ------------------------------------------------------
    # Balance = generación - demanda
    # ------------------------------------------------------
    balance = (
        generacion
        - demandaplana
    )
    # ------------------------------------------------------
    # Reemplazar la serie original por el balance
    # ------------------------------------------------------
    df_balance[serie_nombre] = balance

# ==========================================================
# 4. ORDENAR
# ==========================================================
df_balance = df_balance.sort_values(
    "fecha"
)
df_balance = df_balance.set_index(
    "fecha"
)

print(df_balance)

# ================================================================
# MODELO DE CORRECCIÓN Phi(B,M)

# La capacidad corregida se expresa como:
#
#       C_corr = C_tienda * Phi(B,M)
# donde Phi(B,M) es aprendido a partir del comportamiento de
# confiabilidad de cada serie.

# ================================================================
# 0. CONFIGURACIÓN
# ================================================================

# ------------------------------------------------
# LÍMITES FÍSICOS DE LA CAPACIDAD CORREGIDA
# ------------------------------------------------
#
# Estos límites ya NO representan un objetivo de confiabilidad.
#
# Se utilizan únicamente para evitar predicciones físicamente
# imposibles.
#
# 0.10 = 10% de la energía diaria
# 1.00  = 100% de la energía diaria
#

CAP_MIN = 0.1
CAP_MAX = 1


# ------------------------------------------------
# RANGO TEÓRICO DE B Y M
# ------------------------------------------------

B_MIN_TEORICO = -1.0
B_MAX_TEORICO = 1.0

M_MIN_TEORICO = -1.0
M_MAX_TEORICO = 1.0


# ------------------------------------------------
# PESOS DEL MODELO ORIGINAL
# ------------------------------------------------

W_B = 0.50
W_M = 0.30
W_BM = 0.20


# ------------------------------------------------
# PARÁMETROS SOC
# ------------------------------------------------

UMBRAL_LLENADO = 0.99

EFF_CARGA = 1.0
EFF_DESCARGA = 1.0

SEMILLA = 42


# ------------------------------------------------
# SELECCIÓN DE MODELO
# ------------------------------------------------
#
# Si SELECCION_MANUAL es None, se elige automáticamente el modelo
# con menor RMSE_LOO (comportamiento correcto por defecto).
#
# Si se quiere forzar un modelo específico (por ejemplo para un
# reporte donde se justifica explícitamente su uso), se puede
# escribir su nombre aquí, p. ej. "Logistica_acotada".
#
SELECCION_MANUAL = None


# ================================================================
# ARCHIVOS
# ================================================================

RUTA_CURVAS = "51 series/curvas_con_BM2.xlsx"

# ================================================================
# 1. SIMULACIÓN DE SOC
# ================================================================

def simular_soc(
    balance,
    capacidad,
    soc_inicial_frac=0.0,
    eff_carga=EFF_CARGA,
    eff_descarga=EFF_DESCARGA
):

    balance = np.asarray(balance, dtype=float)
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


# ================================================================
# 2. CONFIABILIDAD
# ================================================================

def calcular_confiabilidad(balance, capacidad):

    balance = np.asarray(balance, dtype=float)
    soc, ens = simular_soc(balance, capacidad)
    deficit = balance[balance < 0]
    energia_deficit = -deficit.sum()
    ENS = ens.sum()

    if energia_deficit <= 0:
        LPSP = 0.0
    else:
        LPSP = ENS / energia_deficit

    confiabilidad = np.clip(1.0 - LPSP, 0.0, 1.0)

    return confiabilidad, LPSP, ENS, soc


# ================================================================
# 3. PROBABILIDAD DE LLENADO
# ================================================================

def calcular_probabilidad_llenado(soc, capacidad, umbral=UMBRAL_LLENADO):

    if capacidad <= 0:
        return 0.0

    return float(np.mean(soc >= umbral * capacidad))


# ================================================================
# 4. CARGA DE DATOS
# ================================================================

df_curvas = pd.read_excel(RUTA_CURVAS)

df_curvas["Serie"] = df_curvas["Serie"].astype(str).str.strip()


# ================================================================
# 5. DATAFRAME DE CUENTA DE TIENDA
# ================================================================

if "df_tienda" not in globals():

    columnas_tienda = [
        "Serie",
        "PSH [h/día]",
        "Energía planta [MWh/día]",
        "Potencia AC máxima promedio [MW]",
        "Potencia BESS cuenta tienda [MW]",
        "Energía BESS cuenta tienda [MWh]",
        "Cuenta tienda [% energía]",
        "B",
        "M"
    ]

    columnas_tienda = [c for c in columnas_tienda if c in df_curvas.columns]

    df_tienda = (
        df_curvas[columnas_tienda]
        .drop_duplicates(subset=["Serie"])
        .reset_index(drop=True)
    )


df_tienda["Serie"] = df_tienda["Serie"].astype(str).str.strip()


# ================================================================
# 6. VALIDACIONES
# ================================================================

columnas_requeridas = ["Serie", "B", "M"]

for columna in columnas_requeridas:
    if columna not in df_curvas.columns:
        raise KeyError(f"No existe la columna '{columna}' en df_curvas.")

if "Cuenta tienda [% energía]" not in df_tienda.columns:
    raise KeyError("No existe la columna 'Cuenta tienda [% energía]'.")

if "Energía planta [MWh/día]" not in df_tienda.columns:
    raise KeyError("No existe la columna 'Energía planta [MWh/día]'.")

if "df_balance" not in globals():
    raise RuntimeError(
        "\nNo se encontró df_balance.\n\n"
        "El modelo necesita df_balance "
        "para evaluar el comportamiento de confiabilidad."
    )


# ================================================================
# 7. CONSTRUIR DATAFRAME BASE
# ================================================================

registros = []

for serie in df_curvas["Serie"].unique():

    grupo = df_curvas[df_curvas["Serie"] == serie]
    fila_tienda = df_tienda[df_tienda["Serie"] == serie]

    if fila_tienda.empty:
        print(f"Advertencia: no existe cuenta de tienda para {serie}")
        continue

    fila_tienda = fila_tienda.iloc[0]

    B = float(grupo["B"].iloc[0])
    M = float(grupo["M"].iloc[0])

    cuenta_pct = float(fila_tienda["Cuenta tienda [% energía]"]) / 100.0
    energia_planta = float(fila_tienda["Energía planta [MWh/día]"])

    registros.append({
        "Serie": serie,
        "B": B,
        "M": M,
        "Cuenta_tienda_%": cuenta_pct,
        "Cuenta_tienda_MWh": cuenta_pct * energia_planta,
        "Energía_planta_MWh_dia": energia_planta
    })

df_resumen = pd.DataFrame(registros)


# ================================================================
# 8. NORMALIZACIÓN DE B Y M
# ================================================================

df_resumen["B_limitado"] = np.clip(df_resumen["B"], B_MIN_TEORICO, B_MAX_TEORICO)
df_resumen["M_limitado"] = np.clip(df_resumen["M"], M_MIN_TEORICO, M_MAX_TEORICO)

df_resumen["B_norm"] = (
    (df_resumen["B_limitado"] - B_MIN_TEORICO)
    / (B_MAX_TEORICO - B_MIN_TEORICO)
)

df_resumen["M_norm"] = (
    (df_resumen["M_limitado"] - M_MIN_TEORICO)
    / (M_MAX_TEORICO - M_MIN_TEORICO)
)


# ================================================================
# 9. CONSTRUIR LA VARIABLE OBJETIVO SIN CONF_OBJETIVO
# ================================================================

capacidades_referencia = []
confiabilidades_referencia = []
confiabilidades_tienda = []
LPSP_tienda = []
ENS_tienda = []

for _, fila in df_resumen.iterrows():

    serie = fila["Serie"]

    if serie not in df_balance.columns:
        capacidades_referencia.append(np.nan)
        confiabilidades_referencia.append(np.nan)
        confiabilidades_tienda.append(np.nan)
        LPSP_tienda.append(np.nan)
        ENS_tienda.append(np.nan)
        continue

    balance = (
        pd.to_numeric(df_balance[serie], errors="coerce")
        .dropna()
        .to_numpy(dtype=float)
    )

    energia_planta = fila["Energía_planta_MWh_dia"]

    # -------------------- CONFIABILIDAD EN CUENTA DE TIENDA --------------------

    cap_tienda = fila["Cuenta_tienda_%"] * energia_planta

    conf_tienda, lpsp_tienda, ens_tienda, _ = calcular_confiabilidad(
        balance, cap_tienda
    )

    confiabilidades_tienda.append(conf_tienda)
    LPSP_tienda.append(lpsp_tienda)
    ENS_tienda.append(ens_tienda)

    # -------------------- CAPACIDADES DISPONIBLES EN df_curvas --------------------

    grupo = df_curvas[df_curvas["Serie"] == serie].copy()

    posibles_columnas = [
        "% energía",
        "BESS [% energía]",
        "Capacidad [% energía]",
        "Capacidad_BESS_%",
        "Cuenta tienda [% energía]",
        "Energía BESS [% energía]"
    ]

    columna_capacidad = None

    for columna in posibles_columnas:
        if columna in grupo.columns:
            columna_capacidad = columna
            break

    if columna_capacidad is None:

        posibles_mwh = [
            "Energía BESS [MWh]",
            "Capacidad BESS [MWh]",
            "Capacidad [MWh]",
            "Energía BESS"
        ]

        for columna in posibles_mwh:
            if columna in grupo.columns:
                columna_capacidad = columna
                break

    if columna_capacidad is None:
        print(f"Advertencia: no se encontró columna de capacidad para {serie}")
        capacidades_referencia.append(np.nan)
        confiabilidades_referencia.append(np.nan)
        continue

    capacidades = pd.to_numeric(grupo[columna_capacidad], errors="coerce").dropna()

    if "%" in columna_capacidad:
        capacidades = capacidades / 100.0
    else:
        if capacidades.max() > 1.5:
            capacidades = capacidades / energia_planta

    capacidades = (
        capacidades
        .clip(CAP_MIN, CAP_MAX)
        .drop_duplicates()
        .sort_values()
    )

    curva = []

    for capacidad_frac in capacidades:

        capacidad_mwh = capacidad_frac * energia_planta

        conf, lpsp, ens, _ = calcular_confiabilidad(balance, capacidad_mwh)

        curva.append({
            "capacidad_frac": capacidad_frac,
            "confiabilidad": conf,
            "LPSP": lpsp,
            "ENS": ens
        })

    df_curva_temp = pd.DataFrame(curva)

    if df_curva_temp.empty:
        capacidades_referencia.append(np.nan)
        confiabilidades_referencia.append(np.nan)
        continue

    conf_max = df_curva_temp["confiabilidad"].max()

    candidatos = df_curva_temp[
        df_curva_temp["confiabilidad"] >= conf_max * 0.99
    ]

    referencia = candidatos.iloc[0]

    capacidades_referencia.append(referencia["capacidad_frac"])
    confiabilidades_referencia.append(referencia["confiabilidad"])


# ================================================================
# 10. GUARDAR VARIABLES DE REFERENCIA
# ================================================================

df_resumen["Capacidad_referencia_%"] = capacidades_referencia
df_resumen["Confiabilidad_referencia"] = confiabilidades_referencia
df_resumen["Confiabilidad_cuenta_tienda"] = confiabilidades_tienda
df_resumen["LPSP_cuenta_tienda"] = LPSP_tienda
df_resumen["ENS_cuenta_tienda_MWh"] = ENS_tienda


# ================================================================
# 11. ELIMINAR DATOS NO VÁLIDOS
# ================================================================

df_resumen = df_resumen[df_resumen["Capacidad_referencia_%"].notna()].copy()
df_resumen = df_resumen[df_resumen["B"].notna()]
df_resumen = df_resumen[df_resumen["M"].notna()]
df_resumen = df_resumen.reset_index(drop=True)

print("\n================================================")
print("VARIABLE OBJETIVO")
print("================================================")
print("No se utiliza CONF_OBJETIVO.")
print(f"Series válidas: {len(df_resumen)}")
print(f"Capacidad referencia mínima: {df_resumen['Capacidad_referencia_%'].min()*100:.2f}%")
print(f"Capacidad referencia máxima: {df_resumen['Capacidad_referencia_%'].max()*100:.2f}%")
print(f"Capacidad referencia promedio: {df_resumen['Capacidad_referencia_%'].mean()*100:.2f}%")


# ================================================================
# 12. MODELOS
# ================================================================

def _clip(y_pred):
    return np.clip(y_pred, CAP_MIN, CAP_MAX)


# ----------------------------------------------------------------
# NUEVO: transformación logit <-> capacidad
# ----------------------------------------------------------------
#
# Se usa para lineal y cuadrático, igual que para el logístico,
# de modo que TODOS los modelos que compiten en el LOO-CV estén
# acotados por construcción dentro de [CAP_MIN, CAP_MAX] y no
# dependan de un clip post-hoc que los satura artificialmente en
# los extremos durante la extrapolación de cada fold.
# ----------------------------------------------------------------

_EPS_LOGIT = 1e-6


def _a_logit(y):

    y = np.asarray(y, dtype=float)

    y_esc = (y - CAP_MIN) / (CAP_MAX - CAP_MIN)

    y_esc = np.clip(y_esc, _EPS_LOGIT, 1.0 - _EPS_LOGIT)

    return np.log(y_esc / (1.0 - y_esc))


def _desde_logit(z):

    z = np.asarray(z, dtype=float)

    return CAP_MIN + (CAP_MAX - CAP_MIN) / (1.0 + np.exp(-z))


# ================================================================
# MODELO 1
# ================================================================

def indice_lineal_fijo(X):

    B_norm = X[:, 0]
    M_norm = X[:, 1]

    indice = (W_B * B_norm) + (W_M * M_norm) + (W_BM * B_norm * M_norm)

    return CAP_MIN + indice * (CAP_MAX - CAP_MIN)


def fit_indice_fijo(X, y):
    return None


def predict_indice_fijo(state, X):
    return _clip(indice_lineal_fijo(X))


# ================================================================
# MODELO 2
# REGRESIÓN LINEAL (ahora en espacio logit -> acotada)
# ================================================================

def fit_lineal(X, y):

    modelo = Pipeline([
        ("scaler", StandardScaler()),
        ("reg", LinearRegression())
    ])

    modelo.fit(X, _a_logit(y))

    return modelo


def predict_lineal(state, X):
    return _clip(_desde_logit(state.predict(X)))


# ================================================================
# MODELO 3
# REGRESIÓN CUADRÁTICA (ahora en espacio logit -> acotada)
# ================================================================

def fit_cuadratico(X, y):

    modelo = Pipeline([
        ("poly", PolynomialFeatures(degree=2, include_bias=False)),
        ("scaler", StandardScaler()),
        ("reg", LinearRegression())
    ])

    modelo.fit(X, _a_logit(y))

    return modelo


def predict_cuadratico(state, X):
    return _clip(_desde_logit(state.predict(X)))


# ================================================================
# MODELO 4
# LOGÍSTICA
# ================================================================

def _funcion_logistica(X, a, b, c, d):

    B_norm = X[:, 0]
    M_norm = X[:, 1]

    z = a + (b * B_norm) + (c * M_norm) + (d * B_norm * M_norm)

    return CAP_MIN + (CAP_MAX - CAP_MIN) / (1.0 + np.exp(-z))


def fit_logistico(X, y):

    try:
        params, _ = curve_fit(
            _funcion_logistica,
            X,
            y,
            p0=[0.0, 1.0, 1.0, 0.0],
            maxfev=30000
        )

    except (RuntimeError, ValueError):
        params = np.array([0.0, 1.0, 1.0, 0.0])

    return params


def predict_logistico(state, X):
    return _clip(_funcion_logistica(X, *state))


# ================================================================
# MODELOS CANDIDATOS
# ================================================================

MODELOS = {
    "Indice_lineal_fijo": (fit_indice_fijo, predict_indice_fijo),
    "Regresion_lineal": (fit_lineal, predict_lineal),
    "Regresion_cuadratica": (fit_cuadratico, predict_cuadratico),
    "Logistica_acotada": (fit_logistico, predict_logistico)
}


# ================================================================
# 13. DATOS PARA MODELAR
# ================================================================

df_calibracion = (
    df_resumen
    .dropna(subset=["Capacidad_referencia_%"])
    .reset_index(drop=True)
)

X_todo = df_calibracion[["B_norm", "M_norm"]].to_numpy(dtype=float)
y_todo = df_calibracion["Capacidad_referencia_%"].to_numpy(dtype=float)

n_cal = len(df_calibracion)


# ================================================================
# 14. LOO-CV
# ================================================================

predicciones_loo = {nombre: np.zeros(n_cal) for nombre in MODELOS}

print("\n================================================")
print("EJECUTANDO LOO-CV")
print("================================================")

for nombre, (fit_fn, predict_fn) in MODELOS.items():

    for i in range(n_cal):

        mascara = np.ones(n_cal, dtype=bool)
        mascara[i] = False

        X_train = X_todo[mascara]
        y_train = y_todo[mascara]
        X_test = X_todo[i:i + 1]

        estado = fit_fn(X_train, y_train)

        predicciones_loo[nombre][i] = predict_fn(estado, X_test)[0]

    print(f"  - {nombre}: listo")


# ================================================================
# 15. MÉTRICAS Y SELECCIÓN DEL MEJOR MODELO
# ================================================================

filas_metricas = []

for nombre in MODELOS:

    y_pred = predicciones_loo[nombre]

    rmse = np.sqrt(mean_squared_error(y_todo, y_pred))
    mae = mean_absolute_error(y_todo, y_pred)
    r2 = r2_score(y_todo, y_pred)

    filas_metricas.append({
        "Modelo": nombre,
        "RMSE_LOO": rmse,
        "MAE_LOO": mae,
        "R2_LOO": r2
    })

df_comparacion_modelos = (
    pd.DataFrame(filas_metricas)
    .sort_values("RMSE_LOO")
    .reset_index(drop=True)
)

print("\n================================================")
print("COMPARACIÓN DE MODELOS")
print("================================================")
print(df_comparacion_modelos.round(5).to_string(index=False))

# ----------------------------------------------------------------
# CORREGIDO: ya no se sobrescribe el resultado a mano.
# Se usa el mejor modelo según LOO-CV (menor RMSE), salvo que se
# fije explícitamente SELECCION_MANUAL arriba en la configuración.
# ----------------------------------------------------------------

mejor_modelo_nombre = df_comparacion_modelos.iloc[0]["Modelo"]

if SELECCION_MANUAL is not None:

    if SELECCION_MANUAL not in MODELOS:
        raise ValueError(
            f"SELECCION_MANUAL='{SELECCION_MANUAL}' no es un modelo válido. "
            f"Opciones: {list(MODELOS.keys())}"
        )

    print(
        f"\n>>> Selección automática hubiera sido: {mejor_modelo_nombre} "
        f"(RMSE_LOO más bajo)"
    )

    mejor_modelo_nombre = SELECCION_MANUAL

    print(f">>> Se fuerza modelo manual: {mejor_modelo_nombre}")

else:

    print(f"\n>>> Mejor modelo (automático, por RMSE_LOO): {mejor_modelo_nombre}")

fila_modelo_elegido = df_comparacion_modelos[
    df_comparacion_modelos["Modelo"] == mejor_modelo_nombre
]

print("\nMétricas LOO-CV del modelo seleccionado:")
print(fila_modelo_elegido.round(5).to_string(index=False))


# ================================================================
# 16. REAJUSTE DEL MEJOR MODELO
# ================================================================

fit_mejor, predict_mejor = MODELOS[mejor_modelo_nombre]

estado_mejor = fit_mejor(X_todo, y_todo)


# ================================================================
# 17. PREDICCIÓN FINAL
# ================================================================

X_completo = df_resumen[["B_norm", "M_norm"]].to_numpy(dtype=float)

df_resumen["Capacidad_corregida_%"] = predict_mejor(estado_mejor, X_completo)
df_resumen["Modelo_seleccionado"] = mejor_modelo_nombre


# ================================================================
# 18. PHI(B,M)
# ================================================================

df_resumen["Phi_BM"] = (
    df_resumen["Capacidad_corregida_%"] / df_resumen["Cuenta_tienda_%"]
)


# ================================================================
# 19. CAPACIDAD CORREGIDA MWh
# ================================================================

df_resumen["Capacidad_corregida_MWh"] = (
    df_resumen["Capacidad_corregida_%"] * df_resumen["Energía_planta_MWh_dia"]
)


# ================================================================
# 20. DIFERENCIA RESPECTO A CUENTA DE TIENDA
# ================================================================

df_resumen["Diferencia_capacidad_%"] = (
    (df_resumen["Capacidad_corregida_%"] / df_resumen["Cuenta_tienda_%"]) - 1
) * 100


# ================================================================
# 21. MOSTRAR RESULTADOS
# ================================================================

print("\n================================================")
print("CORRECCIÓN FINAL")
print("================================================")

resultado_mostrar = df_resumen[[
    "Serie", "B", "M", "Cuenta_tienda_%", "Capacidad_referencia_%",
    "Capacidad_corregida_%", "Phi_BM", "Diferencia_capacidad_%"
]].copy()

resultado_mostrar["Cuenta_tienda_%"] *= 100
resultado_mostrar["Capacidad_referencia_%"] *= 100
resultado_mostrar["Capacidad_corregida_%"] *= 100

print(resultado_mostrar.round(4).to_string(index=False))


# ================================================================
# 22. VERIFICACIÓN ANTES VS DESPUÉS
# ================================================================

resultados = []

for _, fila in df_resumen.iterrows():

    serie = fila["Serie"]

    if serie not in df_balance.columns:
        continue

    balance = (
        pd.to_numeric(df_balance[serie], errors="coerce")
        .dropna()
        .to_numpy(dtype=float)
    )

    energia_planta = fila["Energía_planta_MWh_dia"]

    cap_original_mwh = fila["Cuenta_tienda_%"] * energia_planta

    conf_original, lpsp_original, ens_original, soc_original = (
        calcular_confiabilidad(balance, cap_original_mwh)
    )

    prob_llenado_original = calcular_probabilidad_llenado(
        soc_original, cap_original_mwh
    )

    cap_corregida_pct = fila["Capacidad_corregida_%"]
    cap_corregida_mwh = cap_corregida_pct * energia_planta

    conf_corregida, lpsp_corregida, ens_corregida, soc_corregida = (
        calcular_confiabilidad(balance, cap_corregida_mwh)
    )

    prob_llenado_corregida = calcular_probabilidad_llenado(
        soc_corregida, cap_corregida_mwh
    )

    resultados.append({
        "Serie": serie,
        "B": fila["B"],
        "M": fila["M"],
        "Modelo_seleccionado": mejor_modelo_nombre,
        "Phi_BM": fila["Phi_BM"],

        "Cap_original_%": fila["Cuenta_tienda_%"] * 100,
        "Cap_original_MWh": cap_original_mwh,
        "Confiabilidad_original_%": conf_original * 100,
        "LPSP_original": lpsp_original,
        "ENS_original_MWh": ens_original,
        "Prob_llenado_original": prob_llenado_original,

        "Cap_corregida_%": cap_corregida_pct * 100,
        "Cap_corregida_MWh": cap_corregida_mwh,
        "Confiabilidad_corregida_%": conf_corregida * 100,
        "LPSP_corregida": lpsp_corregida,
        "ENS_corregida_MWh": ens_corregida,
        "Prob_llenado_corregida": prob_llenado_corregida,

        "Diferencia_capacidad_%": (cap_corregida_mwh / cap_original_mwh - 1) * 100,
        "Delta_confiabilidad_puntos_%": (conf_corregida - conf_original) * 100,
        "Delta_LPSP": lpsp_corregida - lpsp_original,
        "Delta_ENS_MWh": ens_corregida - ens_original,
        "Delta_prob_llenado_puntos_%": (
            (prob_llenado_corregida - prob_llenado_original) * 100
        )
    })

df_verificacion = pd.DataFrame(resultados)


# ================================================================
# 23. RESULTADOS ANTES VS DESPUÉS
# ================================================================

print("\n================================================")
print("ANTES VS DESPUÉS")
print("================================================")

print(
    df_verificacion[[
        "Serie", "B", "M", "Phi_BM", "Cap_original_%", "Cap_corregida_%",
        "Diferencia_capacidad_%", "Confiabilidad_original_%",
        "Confiabilidad_corregida_%", "Delta_confiabilidad_puntos_%"
    ]]
    .round(4)
    .to_string(index=False)
)

# ================================================================
# 24. RESUMEN
# ================================================================

n = len(df_verificacion)

if n > 0:

    mejora_conf = (
        df_verificacion[
            "Delta_confiabilidad_puntos_%"
        ] > 0
    ).sum()

    reduccion_lpsp = (
        df_verificacion[
            "Delta_LPSP"
        ] < 0
    ).sum()

    reduccion_ens = (
        df_verificacion[
            "Delta_ENS_MWh"
        ] < 0
    ).sum()


    # ============================================================
    # DIFERENCIA DE CAPACIDAD
    # ============================================================

    diferencia_capacidad = (
        df_verificacion[
            "Diferencia_capacidad_%"
        ]
    )


    # ------------------------------------------------------------
    # SERIES QUE AUMENTARON LA CAPACIDAD
    # ------------------------------------------------------------

    df_aumentaron = (
        df_verificacion[
            diferencia_capacidad > 0
        ]
        .copy()
    )


    # ------------------------------------------------------------
    # SERIES QUE DISMINUYERON LA CAPACIDAD
    # ------------------------------------------------------------

    df_disminuyeron = (
        df_verificacion[
            diferencia_capacidad < 0
        ]
        .copy()
    )


    # ============================================================
    # RESUMEN GENERAL
    # ============================================================

    print("\n================================================")
    print("RESUMEN FINAL")
    print("================================================")

    print(
        f"Modelo seleccionado: "
        f"{mejor_modelo_nombre}"
    )

    print(
        f"Series evaluadas: {n}"
    )

    print(
        f"Series con mejora de confiabilidad: "
        f"{mejora_conf}/{n}"
    )

    print(
        f"Series con reducción de LPSP: "
        f"{reduccion_lpsp}/{n}"
    )

    print(
        f"Series con reducción de ENS: "
        f"{reduccion_ens}/{n}"
    )


    # ============================================================
    # RESUMEN DE DIFERENCIA DE CAPACIDAD
    # ============================================================

    print("\n------------------------------------------------")
    print("DIFERENCIA DE CAPACIDAD")
    print("------------------------------------------------")

    print(
        f"Promedio general: "
        f"{diferencia_capacidad.mean():+.2f}%"
    )

    print(
        f"Mínimo general: "
        f"{diferencia_capacidad.min():+.2f}%"
    )

    print(
        f"Máximo general: "
        f"{diferencia_capacidad.max():+.2f}%"
    )


    # ============================================================
    # SERIES CON AUMENTO DE CAPACIDAD
    # ============================================================

    print("\n------------------------------------------------")
    print("SERIES CON AUMENTO DE CAPACIDAD")
    print("------------------------------------------------")

    print(
        f"Número de series: "
        f"{len(df_aumentaron)}"
    )


    if len(df_aumentaron) > 0:

        print(
            f"Mínimo: "
            f"{df_aumentaron['Diferencia_capacidad_%'].min():+.2f}%"
        )

        print(
            f"Media: "
            f"{df_aumentaron['Diferencia_capacidad_%'].mean():+.2f}%"
        )

        print(
            f"Máximo: "
            f"{df_aumentaron['Diferencia_capacidad_%'].max():+.2f}%"
        )


    # ============================================================
    # SERIES CON DISMINUCIÓN DE CAPACIDAD
    # ============================================================

    print("\n------------------------------------------------")
    print("SERIES CON DISMINUCIÓN DE CAPACIDAD")
    print("------------------------------------------------")

    print(
        f"Número de series: "
        f"{len(df_disminuyeron)}"
    )


    if len(df_disminuyeron) > 0:

        print(
            f"Mínimo: "
            f"{df_disminuyeron['Diferencia_capacidad_%'].min():+.2f}%"
        )

        print(
            f"Media: "
            f"{df_disminuyeron['Diferencia_capacidad_%'].mean():+.2f}%"
        )

        print(
            f"Máximo: "
            f"{df_disminuyeron['Diferencia_capacidad_%'].max():+.2f}%"
        )


    # ============================================================
    # CAMBIOS PROMEDIO DE CONFIABILIDAD
    # ============================================================

    print("\n================================================")
    print("EFECTO PROMEDIO DEL MODELO")
    print("================================================")

    print(
        f"Diferencia promedio de capacidad: "
        f"{diferencia_capacidad.mean():+.2f}%"
    )

    print(
        f"Cambio promedio de confiabilidad: "
        f"{df_verificacion['Delta_confiabilidad_puntos_%'].mean():+.3f} pp"
    )

    print(
        f"Cambio promedio de LPSP: "
        f"{df_verificacion['Delta_LPSP'].mean():+.5f}"
    )

    print(
        f"Cambio promedio de ENS: "
        f"{df_verificacion['Delta_ENS_MWh'].mean():+.3f} MWh"
    )

    # ================================================================
# EXTRAER COEFICIENTES a, b, c, d DEL MODELO LOGÍSTICO
# ================================================================

if mejor_modelo_nombre == "Logistica_acotada":
    a, b, c, d = estado_mejor
    print("Modelo ganador es la logística. Coeficientes:")
else:
    # El ganador fue otro modelo — ajustamos la logística aparte
    # solo para poder ver sus parámetros (no reemplaza al ganador)
    a, b, c, d = fit_logistico(X_todo, y_todo)
    print(f"Modelo ganador fue '{mejor_modelo_nombre}'.")
    print("Coeficientes de la logística ajustada por separado (referencia):")

print(f"a (intercepto)      = {a:.4f}")
print(f"b (peso de B_norm)  = {b:.4f}")
print(f"c (peso de M_norm)  = {c:.4f}")
print(f"d (interacción B·M) = {d:.4f}")
print()

# ================================================================
# GUARDAR df_verificacion EN EXCEL
# ================================================================

RUTA_SALIDA = "51 series/df_verificacion.xlsx"

df_verificacion.to_excel(
    RUTA_SALIDA,
    index=False
)

print(f"\nArchivo guardado correctamente en:")
print(RUTA_SALIDA)

# ==========================================================
# CONSTRUIR df_5_series
# MERGE CUENTA DE TIENDA + B Y M PROMEDIO
# ==========================================================

# ==========================================================
# 1. RUTAS
# ==========================================================

RUTA_TIENDA = "5 series/resultados_cuenta_tienda (2).xlsx"
RUTA_BM = "5 series/promedio_BM_por_serie (1).xlsx"

# ==========================================================
# 2. PARÁMETROS DEL PROYECTO
# ==========================================================

MW_PROYECTO = 100.0

# Límites teóricos de B y M
B_MIN_TEORICO = -1.0
B_MAX_TEORICO = 1.0

M_MIN_TEORICO = -1.0
M_MAX_TEORICO = 1.0

# ==========================================================
# 3. LEER ARCHIVOS
# ==========================================================

df_tienda = pd.read_excel(RUTA_TIENDA)
df_BM = pd.read_excel(RUTA_BM)

# ==========================================================
# 4. LIMPIAR NOMBRES DE SERIE
# ==========================================================

df_tienda["Serie"] = df_tienda["Serie"].astype(str).str.strip()
df_BM["Serie"] = df_BM["Serie"].astype(str).str.strip()

# ==========================================================
# 5. VERIFICAR COLUMNAS NECESARIAS
# ==========================================================

columnas_tienda_necesarias = [
    "Serie",
    "PSH [h/día]",
    "Cuenta de tienda [MWh]"
]

columnas_BM_necesarias = [
    "Serie",
    "B",
    "M"
]

for columna in columnas_tienda_necesarias:
    if columna not in df_tienda.columns:
        raise KeyError(
            f"No existe la columna '{columna}' en {RUTA_TIENDA}"
        )

for columna in columnas_BM_necesarias:
    if columna not in df_BM.columns:
        raise KeyError(
            f"No existe la columna '{columna}' en {RUTA_BM}"
        )

# ==========================================================
# 6. SELECCIONAR COLUMNAS NECESARIAS
# ==========================================================

df_tienda_merge = df_tienda[columnas_tienda_necesarias].copy()
df_BM_merge = df_BM[columnas_BM_necesarias].copy()

# ==========================================================
# 7. MERGE POR SERIE
# ==========================================================

df_5_series = pd.merge(
    df_tienda_merge,
    df_BM_merge,
    on="Serie",
    how="inner"
)

# ==========================================================
# 8. CALCULAR ENERGÍA DIARIA DE LA PLANTA
# ==========================================================
# E_planta = Potencia planta × PSH

df_5_series["Energía_planta_MWh_dia"] = (
    MW_PROYECTO * df_5_series["PSH [h/día]"]
)

# ==========================================================
# 9. CALCULAR CUENTA DE TIENDA EN %
# ==========================================================
# Cuenta tienda / Energía planta × 100

df_5_series["Cuenta_tienda_%"] = (
    df_5_series["Cuenta de tienda [MWh]"]
    / df_5_series["Energía_planta_MWh_dia"]
    * 100
)

# ==========================================================
# 10. CONVERTIR A FRACCIÓN
# ==========================================================

df_5_series["Cuenta_tienda_frac"] = (
    df_5_series["Cuenta_tienda_%"] / 100
)

# ==========================================================
# 11. LIMITAR B Y M
# ==========================================================

df_5_series["B_limitado"] = np.clip(
    df_5_series["B"],
    B_MIN_TEORICO,
    B_MAX_TEORICO
)

df_5_series["M_limitado"] = np.clip(
    df_5_series["M"],
    M_MIN_TEORICO,
    M_MAX_TEORICO
)

# ==========================================================
# 12. NORMALIZAR B Y M
# ==========================================================

df_5_series["B_norm"] = (
    df_5_series["B_limitado"] - B_MIN_TEORICO
) / (
    B_MAX_TEORICO - B_MIN_TEORICO
)

df_5_series["M_norm"] = (
    df_5_series["M_limitado"] - M_MIN_TEORICO
) / (
    M_MAX_TEORICO - M_MIN_TEORICO
)

# ==========================================================
# 13. ORDENAR COLUMNAS
# ==========================================================

df_5_series = df_5_series[
    [
        "Serie",
        "PSH [h/día]",
        "B",
        "M",
        "B_limitado",
        "M_limitado",
        "B_norm",
        "M_norm",
        "Energía_planta_MWh_dia",
        "Cuenta de tienda [MWh]",
        "Cuenta_tienda_%",
        "Cuenta_tienda_frac"
    ]
]

# ==========================================================
# 14. ORDENAR POR SERIE
# ==========================================================

df_5_series = (
    df_5_series
    .sort_values("Serie")
    .reset_index(drop=True)
)

# ==========================================================
# 15. RESUMEN
# ==========================================================

print("==========================================")
print("df_5_series CONSTRUIDO")
print("==========================================")
print(f"Series obtenidas: {len(df_5_series)}")
print(f"Columnas: {len(df_5_series.columns)}")
print()
print(df_5_series)

# ================================================================
# APLICAR MODELO Phi(B,M) A LAS 5 SERIES
# ================================================================
#
# IMPORTANTE:
# - NO se vuelve a entrenar el modelo.
# - Se utiliza el mejor modelo ya seleccionado mediante LOO-CV.
# - estado_mejor contiene los parámetros entrenados.
# - predict_mejor aplica la función correspondiente.
#
# Entrada:
#     B_norm, M_norm
#
# Salida:
#     Capacidad corregida
#     Phi(B,M)
#     Diferencia respecto a cuenta de tienda
# ================================================================


# ================================================================
# 1. VERIFICAR QUE EL MODELO ENTRENADO EXISTA
# ================================================================

if "estado_mejor" not in globals():
    raise RuntimeError(
        "No existe 'estado_mejor'. "
        "Primero debes ejecutar el código de entrenamiento "
        "del modelo Phi(B,M)."
    )

if "predict_mejor" not in globals():
    raise RuntimeError(
        "No existe 'predict_mejor'. "
        "Primero debes ejecutar el código de entrenamiento "
        "del modelo Phi(B,M)."
    )

if "mejor_modelo_nombre" not in globals():
    raise RuntimeError(
        "No existe 'mejor_modelo_nombre'. "
        "Primero debes ejecutar el código de entrenamiento "
        "del modelo Phi(B,M)."
    )


# ================================================================
# 2. COPIA DEL DATAFRAME DE LAS 5 SERIES
# ================================================================

df_aplicacion = df_5_series.copy()


# ================================================================
# 3. VERIFICAR B Y M
# ================================================================

for columna in ["B", "M", "B_norm", "M_norm"]:

    if columna not in df_aplicacion.columns:
        raise KeyError(
            f"No existe la columna '{columna}' en df_5_series."
        )


# ================================================================
# 4. PREPARAR VARIABLES DE ENTRADA
# ================================================================

X_5 = df_aplicacion[
    ["B_norm", "M_norm"]
].to_numpy(dtype=float)


# ================================================================
# 5. APLICAR EL MEJOR MODELO
# ================================================================

df_aplicacion["Capacidad_corregida_frac"] = (
    predict_mejor(
        estado_mejor,
        X_5
    )
)

# ================================================================
# 6. CONVERTIR CAPACIDAD CORREGIDA A %
# ================================================================

df_aplicacion["Capacidad_corregida_%"] = (
    df_aplicacion["Capacidad_corregida_frac"] * 100
)

# ================================================================
# 7. CALCULAR CAPACIDAD CORREGIDA EN MWh
# ================================================================

df_aplicacion["Capacidad_corregida_MWh"] = (
    df_aplicacion["Capacidad_corregida_frac"]
    *
    df_aplicacion["Energía_planta_MWh_dia"]
)


# ================================================================
# 8. CALCULAR Phi(B,M)
# ================================================================

df_aplicacion["Phi_BM"] = (
    df_aplicacion["Capacidad_corregida_frac"]
    /
    df_aplicacion["Cuenta_tienda_frac"]
)

# ================================================================
# 9. DIFERENCIA RESPECTO A CUENTA DE TIENDA
# ================================================================

df_aplicacion["Diferencia_capacidad_%"] = (
    (
        df_aplicacion["Capacidad_corregida_frac"]
        /
        df_aplicacion["Cuenta_tienda_frac"]
    )
    - 1
) * 100


# ================================================================
# 10. DIFERENCIA ABSOLUTA EN MWh
# ================================================================

df_aplicacion["Diferencia_capacidad_MWh"] = (
    df_aplicacion["Capacidad_corregida_MWh"]
    -
    df_aplicacion["Cuenta de tienda [MWh]"]
)


# ================================================================
# 11. INDICAR MODELO UTILIZADO
# ================================================================

df_aplicacion["Modelo_seleccionado"] = (
    mejor_modelo_nombre
)

# ================================================================
# 12. MOSTRAR RESULTADOS
# ================================================================

print("\n================================================")
print("APLICACIÓN DEL MODELO Phi(B,M)")
print("================================================")

print(
    f"Modelo utilizado: {mejor_modelo_nombre}"
)

print(
    f"Series evaluadas: {len(df_aplicacion)}"
)

print("\n================================================")
print("RESULTADOS PARA LAS 5 SERIES")
print("================================================")


columnas_resultado = [

    "Serie",

    "B",
    "M",

    "B_norm",
    "M_norm",

    "Cuenta de tienda [MWh]",
    "Cuenta_tienda_%",

    "Capacidad_corregida_MWh",
    "Capacidad_corregida_%",

    "Phi_BM",

    "Diferencia_capacidad_MWh",
    "Diferencia_capacidad_%",

    "Modelo_seleccionado"

]

# ================================================================
# GRÁFICAS DE BARRAS
# COMPARACIÓN: CUENTA DE TIENDA vs MODELO Phi(B,M)
# % DE LA CAPACIDAD DE PLANTA
# ================================================================

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator


# ================================================================
# 1. CONFIGURACIÓN GENERAL
# ================================================================

df_plot = (
    df_aplicacion
    .sort_values("Serie")
    .copy()
)

series = df_plot["Serie"].astype(str).to_numpy()

x = np.arange(len(series))

ancho = 0.36

# Capacidad de planta
CAP_PLANTA_MW = 100.0


# ================================================================
# 2. CONVERTIR CAPACIDADES A % DE LA CAPACIDAD DE PLANTA
# ================================================================

df_plot["Cuenta_tienda_pct"] = (
    df_plot["Cuenta de tienda [MWh]"]
    / CAP_PLANTA_MW
    * 100
)

df_plot["Capacidad_corregida_pct"] = (
    df_plot["Capacidad_corregida_MWh"]
    / CAP_PLANTA_MW
    * 100
)


# ================================================================
# 3. FIGURA
# ================================================================

fig, ax = plt.subplots(
    figsize=(5, 3.5)
)


# ================================================================
# 4. BARRAS
# ================================================================

# Cuenta de tienda
ax.bar(
    x - ancho / 2,
    df_plot["Cuenta_tienda_pct"],
    width=ancho,
    color="lightgrey",
    edgecolor="black",
    linewidth=0.8,
    label="Inicial"
)

# Modelo Phi(B,M)
ax.bar(
    x + ancho / 2,
    df_plot["Capacidad_corregida_pct"],
    width=ancho,
    color="grey",
    edgecolor="black",
    linewidth=0.8,
    label=r"Modelo $\Phi(B,M)$"
)


# ================================================================
# 6. ETIQUETAS DE LOS EJES
# ================================================================

ax.set_ylabel(
    "Capacidad [MWh]",
    fontsize=10
)


# ================================================================
# 7. EJE X
# ================================================================

ax.set_xticks(x)

ax.set_xticklabels(
    series,
    fontsize=10
)


# ================================================================
# 9. GRID
# ================================================================

ax.grid(
    color="grey",
    alpha=0.8
)

ax.set_axisbelow(True)


# ================================================================
# 10. TICKS PRINCIPALES
# ================================================================

ax.tick_params(
    direction="in",
    axis="both",
    which="major",
    labelsize=10,
    width=1.0,
    length=7
)


# ================================================================
# 11. TICKS MENORES
# ================================================================

ax.tick_params(
    direction="in",
    axis="both",
    which="minor",
    width=1.0,
    length=3.5
)


# ================================================================
# 12. TICKS EN AMBOS LADOS
# ================================================================

ax.yaxis.set_ticks_position(
    "both"
)

ax.xaxis.set_ticks_position(
    "both"
)


# ================================================================
# 14. LEYENDA
# ================================================================

ax.legend(
    frameon=False,
    fontsize=10,
    loc="upper center",
    bbox_to_anchor=(0.5, 1.15),
    ncol=2
)

plt.show()

# ================================================================
# GRÁFICAS DE BARRAS HORIZONTALES
# B_norm Y M_norm — 5 SERIES
# ================================================================

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator


# ================================================================
# 1. DATOS
# ================================================================

df_plot = (
    df_aplicacion[
        ["Serie", "B", "M"]
    ]
    .dropna()
    .sort_values("Serie")
    .head(5)
    .copy()
)

series = df_plot["Serie"].astype(str).to_numpy()

y = np.arange(len(series))

alto = 0.32


# ================================================================
# 2. FIGURA
# ================================================================

fig, ax = plt.subplots(
    figsize=(5, 3.5)
)


# ================================================================
# 3. BARRAS HORIZONTALES — B
# ================================================================

ax.barh(
    y - alto / 2,
    df_plot["B"],
    height=alto,
    color="#fee08b",
    edgecolor="black",
    linewidth=0.8,
    label=r"$B$"
)


# ================================================================
# 4. BARRAS HORIZONTALES — M
# ================================================================

ax.barh(
    y + alto / 2,
    df_plot["M"],
    height=alto,
    color="#abd9e9",
    edgecolor="black",
    linewidth=0.8,
    label=r"$M$"
)


# ================================================================
# 5. EJE Y
# ================================================================

ax.set_yticks(y)

ax.set_yticklabels(
    series,
    fontsize=10
)

ax.set_xlabel(
    "Valor",
    fontsize=10
)


# ================================================================
# 6. LÍMITES
# ================================================================

ax.set_xlim(-1, 1)


# ================================================================
# 7. LÍNEA CENTRAL
# ================================================================

ax.axvline(
    0,
    color="black",
    linewidth=0.8
)




# ================================================================
# 9. TICKS PRINCIPALES
# ================================================================

ax.tick_params(
    direction="in",
    axis="both",
    which="major",
    labelsize=10,
    width=1.0,
    length=7,
    top=True,
    right=True
)


# ================================================================
# 10. TICKS MENORES
# ================================================================

ax.tick_params(
    direction="in",
    axis="both",
    which="minor",
    width=1.0,
    length=3.5,
    top=True,
    right=True
)


# ================================================================
# 11. TICKS EN AMBOS LADOS
# ================================================================

ax.xaxis.set_ticks_position("both")
ax.yaxis.set_ticks_position("both")


# ================================================================
# 12. GRID
# ================================================================

ax.grid(
    color="grey",
    alpha=0.8,
)

ax.set_axisbelow(True)


# ================================================================
# 13. BORDES
# ================================================================

for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_linewidth(0.8)


# ================================================================
# 14. ORDEN
# ================================================================

ax.invert_yaxis()


# ================================================================
# 15. LEYENDA
# ================================================================

ax.legend(
    frameon=False,
    fontsize=10,
    loc="upper center",
    bbox_to_anchor=(0.5, 1.18),
    ncol=2
)

plt.tight_layout()

plt.show()