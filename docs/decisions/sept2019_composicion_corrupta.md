# Decisión: corrección de precios corruptos en composición RFX20 — septiembre 2019

**Fecha:** 16 de septiembre de 2026
**Módulos afectados:** `processing/cleaner.py`, `features/target.py`, `app.py`,
`config/splits.yaml`

## Contexto

Durante la exploración de variables objetivo alternativas para Bloque 3 se
detectó que `log_return` del índice tenía outliers extremos no explicados por
eventos macro conocidos. El más severo (2023-10-09) resultó ser el cambio de
base de octubre 2023 sin ajustar (ver `docs/decisions/base_change_oct2023.md`
para ese caso, ya resuelto por separado). Después de corregirlo, seguían
apareciendo dos outliers muy grandes y simétricos:

| fecha | log_return original | close (spot) |
|---|---|---|
| 2019-09-23 | +0.626 | 77.080,92 |
| 2019-09-30 | -0.641 | 39.073,41 |

Un salto de +62,6% seguido de una caída de -64,1% en una semana, sin ningún
evento macro documentado en esas fechas.

## Investigación

### 1. Reconstrucción vs. spot — no hay desvío entre ambos

Se comparó el índice reconstruido (`Σ close_i × quantity_i`, desde
`rfx20_composition.parquet`) contra el spot oficial (`rfx20_spot.parquet`)
para la ventana 2019-09-20 → 2019-10-04. Coinciden con error ~0,00001% en
**todos** los días, incluida la semana anómala. Esto descarta un desvío entre
ambas fuentes — lo que sea que está mal, ya está en el `close` que alimenta a
las dos.

### 2. Composición vs. OHLCV canónico — sí hay desvío, y es total

Se cruzó el `close` embebido en `rfx20_composition.parquet` (fuente:
`cartera_historica_201909XX.csv`) contra el OHLCV canónico por ticker
(`data/raw/v1/*_ohlcv.parquet`, el que sí valida `scripts/validate_variation.py`
y el que alimenta las features de Track A/B ML). Barriendo **toda** la
historia 2018-2026, el único período con desvío en los 20/20 tickers
simultáneamente es 2019-09-23 → 2019-09-27. Ningún otro rango de 5 días en 8
años tiene este patrón.

Ejemplo (2019-09-23), ordenado por ratio composición/OHLCV:

| ticker | close composición | close OHLCV | ratio |
|---|---:|---:|---:|
| TGSU2 | 23.00 | 114.20 | 0.201 |
| TECO2 | 35.00 | 133.50 | 0.262 |
| BMA | 46.00 | 158.30 | 0.291 |
| TS | 244.00 | 722.00 | 0.338 |
| APBR | 200.00 | 488.00 | 0.410 |
| TXAR | 40.00 | 15.10 | 2.649 |
| BBAR | 275.00 | 95.95 | 2.866 |
| GGAL | 266.00 | 80.00 | 3.325 |
| YPFD | 223.00 | 60.70 | 3.674 |
| COME | 7.00 | 1.66 | 4.217 |
| CRES | 167.00 | 39.45 | 4.233 |
| SUPV | 166.00 | 38.20 | 4.346 |
| PAMP | 190.00 | 43.20 | 4.398 |
| TGNO4 | 194.00 | 43.75 | 4.434 |
| CEPU | 93.00 | 20.70 | 4.493 |
| EDN | 111.00 | 24.65 | 4.503 |
| ALUA | 99.00 | 21.85 | 4.531 |
| TRAN | 108.00 | 23.10 | 4.675 |
| VALO | 219.00 | 6.50 | 33.692 |
| BYMA | 102.00 | 2.18 | 46.735 |

Ratios completamente dispares y sin coherencia direccional entre tickers —
descarta que sea un movimiento de mercado real (un crash/rally real no
dispersa así, con unos activos ×4 arriba y otros ×0,2 al mismo tiempo).
Detalle completo en `docs/diagnostics/composicion_vs_ohlcv_sep2019.csv`.

### 3. Confirmación contra la fuente autoritativa (WS de MatbaRofex)

Se consultó `GET /api/rfx20/historical?date=X` (mismo WS documentado en
`docs/decisions/rfx20_ws_backfill.md`) para 2019-09-20 → 2019-09-30. El API
devuelve **exactamente** los mismos `close` "anómalos" que ya teníamos
guardados (0 diferencias en `quantity` y `close` para 09-20 a 09-27) — el
error está en el origen (`cartera_historica_201909XX.csv`, que a su vez
alimenta `historico_spot_rfx20.csv`), no en la ingesta del proyecto.

### 4. Descartada la hipótesis de recomposición de cartera

Se verificó si el problema era una recomposición trimestral del índice mal
fechada. El API confirma que sí hubo una recomposición real ese mes (`quantity`
cambia y cambia la membresía: salen APBR y TS, entran CVH y LOMA) — pero
efectiva el **2019-10-01**, un día después de lo que `rfx20_composition.parquet`
tenía asignado (2019-09-30). Es un bug real y separado, de menor severidad
(desfasa la fecha de vigencia de cantidades en 1 día hábil), documentado acá
como hallazgo pero **no corregido en este cambio** — ver sección "Pendientes".
Importante: las `quantity` de los 20 tickers durante 09-23→09-27 sí coinciden
con el API — el problema de esta ventana es puramente el `close`, no la
cantidad.

### 5. Nota aparte: desvíos crónicos de BYMA e YPFD (no son parte de este bug)

Al barrer toda la historia también aparecen BYMA (1.677 días) e YPFD (1.964
días, casi toda la serie) con desvío constante composición-vs-OHLCV. Mecanismo
distinto: el OHLCV canónico viene de un feed en vivo (Matriz) que reajusta
retroactivamente toda la serie histórica cada vez que hay un split — incluso
para fechas anteriores al split. `rfx20_composition.parquet` viene de
snapshots congelados (`Cartera Historica`), nunca retocados. Resultado: para
tickers con splits *posteriores* a la fecha consultada, composición (nominal)
queda por encima de OHLCV (ya ajustado), por el factor acumulado de todos los
splits futuros.

- **YPFD**: ratio constante ×10 en toda la historia pre-split. Un solo split
  10:1 (2026-08-03, ver `docs/decisions/ypfd_split_2026.md`). Completamente
  explicado.
- **BYMA**: el ratio **no** es constante, baja en escalones exactos con el
  tiempo:

  | período | ratio |
  |---|---:|
  | antes de 2022-07-06 | 100 |
  | 2022-07-07 → 2024-05-09 | 10 |
  | 2024-05-13 → 2025-05-23 | 2 |
  | desde 2025-05-26 | 1 |

  Los dos splits ya documentados en `splits.yaml` (10:1 en 2022, 5:1 en 2024)
  solo explicaban un factor acumulado de 50x, no 100x. **Resuelto (16 sep
  2026):** el alumno confirmó contra el historial oficial de splits de BYMA
  un tercer desdoblamiento **2:1 el 2025-05-25**, no documentado hasta ahora.
  Verificado en los datos: ratio=2.0 el 2025-05-23, ratio=1.0 el 2025-05-26.
  Agregado a `splits:` en `config/splits.yaml`.

Como septiembre 2019 es anterior al split BYMA de 2022, para esta ventana el
factor crónico de BYMA es ×100 y el de YPFD es ×10 — hay que tenerlo en cuenta
al construir la corrección (sección siguiente), sin confundirlo con la
anomalía real de esta semana.

## Decisión

Igual que en los casos ya resueltos (BBAR en `dirty_data`, cambio de base
oct-2023 en `index_base_changes`): **no se edita ningún archivo de
`data/raw/`** (son inmutables por convención del proyecto). La corrección se
aplica en la capa de `processing/`, de forma declarativa desde
`config/splits.yaml`, reproducible y documentada.

### Composición (`rfx20_composition.parquet`)

Nueva sección `composition_price_corrections` en `splits.yaml` (100 entradas:
20 tickers × 5 fechas, 2019-09-23 → 2019-09-27). `fix` = `close` del OHLCV
canónico para ese ticker/fecha, excepto:

- **BYMA**: `close_ohlcv × 100` (para quedar en la misma base nominal que el
  resto de la serie de composición en ese período — pegar el valor OHLCV
  crudo generaría un salto artificial nuevo en el borde 22/09→23/09 y
  27/09→30/09).
- **YPFD**: `close_ohlcv × 10`, mismo motivo.

Nueva función `processing/cleaner.py::apply_composition_price_corrections()`,
separada de `apply_corrections()` (la de OHLCV por ticker) a propósito: si
compartieran la misma lista `dirty_data`, un fix reescalado ×100 pensado para
la composición podría filtrarse por error al OHLCV real de BYMA si alguna vez
se invoca `apply_corrections` sobre ese ticker. Aplicada en
`app.py::compute_index_reconstruction()`.

### Spot (`rfx20_spot.parquet` → target del modelo)

5 entradas nuevas en `dirty_data` (ticker `RFX20`, campo `close`), una por
fecha. `fix` = `Σ(quantity_i × close_corregido_i)` sobre los 20 componentes,
con las `quantity` originales (correctas, sin tocar) y el `close` corregido de
la sección anterior:

| fecha | spot original (corrupto) | spot corregido |
|---|---:|---:|
| 2019-09-23 | 77.080,92 | 40.205,49 |
| 2019-09-24 | 71.795,88 | 38.453,64 |
| 2019-09-25 | 72.653,59 | 38.530,05 |
| 2019-09-26 | 72.522,30 | 38.331,19 |
| 2019-09-27 | 74.146,57 | 38.912,65 |

Reutiliza `apply_corrections()` (mismo mecanismo que BBAR) pasando
`ticker="RFX20"` — no hay colisión posible porque RFX20 no es un ticker real
de OHLCV. Aplicada en `features/target.py::build_index_target()`, **antes**
del ajuste de cambio de base (`SplitAdjuster.adjust_index_series`), sobre la
escala nominal cruda — el ajuste de base se sigue aplicando después, igual que
al resto de la serie pre-octubre-2023.

## Resultado

`log_return` del índice para la ventana, antes/después:

| fecha | log_return original | log_return corregido |
|---|---:|---:|
| 2019-09-23 | +0.626 | -0.024 |
| 2019-09-24 | -0.071 | -0.045 |
| 2019-09-25 | +0.012 | +0.020 |
| 2019-09-26 | -0.002 | -0.005 |
| 2019-09-27 | +0.022 | +0.015 |
| 2019-09-30 | -0.641 | +0.004 |

Serie continua y de magnitud normal en todo el tramo. `compute_index_reconstruction()`
vuelve a coincidir (reconstrucción ≈ spot, error ~1e-7%) para estas 5 fechas,
igual que en el resto de la serie.

Impacto en Bloque 2 (Track A + Track B): estos 5 días (de 2.041, 0,24%) también
contaminaban las ventanas rodantes de `realized_vol_10/20/50` durante
~2-10 semanas alrededor de esta fecha, y los `log_return_fwd_{1,3,5}` de los
días inmediatamente anteriores. Dado que es una fracción muy pequeña de la
serie, no se espera que cambie la conclusión de síntesis (ningún método
predice dirección), pero **si se re-entrena** cualquier modelo de Bloque 2 el
dataset de features ya sale corregido (`features.runner` fue re-ejecutado);
queda pendiente decidir si vale la pena re-correr Bloque 2 completo solo por
esto.

## Pendientes

1. **Recomposición de cartera desfasada 1 día hábil** (hallazgo #4): el
   `rfx20_composition.parquet` local marca la cartera nueva (salida
   APBR/TS, entrada CVH/LOMA) el 2019-09-30, pero el API de MatbaRofex la
   marca el 2019-10-01. Podría repetirse en otras recomposiciones trimestrales
   de toda la serie 2018-2026 — no se auditó ese alcance todavía.
2. ~~Tercer split de BYMA no documentado~~ — **resuelto (16 sep 2026)**:
   2:1 el 2025-05-25, confirmado por el alumno y agregado a `splits.yaml`.
3. **MIRG**: 970 días (~mitad de la historia) con desvío composición-vs-OHLCV
   no investigado — candidato a tener un split propio no documentado, mismo
   mecanismo que YPFD/BYMA.
4. **Cluster menor 2024-05-13 → 2024-05-17** (5-8%, pocos tickers: CRES,
   TECO2, LOMA, BBAR, GGAL, TGSU2, CEPU, TGNO4, AGRO): coincide con la fecha
   del split BYMA 2024-05-10, probablemente ruido de timing del snapshot de
   composición — mucho menor magnitud que los casos anteriores, no
   investigado a fondo.

## Archivos de soporte

- `docs/diagnostics/composicion_vs_ohlcv_sep2019.csv` — diff completo
  composición vs. OHLCV, toda la historia.
- `docs/diagnostics/composicion_correction_sep2019.csv` — detalle del cálculo
  de corrección por ticker/fecha.
- `docs/diagnostics/spot_correction_sep2019.csv` — spot corregido por fecha.
