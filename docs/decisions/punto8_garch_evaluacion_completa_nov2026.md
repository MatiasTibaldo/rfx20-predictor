# Punto 8 del feedback de los directores: evaluación específica de GARCH

**Fecha:** 4 de noviembre de 2026
**Módulos:** `scripts/punto8_ewma_benchmark.py` (nuevo),
`docs/decisions/garch_volatility_track_a.md`, `docs/tesis/proyecto_final_tibaldo.md`
(sección 5.1.2), `docs/avance_trabajo_final.md` (sección 4.2.1 — el documento de
avance real enviado a los directores tenía la misma tabla vieja y el mismo QLIKE
anunciado-pero-no-mostrado; corregido en el mismo pase)
**Origen:** Punto 8 del feedback de los directores de tesis (Fernanda Mendez /
Rodrigo Del Rosso).

## Los 5 sub-puntos

### 1. Mostrar QLIKE, no solo RMSE

QLIKE ya estaba implementado en código (`garch.py::compute_variance_metrics`)
pero no se mostraba en los documentos de resultados (`garch_volatility_track_a.md`
tenía una tabla vieja con QLIKE, pero la tabla vigente post-Punto 3 no lo
tenía; el Capítulo 5 de la tesis no lo mostraba en absoluto). Agregado en
ambos documentos — ver tabla consolidada en el ítem 2.

### 2. Referencia de volatilidad móvil / EWMA

No existía ningún benchmark de este tipo en el proyecto. Implementado en
`scripts/punto8_ewma_benchmark.py`: EWMA causal (RiskMetrics,
$\lambda=0{,}94$), pronóstico a h días = $h \times \sigma^2_{EWMA,t}$ (mismo
criterio de "sin reversión a la media, se mantiene plano hacia adelante"
que corresponde a este tipo de modelo), evaluado con las mismas funciones
que GARCH (`compute_variance_metrics`) para comparabilidad directa.

**Tabla consolidada (post Punto 3, target acumulado):**

| Horizonte | RMSE naive | RMSE GARCH | RMSE EWMA | QLIKE naive | QLIKE GARCH | QLIKE EWMA |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 0,0027481 | 0,0027724 (+0,88%) | 0,0027784 (+1,10%) | -6,0429 | -5,9879 | -6,0105 |
| 3 | 0,0076656 | 0,0077450 (+1,03%) | 0,0077714 (+1,38%) | -4,8946 | -4,7943 | -4,8441 |
| 5 | 0,0132549 | 0,0134430 (+1,42%) | 0,0135442 (+2,18%) | -4,3557 | -4,2237 | -4,2882 |

**Ningún método mejora sobre el naive de varianza constante**, y **EWMA
queda peor que GARCH** en los tres horizontes y en ambas métricas —
resultado informativo, no solo negativo: EWMA no tiene reversión a la
media (equivalente a persistencia=1), mientras que GARCH sí
($\alpha+\beta=0{,}858$) — en un mercado donde la volatilidad revierte
relativamente rápido (vida media ~4,5 ruedas), es esperable que el modelo
sin reversión pierda más. La conclusión de "sin ventaja de volatilidad" se
sostiene ahora frente a dos benchmarks, no solo uno.

### 3. Qué se pronostica en h=3/h=5

Ya estaba correctamente implementado desde el fix del Punto 3
(`variance_pred_h = Σ(variance_forecast[1..h])`, evaluado contra
`log_return_fwd_h ** 2`, el cuadrado del retorno **acumulado**) — pero no
estaba explicado con la claridad que pide el director. Agregada una
aclaración explícita en ambos documentos: el objetivo es la varianza del
retorno acumulado a h días, no la varianza de un único día futuro en t+h;
bajo la especificación de media cero, `Var(suma de h retornos) = suma de
las h varianzas de un paso`, así que pronóstico y target miden la misma
cantidad en los tres horizontes. El benchmark EWMA sigue el mismo criterio.

### 4. "Por construcción" — corregido

La explicación original decía que la varianza muestral de train "es, por
construcción, el estimador que minimiza el error cuadrático medio" contra
el target real (val) — una garantía que no existe. Corregido en ambos
documentos: por construcción, la varianza muestral de train minimiza el
error cuadrático **dentro de train** (es la definición del estimador de
mínimos cuadrados); que también sea competitiva sobre `val` es una
observación empírica de este dataset, no una propiedad matemática
garantizada entre dos muestras distintas.

### 5. Curtosis de las innovaciones vs. curtosis incondicional — distinguido

El texto original citaba $\nu=4{,}57$ (grado de libertad de las
innovaciones t-Student del GARCH) como si fuera "la misma" curtosis de 821
reportada en el diagnóstico de ARIMA (Jarque-Bera sobre el retorno crudo).
Son cantidades relacionadas pero distintas: $\nu$ caracteriza la curtosis
de las **innovaciones estandarizadas** del modelo (los residuos, una vez
divididos por el desvío condicional estimado), mientras que 821 es la
curtosis **incondicional** (marginal) del retorno sin condicionar en la
volatilidad del momento. Un proceso GARCH genera, por el solo efecto del
agrupamiento de volatilidad (mezclar períodos de alta y baja varianza en
una misma serie), una curtosis incondicional **mayor** que la de sus
propias innovaciones — nunca menor. Corregido en ambos documentos para no
citarlas como si fueran intercambiables.

## Pendiente

- `evaluation/figures.py` / `docs/figures/garch_volatility.png` podrían
  actualizarse para incluir la referencia EWMA visualmente — no se hizo en
  esta ronda, los documentos de texto ya tienen la comparación completa.
