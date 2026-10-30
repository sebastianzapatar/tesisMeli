# Revisión integral: propuesta, código y artículo en *Energies*

**Tesis:** *Desarrollo de una metodología para el dimensionamiento de los BESS considerando la intermitencia de la generación fotovoltaica*. Melisa Tuirán Ruiz, Doctorado en Ingeniería, Universidad EIA.
**Director:** Sebastián Zapata Ramírez. **Fecha de la revisión:** 2026-10-25.
**Material revisado:**

- `Propuesta de tesis_Melisa_Turián.pdf` (33 p., 2025, con comentarios en portugués de la coorientación).
- Repositorio `github.com/sebastianzapatar/tesisMeli`: paquete `src/intermitencia/`, pipeline `01–07`, tests, `BITACORA.md` e informe técnico.
- Tuirán et al. (2026), *Photovoltaic Intermittency Representation in Battery Sizing: A Systematic Literature Review*, *Energies* 19, 4100, publicado el 31/08/2026.

> Los Excel de datos (261 MB) no están en el repositorio, así que no se pudo
> volver a correr el pipeline con las 51 series reales. Lo que sí se verificó:
> los 31 tests pasan (Python 3.12) y se corrió un experimento sintético sobre
> las métricas B y M (`experimentos/sintetico_resolucion_BM.py`, sección 2.1).

---

## Resumen ejecutivo: las cinco cosas que más importan

1. **B a resolución horaria mide sobre todo cuánto sol hay (PSH), no la
   intermitencia.** Con demanda plana, cada noche es un evento de déficit, así
   que los intervalos entre eventos quedan dominados por el ciclo de 24 h. En
   el experimento sintético, la B horaria cambia con la claridad media del cielo
   y casi nada con la persistencia de los días nublados, que es justamente lo
   que define la batería necesaria. La B diaria se comporta al revés, que es
   lo deseable. Esto amenaza la afirmación central de la tesis (que B y M
   predicen el almacenamiento) y hay que resolverlo antes de escribir el artículo
   de resultados. El código ya tiene la opción (`intermitencia.resolucion: "diaria"`).
2. **Falta demostrar que B y M aportan algo más allá de la PSH.** En el modelo
   actual, la PSH sola tiene r = −0.87 con ln κ. Hay que comparar un modelo
   con solo PSH contra uno con PSH + B + M, y contra indicadores sencillos
   (coeficiente de variación de la energía diaria, rachas de días nublados).
   Sin esa comparación, un revisor dirá que B es un proxy de la PSH.
3. **Hay que definir el alcance del sistema, porque condiciona todo lo demás.**
   Una planta de 100 MW no alcanza a abastecer 20 MW planos en ninguna de las 51
   series. El óptimo económico (151 MW de planta y 16.7 h de batería) describe un
   problema de almacenamiento de larga duración que el Li-ion no atiende
   bien. Esta decisión debe tomarse en conjunto con el director (sección 5).
4. **La propuesta ya no describe lo que se hizo.** La sección 6.1.3 (tiempos
   entre arribos sobre la suma acumulada), la definición de M con Spearman y la
   LPSP como "fracción del tiempo" no coinciden con el código. Además, quedan
   pendientes los comentarios de la coorientación y hay figuras copiadas como
   capturas de pantalla. Una de ellas conserva la marca de licencia de IEEE Xplore.
5. **El cronograma va atrasado y el artículo publicado no conecta con B y M.**
   El objetivo 2 está al 20 % y el artículo de resultados al 0 %, en el semestre
   en que debían cerrarse. La revisión sistemática nunca menciona *burstiness*
   ni *memory*. El próximo artículo tiene que tender ese puente de forma explícita (sección 3).

---

## Lo que está bien (y conviene conservar)

- **El código se reconstruyó con criterio.** Tiene configuración única
  (`config.yaml`) y un simulador con límite de potencia, eficiencias, DoD y
  vertimiento, compilado con numba. Usa la LPSP estándar, la corrección de
  Kim & Jo (2016) para B, la M de Goh & Barabási con medias separadas y la
  agregación de Fisher. La validación LOO se compara contra un baseline
  explícito, y los 31 tests incluyen casos analíticos.
- **Los hallazgos sobre el modelo anterior son sólidos y están medidos**
  (`BITACORA.md` §3). El balance energético era negativo, el objetivo de la
  regresión era un artefacto de la grilla, el simulador era optimista y la
  LPSP estaba mal definida.
- **El hallazgo de la "planta común" es una buena idea de tesis.** Si cada
  sitio se compara en su planta óptima, la señal de intermitencia desaparece,
  porque sobredimensionar la planta sustituye a la batería. Este resultado
  merece una sección propia en el artículo.
- **El artículo en *Energies* está publicado y es útil.** Sustenta la brecha de
  investigación con PRISMA 2020 y 36 estudios, y sus conclusiones (sección 5.3)
  piden explícitamente lo que la tesis hace: indicadores de duración,
  persistencia, frecuencia, severidad y agrupamiento de los eventos de déficit.

---

## 1. Propuesta de tesis: qué falta y cómo solucionarlo

| # | Problema | Dónde | Cómo solucionarlo | Prioridad |
|---|---|---|---|---|
| P1 | La metodología de §6.1.3 (tiempos entre arribos sobre la suma acumulada, con múltiplos de a_μ) produjo 49 % de τ = 0 en los datos reales. El código la reemplazó por eventos de déficit, pero la propuesta no lo dice. | §6.1.3, Figs. 6.6–6.8 | Reescribir §6.1.3 explicando el cambio. **Matiz importante:** el método de Schleiss & Smith (2016) es válido en lluvia, porque interpola la curva acumulada para obtener tiempos de cruce fraccionarios y usa un umbral mayor que el incremento por paso. El defecto fue de implementación y de resolución (cruces múltiples en un paso, a_μ = P25), no del concepto. Presentarlo así protege los trabajos de ELAEE y CLH 2024. | Alta |
| P2 | M se define como autocorrelación de **Spearman**; Goh & Barabási usan **Pearson**, y el código también. | §6.1.2 | Usar Pearson como definición y Spearman como análisis de robustez declarado. | Alta |
| P3 | LOLP y LPSP se definen ambas como "fracción del tiempo". El código usa la LPSP energética (ENS/demanda) y LOLH como fracción de horas. | §1, §2.2 | Definir con ecuaciones: LPSP = ΣENS/ΣD (energía) y LOLP/LOLH (tiempo). Mantener las mismas definiciones en propuesta, código y artículos. | Alta |
| P4 | No se describe el sistema de estudio: 51 subestaciones (¿de ISA?), 27 años horarios de GHI, fuente de datos, demanda de 20 MW, planta de 100 MW, si el sistema es aislado o conectado a la red. | §6 | Agregar una subsección "Caso de estudio y datos" con fuente, periodo, resolución, zona horaria, tratamiento de faltantes, mapa de sitios y la decisión de alcance (sección 5). | Alta |
| P5 | Los objetivos no corresponden con las preguntas ni con la metodología. El objetivo general habla de "infraestructura". La actividad 06 (relación intermitencia → capacidad), que es el núcleo, no tiene objetivo propio. El objetivo 2 ("estrategias de gestión") no tiene metodología. No hay hipótesis. | §5, Fig. 6.1 | Reformular con verbos medibles. Por ejemplo: OE1 definir y validar métricas de intermitencia sobre eventos de déficit; OE2 cuantificar la relación (B, M) → κ a planta común y su valor por encima de la PSH; OE3 evaluar estrategias de operación del BESS por escenario de intermitencia y fase ENSO. Agregar H1: "a igual PSH, mayor B diaria implica mayor κ". | Alta |
| P6 | La segunda pregunta de investigación (operación bajo escenarios y precios) no tiene método ni avance. El código solo implementa un despacho codicioso. | §1, §6 | Sustentar esa pregunta con estrategias concretas: despacho codicioso, reserva mínima de SOC, arbitraje con precios de bolsa de XM y una cota de previsión perfecta (LP). Si no hay tiempo, reducirla explícitamente con aprobación del comité. | Alta |
| P7 | Las figuras 2.2, 2.4, 3.1, 3.2 y 6.5 son capturas de páginas completas de otros artículos, con texto ajeno superpuesto. **La Fig. 3.2 conserva la marca "licensed use limited to: Interconexión Eléctrica ISA… IEEE Xplore"**. La Ec. 6.2 quedó mezclada con la Ec. 3 de Takeuchi & Sano. | §2–§6 | Rehacer todas las figuras (redibujar o adaptar con permiso) y citar "adaptado de". Reescribir la Ec. 6.2. Esto es un riesgo de derechos de autor y de imagen ante el comité. | Alta |
| P8 | Hay citas que no corresponden a lo que se afirma. Kuray et al. 2020 (electrolitos de sodio) se cita por métodos probabilísticos; Oryani et al. 2021 (barreras a las renovables en Irán) por métodos analíticos; Monsef et al. 2019 (redes de agua) por NSGA-II en BESS; Shi et al. 2014 (estabilidad transitoria) por cadenas de Markov. Yin et al. 2020 tiene el DOI de arXiv en vez del de *Nat. Commun.*, Carrière et al. tiene el DOI `https://doi.org/s` y AbouBakr et al. tiene el texto corrupto ("stoAbouBakrrage"). | §1, §3.3, Refs. | Revisar cada cita contra el PDF fuente y reemplazar las que no correspondan. Por ejemplo, Yang et al. 2018 sí cubre la taxonomía de métodos de dimensionamiento. Exportar desde Zotero o Mendeley con DOI verificado. | Media |
| P9 | Quedan sin atender los comentarios de la coorientación (UFSC): el orden de las secciones, la diferencia entre "marco teórico" y "referencial teórico", los vínculos entre subsecciones, qué estrategias de mitigación hay en §3.1 y cuál método de la Tabla 3.1 usa la tesis. | pp. 4, 11, 12, 15, 19 | Atenderlos uno por uno con una tabla de respuesta. En especial, cerrar §3 con un párrafo que diga qué método se usa y por qué (simulación cronológica con optimización 2-D y modelo sustituto). | Media |
| P10 | La Fig. 6.1, paso 03, dice que se extraerán "las series de cada hora del día". El análisis principal usa la serie completa. | Fig. 6.1 | Alinear con lo que se decida en C1 (resolución diaria como análisis principal y horaria como complemento). | Media |
| P11 | El cronograma (2025-2S a 2027-1S) no refleja el estado real. El artículo SLR ya publicado no figura, y el artículo de resultados está al 0 % en 2026-2S. | §7 | Actualizar con el plan de la sección 6 de este documento. Incluir la pasantía en la UFSC (ya realizada) con su artículo (Tuirán, Vaz, Uriona Maldonado y Zapata 2026, *Atmosphere* 17(10), 1007, doi:10.3390/atmos17101007) y las fechas del comité. | Media |
| P12 | Las cifras de introducción son de 2022–2024, mientras el artículo de 2026 ya usa datos de IRENA 2026. | §1 | Actualizar con las mismas fuentes del artículo para mantener la coherencia. | Baja |

---

## 2. Código: qué falta y cómo solucionarlo

### 2.1 Hallazgo nuevo: B horaria está confundida con la PSH (crítico)

Con demanda plana y planta solar sola, **cada noche es un evento de déficit**.
A resolución horaria, los intervalos entre eventos son casi siempre de unas
24 h, y un día nublado solo une dos noches en un evento más largo. Por eso B
queda cerca de −1 (régimen periódico), y su variación entre sitios depende de
cuántos días alcanzan a superar la demanda, es decir, del nivel de recurso.

Experimento con 9 sitios sintéticos de 20 años. Se cruzan tres niveles de
claridad media (kt → PSH) con tres niveles de persistencia de días nublados
(φ, AR(1) diario). La planta se escala para generar 1.15 veces la demanda.
`E_Rippl` es la batería necesaria para que ENS = 0:

| kt | φ | PSH | **B horaria** | B diaria | E_Rippl [MWh] |
|---|---|---|---|---|---|
| 0.55 | 0.0 | 4.18 | −0.792 | −0.271 | 1 821 |
| 0.55 | 0.5 | 4.20 | −0.736 | −0.166 | 4 165 |
| 0.55 | 0.8 | 4.16 | −0.732 | −0.090 | 8 236 |
| 0.65 | 0.0 | 4.94 | −0.870 | −0.277 | 1 438 |
| 0.65 | 0.5 | 4.90 | −0.860 | −0.184 | 3 740 |
| 0.65 | 0.8 | 4.92 | −0.826 | −0.067 | 6 604 |
| 0.75 | 0.0 | 5.63 | −0.909 | −0.299 | 1 009 |
| 0.75 | 0.5 | 5.65 | −0.933 | −0.188 | 2 420 |
| 0.75 | 0.8 | 5.70 | −0.915 | −0.086 | 6 321 |

**Cómo leerlo:**

- La batería necesaria crece de 4 a 6 veces con la persistencia (φ).
- La B horaria casi no responde a φ; en kt = 0.75 incluso deja de ser
  monótona. En cambio, sí cambia con la PSH.
- La B diaria crece de forma monótona con φ, de −0.29 a −0.07, y es casi
  independiente de la PSH. Esa es la métrica que la tesis necesita.
- M sale débil en ambas resoluciones; hay que reportarlo con honestidad.

Esto explica los resultados actuales: el rango de B, [−0.71, −0.27], es el del
régimen horario, y la correlación de ln κ con B (+0.77) es parecida a la de la
PSH (−0.87). Parte de la "señal" de B puede ser la PSH contada dos veces.

**Solución:**

1. Usar `intermitencia.resolucion: "diaria"` como análisis principal y
   conservar el horario como complemento.
2. Como robustez, definir los eventos sobre el índice de claridad diario
   (kt = GHI/GHI despejado) o sobre la energía diaria desestacionalizada. Así se
   quita también la estacionalidad.
3. Volver a correr los pasos 02 y 05, y reportar ambas resoluciones en una tabla.

### 2.2 Validación del modelo sustituto (crítico, es la afirmación central)

| # | Problema | Solución |
|---|---|---|
| C2 | No se demuestra el valor incremental de B y M sobre la PSH. | Comparar modelos anidados con LOO: (a) solo PSH; (b) PSH + B; (c) PSH + B + M; (d) PSH + baselines sencillos (CV de la energía diaria, P10 diario, racha máxima de días con kt < umbral, autocorrelación lag-1 de kt diario). Reportar ΔR²_LOO, ΔRMSE y una prueba F parcial o de verosimilitud. La tesis se sostiene si (b) o (c) le gana a (a) y es competitivo con (d). |
| C3 | La LOO sobre 51 sitios vecinos, correlacionados en el espacio, es optimista. | Validación cruzada por bloques espaciales (por región o por clúster de coordenadas) e intervalos de confianza de los coeficientes por bootstrap. Reportar también el VIF entre B, M y PSH. |
| C4 | B y M se calculan sobre el balance de la planta de 100 MW (`_comun.cargar_balances`), mientras κ se calcula a 150 MW. Además, B y M dependen del diseño (planta y demanda), así que no son propiedades del recurso. | Calcular B y M en la misma planta de referencia que κ. Para que el sustituto sirva en sitios nuevos, calcularlos sobre una serie normalizada del recurso (kt diario o energía relativa a la media) y mostrar su sensibilidad al tamaño de planta. |
| C5 | La ley exponencial tiene R² mediano de 0.92, con curvatura residual. | Probar la exponencial estirada exp(−(E/κ)^β) y comparar con AIC. Reportar κ con su error estándar. |

### 2.3 Economía y formulación

| # | Problema | Solución |
|---|---|---|
| C6 | Todos los costos de `config.yaml` siguen marcados `# REVISAR` (CAPEX, OPEX, WACC y VoLL = 600 USD/MWh). El óptimo (LPSP 2.8 %) lo fija el VoLL. | Citar NREL ATB 2024 o 2025 para CAPEX y OPEX, la UPME o la CREG para el costo incremental de racionamiento (convertido de COP/kWh) y el WACC de la CREG. Agregar un análisis de sensibilidad tipo tornado sobre VoLL, CAPEX del BESS y tasa de descuento. Sin esto, ninguna cifra de LCOE es publicable. |
| C7 | El "LCOE" incluye la penalización VoLL × ENS en el numerador. Eso es un costo social total por MWh servido, no un LCOE. | Renombrarlo (`costo_total_usd_mwh`) y reportar aparte el LCOE técnico (sin VoLL) y el costo de la ENS. |
| C8 | La relación E/P está fija en 4 h. Con 335 MWh, la potencia queda en 84 MW para atender 20 MW de demanda: se paga PCS que solo sirve para cargar más rápido. | Optimizar P_bess como tercera variable, o fijarla en máx(demanda, carga útil) y analizar la sensibilidad. |
| C9 | Una batería Li-ion de 16.7 h para abastecer 20 MW planos con solo FV es poco realista. | Depende de la decisión de alcance (sección 5). Las opciones son admitir respaldo de la red o un generador, reportar el resultado como requerimiento de almacenamiento de larga duración (LDES) o cambiar el servicio (firmeza parcial, perfil diurno). |
| C10 | `ciclos_vida` está declarado en la configuración pero no se usa. No hay degradación, y el vertimiento (21 %) no se valora aunque el sistema puede vender a la red. | Vida del BESS = mín(vida calendario, ciclos_vida / ciclos por año). Agregar degradación lineal de capacidad y precio de venta del excedente, si el caso es conectado a la red. |

### 2.4 Datos, reproducibilidad y calidad

| # | Problema | Solución |
|---|---|---|
| C11 | No está documentada la procedencia de los datos: fuente de la GHI (¿NSRDB, ERA5, NASA POWER, mediciones de ISA?), periodo, zona horaria y tratamiento de faltantes. Los datos no están en el repositorio y `DATOS.md` no tiene enlace ni SHA-256. | Completar `DATOS.md` con la fuente, la licencia y la zona horaria (UTC o local; importa para los análisis por hora). Depositar los cuatro insumos en Zenodo u OSF con DOI (o en almacenamiento institucional si ISA restringe su uso). |
| C12 | No hay tests para `economia`, `dimensionamiento`, `sustituto`, `confiabilidad`, `pv` ni `io_datos`. | Agregar tests de CRF contra un valor tabulado, monotonía de la bisección, recuperación de κ conocido en una curva sintética, LOO frente al baseline y conservación de energía en `evaluar`. |
| C13 | El README dice que "la correlación entre el método antiguo y el corregido es negativa (r = −0.64)", pero eso aplica solo a M; para B, r = +0.91 (ver el informe). | Corregir la redacción del README. |
| C14 | Siguen pendientes de la bitácora: ENSO (ONI), aplicación a las 5 zonas, recálculo de la PSH y las 53 filas para 51 series. | La tarea ENSO es la más valiosa para la tesis: calcular B, M y la LPSP por año y agruparlos por fase. Ver `AGENTS.md`. |
| C15 | La carpeta no tenía historial git (venía de un zip). Ahora está enlazada a `origin/main`. Los dos PDF (propuesta y artículo) no están versionados, y `51 series/*.py` y `PSH/calculo_psh.py` son duplicados idénticos de `legacy/`. | Decidir si los PDF entran al repositorio (son 7.8 MB). Dejar los scripts antiguos solo en `legacy/`. |

---

## 3. Artículo en *Energies* (publicado): qué deja abierto y cómo aprovecharlo

El artículo está publicado y no se puede modificar. Lo que sigue sirve para el
capítulo de estado del arte de la tesis, para la defensa y para el próximo artículo.

**Fortalezas:** el proceso PRISMA está bien reportado (348 → 267 → 73 → 36; las
exclusiones suman 37, cuadra), la doble revisión es independiente, la
taxonomía en cuatro ejes es clara y las brechas quedan bien formuladas
(conceptual, temporal, de integración y de indicadores).

**Debilidades que el comité o un revisor pueden señalar:**

1. **La evaluación de calidad no discrimina.** Según la Tabla 10, solo Q2 tiene
   respuestas "No" (9 estudios). Ningún estudio supera el 10 % de respuestas
   negativas, así que los 36 quedan como "alta calidad" según el umbral (< 30 %),
   y las bandas moderada y baja de la Fig. 9 quedan vacías. Además, los umbrales
   dejan un hueco entre 30 y 31 %.
   En la tesis conviene reconocerlo y reportar la distribución de puntajes
   por dimensión, que sí varía (73.6 % en claridad conceptual).
2. **La búsqueda es restrictiva.** Solo cubre "battery storage", "battery
   capacity" o "battery energy", y exige "reliability" y "scenarios" o
   "simulations". Quedan fuera "BESS", "energy storage system", "lulls",
   "persistence" y "burstiness". El artículo lo reconoce en parte (§2.1).
3. **No hay puente con B y M.** El artículo nunca menciona *burstiness*,
   *memory*, Goh & Barabási ni Schleiss, que son la base de la propuesta.
   Su §5.3 pide "indicators capable of quantifying the duration, persistence,
   frequency, severity, and clustering of generation-deficit events", que es
   justo lo que hacen B y M sobre eventos de déficit junto con los cuantiles de
   severidad que ya calcula `eventos.py`.
4. **Hay una tensión temporal con la tesis.** El artículo señala como brecha
   que dominan las simulaciones horarias, y la tesis usa datos horarios.

**Cómo resolverlo en la tesis y en el artículo 2:**

- En la introducción del artículo de resultados, citar Tuirán et al. (2026)
  como origen de la brecha y presentar B y M sobre eventos de déficit como
  respuesta directa a las brechas 2 y 4.
- Resolver la tensión temporal de frente: la escala horaria y multianual
  (27 años) dimensiona la **energía** del BESS (adecuación), no la potencia
  para rampas. Eso coincide con lo que el propio artículo dice en §4.3: los
  periodos prolongados de baja generación determinan la energía, y las rampas
  determinan la potencia.
- Para el capítulo 2 de la tesis, actualizar la búsqueda con *snowballing*
  sobre los trabajos de persistencia y *lulls* (Poddar et al. 2023,
  Yin et al. 2020, Cosgrove et al. 2023, Schleiss & Smith 2016, Goh & Barabási 2008).

---

## 4. Coherencia entre los tres documentos

| Concepto | Propuesta | Código | Artículo SLR | Acción |
|---|---|---|---|---|
| Definición de intermitencia | Alternancia entre periodos de alta y baja actividad (Goh & Barabási) | Corridas de déficit | Transiciones abruptas que comprometen el suministro | Unificar: eventos de déficit frente a la demanda. Encaja con las tres. |
| Evento | Cruces de la acumulada por k·a_μ | Corrida contigua con balance < 0 | — | Actualizar la propuesta (P1). |
| M | Spearman | Pearson | — | Pearson (P2). |
| LPSP | Fracción del tiempo | ENS/demanda | No se define | ENS/demanda (P3). |
| Resolución | Por hora del día | Horaria (por defecto) | Señala lo horario como brecha | Diaria como análisis principal (C1); justificar la escala. |
| Mercado colombiano | Se menciona | Ausente | — | Precios de XM y costo de racionamiento (C6, P6). |

---

## 5. Decisiones de alcance (para el director y la estudiante)

Estas decisiones no son técnicas y bloquean varias tareas:

1. **¿Qué servicio presta el sistema?** Las opciones son (a) 20 MW firmes las
   24 h desde FV + BESS aislado, que exige unos 1.5 veces la planta y LDES;
   (b) firmeza parcial con un objetivo de LPSP sobre la red; (c) un perfil de
   demanda real de la subestación; (d) un servicio de la red (reducir el
   déficit en horas pico).
   **Recomendación:** (b) o (c). Mantienen el BESS en duraciones realistas y
   conectan con la red de ISA.
2. **¿Las 51 series son subestaciones de ISA? ¿Se pueden publicar?** De esto
   depende la sección de disponibilidad de datos del artículo 2.
3. **¿La pregunta 2 (operación) se mantiene completa o se acota?** Con el
   tiempo que queda, se recomienda acotarla a 3 o 4 estrategias de despacho
   evaluadas por escenario de intermitencia y fase ENSO.
4. **Valores B y M ya presentados en ELAEE y CLH 2024.** Cambian con la
   metodología corregida. Hay que decidir si se publica una nota aclaratoria
   o basta con explicarlo en la tesis.

---

## 6. Plan de trabajo propuesto (2026-2S a 2027-1S)

| Semanas | Tarea | Producto |
|---|---|---|
| 1–2 | Tomar las decisiones de la sección 5. Conseguir costos citables (C6). Documentar los datos (C11). | Acta de alcance y `config.yaml` sin `# REVISAR`. |
| 2–4 | Pasar a resolución diaria (C1), recalcular a la planta de referencia (C4) y comparar modelos anidados (C2) con validación espacial (C3). | Tabla "¿B y M aportan sobre la PSH?". **Es el punto de decisión de la tesis.** |
| 4–6 | Exponencial estirada (C5), economía corregida (C7–C10), análisis de sensibilidad. | Figuras F3–F7 regeneradas. |
| 6–8 | ENSO: B, M y LPSP por año, agrupados por fase ONI. Aplicación a las 5 zonas. | El resultado más original de la tesis. |
| 8–12 | Redactar el artículo 2: B y M diarias sobre eventos de déficit como predictores del almacenamiento a planta común, más el efecto ENSO. Revistas candidatas: *Applied Energy*, *Renewable Energy*, *Solar Energy*, *Journal of Energy Storage*. | Manuscrito enviado. |
| 2027-1S | Estrategias de operación (P6), validación por escenarios y redacción final. | Artículo 3 o capítulo, y la tesis. |
| En paralelo | Corregir la propuesta (P1–P12) para el comité. | Propuesta v2 con tabla de respuesta a la coorientación. |

---

## 7. Esquema sugerido para el artículo 2

1. **Introducción:** la brecha según Tuirán et al. (2026); B y M como
   indicadores de agrupamiento de los eventos de déficit.
2. **Datos y caso:** 51 sitios, 27 años horarios, fuente y mapa.
3. **Métodos:** definición de evento a resolución diaria; B con la corrección
   de Kim & Jo; M de Goh & Barabási; simulador; ley exponencial y κ; principio
   de planta común; validación espacial con modelos anidados.
4. **Resultados:** (i) B y M por sitio; (ii) κ frente a B, M y PSH, con su
   valor incremental; (iii) planta óptima frente a planta común: la
   sustitución entre planta y batería; (iv) ENSO.
5. **Discusión:** alcance (adecuación de energía y no de potencia), límites
   de M y transferibilidad a sitios nuevos.
6. **Disponibilidad de datos y código:** Zenodo más el repositorio.
