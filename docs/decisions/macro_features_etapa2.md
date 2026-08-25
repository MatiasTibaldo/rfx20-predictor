# Decisión: diseño de features macro (Nodo 4, Etapa 2)

**Fecha:** 25 de agosto de 2026
**Módulos afectados:** `ingestion/futures.py`, `features/macro.py`, `features/pipeline.py`

## Contexto

Etapa 2 de Nodo 4 cubre la tarea 3 del plan de acción ("features macro
transformados"): spreads cambiarios, riesgo país, tasas (plazo fijo,
BADLAR, TAMAR), IPC con lag de publicación, y tasa implícita/term spread
de futuros RFX20 (decisión de alcance ya tomada en
`docs/decisions/futures_implied_rate.md`).

## Validación de BADLAR/TAMAR

El alumno sumó manualmente `data/raw/macro/badlar.csv` y
`data/raw/macro/tamar.csv`. Validación hecha antes de consumirlos:

| Serie | Filas | Rango de fechas | Nulls | Duplicados | Orden | Rango de valores | Gaps > 5 días |
|---|---|---|---|---|---|---|---|
| BADLAR | 2094 | 2018-01-02 → 2026-08-21 | 0 | 0 | ✅ | 15.9% – 130.3% | 2 (feriados largos) |
| TAMAR | 454 | 2024-10-01 → 2026-08-21 | 0 | 0 | ✅ | 21.4% – 67.0% | 0 |

TAMAR arranca en oct-2024, ~10 meses después de la discontinuación de LELIQ
(dic-2023) que `ingestion/macro.py` documentaba como su reemplazo directo —
es un gap real de la serie, no un error de datos (BADLAR cubre todo el
período sin discontinuidad, así que siempre hay alguna tasa de referencia
de corto plazo disponible).

## Decisiones de diseño

### 1. Front-month de futuros sin calendario de vencimientos

En vez de mantener una tabla de fechas de vencimiento por contrato, el
front-month de cada fecha se determina directamente de los datos: entre los
símbolos `RFX20{MM}{YYYY}` que efectivamente cotizaron ese día, el de menor
`(año, mes)` es el front-month; el siguiente por orden es el "next month"
(`features/macro.py::select_front_month`). Es robusto — la ausencia de un
contrato en los datos ya refleja que venció o no arrancó a cotizar — y evita
mantener una fuente de vencimientos separada. Validado contra el ejemplo ya
inspeccionado manualmente en la sesión anterior: 2020-08-21 → front
`RFX20092020` (tasa implícita 51.76%), next `RFX20122020` (53.10%), term
spread -1.34pp.

`implied_rate_front`/`implied_rate_next` pueden ser `null` en días donde el
contrato efectivamente cotizó pero la API no devolvió tasa implícita para
ese contrato ese día (común cerca del vencimiento) — es una característica
de los datos fuente, no se imputa.

### 2. Spreads cambiarios sobre el precio de venta

Las cinco series de dólar (`oficial`, `bancos`, `informal`, `mep`, `ccl`)
tienen columnas `compra`/`venta` (MEP y CCL con `compra == venta`). Se usa
`venta` de forma consistente para `spread_oficial_informal`,
`spread_oficial_mep`, `spread_oficial_ccl`, `spread_mep_ccl` (variación
fraccional respecto al oficial, o entre sí para mep/ccl). `dolar_bancos.csv`
no se usa — el plan habla de "oficial/blue/MEP/CCL", no de bancos.

### 3. Calendario diario = fechas de `technical_index.parquet`

Todas las fuentes (IPC mensual, BADLAR/TAMAR/dólar diario con gaps,
futuros con gaps) se alinean con `join_asof(strategy="backward")` sobre las
1955 fechas de `technical_index.parquet` (= las de `rfx20_spot`), el
calendario del propio target. Deja `macro.parquet` directamente alineado
para el join final de la etapa de particionamiento.

**Bug encontrado y corregido durante la implementación:** las primeras
versiones de `load_dolar_spreads()` y `load_rates_and_risk()` combinaban
sus fuentes con `join(..., how="full", coalesce=True)` encadenados. Un
`full` join arma la unión de fechas de *todas* las fuentes — así, una
fecha donde solo una fuente publicó (ej. `tasa_plazo_fijo.csv` y
`badlar.csv` tienen dato el 2020-02-03 pero `riesgo_pais.csv` no) queda
como fila real en el resultado, con `null` en las columnas sin dato ese
día. El `join_asof(strategy="backward")` posterior encuentra esa fila
exacta y toma su valor `null` en vez de retroceder al último valor
realmente conocido (2068.0 del 2020-01-31), "tapando" el dato válido.
Se corrigió aplicando `fill_null(strategy="forward")` a cada columna
*dentro* de cada loader (antes de derivar spreads, y antes de que
`build_macro_features` haga el asof final), de modo que una fecha
union-only ya lleve el último valor conocido en vez de un null espurio.
Los nulls "de arranque" (antes de que una serie exista, ej. MEP
pre-2018-10-29 o TAMAR pre-2024-10-01) siguen siendo `null` correctamente
— `fill_null(strategy="forward")` no rellena hacia atrás.

### 4. IPC con lag de publicación

Implementado exactamente según `docs/decisions/ipc_publication_lag.md`:
tabla exacta de 30 meses (dic-2023 a may-2026, hardcodeada en
`features/macro.py::_IPC_LAG_TABLE`) + aproximación `cierre_mes + 12 días
corridos` (ajustada al día hábil siguiente si cae en fin de semana) para
el resto de la serie. Validado en `macro.parquet`: el IPC de diciembre-2023
(25.5%, post-devaluación) no aparece antes del 2024-01-11, tal como exige
la tabla — el valor visible hasta esa fecha es el de noviembre-2023 (12.8%,
disponible desde su fecha aproximada 2023-12-12).

## Alcance de datos de futuros

El fetch inicial (`scripts/fetch_rfx20_futures.py`, rango 2018-01-01 a
2026-08-21) devolvió 2608 filas / 39 contratos, con la primera fecha real
en **2020-01-02** — no hay datos de futuros RFX20 anteriores en la API
(con `excludeEmptyVol=true`). `implied_rate_front`/`term_spread_futures`
son `null` en `macro.parquet` para fechas anteriores a esa, además de los
días sin contrato "next month" simultáneo.

## Salida

`data/features/v1/macro.parquet` — 1955 filas (calendario del índice), 14
columnas: `date` + 4 spreads + `riesgo_pais`/`tasa_pf`/`badlar`/`tamar` +
`ipc_pct` + `implied_rate_front`/`implied_rate_next`/`term_spread_futures`/
`futures_front_symbol`.
