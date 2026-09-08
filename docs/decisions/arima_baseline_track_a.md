# Decisión: baseline ARIMA/SARIMA (Bloque 2, Track A, Etapa 1)

**Fecha:** 5 de septiembre de 2026
**Módulos:** `models/statistical/arima.py`, `models/statistical/runner.py`

## Contexto

Primer paso de Track A (Bloque 2 del plan de acción): "ARIMA/SARIMA + GARCH
primero (baseline rápido)". Esta etapa cubre únicamente ARIMA/SARIMA; GARCH
queda para una etapa siguiente, una vez validado este resultado.

## Decisiones de diseño (acordadas con el alumno antes de implementar)

### 1. Orden fijo por AIC, refit diario de coeficientes

Se separan explícitamente dos pasos de costo muy distinto:

- **Selección de orden** (`select_order`): grid search por AIC, una sola vez,
  sobre el `log_return` completo de train (1661 filas). Grilla: `(p,q) ∈
  [0,5]`, `d ∈ {0,1}` (72 candidatos no estacionales) + una grilla estacional
  con `m=5` (semana hábil), `(P,Q) ∈ {(0,1),(1,0),(1,1)}`, `D=0` (216
  candidatos adicionales). Total 288 candidatos, ~242 convergieron.
- **Walk-forward** (`walk_forward_evaluate`): ventana expansiva sobre el
  split `val` (294 fechas), reestimando coeficientes cada día con el orden
  ya fijado — **no** se vuelve a correr la grilla en cada refit.

Se evaluó explícitamente la alternativa de re-buscar el orden en cada paso
del walk-forward: el costo estimado (grid completo × ~1650 puntos de refit)
rondaba las 3-7 horas, contra minutos con orden fijo. Dado que la corrida es
única y no se repetirá, se priorizó rigor en el refit diario (en vez de
semanal/mensual) precisamente porque con orden fijo ese rigor es
prácticamente gratis (294 fits de un modelo pequeño, sin re-búsqueda).

### 2. El pronóstico a horizonte h calza exacto con `log_return_fwd_h`

`log_return_fwd_h` (ver `processing/returns.py`) es el retorno de un único
día, `h` ruedas adelante (`log_return.shift(-h)`), no un retorno acumulado.
El pronóstico de SARIMAX al paso `h` de un `get_forecast(steps=max_h)`
corresponde exactamente a esa definición — no hace falta sumar retornos
pronosticados para comparar contra el target ya existente.

### 3. Warm-up = train completo, evaluación solo sobre val

El walk-forward no recorre train (sería una evaluación in-sample, poco
informativa) — usa train completo como historia inicial y solo genera
pronósticos, uno por fecha, sobre el split `val`. El split `test` no se toca
en esta etapa (queda para Bloque 3, evaluación final).

## Resultado

| Candidato ganador | AIC | Convergencia walk-forward |
|---|---|---|
| ARIMA(0,0,0), sin estacionalidad | -4270.38 | 294/294 refits ok |

| Horizonte | RMSE ARIMA | RMSE naive (predice 0) | MAE ARIMA | MAE naive |
|---|---|---|---|---|
| 1 | 0.029553 | 0.029553 | 0.020782 | 0.020782 |
| 3 | 0.029531 | 0.029531 | 0.020736 | 0.020736 |
| 5 | 0.029479 | 0.029479 | 0.020647 | 0.020647 |

**El mejor orden encontrado por AIC es, en la práctica, ausencia de
estructura AR/MA.** Ninguno de los 288 candidatos con estructura AR/MA/estacional
superó a este en AIC.

### Diagnóstico estadístico del modelo ganador

Ajuste puntual de `SARIMAX(order=(0,0,0), seasonal_order=(0,0,0,0))` sobre el
`log_return` completo de train (1661 observaciones), vía `statsmodels`:

```
                 coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------
sigma2         0.0045   7.66e-06    582.514      0.000       0.004       0.004
```

**Por qué el modelo tiene un solo coeficiente.** La notación SARIMA
`(p,d,q)(P,D,Q,m)` describe: `p,q` = órdenes autorregresivo (AR) y de media
móvil (MA) no estacionales; `d` = orden de diferenciación no estacional;
`P,D,Q,m` los mismos tres para el componente estacional, con `m` el período
(acá, 5 = semana hábil). Con el orden ganador, los seis son cero: no hay
término AR (el retorno de ayer no informa el de hoy), no hay término MA (los
errores de pronóstico pasados tampoco), no hay diferenciación (se trabaja
sobre `log_return`, ya estacionario) y no hay componente estacional. Además,
al ajustarse con la clase `SARIMAX` de `statsmodels` sin especificar un
término de tendencia (`trend`), el modelo tampoco incluye una constante. El
único parámetro que queda por estimar es **`sigma2`**, la varianza del
término de error (0.0045, equivalente a un desvío estándar diario de
~6.7%). No hay ningún coeficiente que traduzca "cuánto depende el retorno de
hoy del pasado de la serie", porque el criterio AIC concluyó que no existe
tal dependencia lineal explotable en esta serie.

**Consecuencia verificada directamente:** sin AR, MA ni constante, el
pronóstico puntual del modelo es matemáticamente **0.0 exacto** en
cualquier horizonte (`get_forecast(steps=5).predicted_mean` devuelve
`[0., 0., 0., 0., 0.]`). Es la razón precisa por la que las métricas de la
tabla anterior no son solo similares al baseline naive — son idénticas
bit a bit: ambos modelos emiten el mismo pronóstico.

El resto de la salida de `summary()` (estadísticos de diagnóstico sobre los
residuos, que en este caso coinciden con el propio `log_return` al no
restarle ningún término):

| Estadístico | Valor | Interpretación |
|---|---|---|
| Log-verosimilitud / AIC / BIC / HQIC | 2136.19 / −4270.38 / −4264.97 / −4268.37 | Criterios de ajuste. AIC es el que se usó para seleccionar el orden; los cuatro son consistentes entre sí en este caso |
| Ljung-Box (retardo 1), Prob(Q) = 0.24 | No se rechaza H₀ (sin autocorrelación) | Los residuos no muestran autocorrelación de primer orden — coherente con que no había estructura lineal para capturar |
| Jarque-Bera, Prob(JB) ≈ 0 | Se rechaza normalidad, con fuerza | Los retornos diarios del índice **no** siguen una distribución normal — hallazgo a declarar explícitamente en la sección de metodología, dado que muchos modelos clásicos (incluido ARIMA) asumen errores gaussianos |
| Asimetría (Skew) = −23.93 | Asimetría negativa extrema | Cola izquierda mucho más pesada que la derecha: los movimientos bruscos a la baja (crashes) son más extremos que las subas equivalentes — patrón típico de índices bursátiles, y consistente con los eventos macro ya identificados (corrida post-PASO 2019, ver sección 2.1 de `avance_trabajo_final.md`) |
| Curtosis = 821.12 | Colas extremadamente pesadas | Muy por encima de 3 (el valor de referencia de la distribución normal). Indica outliers extremos concentrados en unas pocas jornadas, no un patrón difuso en toda la serie |
| Heterocedasticidad (H), Prob(H) ≈ 0 | Se rechaza varianza constante | **El resultado más relevante para el paso siguiente**: la varianza del error cambia en el tiempo (hay períodos de calma y de turbulencia), algo que un único parámetro `sigma2` fijo no puede representar |

**Nota de datos:** el ajuste se completó pese a que la primera observación
de `log_return` en train es nula (la serie completa no tiene un retorno
definido para su primera fecha, al no existir un cierre previo) — el filtro
de Kalman de `statsmodels` maneja valores faltantes de forma nativa dentro
de un modelo de espacio de estados, sin requerir imputación.

## Lectura del resultado e implicancias para la tesis

No es una falla del pipeline: es el resultado esperable de aplicar un
modelo lineal univariado a un retorno financiero diario, consistente con la
hipótesis de mercado eficiente a esta frecuencia — la señal, si existe, no
es lineal ni está contenida en la propia serie de retornos pasados del
índice. Dos lecturas distintas conviven en este resultado, y ambas deben
declararse en la sección de metodología/resultados de la tesis:

- **Sobre la media condicional (dónde va el retorno): resultado negativo.**
  Ningún orden ARIMA/SARIMA de los 288 evaluados encuentra estructura
  explotable — el modelo colapsa a predecir cero. Esto fija un baseline
  honesto para lo que sigue en Track A (SVM, Random Forest, XGBoost,
  LightGBM) y Track B (LSTM/GRU): cualquiera de esos modelos debería, como
  mínimo, superar esta referencia (idéntica al naive) para justificar su
  complejidad adicional frente a un método lineal simple.
- **Sobre la varianza condicional (cuánto se va a mover el retorno):
  resultado positivo.** El test de heterocedasticidad rechaza con fuerza el
  supuesto de varianza constante que asume ARIMA. Es la motivación
  metodológica concreta — no una elección arbitraria de "seguir con el
  plan"— para la Etapa 2 de Track A: GARCH modela explícitamente esta
  varianza cambiante en el tiempo, una pregunta distinta y no redundante
  con el resultado negativo de la media condicional.
- La asimetría negativa extrema y la curtosis muy por encima de la normal
  (Jarque-Bera) deben citarse como evidencia de que los retornos del índice
  no son gaussianos — una limitación a declarar explícitamente para
  cualquier modelo posterior que asuma errores normales (incluido el propio
  ARIMA, y GARCH en su especificación estándar).

## Nota técnica: migración de MLflow a backend SQLite

La primera corrida falló al loguear a MLflow: la versión instalada (3.15)
puso el backend de archivos plano (`mlruns/`, documentado en
`docs/plan_de_accion.md` al instalar MLflow) en modo mantenimiento, y lanza
una excepción salvo que se use un backend de base de datos o se setee
`MLFLOW_ALLOW_FILE_STORE=true`. Se migró a `sqlite:///mlruns.db` (sigue 100%
local, sin server) en vez de mantener el opt-out del file store, siguiendo
la recomendación del propio proyecto MLflow. Actualizado en `CLAUDE.md` y
`docs/plan_de_accion.md`. `results/experiments.duckdb` no se ve afectado
(sigue a cargo del estado del pipeline y los datos, no de las corridas de
modelos).

## Pendiente (Track A, Etapa 2)

GARCH sobre la volatilidad condicional del log-return del índice — requiere
agregar la dependencia `arch` (no instalada todavía).
