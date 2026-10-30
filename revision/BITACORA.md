# Bitácora del proyecto — Modelo de intermitencia PV + BESS

> Documento de traspaso. Contiene el estado, las decisiones tomadas, los
> hallazgos y los comandos exactos para retomar el trabajo desde otro
> computador. **Actualizar al final de cada sesión.**

- **Última actualización:** 2026-08-31
- **Estado:** Fases 0–7 implementadas, probadas y ejecutadas de punta a punta.
  31 tests pasando. Pipeline completo, figuras e informe PDF corriendo con
  `./run_todo.sh`; cuaderno reproducible disponible.

---

## 1. Cómo retomar desde otro computador

```bash
# 1. Ubicarse en la carpeta del proyecto
cd "ruta/a/Modelo intermitencia"

# 2. Si la carpeta viene de WhatsApp/AirDrop llega en solo lectura.
#    Darle permiso de escritura a los directorios (los .xlsx pueden
#    quedarse en solo lectura: eso protege los datos crudos).
chmod u+w . "5 series" "51 series" PSH

# 3. Crear el entorno e instalar dependencias
python3.12 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev,rapido,notebook]"

# 4. Verificar que todo está sano
./.venv/bin/python -m pytest tests/ -q          # deben pasar 31+ tests

# 5. Correr el pipeline
./.venv/bin/python pipeline/01_diagnostico.py
```

**Requisito de Python:** 3.11–3.12. Con 3.13/3.14 `numba` puede no tener
wheels; sin `numba` el código sigue funcionando (cae a NumPy puro) pero
la simulación es ~100× más lenta.

### Qué NO está en el repositorio

Los `.xlsx` de datos pesan 261 MB en total y no se movieron de su
ubicación original. `config.yaml` apunta a ellos con rutas relativas. Si
copias el proyecto a otra máquina, **copia también las tres carpetas de
datos** (`5 series/`, `51 series/`, `PSH/`).

El directorio `.cache/` contiene los Excel convertidos a pickle para no
releerlos (27 s → 0.3 s). Es regenerable: se puede borrar sin miedo.

---

## 2. Estructura del proyecto

```
Modelo intermitencia/
├── config.yaml              <- TODOS los parámetros. Ningún número mágico en el código.
├── pyproject.toml
├── BITACORA.md              <- este archivo
├── README.md
│
├── src/intermitencia/       <- el paquete
│   ├── config.py            Carga y valida config.yaml; resuelve la raíz del proyecto
│   ├── io_datos.py          Lectura robusta + caché + normalización de nombres
│   ├── pv.py                GHI -> generación; balance con la demanda
│   ├── almacenamiento.py    Simulación de SOC (numba) + pico secuente (Rippl)
│   ├── confiabilidad.py     LPSP estándar, cobertura de déficit, por año/periodo
│   ├── eventos.py           Eventos de déficit, B (Kim-Jo), M (Goh-Barabási)
│   ├── economia.py          CRF, LCOE, LCOS, costo marginal de ENS evitada
│   ├── dimensionamiento.py  Bisección para LPSP objetivo; óptimo 2-D (P_pv, E_bess)
│   ├── sustituto.py         Ley exponencial kappa(B,M) y regresión
│   └── viz.py               Estilo de figuras de la tesis + paleta validada
│
├── pipeline/                <- scripts numerados, se corren en orden
├── tests/                   <- pytest
├── resultados/              <- salidas (generado)
├── .cache/                  <- caché de lectura (generado, borrable)
│
└── legacy/                  <- los 7 scripts originales, sin tocar, como referencia
```

---

## 3. Hallazgos (en orden de gravedad)

### 3.1 La planta de 100 MW no puede servir 20 MW planos — CRÍTICO

Con PR = 0.80, la generación media de **las 51 series** está por debajo
de la demanda:

| | MW |
|---|---|
| Generación media mínima | 13.89 (La Reforma) |
| Generación media mediana | 17.46 |
| Generación media máxima | 19.43 (Cuestesitas) |
| Demanda | 20.00 |

**Series con generación media < demanda: 51 de 51.**

El balance energético anual es negativo, así que **ninguna capacidad de
batería alcanza alta confiabilidad**: el almacenamiento mueve energía en
el tiempo, no la crea. Se necesitan ~115 MW solo para equilibrar la
energía (mediana), y bastante más para tener excedente con el cual
cargar a través de rachas nubladas y pagar las pérdidas.

Esto explica por qué el modelo anterior necesitaba el heurístico
`conf_max * 0.99`: la curva de confiabilidad nunca llegaba cerca de 1, y
había que definir el "óptimo" relativo al máximo alcanzable en la grilla.

**Consecuencia:** el problema tiene que plantearse en 2-D sobre
`(P_pv, E_bess)`. Dimensionar solo la batería con la planta fija en
100 MW no tiene solución de alta confiabilidad.

### 3.2 El cálculo de B y M no medía intermitencia — CRÍTICO

El `ByM.py` original definía los eventos como cruces de la **suma
acumulada de excedentes** por múltiplos de `a_mu = P25(x)`.

- Una suma acumulada de una cantidad positiva es monótona: no tiene
  silencios ni ráfagas. La burstiness está definida para procesos
  puntuales; aplicarla aquí es un error de categoría.
- **Medido sobre los datos reales: el 49.0 % de los intervalos entre
  eventos son τ = 0**, porque un mismo paso cruzaba varios umbrales.
  Los τ = 0 no tienen sentido físico e inflan σ, empujando B hacia +1.
- `a_mu` se recalculaba por serie, así que cada sitio usaba una unidad
  distinta y los valores no eran comparables entre sitios.

**Impacto medido (serie Chinú):**

| | Método antiguo | Método nuevo |
|---|---|---|
| B | −0.041 | −0.599 |
| M | −0.374 | **+0.139** |

**El signo de M se invierte.** Los valores de B y M reportados hasta
ahora no son utilizables.

### 3.3 El objetivo de la regresión era un artefacto — CRÍTICO

`Modelo.py:461` definía la capacidad de referencia como la menor que
alcanza el 99 % de `conf_max`, donde `conf_max` es la confiabilidad en el
**extremo superior de la grilla** (`PORCENTAJE_MAX = 0.30`, escogido a
mano). Si se extiende la grilla, toda la variable objetivo se desplaza.

Se regresionaba B y M contra un artefacto de los límites del barrido.
Sustituido por: (a) pico secuente de Rippl como cota sin parámetros, y
(b) el óptimo económico donde el costo marginal iguala el VoLL.

### 3.4 El simulador era optimista — ALTO

Faltaban límite de potencia (se calculaba y nunca se usaba), eficiencias
(estaban en 1.0), DoD, autodescarga, vertimiento y conteo de ciclos.

**Impacto medido:** la cobertura de déficit cae **6.3 puntos
porcentuales** en promedio al corregirlo, a igual capacidad.

### 3.5 `LPSP` estaba mal definida — ALTO

Usaba `ENS / energía_de_déficit` en vez de `ENS / demanda_total`. Es una
métrica de cobertura válida, pero no es la LPSP de la literatura y no es
comparable. Ahora se reportan **las dos, con nombres distintos**:
`lpsp` y `cobertura_deficit`.

### 3.6 Inconsistencia de 20 % en el modelo FV — MEDIO

`área_total × 0.17` da **79.88 MW** de pico, no 100 MW. Un módulo de
550 W en 2.279 × 1.134 m tiene η = **21.3 %**, no 17 %.

En la práctica ese error equivalía a aplicar sin declararlo un
performance ratio de 0.799. Con `performance_ratio: 0.80` los resultados
coinciden dentro del 0.15 %, pero ahora el supuesto es explícito.
`modelo_legacy: true` reproduce el factor antiguo exacto.

### 3.7 Los nombres de serie estaban en Unicode NFD — MEDIO

Los `.xlsx` vienen de macOS con tildes descompuestas (`'Chinu' + U+0301`).
Se ven idénticas en pantalla pero no son iguales como cadenas. **21 de
las 51 series tienen tilde**, así que cualquier merge entre un archivo
NFD y uno NFC las descarta en silencio. Corregido con normalización NFC
en `io_datos.normalizar_nombre`.

### 3.8 Los resultados "antes vs después" eran in-sample — MEDIO

`Modelo.py:784` predecía sobre los mismos datos con que se ajustó. Hay
que usar `predicciones_loo`, que ya se calculaba pero no se usaba para
el reporte.

### 3.9 La figura del mapa de calor no correspondía al modelo — MEDIO

`Graficasmodelo.py` tiene los coeficientes quemados (`a=-3.7991, ...`) y
usa `LI=0.30, LS=0.50`, mientras `Modelo.py` usa `CAP_MIN=0.1,
CAP_MAX=1.0`. La figura dibuja `0.30 + 0.20·σ(z)` y el modelo produce
`0.10 + 0.90·σ(z)`.

### 3.10 Otros

- Eje dual en `Capacidad inicial.py:131`: el eje derecho (MWh) no es una
  reetiquetación lineal del izquierdo (%) porque la conversión depende de
  la PSH, que varía por serie. Es engañoso.
- `ByM.py:257` usaba `spearmanr` sin importarlo → `NameError`.
- `ByM.py:14` leía de `"51 seriesH/"` (carpeta inexistente).
- `calculo_psh.py:9` creaba una columna `date` muerta e indexaba por la
  columna sin convertir.
- `Modelo.py` leía las series sin `pd.to_datetime` → posible orden
  lexicográfico, y la simulación depende del orden.
- `promedio_BM_por_serie.xlsx` tiene **53 filas para 51 series**.
- `SEMILLA = 42` nunca se usaba; 5 imports de sklearn sin usar.

---

## 4. Decisiones tomadas

| Decisión | Razón |
|---|---|
| Datos crudos **no se mueven** | Pesan 261 MB; `config.yaml` apunta a su ubicación. |
| Los `.xlsx` quedan en solo lectura | Protege los datos de una sobrescritura accidental. |
| Caché en pickle, no parquet | Evita la dependencia de `pyarrow`. Regenerable. |
| `numba` es **opcional** | Si no hay wheels el código corre igual, solo más lento. |
| Se conserva `burstiness_legacy_cruces` | Permite cuantificar en la tesis cuánto cambian B y M. |
| Se conserva `modelo_legacy` en el FV | Permite reproducir resultados previos bit a bit. |
| Se reportan **ambas** métricas de confiabilidad | `lpsp` para comparar con literatura, `cobertura_deficit` para continuidad. |
| Costos como **placeholders marcados** | No se inventan cifras regulatorias; van marcados `# REVISAR`. |

---

## 5. Estado por fase

| Fase | Descripción | Estado |
|---|---|---|
| 0 | Reproducibilidad: paquete, config, caché, tests | ✅ Hecho |
| 1 | Fidelidad del simulador (potencia, η, DoD, vertimiento, ciclos, numba) | ✅ Hecho |
| 2 | Métricas correctas (LPSP estándar, por año, pico secuente) | ✅ Hecho |
| 3 | B y M bien definidas (eventos, Kim-Jo, Fisher-z) | ✅ Hecho |
| 4 | Óptimo económico (CRF, LCOE, LCOS, VoLL, óptimo 2-D) | ✅ Hecho |
| 5 | Modelo sustituto κ(B,M) | ✅ Hecho |
| 6 | Figuras | ✅ 7 figuras generadas |
| 7 | Informe PDF y cuaderno reproducible | ✅ Generados y verificados |

### Rendimiento

Simulación de 27 años (236 520 pasos): **0.0027 s** con numba, frente a
un bucle de Python. Esto es lo que hace viable el barrido 2-D.

---

## 5b. Resultados obtenidos

### Óptimo económico (paso 04)

Resolviendo en 2-D sobre `(P_pv, E_bess)`, con convergencia en las 51 series:

| | Diseño anterior | Óptimo económico (mediana) |
|---|---|---|
| Planta | 100 MW (fija) | **151 MW** (rango 131–198) |
| Batería | se barría 5–30 % de la energía diaria | **335 MWh = 53 %** (rango 51–56 %) |
| Batería en horas de demanda | — | 16.7 h |
| LPSP | ~23 % (techo alcanzable) | **2.8 %** |
| LCOE | — | 240 USD/MWh |
| Vertimiento | no se contabilizaba | 21 % |

**El óptimo nunca estuvo dentro del rango de búsqueda anterior.** Se
barría 5–30 % y el óptimo está en 53 %.

### Ley exponencial y modelo sustituto (paso 05)

`LPSP(E) ≈ L₀·exp(−E/κ)` se sostiene con **R² mediana 0.92** (12 de 51
series superan 0.95). Es una buena aproximación de primer orden, no una
ley exacta: la curvatura residual sugiere que una exponencial estirada
`exp(−(E/κ)^β)` ajustaría mejor si se necesita más precisión.

Regresión (planta común de referencia, 150 MW):

```
ln κ = 11.80 + 0.384·B + 0.484·M − 1.253·PSH
R²_LOO = 0.709      mejora sobre el baseline de la media: +47.1 %
corr(ln κ, B) = +0.77    corr(ln κ, M) = −0.57    corr(ln κ, PSH) = −0.87
```

Los signos son físicamente correctos: más burstiness exige más
almacenamiento, más recurso exige menos.

#### Hallazgo metodológico importante

Si κ se calcula en la planta **óptima de cada serie**, el modelo
sustituto **falla** (R²_LOO = −0.04, peor que predecir la media, y todas
las correlaciones con |r| < 0.13). A planta **común** funciona
(R²_LOO = 0.71).

La razón: sobredimensionar la planta es un sustituto de tener
almacenamiento. Al optimizar la planta por sitio, el dimensionamiento
absorbe las diferencias de intermitencia y κ queda casi constante
(CV pasa de 0.75 a ~0.1). **Para aislar el efecto de la intermitencia hay
que comparar los sitios con la misma planta.** Esto está configurado en
`sustituto.planta_referencia_mw`.

### Figuras generadas (paso 06)

Todas en `resultados/figuras/` como PNG (revisión) y PDF (LaTeX).
Ninguna tiene coeficientes quemados: se construyen desde los resultados
en disco.

| Figura | Contenido |
|---|---|
| F1 | B y M: método anterior vs corregido, con la recta identidad |
| F2 | Curvas capacidad–confiabilidad (cobertura y LPSP en log) |
| F3 | **Mapa LCOE(P_pv, E_bess)** con isolíneas de LPSP y el óptimo |
| F4 | **κ vs B, M y PSH** — el vínculo intermitencia → almacenamiento |
| F5 | Predicho vs observado **fuera de muestra** (LOO) |
| F6 | Óptimos por serie contra el rango que se barría antes |
| F7 | Frente de Pareto costo–confiabilidad |

Sobre la paleta: los colores del gráfico de B y M original (`#fee08b`,
`#abd9e9`) reprueban la validación de accesibilidad (fuera de la banda de
luminancia, el azul lee como gris, contraste 1.26:1 y 1.48:1 contra un
mínimo de 3:1). Reemplazados por `#2a78d6` / `#eb6834` / `#1baf7a`, que
pasan las seis verificaciones.

---

## 6. Pendientes

Por orden de importancia:

1. **Reemplazar los costos marcados `# REVISAR` en `config.yaml`** por
   valores citados (NREL ATB 2024 para CAPEX/OPEX; resolución CREG
   vigente para el VoLL / costo incremental de racionamiento).
   Mientras tanto, **ninguna cifra de LCOE u óptimo es publicable**: los
   tamaños óptimos dependen directamente del VoLL y del CAPEX.
2. **Decidir con el director de tesis qué hacer con el hallazgo 3.1.**
   O se acepta sobredimensionar la planta (~1.5×), o se baja la demanda
   objetivo, o se admite explícitamente que el sistema es de aporte
   parcial y no de suministro firme. Es una decisión de alcance, no
   técnica, y condiciona todo lo demás.
3. **Aplicar el modelo a las 5 zonas** (`5 series/`). El paquete ya lo
   soporta; falta el script `07_aplicacion_5_zonas.py` que lea
   `5 series/5 series GHI juntas.xlsx` y aplique el sustituto ajustado.
4. **Clasificar los años por fase ENSO (ONI)** y reportar confiabilidad
   por fase. `confiabilidad.evaluar_por_periodo` ya devuelve el detalle
   año por año; solo falta unir con la serie ONI del capítulo climático.
   Es la conexión natural con la tesis madre y probablemente el
   resultado más vendible.
5. Probar la exponencial estirada `exp(−(E/κ)^β)` si se necesita más
   precisión que el R² ≈ 0.92 actual.
6. Recalcular la PSH con `calculo_psh.py` corregido y verificar contra
   `PSH_resultados.xlsx` (el paso 01 ya reporta la discrepancia máxima).
7. Revisar por qué `promedio_BM_por_serie.xlsx` tiene 53 filas para 51
   series (probablemente mezcla subestaciones con zonas).

---

## 7. Registro de sesiones

### 2026-08-31 — Sesión 1

- Revisión completa de los 7 scripts originales.
- Creado el entorno (`.venv`, Python 3.12) e instaladas las dependencias.
- Implementadas las fases 0–4: `config`, `io_datos`, `pv`,
  `almacenamiento`, `confiabilidad`, `eventos`, `economia`,
  `dimensionamiento`.
- 31 tests pasando, incluyendo casos con solución analítica
  (Rippl, conservación de energía, monotonía de la curva).
- Hallazgos 3.1 a 3.10 documentados y, donde aplica, medidos sobre los
  datos reales.
- Implementadas y ejecutadas las fases 5 y 6: `sustituto.py`, `viz.py`,
  los 6 pasos del pipeline y las 7 figuras.
- Descubierto el efecto de la planta de referencia sobre el modelo
  sustituto (ver sección 5b): el resultado pasa de R²_LOO = −0.04 a
  +0.71 según se compare a planta óptima o a planta común. Es el
  hallazgo metodológico más sutil de la sesión y estuvo a punto de
  quedar registrado como un resultado negativo falso.

### 2026-08-31 — Sesión 2

- Auditada esta bitácora contra una ejecución nueva y los archivos de
  resultados. Se corrigieron tres cifras desactualizadas: fracción de
  `tau = 0` (49.0 %), valores legacy de Chinú y número de series con
  R² exponencial mayor que 0.95 (12 de 51).
- Ejecutadas las 31 pruebas y los siete pasos. El flujo terminó sin errores.
- Corregida la reproducibilidad de `run_todo.sh`: Matplotlib y Fontconfig
  usan cachés locales, backend `Agg`, y el paso 07 ahora forma parte del flujo.
- Declaradas las dependencias del informe y del cuaderno en `pyproject.toml`.
- Creado y ejecutado `Modelo_intermitencia_explicado.ipynb`: 28 celdas,
  13 celdas de código ejecutadas y cero errores; conserva tablas y figuras.
- Generado y revisado visualmente `resultados/Informe_intermitencia.pdf`:
  9 páginas A4. Se incrustó DejaVu Sans para fórmulas Unicode y se corrigió
  el ajuste de texto de la tabla de hallazgos.

### Plantilla para la próxima sesión

```
### AAAA-MM-DD — Sesión N

- Qué se hizo:
- Qué se decidió y por qué:
- Qué quedó a medias:
- Siguiente paso concreto:
```
