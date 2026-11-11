# Figuras de resultados (capítulo 4 y artículo 2)

Scripts de las figuras que muestran resultados de las 51 series. **No
simulan**: leen las tablas de `codigo/resultados/articulo2/` que dejan los
pasos 10 a 14 del pipeline. Usan el mismo estilo que `figuras/estilo.py`.

| Script | Figura | Lee |
|---|---|---|
| `fig_a2_7_curvas_reales.py` | `fig_curvas_reales` | `10_curvas.csv.gz`, `10_sitios.xlsx` |
| `fig_a2_8_kappa_predictores.py` | `fig_kappa_predictores` | `10_sitios.xlsx` |
| `fig_a2_9_costo_confiabilidad.py` | `fig_costo_confiabilidad` | pasos 10 y 13 |
| `fig_a2_10_efecto_BM.py` | `fig_efecto_BM` | pasos 10 y 11 |
| `fig_4_5_orden_dias.py` | `Orden_dias` | `14_sustitutos_sitios.xlsx` |

Correr desde la raíz del repositorio, por ejemplo:

```bash
python codigo/figuras_resultados/fig_a2_7_curvas_reales.py
```

Salen en `codigo/figuras_resultados/salida/` (no se sube a GitHub).
