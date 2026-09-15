# Exploración descartada: horizontes largos en Track A (10/21 días hábiles)

**Fecha:** 8 de septiembre de 2026
**Módulos:** `scripts/build_features_long_extended.py`,
`scripts/run_track_a_long_horizons.py`, mejoras permanentes en
`models/ml/common.py`.

## Contexto

Track A (ARIMA/SARIMA, GARCH, SVM, Random Forest, XGBoost, LightGBM) no
encontró señal explotable en la dirección del retorno diario del índice a
1/3/5 días hábiles (ver `docs/decisions/lightgbm_track_a.md`, síntesis). El
alumno propuso evaluar horizontes intermedios (10 días ≈ 2 semanas, 21 días
≈ 1 mes de ruedas) antes de pasar a Track B, con una condición de salida
explícita: **si no hay mejoras, se desestima esta línea y se sigue con
Deep Learning**, sin forzar más allá de una exploración acotada.

## Diseño

### 1. Dataset aparte, sin tocar lo canónico

Se generó `data/features/v1/features_long_ext.parquet` (mismo esquema que
`features_long.parquet` + columnas `log_return_fwd_10`/`log_return_fwd_21`),
en vez de extender el archivo canónico ya commiteado. Reutiliza
`macro.parquet` ya persistido (el calendario del índice no cambia al sumar
horizontes) — solo se recalculó el target del índice. Permite descartar
todo el experimento borrando un archivo si no daba resultados, sin tocar
nada de Bloque 1/2 ya cerrado y pusheado.

### 2. Bug de fuga corregido de paso (independiente del resultado)

`models/ml/common.py::build_model_frame` excluía del feature set una lista
**hardcodeada** de columnas `log_return_fwd_{1,3,5}`. Con el dataset
extendido, `log_return_fwd_10`/`log_return_fwd_21` se hubieran colado como
*features* al entrenar el modelo de h=1 (el modelo vería directamente el
retorno real a 10/21 días como input — fuga de información severa). Se
corrigió detectando dinámicamente **todas** las columnas con prefijo
`log_return_fwd_` presentes en el dataframe y excluyendo todas menos la del
horizonte actual, sin importar cuántos horizontes tenga el dataset. Esto
queda como fix permanente, no específico de este experimento.

### 3. CV con purge (López de Prado) — mejora permanente del protocolo

Ya se había identificado (sesión del 6-7 sep) que `TimeSeriesSplit` sin
ajustar puede filtrar información: las últimas `h` filas de cada fold de
train tienen un target que "mira" hacia adentro del fold de validación
siguiente. A h=1/3/5 el efecto es despreciable (≤5 filas por corte de 5,
~1.5% de train); a h=10/21 deja de serlo (hasta 21 filas por corte).

Se implementó `models/ml/common.py::purged_splits(n_samples, n_splits, horizon)`:
mismo `TimeSeriesSplit` expansivo, pero recorta las últimas `horizon` filas
de cada fold de train antes de puntuar contra su validación. Verificado
contra los datos reales: con h=10, el gap entre fin de train e inicio de
val pasa de 1 fila (natural) a 11 (1 natural + 10 purgadas), en los 5
folds. `tune_and_evaluate` ahora acepta un parámetro `horizon` (default 0
= sin purge, compatibilidad con los resultados ya publicados de h=1/3/5,
que no se re-corrieron). Los 4 runners de ML ahora pasan `horizon=h`
siempre — cualquier corrida futura, incluida una eventual re-corrida de
h=1/3/5, usa purge automáticamente.

ARIMA/GARCH no necesitaron este ajuste: su walk-forward diario nunca usa
como entrada nada posterior a la fecha de corte de cada refit, sin importar
el horizonte — el problema de fuga es específico del particionamiento por
folds estáticos de los modelos de ML, no del walk-forward secuencial.

### 4. Runners parametrizados, no duplicados

En vez de crear 6 scripts nuevos, se parametrizó `main()` de los 6 runners
existentes (`horizons`, `dataset_name`, y `results_dir`/`predictions_path`/
`run_name` según corresponda) para poder invocarlos programáticamente sobre
el dataset extendido sin duplicar lógica ya validada. Un driver nuevo
(`scripts/run_track_a_long_horizons.py`) los encadena.

## Resultado

| Horizonte | ARIMA | GARCH | SVM | RF | XGBoost | LightGBM |
|---|---|---|---|---|---|---|
| 10 (RMSE vs. naive) | Empatado (0,0,0) | **-39%** | Peor | ≈Empatado (RMSE), peor MAE | Sustancialmente peor (+31%, sobreajuste) | Peor |
| 21 (RMSE vs. naive) | Empatado (0,0,0) | **-40%** | Peor | Peor | ≈Empatado | Peor |

- **ARIMA:** orden ganador (0,0,0) sin estacionalidad, igual que a 1/3/5
  días — sin estructura AR/MA a ningún horizonte evaluado hasta ahora.
- **GARCH:** GARCH(1,1) t-Student de nuevo gana con contundencia por AIC
  (8029.78 vs. 10258.68 de Normal — el ajuste de volatilidad no depende del
  horizonte de evaluación, solo de la serie de retornos). Sigue reduciendo
  ~39-40% el RMSE de varianza frente al naive, incluso un poco más que a
  corto plazo.
- **SVM/RF/LightGBM:** peor que el naive en RMSE y MAE en ambos horizontes,
  sin mejora en ningún caso.
- **XGBoost:** repite el patrón de sobreajuste ya visto a corto plazo — la
  brecha contra el naive es grande a h=10 (+31%) y se achica hasta casi
  desaparecer a h=21, igual que se achicaba de h=1 a h=5. Consistente con
  la lectura ya documentada: a targets más lejanos y ruidosos, un modelo
  con mucha capacidad tiene menos margen relativo para sobreajustar.
- Importancias por permutación: sin ningún feature repetido de forma
  estable entre modelos ni entre h=10/h=21 — más compatible con ruido de
  búsqueda que con señal real.

## Decisión: se descarta, no se sube a producción

Con la condición de salida ya acordada, el resultado es negativo en los
mismos términos que a 1/3/5 días: **ningún método orientado a la media
condicional mejora de forma consistente al naive a horizontes de 2 semanas
o 1 mes**. Se decide:

- **No fusionar** `features_long_ext.parquet` en el dataset canónico
  (`features_long.parquet` sigue siendo la fuente única para Track A/B).
- **No adoptar** horizontes largos como parte del alcance de predicción del
  proyecto — el foco declarado (1/3/5 días) se mantiene sin cambios.
- **Sí conservar** el código de esta exploración (`scripts/`,
  `purged_splits`, la corrección de detección dinámica de columnas
  `log_return_fwd_*`) como documentación de una vía evaluada y descartada
  con rigor, siguiendo el mismo criterio ya aplicado a la diferenciación
  fraccional (`docs/decisions/fractional_differentiation.md`) — y porque el
  fix de fuga y el purge de CV son mejoras reales del protocolo compartido,
  independientes de este resultado puntual.

## Implicancia para la tesis

Vale como evidencia adicional (séptimo y octavo punto de datos, sumando
h=10/21 a los seis ya reportados en 1/3/5) de que la dirección del retorno
del RFX20 no es pronosticable con este feature set en ningún horizonte de
corto/mediano plazo evaluado — mientras que la volatilidad condicional
(GARCH) sí lo es, y de forma consistente en los cinco horizontes probados
hasta ahora (1, 3, 5, 10, 21). Refuerza, en vez de debilitar, la síntesis
ya redactada para Track A: motiva explícitamente Track B (Deep Learning)
como el siguiente intento de encontrar estructura en la media, y consolida
a GARCH como el hallazgo positivo central del bloque.

## Próximo paso

Track A queda completo y sin líneas de exploración pendientes. Sigue
Track B (Deep Learning: LSTM, GRU, evaluación preliminar de TFT/híbrido
CNN-LSTM), según `docs/plan_de_accion.md`.
