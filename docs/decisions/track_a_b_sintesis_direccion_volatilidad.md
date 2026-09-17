# Síntesis de Bloque 2 (Track A + Track B): dirección no pronosticable, volatilidad sí

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
