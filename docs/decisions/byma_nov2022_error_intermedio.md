# BYMA, 2022-11-22 → 25: error intermedio en `cartera_historica_*.csv`, corregido en el raw

**Fecha:** 16 de septiembre de 2026
**Módulos/archivos afectados:**
`data/raw/rfx20_composition/Cartera Historica/cartera_historica_2022112{2,3,4,5}.csv`,
`data/raw/v1/rfx20_composition.parquet` (regenerado)

## Contexto

Analizando los `close` individuales por ticker dentro de los archivos
`cartera_historica_*.csv` (a pedido del alumno, buscando específicamente
si había algo más además del patrón crónico de splits ya documentado en
`docs/decisions/registro_splits_componentes.md`) se corrió un barrido del
ratio composición/OHLCV de BYMA contra el **régimen esperado para cada
fecha** (100 / 10 / 2 / 1 según los 3 splits documentados) — no contra el
OHLCV crudo directamente, que es lo que ya veníamos usando y que no
distingue "fuera de régimen" de "mismatch crónico esperado".

## Hallazgo

Única anomalía nueva en toda la historia de BYMA (fuera de la ya conocida
de sep-2019): **2022-11-22 al 25**, 4 ruedas, el ratio cae de 10 (régimen
vigente en esa fecha) a exactamente 2 — sin cambio de `quantity`, sin
ningún split documentado en esas fechas.

| fecha                | `close` local (antes) | `close_ohlcv` | ratio |
| -------------------- | --------------------: | ------------: | ----: |
| 2022-11-18 (control) |                194,75 |        19,475 |  10,0 |
| 2022-11-22           |                 38,10 |         19,05 |   2,0 |
| 2022-11-23           |                 37,95 |        18,975 |   2,0 |
| 2022-11-24           |                 38,40 |          19,2 |   2,0 |
| 2022-11-25           |                 37,90 |         18,95 |   2,0 |
| 2022-11-28 (control) |                188,50 |         18,85 |  10,0 |

Verificado que es **exclusivo de BYMA**: ningún otro de los 28 tickers se
desvía de su propio régimen en esa ventana (MIRG y YPFD, que sí tienen
desvío crónico en esas fechas, lo mantienen constante y consistente con lo
esperado).

## Diagnóstico: diferencia clave con sep-2019

Se consultó `GET /api/rfx20/historical?date=X` (API histórico de
MatbaRofex, mismo usado para sep-2019) para las 4 fechas:

| fecha      | `close` local (antes) | API (`price`) |    `quantity`/`size` |
| ---------- | --------------------: | ------------: | -------------------: |
| 2022-11-22 |                 38,10 |     **190,5** | 33,451196 (coincide) |
| 2022-11-23 |                 37,95 |    **189,75** | 33,451196 (coincide) |
| 2022-11-24 |                 38,40 |     **192,0** | 33,451196 (coincide) |
| 2022-11-25 |                 37,90 |     **189,5** | 33,451196 (coincide) |

Controlado en 2022-11-18 y 2022-11-28: el API coincide exactamente con
nuestro archivo local (194,75 y 188,5) — confirma que el API es confiable
como referencia en este caso.

**A diferencia de sep-2019** (donde el API devolvía el mismo valor
corrupto que teníamos nosotros — el error estaba en la fuente, no había
forma de obtener el valor real sin reconstruirlo), **acá el API tiene el
valor correcto** y nuestro archivo coincide con él en todas las fechas
_excepto_ estas 4, donde el `close` está dividido por un factor ~5
respecto al valor real. Es un error puntual de nuestra copia local del
dato ("error intermedio"), no del dato de origen — el mismo patrón de
"dato puntual confirmable contra fuente externa" que ya se trató una vez
para BBAR (`config/data_corrections.yaml::dirty_data`), pero esta vez
corregido directamente en el raw.

## Decisión

Se editan estos 4 archivos — única excepción al principio
de inmutabilidad de `data/raw/` en todo el proyecto, justificada porque:

1. El valor correcto está confirmado de forma independiente contra una
   fuente autoritativa externa (no es una corrección "inventada").
2. Es un error de transcripción puntual de nuestra copia, no del dato
   real de mercado ni de la metodología del índice — corregirlo en el
   archivo de origen es más simple y transparente que mantener un parche
   de `processing/` para un caso que no es sistémico.

Se reemplazó el `close` de BYMA en los 4 CSV por el valor del API
(`190.5`, `189.75`, `192.0`, `189.5`), sin tocar ninguna otra columna ni
ticker. Se regeneró `rfx20_composition.parquet` (`uv run python -m
ingestion.composition_runner`). Verificado: ratio composición/OHLCV de
BYMA vuelve a 10,0 constante en las 4 fechas, igual que el resto del
régimen 2022-07-07 → 2024-05-09.

## Precedente para el futuro

Esta es la única corrección de este proyecto que tocó `data/raw/`
directamente. **No usar como precedente general** — el resto de las
correcciones (sep-2019, splits crónicos) siguen viviendo en
`config/data_corrections.yaml` sin tocar el raw. Esta excepción aplicó
específicamente porque (a) había una fuente externa autoritativa con el
valor exacto, verificable día por día, y (b) el alumno autorizó
explícitamente la edición de estos 4 archivos puntuales, no una política
general.
