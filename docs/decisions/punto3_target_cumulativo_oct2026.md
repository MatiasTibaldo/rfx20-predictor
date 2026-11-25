# Punto 3 del feedback de los directores: target acumulado (no retorno de un solo día)

**Fecha:** 30 de octubre - 3 de noviembre de 2026
**Módulos:** `processing/returns.py`, `models/statistical/arima.py`, `models/statistical/garch.py`,
`models/statistical/garch_runner.py`, `models/ml/common.py` + 4 runners (RF/SVM/XGBoost/LightGBM),
`models/deep_learning/common.py` + 4 runners (LSTM/GRU/CNN-LSTM/TFT-lite)
**Origen:** Punto 3 del feedback de los directores de tesis (Fernanda Mendez / Rodrigo Del Rosso).
La purga de borde train/val que motivó el mismo cambio de código se documenta aparte, en
`docs/decisions/punto4_purga_validacion_temporal_oct2026.md` (Punto 4 del feedback).

## Contexto

Los directores notaron que el RMSE naive (predecir retorno 0) era casi idéntico
en h=1/3/5 en las tablas ya reportadas — señal de que `log_return_fwd_h` podía
no ser el retorno acumulado de h días que describe la Sección 4.2.2 de la tesis
(`Rt+h = ln(Pt+h/Pt)`), sino el retorno de un único día, el día t+h.

**Confirmado en código:** `processing/returns.py::add_returns` calculaba
`log_return_fwd_h = log_return.shift(-h)` — exactamente el retorno de un solo
día en t+h, no el acumulado. Esto explica el síntoma: los tres horizontes
respondían, en los hechos, la misma pregunta (¿cuál es el retorno de un día
cualquiera?), solo que leída con distinto desfasaje.

## El cambio

`log_return_fwd_h` ahora es el retorno **acumulado** de t a t+h:

```
ln(close_t+h / close_t)  ≡  suma de los h retornos diarios siguientes
```

Calculado directamente desde `close` (no como suma de columnas `log_return`
desplazadas), para evitar arrastre de error de punto flotante.

Para h=1 ambas definiciones coinciden exactamente (el retorno acumulado de 1
día es, por definición, el retorno de ese día) — el cambio solo tiene efecto
real en h=3 y h=5.

## Ajustes relacionados, necesarios para ser consistentes con el nuevo target

- **ARIMA** (`arima.py::walk_forward_evaluate`): el pronóstico a horizonte h
  pasó de `forecast[h-1]` (el punto h-ésimo) a `sum(forecast[:h])` (suma de
  los primeros h pronósticos de un paso) — así el pronóstico es del mismo
  tipo de cantidad que ahora mide el target.
- **GARCH** (`garch.py::walk_forward_evaluate_variance`): análogamente,
  `variance_forecast[h-1]` → `sum(variance_forecast[:h])`. Exacto, no una
  aproximación, bajo la especificación `mean="Zero"` ya usada: retornos
  condicionalmente incorrelacionados entre días ⇒ Var(suma) = suma(Var).
- **Bug encontrado en el camino — naive de GARCH** (`garch_runner.py`):
  `_naive_variance_metrics` comparaba contra `train_variance` (varianza de
  un solo día) como constante en los tres horizontes. Con target acumulado,
  el naive correcto escala como `h × train_variance`. Sin este fix el naive
  quedaba artificialmente chico en h=3/h=5, inflando la mejora aparente de
  GARCH sobre él.
- **Purga de borde train/val** (Punto 4 del feedback, resuelto en la misma
  pasada porque un target acumulado agrava el problema de ventanas
  superpuestas): se agregó `purge_horizon` a
  `models/ml/common.py::split_arrays` y `purge_train_tail` a
  `models/deep_learning/common.py`. Ver
  `docs/decisions/punto4_purga_validacion_temporal_oct2026.md` para el detalle
  completo y la verificación de que esta purga estaba activa en la re-corrida
  de más abajo.

## Validación manual

Caso 2023-06-01 (el mismo usado en otros ejemplos del proyecto):

| Fecha | Close | log_return (diario) |
|---|---:|---:|
| 2023-06-01 | 48.155,81 | +3,76% |
| 2023-06-02 | 48.195,28 | +0,08% |
| 2023-06-05 | 49.245,12 | +2,15% |
| 2023-06-06 | 51.956,82 | +5,36% |
| 2023-06-07 | 52.133,05 | +0,34% |
| 2023-06-08 | 52.285,77 | +0,29% |

| Horizonte | Columna `log_return_fwd_h` | Manual: ln(close_t+h/close_t) | Manual: suma de retornos diarios |
|---|---:|---:|---:|
| 1 | 0,000819 | 0,000819 | 0,000819 |
| 3 | 0,075971 | 0,075971 | 0,075971 |
| 5 | 0,082282 | 0,082282 | 0,082282 |

Las tres columnas coinciden al dígito en los tres horizontes. Verificado también
en 3 fechas adicionales elegidas al azar (diff=0.00e+00). Esta misma validación
está disponible de forma interactiva en Streamlit → "Validación de datos" →
"Dataset de modelado" (cualquier fecha, no solo este ejemplo).

Como diagnóstico adicional: el RMSE naive sobre val pasó de ser casi idéntico
entre horizontes a escalar razonablemente con √h:

| Horizonte | RMSE naive (antes — bug) | RMSE naive (ahora — correcto) |
|---|---:|---:|
| 1 | 0,029553 | 0,029553 (sin cambio, por definición) |
| 3 | 0,029531 | 0,052421 |
| 5 | 0,029479 | 0,068560 |

## Resultado — Bloque 2 completo, re-corrido sobre el pipeline corregido

% de RMSE vs. naive (RMSE de varianza y QLIKE para GARCH), conjunto de validación:

| Modelo | h=1 | h=3 | h=5 |
|---|---:|---:|---:|
| ARIMA (orden real (0,0,1), no (0,0,0) — ver nota abajo) | -0,06% | +0,06% | -0,12% |
| GARCH(1,1) t-Student | +0,88% | +1,03% | +1,42% |
| Random Forest | -0,12% | +2,81% | +3,50% |
| SVM | +0,47% | +0,32% | +2,68% |
| XGBoost | +2,80% | +8,47% | +5,84% |
| LightGBM | +4,08% | +6,37% | +5,85% |
| LSTM (feature set narrow) | +1,04% | +0,48% | +1,57% |
| GRU (narrow) | +1,84% | +3,61% | +5,20% |
| CNN-LSTM (narrow) | +2,15% | +2,19% | +1,04% |
| TFT-lite (narrow) | +2,50% | +6,15% | +5,41% |

**Nota sobre ARIMA — responde la inconsistencia puntual que señala el director
en h=1:** la documentación previa (`docs/decisions/arima_baseline_track_a.md`,
`docs/tesis/proyecto_final_tibaldo.md` Tabla 5.1) describe el orden ganador
como (0,0,0) — idéntico al naive por construcción. La corrida con el target
corregido selecciona en cambio **(0,0,1)** (AIC=-6996.37, un MA(1)), confirmado
dos veces de forma independiente (la corrida de esta ronda y, antes de
corregir el target, una inspección directa de
`results/track_a/arima_val_predictions.parquet` que ya mostraba el mismo
orden). Un MA(1) **no es idéntico** al naive de retorno cero: aporta un
ajuste mínimo dependiente del residuo más reciente, que explica la pequeña
diferencia en h=1 (0,029536 vs. 0,029553) y se diluye en h=3/h=5 porque el
componente MA no tiene memoria más allá de un paso. No es un problema de
especificación, de alineación temporal, ni una versión vieja de resultados —
es el comportamiento esperado de un MA(1) real. La documentación de Track A
queda pendiente de actualizar para no seguir citando (0,0,0).

## Lectura e implicancias

**La conclusión central no cambia**: ningún modelo le gana de forma consistente
al naive, ni siquiera corrigiendo la definición del target. Es, si acaso, un
resultado más sólido para la tesis — "no hay señal" ya no depende de una
posible mala especificación del objetivo.

El Punto 2 del feedback (homogeneidad del cambio de base oct-2023 y
reconciliación reconstrucción-vs-spot) se resolvió por separado — ver
`docs/decisions/punto2_reconciliacion_oct2026.md` — y confirma que el target
que entrenó esta batería nunca vio el artefacto del cambio de base. El Punto 4
(purga de validación temporal) se verificó como ya satisfecho por el mismo
código usado en esta re-corrida — ver
`docs/decisions/punto4_purga_validacion_temporal_oct2026.md`.

## Pendiente

- Actualizar `docs/decisions/arima_baseline_track_a.md` y el resto de los
  `docs/decisions/*.md` de Bloque 2 que todavía citan el target viejo
  (`garch_volatility_track_a.md` ya corregido, ver
  `docs/decisions/punto8_garch_evaluacion_completa_nov2026.md`).
- **[Hecho 6-nov-2026]** `docs/tesis/proyecto_final_tibaldo.md` sección
  5.1.1 y Tabla 5.1 (ARIMA) corregidas: orden real (0,0,1, AIC=-6996,37),
  cifras del target acumulado, y las estadísticas de diagnóstico
  (std/asimetría de train, Ljung-Box, ARCH-LM) recalculadas sobre los datos
  ya corregidos — citaban valores de una versión de los datos previa a los
  Puntos 2 y 3 (std 6,7% en vez de 2,93%; asimetría -24 en vez de -1,17) que
  nadie había notado hasta ahora. `docs/tesis/draf_proyecto_final_google_docs.md`
  no llega todavía a estas tablas.
- `docs/avance_trabajo_final.md` (sección 4.2.1) ya corregido en el mismo
  pase que el Punto 8 — tabla de ARIMA/GARCH con el target acumulado,
  orden real de ARIMA, QLIKE y EWMA.
- Actualizar `CLAUDE.md` con el nuevo estado de Bloque 2 (hecho en esta misma
  sesión, ver sección "Punto 3" de `CLAUDE.md`).
- Regenerar `evaluation/figures.py` (los PNG de `docs/figures/` tienen los
  números viejos).

## Nota de conciliación (6-nov-2026): el pendiente de arriba se concretó a medias, y se detectó en el feedback de seguimiento

El ítem "actualizar el resto de los decision docs / tesis" quedó marcado
como pendiente desde el 4-nov-2026, pero solo se ejecutó parcialmente: las
Tablas 5.1 (ARIMA) y 5.2 (GARCH) de la tesis sí se corrigieron (ver arriba),
pero las **Tablas 5.3 a 5.7** (SVM/RF/XGBoost/LightGBM, LSTM/GRU acotado y
completo, CNN-LSTM/Transformer encoder, y la síntesis) **quedaron sin
regenerar** — seguían citando el naive de un solo día (~0,0295 en $h=3$/
$h=5$) de la tabla "antes — bug" de este mismo documento, en vez del
acumulado correcto que esta misma sección ya documentaba desde el
3-nov-2026. Lo mismo ocurría en `docs/avance_trabajo_final.md`.

Esto salió a la luz en el feedback de seguimiento de los directores
(6-nov-2026) sobre la versión con los ajustes de las Fases A/B: notaron que
la Tabla 5.9 (bootstrap, agregada en esa misma ronda con los números
correctos) no coincidía con la Tabla 5.3 para las mismas combinaciones
(modelo, horizonte) — exactamente el síntoma de este gap. Corregido en el
mismo pase: las 5 tablas regeneradas contra
`results/punto9_bootstrap/bootstrap_ci_summary.parquet` (fuente única,
consistente con la Tabla 5.9 por construcción) y
`results/track_b_full_baseline/` para la Tabla 5.5, en la tesis y en
`docs/avance_trabajo_final.md`. Quedan sin tocar, señalados como deuda
técnica explícita (no son el documento bajo revisión de los directores):
`arima_baseline_track_a.md`, `rf_track_a.md`, `svm_track_a.md`,
`lightgbm_track_a.md`, `lstm_baseline_track_b.md` y
`track_b_etapa2_gru_full_features.md`.
