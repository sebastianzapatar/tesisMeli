# Fuentes de los parámetros económicos y técnicos (T03)

Fecha: 27 de octubre de 2026. Estos valores reemplazan los marcados `# REVISAR` en
`config.yaml`. Cada cifra se tomó de la página o del PDF que se cita, y las
conversiones se muestran explícitamente.

| Parámetro (`config.yaml`) | Antes | Ahora | Unidad | Fuente | Ubicación en la fuente | Conversión o nota |
|---|---:|---:|---|---|---|---|
| `economia.capex_pv_usd_kw` | 1100 | 1560 | USD/kW_ac | NREL, Annual Technology Baseline 2024, Utility-Scale PV | Sección de CAPEX: «$1.56/WAC overnight capital cost (plus grid connection cost) in 2023» | Planta de referencia de 100 MWdc (74,6 MWac), seguimiento a un eje, ILR 1,34 |
| `economia.opex_pv_usd_kw_anio` | 18 | 22 | USD/kW_ac-año | NREL ATB 2024, Utility-Scale PV | «fixed O&M (FOM) cost of $22/kWAC-yr for 2023» | — |
| `economia.capex_bess_energia_usd_kwh` | 250 | 241 | USD/kWh | Cole, Ramasamy y Turan (2025), *Cost Projections for Utility-Scale Battery Storage: 2025 Update*, NREL/TP-6A40-93281 | Figura 2 y texto: «the energy cost is $241/kWh» | USD de 2024 |
| `economia.capex_bess_potencia_usd_kw` | 150 | 372 | USD/kW | Ídem | «power cost is $379/kW adjusted down by $7/kW for a final power cost of $372/kW» | Chequeo: 241 × 4 + 372 = 1336 USD/kW = 334 USD/kWh, igual al valor de 2024 de la Tabla 2 (caso medio) |
| `economia.opex_bess_usd_kwh_anio` | 6 | 13,36 | USD/kWh-año | Ídem | «The FOM value selected is 4% of the $/kW capacity cost for a 4-hour battery» | 0,04 × 1336 USD/kW = 53,4 USD/kW-año ÷ 4 h = 13,36 USD/kWh-año |
| `economia.vida_bess_anios` | 12 | 15 | años | Ídem | «The lifetime we selected is 15 years» | — |
| `economia.ciclos_vida` | 6000 | 5475 | ciclos | NREL ATB 2024, Utility-Scale Battery Storage | Supone «approximately one cycle per day» y 15 años de vida | Derivado: 365 × 15. En la corrida con costos citados el sistema hace 259 a 281 ciclos/año, así que la vida calendario es la que limita |
| `bess.eff_carga`, `bess.eff_descarga` | 0,95 / 0,95 | 0,922 / 0,922 | — | NREL/TP-6A40-93281 | «The round-trip efficiency is chosen to be 85%» | √0,85 = 0,922 por etapa |
| `economia.voll_usd_mwh` | 600 | 546,3 | USD/MWh | UPME, Costo Incremental Operativo de Racionamiento (CRO), citado en el Documento CREG 901 377 de 2026 (12-jun-2026), nota 28 | «Para junio 2026 este valor se ubica en $1.881,33, según la información publicada por la UPME» | 1881,33 COP/kWh ÷ 3443,59 COP/USD = 0,5463 USD/kWh. **Pendiente:** confirmar en la página de la UPME a qué escalón corresponde el valor |
| (TRM usada en la conversión) | — | 3443,59 | COP/USD | TRM del 30-jun-2026 reportada por *Portafolio* | «estaba en 3.443,59 pesos» | Conviene reemplazarla por el promedio de junio de 2026 del Banco de la República |
| `economia.tasa_descuento` | 0,10 | 0,115 | — (real) | Documento CREG 901 355 de 2026, *Tasa de descuento para proyectos requeridos en el STN* (soporte de la Res. CREG 101 101 de 2026) | §5.1.1.3 y Tabla 2: «WACC real antes impuestos del 11,5%», fijado en la Res. CREG 083 de 2008 | Real y antes de impuestos; coherente con costos en moneda constante |

## Lo que queda abierto

- **Año del dólar.** La FV viene de cifras de 2023 del ATB 2024, cuyo año base es
  2022, y el BESS está en USD de 2024. La diferencia (≈5–7 %) es pequeña frente al
  ±30 % del análisis de sensibilidad (T11), pero en la tesis hay que declararla o
  llevar todo a USD de 2024 con el IPC de EE. UU.
- **Escalón del CRO.** Confirmar en la UPME el escalón y el mes; si se usa otro
  escalón, cambiar `voll_usd_mwh`.
- **Costos de EE. UU. aplicados a Colombia.** NREL describe proyectos en EE. UU.
  Declararlo como limitación o contrastarlo con una referencia local (por ejemplo,
  costos de proyectos de las subastas de la UPME).
- **Parámetros técnicos todavía sin fuente:** `planta.performance_ratio` (0,80) y
  `bess.autodescarga_frac_h` (0). No son costos y no entraban en T03; siguen
  marcados `# REVISAR`.
- **`escenarios_creg.yaml`:** su `trm_cop_usd` (4000) corresponde al periodo de
  precios de bolsa y se revisará cuando se descarguen esos precios (T15).

## Efecto sobre el óptimo económico (paso 04, 51 series, mediana)

| Indicador | Costos provisionales | Costos citados |
|---|---:|---:|
| Planta FV | 151 MW | 145 MW |
| Batería | 335 MWh (16,7 h) | 341 MWh (17,0 h) |
| LPSP | 2,8 % | 4,1 % |
| Costo total por MWh servido (incluye VoLL × ENS) | 240 USD/MWh | 335 USD/MWh |
| Vertimiento | 21,4 % | 16,6 % |

El óptimo converge en las 51 series. El costo sube por el CAPEX FV y del BESS y
por la tasa de descuento; la LPSP óptima sube porque el VoLL bajó. La batería
sigue cerca de 17 h de demanda, así que la decisión D1 del acta (servicio con
respaldo de red) sigue siendo necesaria.

## Referencias

- NREL. (2024). *2024 Annual Technology Baseline: Utility-Scale PV*.
  <https://atb.nrel.gov/electricity/2024/utility-scale_pv>
- NREL. (2024). *2024 Annual Technology Baseline: Utility-Scale Battery Storage*.
  <https://atb.nrel.gov/electricity/2024/utility-scale_battery_storage>
- Cole, W., Ramasamy, V. y Turan, M. (2025). *Cost Projections for Utility-Scale
  Battery Storage: 2025 Update* (NREL/TP-6A40-93281).
  <https://docs.nrel.gov/docs/fy25osti/93281.pdf>
- CREG. (2026). *Documento CREG 901 355: Tasa de descuento para proyectos
  requeridos en el STN*.
  <https://gestornormativo.creg.gov.co/gestor/entorno/docs/originales/Resoluci%C3%B3n_CREG_101_101_2026/Documento_CREG_901_355_2026.pdf>
- CREG. (2026). *Documento CREG 901 377: Programa transitorio de incentivos al uso
  eficiente de energía eléctrica por parte de la demanda regulada – 2026*.
  <https://gestornormativo.creg.gov.co/gestor/entorno/docs/pdf/doc_creg_0901_377_2026.pdf>
- Portafolio. (2026, 1 de julio). Precio del dólar en Colombia arrancó la jornada
  del 1 de julio a la baja.
  <https://www.portafolio.co/economia/finanzas/precio-del-dolar-en-colombia-arranco-la-jornada-del-1-de-julio-a-la-baja-497266>
