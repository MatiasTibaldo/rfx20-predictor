# Decisión: baseline GARCH sobre volatilidad condicional (Bloque 2, Track A, Etapa 2)

> **⚠️ Actualización (16 sep 2026):** el resultado de este documento (GARCH
> reduce ~39% el RMSE vs. naive) quedó obsoleto tras corregir el precio de
> composición corrupto de sep-2019
> (`docs/decisions/sept2019_composicion_corrupta.md`) — ese error inflaba la
> varianza incondicional de train (el naive de este experimento) en ~39%,
> porque la varianza pondera al cuadrado y los retornos corruptos eran de
> ±60%. Con datos corregidos, GARCH queda ~1% **peor** que naive en los tres
> horizontes — mismo patrón de empate que el resto de Bloque 2. Ver el
> detalle completo en `docs/decisions/track_a_b_sintesis_direccion_volatilidad.md`
> (sección de actualización) y `docs/decisions/sept2019_composicion_corrupta.md`
> ("Impacto en Bloque 2"). El resto de este documento (metodología, orden
> GARCH(1,1) t-Student, walk-forward) sigue vigente sin cambios — solo el
> resultado numérico y su lectura quedaron desactualizados.
>
> **Chequeo adicional (16 sep 2026): ¿el naive sigue siendo injusto con GARCH
> por ser sensible a outliers?** El naive usa varianza incondicional de train,
> que pondera al cuadrado — sensible por diseño incluso a eventos reales
> (PASO 2019, elecciones, COVID). Se probó un naive alternativo winsorizado
> (recorte 1%/99% de `log_return` antes de calcular la varianza,
> `models/statistical/garch_runner.py::_winsorized_variance`) para ver si
> reabría la ventaja de GARCH:
>
> | horizonte | RMSE naive (crudo) | RMSE naive (winsorizado) | RMSE GARCH |
> |---|---|---|---|
> | 1 | 2.7481e-3 | 2.7547e-3 | 2.7724e-3 |
> | 3 | 2.7484e-3 | 2.7549e-3 | 2.7799e-3 |
> | 5 | 2.7487e-3 | 2.7550e-3 | 2.7849e-3 |
>
> El naive winsorizado (varianza de train 20.4% menor) resulta **igual o
> levemente peor** que el naive crudo en ambas métricas (RMSE y QLIKE), no
> mejor — y GARCH sigue perdiendo contra los dos. Tiene sentido
> estadísticamente: la varianza muestral cruda es, por construcción, el
> estimador que minimiza el error cuadrático medio contra el target real
> (asumiendo estacionariedad train→val); winsorizarla introduce un sesgo que
> solo puede empeorar el RMSE, no mejorarlo. **Conclusión: la reversión de
> GARCH no es un artefacto de un naive injusto — se sostiene con al menos
> dos definiciones razonables de naive.** Se descarta seguir por esta línea.

**Fecha:** 5 de septiembre de 2026
**Módulos:** `models/statistical/garch.py`, `models/statistical/garch_runner.py`

## Contexto

Segundo paso de Track A: "ARIMA/SARIMA + GARCH primero (baseline rápido)".
La Etapa 1 (ver `docs/decisions/arima_baseline_track_a.md`) encontró que
ningún orden ARIMA/SARIMA captura estructura en la **media condicional**
del log-return del índice (el mejor orden fue (0,0,0), equivalente a
pronosticar siempre 0). El mismo diagnóstico, sin embargo, rechazó con
fuerza el supuesto de varianza constante (test de heterocedasticidad) y
mostró curtosis extrema (821) y asimetría fuerte (-23.93) — evidencia
directa de que la **varianza condicional** sí tiene estructura, y de que
los errores no son gaussianos. GARCH ataca exactamente esa pregunta.

## Decisiones de diseño (acordadas con el alumno antes de implementar)

### 1. Media fija en cero — GARCH no hereda un modelo ARIMA de la media

Dado que la Etapa 1 concluyó que la media condicional no tiene estructura
explotable (pronóstico ARIMA = 0 exacto), se ajusta un GARCH de **media
cero** (`mean="Zero"` en `arch_model`) directamente sobre `log_return`, en
vez de un modelo ARIMA-GARCH combinado. No hay nada que un modelo de media
le aportaría a este GARCH que la Etapa 1 no haya descartado ya.

### 2. Comparación experimental Normal vs. t-Student, con la peor descartada de los informes

Se corrió un grid search por AIC de `(p,q) ∈ [1,3]×[1,3]` (9 candidatos)
para cada distribución de innovaciones, una sola vez sobre train, como
chequeo rápido y barato antes de comprometerse a una walk-forward completa:

| Distribución | Mejor orden | AIC |
|---|---|---|
| Normal | GARCH(3,2) | 10258.68 |
| t-Student | GARCH(1,1) | 8029.78 |

La diferencia (~2229 puntos de AIC) es contundente y confirma la
expectativa fijada por el diagnóstico de curtosis de la Etapa 1: la
distribución Normal se descarta de aquí en adelante — no se corrió walk-forward
para ella, y no aparece en ninguna métrica de resultado. Solo GARCH(1,1)
con t-Student avanza al walk-forward.

### 3. Evaluación contra el retorno al cuadrado (proxy de varianza realizada)

GARCH pronostica **varianza condicional**, no un retorno. No hay una
columna de "varianza futura realizada" en `features_long.parquet`, así que
se usa el proxy estándar y no sesgado bajo el supuesto de media cero:
`log_return_fwd_h ** 2`. Es ruidoso (un solo retorno al cuadrado es una
estimación de altísima varianza de la varianza verdadera de ese día), pero
evita construir un feature nuevo y es la práctica habitual en la literatura
cuando no se dispone de datos intradiarios para una medida de volatilidad
realizada más precisa.

### 4. Métricas: RMSE y QLIKE

- **RMSE** sobre la varianza pronosticada vs. el proxy, directo pero
  sensible al ruido del proxy (un solo día extremo puede dominar el error).
- **QLIKE** = `mean(log(σ²_pred) + r²_actual / σ²_pred)` — función de
  pérdida estándar en la literatura de pronóstico de volatilidad (Patton,
  2011), más robusta a lo ruidoso del proxy que el RMSE. Es una pérdida a
  minimizar: valores más negativos son mejores.

### 5. Mismo esquema de walk-forward que Etapa 1

Orden y distribución fijos desde el paso 2 (GARCH(1,1), t-Student); refit
diario de los parámetros (no se vuelve a correr el grid) en ventana
expansiva sobre el split `val`, igual que en ARIMA. El naive de referencia
es el análogo de "predecir retorno 0" de la Etapa 1: varianza constante,
igual a la varianza muestral (no condicional) de todo train.

## Bug encontrado y corregido: `arch` no acepta NaN

La primera corrida falló los 294 refits del walk-forward con
`"NaN or inf values found in y"`. A diferencia de `statsmodels` (usado en
Etapa 1), cuyo filtro de Kalman maneja valores faltantes de forma nativa,
la librería `arch` no admite ningún NaN en la serie de entrada. El
historial usado en cada refit incluye la primera fila de todo el dataset
(2018-04-03), cuyo `log_return` es nulo por construcción (no hay cierre
previo). Se corrigió agregando `.drop_nulls()` antes de convertir a
`numpy` en `walk_forward_evaluate_variance` (la selección de orden sobre
train ya lo hacía correctamente desde el inicio, en `garch_runner.py`).

## Resultado

Ajuste puntual de `GARCH(1,1)`, t-Student, sobre el `log_return` completo
de train (1660 observaciones no nulas):

```
                 coef    std err          t      P>|t|
--------------------------------------------------------------------------
omega          1.2254      0.489      2.508  1.215e-02
alpha[1]       0.1235  5.476e-02      2.255  2.413e-02
beta[1]        0.7343  9.333e-02      7.868  3.610e-15
nu             4.5706      0.855      5.345  9.029e-08
```

(Coeficientes en unidades escaladas — la serie se multiplica por 100 antes
de ajustar, siguiendo la recomendación de la librería para estabilidad
numérica, y se des-escala dividiendo la varianza pronosticada por 100².)

**Lectura de los coeficientes.** La ecuación de varianza de GARCH(1,1) es
`σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}` — la varianza de hoy es una combinación
de un piso constante (`ω`), el "shock" de ayer al cuadrado (`α`, reactividad
a sorpresas nuevas) y la varianza de ayer misma (`β`, memoria de
volatilidad):

- **α = 0.1235**: reactividad moderada a sorpresas nuevas.
- **β = 0.7343**: la mayor parte de la persistencia viene de la memoria de
  volatilidad, no de shocks puntuales.
- **α + β = 0.858** (persistencia): implica una vida media de shocks de
  volatilidad de ~4.5 ruedas (menos de una semana hábil) — moderada frente a
  índices de mercados desarrollados, donde 0.95-0.99 (memoria de meses) es
  habitual. El RFX20 "olvida" un shock de volatilidad relativamente rápido.
- **ν = 4.57** (grados de libertad de la t): apenas por encima del mínimo
  (ν>4) para que exista curtosis finita — confirma colas muy pesadas,
  consistente con la curtosis de 821 ya documentada en Etapa 1.

**Walk-forward (294/294 refits ok) — GARCH(1,1) t-Student vs. varianza
constante (naive):**

| Horizonte | RMSE GARCH | RMSE naive | QLIKE GARCH | QLIKE naive |
|---|---|---|---|---|
| 1 | 2.7645e-3 | 4.5204e-3 | -6.0180 | -5.2163 |
| 3 | 2.7636e-3 | 4.5216e-3 | -6.0214 | -5.2166 |
| 5 | 2.7642e-3 | 4.5243e-3 | -6.0289 | -5.2173 |

GARCH reduce el RMSE de varianza en ~39% frente al naive y mejora el QLIKE
en los tres horizontes (recordar: QLIKE es una pérdida, valores más
negativos son mejores).

## Lectura del resultado e implicancias para la tesis

A diferencia del resultado negativo de la Etapa 1 sobre la media
condicional, este es un **resultado positivo**: la magnitud de los
movimientos diarios del índice sí tiene estructura predecible — los
períodos de calma y de turbulencia se agrupan en el tiempo (volatility
clustering), y un modelo que lo explota (GARCH) supera de forma consistente
a asumir volatilidad constante.

- Este resultado debe presentarse en la tesis como el contraste
  metodológico central de Track A: la dirección del retorno no es
  pronosticable con un modelo lineal univariado sobre la propia serie
  (Etapa 1), pero la magnitud del movimiento sí lo es (Etapa 2). Son
  preguntas distintas y merecen conclusiones separadas.
- La persistencia moderada (0.858, vida media de ~4.5 ruedas) es un dato
  concreto a contrastar contra la literatura de mercados desarrollados al
  discutir resultados.
- El grado de libertad bajo de la t (ν=4.57) es evidencia adicional, ya
  anticipada por la curtosis de Etapa 1, de que cualquier modelo posterior
  que asuma errores gaussianos (incluidos varios de ML clásico sin ajuste
  de distribución) subestimará la probabilidad de movimientos extremos.
- La comparación Normal vs. t-Student, aunque descartada de las métricas
  finales, vale la pena citarla brevemente en la tesis como evidencia
  cuantitativa (diferencia de ~2229 puntos de AIC) de que la elección de
  distribución no es un detalle menor en este dataset.

## Pendiente

Ninguno bloqueante para el resto de Track A. Si más adelante se necesita un
proxy de varianza realizada menos ruidoso que el retorno al cuadrado (por
ejemplo, para comparar contra ML/DL en Bloque 2), evaluar datos intradiarios
o una ventana de retornos de alta frecuencia — fuera de alcance por ahora.
