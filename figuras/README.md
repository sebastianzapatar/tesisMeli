# Figuras de la tesis (capítulos 1 a 4)

Cada figura está en `capitulo_N/` junto al script que la hace. Las que dicen *Canva* o *hecha aparte* no tienen script. Cómo se calcula cada una: [COMO_SE_CALCULA.md](COMO_SE_CALCULA.md).

## Capítulo 1. Introducción

| Fig. | Figura | Script | Datos |
|---|---|---|---|
| 1.1 | [Generation](capitulo_1/Generation.pdf) | [`fig_1_1_generacion_renovable.py`](capitulo_1/fig_1_1_generacion_renovable.py) | `capitulo_1/datos/Inversiones.xlsx` |
| 1.2 | [Tres_dias_horizontal](capitulo_1/Tres_dias_horizontal.pdf) | [`fig_1_2_tres_dias.py`](capitulo_1/fig_1_2_tres_dias.py) | 51 series de GHI |
| 1.3 | [Linea_tiempo_normativa](capitulo_1/Linea_tiempo_normativa.pdf) | Canva | ninguno |
| 1.4 | [Mismo_mes_agrupamiento](capitulo_1/Mismo_mes_agrupamiento.pdf) | [`fig_1_4_mismo_mes_agrupamiento.py`](capitulo_1/fig_1_4_mismo_mes_agrupamiento.py) | ninguno |
| 1.5 | [Estructura_tesis](capitulo_1/Estructura_tesis.pdf) | Canva | ninguno |

## Capítulo 2. Marco teórico y revisión

| Fig. | Figura | Script | Datos |
|---|---|---|---|
| 2.1 | [PRISMA](capitulo_2/PRISMA.pdf) | hecha aparte | cifras del artículo 1 |
| 2.2 | [Curva_LPSP_kappa](capitulo_2/Curva_LPSP_kappa.pdf) | [`fig_2_2_curva_lpsp_kappa.py`](capitulo_2/fig_2_2_curva_lpsp_kappa.py) | fórmula |
| 2.3 | [Plano_BM_conceptual](capitulo_2/Plano_BM_conceptual.pdf) | [`fig_2_3_plano_BM.py`](capitulo_2/fig_2_3_plano_BM.py) | sintéticos |
| 2.4 | [Efecto_intermitencia_curva](capitulo_2/Efecto_intermitencia_curva.pdf) | [`fig_2_4_efecto_intermitencia_curva.py`](capitulo_2/fig_2_4_efecto_intermitencia_curva.py) | sitios sintéticos |
| 2.5 | Clasificacion_estudios [1](capitulo_2/Clasificacion_estudios1.pdf), [2](capitulo_2/Clasificacion_estudios2.pdf), [3](capitulo_2/Clasificacion_estudios3.pdf), [4](capitulo_2/Clasificacion_estudios4.pdf) | Canva | cifras del artículo 1 |
| 2.6 | [Calidad_metodologica](capitulo_2/Calidad_metodologica.pdf) | [`fig_2_6_calidad_metodologica.py`](capitulo_2/fig_2_6_calidad_metodologica.py) | cifras del artículo 1 |
| 2.7 | [Escalas_temporales](capitulo_2/Escalas_temporales.pdf) | [`fig_2_7_escalas_temporales.py`](capitulo_2/fig_2_7_escalas_temporales.py) | ninguno |
| 2.8 | [Marco_conceptual](capitulo_2/Marco_conceptual.pdf) | Canva | ninguno |

## Capítulo 3. Metodología

| Fig. | Figura | Script | Datos |
|---|---|---|---|
| 3.1 | [Diseno_investigacion](capitulo_3/Diseno_investigacion.pdf) | [`fig_3_1_diseno_investigacion.py`](capitulo_3/fig_3_1_diseno_investigacion.py) | ninguno |
| 3.2 | [fig_flujo_metodologico](capitulo_3/fig_flujo_metodologico.pdf) | [`fig_3_2_flujo_metodologico.py`](capitulo_3/fig_3_2_flujo_metodologico.py) | ninguno |
| 3.3 | [fig_sustitucion_planta](capitulo_3/fig_sustitucion_planta.pdf) | [`fig_3_3_sustitucion_planta.py`](capitulo_3/fig_3_3_sustitucion_planta.py) | sitios sintéticos |
| 3.4 | [Muestra_PSH](capitulo_3/Muestra_PSH.pdf) | [`fig_3_4_muestra_psh.py`](capitulo_3/fig_3_4_muestra_psh.py) | PSH y 5 zonas |
| 3.5 | [fig_eventos_deficit](capitulo_3/fig_eventos_deficit.pdf) | [`fig_3_5_eventos_deficit.py`](capitulo_3/fig_3_5_eventos_deficit.py) | sitios sintéticos |
| 3.6 | [fig_tiempos_entre_eventos](capitulo_3/fig_tiempos_entre_eventos.pdf) | [`fig_3_6_tiempos_entre_eventos.py`](capitulo_3/fig_3_6_tiempos_entre_eventos.py) | sitios sintéticos |
| 3.7 | [fig_estiramiento_curva](capitulo_3/fig_estiramiento_curva.pdf) | [`fig_3_7_estiramiento_curva.py`](capitulo_3/fig_3_7_estiramiento_curva.py) | sitios sintéticos (`datos_estiramiento.csv`) |
| 3.8 | [Esquema_validacion](capitulo_3/Esquema_validacion.pdf) | [`fig_3_8_esquema_validacion.py`](capitulo_3/fig_3_8_esquema_validacion.py) | ninguno |
| 3.9 | [Series_barajadas](capitulo_3/Series_barajadas.pdf) | [`fig_3_9_series_barajadas.py`](capitulo_3/fig_3_9_series_barajadas.py) | 51 series de GHI |
| 3.10 | [fig_reglas_operacion](capitulo_3/fig_reglas_operacion.pdf) | [`fig_3_10_reglas_operacion.py`](capitulo_3/fig_3_10_reglas_operacion.py) | sitios sintéticos |

## Capítulo 4. Resultados

Todas leen las tablas de `codigo/resultados/articulo2/` (pasos 10 a 15 del pipeline) con `resultados.py`; no simulan.

| Fig. | Figura | Script | Datos |
|---|---|---|---|
| 4.1 | [Intermitencia_sitios](capitulo_4/Intermitencia_sitios.pdf) | [`fig_4_1_intermitencia_sitios.py`](capitulo_4/fig_4_1_intermitencia_sitios.py) | `10_sitios`, `10_sensibilidad_BM_planta`, `14_sustitutos_sitios` |
| 4.2 | [fig_curvas_reales](capitulo_4/fig_curvas_reales.pdf) | [`fig_4_2_curvas_reales.py`](capitulo_4/fig_4_2_curvas_reales.py) | `10_curvas`, `10_sitios`, `10_costo_planta_comun` |
| 4.3 | [fig_kappa_predictores](capitulo_4/fig_kappa_predictores.pdf) | [`fig_4_3_kappa_predictores.py`](capitulo_4/fig_4_3_kappa_predictores.py) | `10_sitios` |
| 4.4 | [fig_efecto_BM](capitulo_4/fig_efecto_BM.pdf) | [`fig_4_4_efecto_BM.py`](capitulo_4/fig_4_4_efecto_BM.py) | `11_comparacion_modelos`, `11_bootstrap_coeficientes`, `11_efecto_BM` |
| 4.5 | [Orden_dias](capitulo_4/Orden_dias.pdf) | [`fig_4_5_orden_dias.py`](capitulo_4/fig_4_5_orden_dias.py) | `14_sustitutos_sitios` |
| 4.6 | [Zonas_aplicacion](capitulo_4/Zonas_aplicacion.pdf) | [`fig_4_6_zonas.py`](capitulo_4/fig_4_6_zonas.py) | `15_zonas` |
| 4.7 | [fig_costo_confiabilidad](capitulo_4/fig_costo_confiabilidad.pdf) | [`fig_4_7_costo_confiabilidad.py`](capitulo_4/fig_4_7_costo_confiabilidad.py) | `10_costo_planta_comun`, `10_minimo_costo`, `10_sitios`, `10_sustitucion_planta_bateria` |
| 4.8 | [Reglas_resultados](capitulo_4/Reglas_resultados.pdf) | [`fig_4_8_reglas_operacion.py`](capitulo_4/fig_4_8_reglas_operacion.py) | `12_reglas`, `12_cota_lp`, `10_sitios` |

## Archivos comunes

- `estilo.py`: colores, tamaños y la función `guardar`.
- `comun_tesis.py` y `sitios_ilustrativos.py`: sitios sintéticos y simulador para las figuras de los capítulos 1 a 3.
- `resultados.py`: lee las tablas de resultados para el capítulo 4.
- `generar_todas.py`: corre todos los scripts.
