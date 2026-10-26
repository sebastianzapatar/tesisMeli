# AGENTS.md — Instrucciones para agentes que trabajen en este repositorio

Proyecto de tesis doctoral (Universidad EIA). Dimensionamiento de PV + BESS a
partir de métricas de intermitencia (burstiness B y memory M) de series
solares, con criterio económico. Autora: Melisa Tuirán. Director: Sebastián Zapata.

**Antes de hacer cualquier cosa, lee en este orden:**

1. `REVISION_TESIS.md`: revisión del 2026-10-25. Cada tarea de abajo
   referencia un ID de allí (P = propuesta, C = código).
2. `BITACORA.md`: estado, decisiones y hallazgos anteriores.
3. `config.yaml`: todos los parámetros. No escribas números mágicos en el código.

## Entorno

```bash
python3.12 -m venv .venv                      # ya existe si alguien lo creó
./.venv/bin/python -m pip install -e ".[dev,rapido,notebook]"
./.venv/bin/python -m pytest tests/ -q        # 31 tests, deben pasar siempre
./run_todo.sh                                 # pipeline completo (requiere datos)
./.venv/bin/python experimentos/sintetico_resolucion_BM.py   # no requiere datos
```

- Python 3.11–3.12. Con 3.13+ puede que numba no tenga wheels.
- **Los datos NO están en el repositorio** (ver `DATOS.md`). Los pasos 01–07
  necesitan `51 series/df_series_todas_las_subestaciones.xlsx`,
  `PSH/PSH_resultados.xlsx` y los archivos de `5 series/`. Si faltan, trabaja con
  datos sintéticos y tests, y dilo en tu reporte. **Nunca inventes resultados de
  las 51 series.**

## Reglas

- **Idioma:** código, comentarios, nombres y documentos en español, con el
  estilo existente (docstrings que explican el *porqué*, nombres como
  `capacidad_mwh` o `metricas_intermitencia`).
- **No modifiques `legacy/`.** Es la referencia del modelo anterior.
- **No inventes costos ni valores regulatorios.** Los valores marcados
  `# REVISAR` se reemplazan solo con una fuente citada en el comentario (autor,
  año, tabla). Si no tienes la fuente, deja el `# REVISAR` y repórtalo.
- **Cada cambio metodológico se hace configurable** en `config.yaml`, y el
  comportamiento anterior se conserva como opción, para poder comparar en la tesis.
- **Cada función nueva lleva su test** en `tests/`. Si es posible, usa un caso
  con solución analítica.
- **Al terminar una sesión**, agrega una entrada en `BITACORA.md §7` con la
  plantilla que está allí y actualiza `§6 Pendientes`.
- **Git:** trabaja en una rama (`git checkout -b <tarea>`), con un commit por
  tarea. No hagas push ni abras PR sin que el usuario lo pida. No subas Excel
  ni PDFs de terceros.

## Backlog de tareas (en orden de prioridad)

Estados: `[ ]` pendiente · `[~]` en curso · `[x]` hecha · `[B]` bloqueada por una decisión humana.

### Bloque A: validez de la métrica (crítico; hacerlo primero)

- [ ] **A1 (C1): resolución diaria como análisis principal.**
  En `pipeline/02_intermitencia.py`, calcula B y M en las dos resoluciones
  siempre: columnas `B_horaria`, `M_horaria`, `B_diaria`, `M_diaria`. La
  configuración decide cuál se usa aguas abajo como `B` y `M`. Pon
  `intermitencia.resolucion: "diaria"` por defecto. Corrige que el bucle por
  hora del día solo tiene sentido en modo horario.
  *Aceptación:* un test en `tests/test_eventos.py` reproduce el patrón del
  experimento sintético. Con kt fijo, `B_diaria` crece con φ; con φ fijo,
  `|B_diaria(kt=0.55) − B_diaria(kt=0.75)| < 0.05`.
- [ ] **A2 (C1, robustez): eventos sobre el índice de claridad.**
  Agrega en `eventos.py` una función que construya kt diario
  (GHI diario / GHI despejado diario). El modelo de cielo despejado debe ir
  en `pv.py` y ser configurable; para empezar basta un percentil alto por día
  del año. Ofrece `base_evento: "claridad"` en la configuración.
  *Aceptación:* test con una serie sintética de kt conocido.
- [ ] **A3 (C4): misma planta para B, M y κ.**
  B y M deben calcularse con `sustituto.planta_referencia_mw`, no con
  `planta.potencia_mw`. Agrega a `05_sustituto.py` una tabla de la sensibilidad
  de B y M al tamaño de planta (100, 125, 150 y 200 MW).
  *Aceptación:* salida `05_sensibilidad_BM_planta.xlsx`.
- [ ] **A4 (C2): valor incremental de B y M sobre la PSH.**
  En `sustituto.py`, agrega `comparar_modelos(df, especificaciones)`, que
  devuelve R²_LOO, RMSE_LOO, AIC y la prueba F parcial frente al modelo anidado.
  Especificaciones mínimas: `[PSH]`, `[PSH, B]`, `[PSH, B, M]`,
  `[PSH, CV_diario]`, `[PSH, racha_max_nublada]`, `[PSH, ac1_kt]`. Calcula esos
  baselines en el paso 02.
  *Aceptación:* `05_comparacion_modelos.xlsx` y una figura nueva en el paso 06.
  **Reporta el resultado tal cual, aunque B no gane:** es el punto de
  decisión de la tesis.
- [ ] **A5 (C3): validación espacial.**
  Agrega CV por bloques (agrupa los sitios por región o por k-means de
  coordenadas; las coordenadas deben venir de los datos, y si no existen, la
  tarea queda `[B]`), bootstrap de coeficientes (≥ 2000 réplicas, usa
  `proyecto.semilla`) y el VIF.
  *Aceptación:* tabla con IC del 95 % por coeficiente.
- [ ] **A6 (C5): exponencial estirada.**
  Agrega a `ajustar_kappa` la forma `exp(−(E/κ)^β)` y compara con AIC.
  Expón el error estándar de κ.

### Bloque B: economía y formulación

- [B] **B1 (C6): costos citados.** Requiere fuentes (NREL ATB, UPME/CREG,
  WACC CREG) entregadas por el usuario o verificadas en línea con cita
  completa. Mientras tanto, implementa B2 a B5.
- [ ] **B2 (C7): nombres de costos.** Separa `lcoe_tecnico_usd_mwh` (sin VoLL),
  `costo_ens_usd_mwh` y `costo_total_usd_mwh`. Actualiza los pasos 03–07 y el
  informe. Si 06 o 07 leen las columnas por nombre, mantén compatibilidad o
  actualízalos.
- [ ] **B3 (C8): potencia del BESS.** Agrega `bess.modo_potencia:
  "duracion" | "optimizada" | "demanda"` en la configuración. En
  `"optimizada"`, `optimizar_sistema` busca sobre (P_pv, E_bess, P_bess).
- [ ] **B4 (C10): vida por ciclos y degradación.** Calcula
  vida_bess = mín(vida_bess_anios, ciclos_vida / ciclos_por_año) y agrega
  degradación lineal configurable (`bess.degradacion_frac_anio`) y precio de
  venta del vertimiento (`economia.precio_venta_excedente_usd_mwh`, 0 por defecto).
- [ ] **B5: análisis de sensibilidad.** Agrega el paso
  `pipeline/04b_sensibilidad.py`, un tornado de P_pv*, E_bess* y costo total
  frente a ±30 % de VoLL, CAPEX del BESS, CAPEX FV y tasa de descuento.
- [B] **B6 (C9): alcance del servicio.** Esperar la decisión de
  `REVISION_TESIS.md §5.1`. Deja preparada la demanda como serie (perfil
  horario desde archivo) además del valor plano: `demanda.perfil: null | ruta`.

### Bloque C: resultados nuevos

- [ ] **C1 (C14): ENSO.** Agrega `pipeline/08_enso.py`, que lee la serie ONI
  de NOAA CPC. La URL y la fecha de descarga van en la configuración, y el CSV
  se guarda en `datos_externos/`. Clasifica cada año (o cada DEF) en Niño,
  Niña o neutro, calcula B, M y LPSP por año con `evaluar_por_periodo` (con
  la planta y la batería óptimas y la de referencia), y compara las
  distribuciones por fase con Kruskal-Wallis y tamaño de efecto.
  *Aceptación:* tabla, figura y una entrada en el informe.
- [ ] **C2 (C14): aplicación a 5 zonas.** Agrega
  `pipeline/09_aplicacion_5_zonas.py`. Aplica el sustituto ajustado a
  `5 series/5 series GHI juntas.xlsx`, compara κ predicho con κ simulado y
  marca las extrapolaciones fuera del rango de entrenamiento.
- [ ] **C3: estrategias de operación (P6).** Agrega en `almacenamiento.py`
  despachos alternativos: reserva mínima de SOC por hora y una cota de
  previsión perfecta (LP con `scipy.optimize.linprog` en ventanas). El
  arbitraje con precios de XM queda `[B]` hasta tener la serie de precios.

### Bloque D: calidad y documentación

- [ ] **D1 (C12):** tests para `economia` (CRF tabulado, factor de reemplazos),
  `dimensionamiento` (bisección contra una grilla densa), `sustituto`
  (recupera κ y los coeficientes de datos sintéticos), `confiabilidad`
  (LPSP = ENS/demanda) y `pv`.
- [ ] **D2 (C13):** corrige el README. El r = −0.64 es solo de M; para B,
  r = +0.91.
- [ ] **D3 (C11):** completa `DATOS.md` con la fuente de la GHI, el periodo,
  la zona horaria y la licencia. Pide estos datos al usuario: **no los deduzcas**.
- [ ] **D4 (C15):** elimina los duplicados `51 series/*.py` y
  `PSH/calculo_psh.py`, que son idénticos a `legacy/`. Confírmalo con
  `diff -rq` y pide confirmación antes de borrar.
- [ ] **D5:** CI mínimo en `.github/workflows/tests.yml` (pytest en 3.12,
  sin datos).

### Bloque E: documentos de la tesis (requieren a la estudiante)

Un agente puede preparar borradores, pero no reemplaza el criterio de la
autora ni del director.

- [ ] **E1 (P1–P3, P10):** borrador de la nueva §6 de la propuesta (eventos
  de déficit, M de Pearson, LPSP energética, resolución diaria) en
  `docs/propuesta_v2_seccion6.md`.
- [ ] **E2 (P8):** verifica cada referencia de la propuesta contra su DOI
  (Crossref) y entrega una tabla con OK, DOI erróneo o cita que no
  corresponde, más un reemplazo sugerido. Las citas dudosas conocidas son
  Kuray 2020, Oryani 2021, Monsef 2019, Shi 2014, Yin 2020 (DOI) y Carrière
  2019 (DOI).
- [ ] **E3 (P7):** inventario de las figuras que hay que redibujar: 2.2, 2.4,
  3.1, 3.2 (tiene la marca de licencia de IEEE), 6.5 y la Ec. 6.2.
- [ ] **E4:** esqueleto del artículo 2 en `docs/articulo2_esqueleto.md`,
  siguiendo `REVISION_TESIS.md §7`.

## Hechos establecidos (no los vuelvas a investigar)

- Con 100 MW, ninguna de las 51 series cubre 20 MW planos (generación media
  mediana 17.46 MW).
- El método de cruces antiguo da 49 % de τ = 0; está en
  `eventos.burstiness_legacy_cruces` solo para comparar.
- A planta óptima, κ no tiene señal (R²_LOO = −0.04); a planta común de
  150 MW, R²_LOO = 0.71. Ese resultado se obtuvo con B **horaria** y hay que
  rehacerlo tras A1–A4.
- Experimento sintético (`experimentos/sintetico_resolucion_BM.py`): la B
  horaria sigue a la PSH y la B diaria sigue a la persistencia.
- El artículo SLR (Tuirán et al. 2026, *Energies* 19, 4100) está publicado;
  no se edita.
- La pasantía en la UFSC (Florianópolis) ya se hizo. Produjo el artículo
  Tuirán, Vaz, Uriona Maldonado y Zapata (2026), *Atmosphere* 17(10), 1007,
  doi:10.3390/atmos17101007, sobre XCO2 y variables climáticas en Brasil.
  Está publicado; no se edita.

## Formato del reporte al terminar

1. Qué tareas se cerraron (ID), con los archivos tocados.
2. Resultados numéricos nuevos, indicando si son con datos reales o sintéticos.
3. Tests: cuántos pasan, y la salida si alguno falla.
4. Qué quedó bloqueado y qué decisión humana hace falta.
