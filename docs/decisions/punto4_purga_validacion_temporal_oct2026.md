# Punto 4 del feedback de los directores: protocolo de validación temporal

**Fecha:** 3 de noviembre de 2026
**Módulos:** `models/ml/common.py`, `models/deep_learning/common.py`
**Origen:** Punto 4 del feedback de los directores de tesis (Fernanda Mendez /
Rodrigo Del Rosso): refuerzo del protocolo de validación temporal (purga de
fuga por superposición de objetivos, ajuste de escaladores exclusivamente
dentro de cada fold, documentación del test reservado, y asimetría de
actualización entre ARIMA/GARCH y el resto de los modelos).

## Contexto

El director señala que la fuga por superposición de objetivos (las últimas
etiquetas de `train` miran precios que ya pertenecen a `val`) no es
despreciable aunque sean pocas observaciones, y pide verificarla en tres
lugares: el corte final train/val, los folds internos de búsqueda de
hiperparámetros, y la porción de early stopping. También pide confirmar que
los escaladores se ajustan exclusivamente dentro del entrenamiento
correspondiente a cada fold.

Este punto se resolvió en el mismo cambio de código que el Punto 3 (target
acumulado — un target acumulado agrava el problema de ventanas superpuestas,
así que se atendieron juntos). Ver
`docs/decisions/punto3_target_cumulativo_oct2026.md` para el detalle del
cambio de target.

## Verificación, código por código

**1. Corte final train/val — `purge_horizon`.** Antes de este cambio,
`purged_splits` (`models/ml/common.py`) solo purgaba folds internos de
`RandomizedSearchCV`; nada purgaba las últimas `horizon` filas de `train`
antes del fit final contra `val`. Se agregó el parámetro `purge_horizon` a
`split_arrays()`:

```python
if purge_horizon > 0 and split == "train":
    subset = subset.head(max(0, subset.height - purge_horizon))
```

Confirmado activo en los 4 runners de ML (SVM/RF/XGBoost/LightGBM):
`split_arrays(model_frame, "train", purge_horizon=h)` para train,
`split_arrays(model_frame, "val")` (sin purga, correcto) para val.

**2. Folds internos de CV.** `purged_splits` ya existía (trabajo de
horizontes largos, sep-2026) y sigue siendo el `cv=` que recibe
`RandomizedSearchCV` dentro de `tune_and_evaluate` — purga el solapamiento
dentro de cada fold de búsqueda de hiperparámetros, no solo en el corte
final. Sin cambios necesarios acá, ya cumplía el requisito.

**3. Porción de early stopping (Deep Learning) — `purge_train_tail`.** Se
agregó a `models/deep_learning/common.py`, análogo a `purge_horizon` pero
sobre secuencias ventaneadas en vez de filas planas. El orden de operaciones
en `select_lookback()` es:

```
build_sequences → purge_train_tail → chronological_earlystop_split → scale_sequences
```

Es decir, la purga ocurre **antes** de recortar la porción de early
stopping — así esa porción tampoco mira hacia `val`, porque sale de la cola
de un `train` ya purgado. Confirmado activo en los 4 runners de DL
(LSTM/GRU/CNN-LSTM/TFT-lite): `select_lookback(..., purge_horizon=h)`.

**4. Escaladores ajustados solo dentro de cada fold.**
- **SVM**: `StandardScaler` dentro de un `sklearn.Pipeline` junto con `SVR`,
  alimentado a `RandomizedSearchCV(cv=purged_splits(...))` — sklearn reajusta
  el scaler en cada fold usando solo el train de ese fold; el fit final usa
  únicamente `X_train` (ya purgado), `X_val` solo se transforma, nunca se usa
  para ajustar.
- **Deep Learning**: `scale_sequences()` ajusta el `StandardScaler`
  exclusivamente sobre `fit_seq.X` (el train purgado, sin la porción de early
  stopping) y reutiliza ese mismo scaler — nunca lo reajusta — para
  transformar early stopping y, después, `val` (`evaluate()` llama
  `result.scaler.transform(...)`, nunca `.fit()`).

**Conclusión de la verificación: los 4 requisitos de purga/escalado ya
estaban activos en la re-corrida completa de Bloque 2 documentada en
`docs/decisions/punto3_target_cumulativo_oct2026.md`** — los resultados de
esa tabla ya cumplen el protocolo que pide este punto, no hace falta
re-correr nada de nuevo por este motivo.

## Pendiente — documentación, no afecta resultados numéricos

- **Test reservado**: documentar cuándo quedó reservado (`features/temporal_split.py`,
  ver `docs/decisions/temporal_split_and_consolidation.md` — test = 86 filas,
  2026-04-20 → 2026-08-25, 100% out-of-sample), qué resultados se observaron
  ahí, y si se modificó alguna decisión de desarrollo después de fijarlo. El
  director aclara explícitamente que ser histórico no garantiza
  independencia por sí solo — lo determinante es que no haya intervenido en
  decisiones de desarrollo, y eso hay que dejarlo trazado por escrito, no
  solo asumido.
- **Predictores disponibles en el tramo de test**: confirmar que para esas 86
  filas estén disponibles todos los predictores usados (macro, futuros,
  TAMAR/BADLAR, no solo el spot del índice) — pendiente de verificación
  explícita.
- **Asimetría de refit ARIMA/GARCH (diario) vs. resto (fijo)**: explicitar
  este hecho en la redacción de metodología. Opcional, si resulta viable:
  una comprobación acotada con una frecuencia de actualización comparable
  (ej. refit semanal en vez de diario para ARIMA/GARCH, o reentrenos
  periódicos para los modelos de ML/DL) — no se priorizó en esta ronda.
