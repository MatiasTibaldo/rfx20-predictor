# Decisión: alcance de indicadores técnicos, volatilidad y target (Nodo 4, Etapa 1)

**Fecha:** 24 de agosto de 2026
**Módulos afectados:** `features/technical.py`, `features/volatility.py`, `features/target.py`, `features/pipeline.py`

## Contexto

El Bloque 1 del plan de acción (`docs/plan_de_accion.md`) agrupa 5 tareas de
feature engineering (indicadores técnicos, volatilidad, macro, diferenciación
fraccional, particionamiento temporal). Se acordó con el alumno avanzar
**por etapas** en vez de construir todo el módulo `features/` de una sola vez,
para poder validar cada bloque de datos antes de sumar el siguiente. Esta
etapa cubre indicadores técnicos y volatilidad realizada.

## Decisión 1 — Indicadores calculados en dos niveles: componentes e índice

El plan original describía los indicadores técnicos como una tarea sobre "los
27 componentes". Se decidió calcularlos **también sobre la propia serie del
índice RFX20** (`data/raw/v1/rfx20_spot.parquet`).

**Razón:** el RFX20 reconstruido es una combinación lineal de sus componentes
(Σ close_i × cantidad_i / divisor). Un indicador técnico calculado sobre el
spot del índice no es información externa a la composición — es una lectura
agregada de la misma serie, solo que resumida a nivel índice en vez de nivel
componente antes de aplicar el indicador. Motivos para incluirlo:

- El momentum/autocorrelación propio del índice suele ser, en la literatura
  de forecasting financiero, la clase de feature individual con mayor poder
  predictivo — omitirlo descarta la señal más fuerte disponible.
- Da un baseline natural para la tesis: comparar un modelo "solo técnico del
  índice" contra el modelo completo con features de composición permite
  cuantificar cuánto aporta desagregar por componente.
- No genera look-ahead bias: los indicadores solo usan cierres pasados.

**Implementación:** `features/technical.py` y `features/volatility.py`
exponen funciones puras (`add_technical_indicators`,
`add_realized_volatility`) que operan sobre cualquier DataFrame con
`date`/`close`/`log_return`. Se aplican tanto a los 27 componentes
(`add_*_all` sobre el dict por ticker) como a la serie del índice
individualmente en `features/pipeline.py`.

## Decisión 2 — Ventanas e indicadores elegidos

| Indicador | Parámetro | Fuente |
|---|---|---|
| Media móvil simple | 10, 20, 50 ruedas | Plan de acción (literal) |
| RSI | 14 ruedas | Plan de acción (literal) |
| MACD | 12/26/9 (EMA rápida/lenta/señal) | Default de la librería `ta` |
| Bandas de Bollinger | 20 ruedas, 2 desvíos estándar | Default de la librería `ta` |
| Volatilidad realizada | rolling std de `log_return`, ventanas 10/20/50 | Igualadas a las de MA, no se introduce un tercer set de parámetros sin justificar |

`ta` opera sobre `pandas.Series`, no `polars` — la conversión ocurre
localmente dentro de `add_technical_indicators` (columna `close` a pandas,
resultado de vuelta a `pl.Series`), sin dejar pandas en el resto del módulo,
siguiendo el criterio ya establecido en `CLAUDE.md` para librerías externas.

**Nota de comportamiento:** los indicadores de `ta` devuelven `NaN` (float)
durante el período de warm-up (ej. `ma_50` es `NaN` en las primeras 49 filas
de cada ticker), mientras que `realized_vol_{w}` (calculado con
`pl.rolling_std` nativo de polars) usa `null`. Es una diferencia de
implementación entre ambas librerías, no un error — a tener en cuenta al
filtrar/imputar nulls más adelante (`NaN != null` en polars).

## Decisión 3 — Target del índice construido en esta etapa, no en Bloque 2

No existía ninguna serie de retorno del índice en sí — `ohlcv_long.parquet`
solo tiene retornos por ticker. Se decidió construir el target
(`log_return`, `log_return_fwd_{1,3,5}` del RFX20) ya en esta etapa
(`features/target.py`), en vez de posponerlo a cuando se armen los datasets
de entrenamiento en Bloque 2.

**Razón:** es una transformación mínima (reutiliza
`processing.returns.add_returns` sobre `rfx20_spot`, sin duplicar la
fórmula) y evita tener que revisitar el esquema de `features/` más adelante
para agregar una columna que de todos modos hacía falta desde el principio.

## Alcance de salida de esta etapa

Se persisten dos parquets intermedios en `data/features/v1/`:

- `technical_components_long.parquet` — long format, 27 tickers, columnas de
  `ohlcv_long` + indicadores técnicos + volatilidad realizada.
- `technical_index.parquet` — serie diaria del índice con target
  (`log_return_fwd_{1,3,5}`) + indicadores técnicos + volatilidad realizada.

**No** se genera todavía el `features_long.parquet` final nombrado en el plan
original — ese nombre se reserva para cuando se sume la etapa de macro y haya
que decidir el join definitivo componente↔índice↔macro. Evita rehacer el
esquema de salida en cada etapa.

## Pendiente (próximas etapas de Nodo 4)

- Features macro (spreads cambiarios, term spread, IPC con lag de
  publicación — ver `docs/decisions/ipc_publication_lag.md`).
- Tasa implícita y term spread de futuros RFX20 — ver
  `docs/decisions/futures_implied_rate.md`.
- Diferenciación fraccional (exploración acotada, no bloqueante).
- Particionamiento temporal 70/15/15 y consolidación en `features_long.parquet`.
