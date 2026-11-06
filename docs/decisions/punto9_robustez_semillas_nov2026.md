# Complemento al Punto 9: robustez de la conclusión por semilla

**Fecha:** 5 de noviembre de 2026
**Módulos:** `scripts/punto_seeds_full_battery.py`, `scripts/punto_seeds_summary.py` (nuevos)
**Origen:** extensión propuesta por el alumno al Punto 9 del feedback de los
directores (incertidumbre de las diferencias pequeñas) — el bootstrap de
bloques del Punto 9 mide si el resultado es compatible con variabilidad
muestral; este complemento mide si es compatible con variabilidad de
semilla, una fuente de incertidumbre distinta (RandomizedSearchCV +
aleatoriedad interna del estimador para RF/XGBoost/LightGBM/SVM; init de
pesos + shuffling del *DataLoader* para las 4 redes).

## Qué se corrió

Los 8 modelos no determinísticos de Bloque 2 (quedan afuera ARIMA y GARCH:
ajuste por máxima verosimilitud, sin generador aleatorio — repetirlos con
otra "semilla" no cambia el resultado), sobre el dataset baseline
(`features_long.parquet`, ya con los Puntos 1-4 aplicados), con 5 semillas:
la oficial (42, ya documentada en los Puntos 3/7/8/9) más 4 nuevas (7, 123,
2024, 555). Random state parcheado tanto en `models.ml.common`/`models.deep_learning.common`
(afecta `RandomizedSearchCV` y `train_with_early_stopping`) como en el
módulo de cada runner (afecta el `random_state` propio del estimador, ej.
`RandomForestRegressor`) — son bindings de Python distintos, hay que
parchear ambos.

## Resultado completo

RMSE (% vs. naive) por semilla — media, desvío, mínimo y máximo de las 5:

| Modelo | h | Semilla 42 (oficial) | Media | Std | Mín | Máx | Mismo signo en las 5 |
|---|---|---:|---:|---:|---:|---:|---|
| RF | 1 | -0,12% | +0,78% | 0,58 | -0,12% | +1,41% | **No** |
| RF | 3 | +2,81% | +3,21% | 0,70 | +2,36% | +4,33% | Sí |
| RF | 5 | +3,50% | +4,07% | 0,86 | +2,77% | +5,00% | Sí |
| SVM | 1 | +0,47% | +0,74% | 0,31 | +0,43% | +1,20% | Sí |
| SVM | 3 | +0,32% | +1,07% | 0,48 | +0,32% | +1,68% | Sí |
| SVM | 5 | +2,68% | +2,81% | 0,60 | +1,78% | +3,58% | Sí |
| XGBoost | 1 | +2,80% | +9,44% | 3,51 | +2,80% | +12,30% | Sí |
| XGBoost | 3 | +8,47% | +11,39% | 3,20 | +8,47% | +16,15% | Sí |
| XGBoost | 5 | +5,84% | +10,20% | 4,66 | +3,86% | +16,37% | Sí |
| LightGBM | 1 | +4,08% | +6,11% | 2,93 | +1,71% | +10,16% | Sí |
| LightGBM | 3 | +6,37% | +10,29% | 3,65 | +6,37% | +16,56% | Sí |
| LightGBM | 5 | +5,85% | +10,30% | 5,35 | +5,25% | +19,28% | Sí |
| LSTM | 1 | +1,04% | +1,93% | 0,98 | +1,04% | +3,83% | Sí |
| LSTM | 3 | +0,47% | +3,59% | 4,09 | +0,47% | +11,59% | Sí |
| LSTM | 5 | +1,57% | +8,22% | 7,28 | +1,27% | +17,05% | Sí |
| GRU | 1 | +1,84% | +2,24% | 0,36 | +1,84% | +2,85% | Sí |
| GRU | 3 | +3,61% | +3,70% | 1,33 | +2,49% | +6,26% | Sí |
| GRU | 5 | +5,20% | +13,69% | 12,24 | +4,00% | +36,94% | Sí |
| CNN-LSTM | 1 | +2,14% | +2,70% | 0,96 | +1,77% | +4,00% | Sí |
| CNN-LSTM | 3 | +2,19% | +2,50% | 0,58 | +2,09% | +3,65% | Sí |
| CNN-LSTM | 5 | +1,04% | +3,06% | 1,51 | +1,04% | +4,80% | Sí |
| Transformer encoder | 1 | +2,50% | +3,54% | 0,91 | +2,50% | +5,08% | Sí |
| Transformer encoder | 3 | +6,15% | +7,63% | 2,47 | +3,99% | +11,37% | Sí |
| Transformer encoder | 5 | +5,41% | +8,13% | 2,41 | +5,13% | +11,08% | Sí |

*(Detalle completo en `results/punto_seeds/summary.parquet`.)*

## Lectura

1. **RF h=1 es la única combinación sin signo consistente entre semillas**
   (rango -0,12% a +1,41%) — la pequeña mejora de la semilla oficial no es
   robusta a la semilla, en 4 de 5 semillas RF queda levemente peor que el
   naive. Confirma, por una vía distinta a la del Punto 9 (variar la
   semilla en vez de remuestrear los datos), la misma conclusión: esa
   mejora puntual es ruido, no señal.
2. **Las 23 combinaciones restantes mantienen el mismo signo (peor que el
   naive) en las 5 semillas** — ningún modelo "cruza" a mejora en ninguna
   semilla probada.
3. **La semilla oficial (42) no está sesgada hacia el peor caso** — en
   varios modelos (XGBoost, LightGBM, GRU) queda en el extremo más
   favorable de las 5 semillas, no en el más desfavorable. Los números ya
   documentados en Bloque 2 no exageran la degradación.
4. **GRU h=5 es extremadamente sensible a la semilla** (rango +4,00% a
   +36,94%, std=12,24) — coherente con la inestabilidad de las redes bajo
   alta dimensionalidad/capacidad ya diagnosticada en el Punto 6.

## Conclusión

La conclusión central de Bloque 2 ("no se encontró una mejora consistente
frente al naive") se sostiene bajo esta segunda fuente de incertidumbre
(semilla), no solo bajo la de remuestreo (Punto 9) — con la única excepción,
ya identificada y descartada por ambos métodos de forma independiente, de
RF en h=1.
