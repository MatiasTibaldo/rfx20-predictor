# Punto 10 del feedback de los directores: ajustes del documento y próximo paso

**Fecha:** 4 de noviembre de 2026
**Módulos:** `docs/tesis/proyecto_final_tibaldo.md`, `docs/decisions/futures_implied_rate.md`,
`docs/decisions/track_a_b_sintesis_direccion_volatilidad.md`, `docs/avance_trabajo_final.md`
**Origen:** Punto 10 del feedback de los directores de tesis (Fernanda Mendez /
Rodrigo Del Rosso).

## 1. Tasa implícita y term spread — ya no se leen como expectativas sin más

Corregido en `docs/tesis/proyecto_final_tibaldo.md` (sección 4.3.2) y
`docs/decisions/futures_implied_rate.md`: la lectura original de la tasa
implícita y el term spread de futuros como "expectativas de devaluación e
inflación" se reformula. Ambos reflejan, en primer término, **condiciones de
financiamiento** (la tasa implícita surge del arbitraje spot-futuro, análogo
a un costo de *carry*) y la forma de la curva de futuros del índice — leerlos
como proxy de expectativas macroeconómicas requeriría asumir adicionalmente
que esas condiciones están dominadas por la paridad de tasas de interés no
cubierta peso/dólar, un supuesto razonable en el contexto argentino pero no
verificado de forma independiente en este trabajo. Se documenta el matiz, no
se afirma como hecho dado.

## 2. "TFT-lite" renombrado a "Transformer encoder"

Renombrado en todo el cuerpo de `docs/tesis/proyecto_final_tibaldo.md`
(14 ocurrencias) — la arquitectura usa una `TransformerEncoderLayer` de
PyTorch como componente central, así que el nombre nuevo es además más
preciso que el anterior, no solo más prudente. Se agregó una nota de
nomenclatura explícita en la sección 3.4.6 explicando el cambio y su motivo
(se omiten varios componentes centrales del TFT completo de Lim et al.
2019/2021 — redes de selección de variables, *gating*, encoder de
covariables estáticas — y mantener "TFT" en el nombre sugería una
reproducción que no es tal).

**Decisión de alcance**: el renombre se aplicó solo en la prosa de la tesis
(el documento que efectivamente leen los directores), no en el código ni en
los documentos de trabajo internos (`CLAUDE.md`, `docs/avance_trabajo_final.md`,
`docs/decisions/track_a_b_sintesis_direccion_volatilidad.md`,
`docs/decisions/track_b_etapa3_tft_hibrido.md`). Los identificadores de
código (`models/deep_learning/tft_lite.py`, `tft_lite_runner.py`, clase
`TFTLiteRegressor`, archivos de resultados `tft_lite_val_predictions_*.parquet`,
nombres de corrida de MLflow) se mantienen sin cambios — renombrarlos
invalidaría la trazabilidad con todos los experimentos ya corridos y
documentados bajo ese nombre, sin aportar nada que el cambio de nombre en la
tesis no resuelva ya (evitar la confusión de un lector externo con el TFT
completo). Si en algún momento se decide renombrar también el código, debe
ser una decisión aparte, explícitamente consultada — no se hizo acá.

## 3. Tabla comparativa de antecedentes

Agregada **Tabla 3.1** en `docs/tesis/proyecto_final_tibaldo.md`, inmediatamente
después del párrafo de antecedentes existente (capítulo 3): columnas Estudio
| Activo/mercado | Variable objetivo (nivel vs. retorno) | Familias comparadas
| Validación, para los 8 estudios de predicción ya citados en el trabajo
(se excluyen 3 citas de contexto de mercado que no son estudios de
predicción comparables — Mastrangelo y Salvatierra 2022, Edwards et al. 2003,
Assaf et al. 2025).

**Nota de integridad importante**: no se tuvo acceso a los papers originales
en esta ronda de trabajo — la tabla se completó **únicamente** con lo que ya
está explícitamente descripto en la prosa de antecedentes de este mismo
trabajo (ej. "predecir el precio del Estireno" → nivel; "predicción de
movimientos" → retorno/dirección). De los 8 estudios, solo 3 permiten
clasificar la variable objetivo con ese nivel de detalle (Yavasani y Wang
2023 y Drago 2023 → nivel; Ruiz Solivella 2025 → retorno/dirección); los 5
restantes, y la columna de validación completa, quedan marcados
explícitamente como "no especificado en este trabajo" en vez de completarse
con un valor plausible pero no verificado. **Pendiente**: el alumno debería
confirmar estos datos contra las fuentes originales antes de la entrega
final — esta tabla es un punto de partida construido de forma segura, no una
revisión bibliográfica completa.

## 4. Afirmación sobre imposibilidad teórica del ensamble — corregida

Corregida en 3 documentos (`docs/tesis/proyecto_final_tibaldo.md` sección
5.4, `docs/decisions/track_a_b_sintesis_direccion_volatilidad.md`,
`docs/avance_trabajo_final.md` sección 4.6): la afirmación original decía
que "un ensamble no puede generar señal que no está presente en sus modelos
de entrada", como imposibilidad teórica. No es correcto — una combinación de
modelos puede reducir el error de pronóstico aunque ninguno de sus
integrantes supere individualmente al naive, si sus errores no están
perfectamente correlacionados entre sí (el mismo principio de reducción de
varianza que sostiene a Random Forest, sección 3.3.4, o a cualquier método
de ensamble). El encuadre correcto, en los 3 documentos, pasa a ser de
**alcance y costo**: desarrollar y validar un ensamble sobre nueve modelos de
dirección es trabajo no trivial (correlación de errores, *stacking* o peso
óptimo, validación sin fuga adicional) con retorno esperado incierto dado
que ninguno individualmente supera al naive de forma significativa (Punto 9).
Es una decisión de priorización a discutir con la dirección, no una
conclusión forzada por los resultados de Bloque 2.

## 5. Propuesta de continuidad del director — estado actual

El director propone, como próximo paso: (1) conciliación de precios y
cantidades, (2) continuidad de la base, (3) verificación de objetivos y
particiones, (4) re-ejecutar un conjunto reducido de modelos representativos
sobre la versión validada, (5) completar las métricas, y (6) evaluación
final sobre el conjunto reservado.

**Estado real, al cerrar los 10 puntos del feedback:**

| Paso del director | Estado |
|---|---|
| (1) Conciliación de precios y cantidades | ✅ Hecho — Punto 1 |
| (2) Continuidad de la base | ✅ Hecho — Punto 2 |
| (3) Verificación de objetivos y particiones | ✅ Hecho — Puntos 3 y 4 |
| (4) Re-ejecutar modelos representativos | ✅ Hecho — y más amplio de lo pedido: se re-corrió la batería **completa** de 10 modelos con los runners reales (Punto 3), no solo un subconjunto representativo |
| (5) Completar las métricas | ✅ Hecho — hit-rate (Punto 7), QLIKE + EWMA (Punto 8), intervalos de confianza (Punto 9) |
| (6) **Evaluación final sobre el conjunto reservado (test, 86 filas)** | ❌ **No hecho — sigue pendiente** |

El único paso de la hoja de ruta del director que **todavía no se ejecutó**
es el (6): la evaluación final sobre el conjunto de test reservado
(2026-04-20 → 2026-08-25, 100% out-of-sample, nunca tocado hasta ahora por
diseño). Con los Puntos 1 a 10 del feedback cerrados, este es el hito natural
que sigue — una única pasada, no iterativa, sobre el modelo o conjunto de
modelos que se decida llevar a esa instancia final.

## Pendiente

- Confirmar con la dirección si corresponde ya avanzar a la evaluación sobre
  el conjunto de test reservado (punto 6 de su propuesta), dado que los
  Puntos 1-10 del feedback quedan cerrados.
- Verificar (Punto 4, ítem pendiente de documentación) que para el tramo de
  test estén disponibles todos los predictores necesarios, no solo el spot
  del índice, antes de correr esa evaluación final.
- Completar la tabla de antecedentes (ítem 3) contra las fuentes originales.
