# Modelo de intermitencia — dimensionamiento PV + BESS

Dimensionamiento de plantas solares con almacenamiento a partir de métricas
de intermitencia (burstiness *B* y memory *M*) de las series de irradiancia,
con criterio económico.

> **Para retomar el trabajo desde otro computador, lee
> [`BITACORA.md`](BITACORA.md)**: contiene el estado, las decisiones, los
> hallazgos y los comandos de instalación.

---

## Instalación

```bash
python3.12 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev,rapido,notebook]"
./.venv/bin/python -m pytest tests/ -q      # 31 tests
```

Python 3.11–3.12. `numba` es opcional: sin él todo funciona, pero la
simulación es ~100× más lenta.

## Cómo correr

```bash
./run_todo.sh                                   # el pipeline completo
# o paso a paso:
./.venv/bin/python pipeline/01_diagnostico.py
./.venv/bin/python pipeline/02_intermitencia.py
./.venv/bin/python pipeline/03_curvas.py
./.venv/bin/python pipeline/04_optimo.py
./.venv/bin/python pipeline/05_sustituto.py
./.venv/bin/python pipeline/06_figuras.py
./.venv/bin/python pipeline/07_informe.py
```

Todos los parámetros están en [`config.yaml`](config.yaml). **No hay
números mágicos en el código**: para cambiar un supuesto se edita ese
archivo y se vuelve a correr.

## Qué hace cada paso

| Paso | Qué responde | Salidas |
|---|---|---|
| `01_diagnostico` | ¿Los datos están sanos? ¿El problema tiene solución? | `01_diagnostico_series.xlsx` |
| `02_intermitencia` | *B* y *M* corregidas, y cuánto cambian frente al método anterior | `02_intermitencia.xlsx`, `02_comparacion_metodos.xlsx` |
| `03_curvas` | Curvas capacidad–confiabilidad, costo marginal, variabilidad interanual | `03_curvas.xlsx`, `03_marginal.xlsx`, `03_interanual.xlsx` |
| `04_optimo` | Tamaño óptimo **conjunto** de planta y batería | `04_optimos.xlsx`, `04_grilla.xlsx`, `04_pareto.xlsx` |
| `05_sustituto` | ¿*B* y *M* predicen el almacenamiento necesario? | `05_kappa.xlsx`, `05_sustituto_coeficientes.xlsx` |
| `06_figuras` | Figuras para la tesis | `resultados/figuras/*.{png,pdf}` |
| `07_informe` | Informe técnico autocontenido | `resultados/Informe_intermitencia.pdf` |

El cuaderno [`Modelo_intermitencia_explicado.ipynb`](Modelo_intermitencia_explicado.ipynb)
permite recorrer, recalcular y mostrar el análisis de forma interactiva. Para
abrirlo:

```bash
./.venv/bin/python -m jupyter lab Modelo_intermitencia_explicado.ipynb
```

## Resultados principales

**El problema anterior no tenía solución.** Con la planta fija en 100 MW,
las 51 series generan en promedio menos que la demanda de 20 MW (mediana
17.5 MW). El balance energético anual es negativo, así que ninguna batería
alcanza alta confiabilidad. Por eso el modelo anterior necesitaba un
heurístico (`conf_max × 0.99`) para definir un óptimo.

**El óptimo económico está fuera del rango que se buscaba.** Resolviendo en
2-D sobre (planta, batería):

| | Anterior | Óptimo económico |
|---|---|---|
| Planta | 100 MW (fija) | **151 MW** (mediana) |
| Batería | se buscaba en 5–30 % de la energía diaria | **53 %** (335 MWh) |
| LPSP | ~23 % (techo alcanzable) | **2.8 %** |

**Las métricas de intermitencia anteriores no eran utilizables.** El 49 % de
los intervalos entre eventos del método antiguo eran τ = 0 (un artefacto de
medir cruces sobre una suma acumulada monótona). *M* cambia de signo en 47
de las 51 series, y la correlación entre el método antiguo y el corregido es
**negativa** (r = −0.64): el ranking estaba invertido.

**La intermitencia sí predice el almacenamiento, pero a planta común.**
Ajustando `LPSP(E) ≈ L₀·exp(−E/κ)` (R² ≈ 0.92) y regresando κ:

```
ln κ = 11.80 + 0.384·B + 0.484·M − 1.253·PSH        R²_LOO = 0.71  (+47 % vs. baseline)
```

Con más burstiness hace falta más almacenamiento; con más recurso, menos.
Comparadas en **su propia planta óptima** las series pierden esa señal
(κ casi constante): sobredimensionar la planta es un sustituto de tener
batería, así que hay que comparar a planta común para aislar el efecto.

## Estructura

```
config.yaml            todos los parámetros
src/intermitencia/     el paquete (ver BITACORA.md para el detalle de cada módulo)
pipeline/              scripts numerados
tests/                 pytest
legacy/                los 7 scripts originales, sin modificar
resultados/            salidas y figuras
```

Los datos crudos (261 MB) permanecen en `5 series/`, `51 series/` y `PSH/`.
No se movieron; `config.yaml` apunta a ellos. Los Excel están excluidos de Git:
consulta [`DATOS.md`](DATOS.md) para saber cuáles son realmente necesarios y
cómo compartirlos sin inflar el repositorio.

## Advertencia sobre los costos

Los valores económicos de `config.yaml` están marcados `# REVISAR`. Son
placeholders de orden de magnitud razonable, **no fuentes citables**.
Reemplázalos por los tuyos (NREL ATB 2024 para CAPEX/OPEX; la resolución
CREG vigente para el costo incremental de racionamiento) antes de publicar
cualquier cifra de LCOE u óptimo.
