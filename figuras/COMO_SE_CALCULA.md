# Cómo se calcula cada figura (capítulos 1 a 4)

Cada figura se hace con un script de esta carpeta, en `capitulo_N/`, y se
guarda en la misma carpeta como PDF (para LaTeX) y PNG. Para regenerarlas
todas, desde la raíz del repositorio: `python figuras/generar_todas.py`.

Hay cuatro tipos de figura:

- **Esquemas y cifras escritas en el script** (no usan datos): 1.3, 1.5, 2.1, 2.5, 2.6, 2.7, 2.8, 3.1, 3.2 y 3.8.
- **Curvas teóricas** (fórmulas, sin simulación): 2.2 y 2.3.
- **Sitios sintéticos con el simulador del pipeline** (`sitios_ilustrativos.py`): 1.4, 2.4, 3.3, 3.5, 3.6, 3.7 y 3.10.
- **Datos reales**: 1.1 (IEA), 1.2, 3.4 y 3.9 (series de GHI de `datos/51 series/`).

Parámetros comunes de las simulaciones: demanda plana D = 20 MW, planta
común de 150 MW (7,5D), PR = 0,80, eficiencia de carga y descarga 0,922,
SOC entre 10 % y 90 % (80 % de la capacidad nominal es utilizable), relación E/P = 4 h (todo en `codigo/config.yaml`).

## Capítulo 1. Introducción

### Figura 1.1. Participación de las renovables en la generación eléctrica

- **Script:** `capitulo_1/fig_1_1_generacion_renovable.py`
- **Figura:** `capitulo_1/Generation.pdf` y `.png`
- **Datos:** Inversiones.xlsx (IEA)

Lee la hoja «Generacion» de `capitulo_1/datos/Inversiones.xlsx` (IEA, 2025): para cada año, el porcentaje de la generación eléctrica que aporta cada tecnología (solar FV, eólica, hidroeléctrica y otras). Toma los años desde 2014 y dibuja una línea por tecnología con el área sombreada. No hace cálculos: grafica los porcentajes como vienen.

### Figura 1.2. Generación FV horaria en tres días

- **Script:** `capitulo_1/fig_1_2_tres_dias.py`
- **Figura:** `capitulo_1/Tres_dias_horizontal.pdf` y `.png`
- **Datos:** 51 series de GHI

Lee la GHI horaria de Cuestesitas (51 series, ruta de `config.yaml`) y la convierte en potencia con el mismo modelo del pipeline, `pv.generacion_mw`: P = P_planta · PR · G / 1000. Dibuja la generación hora a hora de tres días (28-09-2024, 04-11-2003 y 30-11-2011) y escribe encima la energía del día, E_d = suma de las 24 horas.

### Figura 1.3. Línea de tiempo de la normativa

- **Hecha en:** Canva (no tiene script)
- **Figura:** `capitulo_1/Linea_tiempo_normativa.pdf` y `.png`
- **Datos:** ninguno

Esquema diseñado a mano en Canva y exportado como PDF y PNG. No se genera con
código: `generar_todas.py` no la toca. Para cambiarla, editarla en Canva y
volver a exportar los dos archivos con el mismo nombre.

### Figura 1.4. Mismo mes, distinto agrupamiento de los días nublados

- **Script:** `capitulo_1/fig_1_4_mismo_mes_agrupamiento.py`
- **Figura:** `capitulo_1/Mismo_mes_agrupamiento.pdf` y `.png`
- **Datos:** sintéticos

Datos sintéticos: dos meses de 30 días con 10 días nublados cada uno, es decir, la misma energía. Generación horaria = 150 MW · 0,80 · índice de claridad (0,78 despejado, 0,40 nublado) · perfil de cielo despejado. En (a) los días nublados van uno cada tres días y en (b) son diez seguidos. Simula hora a hora una batería de 27 h de demanda (540 MWh nominales, 432 MWh utilizables; E/P = 4 h; η = 0,922; SOC entre 10 % y 90 %; empieza en 90 %) con despacho directo y grafica el SOC y la energía no suministrada acumulada.

### Figura 1.5. Estructura de la tesis

- **Script:** `capitulo_1/fig_1_5_estructura_tesis.py`
- **Figura:** `capitulo_1/Estructura_tesis.pdf` y `.png`
- **Datos:** ninguno

Esquema sin datos con el formato de etapas: tres paneles a la izquierda (Stage 1 a 3, cada uno con pestaña azul, título y descripción) y la etapa 4 a la derecha con los dos artículos. Las líneas muestran de qué etapas sale cada artículo. Textos en `ETAPAS`, `ETAPA_4` y `ARTICULOS`.

## Capítulo 2. Marco teórico y revisión

### Figura 2.1. Diagrama PRISMA de la revisión

- **Script:** `capitulo_2/fig_2_1_prisma.py`
- **Figura:** `capitulo_2/PRISMA_revision.pdf` y `.png`
- **Datos:** cifras del artículo 1

Diagrama PRISMA dibujado con cajas y flechas. Las cifras (348 registros, 81 duplicados, 267 tamizados, 194 excluidos, 73 evaluados, 37 excluidos y 36 incluidos) están en el diccionario `NUMEROS`, tomadas de Tuirán et al. (2026).

### Figura 2.2. Forma de la curva capacidad–confiabilidad y κ

- **Script:** `capitulo_2/fig_2_2_curva_lpsp_kappa.py`
- **Figura:** `capitulo_2/Curva_LPSP_kappa.pdf` y `.png`
- **Datos:** fórmula

Curvas analíticas, sin simulación: LPSP(E) = L_0 · e^(−E/κ) con L_0 = 0,30 y κ = 6, 12 y 24 h. (a) Escala lineal, con κ marcado donde la LPSP cae a L_0/e. (b) Escala logarítmica: rectas de pendiente −1/κ, con los puntos E* = κ · ln(L_0/LPSP*) para 5, 2 y 1 %. (c) E* frente a la meta.

### Figura 2.3. Qué miden B y M

- **Script:** `capitulo_2/fig_2_3_plano_BM.py`
- **Figura:** `capitulo_2/Plano_BM_conceptual.pdf` y `.png`
- **Datos:** sintéticos

Genera cuatro secuencias de 4000 intervalos con media 10: regular (10 ± 1), Poisson (exponencial), ráfagas sin memoria (20 % de intervalos largos) y ráfagas con memoria (cadena de Markov de dos estados con la misma proporción). Para cada una calcula B = (σ − μ)/(σ + μ) y M, la correlación entre intervalos consecutivos, y las ubica en el plano B–M. Semilla fija (7).

### Figura 2.4. Efecto de la intermitencia en la curva

- **Script:** `capitulo_2/fig_2_4_efecto_intermitencia_curva.py`
- **Figura:** `capitulo_2/Efecto_intermitencia_curva.pdf` y `.png`
- **Datos:** sitios sintéticos + simulador

Dos sitios sintéticos de `sitios_ilustrativos.py` con 30 % de días nublados: dispersos (δ = 0) y agrupados (δ = 0,25, q = 0,97). Genera 27 años de GHI, calcula el balance con la planta de 150 MW y la demanda de 20 MW, y simula la batería con el simulador del pipeline (`confiabilidad.evaluar`) de 0 a 6000 MWh cada 75. (a) Días de déficit de un año. (b) LPSP frente a la capacidad y κ ajustado (`sustituto.ajustar_kappa`). (c) E* para cada meta.

### Figura 2.5. Clasificación de los 36 estudios

- **Script:** `capitulo_2/fig_2_5_clasificacion_estudios.py`
- **Figura:** `capitulo_2/Clasificacion_estudios.pdf` y `.png`
- **Datos:** cifras del artículo 1

Barras horizontales con el número de estudios en cada categoría: representación del fenómeno FV, métrica de decisión y horizonte de simulación. Las cifras de Tuirán et al. (2026) están en `REPRESENTACION`, `METRICAS` y `HORIZONTES`; el total es 36.

### Figura 2.6. Calidad metodológica de los estudios

- **Script:** `capitulo_2/fig_2_6_calidad_metodologica.py`
- **Figura:** `capitulo_2/Calidad_metodologica.pdf` y `.png`
- **Datos:** cifras del artículo 1

Barras apiladas: para cada criterio Q1–Q10, el porcentaje de los 36 estudios que cumple, cumple en parte o no cumple (número de estudios / 36 · 100). Las cifras están en `CRITERIOS`.

### Figura 2.7. Escalas temporales de la variabilidad FV

- **Script:** `capitulo_2/fig_2_7_escalas_temporales.py`
- **Figura:** `capitulo_2/Escalas_temporales.pdf` y `.png`
- **Datos:** ninguno

Esquema conceptual sobre un eje de tiempo logarítmico: cada fila es un fenómeno con el rango de duraciones en que actúa y el criterio de dimensionamiento que suele determinar. No usa datos; se edita en `FILAS`.

### Figura 2.8. Marco conceptual

- **Script:** `capitulo_2/fig_2_8_marco_conceptual.py`
- **Figura:** `capitulo_2/Marco_conceptual.pdf` y `.png`
- **Datos:** ninguno

Esquema sin datos: PSH, B y M actúan sobre el déficit acumulado, que fija la curva capacidad–confiabilidad (κ), de la que salen RQ1 y RQ2, con las hipótesis H1–H3. Se edita en `BLOQUES` y `FLECHAS`.

## Capítulo 3. Metodología

### Figura 3.1. Diseño de la investigación

- **Script:** `capitulo_3/fig_3_1_diseno_investigacion.py`
- **Figura:** `capitulo_3/Diseno_investigacion.pdf` y `.png`
- **Datos:** ninguno

Esquema sin datos: tres capas (paradigma, enfoque y diseño) y las cuatro etapas del estudio. Se edita en `CAPAS` y `ETAPAS`.

### Figura 3.2. Flujo metodológico

- **Script:** `capitulo_3/fig_3_2_flujo_metodologico.py`
- **Figura:** `capitulo_3/fig_flujo_metodologico.pdf` y `.png`
- **Datos:** ninguno

Esquema sin datos del flujo metodológico: de la GHI horaria a dos ramas (métricas B y M; curva y κ) que se unen en el modelo sustituto. Se edita en `BLOQUES` y `FLECHAS`.

### Figura 3.3. Curvas de igual LPSP: planta común

- **Script:** `capitulo_3/fig_3_3_sustitucion_planta.py`
- **Figura:** `capitulo_3/fig_sustitucion_planta.pdf` y `.png`
- **Datos:** sitios sintéticos + simulador

Para los sitios sintéticos independiente y agrupado (15 años), simula la LPSP en una grilla de potencia FV de 110 a 260 MW (cada 10) y capacidad de 0 a 6000 MWh (cada 150), y traza las curvas de igual LPSP (1, 2 y 5 %). La línea horizontal es la planta común de 150 MW (7,5D).

### Figura 3.4. Recurso solar de la muestra

- **Script:** `capitulo_3/fig_3_4_muestra_psh.py`
- **Figura:** `capitulo_3/Muestra_PSH.pdf` y `.png`
- **Datos:** PSH de 51 sitios y 5 zonas

Datos reales. Para los 51 sitios lee la hoja «PSH diarias» de `PSH_resultados.xlsx` y calcula la media y los percentiles 10 y 90. Para las 5 zonas suma la GHI horaria de cada día y la divide entre 1000 (PSH diaria), sin el 29 de febrero, y calcula lo mismo. Ordena los sitios por PSH media.

### Figura 3.5. Definición de los eventos de déficit

- **Script:** `capitulo_3/fig_3_5_eventos_deficit.py`
- **Figura:** `capitulo_3/fig_eventos_deficit.pdf` y `.png`
- **Datos:** sitio sintético

Sitio sintético «Clustered». (a) Generación horaria de 12 días frente a la demanda de 20 MW. (b) Déficit diario d_j = Σ_h max(D − P, 0) durante 45 días, su media, los días de evento (d_j > media) y los tiempos τ entre inicios de eventos.

### Figura 3.6. Qué miden B y M en los tiempos entre eventos

- **Script:** `capitulo_3/fig_3_6_tiempos_entre_eventos.py`
- **Figura:** `capitulo_3/fig_tiempos_entre_eventos.pdf` y `.png`
- **Datos:** sitios sintéticos

Cuatro sitios sintéticos de 27 años con la misma PSH (regular, independiente, agrupado y muy agrupado). Para cada uno calcula los eventos diarios y los τ. (a) Probabilidad de que τ supere cada valor. (b) τ_k frente a τ_k+1. (c) B y M de cada sitio en el plano B–M, junto con un conjunto de sitios que barre δ y q.

### Figura 3.7. Cómo la intermitencia estira la curva

- **Script:** `capitulo_3/fig_3_7_estiramiento_curva.py`
- **Figura:** `capitulo_3/fig_estiramiento_curva.pdf` y `.png`
- **Datos:** sitios sintéticos + simulador

Los cuatro sitios sintéticos (27 años) se simulan de 0 a 6000 MWh cada 75. (a) LPSP frente a la capacidad, con el ajuste exponencial y la capacidad para 1 %. (b) E* frente a la meta. (c) El mismo agrupamiento con distinta PSH. (d) 25 sitios (5 valores de δ × 5 de q, 15 años) con κ frente a B, coloreados por M. Los valores quedan en `datos_estiramiento.csv`.

### Figura 3.8. Esquema de validación

- **Script:** `capitulo_3/fig_3_8_esquema_validacion.py`
- **Figura:** `capitulo_3/Esquema_validacion.pdf` y `.png`
- **Datos:** ninguno

Esquema sin datos: especificaciones comparadas, pruebas y criterios de decisión del modelo sustituto. Se edita en `MODELOS`, `PRUEBAS` y `CRITERIOS`.

### Figura 3.9. Series de días barajados

- **Script:** `capitulo_3/fig_3_9_series_barajadas.py`
- **Figura:** `capitulo_3/Series_barajadas.pdf` y `.png`
- **Datos:** serie real de Ibagué

Datos reales. Elige el sitio de PSH mediana (Ibagué), calcula el balance con la planta común (150 MW · 0,80 · G/1000 − 20 MW) y crea dos versiones con `sinteticas.barajar_dias`: días barajados dentro de cada mes y todos los días barajados (semilla 7). Marca los días de déficit (d_j > media) de 2015–2016 y calcula B sobre los 27 años de cada versión.

### Figura 3.10. Reglas de operación del BESS

- **Script:** `capitulo_3/fig_3_10_reglas_operacion.py`
- **Figura:** `capitulo_3/fig_reglas_operacion.pdf` y `.png`
- **Datos:** sitio sintético + simulador

Sitio sintético agrupado con una batería de 1000 MWh. Simula tres reglas con `reglas_operacion.simular_regla`: R1 despacho directo, R2 reserva de 30 % del SOC (20 puntos sobre el piso) y R3 descarga solo de 18:00 a 22:00. (a) SOC durante una racha de días de déficit. (b) Energía no suministrada acumulada.

## Capítulo 4. Resultados

Ninguna de estas figuras simula: leen las tablas que dejó el pipeline en
`codigo/resultados/articulo2/` con `resultados.leer_resultado(...)`. Si se
cambia algo en `config.yaml`, primero se corren los pasos 10–15 y luego estas
figuras. Todas usan la planta común de 7,5D (150 MW), demanda plana de 20 MW
y almacenamiento en horas de demanda.

### Figura 4.1. Intermitencia de los 51 sitios

- **Script:** `capitulo_4/fig_4_1_intermitencia_sitios.py`
- **Figura:** `capitulo_4/Intermitencia_sitios.pdf` y `.png`
- **Datos:** `10_sitios.xlsx`, `10_sensibilidad_BM_planta.xlsx`, `14_sustitutos_sitios.xlsx`

(a) B diaria frente a la PSH de cada sitio, con el color según M; r es la correlación de Pearson (0,54). La franja gris va del mínimo al máximo de B de las series con todos los días barajados (media de las 6 realizaciones de cada sitio): todas las series reales quedan por encima. (b) M frente a B (r = 0,67). (c) B calculada con eventos horarios frente a la PSH (r = −0,88): con eventos horarios B mide la noche y la cantidad de sol. (d) B recalculada con plantas de 5D, 6,25D y 10D frente a B con 7,5D; ρ es la correlación de Spearman del orden de los sitios (0,94, 0,98 y 0,89).

### Figura 4.2. Curvas capacidad–confiabilidad

- **Script:** `capitulo_4/fig_4_2_curvas_reales.py`
- **Figura:** `capitulo_4/fig_curvas_reales.pdf` y `.png`
- **Datos:** `10_curvas.csv.gz`, `10_sitios.xlsx`, `10_costo_planta_comun.xlsx`

(a) LPSP de cada sitio frente a la capacidad del BESS (barrido del paso 10), coloreada por PSH, con las metas de 5, 2 y 1 %. (b) Capacidad necesaria E* para cada meta (bisección sobre el simulador) frente a κ: E* crece con κ, como dice E* = κ·ln(L0/LPSP*).

### Figura 4.3. Qué explica κ

- **Script:** `capitulo_4/fig_4_3_kappa_predictores.py`
- **Figura:** `capitulo_4/fig_kappa_predictores.pdf` y `.png`
- **Datos:** `10_sitios.xlsx`

(a) ln κ frente a la PSH, coloreado por B, con la recta del modelo de solo PSH. (b) Predicción leave-one-out (se ajusta sin el sitio y se predice el sitio) del modelo de solo PSH y del modelo PSH + B + M. (c) y (d) Residuos parciales: residuo del modelo completo + β_j·x_j frente a B y a M; la pendiente de cada nube es el coeficiente de la regresión múltiple.

### Figura 4.4. Valor agregado de B y M

- **Script:** `capitulo_4/fig_4_4_efecto_BM.py`
- **Figura:** `capitulo_4/fig_efecto_BM.pdf` y `.png`
- **Datos:** `11_comparacion_modelos.xlsx`, `11_bootstrap_coeficientes.xlsx`, `11_efecto_BM.xlsx`

(a) R² leave-one-out de cada modelo; la línea punteada es R²_LOO(PSH) + 0,05, el umbral fijado antes de ajustar. (b) Cambio de ln κ por una desviación estándar de cada predictor, con el intervalo bootstrap del 95 % (2000 remuestreos de sitios y de bloques). (c) Batería extra para pasar de 5 % a 1 % (κ·ln 5) en un sitio de PSH mediana con B o M en sus percentiles 10, 50 y 90.

### Figura 4.5. Almacenamiento debido al orden de los días

- **Script:** `capitulo_4/fig_4_5_orden_dias.py`
- **Figura:** `capitulo_4/Orden_dias.pdf` y `.png`
- **Datos:** `14_sustitutos_sitios.xlsx`

(a) E* para LPSP = 1 % de cada sitio con la serie observada, con los días barajados dentro del mes y con todos los días barajados (media de 6 realizaciones), sitios de mayor a menor PSH. (b) Parte de E* observada que se debe al orden: (E*obs − E*todo)/E*obs, dividida en estacional e interanual (E*mes − E*todo) y rachas dentro del mes (E*obs − E*mes). Barras: mediana; puntos: cada sitio.

### Figura 4.6. Aplicación a las cinco zonas nuevas

- **Script:** `capitulo_4/fig_4_6_zonas.py`
- **Figura:** `capitulo_4/Zonas_aplicacion.pdf` y `.png`
- **Datos:** `15_zonas.xlsx`

(a) κ simulado de cada zona frente al κ predicho con los coeficientes del paso 11, sin reajustar: círculo vacío con solo PSH y círculo lleno con PSH + B; la flecha muestra cuánto cambia la predicción al agregar B. El RMSE de ln κ baja de 0,46 a 0,28. (b) E* simulada de cada zona para 5, 2 y 1 %, zonas de mayor a menor PSH.

### Figura 4.7. Costo de la confiabilidad

- **Script:** `capitulo_4/fig_4_7_costo_confiabilidad.py`
- **Figura:** `capitulo_4/fig_costo_confiabilidad.pdf` y `.png`
- **Datos:** `10_costo_planta_comun.xlsx`, `10_minimo_costo.xlsx`, `10_sitios.xlsx`, `10_sustitucion_planta_bateria.csv.gz`

(a) Costo anual (CAPEX anualizado + O&M) de cada punto de LPSP en los tramos 5→2 % y 2→1 %, con solo batería y con planta y batería de mínimo costo. (b) Costo marginal de la ENS evitada con batería, c_E·κ/(LPSP·D), frente a la meta, con el VoLL (546 USD/MWh). (c) Batería mínima para cada potencia FV en el sitio de κ mediano, con el punto de mínimo costo. (d) Potencia FV del sistema de mínimo costo.

### Figura 4.8. Reglas de operación

- **Script:** `capitulo_4/fig_4_8_reglas_operacion.py`
- **Figura:** `capitulo_4/Reglas_resultados.pdf` y `.png`
- **Datos:** `12_reglas.xlsx`, `12_cota_lp.xlsx`, `10_sitios.xlsx`

(a) LPSP de R2 (reserva de 30 % del SOC) y de R3 (descarga solo de 18:00 a 22:00) dividida por la LPSP de R1, con la batería E* de R1 para cada meta; puntos = sitios, barra = mediana (R2: 3,37, 2,38, 1,98; R3: 7,3, 18,3, 36,6). (b) Penalidad de R2 al 5 % frente a B (Spearman ρ = 0,41): la reserva perjudica más donde B es mayor. (c) Energía no servida con R1 frente al programa lineal con previsión perfecta en 306 ventanas de 60 días: todos los puntos sobre la identidad (diferencia máxima ≈ 2·10⁻¹¹ MWh), así que R1 es óptima.

