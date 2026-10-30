# Datos del modelo

Última actualización: 27 de octubre de 2026 (tarea T02 del plan de trabajo).

Los libros de Excel no se versionan en Git. Son archivos binarios grandes, y Git
guarda una copia adicional en el historial cada vez que cambian. El `.gitignore`
los mantiene fuera del repositorio.

## 1. Archivos que necesita el pipeline

Las rutas son relativas a la raíz del proyecto y coinciden con `config.yaml`
(`rutas.*`). Los hashes se calcularon el 27-oct-2026 sobre la copia de trabajo.

| Clave en `config.yaml` | Ruta | Tamaño | SHA-256 |
|---|---|---:|---|
| `series_51` | `51 series/df_series_todas_las_subestaciones.xlsx` | 55,2 MB | `3227b96b13f81f0bb9df55b618a46157b63e36bd823859f65ea7e63ef25f3f65` |
| `series_5` | `51 series/5 series GHI juntas.xlsx` | 8,3 MB | `6ec6720ac2d2a738a4bd0d237ffd9109a75cc3f9245d609043aae36cbf85cfc8` |
| `psh_51` | `51 series/PSH_resultados.xlsx` | 2,8 MB | `4ef0040b15cb883530afca12bb5e28aac1a61e3a0034dcb62a3fc7e1c05187d9` |
| `tienda_5` | `51 series/resultados_cuenta_tienda (2).xlsx` | 5 KB | `a2ad3ec8535fa3cb84db2117a2fc61372c58fa8c7355495dc390734d850afaf8` |
| `series_ghi_psh` | `51 series/df_series_todas_las_subestaciones con GHI.xlsx` | 55,2 MB | `5e526f40b513f366181a71940cf1520f18720e1bdf2b6cb0e95392d73b437e1a` |

**Duplicado.** `df_series_todas_las_subestaciones con GHI.xlsx` tiene exactamente
los mismos valores que `df_series_todas_las_subestaciones.xlsx` (diferencia
máxima 0). Solo cambian los encabezados, que llevan el prefijo «GHI ». No hace
falta depositarlo; basta con apuntar `series_ghi_psh` al otro archivo.

Para verificar un hash en Windows:

```
certutil -hashfile "51 series\df_series_todas_las_subestaciones.xlsx" SHA256
```

## 2. Descripción de las series

### 2.1 Las 51 series (`series_51`)

| Atributo | Valor |
|---|---|
| Variable | Irradiancia global horizontal (GHI), W/m², enteros |
| Sitios | 51, identificados por el nombre de la subestación (lista en §2.4) |
| Periodo | 1998-01-01 00:30 a 2024-12-31 23:30 (27 años) |
| Resolución | Horaria; 236 520 registros por sitio |
| Marca de tiempo | Al minuto 30 de cada hora: el valor representa la hora centrada |
| Zona horaria | Hora local de Colombia (UTC−5). El perfil medio es cero de 18:00 a 05:59, sube desde las 06:30 y alcanza su máximo a las 11:30 (726 W/m² en promedio de los 51 sitios), lo que corresponde a mediodía solar en hora local |
| Años bisiestos | No hay registros del 29 de febrero: faltan los 7 días de 2000, 2004, 2008, 2012, 2016, 2020 y 2024. Todos los años tienen 8760 horas |
| Faltantes | Ninguno: 0 celdas vacías y 0 días ausentes fuera de los 29 de febrero |
| Valores | Mínimo 0, máximo 1126 W/m²; ningún valor negativo; ningún valor positivo de noche |
| Control de calidad | Ninguna racha de 6 h o más con el mismo valor diurno (indicio de relleno); ningún día con GHI total igual a cero |
| PSH media por sitio | 4,17 a 5,83 h/día |
| Codificación | Los nombres llegaron en Unicode NFD (macOS); `io_datos.normalizar_nombre` los pasa a NFC |

### 2.2 Las 5 zonas (`series_5`)

| Atributo | Valor |
|---|---|
| Zonas | Antioquia, Suroccidente, Nordeste, Caribe, Oriente |
| Periodo | 1998-01-01 00:00 a 2025-12-31 23:00 (28 años, un año más que las 51 series) |
| Resolución | Horaria; 245 280 registros por zona |
| Marca de tiempo | Al minuto 0, **distinta** de las 51 series (minuto 30). Al comparar ambos conjuntos, alinear las marcas antes de calcular |
| Zona horaria | Hora local (mismo perfil diurno que las 51 series) |
| Años bisiestos y faltantes | Sin 29 de febrero; ningún otro faltante |
| PSH media por zona | 4,79 a 5,56 h/día |

### 2.3 PSH (`psh_51`)

Hojas: `Resumen` (PSH media, mediana, P90, mínimo y máximo diario y GHI anual por
sitio), `Climatología mensual`, `Promedio anual` (1998–2024) y `PSH diarias`
(9855 días × 51 sitios). La hoja `PSH diarias` coincide exactamente con la suma
diaria de la GHI horaria dividida por 1000 (diferencia máxima 0,000), así que es
un derivado del archivo `series_51`, no un dato independiente.

### 2.4 Sitios

Ancón Sur, Porce III, Jamondino, Chinú, San Carlos, Caracolí, Primavera,
San Mateo, Sogamoso, La Miel, Ibagué, La Virginia, Antioquia, La Enea,
Comuneros, Guatiguará, La Reforma, Bolívar, Termocol, Banadía, Cuestesitas,
Urrá, Chivor, Urabá, Medellín, Ocaña, El Copey, Brisas, Cerromatoso, Purnio,
Torca, Bacatá, Sochagota, Cari Care, La Sierra, El Bosque, Panamericana,
Caño Limón, Jaguas, San Antonio, Fundación, La Esmeralda, Paez, San Marcos,
La Mesa, La Hermosa, San Bernardino, San Felipe, La Cira, Akacías, Betania.

## 3. Procedencia: lo que está confirmado y lo que falta

| Dato | Estado |
|---|---|
| Fuente de la GHI | **Por confirmar.** Los archivos no traen metadatos de origen (propiedades del Excel: creados con `openpyxl` el 19-jun-2026). Las características son compatibles con el NSRDB de NREL (Physical Solar Model sobre GOES): inicio en 1998, marcas al minuto 30, valores enteros en W/m², sin 29 de febrero y sin faltantes. Es una hipótesis: confirmar con quien descargó o entregó las series, junto con la versión y la fecha de descarga |
| Licencia y uso | **Por confirmar** con el director y con ISA (decisión D2 del acta de alcance) |
| Coordenadas de los 51 sitios | **Pendiente.** No están en ningún archivo. Guardarlas en `datos_externos/coordenadas_51.csv` con columnas `serie, lat, lon, departamento, region`. Son necesarias para la validación espacial (T07) |
| Definición de las 5 zonas | **Pendiente.** Documentar cómo se construyó cada zona (sitio representativo o promedio de varios) |
| Tratamiento de faltantes | No aplica en los archivos entregados (no hay faltantes). Si la fuente es el NSRDB, el relleno lo hace el proveedor; citarlo cuando se confirme |
| Filas sobrantes de `promedio_BM_por_serie.xlsx` | Pendiente de la bitácora: ese archivo no está en la carpeta de trabajo, así que no se pudo revisar |

## 4. Depósito en Zenodo

Pendiente de la decisión D2 (acceso abierto o restringido). Pasos cuando se decida:

1. Entrar a <https://zenodo.org> con la cuenta institucional o ORCID y crear un
   «New upload».
2. Subir los cuatro archivos de §1 sin el duplicado: `series_51`, `series_5`,
   `psh_51` y `tienda_5`, más este `DATOS.md`.
3. Tipo: *Dataset*. Título sugerido: «Series horarias de irradiancia global
   horizontal (1998–2024) en 51 subestaciones de Colombia, insumo de la tesis
   Dimensionamiento de BESS considerando la intermitencia fotovoltaica».
4. Acceso: *Open* si ISA lo autoriza; si no, *Restricted* con solicitud de acceso.
5. Licencia: la que permita la fuente original (si es NSRDB, revisar sus términos).
6. Publicar y pegar aquí el DOI:

   - DOI: `pendiente`
   - Versión: `v1`
   - Fecha del depósito: `pendiente`

## 5. Archivos que no hace falta distribuir

- `df_series_todas_las_subestaciones con GHI.xlsx` (duplicado, §1).
- `51 series/resultados_20MW_Todas (1).xlsx` (145 MB): salida del modelo
  anterior; el pipeline nuevo no la usa.
- Los Excel de `resultados/` se reconstruyen con `./run_todo.sh`.
- `.cache/` contiene copias regenerables para acelerar la lectura.
