# Punto 5 del feedback de los directores: precauciones sobre variantes de componentes

**Fecha:** 4 de noviembre de 2026
**Módulos:** `scripts/punto5_common_predictor_set.py` (nuevo),
`scripts/punto5_availability_mask.py` (nuevo), `data/features/v1/features_long_compA.parquet`
y `features_long_compC_masked.parquet` (nuevos, git-ignored, regenerables)
**Origen:** Punto 5 del feedback de los directores de tesis (Fernanda Mendez /
Rodrigo Del Rosso), sobre las variantes de dataset con datos de composición
(A-F, exploradas antes de este punto del feedback — ver conversación de
elección del dataset A).

## 1. Preferencia por variantes normalizadas

El director considera las versiones normalizadas (peso, retorno) más
defendibles que las crudas (cantidad, precio) porque estas últimas arrastran
efectos de escala — inflación, splits, rebalanceos de la cartera — que se
mezclan con la información económica real. Esto coincide con la decisión ya
tomada en el proyecto: **dataset A (ranking top-20 por peso + retorno,
normalizado) es la representación principal**, no las variantes crudas B/D
(cantidad/close) ni las variantes con OHLCV completo E/F (que además mezclan
niveles absolutos entre composición y OHLCV — ver
`docs/decisions/fuentes_independientes_composicion_ohlcv.md`).

Queda documentado explícitamente el motivo: `weight` (peso normalizado,
`quantity × close / Σ`) es invariante a cualquier redenominación o split —
una acción que vale 10x menos nominal tras un split sigue teniendo el mismo
peso en el índice. `quantity`/`close` crudos, en cambio, saltan con cada
split y no son comparables entre sí a través del tiempo sin reconciliar la
base (el mismo problema que motivó el Punto 1 y el Punto 2 del feedback).

## 2. El ranking por peso no fija la identidad de la empresa

El director señala que, en una ventana de una red recurrente, la columna
"primera posición" (rank01) puede representar compañías distintas entre
días — esto no invalida el enfoque, pero cambia su interpretación y debe
quedar explicado.

**Verificado empíricamente** sobre los ~1983 días de historia con
composición disponible: **3 tickers distintos** ocuparon la posición rank01
en algún momento (GGAL: 1029 días, YPFD: 735, APBR: 219), con **85 cambios
de identidad** a lo largo de la serie.

**Implicancia para la interpretación**: una columna como `rank01_weight` o
`rank01_return` no representa "el comportamiento de una empresa fija" sino
"el comportamiento de quien sea el líder del índice ese día". Un modelo que
aprenda de esta columna está aprendiendo sobre la dinámica de concentración
del índice (cuánto pesa y cómo se mueve el líder, sea quien sea), no sobre
una empresa en particular. Esto es economía legítima para predecir el índice
agregado (que es, al fin, una suma ponderada de sus componentes), pero no
debe leerse como "GGAL predice al RFX20" solo porque `rank01` resultó
importante en la importancia por permutación — el director tiene razón en
que esto merece una aclaración explícita en la redacción, no solo en el
código.

## 3. Máscara de disponibilidad explícita para esquemas por ticker — implementado y probado

Para los esquemas por ticker (variante C: peso+retorno fijo por cada una de
las 28 componentes históricas, 56 columnas), el director sugiere distinguir
"ausencia del índice" de "falta de cotización", conservando el dato
original como nulo pero agregando, en la matriz del modelo, una codificación
explícita (relleno) acompañada de una máscara de pertenencia/disponibilidad
— así SVM y las redes pueden usar el dato sin que el relleno se presente
como una observación real. El propio director aclara que es **una
alternativa a considerar, no una obligación**.

**Implementado** en `scripts/punto5_availability_mask.py::build_masked_dataset()`:
para cada uno de los 28 tickers se agrega un flag `{TICKER}_in_index`
(1/0) y las columnas `{TICKER}_weight`/`{TICKER}_return` se rellenan con 0.0
únicamente cuando el flag ya indica la ausencia — el modelo siempre ve el
par (valor, flag) junto, nunca el valor de relleno sin su indicador. Esto es
conceptualmente distinto de la regla general del proyecto de "nunca imputar
datos reales faltantes" (ver `CLAUDE.md`): ahí se prohíbe presentar un
relleno como si fuera una observación real; acá el relleno viene siempre
acompañado de la señal explícita de que no lo es — el patrón estándar de
"missing indicator" en la literatura de ML, no una imputación oculta.

**Resultado (SVM — único candidato clásico, dataset_name=`features_long_compC_masked`,
runner real `models.ml.svm_runner`):**

| Horizonte | RMSE (% vs. naive) |
|---|---:|
| 1 | +0,31% |
| 3 | +0,86% |
| 5 | +2,81% |

Prácticamente empatado con SVM sobre dataset A (+0,47/+0,32/+2,68% con el
target narrow del Punto 3, +0,34/+0,97/+1,57% con el conjunto común del
ítem 4) — la metodología **funciona técnicamente sin problemas** (sin NaN,
sin errores de ejecución), pero el acceso a la granularidad por ticker no
aporta señal adicional. Resultado negativo, pero limpio y metodológicamente
válido.

**Resultado (LSTM, mismo dataset, `feature_set="full"`):** +510,85% / +274,31%
/ +210,51% vs. naive — el peor resultado de toda la batería de Bloque 2.
Mismo patrón de sobreajuste severo que ya se ve en el ítem 4 con el
conjunto "full" de predictores (ver abajo), agravado acá por las 84
columnas adicionales (28 flags + 56 valores) sobre un dataset de ~1600 filas
de train. **La máscara no es un remedio para esto** — el problema de fondo
es la dimensionalidad frente al tamaño de muestra, no el tratamiento de los
nulos.

**Conclusión**: la máscara de disponibilidad es una técnica válida y queda
documentada como tal, viable para SVM (y en principio para los modelos de
árbol, que de hecho ya toleran los nulos reales nativamente sin necesitar
esta técnica). Para Deep Learning no es útil en este proyecto — el límite
real es el tamaño de la muestra frente a la dimensionalidad del feature set
"full"/por ticker, no la forma en que se codifican los nulos.

## 4. Comparación con un conjunto común de predictores entre familias — implementado y probado

El director observa que hoy algunos modelos reciben variables que otros
excluyen por sus faltantes (confirmado en código: `build_model_frame(...,
exclude_structural_gaps=True)` hace que SVM descarte las columnas de
futuros/TAMAR/MEP por completo, mientras que RF/XGBoost/LightGBM las reciben
con nulos reales; en el dataset de composición, los modelos de árbol además
pudieron usar variantes por ticker (C/D/F) que SVM/DL nunca tocaron) — pide
una comparación con un conjunto común para aislar cuánta diferencia viene
del algoritmo y cuánta de la información disponible.

**Implementado** en `scripts/punto5_common_predictor_set.py`, usando los
runners reales (ya con `purge_horizon` del Punto 4 y el target acumulado del
Punto 3): los 8 modelos aplicables (ARIMA/GARCH quedan afuera — son
univariados) evaluados sobre el mismo conjunto de predictores — el
`feature_set="full"` ya existente en el proyecto (24 predictores de Track A,
gaps estructurales excluidos, el mismo tratamiento para todas las familias)
más, para la variante A, las 40 columnas de ranking peso+retorno.

**Baseline-full vs. A-full, RMSE (% vs. naive):**

| Modelo | Baseline-full h=1 | h=3 | h=5 | A-full h=1 | h=3 | h=5 |
|---|---:|---:|---:|---:|---:|---:|
| RF | (ver nota) | | | +0,34% | +5,92% | +8,84% |
| SVM | (ver nota) | | | +0,34% | +0,97% | +1,57% |
| XGBoost | (ver nota) | | | +3,12% | +7,73% | +12,14% |
| LightGBM | (ver nota) | | | +3,56% | +18,38% | +17,37% |
| LSTM | +170,77% | +81,97% | +60,78% | +324,58% | +190,26% | +135,27% |
| GRU | +196,20% | +106,48% | +77,19% | +352,87% | +218,24% | +164,50% |
| CNN-LSTM | +19,13% | +28,44% | +32,12% | +15,94% | +16,40% | +33,55% |
| TFT-lite | +123,08% | +41,33% | +128,44% | +161,69% | +128,13% | +140,79% |

Nota: para RF/SVM/XGBoost/LightGBM, "Baseline-full" con el conjunto común ya
está cubierto por la re-corrida de `features_long` del Punto 3 (estos 4
modelos clásicos no distinguen "narrow" vs. "full" — siempre usan el
conjunto completo salvo los gaps estructurales); no se repite acá, la
columna de la derecha (A-full) es el agregado real de este punto. Para
LSTM/GRU/CNN-LSTM/TFT-lite sí hubo que re-correr Baseline-full fresco, ya
que la numeración oficial de Track B usa `feature_set="narrow"`.

**Hallazgo principal, no anticipado**: con `feature_set="full"` (24
predictores, el único conjunto verdaderamente común entre las 8 familias),
**LSTM/GRU/TFT-lite colapsan** — entre 61% y 353% peor que el naive, muy por
encima de lo ya documentado para LSTM/GRU en
`docs/decisions/track_b_etapa2_gru_full_features.md` (que hablaba de "2-2.5x
el naive") y ahora confirmado también para TFT-lite, que no se había
probado con "full" hasta este punto. **CNN-LSTM es la única arquitectura de
Deep Learning que tolera razonablemente el conjunto común** (16%-34% peor
que el naive, en línea con los modelos clásicos). Agregar la variante A
empeora aún más a LSTM/GRU/TFT-lite, pero deja a CNN-LSTM prácticamente sin
cambios.

**Respuesta directa al pedido del director**: con un conjunto de predictores
idéntico entre las 8 familias, la diferencia de desempeño entre ellas ya no
puede atribuirse a que "unas vieron más información que otras" — la brecha
LSTM/GRU/TFT-lite vs. RF/SVM/XGBoost/LightGBM/CNN-LSTM es un efecto de
arquitectura (capacidad del modelo frente al tamaño de la muestra, ~1600
filas de train), no de disponibilidad de predictores. Esto también explica,
retroactivamente, por qué el protocolo de Track B adoptó `feature_set="narrow"`
como la comparación principal desde el inicio — el conjunto "full" nunca fue
viable para esas arquitecturas, independientemente de si se le suma
composición o no.

**La conclusión central de Bloque 2 no cambia**: ningún modelo, bajo ningún
conjunto de predictores probado, supera de forma consistente al naive en
dirección.

## Anexo: muestra de los datasets de input, por etapa

Tres datasets de input distintos conviven en el proyecto según la familia y
el punto de la transformación. Ejemplo sobre la misma ventana de fechas
(jun-2023) en cada uno.

**1. `features_long.parquet` (34 columnas) — base que comparten casi todos
los modelos**, antes de cualquier transformación específica de modelo (índice
+ indicadores técnicos + macro + futuros):

| date | close | log_return | fwd_1 | fwd_3 | fwd_5 | ma_20 | rsi_14 | riesgo_pais | tasa_pf |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023-06-01 | 48.155,81 | +3,76% | +0,08% | +7,60% | +8,23% | 43.688,44 | 75,91 | 2.616 | 92,55 |
| 2023-06-02 | 48.195,28 | +0,08% | +2,15% | +7,85% | +8,12% | 44.061,05 | 76,00 | 2.561 | 93,23 |
| 2023-06-05 | 49.245,12 | +2,15% | +5,36% | +5,99% | +5,88% | 44.506,97 | 78,47 | 2.518 | 92,63 |
| 2023-06-06 | 51.956,82 | +5,36% | +0,34% | +0,60% | +0,45% | 45.147,26 | 83,25 | 2.396 | 92,92 |
| 2023-06-07 | 52.133,05 | +0,34% | +0,29% | +0,18% | -0,45% | 45.832,38 | 83,50 | 2.341 | 91,13 |
| 2023-06-08 | 52.285,77 | +0,29% | -0,03% | -0,18% | +3,26% | 46.404,93 | 83,74 | 2.388 | 92,99 |

**2. Lo que efectivamente entra al modelo, tras `build_model_frame` (ej.
h=1)** — `close` se elimina, los indicadores de precio pasan a ratio
(`ma_20` → `ma_20_rel`), `log_return_fwd_1` se renombra `target`, y aparecen
los flags de disponibilidad (`futures_available=0` cuando
`term_spread_futures` es nulo — el modelo ve el nulo real, no un valor
inventado):

| date | target | log_return | ma_20_rel | rsi_14 | realized_vol_20 | riesgo_pais | term_spread_futures | futures_available |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023-06-01 | 0,000819 | +3,76% | -9,28% | 75,91 | 2,11% | 2.616 | null | 0 |
| 2023-06-02 | 0,021549 | +0,08% | -8,58% | 76,00 | 2,12% | 2.561 | -23,27 | 1 |
| 2023-06-05 | 0,053603 | +2,15% | -9,62% | 78,47 | 2,09% | 2.518 | null | 0 |

**3. Dataset A (composición, 74 columnas) — suma 40 columnas de ranking
peso+retorno a `features_long.parquet`:**

| date | close | log_return | rank01_weight | rank01_return | rank02_weight | rank02_return | rank03_weight | rank03_return |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023-06-01 | 48.155,81 | +3,76% | 18,35% | +3,99% | 12,65% | +4,82% | 12,22% | +2,50% |
| 2023-06-02 | 48.195,28 | +0,08% | 18,60% | +1,44% | 12,73% | +0,74% | 11,95% | -2,20% |
| 2023-06-05 | 49.245,12 | +2,15% | 18,59% | +2,12% | 12,66% | +1,54% | 12,16% | +3,91% |

## Pendiente

- Incorporar la aclaración del ítem 2 (ranking ≠ empresa fija) a la
  redacción de metodología de la tesis, donde se describa el dataset A.
- Estos resultados (ítems 3 y 4) quedan en `results/track_a_ml_compA/`,
  `results/track_a_ml_compC_masked/`, `results/track_b_full_baseline/`,
  `results/track_b_full_compA/`, `results/track_b_full_compC_masked/`
  (git-ignored, regenerables desde `scripts/punto5_*.py`) — no se
  promueven a la numeración oficial de Bloque 2 porque son comparaciones
  de control, no la batería principal.
