# Punto 2 del feedback de los directores: reconciliación completa (30 oct 2026)

**Fecha:** 30 de octubre de 2026
**Origen:** Punto 2 del feedback de los directores de tesis (homogeneidad del
cambio de base oct-2023 + validación de la reconciliación reconstrucción-vs-spot
sobre toda la historia).

## 1. Homogeneidad de base a ambos lados del corte oct-2023

Verificado directamente sobre `log_return` del dataset real de entrenamiento
(`data/features/v1/features_long.parquet`, construido por
`features/target.py::build_index_target()`), no solo sobre el spot crudo.

El spot oficial (`rfx20_spot.parquet`) sí tiene la discontinuidad cruda: pasa de
861.644,97 (06-oct-2023) a 88.673,98 (09-oct-2023) — factor exacto ~10x. Sin
corrección, `log_return` de esa fecha sería **-2.27 (-89.7% en un día)**. Pero
el ajuste ya existente (`config/data_corrections.yaml::index_base_changes`,
consumido por `SplitAdjuster().adjust_index_series()` **antes** de calcular
retornos) reescala hacia atrás todo el historial previo al 09-oct-2023 (÷10).
Verificado en el dataset real: `log_return` del 09-oct-2023 queda en **+0.0287
(+2.9%)**, un movimiento de mercado normal, consistente con los días vecinos.

Barrido de 3 semanas antes/después del corte (18-sep a 30-oct-2023,
`features_long.parquet`): el único `|log_return| > 10%` en toda la ventana es
**23-oct-2023, -12.5%** — coincide con la reacción de mercado a la 1ª vuelta
presidencial (22-oct-2023, domingo), ya identificado de forma independiente en
el Punto 1 (TXAR mostraba -22.8% el mismo día, ver
`docs/decisions/validacion_manual_splits_oct2026.md`). **Sin residuo del salto
de base** — el ajuste está limpio y el target que entrena los modelos nunca vio
la discontinuidad cruda.

## 2. Reconciliación reconstrucción-vs-spot, toda la historia

Dos métodos de reconstrucción coexisten en el repo:

- `processing/reconstruction.py::reconstruct_index` — mezcla
  `composición.quantity × OHLCV.close` (una fuente para `quantity`, otra para
  `close`). Clasificado como **"⚠️ inseguro"** en
  `docs/decisions/fuentes_independientes_composicion_ohlcv.md`.
- `app.py::compute_index_reconstruction` — usa `composición.quantity ×
  composición.close`, **una sola fuente**. Clasificado como **"✅ seguro"**.

Re-corriendo ambos sobre toda la historia (1981 días, 2018-06-29 a hoy) tras
las 2 correcciones del Punto 1 (COME, AGRO):

| Método | Días fuera de tolerancia (>1%) | % |
|---|---|---|
| Mezcla (`processing/reconstruction.py`) | ~1965/1981 | 99.2% |
| Fuente única (`app.py`) | **4/1981** | **0.20%** |

**Hallazgo principal: el 99.2% de error crónico no era un problema de datos —
era el artefacto de mezclar `composición.quantity` con `OHLCV.close`** para
BYMA/YPFD/MIRG, que no comparten la misma base de precio entre ambas fuentes
(ver `docs/decisions/fuentes_independientes_composicion_ohlcv.md`). Con la
reconstrucción de fuente única, ese 99.2% desaparece, incluyendo el cluster
2020-06-30 que había aparecido en la primera re-corrida (no es una anomalía
real, era parte del mismo artefacto de mezcla).

### Conclusión para el pipeline de reconciliación

`processing/reconstruction.py` debería migrar al método de fuente única de
`app.py` (o consumir `composition_only_splits` para reconciliar la base antes
de mezclar) — queda como mejora pendiente, no urgente porque esta
reconciliación es una validación de monitoreo, no alimenta ningún feature de
entrenamiento.

## 3. Cluster mayo-2024 (4 días, máx 3.25%) — explicado, cerrado

Único residuo real tras el método de fuente única: **13, 14, 15 y 17 de mayo
de 2024**, error 1.29%-3.25%. Ya estaba anotado como pendiente en `CLAUDE.md`
("cluster menor may-2024, sin investigar") y en
`docs/decisions/base_change_oct2023.md`.

**Descartado como error de datos, explicado como ruido de snapshot entre
fuentes:**

- El divisor no cambia en ningún día de este rango (05-10 a 05-16 son todos el
  mismo divisor) y las `quantity` de las 20 componentes están **congeladas,
  idénticas** durante toda la ventana — descarta un problema de
  cantidades/rebalanceo.
- Comparando `composición.close` vs `OHLCV.close` ticker por ticker: en
  05-09, 05-10 y 05-20 el ratio es exactamente 1.0 (o el ratio estructural
  conocido de BYMA/COME/YPFD) para las 20 componentes. En **05-13 a 05-17**,
  **las 20 componentes simultáneamente** se desvían 1-6% del ratio esperado,
  cada una en magnitud y signo distintos — no es un ticker puntual, no es un
  factor uniforme, no es un desfasaje limpio de ±1 día.
- Esa semana fue la de mayor volatilidad diaria del período (retornos entre
  -1.75% y +4.36%). El patrón (desvío simultáneo, pequeño, no sistemático, en
  todas las componentes a la vez) es consistente con que composición y OHLCV
  capturan el cierre en instantes ligeramente distintos (ej. subasta de cierre
  vs. última operación) — normalmente invisible porque el precio no se mueve
  en esa ventana de tiempo, pero visible en una semana inusualmente volátil.

**No requiere corrección.** Es ruido de snapshot acotado (máx 3.25% a nivel
índice, 4 días en 7+ años de historia), consistente con el principio ya
documentado de que composición y OHLCV son fuentes independientes que no
están garantizadas a coincidir al centavo fuera de los splits ya
reconciliados.

## Estado del Punto 2

Los 3 sub-puntos (homogeneidad de base, estadísticas descriptivas, 
reconciliación completa) quedan cerrados. Sin impacto en el dataset de
entrenamiento (`features_long.parquet` no usa reconstrucción ni OHLCV por
componente).
