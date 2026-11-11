# Figuras de la tesis (capítulos 1 a 3)

Aquí está **cada figura junto al código que la hace**: una carpeta por
capítulo y, dentro, un script por figura y su resultado en PDF (para LaTeX)
y PNG (para verla en GitHub). El número del script es el número de la
figura en la tesis (`fig_3_6_…py` → Figura 3.6).

```
figuras/
├── estilo.py               tamaño, márgenes, letra y guardar() comunes a todas
├── comun_tesis.py          paleta y funciones para esquemas (cajas y flechas)
├── sitios_ilustrativos.py  sitios sintéticos de las figuras 2.4, 3.3, 3.5–3.7 y 3.10
├── generar_todas.py        corre todos los scripts (cada uno en su proceso)
├── copiar_a_tesis.py       copia los PDF a TESIS/Figuras
├── capitulo_1/             fig_1_1 … fig_1_5  (+ datos/Inversiones.xlsx)
├── capitulo_2/             fig_2_1 … fig_2_8
└── capitulo_3/             fig_3_1 … fig_3_10
```

## Cómo regenerarlas

Desde la raíz del repositorio, con el entorno del proyecto:

```bash
python figuras/generar_todas.py                          # todas
python figuras/capitulo_3/fig_3_9_series_barajadas.py    # solo una
python figuras/copiar_a_tesis.py                         # PDF -> TESIS/Figuras
```

Las figuras 1.2, 3.4 y 3.9 leen los Excel de `datos/51 series/` (no están
en GitHub, ver `datos/DATOS.md`). Las demás no necesitan datos externos.

## Capítulo 1. Introducción

| Fig. | Figura | Script | Datos |
|---|---|---|---|
| 1.1 | [Generation](capitulo_1/Generation.png) | [`fig_1_1_generacion_renovable.py`](capitulo_1/fig_1_1_generacion_renovable.py) | `capitulo_1/datos/Inversiones.xlsx` |
| 1.2 | [Tres_dias_horizontal](capitulo_1/Tres_dias_horizontal.png) | [`fig_1_2_tres_dias.py`](capitulo_1/fig_1_2_tres_dias.py) | 51 series de GHI |
| 1.3 | [Linea_tiempo_normativa](capitulo_1/Linea_tiempo_normativa.png) | [`fig_1_3_linea_tiempo_normativa.py`](capitulo_1/fig_1_3_linea_tiempo_normativa.py) | ninguno |
| 1.4 | [Mismo_mes_agrupamiento](capitulo_1/Mismo_mes_agrupamiento.png) | [`fig_1_4_mismo_mes_agrupamiento.py`](capitulo_1/fig_1_4_mismo_mes_agrupamiento.py) | ninguno |
| 1.5 | [Estructura_tesis](capitulo_1/Estructura_tesis.png) | [`fig_1_5_estructura_tesis.py`](capitulo_1/fig_1_5_estructura_tesis.py) | ninguno |

## Capítulo 2. Marco teórico y revisión

| Fig. | Figura | Script | Datos |
|---|---|---|---|
| 2.1 | [PRISMA_revision](capitulo_2/PRISMA_revision.png) | [`fig_2_1_prisma.py`](capitulo_2/fig_2_1_prisma.py) | ninguno |
| 2.2 | [Curva_LPSP_kappa](capitulo_2/Curva_LPSP_kappa.png) | [`fig_2_2_curva_lpsp_kappa.py`](capitulo_2/fig_2_2_curva_lpsp_kappa.py) | ninguno |
| 2.3 | [Plano_BM_conceptual](capitulo_2/Plano_BM_conceptual.png) | [`fig_2_3_plano_BM.py`](capitulo_2/fig_2_3_plano_BM.py) | ninguno |
| 2.4 | [Efecto_intermitencia_curva](capitulo_2/Efecto_intermitencia_curva.png) | [`fig_2_4_efecto_intermitencia_curva.py`](capitulo_2/fig_2_4_efecto_intermitencia_curva.py) | sitios sintéticos |
| 2.5 | [Clasificacion_estudios](capitulo_2/Clasificacion_estudios.png) | [`fig_2_5_clasificacion_estudios.py`](capitulo_2/fig_2_5_clasificacion_estudios.py) | ninguno |
| 2.6 | [Calidad_metodologica](capitulo_2/Calidad_metodologica.png) | [`fig_2_6_calidad_metodologica.py`](capitulo_2/fig_2_6_calidad_metodologica.py) | ninguno |
| 2.7 | [Escalas_temporales](capitulo_2/Escalas_temporales.png) | [`fig_2_7_escalas_temporales.py`](capitulo_2/fig_2_7_escalas_temporales.py) | ninguno |
| 2.8 | [Marco_conceptual](capitulo_2/Marco_conceptual.png) | [`fig_2_8_marco_conceptual.py`](capitulo_2/fig_2_8_marco_conceptual.py) | ninguno |

## Capítulo 3. Metodología

| Fig. | Figura | Script | Datos |
|---|---|---|---|
| 3.1 | [Diseno_investigacion](capitulo_3/Diseno_investigacion.png) | [`fig_3_1_diseno_investigacion.py`](capitulo_3/fig_3_1_diseno_investigacion.py) | ninguno |
| 3.2 | [fig_flujo_metodologico](capitulo_3/fig_flujo_metodologico.png) | [`fig_3_2_flujo_metodologico.py`](capitulo_3/fig_3_2_flujo_metodologico.py) | ninguno |
| 3.3 | [fig_sustitucion_planta](capitulo_3/fig_sustitucion_planta.png) | [`fig_3_3_sustitucion_planta.py`](capitulo_3/fig_3_3_sustitucion_planta.py) | sitios sintéticos |
| 3.4 | [Muestra_PSH](capitulo_3/Muestra_PSH.png) | [`fig_3_4_muestra_psh.py`](capitulo_3/fig_3_4_muestra_psh.py) | PSH y 5 zonas |
| 3.5 | [fig_eventos_deficit](capitulo_3/fig_eventos_deficit.png) | [`fig_3_5_eventos_deficit.py`](capitulo_3/fig_3_5_eventos_deficit.py) | sitios sintéticos |
| 3.6 | [fig_tiempos_entre_eventos](capitulo_3/fig_tiempos_entre_eventos.png) | [`fig_3_6_tiempos_entre_eventos.py`](capitulo_3/fig_3_6_tiempos_entre_eventos.py) | sitios sintéticos |
| 3.7 | [fig_estiramiento_curva](capitulo_3/fig_estiramiento_curva.png) | [`fig_3_7_estiramiento_curva.py`](capitulo_3/fig_3_7_estiramiento_curva.py) | sitios sintéticos |
| 3.8 | [Esquema_validacion](capitulo_3/Esquema_validacion.png) | [`fig_3_8_esquema_validacion.py`](capitulo_3/fig_3_8_esquema_validacion.py) | ninguno |
| 3.9 | [Series_barajadas](capitulo_3/Series_barajadas.png) | [`fig_3_9_series_barajadas.py`](capitulo_3/fig_3_9_series_barajadas.py) | 51 series de GHI |
| 3.10 | [fig_reglas_operacion](capitulo_3/fig_reglas_operacion.png) | [`fig_3_10_reglas_operacion.py`](capitulo_3/fig_3_10_reglas_operacion.py) | sitios sintéticos |

## Reglas comunes (`estilo.py`)

| Qué | Valor |
|---|---|
| Ancho de toda figura | 6.3 in (≈ `\textwidth`) |
| Espacio para el eje Y | 0.70 in, igual en todas |
| Letra | 10 pt |
| `bbox_inches="tight"` | no se usa (cambiaría el margen de cada figura) |

Para agregar una figura: copiar un script del mismo capítulo, cambiar el
dibujo y guardar con `guardar(fig, "capitulo_N", "Nombre")`.

Las figuras de resultados (capítulo 4) están en `codigo/figuras_resultados/`.
