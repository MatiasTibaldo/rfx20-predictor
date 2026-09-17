# Síntesis de Bloque 2 (Track A + Track B): dirección no pronosticable, volatilidad sí

> ## ⚠️ Actualización (16 sep 2026) — el hallazgo de volatilidad se revirtió
>
> Tras corregir el precio corrupto de composición de 2019-09-23→27
> (`docs/decisions/sept2019_composicion_corrupta.md`) se re-corrió toda la
> batería de Bloque 2. **La sección "Evidencia: volatilidad condicional" de
> este documento (más abajo) queda obsoleta** — se conserva sin editar como
> registro histórico, pero la conclusión ya no es válida.
>
> **Qué cambió:** el naive de GARCH usa la varianza incondicional de train
> como baseline (`train_variance`, en `models/statistical/garch_runner.py`).
> El retorno corrupto de sep-2019 (±60%, dos días) contribuía
> desproporcionadamente a esa varianza (por estar al cuadrado: 0.6² = 0.36
> vs. ~0.0004 típico) — inflaba el naive en un ~39%. Al corregirlo, el naive
> cae de ~4.52e-3 a ~2.75e-3 RMSE, y la ventaja que GARCH le sacaba
> desaparece casi por completo:
>
> | horizonte | RMSE GARCH (antes → ahora) | RMSE naive (antes → ahora) | GARCH vs. naive (antes → ahora) |
> |---|---|---|---|
> | 1 | 2.7645e-3 → 2.7724e-3 | 4.5204e-3 → 2.7481e-3 | -38.8% → **+0.9%** |
> | 3 | 2.7636e-3 → 2.7799e-3 | 4.5216e-3 → 2.7484e-3 | -38.9% → **+1.2%** |
> | 5 | 2.7642e-3 → 2.7849e-3 | 4.5243e-3 → 2.7487e-3 | -38.9% → **+1.3%** |
>
> GARCH pasa de "reduce ~39% el error vs. naive" a "~1% peor que naive" en
> los tres horizontes — el mismo patrón de empate que ya se veía en
> dirección. **El resto de la síntesis (dirección no pronosticable) se
> mantiene sin cambios** — ningún otro modelo cambió de lado del naive tras
> la corrección (ver `docs/decisions/sept2019_composicion_corrupta.md`,
> sección "Impacto en Bloque 2", para la comparación completa de los 9
> modelos). Dos hallazgos secundarios sí mejoraron con datos limpios:
> XGBoost dejó de sobreajustar tan fuerte (de +61%/+42%/+6% peor que naive a
> +3.6%/+0.9%/+0.6%) y la predicción inestable de TFT-lite en h=5 se resolvió
> (de +18.6% peor a +3.5% peor) — ninguno cambia de "empatado/peor que
> naive" a "mejor que naive", así que no alteran la conclusión de dirección.
>
> **Implicancia para la tesis:** ya no hay un modelo ganador positivo en
> Bloque 2. La lectura honesta ahora es: **nueve métodos de dirección +
> GARCH de volatilidad, los diez empatados o levemente peores que sus
> respectivos naive**. Sigue siendo un resultado válido y defendible (ver
> razones en la sección "Por qué esto es un resultado válido" más abajo,
> que aplican igual a este resultado ampliado) — simplemente ya no incluye
> un lado "ganador".
>
> **Chequeo de robustez (16 sep 2026) — ya resuelto:** se probó un naive
> alternativo winsorizado (recorte 1%/99% de `log_return` antes de calcular
> la varianza) para descartar que la reversión fuera un artefacto de un
> naive injusto/sensible a outliers. Resultado: el naive winsorizado es
> **igual o levemente peor** que el crudo (esperable — la varianza muestral
> cruda ya es, por construcción, el estimador que minimiza MSE), y GARCH
> sigue perdiendo contra ambos. La reversión de GARCH se sostiene con dos
> definiciones razonables de naive — no era un artefacto de la métrica de
> referencia. Ver `docs/decisions/garch_volatility_track_a.md` para la
> tabla completa. No queda ninguna línea abierta de este lado.

**Fecha:** 15 de septiembre de 2026 (cierre de Track B, Etapa 3)
**Alcance:** este documento no reporta un experimento nuevo — consolida la
lectura conjunta de todos los modelos corridos en Bloque 2 (Track A:
`docs/decisions/arima_baseline_track_a.md`, `garch_volatility_track_a.md`,
`svm_track_a.md`, `rf_track_a.md`, `xgboost_track_a.md`,
`lightgbm_track_a.md`, `long_horizons_track_a.md`; Track B:
`lstm_baseline_track_b.md`, `track_b_etapa2_gru_full_features.md`,
`track_b_etapa3_tft_hibrido.md`), pensada como referencia única para la
sección de resultados de la tesis y como respuesta documentada a la
pregunta de fondo del proyecto: **¿hay o no un modelo capaz de predecir el
comportamiento del RFX20 con los datos, features y modelos disponibles?**

## Respuesta corta

**No, para la dirección del retorno diario — sí, para su volatilidad.**
No es "ningún modelo funciona": es que la pregunta "¿hacia dónde se mueve
el índice?" y la pregunta "¿cuánto probablemente se va a mover?" tienen
respuestas distintas con los mismos datos.

## Evidencia: dirección del retorno (media condicional)

Nueve métodos independientes, de tres paradigmas distintos, evaluados en
los horizontes 1/3/5 días hábiles (más una extensión a 10/21 días,
evaluada y descartada — mismo patrón, ver `long_horizons_track_a.md`):

| Familia | Métodos | Resultado vs. naive (predecir retorno 0) |
|---|---|---|
| Estadístico | ARIMA/SARIMA | Orden (0,0,0) sin estructura — empatado |
| ML clásico | SVM, Random Forest | Empatados (diferencia de 3er-4to decimal) |
| ML clásico | XGBoost, LightGBM | Peores que naive (sobreajuste, hasta -61% en XGBoost h=1) |
| Deep Learning | LSTM, GRU (feature set acotado) | Empatados |
| Deep Learning | LSTM, GRU (feature set completo, 24 features) | Sustancialmente peores (sobreajuste, RMSE 2-2.5x naive) |
| Deep Learning | CNN-LSTM, "TFT-lite" (feature set acotado) | Empatados |

Ningún método —lineal, no lineal, basado en árboles, recurrente,
convolucional o de atención— encuentra estructura explotable en la media
condicional del retorno. Cuando se sube la capacidad del modelo sin subir
la señal disponible (XGBoost en Track A, LSTM/GRU con feature set completo
en Track B), el resultado no es un empate sino una **degradación** — el
modelo sobreajusta ruido en vez de encontrar señal, lo cual es evidencia
adicional (no solo ausencia de evidencia) de que la señal direccional
buscada no existe en este conjunto de datos con esta granularidad diaria.

## Evidencia: volatilidad condicional

Un método, aplicado una vez (`garch_volatility_track_a.md`): GARCH(1,1)
con innovaciones t-Student sobre el log-retorno del índice, media cero.
Reduce ~39-40% el RMSE de varianza condicional frente al naive (varianza
constante) en los tres horizontes, y mejora el QLIKE. A diferencia de
todo lo anterior, acá **sí hay señal explotable** — la magnitud del
movimiento tiene estructura predecible, aunque su signo no.

## Por qué esto es un resultado válido, no una falla del proyecto

1. **Consistencia entre métodos independientes es la forma más fuerte de
   evidencia negativa disponible en ML aplicado.** Un solo modelo que no
   funciona puede deberse a una mala elección de arquitectura o
   hiperparámetros. Nueve métodos con supuestos completamente distintos
   (lineales vs. no lineales, con y sin memoria explícita de secuencia,
   con distintos niveles de capacidad) convergiendo en la misma conclusión
   descarta esa explicación.
2. **Es consistente con la hipótesis de mercados eficientes en su forma
   débil**: en un índice líder y líquido como el RFX20, no sería
   sorprendente que la dirección diaria no sea explicable con información
   pública rezagada (precios, indicadores técnicos, variables
   macroeconómicas ya publicadas) — sería más sorprendente lo contrario,
   dado que cualquier patrón explotable con datos públicos tendería a ser
   arbitrado. Este proyecto no *asume* esa hipótesis, pero sus resultados
   son coherentes con ella.
3. **El hallazgo de volatilidad no es un consuelo menor.** GARCH ofrece
   valor concreto y accionable — dimensionamiento de posiciones, gestión
   de riesgo, valuación relativa de instrumentos que dependen de
   volatilidad esperada — independientemente de que no exista señal
   direccional. Para el objetivo dual del proyecto (herramienta interna
   para Primary S.A. + tesis), este es un entregable real.

## Qué significa para lo que sigue (Bloque 3)

- El **modelo ganador del proyecto, con la evidencia actual, es GARCH**
  para volatilidad — no hay un modelo ganador para dirección porque la
  evidencia indica que, con estos datos, no lo hay.
- Un ensamble (Bloque 3) no puede inventar señal direccional que no está
  en los inputs — combinar modelos que ya empatan con el naive no debería
  superarlo. Sí tiene sentido evaluar ensamble/combinación **del lado de
  volatilidad** (por ejemplo, GARCH combinado con volatilidad realizada de
  otras ventanas) si hubiera más de un método positivo — hoy hay uno solo.
- Si en el futuro se quisiera reabrir la pregunta de dirección, el camino
  no es más modelos sobre los mismos datos — es sumar información de
  naturaleza distinta a la ya usada (order flow, datos intradiarios,
  sentiment) o cambiar la granularidad temporal del problema. Ambos son
  cambios de alcance del proyecto, no una tarea de modelado adicional.

## Índice de la evidencia completa

- `docs/decisions/arima_baseline_track_a.md` — ARIMA/SARIMA
- `docs/decisions/garch_volatility_track_a.md` — GARCH (resultado positivo)
- `docs/decisions/svm_track_a.md`, `rf_track_a.md`, `xgboost_track_a.md`,
  `lightgbm_track_a.md` — ML clásico
- `docs/decisions/long_horizons_track_a.md` — extensión a 10/21 días,
  descartada
- `docs/decisions/lstm_baseline_track_b.md` — LSTM, feature set acotado
- `docs/decisions/track_b_etapa2_gru_full_features.md` — GRU + feature
  set completo (degradación)
- `docs/decisions/track_b_etapa3_tft_hibrido.md` — CNN-LSTM + "TFT-lite"
  (cierre de Track B)
