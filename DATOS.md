# Datos del modelo

Los libros de Excel no se versionan en Git. Son archivos binarios grandes y
Git guarda una copia adicional en el historial cada vez que cambian. El
`.gitignore` conserva localmente los Excel de `5 series/`, `51 series/` y
`PSH/`, pero evita que entren accidentalmente al repositorio.

## Archivos necesarios para ejecutar el pipeline

Mantén estos archivos en las rutas exactas indicadas:

| Ruta local | Tamaño aproximado | Uso |
|---|---:|---|
| `51 series/df_series_todas_las_subestaciones.xlsx` | 53 MB | Series horarias de las 51 subestaciones |
| `5 series/5 series GHI juntas.xlsx` | 7.9 MB | Aplicación posterior a las cinco zonas |
| `PSH/PSH_resultados.xlsx` | 2.7 MB | PSH por subestación |
| `5 series/resultados_cuenta_tienda (2).xlsx` | 8 KB | Datos complementarios de las cinco zonas |

Las rutas se configuran en `config.yaml`. Si los archivos se guardan en otro
lugar, cambia allí las rutas relativas.

## Archivos que no hace falta distribuir

- `51 series/resultados_20MW_Todas (1).xlsx` (145 MB) es una salida del modelo
  anterior. El pipeline nuevo no la necesita.
- Los Excel de `resultados/` se reconstruyen ejecutando `./run_todo.sh`.
- `.cache/` contiene copias regenerables para acelerar la lectura.

## Forma recomendada de compartir los datos

Para este proyecto, la opción más limpia es:

1. Publicar en GitHub el código, la documentación, el cuaderno ejecutado y el
   PDF final.
2. Guardar únicamente los cuatro insumos necesarios en un archivo comprimido
   versionado fuera del historial Git. Para investigación pública, Zenodo u OSF
   permiten conservar una versión estable y obtener una referencia; para un
   equipo privado también sirve almacenamiento institucional.
3. Añadir aquí el enlace, la versión y, preferiblemente, el SHA-256 del archivo
   cuando se defina el destino.

Una GitHub Release también es válida para una entrega puntual. Git LFS se
recomienda solo si los datos deben clonarse junto con el repositorio y se han
revisado previamente sus cuotas de almacenamiento y transferencia.

## Verificación antes de publicar

```bash
# Debe listar código, documentación, el cuaderno y el PDF; no los Excel crudos.
git status --short

# Comprueba qué regla excluye un archivo concreto.
git check-ignore -v "51 series/df_series_todas_las_subestaciones.xlsx"
```
