import pandas as pd
import numpy as np

# ==========================================================
# CONFIGURACIÓN
# ==========================================================
demandaplana = 20  # MW
# Factor de conversión de irradiancia a generación
factor_generacion = (469888 / 1000000) * 0.17

# ==========================================================
# LEER EXCEL
# ==========================================================
df = pd.read_excel("51 seriesH/df_series_todas_las_subestaciones.xlsx")
df["fecha"] = pd.to_datetime(df["fecha"])

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

# ==========================================================
# CONTENEDOR GLOBAL
# ==========================================================
resultados_global = []
# ==========================================================
# LOOP POR SERIE
# ==========================================================
for serie_nombre in df_balance.columns:
    print(
        f"Procesando: {serie_nombre}"
    )
    # ======================================================
    # TOMAR BALANCE DE LA SERIE
    # ======================================================
    serie = df_balance[
        serie_nombre
    ].copy()
    # ======================================================
    # SELECCIONAR ÚNICAMENTE EXCEDENTES
    # ======================================================
    serie_excedentes = (
        serie.clip(lower=0)
    )
    # ======================================================
    # PASAR A COLUMNAS POR HORA
    # ======================================================
    df_aux = pd.DataFrame({

        "valor": serie_excedentes
    })
    df_aux["fecha"] = (
        df_aux.index.floor("D")
    )
    df_aux["hora"] = (
        df_aux.index.hour
    )
    # ======================================================
    # MATRIZ DÍA × HORA
    # ======================================================
    Datos = df_aux.pivot(
        index="fecha",
        columns="hora",
        values="valor"
    )
    Datos.columns = [
        f"hora_{h}"
        for h in Datos.columns
    ]
    # ======================================================
    # B Y M POR HORA
    # ======================================================
    for col in Datos.columns:
        # --------------------------------------------------
        # Serie temporal de esa hora
        # --------------------------------------------------
        x = Datos[col].dropna()
        # --------------------------------------------------
        # Validación
        # --------------------------------------------------
        if (
            x.sum() == 0
            or len(x) < 5
        ):
            continue
        # ==================================================
        # ACUMULADO
        # ==================================================
        Accum = x.cumsum()
        # ==================================================
        # MEDIA
        # ==================================================
        a_mu = np.percentile(x, 25)
        if a_mu == 0:
            continue
        # ==================================================
        # ACUMULADO FINAL
        # ==================================================
        acumulado = (
            Accum.iloc[-1]
        )
        # ==================================================
        # NÚMERO DE INTERSECCIONES
        # ==================================================
        Numero_final = int(
            (
                acumulado
                / a_mu
            )
            + 10
        )

        Numeros = np.arange(
            1,
            Numero_final,
            1
        )

        lista_a_mu = [

            i * a_mu

            for i in Numeros
        ]

        # ==================================================
        # IDENTIFICAR CRUCES
        # ==================================================
        listay = [
            i
            for i in Accum
            if i >= a_mu
        ]
        posiciony = [
            c
            for c, i in enumerate(Accum)
            if i >= a_mu

        ]

        # --------------------------------------------------
        # Si no hay cruces
        # --------------------------------------------------
        if len(listay) == 0:
            continue
        # ==================================================
        # CONSTRUIR tk
        # ==================================================
        lista_t1 = []
        lista_t2 = []
        # --------------------------------------------------
        # Primer intervalo
        # -------------------------------------------------
        for item in lista_a_mu:
            if item < listay[0]:
                lista_t1.append(
                    posiciony[0]
                )
        # --------------------------------------------------
        # Intervalos posteriores
        # --------------------------------------------------
        for k in range(
            len(listay) - 1
        ):
            for item in lista_a_mu:
                if (
                    listay[k]
                    <= item
                    < listay[k + 1]
                ):
                    lista_t2.append(
                        posiciony[k + 1]
                    )
        lista_t = (
            lista_t1
            + lista_t2
        )
        # ==================================================
        # VALIDAR tk
        # ==================================================
        if len(lista_t) < 2:
            continue
        # ==================================================
        # INTERVALOS tau_k
        # ==================================================
        df_t = pd.DataFrame({
            "tk": lista_t
        })
        df_t["tauk"] = (
            df_t["tk"]
            .diff()
            .fillna(
                df_t["tk"]
            )
        )
        # ==================================================
        # MEDIA Y DESVIACIÓN DE tau
        # ==================================================
        Media = (
            df_t["tauk"].mean()
        )
        DesviacionE = (
            df_t["tauk"].std()
        )
        # ==================================================
        # BURSTINESS B
        # ==================================================
        if (
            Media
            + DesviacionE
            == 0
        ):
            continue
        Bmu = (
            DesviacionE
            - Media
        ) / (

            DesviacionE
            + Media
        )
        # ==================================================
        # MEMORY M
        # ==================================================
        if len(df_t) > 2:
            Mmu, _ = spearmanr(
                df_t["tauk"][:-1],
                df_t["tauk"][1:]
            )
        else:
            Mmu = np.nan
        # ==================================================
        # GUARDAR
        # ==================================================
        resultados_global.append({
            "Serie": serie_nombre,
            "Hora": col,
            "a_mu": a_mu,
            "Media_tk": Media,
            "Std_tk": DesviacionE,
            "B": Bmu,
            "M": Mmu
        })
# ==========================================================
# DATAFRAME FINAL
# ==========================================================
df_BM_horas_series = pd.DataFrame(
    resultados_global
)

# ==========================================================
# CALCULAR B Y M PROMEDIO POR SERIE
# ==========================================================

df_plot = (
    df_BM_horas_series
    .groupby("Serie")[["B", "M"]]
    .mean()
    .reset_index()
)

# ==========================================================
# GUARDAR B Y M PROMEDIO POR SERIE
# ==========================================================

RUTA_SALIDA_BM = (
    "51 series/promedio_BM_por_serie.xlsx"
)

df_plot.to_excel(

    RUTA_SALIDA_BM,

    index=False

)

print(
    f"\nB y M promedio por serie guardados en:\n"
    f"{RUTA_SALIDA_BM}"
)