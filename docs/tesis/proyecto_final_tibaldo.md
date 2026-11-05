UNIVERSIDAD AUSTRAL

Maestría en Explotación de Datos y Gestión del Conocimiento

Proyecto Final de Maestría

**Predicción del Valor del Índice ROFEX 20 mediante Técnicas de Machine
Learning y Deep Learning para el Soporte en la Toma de Decisiones en
Mercados Financieros**

Alumno: Matías Humberto Tibaldo

Directora: Mag. Fernanda Mendez

Co-Director: Mag. Rodrigo Del Rosso

*(fecha de presentación a completar)*

---

> **Nota sobre el estado de este documento (a eliminar antes de la entrega final).**
> Este archivo es el borrador del Trabajo Final, construido por etapas validadas junto
> con la dirección, siguiendo la estructura de referencia de trabajos previos de la
> Maestría. No reemplaza al informe de avance (`docs/avance_trabajo_final.md`), que
> sigue siendo la bitácora completa de decisiones metodológicas y su cronología —
> este documento reelabora ese contenido en registro y estructura de tesis, y lo
> amplía (particularmente en el capítulo de Estado del Arte).
>
> **Estado por capítulo:**
>
> | Capítulo | Estado |
> |---|---|
> | Portada | Completo |
> | Resumen | Esqueleto solamente — redacción final pospuesta a pedido del alumno, ver nota abajo |
> | Agradecimientos | Pendiente — a redactar por el alumno |
> | 1. Introducción | Borrador — completo |
> | 2. Contexto Organizacional | Borrador — completo (2.3 acotada, ver nota al final de esa sección) |
> | 3. Estado del Arte y trabajos relacionados | Borrador — completo (3.1 a 3.6) |
> | 4. Metodología | Borrador — completo (4.1 a 4.5) |
> | 5. Análisis de resultados | Borrador — completo (5.1 a 5.4) |
> | 6. Conclusión y trabajos futuros | Pendiente |
> | 7. Bibliografía | Pendiente |
>
> **Fuentes pendientes de incorporar a la Bibliografía final (capítulo 7):**
> - Matba Rofex (2025), *Guía Metodológica Índice de Acciones ROFEX 20* (vigencia
>   21/02/2025) — citada en el capítulo 2.
> - Matba Rofex (2023), *Circular Nro. 889-23 — Índice de Acciones ROFEX 20: Cambio
>   de Base* (2/10/2023) — citada en el capítulo 2.
> - Chatfield, C. (2019). *The Analysis of Time Series: An Introduction*. — 3.1.
> - Brockwell, P.J., & Davis, R.A. (2016). *Introduction to Time Series and
>   Forecasting*. — 3.1.1.
> - Nielsen, A. (2020). *Practical Time Series Analysis*. O'Reilly. — 3.1, 3.1.5.
> - Hyndman, R.J., & Athanasopoulos, G. (2021). *Forecasting: Principles and
>   Practice* (3rd ed.). OTexts. — 3.1, 3.2.3.
> - Peña, D. (2010). *Análisis de series temporales*. — 3.1.4.
> - Dickey, D.A., & Fuller, W.A. (1979). Distribution of the Estimators for
>   Autoregressive Time Series with a Unit Root. *JASA*. — 3.1.5 (test ADF).
> - Kwiatkowski, D., Phillips, P.C.B., Schmidt, P., & Shin, Y. (1992). Testing the
>   null hypothesis of stationarity against the alternative of a unit root. *Journal
>   of Econometrics*. — 3.1.5 (test KPSS).
> - Box, G.E.P., & Jenkins, G.M. (1970). *Time Series Analysis: Forecasting and
>   Control*. — 3.2.3 (metodología Box-Jenkins).
> - Cryer, J.D., & Chan, K. (2008). *Time Series Analysis with Applications in R*. —
>   3.2.4 (agrupamiento de volatilidad).
> - Engle, R.F. (1982). Autoregressive Conditional Heteroscedasticity with Estimates
>   of the Variance of United Kingdom Inflation. *Econometrica*. — 3.2.4 (ARCH).
> - Bollerslev, T. (1986). Generalized Autoregressive Conditional Heteroskedasticity.
>   *Journal of Econometrics*. — 3.2.4 (GARCH).
> - Patton, A.J. (2011). Volatility forecast comparison using imperfect volatility
>   proxies. *Journal of Econometrics*. — 3.2.4 (QLIKE).
> - Bontempi, G. (2014). *Statistical foundations of machine learning*. — 3.3.1.
> - Géron, A. (2019). *Hands-On Machine Learning with Scikit-Learn, Keras, and
>   TensorFlow* (2nd ed.). O'Reilly. — 3.3.1.
> - Chollet, F. (2021). *Deep Learning with Python* (2nd ed.). Manning. — 3.3.1.
> - Cortes, C., & Vapnik, V. (1995). Support-vector networks. *Machine Learning*,
>   20(3). — 3.3.2 (SVM).
> - Vapnik, V. (1998). *Statistical Learning Theory*. Wiley. — 3.3.2 (SVM).
> - Smola, A.J., & Schölkopf, B. (2004). A tutorial on support vector regression.
>   *Statistics and Computing*, 14(3). — 3.3.2 (SVR).
> - James, G., Witten, D., Hastie, T., & Tibshirani, R. (2021). *An Introduction to
>   Statistical Learning: with Applications in R* (2nd ed.). Springer. — 3.3.3
>   (árboles de decisión).
> - Breiman, L. (1996). Bagging predictors. *Machine Learning*, 24(2). — 3.3.4
>   (Bagging).
> - Breiman, L. (2001). Random Forests. *Machine Learning*, 45(1). — 3.3.4 (Random
>   Forest).
> - Friedman, J.H. (2001). Greedy function approximation: A gradient boosting
>   machine. *Annals of Statistics*, 29(5). — 3.3.4 (Gradient Boosting).
> - Chen, T., & Guestrin, C. (2016). XGBoost: A Scalable Tree Boosting System. *KDD
>   '16*. — 3.3.5 (XGBoost).
> - Ke, G., et al. (2017). LightGBM: A Highly Efficient Gradient Boosting Decision
>   Tree. *NeurIPS 2017*. — 3.3.6 (LightGBM).
> - LeCun, Y., Bottou, L., Bengio, Y., & Haffner, P. (1998). Gradient-based learning
>   applied to document recognition. *Proceedings of the IEEE*, 86(11). — 3.4.1 (CNN).
> - Brownlee, J. (2017). *Long Short-Term Memory Networks with Python*. — 3.4.2.
> - Hochreiter, S., & Schmidhuber, J. (1997). Long Short-Term Memory. *Neural
>   Computation*, 9(8). — 3.4.3 (LSTM).
> - Gers, F.A., Schmidhuber, J., & Cummins, F. (2000). Learning to Forget: Continual
>   Prediction with LSTM. *Neural Computation*, 12(10). — 3.4.3 (forget gate).
> - Cho, K., et al. (2014). Learning Phrase Representations using RNN
>   Encoder-Decoder for Statistical Machine Translation. *EMNLP 2014*. — 3.4.4 (GRU).
> - Sainath, T.N., Vinyals, O., Senior, A., & Sak, H. (2015). Convolutional, Long
>   Short-Term Memory, Fully Connected Deep Neural Networks. *ICASSP 2015*. — 3.4.5
>   (CNN-LSTM).
> - Vaswani, A., et al. (2017). Attention Is All You Need. *NeurIPS 2017*. — 3.4.6
>   (atención, Transformer).
> - Lim, B., Arık, S.Ö., Loeff, N., & Pfister, T. (2019/2021). Temporal Fusion
>   Transformers for Interpretable Multi-horizon Time Series Forecasting.
>   *International Journal of Forecasting*, 37(4). — 3.4.6 (TFT).
> - Rumelhart, D.E., Hinton, G.E., & Williams, R.J. (1986). Learning representations
>   by back-propagating errors. *Nature*, 323. — 3.4.7 (backpropagation).
> - Kingma, D.P., & Ba, J. (2015). Adam: A Method for Stochastic Optimization.
>   *ICLR 2015*. — 3.4.7 (optimizador Adam).
> - Zheng, A. (2015). *Evaluating Machine Learning Models*. O'Reilly. — 3.5.1.
> - Brownlee, J. (2020). *Deep Learning for Time Series Forecasting*. — 3.5.5.
> - López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. —
>   3.5.4 (purga de folds); ya citado en `docs/decisions/fractional_differentiation.md`
>   y `docs/decisions/long_horizons_track_a.md`.
> - Bhandari, H.N., Rimal, B., Pokhrel, N.R., Rimal, R., Dahal, K.R., & Khatri,
>   R.K.C. (2022). Predicting stock market index using LSTM. *Machine Learning with
>   Applications*, 9. — 3.6. (ya en la bibliografía del Plan de Trabajo Final).
> - Yavasani, R., & Wang, H. (2023). Comparative analysis of LSTM, GRU, and ARIMA
>   models for stock market price prediction. *Journal of Student Research*, 12(4).
>   — 3.6. (ya en el Plan).
> - Kulkarni, M.S., Vijayakumar Bharathi, S., Perdana, A., & Kilari, D. (2025). A
>   quest for context-specific stock price prediction. *SN Computer Science*, 6(4).
>   — 3.6. (ya en el Plan).
> - Mohapatra, S., Mukherjee, R., Apergis, N., & Sengupta, A. (2025). Exploring
>   predictive prowess of ensemble machine learning models in banking stocks. *IIMB
>   Management Review*, 37(2). — 3.6. (ya en el Plan).
> - Nasir, J., Iftikhar, H., Aamir, M., Iftikhar, H., Rodrigues, P.C., & Rehman, M.Z.
>   (2025). A hybrid LMD–ARIMA–machine learning framework. *Mathematics*, 13(15). —
>   3.6. (ya en el Plan).
> - Gülmez, B. (2023). Stock price prediction with optimized deep LSTM network with
>   artificial rabbits optimization algorithm. *Expert Systems with Applications*,
>   227. — 3.6. (ya en el Plan).
> - Edwards, S., Biscarri, J.G., & de Gracia, F.P. (2003). *Stock market cycles,
>   financial liberalization and volatility*. NBER. — 3.6. (ya en el Plan).
> - Assaf, A., Al-Shboul, M., Mokni, K., & Demir, E. (2025). Are Latin American
>   stock markets connected? *Emerging Markets Review*, 65. — 3.6. (ya en el Plan).
> - Mastrangelo, M.E., & Salvatierra, J.M. (2022). Análisis de rendimientos
>   ajustados por riesgo de fondos de inversión de renta variable en Argentina.
>   *Escritos Contables y de Administración*, 13(2). — 3.6. (ya en el Plan).
> - Ruiz Solivella, J.L. (2025). *Predicción de Movimientos en los Principales
>   Índices Bursátiles mediante Random Forest* [TFG, Universidad Miguel Hernández].
>   — 3.6. (ya en el Plan).
> - Pimentel Ramírez, P.I. (2024). *Aplicación de deep learning para la predicción
>   de índices bursátiles extranjeros...* [Tesis Magíster, Universidad de Chile]. —
>   3.6. (ya en el Plan).
> - Drago, B.D. (2023). *Predicción del precio del Estireno para la industria
>   Petroquímica mediante la utilización de metodologías de análisis de series
>   temporales tradicionales y modernas* [Proyecto Final de Maestría, Universidad
>   Austral]. — 3.6, citado como antecedente directo dentro del mismo programa.
>
> *(Las 10 referencias marcadas "ya en el Plan" son las mismas ya aprobadas en la
> bibliografía del Plan de Trabajo Final — se reutilizan sin modificar autores/año.
> Todas verificadas como referencias reales y localizables — varias ya citadas en
> `docs/decisions/garch_volatility_track_a.md`. Faltan datos bibliográficos
> completos —editorial, DOI, edición exacta— a confirmar al consolidar el capítulo 7.)*
>
> **Punto abierto que puede afectar este documento:** al momento de escribir este
> borrador, el alcance de la Fase 5 del proyecto (comparación y selección de modelo
> final) todavía está pendiente de redefinir con la dirección, dado que ningún modelo
> de Bloque 2 mejora de forma consistente sobre el naive (ver
> `docs/avance_trabajo_final.md`, secciones 4.6 y 7, punto 8). **El alumno prefiere
> seguir investigando antes de redactar en forma definitiva el Resumen y la
> Conclusión** (2026-09-21) — ambas secciones se dejan como esqueleto/placeholder
> hasta entonces, aunque el resto del documento (capítulos que no comprometen un
> resultado final) se sigue construyendo en paralelo.

## Índice General

*(Se completará con numeración de página al consolidar el documento final. Por
ahora, se muestra la estructura de capítulos prevista y su estado.)*

- Resumen — Esqueleto (redacción final pospuesta)
- Agradecimientos — Pendiente
- 1. Introducción — Borrador completo
  - 1.1. Introducción
  - 1.2. Objetivo
- 2. Contexto Organizacional — Borrador completo
  - 2.1. El mercado de capitales argentino y A3 Mercados
  - 2.2. El Índice ROFEX 20
  - 2.3. Primary S.A. y el rol de la predicción en la toma de decisiones
- 3. Estado del Arte y trabajos relacionados — Borrador completo
  - 3.1. Series de tiempo: definiciones y propiedades
  - 3.2. Modelos estadísticos (ARIMA/SARIMA, GARCH)
  - 3.3. Modelos de Machine Learning (SVM, árboles, boosting)
  - 3.4. Modelos de Deep Learning (LSTM, GRU, atención)
  - 3.5. Métricas de evaluación y validación en series de tiempo
  - 3.6. Trabajos relacionados: predicción en mercados emergentes
- 4. Metodología — Borrador completo
  - 4.1. Procedimiento general
  - 4.2. Selección y descripción de los datos
  - 4.3. Ingeniería de features
  - 4.4. Particionamiento temporal y protocolo de validación
  - 4.5. Modelos desarrollados
- 5. Análisis de resultados — Borrador completo
  - 5.1. Modelos estadísticos (ARIMA/SARIMA, GARCH)
  - 5.2. Modelos de Machine Learning clásico
  - 5.3. Modelos de Deep Learning
  - 5.4. Síntesis comparativa
- 6. Conclusión y trabajos futuros — Pendiente (redacción final pospuesta)
- 7. Bibliografía — Pendiente

## Resumen

*(Borrador en elaboración — pendiente de redacción final. El alumno prefiere seguir
trabajando e investigando sobre los resultados de Bloque 2 y el alcance de la Fase 5
antes de comprometer por escrito las conclusiones del trabajo, aun cuando la
tendencia de los resultados obtenidos hasta el momento sea consistente. Se deja a
continuación un esqueleto de los elementos que debería cubrir, a completar en una
etapa posterior.)*

- Contexto: el RFX20 como principal indicador del mercado de capitales argentino,
  operado en A3 Mercados, y su relevancia para Primary S.A. y para la literatura de
  predicción en mercados emergentes.
- Qué se hizo: comparación sistemática de modelos estadísticos, de Machine Learning
  y de Deep Learning sobre el retorno logarítmico diario del RFX20, horizontes de 1,
  3 y 5 días hábiles, con un dataset que combina precios, indicadores técnicos y
  variables macroeconómicas del contexto argentino.
- Qué se encontró: *(a definir una vez cerrada la Fase 5 — ver nota de estado al
  inicio del documento)*.
- Palabras clave: *(a definir junto con el resultado final)*.

## Agradecimientos

*(A completar por el alumno.)*

## 1. Introducción

### 1.1. Introducción

La predicción del valor que puede adoptar una variable económica en un período
futuro constituye, desde hace décadas, un campo de estudio de amplio interés tanto
académico como aplicado. Cuando la variable en cuestión es el precio de un
instrumento financiero, contar con una estimación anticipada —aun cuando sea
imperfecta— tiene valor directo para la toma de decisiones: gestión de riesgo,
dimensionamiento de posiciones, estrategias de cobertura y planificación operativa,
entre otros usos. Los mercados de capitales, en particular, concentran un interés
especial en esta tarea, dado que cada participante busca anticipar movimientos que le
permitan operar con ventaja o, al menos, con mejor información que la disponible en
el momento de la decisión.

El Índice ROFEX 20 (RFX20) es el principal indicador bursátil del mercado de
capitales argentino, representando el comportamiento agregado de las veinte acciones
más líquidas operadas en A3 Mercados (ex MATBA-ROFEX). Además de utilizarse como
referencia (benchmark) para numerosos fondos de inversión locales, el RFX20 es
activamente negociado a través de contratos de futuros, lo que lo constituye en un
indicador central del mercado de capitales local y en un activo subyacente relevante
para estrategias de trading, cobertura y arbitraje. Primary S.A., responsable de la
infraestructura tecnológica de A3 Mercados, cuenta con acceso privilegiado a datos
históricos completos del índice y de sus componentes, lo cual habilita el desarrollo
de un proyecto de investigación aplicada como el presente.

La predicción de índices bursátiles en mercados emergentes como el argentino
presenta desafíos que la distinguen de la vasta literatura desarrollada sobre
mercados como el NYSE o el NASDAQ: una volatilidad sustancialmente mayor, una fuerte
influencia de variables macroeconómicas locales (tipo de cambio, inflación, tasas de
interés reguladas y de mercado), cambios regulatorios frecuentes y una profundidad de
mercado menor. Estas particularidades hacen que los resultados obtenidos en mercados
desarrollados no sean necesariamente transferibles al contexto local sin una
validación empírica propia —motivación central de este trabajo.

En ese sentido, en el presente trabajo se desarrollan, entrenan y comparan
sistemáticamente modelos de predicción pertenecientes a tres paradigmas
metodológicos: modelos estadísticos clásicos de series de tiempo (ARIMA/SARIMA para
la media condicional, GARCH para la volatilidad condicional), modelos de Machine
Learning (Support Vector Machines, Random Forest y los algoritmos de *gradient
boosting* XGBoost y LightGBM) y modelos de Deep Learning (redes recurrentes LSTM y
GRU, una arquitectura híbrida convolucional-recurrente y una arquitectura basada en
mecanismos de atención). La comparación se realiza bajo un protocolo de validación
temporal común a las tres familias, con el objetivo de que las conclusiones sobre qué
paradigma resulta más adecuado para este problema sean comparables entre sí y no
producto de diferencias metodológicas incidentales entre modelos.

### 1.2. Objetivo

**Objetivo General**

Desarrollar un sistema de predicción del Índice ROFEX 20 mediante la comparación
sistemática de modelos estadísticos, de Machine Learning y de Deep Learning, en
horizontes de corto plazo (de uno a cinco días hábiles), como herramienta de soporte
para la toma de decisiones en Primary S.A. y como aporte académico al estudio de la
predicción de series financieras en mercados emergentes.

**Objetivos Específicos**

- Construir un pipeline de datos reproducible que consolide series históricas del
  RFX20, precios de sus acciones componentes, variables macroeconómicas y eventos
  corporativos relevantes (splits, dividendos, cambios de composición del índice).
- Implementar y entrenar modelos pertenecientes a tres familias —estadística
  (ARIMA/SARIMA, GARCH), Machine Learning (SVM, Random Forest, XGBoost, LightGBM) y
  Deep Learning (LSTM, GRU y arquitecturas híbridas)— bajo un protocolo de validación
  temporal riguroso y comparable entre familias.
- Realizar ingeniería de features especializada para el contexto del mercado
  argentino, incluyendo indicadores técnicos tradicionales, variables macroeconómicas
  transformadas (spreads cambiarios, tasas de referencia) y una reinterpretación de
  la volatilidad implícita a partir de la curva de futuros propia del RFX20.
- Evaluar la capacidad predictiva de los modelos desarrollados tanto sobre la
  dirección del retorno diario del índice (métricas de error y de acierto
  direccional) como sobre su volatilidad condicional, discutiendo los resultados a la
  luz de la literatura sobre eficiencia de mercado.
- Analizar comparativamente las fortalezas y limitaciones de cada familia de modelos
  en el contexto específico del RFX20, generando conclusiones transferibles a otros
  activos y mercados emergentes.
- Documentar de forma exhaustiva la metodología, las decisiones de diseño y los
  resultados obtenidos, cumpliendo con los estándares de rigor y replicabilidad
  esperables de un trabajo de tesis de maestría.

## 2. Contexto Organizacional

### 2.1. El mercado de capitales argentino y A3 Mercados

A3 Mercados (denominación comercial vigente del mercado anteriormente conocido como
MATBA-ROFEX) es el mercado bajo cuya jurisdicción cotizan las acciones locales que
integran el Índice ROFEX 20, y en el cual se negocian, además, los contratos de
futuros que tienen a dicho índice como activo subyacente. Primary S.A. es la empresa
responsable de la infraestructura tecnológica de A3 Mercados —la plataforma sobre la
que se procesan las operaciones y se distribuyen los datos de mercado—, lo que le
otorga acceso privilegiado a series históricas completas del índice, de sus acciones
componentes y de los contratos de futuros negociados sobre él. Este acceso es el que
habilita, en términos prácticos, el desarrollo de un proyecto de investigación
aplicada como el presente: sin él, buena parte de las variables utilizadas en este
trabajo (en particular, la tasa implícita de la curva de futuros descripta en el
capítulo 4) no estarían disponibles con el nivel de detalle e historia requerido.

### 2.2. El Índice de Acciones ROFEX 20

El Índice de Acciones ROFEX 20 (RFX20) está definido y administrado por Matba Rofex
S.A. de acuerdo con una metodología pública, documentada en la *Guía Metodológica
Índice de Acciones ROFEX 20* (Matba Rofex, 2025), cuya versión vigente a la fecha de
este trabajo data de febrero de 2025. Conocer esta metodología con precisión es un
requisito para interpretar correctamente tanto la serie histórica del índice como las
correcciones de datos descriptas en el capítulo 4, dado que varias de ellas están
directamente motivadas por eventos que la propia metodología define y regula.

#### 2.2.1. Composición y criterios de elegibilidad

El RFX20 es un **índice de retorno total** —es decir, que además de reflejar las
variaciones de precio de sus componentes asume la reinversión de los dividendos
distribuidos— integrado por las veinte acciones más líquidas del mercado accionario
argentino, ponderadas por su capitalización bursátil ajustada por capital flotante
(*free float*: el total de acciones en circulación de una compañía, excluyendo la
porción en manos del grupo controlante y de inversores estratégicos).

La cartera del índice se revisa cuatrimestralmente, el día hábil previo al tercer
viernes del último mes de cada cuatrimestre calendario, e implementa la nueva cartera
el primer día bursátil del cuatrimestre siguiente. La responsabilidad sobre el
índice recae en un Comité Técnico Asesor (entre 5 y 9 miembros, con representación
técnica de Matba Rofex S.A. y de expertos externos del ámbito académico y
financiero), que define la composición de acuerdo con tres criterios de
elegibilidad: (i) haberse negociado activamente en al menos el 80% de las ruedas de
los seis meses previos a la revisión, (ii) encontrarse entre las veinte acciones más
líquidas según el **Ratio de Liquidez** definido en la ecuación 2.1, y (iii) no
encontrarse suspendida ni en otras situaciones especiales (por ejemplo, procesos
judiciales).

$$r_a = \frac{\left(\frac{n_a}{N}\right)^{1/3} \left(\frac{v_a}{V}\right)^{2/3}}{T} \qquad (2.1)$$

donde $r_a$ es el ratio de liquidez de la acción $a$; $n_a$ y $v_a$ son,
respectivamente, el número de operaciones y el valor total operado en la acción $a$
en el mercado de contado durante el período de revisión; $N$ y $V$ son los mismos
totales para el conjunto del mercado; y $T$ es el número de ruedas del período de
revisión. Esta ponderación de dos tercios al valor operado y un tercio al número de
operaciones es, en sí misma, una decisión metodológica del administrador del índice
relevante para entender por qué la composición del RFX20 (y, por lo tanto, el
universo de acciones cuyas series de precios alimentan este trabajo, ver sección
4.2) cambia en el tiempo: una acción puede salir del índice no solo por dejar de
cotizar, sino por perder liquidez relativa frente a otras.

#### 2.2.2. Cálculo del índice y límites de ponderación

El valor del índice en cada momento $t$ se calcula como:

$$\text{ROFEX20}_t = \frac{\text{Capitalización de Mercado de las acciones del Índice}_t}{\text{Divisor}_t} = \sum_{i=1}^{n=20} P_{i,t} \cdot QI_{i,t} \qquad (2.2)$$

donde $P_{i,t}$ es el último precio operado de la acción $i$ en el momento $t$, y
$QI_{i,t} = Q_{i,t} / \text{Divisor}_t$ es la cantidad teórica de acciones de la
compañía $i$ expresada en unidades del índice ($Q_{i,t}$ es el número total de
acciones en circulación de la empresa $i$). El **Divisor** es un ponderador que se
ajusta ante la revisión de la cartera o ante determinados eventos corporativos, con
el propósito de que el valor del índice no se vea alterado por esos eventos en sí
mismos —solo por variaciones genuinas de precio de mercado.

Un elemento metodológico relevante para la interpretación de la serie es que el peso
relativo de cada componente en la fecha de rebalanceo **no puede superar el 20%, ni
1,5 veces la ponderación que resultaría de su Ratio de Liquidez relativo al del
conjunto del índice** (el que de los dos resulte menor). Cuando una compañía supera
ese límite, el excedente se redistribuye proporcionalmente entre el resto de los
componentes que todavía no alcanzaron su propio límite, de forma iterativa hasta que
ninguna acción lo excede. Este mecanismo de topes es lo que evita que el RFX20 quede
dominado por uno o dos componentes de capitalización extraordinaria (un riesgo
concreto en un mercado de baja profundidad como el argentino, ver sección 1.1), y
debe tenerse presente al interpretar cualquier análisis de importancia de variables
por ticker individual en los capítulos siguientes.

#### 2.2.3. Mantenimiento del índice: ajustes del divisor ante eventos corporativos

La guía metodológica detalla qué eventos corporativos disparan un ajuste del divisor
y cuáles no. Los más relevantes para este trabajo se resumen en la Tabla 2.1.

**Tabla 2.1.** Eventos corporativos y su efecto sobre el divisor del RFX20 (adaptado
de Matba Rofex, 2025).

| Evento | Ajusta el divisor | Motivo |
|---|---|---|
| Adición/eliminación de una compañía | Sí | El cambio neto en el valor de mercado del índice determina el ajuste |
| Cambio en la cantidad de acciones emitidas | Sí | Cualquier emisión secundaria o recompra se refleja en el divisor |
| Dividendos (ordinarios o extraordinarios) | Sí | Se ajusta para evitar la caída artificial del índice por el pago |
| Fusiones o adquisiciones | Sí, en caso de remoción | Si la compañía sobreviviente ya integra el índice o no cumple los criterios de elegibilidad |
| Deslistado o cualquier evento que suprima una compañía | Sí | La compañía se remueve del índice |
| Cambio de base | Sí | Se agregan o restan ceros a la cotización del índice |
| **Split** | **No** | El cambio en el número de acciones se compensa exactamente con el cambio en el precio, sin efecto neto en la capitalización |
| Cambio en una acción integrante (reemplazo dentro del índice) | No | La compañía entrante ingresa con la misma ponderación que la saliente |

La fila de **splits** merece una aclaración específica para este trabajo: que la
metodología oficial del índice no requiera ajustar el divisor ante un split no
implica que las fuentes de datos utilizadas para reconstruir las series históricas
de los componentes individuales (necesarias para el pipeline de este proyecto, ver
capítulo 4) reflejen ese split correctamente de forma automática. De hecho, la
verificación empírica de que varios splits de componentes del RFX20 **no** estaban
ajustados en la plataforma de datos de Primary S.A. utilizada para este trabajo —a
diferencia del divisor oficial del índice, que no necesita tocarlos— fue uno de los
primeros hallazgos metodológicos del proyecto (desarrollado en detalle en la sección
4.2).

Un caso particular de ajuste de divisor, documentado explícitamente por el
administrador del índice, es el **cambio de base de octubre de 2023**: mediante la
Circular Nro. 889-23 (Matba Rofex, 2023), se fijó un nuevo valor del divisor —el
vigente al cierre del 6 de octubre de 2023, multiplicado por diez— con el objetivo
declarado de "facilitar el trading de los futuros de Rofex 20". El efecto neto es
que la cantidad teórica de acciones que integran el índice se divide por diez, lo
que equivale a restarle un cero a la cotización del índice a partir del 9 de octubre
de 2023. Este evento, documentado oficialmente por el propio administrador del
índice, es el que motivó la corrección descripta en la sección 4.2 de este trabajo,
necesaria porque el proyecto reconstruye el índice a partir de los precios y
cantidades de sus componentes individuales, y esa reconstrucción debe replicar el
mismo ajuste que el divisor oficial aplicó en esa fecha.

### 2.3. Primary S.A. y el rol de la predicción en la toma de decisiones

Primary S.A., además de proveer la infraestructura tecnológica de A3 Mercados
descripta en la sección 2.1, opera como participante del mercado de capitales
argentino, con interés directo en contar con capacidad de anticipación sobre el
comportamiento del RFX20 y de los contratos de futuros que lo tienen como
subyacente. Al día de este trabajo, la compañía no cuenta con un desarrollo interno
de modelos de Machine Learning o Deep Learning para la predicción de este ni de
otros instrumentos, apoyándose en su lugar en análisis técnico tradicional. Este
trabajo constituye, en ese sentido, tanto un desarrollo de investigación aplicada de
interés académico como una primera exploración, con estándares metodológicos
rigurosos, de si ese tipo de herramienta puede aportar valor concreto a la operatoria
de la compañía.

*(Nota: esta sección se mantiene deliberadamente acotada a lo que puede sostenerse
con las fuentes disponibles hasta el momento —el Plan de Trabajo Final y el
conocimiento de dominio ya volcado en el capítulo 1—. Si existe material
institucional adicional sobre la estructura de Primary S.A., sus áreas de negocio o
su rol específico en la operatoria de mercado —análogo a lo que Braian Drago
describe para la industria petroquímica en su propio trabajo—, se puede ampliar esta
sección con ese contenido.)*

## 3. Estado del Arte y trabajos relacionados

*(Capítulo en construcción por sub-entregas. Esta versión cubre 3.1 y 3.2 —series de
tiempo, y modelos estadísticos ARIMA/SARIMA y GARCH—. Quedan pendientes 3.3 (Machine
Learning), 3.4 (Deep Learning), 3.5 (métricas y validación) y 3.6 (trabajos
relacionados sobre predicción en mercados emergentes), a entregar en sub-entregas
siguientes.)*

Este capítulo desarrolla los fundamentos teóricos de las familias de modelos
comparadas en este trabajo, presentando cada una de la forma en que se las aplica
posteriormente en el capítulo 5 (Análisis de resultados). Se ordena siguiendo la
misma progresión metodológica del proyecto: primero los modelos estadísticos
clásicos de series de tiempo (sección 3.2), luego los modelos de Machine Learning
(sección 3.3) y finalmente los de Deep Learning (sección 3.4), antes de discutir las
métricas de evaluación (sección 3.5) y los trabajos relacionados específicos sobre
predicción en mercados emergentes (sección 3.6).

### 3.1. Series de tiempo: definiciones y propiedades

#### 3.1.1. Serie temporal, modelado y pronóstico

Una serie temporal es una colección de observaciones registradas secuencialmente a
lo largo del tiempo (Chatfield, 2019). Su origen puede ser muy diverso —física,
meteorología, demografía—, pero es en economía y finanzas donde se registran
rutinariamente algunas de las series más estudiadas: precios de activos financieros
en jornadas sucesivas, tasas de interés, tipos de cambio, o —como en el caso de este
trabajo— el valor de cierre diario de un índice bursátil. Formalmente, un modelo de
serie de tiempo para un conjunto de observaciones $\{X_t\}$ es una especificación de
las distribuciones conjuntas —o, en su versión más simple, solo de las medias y
covarianzas— de una secuencia de variables aleatorias de la cual se postula que
$\{X_t\}$ es una realización (Brockwell & Davis, 2016).

El análisis de series de tiempo consiste en extraer información estadística
significativa de observaciones ordenadas cronológicamente, tanto para diagnosticar
el comportamiento pasado de la serie como para anticipar su comportamiento futuro
(Nielsen, 2020). Al pronosticar, el objetivo es estimar cómo continuará la secuencia
de observaciones: lo que se busca predecir es, por definición, desconocido, y puede
interpretarse como una variable aleatoria cuya incertidumbre generalmente crece
cuanto más lejano es el horizonte de pronóstico (Hyndman & Athanasopoulos, 2021).
Esta propiedad —incertidumbre creciente con el horizonte— es relevante para este
trabajo, en el cual se evalúan explícitamente tres horizontes de predicción
distintos (1, 3 y 5 días hábiles, ver sección 4.4) precisamente para observar cómo
se comporta la capacidad predictiva de cada modelo a medida que el horizonte se
extiende.

#### 3.1.2. Patrones de las series de tiempo

Al caracterizar una serie de tiempo suelen distinguirse tres tipos de patrones
(Hyndman & Athanasopoulos, 2021):

- **Tendencia:** existe cuando hay un aumento o disminución sostenida en los datos a
  largo plazo. No necesariamente es lineal.
- **Estacionalidad:** se produce cuando la serie se ve afectada por factores
  periódicos de frecuencia fija y conocida (por ejemplo, el día de la semana o el
  mes del año).
- **Ciclo:** ocurre cuando los datos exhiben subidas y bajadas que no tienen una
  frecuencia fija —a diferencia de la estacionalidad—, habitualmente asociadas a
  condiciones económicas más amplias.

Distinguir estos patrones es un primer paso obligado antes de ajustar cualquier
modelo estadístico clásico: como se desarrolla en la sección 3.2.3, la presencia de
un componente estacional determina si corresponde utilizar la extensión estacional
del modelo ARIMA (SARIMA) en lugar de su forma no estacional.

#### 3.1.3. Estacionariedad

Una serie de tiempo es estacionaria si no presenta un cambio sistemático en su media
(ausencia de tendencia), no presenta un cambio sistemático en su varianza, y no
conserva variaciones estrictamente periódicas (Chatfield, 2019). Gran parte de la
teoría de probabilidad aplicable a series de tiempo se ocupa específicamente de
series estacionarias, razón por la cual el análisis de series de tiempo
frecuentemente requiere transformar una serie no estacionaria en una estacionaria
antes de poder aplicar dicha teoría (Chatfield, 2019). Matemáticamente, la serie
subyacente puede describirse como un **proceso estocástico**: una colección de
variables aleatorias ordenadas en el tiempo y definidas sobre un conjunto de puntos
temporales, continuos o discretos (Chatfield, 2019).

#### 3.1.4. Función de autocorrelación y ruido blanco

Para evaluar el grado de dependencia temporal en una serie y orientar la selección
de un modelo que la represente adecuadamente, se recurre habitualmente a la
**función de autocorrelación** (ACF). Los coeficientes de autocorrelación miden la
correlación entre observaciones separadas por distintas distancias temporales
(*lags*), en un rango de -1 a 1: si dos observaciones separadas por un determinado
lag son independientes entre sí, su correlación verdadera es cero (Chatfield, 2019).
En la práctica, se utiliza el correlograma (gráfico de ACF) para identificar
estacionariedad: en una serie estacionaria, la ACF decae a cero relativamente rápido
con el lag, mientras que en una serie no estacionaria decae lentamente (Hyndman &
Athanasopoulos, 2021). La **función de autocorrelación parcial** (PACF) complementa
esta lectura, midiendo la correlación entre una observación y un lag determinado una
vez controlado el efecto de los lags intermedios —de particular utilidad para
identificar el orden de un proceso autorregresivo (sección 3.2.1).

Una serie de tiempo que no muestra autocorrelación significativa en ningún lag se
denomina **ruido blanco**: se espera que cada coeficiente de autocorrelación sea
cercano a cero (Nielsen, 2020). Cuando una serie se comporta como ruido blanco,
conocer sus valores pasados no aporta ninguna información sobre su valor futuro, ya
que el proceso carece de memoria explotable (Peña, 2010). Esta noción es central
para la interpretación de los resultados de este trabajo (capítulo 5): buena parte
de la discusión sobre la predictibilidad del retorno diario del RFX20 se apoya
directamente en si su comportamiento es o no estadísticamente distinguible de un
ruido blanco.

#### 3.1.5. Transformaciones y test de raíces unitarias

Es habitual que una serie se vuelva suficientemente estacionaria mediante
transformaciones simples. Aplicar logaritmos ayuda a estabilizar la varianza de una
serie; la **diferenciación** —calcular la diferencia entre valores consecutivos
(o entre valores separados por un lag mayor a uno, si resulta pertinente)— ayuda a
estabilizar la media, eliminando o reduciendo tendencia y estacionalidad (Hyndman &
Athanasopoulos, 2021; Nielsen, 2020). Cuando además se busca corregir asimetría en
la distribución de los datos —un supuesto que varios modelos estadísticos clásicos
requieren, al menos aproximadamente—, puede recurrirse a transformaciones más
generales como la familia Box-Cox (Nielsen, 2020).

Para determinar de forma más objetiva si una serie requiere diferenciación, se
recurre a **pruebas de raíces unitarias**: pruebas de hipótesis estadística
diseñadas específicamente con ese propósito. La prueba **ADF** (*Augmented
Dickey-Fuller*, Dickey & Fuller, 1979) plantea como hipótesis nula la presencia de
una raíz unitaria (es decir, que la serie **no** es estacionaria); un p-value
suficientemente pequeño permite rechazar esa hipótesis nula y concluir a favor de la
estacionariedad. La prueba **KPSS** (Kwiatkowski, Phillips, Schmidt & Shin, 1992)
invierte el planteo: su hipótesis nula es que la serie **sí** es estacionaria, de
modo que un p-value pequeño lleva a rechazar la estacionariedad. Utilizar ambas
pruebas de forma conjunta —como se hizo en la etapa de ingeniería de features de
este trabajo (ver sección 4.3)— permite una lectura más robusta que apoyarse en una
sola prueba: coincidencia entre ambas (ADF rechaza la raíz unitaria y KPSS no
rechaza la estacionariedad) es evidencia más fuerte que el resultado de cualquiera
de las dos por separado, mientras que un resultado contradictorio entre ambas suele
señalar una serie con estacionariedad ambigua o dependiente de la especificación
(por ejemplo, estacionaria en tendencia pero no en diferencia).

### 3.2. Modelos estadísticos de series de tiempo: ARIMA/SARIMA y GARCH

Al trabajar con modelos estadísticos clásicos, la estacionariedad es una propiedad
central tanto para el modelado como para su validación: las herramientas descriptas
en la sección 3.1 (ACF/PACF, transformaciones, tests de raíz unitaria) son,
precisamente, el instrumental que permite decidir qué estructura de modelo
corresponde aplicar y con qué grado de diferenciación.

#### 3.2.1. Modelos autorregresivos (AR)

En un modelo autorregresivo se pronostica la variable de interés como una
combinación lineal de sus propios valores pasados —de ahí el término
"autorregresivo": una regresión de la variable contra sí misma—. Se dice que una
serie $Y_t$ sigue un proceso autorregresivo de orden $p$, o $AR(p)$, si:

$$Y_t = c + \varphi_1 Y_{t-1} + \varphi_2 Y_{t-2} + \cdots + \varphi_p Y_{t-p} + \varepsilon_t \qquad (3.1)$$

donde $c$ y $\varphi_1, \ldots, \varphi_p$ son constantes a estimar y $\varepsilon_t$
es un proceso de ruido blanco de varianza $\sigma^2$.

#### 3.2.2. Modelos de media móvil (MA)

En lugar de usar valores pasados de la propia variable, un modelo de media móvil de
orden $q$, o $MA(q)$, utiliza errores de pronóstico pasados:

$$Y_t = c + \varepsilon_t + \theta_1 \varepsilon_{t-1} + \theta_2 \varepsilon_{t-2} + \cdots + \theta_q \varepsilon_{t-q} \qquad (3.2)$$

donde $c$ y $\theta_1, \ldots, \theta_q$ son constantes a estimar y $\varepsilon_t$
es, nuevamente, ruido blanco de varianza $\sigma^2$: el valor actual de la serie
depende de los últimos $q$ errores de pronóstico, no de sus valores pasados.

#### 3.2.3. Modelo ARIMA y su extensión estacional SARIMA

Combinando diferenciación, autorregresión y un componente de media móvil se obtiene
un modelo $ARIMA(p, d, q)$:

$$Y'_t = c + \varphi_1 Y'_{t-1} + \cdots + \varphi_p Y'_{t-p} + \theta_1 \varepsilon_{t-1} + \cdots + \theta_q \varepsilon_{t-q} + \varepsilon_t \qquad (3.3)$$

donde $Y'_t$ es la serie diferenciada $d$ veces, $p$ es el orden autorregresivo,
$q$ el orden de media móvil, y $\varepsilon_t$ nuevamente ruido blanco de varianza
$\sigma^2$. Son casos particulares de esta formulación: si $d=0$, $ARIMA(p,0,q)$ se
reduce a un $ARMA(p,q)$; si además $q=0$, a un $AR(p)$ puro; si además $p=0$, a un
$MA(q)$ puro; y si $p=q=d=0$, el modelo se reduce a ruido blanco puro —el caso límite
de "ausencia total de estructura explotable" que resulta directamente relevante para
la lectura de los resultados de este trabajo (sección 5.1).

Cuando la serie presenta, además, un componente estacional de período conocido $m$
(sección 3.1.2), la formulación se extiende a un modelo $SARIMA(p,d,q)(P,D,Q,m)$, que
agrega un segundo bloque autorregresivo/de media móvil/de diferenciación aplicado no
sobre observaciones consecutivas sino sobre observaciones separadas por $m$ períodos
(Hyndman & Athanasopoulos, 2021). Para una serie de precios financieros diarios, el
candidato de periodicidad más natural a evaluar es $m=5$ (la semana hábil bursátil),
que es precisamente el que se evalúa en este trabajo (ver sección 4.5.1).

La metodología para identificar, ajustar y validar un modelo ARIMA/SARIMA fue
formalizada por Box y Jenkins (Box & Jenkins, 1970) y, en términos generales, sigue
cuatro etapas (Hyndman & Athanasopoulos, 2021):

1. **Identificación:** visualización de la serie y sus correlogramas (ACF/PACF),
   aplicación de las transformaciones necesarias para alcanzar estacionariedad
   (apoyada en tests de raíz unitaria, sección 3.1.5).
2. **Estimación:** ajuste de los parámetros del modelo para uno o varios órdenes
   candidatos $(p,d,q)$ —y, si corresponde, $(P,D,Q,m)$—, preseleccionados a partir
   de la lectura gráfica de ACF/PACF o mediante una búsqueda automatizada sobre una
   grilla de candidatos.
3. **Selección del modelo:** comparación de los candidatos ajustados mediante un
   criterio de información, típicamente el **Criterio de Información de Akaike**
   (AIC), donde se prefiere el modelo con el valor más bajo —criterio efectivamente
   utilizado en este trabajo (ver sección 4.5.1).
4. **Verificación (diagnóstico):** análisis de los residuos del modelo seleccionado,
   evaluando si se comportan como ruido blanco (ausencia de autocorrelación
   remanente) y, adicionalmente, si son compatibles con los supuestos distribucionales
   que el modelo asume —normalidad, en la especificación estándar de ARIMA/SARIMA—.

#### 3.2.4. Heterocedasticidad condicional: modelos ARCH y GARCH

Es habitual observar en series financieras un fenómeno de **agrupamiento de
volatilidad** (*volatility clustering*): períodos de alta volatilidad tienden a
sucederse con otros períodos de alta volatilidad, y análogamente para períodos de
calma (Cryer & Chan, 2008). Este comportamiento no puede ser capturado por un modelo
lineal como ARIMA, que asume una varianza del error constante en el tiempo
(homocedasticidad) — un supuesto que, cuando se lo contrasta empíricamente contra
series financieras reales, suele rechazarse con fuerza (ver, en este trabajo,
sección 5.1).

Engle (1982) propuso el primer modelo diseñado específicamente para capturar esta
estructura: la **heterocedasticidad condicional autorregresiva** (ARCH), en la cual
la varianza del error en el momento $t$ depende de los residuos al cuadrado de
períodos anteriores. Bollerslev (1986) generalizó este modelo dando lugar al
$GARCH(p,q)$ (*Generalized ARCH*), cuya ecuación de varianza condicional es:

$$\sigma_t^2 = \omega + \sum_{i=1}^{q} \alpha_i \varepsilon_{t-i}^2 + \sum_{j=1}^{p} \beta_j \sigma_{t-j}^2 \qquad (3.4)$$

donde $\sigma_t^2$ es la varianza condicional en $t$, $\omega > 0$ es un piso
constante, los coeficientes $\alpha_i$ capturan la reactividad de la varianza a
shocks recientes (el término ARCH) y los coeficientes $\beta_j$ capturan la memoria
de la propia varianza pasada (el término GARCH propiamente dicho). El caso más
utilizado en la práctica, y el efectivamente ajustado en este trabajo (sección
4.5.1), es $GARCH(1,1)$: un único término de cada tipo. Una propiedad central de
esta especificación es la **persistencia**, $\alpha_1 + \beta_1$: cuanto más cercana
a 1, más lentamente se disipa en el tiempo el efecto de un shock de volatilidad —la
formulación es estacionaria en varianza solo si esta suma es estrictamente menor a
1—, y de ella puede derivarse una vida media de los shocks de volatilidad,
interpretable en la misma unidad temporal que la serie modelada.

A diferencia de ARIMA, que modela la **media condicional** de una serie financiera
(hacia dónde se espera que se mueva su valor), GARCH modela su **varianza
condicional** (cuánto se espera que se mueva, independientemente de la dirección).
Se trata, por lo tanto, de dos preguntas distintas y no redundantes sobre la misma
serie —una distinción metodológica que se retoma explícitamente en la lectura de
resultados de este trabajo (secciones 5.1 y 5.4), donde ambas dimensiones arrojan
conclusiones diferentes entre sí.

Es también frecuente que los residuos de una serie financiera muestren **colas más
pesadas** que las de una distribución normal (curtosis superior a 3) y asimetría —lo
cual motiva ajustar GARCH no bajo el supuesto de innovaciones normales sino con una
distribución de colas más pesadas, típicamente una **t de Student**, cuyo grado de
libertad $\nu$ se estima junto con el resto de los parámetros del modelo y cuantifica
qué tan pesadas son esas colas (a menor $\nu$, colas más pesadas). La comparación
empírica entre ambas distribuciones de innovaciones, y su impacto en el ajuste, se
desarrolla en la sección 5.1 de este trabajo.

Por último, dado que un modelo GARCH pronostica una varianza y no un valor
observable directamente, su evaluación requiere una métrica adaptada a ese objetivo.
Además de comparar contra un proxy de varianza realizada (típicamente el retorno al
cuadrado, cuando no se dispone de datos de mayor frecuencia intradiaria), la
literatura de pronóstico de volatilidad utiliza la función de pérdida **QLIKE**
(Patton, 2011), definida como:

$$\text{QLIKE} = \log(\hat{\sigma}_t^2) + \frac{r_t^2}{\hat{\sigma}_t^2} \qquad (3.5)$$

que penaliza tanto sobreestimar como subestimar la varianza real, y es preferida en
esta literatura frente al error cuadrático medio simple por ser más robusta ante lo
ruidoso del proxy de varianza realizada utilizado como referencia.

### 3.3. Modelos de Machine Learning

#### 3.3.1. Aprendizaje automático supervisado

En las últimas décadas, los modelos de Machine Learning han demostrado adaptarse muy
bien a numerosas aplicaciones de pronóstico frente a los modelos lineales
estadísticos clásicos descriptos en la sección 3.2 (Bontempi, 2014). Una definición
general y ampliamente utilizada es la de Géron (2019): el aprendizaje automático es
la ciencia (y el arte) de programar computadoras de manera que puedan aprender de
los datos, en lugar de ser programadas explícitamente con reglas fijas (Chollet,
2021) —una diferencia fundamental respecto de la programación tradicional, y también
respecto de los modelos estadísticos de la sección 3.2, cuya forma funcional se fija
de antemano (lineal, autorregresiva) y solo se estiman sus parámetros.

Los modelos utilizados en este trabajo (SVM, árboles de decisión y sus variantes de
ensamble) pertenecen a la familia de **aprendizaje supervisado**: los datos de
entrenamiento incluyen la solución deseada (la etiqueta o *label*, en este caso el
retorno logarítmico futuro del índice a un horizonte determinado). Esto requiere,
como mínimo, tres elementos: datos de entrada (*inputs*, los features descriptos en
el capítulo 4), ejemplos del resultado esperado, y una función que mida qué tan
cerca está la predicción del modelo del resultado real —una señal de
retroalimentación que permite ajustar los parámetros del modelo durante el
entrenamiento (Géron, 2019). La práctica habitual de separar los datos disponibles en
entrenamiento, validación y prueba (utilizada también para los modelos estadísticos
de la sección 3.2, aunque con particularidades específicas cuando los datos están
ordenados temporalmente) se desarrolla en detalle en la sección 3.5.

#### 3.3.2. Máquinas de Vector Soporte (SVM)

Las Máquinas de Vector Soporte (*Support Vector Machines*, SVM) fueron formalizadas
originalmente como un método de clasificación que busca el hiperplano de separación
que **maximiza el margen** entre clases —la distancia entre el hiperplano y las
observaciones más cercanas de cada clase, llamadas vectores de soporte (Cortes &
Vapnik, 1995; Vapnik, 1998). Su extensión a problemas de regresión, la **Support
Vector Regression** (SVR, Smola & Schölkopf, 2004), es la variante efectivamente
utilizada en este trabajo: en lugar de buscar un hiperplano que separe clases, SVR
busca una función que se aparte como máximo un margen $\epsilon$ del valor real
observado para la mayor cantidad de puntos posible, penalizando únicamente los
errores que exceden ese margen (la llamada función de pérdida
**$\epsilon$-insensible**).

Cuando la relación entre los predictores y la variable objetivo no es lineal, SVR
recurre al **truco del kernel** (*kernel trick*): en vez de ajustar una función
lineal directamente sobre los predictores originales, los proyecta —implícitamente,
sin calcular la proyección de forma explícita— a un espacio de mayor dimensión en el
que sí resulta razonable ajustar una relación lineal. El kernel **RBF**
(*Radial Basis Function*, o gaussiano) es la elección más habitual cuando no hay
información previa que sugiera una forma funcional específica, y es el utilizado en
este trabajo (ver sección 4.5.2). Tres hiperparámetros gobiernan el comportamiento
del modelo: $C$ (la penalización por errores que exceden el margen $\epsilon$, que
regula el balance entre ajuste y regularización), $\gamma$ (que controla el alcance
de la influencia de cada observación de entrenamiento en el kernel RBF) y el propio
$\epsilon$. A diferencia de los modelos basados en árboles descriptos más adelante en
esta sección, SVR es sensible a la escala de los predictores —dado que su
formulación depende de distancias entre observaciones—, por lo que requiere
estandarizar los features antes de entrenar (ver sección 4.5.2), y no admite valores
faltantes en la matriz de entrada, una limitación práctica que también se retoma en
el capítulo 4.

#### 3.3.3. Árboles de decisión

Los métodos basados en árboles de decisión segmentan el espacio de los predictores
en regiones simples y no superpuestas; para predecir el valor de una nueva
observación, se utiliza la media (en un árbol de regresión) de las observaciones de
entrenamiento que caen en la misma región (James, Witten, Hastie & Tibshirani,
2021). El conjunto de reglas de división puede representarse gráficamente como un
árbol, de donde toma su nombre el método: los puntos donde el espacio se subdivide
se llaman nodos internos, y los segmentos que conectan nodos, ramas.

La construcción de un árbol de regresión sigue, en términos generales, dos pasos: se
divide el espacio de los predictores $X_1, X_2, \ldots, X_p$ en $J$ regiones
distintas $R_1, \ldots, R_J$, y toda observación que cae dentro de una región $R_j$
recibe como predicción la media de la variable objetivo entre las observaciones de
entrenamiento de esa región. Las regiones se eligen mediante **división binaria
recursiva** (*recursive binary splitting*): en cada paso se busca el predictor
$X_j$ y el punto de corte $s$ que maximizan la reducción en la suma de residuos al
cuadrado, dividiendo las observaciones en $\{X \mid X_j < s\}$ y
$\{X \mid X_j \geq s\}$ (James et al., 2021).

Un árbol individual, aunque simple e interpretable, suele tener una capacidad de
predicción limitada frente a otros métodos de regresión. Los métodos de ensamble
descriptos a continuación explotan precisamente esta limitación —y, en particular,
la alta varianza de un árbol no podado— para construir modelos sustancialmente más
potentes.

#### 3.3.4. Métodos de ensamble: Bagging, Random Forest y Gradient Boosting

**Bagging** (*Bootstrap Aggregating*, Breiman, 1996) es un procedimiento general
para reducir la varianza de un método de aprendizaje: se entrenan múltiples árboles
—sin podar, por lo que cada uno individualmente tiene varianza alta y sesgo bajo—
sobre distintas muestras bootstrap de los datos de entrenamiento, y se promedian sus
predicciones. **Random Forest** (Breiman, 2001) mejora sobre Bagging forzando, en
cada división de cada árbol, a considerar solamente un subconjunto aleatorio de los
predictores disponibles —no la totalidad—, lo que reduce la correlación entre los
árboles del ensamble y, con ella, la varianza del promedio resultante. Es el método
utilizado en este trabajo bajo el nombre de Random Forest (sección 4.5.2), y su
principal ventaja práctica frente a SVM es que admite valores faltantes de forma
nativa en implementaciones modernas —una propiedad explotada explícitamente en el
tratamiento de datos faltantes de este proyecto (ver sección 4.3)— y expone una
medida de importancia de variables directamente interpretable.

A diferencia de Bagging y Random Forest, que construyen árboles independientes entre
sí, el **Gradient Boosting** (Friedman, 2001) construye los árboles de forma
secuencial: cada nuevo árbol se ajusta para corregir los errores (más precisamente,
el gradiente de la función de pérdida) del ensamble construido hasta ese momento, en
lugar de ajustar un único árbol grande de una sola vez —un enfoque de aprendizaje
"lento" y aditivo que, con suficientes iteraciones bien reguladas, generalmente
generaliza mejor que un árbol único de gran profundidad. XGBoost y LightGBM,
desarrollados en las dos secciones siguientes, son dos implementaciones distintas y
altamente optimizadas de esta misma idea general.

#### 3.3.5. XGBoost

XGBoost (*Extreme Gradient Boosting*, Chen & Guestrin, 2016) es una implementación
de Gradient Boosting que incorpora, respecto de la formulación original de Friedman
(2001), una serie de mejoras orientadas simultáneamente a la regularización del
modelo y a la eficiencia computacional. En términos de regularización, XGBoost
incorpora explícitamente en su función objetivo penalizaciones L1 y L2 sobre la
complejidad del árbol (número de hojas y magnitud de los valores predichos en cada
hoja), además del término de pérdida propiamente dicho —el hiperparámetro de
penalización L2 (`reg_lambda`) es, de hecho, uno de los buscados explícitamente en
este trabajo (ver sección 4.5.2)—. En términos de optimización, XGBoost utiliza una
aproximación de segundo orden (tipo Newton) del gradiente de la función de pérdida
para decidir cada división, en lugar de la aproximación de primer orden del
Gradient Boosting original, lo que en general permite convergencia más rápida y
precisa.

Una característica de XGBoost particularmente relevante para este trabajo es su
manejo nativo de valores faltantes: en lugar de requerir que se complete la matriz
de entrada con algún valor imputado, XGBoost aprende, para cada división del árbol,
cuál es la dirección por defecto (izquierda o derecha) hacia la que deben enviarse
las observaciones con datos faltantes en esa variable —tratando la propia
ausencia de dato como una señal potencialmente informativa, no como un problema a
resolver antes del entrenamiento (Chen & Guestrin, 2016). Esta propiedad es la que
permite, en este trabajo, pasar a XGBoost las columnas con gaps estructurales reales
sin imputar (ver sección 4.3), a diferencia de SVM.

Al ser un método de alta capacidad, XGBoost es también particularmente propenso al
sobreajuste sobre datasets de tamaño moderado si no se controla explícitamente su
complejidad —mediante regularización, profundidad máxima acotada, o, especialmente,
*early stopping* (deteniendo el entrenamiento cuando la métrica de validación deja
de mejorar, en lugar de fijar de antemano el número de árboles). Esta sensibilidad
se retoma de forma concreta en la discusión de resultados de este trabajo (sección
5.2), donde resulta directamente relevante para interpretar el desempeño obtenido.

#### 3.3.6. LightGBM

LightGBM (Ke et al., 2017) es, al igual que XGBoost, una implementación de Gradient
Boosting sobre árboles de decisión, desarrollada por Microsoft con un énfasis
particular en velocidad de entrenamiento y eficiencia de memoria sobre datasets de
gran volumen. Dos innovaciones distinguen a LightGBM de implementaciones anteriores
de Gradient Boosting:

- **Búsqueda de particiones basada en histogramas:** en lugar de evaluar todos los
  valores posibles de corte de cada variable continua, LightGBM agrupa (*bins*) los
  valores en un histograma de resolución acotada y evalúa cortes solo sobre esos
  contenedores, reduciendo drásticamente la complejidad computacional de cada
  división sin una pérdida relevante de precisión.
- **Crecimiento de árboles por hoja (*leaf-wise*), no por nivel (*level-wise*):** la
  mayoría de las implementaciones de árboles de boosting hacen crecer el árbol nivel
  por nivel, expandiendo todas las hojas de una misma profundidad antes de pasar a
  la siguiente. LightGBM, en cambio, siempre expande la hoja que produce la mayor
  reducción posible en la función de pérdida, sin importar su profundidad relativa
  —lo que tiende a producir árboles más profundos y desbalanceados, potencialmente
  más precisos, pero también más propensos a sobreajustar sobre datasets chicos si
  no se limita explícitamente la profundidad máxima (Ke et al., 2017).

Al igual que XGBoost, LightGBM admite valores faltantes de forma nativa
(parámetro `use_missing`, activado por defecto), por lo que en este trabajo recibe
las mismas columnas con gaps estructurales reales sin imputar que XGBoost y Random
Forest (ver sección 4.3).

### 3.4. Modelos de Deep Learning

El aprendizaje profundo (*Deep Learning*) es una subárea del aprendizaje automático
orientada a aprender representaciones de los datos mediante capas sucesivas de
transformación, cada una construyendo representaciones progresivamente más
significativas a partir de la anterior; la cantidad de capas que contribuyen a un
modelo se denomina su profundidad (Chollet, 2021).

#### 3.4.1. Redes neuronales: definiciones generales

Una red neuronal artificial organiza neuronas (o nodos) en una estructura de capas:
los predictores forman la capa de entrada, los pronósticos la capa de salida, y
entre ambas puede haber una o más capas intermedias de neuronas ocultas. Una red sin
capas ocultas es equivalente a una regresión lineal; al incorporar capas ocultas con
funciones de activación no lineales, la red adquiere capacidad de representar
relaciones no lineales entre predictores y variable objetivo. Las entradas a cada
neurona se combinan mediante una suma ponderada por los **pesos** de la red (el
conocimiento que el modelo va adquiriendo durante el entrenamiento, inicializados en
valores pequeños aleatorios), y el resultado se transforma mediante una **función de
activación** no lineal antes de propagarse a la capa siguiente (Chollet, 2021).

Entre las arquitecturas de red neuronal más relevantes para este trabajo se
encuentran las **redes neuronales convolucionales** (CNN), en las que cada neurona
se conecta solo con un subconjunto local de la capa anterior —lo que reduce
drásticamente el número de parámetros respecto de una red totalmente conectada, y
las vuelve particularmente adecuadas para detectar patrones locales en datos con
estructura espacial o secuencial (LeCun, Bottou, Bengio & Haffner, 1998)—, y las
**redes neuronales recurrentes** (RNN), que a diferencia de las arquitecturas
puramente *feedforward* permiten conexiones que retroalimentan la salida de una capa
como entrada de sí misma en el paso temporal siguiente, dotando a la red de una
forma de memoria y haciéndola naturalmente apta para datos secuenciales ordenados en
el tiempo.

#### 3.4.2. Redes neuronales recurrentes y el problema del gradiente

En una RNN, la salida (o estado oculto) de un paso temporal se retroalimenta como
entrada adicional del paso siguiente, lo que permite a la red aprender y explotar el
orden de las observaciones dentro de una secuencia (Brownlee, 2017) —una propiedad
que ninguno de los modelos de las secciones 3.2 y 3.3 explota de forma explícita
sobre secuencias arbitrariamente largas: ARIMA solo captura dependencia lineal hasta
el orden fijado, y los modelos de árbol de la sección 3.3 tratan cada observación
como independiente salvo que la secuencia se codifique manualmente como features
rezagados.

El principal desafío técnico para entrenar una RNN es el llamado **problema del
gradiente que se desvanece o explota** (*vanishing/exploding gradient problem*): al
propagar el error hacia atrás a través de muchos pasos temporales (sección 3.4.7),
los gradientes pueden volverse sucesivamente más pequeños (impidiendo que la red
aprenda dependencias de largo plazo) o más grandes (haciendo inestable el
entrenamiento), en ambos casos degradando severamente el ajuste de una RNN simple
sobre secuencias largas.

#### 3.4.3. Redes LSTM

Las redes **LSTM** (*Long Short-Term Memory*, Hochreiter & Schmidhuber, 1997, con el
mecanismo de *forget gate* añadido por Gers, Schmidhuber & Cummins, 2000, en la
formulación hoy estándar que se presenta a continuación) son un tipo de RNN
diseñado específicamente para superar el problema del gradiente, mediante un
mecanismo explícito de compuertas que decide qué información se conserva y cuál se
descarta a lo largo del tiempo, permitiendo una memoria efectiva de más largo plazo
que una RNN simple.

Cada celda LSTM mantiene un **estado de celda** $C_t$ (la memoria de largo plazo) y
un **estado oculto** $h_t$ (la salida en el paso $t$), actualizados mediante tres
compuertas, cada una una función sigmoidea que produce valores entre 0 y 1
(interpretables como "cuánto dejar pasar"):

$$f_t = \sigma(W_f \cdot [h_{t-1}, x_t] + b_f) \qquad \text{(olvido)} \qquad (3.6)$$
$$i_t = \sigma(W_i \cdot [h_{t-1}, x_t] + b_i) \qquad \text{(entrada)} \qquad (3.7)$$
$$\tilde{C}_t = \tanh(W_C \cdot [h_{t-1}, x_t] + b_C) \qquad \text{(candidato)} \qquad (3.8)$$
$$C_t = f_t \odot C_{t-1} + i_t \odot \tilde{C}_t \qquad \text{(actualización de memoria)} \qquad (3.9)$$
$$o_t = \sigma(W_o \cdot [h_{t-1}, x_t] + b_o) \qquad \text{(salida)} \qquad (3.10)$$
$$h_t = o_t \odot \tanh(C_t) \qquad (3.11)$$

donde $x_t$ es la entrada en el paso $t$, $[h_{t-1}, x_t]$ denota la concatenación
del estado oculto anterior con la entrada actual, $\odot$ es el producto elemento a
elemento, y $W_\bullet$, $b_\bullet$ son los pesos y sesgos de cada compuerta,
ajustados durante el entrenamiento. Intuitivamente: la **compuerta de olvido** ($f_t$)
decide qué proporción de la memoria anterior se conserva; la **compuerta de
entrada** ($i_t$), combinada con el estado candidato $\tilde{C}_t$, decide qué
información nueva se incorpora a la memoria; y la **compuerta de salida** ($o_t$)
decide qué parte de la memoria actualizada se expone como salida del paso $t$. Es
esta separación explícita entre "memoria interna" ($C_t$) y "salida" ($h_t$),
regulada por compuertas entrenables, lo que le permite a una LSTM preservar
información relevante a lo largo de muchos pasos temporales sin que el gradiente se
desvanezca en el proceso.

#### 3.4.4. Redes GRU

La **Gated Recurrent Unit** (GRU, Cho et al., 2014) es una variante simplificada de
LSTM que combina las compuertas de olvido y entrada en una única **compuerta de
actualización** ($z_t$), y prescinde de un estado de celda separado del estado
oculto:

$$z_t = \sigma(W_z \cdot [h_{t-1}, x_t]) \qquad \text{(actualización)} \qquad (3.12)$$
$$r_t = \sigma(W_r \cdot [h_{t-1}, x_t]) \qquad \text{(reinicio)} \qquad (3.13)$$
$$\tilde{h}_t = \tanh(W \cdot [r_t \odot h_{t-1}, x_t]) \qquad \text{(candidato)} \qquad (3.14)$$
$$h_t = (1 - z_t) \odot h_{t-1} + z_t \odot \tilde{h}_t \qquad (3.15)$$

La compuerta de **reinicio** ($r_t$) determina cuánto del estado anterior se ignora
al calcular el candidato $\tilde{h}_t$, mientras que la de actualización ($z_t$)
interpola entre el estado anterior y el candidato para producir el nuevo estado. Al
tener menos parámetros que una LSTM equivalente (dos compuertas en lugar de tres, y
sin estado de celda separado), una GRU es más liviana de entrenar y, en muchas
tareas, alcanza un desempeño comparable —una comparación empírica directa entre
ambas arquitecturas, con el mismo protocolo de entrenamiento, es precisamente uno de
los ejercicios realizados en este trabajo (ver sección 5.3).

#### 3.4.5. Arquitectura híbrida CNN-LSTM

Una arquitectura híbrida **CNN-LSTM** combina una o más capas convolucionales
(típicamente `Conv1d` cuando la entrada es una secuencia unidimensional, como una
serie de tiempo) con una o más capas recurrentes LSTM: la capa convolucional actúa
primero como un extractor de patrones locales a lo largo del eje temporal —de forma
análoga a como una CNN extrae patrones espaciales locales en una imagen—, y la
representación resultante se pasa a una LSTM para modelar la dependencia secuencial
de más largo plazo sobre esos patrones ya extraídos, en lugar de sobre la serie
cruda. Esta combinación fue propuesta originalmente para tareas de reconocimiento de
habla (Sainath, Vinyals, Senior & Sak, 2015) y se ha adoptado ampliamente desde
entonces en tareas de pronóstico de series de tiempo, bajo la intuición de que
permite a la red capturar simultáneamente patrones de corto plazo (mediante la
convolución) y de más largo plazo (mediante la recurrencia).

#### 3.4.6. Mecanismos de atención y arquitecturas basadas en Transformer

Tanto LSTM como GRU procesan una secuencia comprimiendo, en cada paso, toda la
información relevante del pasado en un único vector de estado oculto de tamaño
fijo —un "cuello de botella" que puede dificultar preservar información de pasos
muy alejados en secuencias largas, aun con el mecanismo de compuertas descripto en
las secciones 3.4.3 y 3.4.4—. Los **mecanismos de atención** (Vaswani et al., 2017)
proponen una alternativa: en lugar de depender de un único estado comprimido, la red
aprende a asignar, para cada predicción, un peso de relevancia distinto a cada paso
temporal de la entrada, permitiendo acceder directamente a cualquier punto de la
secuencia sin necesidad de que esa información "sobreviva" comprimida a través de
todos los pasos intermedios.

La arquitectura **Transformer** (Vaswani et al., 2017) lleva esta idea al extremo de
prescindir por completo de la recurrencia: en su lugar, utiliza **auto-atención
multi-cabeza** (*multi-head self-attention*), que permite a cada posición de la
secuencia atender directamente a todas las demás en un único paso, combinada con un
**encoding posicional** —típicamente funciones seno/coseno de frecuencia creciente—
que le permite a la red recuperar la información de orden secuencial que, al
prescindir de la recurrencia, ya no está implícita en el propio mecanismo de
procesamiento.

Sobre esta base, Lim et al. (2019, publicado en 2021) propusieron el **Temporal
Fusion Transformer** (TFT), una arquitectura específicamente diseñada para pronóstico
de series de tiempo multi-horizonte, que combina atención con redes de selección de
variables, mecanismos de *gating*, y un encoder dedicado a covariables estáticas —
pensada para escenarios con múltiples series y entidades que comparten covariables
que no varían en el tiempo (por ejemplo, atributos propios de cada tienda al
pronosticar la demanda de una cadena de comercios). Ninguno de esos componentes
adicionales del TFT completo resulta necesariamente aplicable a un escenario de una
única serie sin covariables estáticas, como el del RFX20 en este trabajo —una
consideración de alcance que se retoma explícitamente en la sección 4.5.3, donde se
describe la arquitectura efectivamente implementada.

#### 3.4.7. Optimización basada en el gradiente

El ajuste de los pesos de una red neuronal se realiza mediante **descenso del
gradiente**: se calcula el gradiente de la función de pérdida respecto de cada peso
—mediante el algoritmo de **retropropagación** (*backpropagation*, Rumelhart,
Hinton & Williams, 1986), que aplica la regla de la cadena para propagar el error
desde la salida de la red hacia atrás, capa por capa— y se actualiza cada peso en la
dirección que reduce esa pérdida. La magnitud de cada actualización está regulada
por la **tasa de aprendizaje** (*learning rate*): una tasa demasiado pequeña
requiere muchas iteraciones y puede estancarse en un mínimo local; una tasa
demasiado grande puede producir actualizaciones inestables que impidan la
convergencia (Chollet, 2021). El optimizador **Adam** (Kingma & Ba, 2015), que
adapta la tasa de aprendizaje de cada parámetro combinando estimaciones de primer y
segundo momento del gradiente, es el utilizado en los modelos de Deep Learning de
este trabajo (ver sección 4.5.3).

#### 3.4.8. Datos secuenciales: ventanas y tensores de rango 3

A diferencia de los modelos de la sección 3.3, que reciben cada observación como un
vector de features independiente, los modelos de esta sección requieren que la
información temporal se codifique explícitamente en la forma de los datos de
entrada: cada muestra se representa como una secuencia de vectores —un tensor de
rango 2, tiempo × features— y un lote de muestras se codifica como un tensor de
rango 3 (Chollet, 2021). En la práctica, esto se instrumenta mediante **ventanas
deslizantes**: para predecir el valor en $t+h$, se construye una ventana con las
últimas $L$ observaciones (el **lookback**) hasta $t$, y esa ventana —no la
observación aislada en $t$— es la unidad de entrada de la red. La elección del
lookback $L$ es, en sí misma, un hiperparámetro del modelo, tratado como tal en este
trabajo (ver sección 4.5.3).

### 3.5. Métricas de evaluación y validación en series de tiempo

#### 3.5.1. Separación de datos: entrenamiento, validación y prueba

Un modelo debe evaluarse sobre datos que no ha visto durante el entrenamiento
(Zheng, 2015): evaluarlo sobre los mismos datos con los que fue entrenado produciría
una puntuación artificialmente perfecta, sin ninguna capacidad demostrada de
generalizar a observaciones nuevas —situación conocida como **sobreajuste**
(*overfitting*)—. Por el mismo motivo, seleccionar hiperparámetros comparando
candidatos directamente contra el conjunto reservado para la evaluación final
introduce el riesgo de sobreajustar esa selección al propio conjunto de evaluación,
inflando artificialmente la métrica reportada. Esto motiva la práctica estándar de
dividir los datos disponibles en tres partes: **entrenamiento** (para ajustar los
parámetros del modelo), **validación** (para comparar configuraciones o
hiperparámetros candidatos) y **prueba** (para una única evaluación final, honesta,
del modelo ya seleccionado). Esta partición en tres conjuntos —con la variante
adicional descripta en 3.5.3— es la que se utiliza en este trabajo (ver sección 4.4).

#### 3.5.2. Validación cruzada y su adaptación a series de tiempo

La partición en tres conjuntos deja abierta una pregunta adicional: el resultado
obtenido puede depender, hasta cierto punto, de dónde exactamente se trazó el corte
entre entrenamiento y validación. La **validación cruzada** (*k-fold
cross-validation*) aborda este problema dividiendo los datos en $k$ particiones,
entrenando $k$ modelos distintos (cada uno usando $k-1$ particiones como
entrenamiento y la restante como validación) y promediando el resultado sobre las
$k$ evaluaciones, en lugar de depender de una única partición fija.

Aplicada tal cual a datos ordenados temporalmente, la validación cruzada estándar
violaría el orden de la serie: entrenar con datos posteriores para validar sobre
datos anteriores no respeta la restricción de que, en un escenario de pronóstico
real, únicamente se dispone de información pasada. La adaptación estándar para este
caso es la **validación cruzada expansiva para series de tiempo** (`TimeSeriesSplit`
en la implementación de referencia de scikit-learn): en cada fold sucesivo, el
conjunto de entrenamiento es un superconjunto —nunca un subconjunto ni un conjunto
disjunto— del fold anterior, y el conjunto de validación de cada fold siempre
corresponde a observaciones posteriores a las de su propio entrenamiento. Esta es la
estrategia utilizada en este trabajo para la selección de hiperparámetros de los
modelos de Machine Learning (sección 4.5.2).

#### 3.5.3. Validación walk-forward

Una estrategia distinta, y complementaria, a la validación cruzada expansiva de
3.5.2 es la **validación walk-forward**: en lugar de reservar folds fijos para
comparar hiperparámetros, el modelo se reentrena (o se re-estima) secuencialmente,
un paso a la vez, incorporando cada nueva observación real a la historia disponible
antes de emitir el siguiente pronóstico. Es la estrategia de evaluación
efectivamente utilizada en este trabajo para los modelos estadísticos de la sección
3.2 (ARIMA/SARIMA y GARCH, ver sección 4.5.1): el orden del modelo se fija una única
vez (por costo computacional, ver esa misma sección), pero sus coeficientes se
reestiman en cada paso del walk-forward sobre el conjunto de validación, de modo que
cada pronóstico individual se genera con toda la información disponible hasta ese
momento y ninguna posterior. A diferencia de la validación cruzada expansiva
—pensada para comparar configuraciones candidatas—, el walk-forward está pensado
para producir una serie completa de pronósticos "en producción simulada",
directamente comparable contra los valores reales observados.

#### 3.5.4. Fuga de información en validación temporal: purga de folds

Un riesgo metodológico específico de la validación cruzada expansiva (sección 3.5.2)
aplicada a un problema de pronóstico a horizonte $h > 1$ es que las últimas $h$
filas de un fold de entrenamiento pueden tener, como variable objetivo, un valor
que corresponde temporalmente a fechas ya incluidas en el fold de validación
siguiente —una forma sutil de fuga de información (*data leakage*), inadvertida
porque no involucra directamente a los predictores sino a la superposición temporal
entre el objetivo de un fold y las observaciones del siguiente—. López de Prado
(2018) formaliza esta clase de problema, específico de aplicaciones de Machine
Learning a datos financieros, y propone la técnica de **purga** (*purging*):
eliminar del extremo final de cada fold de entrenamiento las observaciones cuya
ventana de horizonte se superpone con el fold de validación siguiente, de modo que
ningún objetivo de entrenamiento contenga información temporal del período que se
usará para evaluar. El efecto de esta fuga es despreciable para horizontes cortos
(1 a 5 días, el foco de este trabajo) frente al tamaño de cada fold, pero deja de
serlo en horizontes más largos —una distinción tratada explícitamente en la sección
4.5.2 de este trabajo, en el contexto de una exploración de horizontes extendidos.

#### 3.5.5. Métricas de error de pronóstico

El **error de pronóstico** para una observación es, simplemente, la diferencia entre
el valor observado y el valor pronosticado (Brownlee, 2020):

$$e_t = Y_t - \hat{Y}_t \qquad (3.16)$$

A partir de esta cantidad, calculada para cada observación de un conjunto de
evaluación de tamaño $N$, se derivan las métricas de error agregadas más utilizadas
en este trabajo (ver sección 5.1 en adelante):

$$\text{MAE} = \frac{1}{N}\sum_{t=1}^{N} |Y_t - \hat{Y}_t| \qquad \text{(Error Absoluto Medio)} \qquad (3.17)$$

$$\text{MSE} = \frac{1}{N}\sum_{t=1}^{N} (Y_t - \hat{Y}_t)^2 \qquad \text{(Error Cuadrático Medio)} \qquad (3.18)$$

$$\text{RMSE} = \sqrt{\text{MSE}} \qquad \text{(Raíz del Error Cuadrático Medio)} \qquad (3.19)$$

$$\text{MAPE} = \frac{100\%}{N}\sum_{t=1}^{N} \left|\frac{Y_t - \hat{Y}_t}{Y_t}\right| \qquad \text{(Error Porcentual Absoluto Medio)} \qquad (3.20)$$

El MAE da una idea directa e interpretable de la magnitud promedio del error, sin
indicar su dirección (sobre- o sub-estimación) ni penalizar de forma distinta los
errores grandes de los pequeños. El RMSE, al elevar al cuadrado antes de promediar,
penaliza más que proporcionalmente los errores grandes —por lo que es sensible a
valores atípicos: un único punto con error muy grande puede dominar la métrica—, una
propiedad relevante para la interpretación de resultados de este trabajo dado que la
serie de retornos del RFX20 presenta colas pesadas y eventos extremos documentados
(ver capítulo 4). El MAPE expresa el error en términos porcentuales relativos al
valor real, lo que facilita la interpretación en unidades de negocio, pero no está
definido cuando el valor real es cero o cercano a cero —una limitación práctica
relevante cuando la variable objetivo es un retorno logarítmico diario, que
frecuentemente toma valores muy próximos a cero (ver capítulo 4)—.

#### 3.5.6. Métricas de acierto direccional y de relevancia económica

Más allá de la magnitud del error, en un problema de pronóstico financiero suele
ser al menos igual de relevante acertar la **dirección** del movimiento —si el
retorno será positivo o negativo— que su magnitud exacta, dado que buena parte de
las decisiones de trading dependen del signo del movimiento esperado más que de su
valor puntual. El **Hit Ratio** (o *directional accuracy*) mide la proporción de
observaciones en las que el signo del pronóstico coincide con el signo del valor
real observado, y puede complementarse con las métricas de **precisión** y
**exhaustividad** (*recall*) de una clasificación binaria alcista/bajista, en
particular cuando existe desbalance entre la cantidad de jornadas de suba y de baja
en el período evaluado.

Finalmente, un conjunto de métricas de **relevancia económica** evalúa el valor
práctico de un modelo de pronóstico más allá de sus propiedades estadísticas: una
simulación simple de estrategia de trading (por ejemplo, tomar posición larga o
corta según el signo del pronóstico) permite calcular el retorno acumulado de esa
estrategia frente a una referencia pasiva (*buy-and-hold*), el **ratio de Sharpe**
(el retorno de la estrategia por unidad de riesgo asumido) y el **drawdown máximo**
(la mayor caída acumulada desde un máximo previo del capital de la estrategia). Este
conjunto de métricas —hit ratio, precisión/recall direccional y backtesting
económico— forma parte del marco de evaluación multicriterio previsto en el Plan de
Trabajo Final de este proyecto, pero **su aplicación efectiva a los modelos de este
trabajo corresponde a la Fase 5** (comparación y selección, ver capítulo 5,
sección 5.4), todavía no cerrada al momento de escribir este capítulo: los
resultados reportados en las secciones 5.1 a 5.3 de este trabajo se basan
principalmente en RMSE y MAE (sección 3.5.5), que son las métricas efectivamente
calculadas hasta el momento para las nueve familias de modelos comparadas.

### 3.6. Trabajos relacionados: predicción de series financieras en mercados emergentes

La predicción de índices bursátiles y de activos financieros individuales mediante
métodos estadísticos, de Machine Learning y de Deep Learning cuenta con una
literatura extensa, mayormente desarrollada sobre mercados desarrollados. Bhandari,
Rimal, Pokhrel, Rimal, Dahal y Khatri (2022) muestran que redes LSTM superan
consistentemente a métodos estadísticos clásicos al predecir el índice S&P 500,
mientras que Yavasani y Wang (2023) realizan una comparación directa entre LSTM, GRU
y ARIMA sobre precios de mercado, encontrando también una ventaja sistemática de los
métodos de Deep Learning por sobre ARIMA. Estos y otros trabajos similares (Kulkarni,
Vijayakumar Bharathi, Perdana & Kilari, 2025) sostienen que una comparación
exhaustiva entre familias de modelos —estadísticos, de Machine Learning y de Deep
Learning— es la vía más efectiva para identificar la arquitectura más adecuada para
un activo financiero determinado, en lugar de asumir a priori que una familia
domina a las demás; es precisamente esta lógica comparativa, y no la búsqueda de un
único modelo "ganador" definido de antemano, la que estructura la metodología de
este trabajo (capítulo 4).

Un hilo relevante de esta literatura, sin embargo, es menos optimista respecto de la
ventaja sistemática del Deep Learning sobre otros enfoques: Mohapatra, Mukherjee,
Apergis y Sengupta (2025) destacan que la ingeniería de features (variables técnicas,
fundamentales y macroeconómicas) es un factor tan o más determinante que la elección
de arquitectura para explicar el desempeño de modelos de ensamble sobre acciones
bancarias, y Nasir, Iftikhar, Aamir, Iftikhar, Rodrigues y Rehman (2025) encuentran
que un enfoque híbrido que combina descomposición de la serie con modelos
estadísticos y de Machine Learning puede superar a arquitecturas de Deep Learning
puras sobre el índice NASDAQ Composite. Gülmez (2023), por su parte, se enfoca
específicamente en la optimización de hiperparámetros de redes LSTM mediante
metaheurísticas, subrayando que buena parte del desempeño reportado en la literatura
de Deep Learning aplicado a mercados financieros depende críticamente de un ajuste
fino de hiperparámetros no siempre reproducible fuera del estudio original —una
consideración que motiva, en este trabajo, documentar explícitamente el protocolo de
búsqueda de hiperparámetros utilizado para cada familia de modelos (sección 4.5), en
lugar de reportar únicamente el resultado final.

La literatura orientada específicamente a mercados emergentes, y en particular al
mercado argentino, es sustancialmente más escasa. Edwards, Biscarri y de Gracia
(2003) documentan que los mercados emergentes atraviesan ciclos de volatilidad
marcadamente más extremos que los mercados desarrollados, especialmente en episodios
de liberalización financiera, mientras que Assaf, Al-Shboul, Mokni y Demir (2025)
confirman, en un análisis más reciente sobre mercados latinoamericanos, tanto la
elevada volatilidad de estos mercados como su fuerte interconexión con factores de
riesgo regionales y globales. Estos trabajos no abordan directamente la predicción
del RFX20, pero sí caracterizan empíricamente el contexto de alta volatilidad y
fuerte influencia macroeconómica que motiva, en este trabajo, la inclusión explícita
de variables macroeconómicas locales (capítulo 4) más allá de los indicadores
técnicos estándar utilizados en la literatura de mercados desarrollados.

Dentro de los antecedentes directos sobre el mercado argentino, Mastrangelo y
Salvatierra (2022) analizan el desempeño ajustado por riesgo de fondos de inversión
de renta variable local —relevante para este trabajo en tanto el RFX20 es,
precisamente, el benchmark de referencia para buena parte de esos fondos (ver
capítulo 1)—, mientras que Ruiz Solivella (2025) aplica Random Forest a la
predicción de movimientos de los principales índices bursátiles, y Pimentel Ramírez
(2024), en un trabajo de tesis de maestría de la Universidad de Chile, aplica
modelos recurrentes y convolucionales con mecanismos de atención a índices
bursátiles extranjeros —un antecedente metodológicamente cercano a la arquitectura
"Transformer encoder" evaluada en este trabajo (sección 3.4.6)—.

Finalmente, cabe destacar como antecedente directo el trabajo de Drago (2023),
desarrollado en el marco de la misma Maestría en Explotación de Datos y Gestión del
Conocimiento de la Universidad Austral, que compara modelos ARIMA, GARCH, LightGBM y
LSTM para predecir el precio del Estireno —un producto petroquímico de cotización
internacional—. Más allá de la similitud de alcance metodológico (la misma
progresión de tres paradigmas: estadístico, Machine Learning y Deep Learning),
resulta particularmente relevante para la discusión de resultados de este trabajo
(capítulo 5) que ese antecedente encontró, también, que la serie de precios
analizada se comportaba como ruido blanco frente a los modelos ARIMA/GARCH, y que —a
diferencia de lo esperado a priori— los modelos de Machine Learning (LightGBM)
terminaron superando a los de Deep Learning (LSTM) en ese caso concreto. Si bien se
trata de un producto y un mercado distintos a los de este trabajo, la coincidencia
en el patrón metodológico (fracaso de los modelos estadísticos clásicos frente a una
serie de comportamiento cercano al ruido blanco) constituye un punto de comparación
directo y valioso al discutir los resultados obtenidos para el RFX20.

**Tabla 3.1.** Síntesis comparativa de los antecedentes citados — variable objetivo,
comparación de modelos y validación (agregada 4-nov-2026, Punto 10 del feedback de
los directores). Las celdas marcadas "no especificado" reflejan el nivel de detalle
disponible en la cita tal como se la describe en este trabajo, no una verificación
directa contra la fuente original — distinguir trabajos que predicen **nivel** de
precio de los que predicen **retorno** es precisamente el punto que señala el
director, y no siempre es inferible solo de la descripción narrativa ya incluida más
arriba.

| Estudio | Activo / mercado | Variable objetivo | Familias comparadas | Validación |
|---|---|---|---|---|
| Bhandari et al. (2022) | S&P 500 | No especificado en este trabajo | LSTM vs. métodos estadísticos clásicos | No especificado en este trabajo |
| Yavasani y Wang (2023) | Precios de mercado (no especificado cuál) | **Nivel** (el texto dice "precios de mercado", no retornos) | LSTM, GRU, ARIMA | No especificado en este trabajo |
| Mohapatra et al. (2025) | Acciones bancarias | No especificado en este trabajo | Ensamble, con foco en ingeniería de features vs. arquitectura | No especificado en este trabajo |
| Nasir et al. (2025) | NASDAQ Composite | No especificado en este trabajo | Híbrido (descomposición + estadístico + ML) vs. Deep Learning puro | No especificado en este trabajo |
| Gülmez (2023) | No especifica un mercado puntual (foco metodológico) | No aplica — foco en optimización de hiperparámetros de LSTM | LSTM (metaheurísticas de ajuste) | No especificado en este trabajo |
| Ruiz Solivella (2025) | Índices bursátiles argentinos | **Retorno/dirección** (el texto dice "movimientos", no niveles) | Random Forest | No especificado en este trabajo |
| Pimentel Ramírez (2024) | Índices bursátiles extranjeros | No especificado en este trabajo | Recurrentes y convolucionales con atención | No especificado en este trabajo |
| Drago (2023) | Estireno (commodity petroquímico) | **Nivel** (el texto dice "el precio del Estireno") | ARIMA, GARCH, LightGBM, LSTM | No especificado en este trabajo |

Mastrangelo y Salvatierra (2022), Edwards, Biscarri y de Gracia (2003) y Assaf et al.
(2025) se citan arriba como contexto de mercado (desempeño de fondos, caracterización
de volatilidad en mercados emergentes), no como estudios de predicción algorítmica
comparables en estructura a los de la tabla — se excluyen de ella por ese motivo, no
por omisión.

De los ocho estudios de predicción listados, solo tres permiten clasificar la
variable objetivo con la información ya incluida en este trabajo: dos predicen
**nivel** de precio (Yavasani y Wang 2023; Drago 2023) y uno predice **retorno o
dirección** (Ruiz Solivella 2025) — exactamente la distinción que señala el
director como relevante, y que en los cinco casos restantes no puede resolverse sin
consultar la fuente original (pendiente, no se afirma un valor sin poder
verificarlo). Es, en cualquier caso, una distinción metodológicamente central: un
estudio que reporta buen desempeño prediciendo el **nivel** de un precio (una serie
con tendencia, altamente autocorrelacionada) no es directamente comparable con este
trabajo, que predice **retornos** (una serie mucho más cercana a ruido blanco por
construcción) — la dificultad relativa de ambos problemas no es la misma, y
conflacionarlos sobreestimaría qué tan "fácil" debería ser el problema abordado acá.

---

*(Con esta sub-entrega se completa el Capítulo 3.)*

## 4. Metodología

*(Capítulo en construcción por sub-entregas. Esta versión cubre 4.1 y 4.2
—procedimiento general y descripción de los datos, incluida la calidad de datos—.
Quedan pendientes 4.3 (ingeniería de features), 4.4 (particionamiento temporal) y
4.5 (modelos desarrollados, con una sub-sección por familia).)*

### 4.1. Procedimiento general

El presente trabajo constituye un estudio de tipo empírico/aplicado, desarrollado en
colaboración con Primary S.A., lo que permitió el acceso a datos propietarios de la
plataforma tecnológica de A3 Mercados (sección 2.1) y a la experiencia de dominio del
personal de la compañía en los temas abordados. Los datos utilizados provienen de dos
tipos de fuentes: **industriales** (series propias de la compañía, obtenidas a
través de su plataforma interna) y **externas** (variables macroeconómicas de
fuentes públicas, y la curva de futuros del propio RFX20 obtenida de la API pública
de Matba Rofex).

El desarrollo se organizó como un pipeline de datos modular, siguiendo un principio
de diseño explícito: cada etapa del pipeline debe poder modificarse sin afectar a
las etapas subsiguientes, comunicándose exclusivamente a través de archivos Parquet
persistidos —nunca acoplando la lógica interna de una etapa con la implementación de
otra—. Concretamente, el pipeline se organiza en cuatro grandes etapas secuenciales,
seguidas de una etapa de modelado propiamente dicha:

1. **Ingesta:** consolidación de la composición histórica del índice, de las series
   OHLCV (apertura, máximo, mínimo, cierre, volumen) de sus componentes, y de la
   curva de futuros del RFX20 (sección 4.2).
2. **Procesamiento:** limpieza de datos, ajuste por eventos corporativos, cálculo de
   retornos y reconstrucción del índice a partir de sus componentes (sección 4.2.3).
3. **Ingeniería de features:** cálculo de indicadores técnicos, volatilidad
   realizada y features macroeconómicos derivados (sección 4.3).
4. **Particionamiento:** consolidación del dataset final de modelado y su división
   temporal en entrenamiento, validación y prueba (sección 4.4).
5. **Modelado y evaluación:** entrenamiento y evaluación de las tres familias de
   modelos descriptas en el capítulo 3, bajo protocolos de validación específicos
   para cada una (sección 4.5).

Cada etapa quedó registrada, a medida que se desarrolló, en un documento de decisión
metodológica independiente (más de veinticinco a la fecha de este trabajo), que
constituye la fuente primaria de trazabilidad de este capítulo y del capítulo 5. Todo
el desarrollo está versionado con control de código fuente, lo que permite
reconstruir con precisión el estado del pipeline en cualquier punto del proyecto.

### 4.2. Selección y descripción de los datos

#### 4.2.1. Horizonte temporal y frecuencia

El conjunto de datos abarca desde el 3 de abril de 2018 hasta el 25 de agosto de
2026, con frecuencia diaria (una observación por jornada hábil bursátil), totalizando
2.041 jornadas. Este horizonte fue determinado por la disponibilidad efectiva de
series históricas confiables de OHLCV para los componentes del índice, y se extendió
sobre la marcha del proyecto mediante un backfill de datos genuinamente nuevos
—nunca antes incorporados al proyecto— obtenido a través de un servicio de datos en
tiempo real de Matba Rofex, con el propósito específico de habilitar un conjunto de
prueba out-of-sample real en lugar de un recorte del historial existente (se
retoma en detalle en la sección 4.4). El horizonte de predicción, siguiendo el foco
principal declarado en el Plan de Trabajo Final (capítulo 1), es de corto plazo: 1, 3
y 5 días hábiles hacia adelante. Se evaluó adicionalmente, como exploración acotada,
la extensión a horizontes de 10 y 21 días hábiles, descartada del alcance final del
proyecto por no aportar mejoras (se retoma en la sección 5.2).

#### 4.2.2. Variable objetivo

Siguiendo lo definido en el Plan de Trabajo Final y fundamentado en la sección 3.1.5,
la variable objetivo de este trabajo es el **retorno logarítmico** del índice a
horizonte $h$ días hábiles:

$$R_{t+h} = \ln\left(\frac{P_{t+h}}{P_t}\right) \qquad (4.1)$$

donde $P_t$ es el valor de cierre del RFX20 en la jornada $t$. El uso de retornos
logarítmicos en lugar del precio nominal del índice aborda directamente el problema
de no estacionariedad descripto en la sección 3.1.3 —la serie de precios del RFX20
no es estacionaria (creció varios órdenes de magnitud entre 2018 y 2026 por efecto
combinado de inflación, devaluación y revalorización real), mientras que su serie de
retornos logarítmicos sí lo es—, y es la transformación estándar en la literatura de
pronóstico financiero para estabilizar la varianza y mejorar la convergencia de los
modelos de Machine Learning y Deep Learning del capítulo 3.

#### 4.2.3. Fuentes y variables

La Tabla 4.1 resume las variables macroeconómicas incorporadas al dataset, todas
ellas de fuentes públicas o semi-públicas y frecuencia diaria salvo el índice de
precios al consumidor (mensual).

**Tabla 4.1.** Variables macroeconómicas incorporadas al dataset de modelado.

| Variable | Frecuencia | Rango disponible | Fuente / notas |
|---|---|---|---|
| Índice Merval | Diaria | 2018-01-02 → 2026-07-01 | Índice bursátil de referencia en ARS |
| IPC (variación mensual) | Mensual | 2018-01-31 → 2026-05-31 | INDEC |
| Riesgo país | Diaria | 2018-01-02 → 2026-07-01 | — |
| Tasa de plazo fijo (TNA) | Diaria | 2018-01-02 → 2026-06-30 | — |
| Dólar oficial (compra/venta) | Diaria | 2018-01-02 → 2026-07-01 | Banco Nación |
| Dólar bancos privados | Diaria | 2018-01-02 → 2026-07-01 | Promedio bancos privados |
| Dólar informal ("blue") | Diaria | 2018-01-02 → 2026-07-01 | — |
| Dólar MEP | Diaria | 2018-10-29 → 2026-07-01 | — |
| Dólar CCL (contado con liqui) | Diaria | 2018-01-02 → 2026-07-01 | — |
| BADLAR (tasa bancos privados) | Diaria | 2018-01-02 → 2026-08-21 | — |
| TAMAR (ex-LELIQ) | Diaria | 2024-10-01 → 2026-08-21 | Arranca ~10 meses después de discontinuarse LELIQ (dic-2023): gap real de la serie, no un error de datos |

A estas variables se suma la curva de futuros del propio RFX20, obtenida de la API
pública de Matba Rofex (Circular Nro. 889, ver sección 2.2.3), con datos disponibles
desde el 2 de enero de 2020 —una fecha de inicio posterior al resto del dataset, lo
que introduce un tramo estructural de valores faltantes que se aborda explícitamente
en la sección 4.3.3—. Sobre esta curva se derivan, en la etapa de ingeniería de
features (sección 4.3.2), una tasa implícita y un term spread, en reemplazo de la
volatilidad implícita prevista originalmente en el Plan de Trabajo Final —el RFX20
no cuenta con un mercado de opciones con volumen operable del cual derivar una
volatilidad implícita en sentido estricto, una limitación real del mercado
subyacente y no una decisión de conveniencia técnica—.

Finalmente, se incorporan eventos corporativos (splits, dividendos en efectivo y en
acciones, cambios de composición del índice) registrados de forma declarativa en un
archivo de configuración editable, separado del código, que permite actualizar los
criterios de ajuste sin modificar la lógica del pipeline (sección 4.2.3 siguiente).

#### 4.2.4. Calidad de datos: verificación y correcciones identificadas

Un principio de diseño transversal a todo el proyecto es que los **datos crudos no
se modifican**: cualquier corrección identificada se implementa exclusivamente en la
capa de procesamiento, de forma declarativa y documentada, preservando la
posibilidad de reproducir el dato original en cualquier momento. Bajo este
principio, se identificaron y corrigieron tres problemas de calidad de datos
relevantes para la interpretación de los resultados de este trabajo:

**Splits no ajustados en la plataforma de datos.** Mediante un procedimiento de
detección empírica (variaciones diarias de cierre a apertura superiores al 30%,
validadas manualmente contra fuentes externas), se identificaron cinco splits de
componentes del índice —notablemente, en dos oportunidades para el mismo ticker
(COME)— que la plataforma de datos de Primary S.A. no había ajustado
retroactivamente, a diferencia de lo que la propia metodología oficial del índice
asume implícitamente al no requerir un ajuste de divisor ante un split (sección
2.2.3): la metodología oficial da por sentado que el precio observado ya refleja el
split, supuesto que en la práctica no se cumplía para estos cinco casos. Se
implementó un esquema de ajuste retroactivo (*backward*) parametrizado desde
configuración, aplicado únicamente a los splits ocurridos mientras el ticker
integraba el índice.

**Cambio de base de octubre de 2023.** Como se describió en la sección 2.2.3, Matba
Rofex fijó un nuevo divisor del índice a partir del 9 de octubre de 2023 (Circular
Nro. 889), reduciendo la cotización nominal del índice en un factor de diez. Al
reconstruir el índice como sumatoria de precio por cantidad de cada componente y
contrastarlo contra el valor spot oficial, se detectó una desviación exacta del 90%
durante siete jornadas hábiles alrededor de esa fecha, explicada por una diferencia
entre la fecha en que los datos de composición ya reflejaban la nueva base y la
fecha de vigencia efectiva de la circular. Se corrigió acotando el ajuste al rango de
fechas afectado.

**Composición corrupta de septiembre de 2019.** Durante la etapa de exploración
previa al desarrollo de modelos se identificaron dos outliers extremos y simétricos
en el retorno logarítmico del índice (+62,6% y -64,1% en la misma semana) sin ningún
evento macroeconómico que los explicara. La investigación —contraste entre el precio
embebido en los archivos de composición histórica y el OHLCV canónico de los veinte
componentes de esa fecha, y confirmación contra el servicio histórico de Matba
Rofex— permitió aislar el problema a un error del archivo de composición histórica
para el período 23 al 27 de septiembre de 2019, con los veinte componentes
simultáneamente afectados y ratios de desviación completamente dispares entre sí
(desde 0,2 hasta 46 veces el valor correcto) — un patrón incompatible con un
movimiento de mercado real, y confirmado como error de la fuente contra el propio
servicio histórico del administrador del índice. Se corrigió de la misma forma
declarativa que los dos casos anteriores.

Las tres correcciones se aplican antes de cualquiera de las etapas descriptas en las
secciones 4.3 a 4.5, de modo que todos los resultados reportados en el capítulo 5 de
este trabajo ya las incorporan.

### 4.3. Ingeniería de features

#### 4.3.1. Indicadores técnicos y volatilidad realizada

Sobre la serie de precios se calcularon los indicadores técnicos previstos en el
Plan de Trabajo Final: medias móviles simples (10, 20 y 50 ruedas), RSI (14 ruedas),
MACD y Bandas de Bollinger (20 ruedas, 2 desvíos estándar), junto con volatilidad
realizada (desvío estándar móvil del retorno logarítmico, mismas ventanas 10/20/50
que las medias móviles, para no introducir un tercer conjunto de parámetros sin
justificación adicional). Una decisión metodológica relevante fue calcular estos
indicadores **en dos niveles**: sobre cada uno de los componentes individuales del
índice, como preveía originalmente el Plan de Trabajo Final, y también sobre la
propia serie del índice RFX20. Esta segunda aplicación no constituye información
externa a la composición del índice —el RFX20 reconstruido es, por definición, una
combinación lineal de sus componentes (sección 2.2.2)—, sino una lectura agregada de
esa misma información a nivel índice en lugar de nivel componente, motivada por dos
razones: el momentum propio de un índice suele ser, en la literatura de pronóstico
financiero, la clase de feature individual con mayor poder predictivo, y esta
elección habilita comparar un modelo "solo técnico del índice" contra un modelo que
además desagrega por componente, para cuantificar el aporte relativo de esa
desagregación. En esta misma etapa se construyó también la variable objetivo del
índice (retornos logarítmicos forward a 1, 3 y 5 días, sección 4.2.2), que no existía
previamente en el dataset procesado.

#### 4.3.2. Features macroeconómicos derivados

A partir de las series macroeconómicas consolidadas (sección 4.2.3) se derivaron
spreads cambiarios entre las distintas modalidades de tipo de cambio (oficial,
informal, MEP, CCL), calculados de forma consistente sobre el precio de venta. Dado
que estas series tienen frecuencias heterogéneas —diarias con gaps ocasionales, o
mensuales, en el caso del IPC—, la alineación contra el calendario diario del índice
se realizó mediante un *join* de tipo *as-of* con estrategia hacia atrás (es decir,
asignando a cada fecha el último valor conocido de cada serie). Esta alineación
requirió una corrección metodológica no trivial: una primera implementación que
combinaba las fuentes mediante uniones completas introducía valores nulos espurios
en fechas donde solo una fuente había publicado dato ese día —encubriendo el último
valor realmente conocido en lugar de dejar que la estrategia *as-of* lo recuperara
correctamente—, un tipo de error silencioso (no produce fallas, sino datos
plausibles pero incorrectos) particularmente relevante de señalar para cualquier
combinación futura de fuentes de frecuencia heterogénea.

La variación mensual del IPC se incorporó respetando su **lag de publicación real**
—la fecha en la que el dato efectivamente se conoce, no la fecha a la que se
refiere—, con precisión exacta para el período diciembre de 2023 a mayo de 2026 (a
partir del calendario de difusión oficial de INDEC) y una aproximación documentada
para el período 2018 a noviembre de 2023, donde no se contó con ese calendario
exacto. Omitir este ajuste habría introducido una forma sutil de fuga de información
hacia el pasado: sin él, el modelo tendría acceso, en una fecha determinada, a una
cifra de inflación que en la realidad todavía no había sido publicada.

Finalmente, sobre la curva de futuros del RFX20 (sección 4.2.3) se derivaron dos
features en reemplazo de la volatilidad implícita prevista originalmente: la **tasa
implícita** del contrato de vencimiento más próximo (*front-month*, determinado
directamente de los datos disponibles cada día, sin mantener un calendario de
vencimientos separado) y el **term spread** entre esa tasa y la del siguiente
contrato disponible el mismo día. **Corrección (4-nov-2026, Punto 10 del
feedback de los directores):** la lectura original de estos dos features como
"expectativas de devaluación e inflación" se reformula — ambos reflejan, en
primer término, **condiciones de financiamiento** (la tasa implícita surge del
arbitraje spot-futuro, análoga a un costo de *carry*) y la forma de la curva de
futuros del índice, no una medición directa de expectativas macroeconómicas.
Leerlos como proxy de devaluación/inflación requeriría asumir adicionalmente
que esas condiciones de financiamiento están dominadas por el diferencial de
tasas entre pesos y dólares (paridad de tasas de interés no cubierta) — un
supuesto razonable en el contexto argentino, pero que no se verifica de forma
independiente en este trabajo, y que por lo tanto no se afirma como hecho
dado. Ambos features son nulos antes de la
primera fecha con datos de futuros disponibles en la fuente (2 de enero de 2020) —el
tratamiento de este y otros gaps estructurales se desarrolla en la sección 4.3.3.

#### 4.3.3. Tratamiento de datos faltantes

Un principio metodológico adoptado explícitamente en este trabajo es que **nunca se
imputa un valor para un dato que genuinamente no existe** —ni cero, ni la media o
mediana de la serie, ni un relleno hacia adelante sobre un tramo extenso—, a
diferencia de la práctica, habitual en otros contextos de Machine Learning, de
completar cualquier faltante para mantener una matriz de features uniforme entre
modelos. La razón es directa: un valor inventado (por ejemplo, una tasa implícita de
0% o la mediana histórica) quedaría mezclado entre observaciones reales de magnitud
muy distinta, y un modelo —en particular uno basado en distancias, como SVM (sección
3.3.2)— lo trataría como una observación genuina en lugar de como la ausencia de
información que efectivamente es.

Este principio se traduce en un tratamiento diferenciado según la capacidad nativa
de cada familia de modelo para manejar valores nulos, verificada empíricamente antes
de decidir el protocolo (Tabla 4.2).

**Tabla 4.2.** Tratamiento de columnas con gaps estructurales reales (tasa implícita
y term spread de futuros, TAMAR, spreads del dólar MEP) por familia de modelo.

| Familia de modelo | Maneja nulos nativamente | Tratamiento adoptado |
|---|---|---|
| Random Forest, XGBoost, LightGBM (sección 3.3) | Sí | Reciben las columnas con sus nulos reales, sin imputar |
| SVM (sección 3.3.2) | No | Se excluyen esas columnas específicamente de su feature set |
| LSTM, GRU, CNN-LSTM, Transformer encoder (sección 3.4) | No | Mismo criterio que SVM: exclusión, no imputación |
| ARIMA/SARIMA, GARCH (sección 3.2) | — | No aplica: son modelos univariados sobre la propia serie del índice |

Adicionalmente, se incorporó una columna binaria de disponibilidad (1 si las
columnas de futuros tienen dato ese día, 0 si no) a los modelos de árbol, que no
introduce ningún valor fabricado —es información genuina sobre el patrón de
faltantes, potencialmente relevante en sí misma— y permite, a través del análisis de
importancia de variables (sección 3.3, y capítulo 5), verificar si la disponibilidad
de dato es en sí misma una señal relevante para el modelo.

#### 4.3.4. Exploración de diferenciación fraccional

Como exploración acotada y no bloqueante, se evaluó si una diferenciación
fraccional de ventana fija (*Fixed-Width Window Fracdiff*, López de Prado, 2018)
aplicada al log-precio del índice permite alcanzar estacionariedad (sección 3.1.3)
conservando más memoria de la serie original que la diferenciación completa
($d=1$, equivalente al log-retorno utilizado como variable objetivo, sección 4.2.2).
Sobre una grilla de valores de $d$ entre 0 y 1, el valor mínimo que logra
estacionariedad según el test ADF (sección 3.1.5, $p=0{,}0165$) es $d=0{,}35$, con
una correlación de 0,56 respecto de la serie original de log-precio, frente a 0,03
de la diferenciación completa —una diferencia sustancial (aproximadamente 16 veces
mayor), aunque la correlación absoluta resultante es moderada y no concluyente por sí
sola—.

Este resultado no se productivizó como feature de ningún modelo de este trabajo: se
había previsto retomarlo si el desarrollo de los modelos ARIMA/SARIMA (sección
4.5.1) lo requería como una alternativa al log-retorno estándar, lo cual no llegó a
materializarse, dado que ese modelo no encontró estructura explotable ni siquiera
sobre la transformación estándar (sección 5.1). El hallazgo (el valor de $d$ mínimo
y la ganancia de memoria respecto de la diferenciación completa) se documenta en
este trabajo como un aporte metodológico exploratorio en sí mismo, más que como un
insumo de un modelo concreto.

### 4.4. Particionamiento temporal y protocolo de validación

#### 4.4.1. De un split estático 70/15/15 a un diseño ajustado al régimen de mercado

El Plan de Trabajo Final preveía un particionamiento temporal estático 70%
entrenamiento / 15% validación / 15% prueba. Al aplicarlo sobre el historial
disponible en ese momento del proyecto, el corte entre entrenamiento y validación
caía apenas cinco días antes de las elecciones presidenciales de noviembre de 2023
—un evento macroeconómico ya identificado como relevante para la serie (sección
4.2.4)—, de modo que el conjunto de entrenamiento nunca llegaría a ver, durante la
selección de modelos, el régimen de mercado posterior a ese evento (la devaluación
de diciembre de 2023 y la dinámica 2024-2026 en su totalidad). Dado que ese régimen
representa una porción sustancial y cualitativamente distinta de la historia
reciente del índice, se optó por no sostener el split 70/15/15 tal como estaba
definido y rediseñar el particionamiento con dos decisiones combinadas.

#### 4.4.2. Conjunto de prueba: datos genuinamente nuevos, no un recorte del historial

En lugar de reservar como conjunto de prueba un tramo final del historial ya
disponible, se incorporaron datos nunca antes utilizados en el proyecto: mediante un
servicio de datos en tiempo real de Matba Rofex, se extendió el spot del índice
desde el 20 de abril hasta el 25 de agosto de 2026 (86 jornadas hábiles). Este tramo
se define como conjunto de **prueba 100% out-of-sample real**: a diferencia de
cualquier recorte de un historial ya conocido al momento de diseñar el pipeline, se
trata de observaciones que no existían en el proyecto cuando se tomaron las
decisiones de diseño de los capítulos 3 y 4, lo que fortalece sustancialmente la
validez de cualquier evaluación final sobre este conjunto. La fecha de corte de este
conjunto de prueba se fijó como una constante explícita del proyecto, que no se
recalcula automáticamente si en el futuro se incorporan más datos históricos al
pipeline.

#### 4.4.3. Entrenamiento y validación: split cronológico 85/15

Sobre el resto del historial disponible (3 de abril de 2018 al 17 de abril de 2026)
se aplicó un split cronológico simple 85% entrenamiento / 15% validación, con el
corte el 28 de enero de 2025 —de modo que el conjunto de entrenamiento incluye, esta
vez sí, la totalidad del régimen post-electoral 2023-2025 que el split 70/15/15
original hubiera dejado fuera—. El conjunto de validación (desde el 29 de enero de
2025 hasta el 17 de abril de 2026, 294 jornadas) es el que se utiliza, a lo largo de
todo el capítulo 5, para comparar de forma homogénea el desempeño de las nueve
familias de modelos entre sí.

Se deja constancia de que este particionamiento constituye una herramienta de
**selección y evaluación honesta** del modelo, no una exclusión permanente de esos
datos: el modelo final que eventualmente se seleccione (Fase 5, sección 5.4) deberá
reentrenarse sobre el dataset completo antes de cualquier uso en producción,
siguiendo la práctica estándar de utilizar train+validation combinados —o
únicamente train, según corresponda— solo para la etapa de selección, y el historial
completo disponible para el modelo que efectivamente se despliegue.

#### 4.4.4. Consolidación del dataset de modelado

El dataset final (`features_long.parquet`) consolida la serie del índice —indicadores
técnicos, volatilidad realizada y variable objetivo (sección 4.3.1)— junto con los
features macroeconómicos derivados (sección 4.3.2), sobre el calendario común de
2.041 jornadas descripto en la sección 4.2.1. Se optó deliberadamente por no pivotar
los precios de los 27 (luego 28) componentes individuales a un formato ancho dentro
de este dataset —lo que hubiera implicado comprometerse de antemano a un esquema de
varios cientos de columnas sin un consumidor concreto que lo requiriera—; los
componentes permanecen disponibles en formato largo por separado, y cada modelo
recurre a ellos únicamente si su diseño lo requiere.

#### 4.4.5. Correspondencia entre familia de modelo y estrategia de validación

Como se anticipó en la sección 3.5, las tres familias de modelos comparadas en este
trabajo no comparten una única estrategia de validación, sino que cada una utiliza
la que resulta metodológicamente apropiada dada su naturaleza (Tabla 4.3) —una
decisión de diseño que se retoma en detalle, familia por familia, en la sección 4.5—.

**Tabla 4.3.** Estrategia de validación por familia de modelo.

| Familia | Estrategia | Rol del conjunto de validación |
|---|---|---|
| Estadística (ARIMA/SARIMA, GARCH) | Walk-forward (sección 3.5.3): orden fijado una única vez por AIC sobre train, coeficientes reestimados en cada paso | Serie completa de pronósticos "en producción simulada", evaluada directamente |
| Machine Learning (SVM, RF, XGBoost, LightGBM) | Validación cruzada expansiva sobre train (sección 3.5.2) para elegir hiperparámetros | No participa de la búsqueda; una única evaluación del modelo ya elegido |
| Deep Learning (LSTM, GRU, CNN-LSTM, Transformer encoder) | *Early stopping* sobre una porción reservada del final de train (sección 4.5.3) para elegir el *lookback* y detener el entrenamiento | No participa de ninguna decisión de diseño; una única evaluación del modelo ya entrenado |

En los tres casos, el conjunto de prueba (sección 4.4.2) no se utiliza en ninguna
etapa de desarrollo de este trabajo —queda reservado para la evaluación final del
modelo que se seleccione en la Fase 5 (sección 5.4)—, y el conjunto de validación
cumple, en los tres casos, el mismo rol de comparación limpia y homogénea entre las
nueve familias de modelos, aun cuando el camino metodológico para llegar a esa
comparación difiera entre ellas.

### 4.5. Modelos desarrollados

Esta sección describe el diseño y el protocolo de entrenamiento de cada familia de
modelo introducida teóricamente en el capítulo 3. Los resultados obtenidos con cada
uno se presentan y discuten en el capítulo 5; esta sección se limita a las
decisiones de diseño adoptadas **antes** de observar esos resultados, de forma
consistente con el principio de no ajustar retroactivamente el protocolo en función
de lo obtenido (ver, en particular, la sección 5.2 respecto de XGBoost).

#### 4.5.1. Modelos estadísticos: ARIMA/SARIMA y GARCH

**ARIMA/SARIMA.** Se separaron explícitamente dos pasos de costo computacional muy
distinto: la **selección de orden**, mediante una búsqueda en grilla por AIC
(sección 3.2.3) realizada una única vez sobre la totalidad del conjunto de
entrenamiento —72 candidatos no estacionales, con $(p,q) \in [0,5]$ y $d \in
\{0,1\}$, más una grilla estacional de 216 candidatos adicionales con periodicidad
semanal ($m=5$, sección 3.1.2) y $(P,Q) \in \{(0,1),(1,0),(1,1)\}$, $D=0$—, y el
**walk-forward de evaluación** (sección 3.5.3), que reestima únicamente los
coeficientes del orden ya fijado en cada paso, sobre una ventana expansiva que
recorre el conjunto de validación. Se evaluó explícitamente la alternativa de volver
a ejecutar la búsqueda de orden en cada paso del walk-forward; dado el costo
estimado (varias horas, frente a minutos con el orden fijo) y que la corrida es
única y no se repite periódicamente en este trabajo, se priorizó en cambio un refit
diario —en lugar de semanal o mensual— de los coeficientes, precisamente porque con
el orden ya fijo ese refit resulta prácticamente gratuito en términos de cómputo. El
conjunto de entrenamiento completo se utiliza únicamente como historia inicial (*warm-up*)
del walk-forward; la evaluación se genera exclusivamente sobre el conjunto de
validación, nunca sobre el propio conjunto de entrenamiento.

**GARCH.** Dado que el diagnóstico de ARIMA (sección 5.1) motiva evaluar la varianza
condicional de forma independiente de su media, se ajustó GARCH con **media fija en
cero** (sección 3.2.4) directamente sobre el retorno logarítmico, sin combinarlo con
un modelo ARIMA de la media. Antes de comprometerse a un walk-forward completo, se
realizó una comparación experimental económica —una búsqueda en grilla por AIC de
$(p,q) \in [1,3] \times [1,3]$, 9 candidatos— entre innovaciones con distribución
Normal y t-Student (sección 3.2.4), sobre la cual avanza únicamente la distribución
ganadora al walk-forward completo. La evaluación se realiza contra el retorno al
cuadrado como proxy de varianza realizada (sección 3.2.4, ante la ausencia de datos
intradiarios de mayor frecuencia), con RMSE y QLIKE (ecuación 3.5) como métricas, y
el mismo esquema de walk-forward diario que ARIMA/SARIMA, con orden y distribución
fijados una única vez.

#### 4.5.2. Modelos de Machine Learning: SVM, Random Forest, XGBoost y LightGBM

A diferencia de los modelos estadísticos de la sección 4.5.1 —univariados, que
consumen únicamente la propia serie del índice—, los cuatro modelos de esta sección
son multivariados y consumen el dataset completo consolidado en la sección 4.4.4. Se
definió un protocolo único, compartido por los cuatro modelos, con el objetivo
explícito de que los resultados fueran robustos, replicables y fáciles de explicar
—un requisito declarado para esta etapa del proyecto—:

- **Un modelo independiente por horizonte y por algoritmo** (doce modelos en total),
  en lugar de un único modelo multi-output, priorizando la interpretabilidad
  individual de cada modelo sobre la parsimonia de tener un modelo único.
- Los indicadores de nivel de precio (medias móviles, Bandas de Bollinger) se
  **re-expresan como razón relativa al cierre del mismo día** antes de entrenar
  (por ejemplo, $ma_{10,\text{rel}} = ma_{10}/\text{close} - 1$), en lugar de
  alimentarse en su escala nominal cruda —que, al haber crecido varios órdenes de
  magnitud entre 2018 y 2026 (sección 4.2.2), introduciría una tendencia no
  estacionaria ajena a la señal real que estos indicadores buscan capturar,
  particularmente grave para SVM por su sensibilidad a la escala (sección 3.3.2)—.
- El tratamiento de valores faltantes sigue el principio y la asignación por modelo
  descriptos en la sección 4.3.3 (Tabla 4.2).
- Los hiperparámetros de cada modelo se seleccionan mediante `RandomizedSearchCV`
  (búsqueda aleatoria acotada, con semilla fija para replicabilidad exacta) sobre la
  validación cruzada expansiva de la sección 3.5.2, dentro del conjunto de
  entrenamiento únicamente.
- La importancia de variables se calcula, para los cuatro modelos por igual, mediante
  *permutation importance* sobre el conjunto de validación con semilla fija —el único
  método de importancia aplicable de forma idéntica a los cuatro estimadores, lo que
  permite comparar qué variables pesan más en cada familia bajo el mismo criterio,
  incluso para SVM, que no expone una medida de importancia nativa.

#### 4.5.3. Modelos de Deep Learning: LSTM, GRU, CNN-LSTM y Transformer encoder

Las cuatro arquitecturas de esta sección comparten un protocolo común, deliberadamente
distinto en varios aspectos del de la sección 4.5.2:

- **Feature set inicial deliberadamente acotado:** retorno logarítmico y volatilidad
  realizada en las tres ventanas ya utilizadas en el resto del proyecto (10, 20 y 50
  ruedas) —sin macro ni indicadores técnicos—, con el objetivo de aislar si la
  capacidad de modelar dependencia secuencial explícita (sección 3.4.2) aporta algo
  por sí sola frente a la señal más simple posible, antes de asumir el costo de
  complejidad adicional (más parámetros, mayor riesgo de sobreajuste) de sumar
  features macroeconómicos. Se evaluó, como paso posterior explícito de este mismo
  desarrollo, qué ocurre al reintroducir el feature set completo de la sección 4.5.2
  (24 predictores) en estas arquitecturas —resultado que se discute en la sección
  5.3, dado que constituye en sí mismo un hallazgo relevante—.
- **Windowing** (sección 3.4.8): ventanas deslizantes de *lookback* días construidas
  sobre la serie completa; la fecha de la última fila de cada ventana determina a
  qué partición (entrenamiento, validación o prueba) pertenece esa ventana en su
  totalidad.
- **Lookback como hiperparámetro elegido empíricamente**, mediante una grilla
  acotada $\{10, 20, 30\}$ —anclada a las ventanas de medias móviles y volatilidad ya
  utilizadas en el resto del proyecto—, seleccionado por la pérdida de un conjunto de
  *early stopping* (nunca por el conjunto de validación, sección 4.4.5).
- **Escalado** (`StandardScaler`) ajustado únicamente sobre la porción de
  entrenamiento efectivamente usada para entrenar, aplicado sin reajustar al resto
  de las particiones.
- **Conjunto de *early stopping*:** el 15% cronológicamente más reciente del
  conjunto de entrenamiento se reserva para decidir cuándo detener el entrenamiento y
  para seleccionar el lookback —nunca el conjunto de validación—, preservando el
  mismo principio de comparación limpia entre familias de modelos que rige el resto
  de este capítulo (sección 4.4.5).
- Un modelo por horizonte, con **un único entrenamiento con *early stopping*** por
  modelo —no un refit diario tipo walk-forward, que resultaría computacionalmente
  injustificado para una red neuronal en este contexto—.
- **Optimizador Adam** (sección 3.4.7) en los cuatro casos.

Las cuatro arquitecturas difieren entre sí únicamente en su estructura interna,
manteniendo el resto del protocolo idéntico para asegurar comparabilidad: **LSTM**
(sección 3.4.3) de una capa, sin atención ni bidireccionalidad; **GRU** (sección
3.4.4), bajo el mismo protocolo exacto, para aislar el efecto de la elección de
celda recurrente; el híbrido **CNN-LSTM** (sección 3.4.5), con una capa
convolucional unidimensional seguida de una LSTM; y el **Transformer encoder**
(sección 3.4.6) —proyección lineal de los features de entrada, encoding
posicional sinusoidal, una capa `TransformerEncoderLayer` de atención
multi-cabeza y una cabeza lineal de salida—, una arquitectura basada en
atención deliberadamente acotada frente a un Temporal Fusion Transformer (TFT)
completo, ya que los componentes adicionales del TFT (redes de selección de
variables, *gating*, encoder de covariables estáticas) están diseñados para
escenarios con múltiples series y entidades que no aplican al presente trabajo:
una única serie, sin covariables estáticas, sobre un conjunto de entrenamiento
de tamaño moderado (sección 4.2.1). **Nota de nomenclatura (corregida
4-nov-2026, Punto 10 del feedback de los directores):** esta arquitectura se
llamaba "TFT-lite" en versiones anteriores de este trabajo — nombre que se
reemplaza por **Transformer encoder** en toda la redacción, porque se omiten
varios componentes centrales del TFT y mantener su nombre en el título sugería
una reproducción del modelo original de Lim et al. (2019/2021) que no es tal.
Los identificadores de código (`tft_lite.py`, `tft_lite_runner.py`, clase
`TFTLiteRegressor`, archivos de resultados `tft_lite_val_predictions_*`) se
mantienen sin cambios, por trazabilidad con los experimentos ya ejecutados y
documentados bajo ese nombre.

---

*(Con esta sub-entrega se completa el Capítulo 4.)*

## 5. Análisis de resultados

*(Capítulo en construcción por sub-entregas. Todos los resultados numéricos de este
capítulo se calcularon directamente sobre los archivos de predicciones persistidos
por cada modelo, ya con las tres correcciones de datos de la sección 4.2.4
incorporadas — no se transcriben de un único resultado parcial que pudiera haber
quedado desactualizado por una corrección posterior. Las figuras estáticas
referenciadas (`docs/figures/`) fueron generadas con el mismo criterio.)*

### 5.1. Modelos estadísticos: ARIMA/SARIMA y GARCH

#### 5.1.1. ARIMA/SARIMA

La búsqueda en grilla por AIC (sección 4.5.1, 288 candidatos) convergió a un
resultado llamativo por su simplicidad: el orden ganador es **$(0,0,0)$, sin
componente estacional** —ninguno de los candidatos con estructura autorregresiva, de
media móvil o estacional superó en AIC a la ausencia total de esa estructura—. Con
ese orden, y sin término de tendencia, el modelo queda reducido a un único parámetro
estimado: la varianza del error ($\sigma^2 = 0{,}0045$, equivalente a un desvío
estándar diario de aproximadamente 6,7%). En consecuencia, el pronóstico puntual del
modelo es matemáticamente cero en cualquier horizonte —no una aproximación cercana a
cero, sino exactamente cero—, por lo que sus métricas de error coinciden, bit a bit,
con las de un pronóstico naive que siempre predice retorno cero (Tabla 5.1).

**Tabla 5.1.** ARIMA/SARIMA vs. naive (predecir retorno 0), conjunto de validación.

| Horizonte | RMSE ARIMA | RMSE naive | Variación vs. naive |
|---|---:|---:|---:|
| 1 | 0,029536 | 0,029553 | -0,1% |
| 3 | 0,029531 | 0,029531 | 0,0% |
| 5 | 0,029479 | 0,029479 | 0,0% |

El diagnóstico estadístico del modelo ajustado sobre el conjunto de entrenamiento
aporta información relevante más allá del resultado puntual. El test de **Ljung-Box**
sobre el primer retardo no rechaza la ausencia de autocorrelación en los residuos
—coherente con que no había estructura lineal para capturar—, pero el test de
**Jarque-Bera** rechaza con fuerza la normalidad: la serie presenta una asimetría
negativa extrema (coeficiente de asimetría $\approx -24$, es decir, los movimientos
bruscos a la baja son sustancialmente más extremos que las subas equivalentes) y una
curtosis muy por encima de 3 (el valor de referencia de la distribución normal),
indicando outliers extremos concentrados en unas pocas jornadas más que un patrón
difuso en toda la serie. Más relevante aún para lo que sigue: un test de
**heterocedasticidad** rechaza con fuerza el supuesto de varianza constante que ARIMA
asume —la varianza del error cambia en el tiempo, alternando períodos de calma y de
turbulencia—, algo que un único parámetro $\sigma^2$ fijo no puede representar.

Esta última observación es la motivación metodológica concreta, y no una elección
arbitraria, para evaluar GARCH a continuación: el resultado de ARIMA es negativo
respecto de la **media condicional** del retorno (hacia dónde se mueve el índice),
pero el propio diagnóstico de este modelo señala que la **varianza condicional**
(cuánto se mueve) sí tiene estructura explotable —una pregunta distinta, que ARIMA no
está diseñado para responder.

#### 5.1.2. GARCH

La comparación experimental por AIC entre innovaciones Normal y t-Student (sección
4.5.1) resultó contundente a favor de la segunda (diferencia de AIC de
aproximadamente 2.229 puntos). El orden ganador fue **GARCH(1,1)** con distribución
t-Student, con los siguientes coeficientes estimados sobre el conjunto de
entrenamiento: $\omega = 1{,}2254$, $\alpha = 0{,}1235$, $\beta = 0{,}7343$,
$\nu = 4{,}57$ (en unidades escaladas, ver nota metodológica de la sección 4.5.1).
La persistencia ($\alpha + \beta = 0{,}858$) implica una vida media de los shocks de
volatilidad de aproximadamente 4,5 ruedas —menos de una semana hábil—, moderada
frente a los valores de 0,95-0,99 habituales en índices de mercados desarrollados: el
RFX20 "olvida" un shock de volatilidad relativamente rápido. El grado de libertad
bajo de la distribución t ($\nu = 4{,}57$) confirma colas pesadas **en las
innovaciones estandarizadas** del modelo. Esto es distinto de la curtosis
incondicional (marginal) del retorno crudo reportada en 5.1.1: un proceso GARCH
genera, por el solo efecto del agrupamiento de volatilidad, una curtosis
incondicional mayor que la de sus propias innovaciones — ambas cantidades son
consistentes entre sí, pero no son el mismo número y no deben citarse de forma
intercambiable.

El target que se pronostica (`log_return_fwd_h`) es el retorno **acumulado** de t a
t+h (sección 4.2.2), no el retorno puntual del día t+h — por lo tanto el objetivo
correcto en h=3 y h=5 es la varianza del retorno acumulado a h días, no la varianza
de un único día futuro. Bajo la especificación de media cero, $\mathrm{Var}(\text{suma
de } h \text{ retornos}) = \text{suma de las } h \text{ varianzas de un paso}$, así
que el pronóstico se construye como $\sigma^2_{h} = \sum_{i=1}^{h}\sigma^2_{t+i}$, y
se evalúa contra `log_return_fwd_h`$^2$ (el cuadrado del retorno acumulado) — target
y pronóstico miden la misma cantidad en los tres horizontes.

**Tabla 5.2.** GARCH vs. naive (varianza incondicional de entrenamiento) y vs. un
benchmark adicional de volatilidad móvil (EWMA, $\lambda=0{,}94$), RMSE y QLIKE
sobre el proxy de varianza realizada (retorno acumulado al cuadrado), conjunto de
validación.

| Horizonte | RMSE GARCH | RMSE naive | RMSE EWMA | QLIKE GARCH | QLIKE naive | QLIKE EWMA |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 0,0027724 | 0,0027481 | 0,0027784 | -5,988 | -6,043 | -6,011 |
| 3 | 0,0077450 | 0,0076656 | 0,0077714 | -4,794 | -4,895 | -4,844 |
| 5 | 0,0134430 | 0,0132549 | 0,0135442 | -4,224 | -4,356 | -4,288 |

A diferencia de lo que el diagnóstico de ARIMA hacía anticipar, **ninguno de los
tres métodos** —naive de varianza constante, GARCH, o EWMA— mejora sobre los otros
dos en ambas métricas: GARCH queda consistentemente peor que el naive (RMSE y
QLIKE, los tres horizontes), y EWMA queda peor todavía que GARCH. Esto es, en sí
mismo, informativo: EWMA no incorpora reversión a la media en su pronóstico
(equivalente a un proceso IGARCH, persistencia=1), mientras que GARCH sí la tiene
($\alpha+\beta=0{,}858<1$) — en un mercado donde la volatilidad revierte
relativamente rápido (vida media ~4,5 ruedas), es esperable que un modelo sin
reversión quede peor que uno con reversión moderada, que es exactamente lo
observado. Se verificó además que la comparación no depende de una definición
particularmente desfavorable del naive: un naive alternativo calculado sobre la
varianza de entrenamiento winsorizada (recorte del 1%/99%) resulta igual o
levemente peor que el naive crudo, y GARCH sigue sin superar a ninguno de los dos.
Esta robustez del naive frente a la winsorización **no se debe a que la varianza
muestral de train minimice "por construcción" el error fuera de muestra** — esa
garantía solo existe dentro de la propia muestra de entrenamiento, que es donde el
estimador de mínimos cuadrados se define; que también resulte competitivo sobre
`val` es una observación empírica de este dataset, no una propiedad matemática
general. La comparación es, de todos modos, robusta a esta variante metodológica y
no un artefacto de cómo se construye la referencia.

#### 5.1.3. Lectura conjunta

El resultado de esta sección deja una asimetría metodológicamente interesante: el
diagnóstico de heterocedasticidad de ARIMA (sección 5.1.1) predecía correctamente que
la varianza condicional del RFX20 tiene estructura temporal —hay, en efecto,
agrupamiento de volatilidad (sección 3.2.4)—, pero esa estructura no resulta, en la
práctica, más fácil de explotar con un RMSE mejor que el de un naive de varianza
constante. En otras palabras: que una serie *no* sea homocedástica no garantiza que
un modelo GARCH mejore sobre un naive en la métrica de error cuadrático, aun cuando
la especificación capture correctamente la dinámica de la volatilidad (persistencia
moderada, colas pesadas). Ninguno de los dos modelos estadísticos clásicos de este
trabajo —ni para la media, ni para la varianza condicional— supera a su naive
respectivo en los tres horizontes evaluados. Las figuras `docs/figures/predicted_vs_real_h{1,3,5}.png`
y `docs/figures/garch_volatility.png` ilustran, respectivamente, las predicciones de
ambos modelos frente al valor real.

### 5.2. Modelos de Machine Learning clásico

Los cuatro modelos de esta sección (protocolo compartido, sección 4.5.2) se evalúan
en la Tabla 5.3.

**Tabla 5.3.** SVM, Random Forest, XGBoost y LightGBM vs. naive, conjunto de
validación.

| Modelo | Horizonte | RMSE | RMSE naive | Variación vs. naive |
|---|---|---:|---:|---:|
| SVM | 1 | 0,029695 | 0,029553 | +0,5% |
| SVM | 3 | 0,029849 | 0,029531 | +1,1% |
| SVM | 5 | 0,029789 | 0,029479 | +1,0% |
| Random Forest | 1 | 0,029539 | 0,029553 | -0,0% |
| Random Forest | 3 | 0,029694 | 0,029531 | +0,6% |
| Random Forest | 5 | 0,029587 | 0,029479 | +0,4% |
| XGBoost | 1 | 0,030607 | 0,029553 | +3,6% |
| XGBoost | 3 | 0,029792 | 0,029531 | +0,9% |
| XGBoost | 5 | 0,029655 | 0,029479 | +0,6% |
| LightGBM | 1 | 0,030767 | 0,029553 | +4,1% |
| LightGBM | 3 | 0,029550 | 0,029531 | +0,1% |
| LightGBM | 5 | 0,029688 | 0,029479 | +0,7% |

SVM y Random Forest quedan prácticamente empatados con el naive en los tres
horizontes —diferencias de tercer o cuarto decimal, dentro del margen esperable de
ruido—. XGBoost y LightGBM muestran una desviación algo mayor en el horizonte más
corto (+3,6% y +4,1% respectivamente en $h=1$), que se reduce a un empate virtual en
$h=3$ y $h=5$. Este patrón —peor desempeño relativo cuanto más corto (y más ruidoso)
el horizonte— es consistente con **sobreajuste leve** más que con una limitación
estructural de estos dos algoritmos: ambos son los de mayor capacidad entre los
cuatro (sección 3.3.4-3.3.6), y sobre un conjunto de entrenamiento de tamaño moderado
(~1.600 filas) tienen más margen para ajustar ruido específico del horizonte más
cercano que para encontrar señal genuina. Es importante notar que este resultado se
reporta tal como salió de la búsqueda de hiperparámetros por validación cruzada
(sección 4.5.2), sin ajuste manual posterior para mejorar el número —un criterio
deliberado para mantener el protocolo replicable y no sesgado por intervención
post-hoc.

En los cuatro modelos, el análisis de **importancia de variables por permutación**
(sección 4.5.2) no muestra ningún feature que se repita de forma estable como el más
relevante entre los tres horizontes, y las magnitudes son pequeñas en términos
absolutos —un patrón más compatible con ruido de la búsqueda de hiperparámetros que
con una señal genuina y estable, y consistente con el resultado de error de la Tabla
5.3: si existiera una variable con poder predictivo real y estable, sería esperable
que su importancia relativa también lo fuera.

#### 5.2.1. Extensión a horizontes largos (evaluada y descartada)

Como exploración acotada, con una condición de salida acordada de antemano (sección
4.2.1), se evaluó si horizontes de 10 y 21 días hábiles mostraban señal que los
horizontes de 1, 3 y 5 días no mostraron. El patrón direccional resultó idéntico: ARIMA
sin estructura, SVM/Random Forest/LightGBM sin mejora sobre el naive, y XGBoost
repitiendo el patrón de sobreajuste más pronunciado ya visto en $h=1$ (con una brecha
que se achica hacia $h=21$). GARCH, en esta exploración puntual, sí mostró una
reducción relevante del RMSE de varianza frente al naive —pero esta exploración se
ejecutó **antes** de la corrección de composición de septiembre de 2019 descripta en
la sección 4.2.4, y a diferencia de los resultados de las Tablas 5.1 a 5.3 (todos
recalculados sobre el dataset ya corregido), **no fue re-ejecutada después de esa
corrección**. Dado que esa corrección afecta directamente al cálculo de la varianza
incondicional que actúa como naive de GARCH (sección 5.1.2), la magnitud reportada en
esta exploración para GARCH debe considerarse no confirmada, y no se cita en este
trabajo como resultado numérico vigente. La decisión de no adoptar horizontes largos
como parte del alcance del proyecto no depende de esa cifra puntual: el patrón de
ausencia de señal direccional —la dimensión que sí fue verificada sobre datos
corregidos— es consistente con o sin ella, y es la que motivó, con la condición de
salida ya acordada, descartar esta línea.

### 5.3. Modelos de Deep Learning

#### 5.3.1. LSTM y GRU sobre el feature set acotado

**Tabla 5.4.** LSTM y GRU (feature set acotado: retorno logarítmico + volatilidad
realizada) vs. naive, conjunto de validación.

| Modelo | Horizonte | RMSE | RMSE naive | Variación vs. naive |
|---|---|---:|---:|---:|
| LSTM | 1 | 0,029803 | 0,029553 | +0,8% |
| LSTM | 3 | 0,029709 | 0,029531 | +0,6% |
| LSTM | 5 | 0,029903 | 0,029479 | +1,4% |
| GRU | 1 | 0,031437 | 0,029553 | +6,4% |
| GRU | 3 | 0,030199 | 0,029531 | +2,3% |
| GRU | 5 | 0,030202 | 0,029479 | +2,5% |

Ambas arquitecturas quedan en el mismo orden de magnitud que el naive. GRU se aparta
algo más que LSTM, en particular en $h=1$, pero dentro de un rango comparable al ya
observado para los modelos de Machine Learning clásico (Tabla 5.3): no hay evidencia
de que la elección de celda recurrente (sección 3.4.3-3.4.4) cambie la conclusión de
fondo sobre la ausencia de señal direccional explotable.

#### 5.3.2. Exploración del feature set completo: degradación, no solo empate

**Tabla 5.5.** LSTM y GRU con el feature set completo de la sección 5.2 (24
predictores) vs. naive, conjunto de validación.

| Modelo | Horizonte | RMSE | RMSE naive | Variación vs. naive |
|---|---|---:|---:|---:|
| LSTM (completo) | 1 | 0,068980 | 0,029553 | +133% |
| LSTM (completo) | 3 | 0,054863 | 0,029531 | +86% |
| LSTM (completo) | 5 | 0,060326 | 0,029479 | +105% |
| GRU (completo) | 1 | 0,075682 | 0,029553 | +156% |
| GRU (completo) | 3 | 0,071396 | 0,029531 | +142% |
| GRU (completo) | 5 | 0,063343 | 0,029479 | +115% |

A diferencia del empate virtual de la Tabla 5.4, sumar el feature set completo
**degrada sustancialmente** el resultado en ambas arquitecturas —RMSE entre 2 y 2,5
veces el del naive, no un empate—. La inspección de las predicciones descartó un
problema de escala o de fuga de información: el modelo converge a una predicción con
sesgo sistemático que no generaliza al conjunto de validación, el patrón característico
de sobreajuste, aquí agravado por la dimensión temporal de las ventanas (24 features
× hasta 30 pasos de lookback, sobre ~1.600 filas de entrenamiento) — el mismo
fenómeno observado con XGBoost en la Tabla 5.3, pero más pronunciado. El feature set
acotado de la Tabla 5.4 queda confirmado como la opción correcta para esta cantidad
de datos disponible.

#### 5.3.3. Arquitecturas híbridas y basadas en atención: CNN-LSTM y Transformer encoder

**Tabla 5.6.** CNN-LSTM y Transformer encoder (feature set acotado) vs. naive, conjunto de
validación.

| Modelo | Horizonte | RMSE | RMSE naive | Variación vs. naive |
|---|---|---:|---:|---:|
| CNN-LSTM | 1 | 0,030018 | 0,029553 | +1,6% |
| CNN-LSTM | 3 | 0,030362 | 0,029531 | +2,8% |
| CNN-LSTM | 5 | 0,029818 | 0,029479 | +1,2% |
| Transformer encoder | 1 | 0,030330 | 0,029553 | +2,6% |
| Transformer encoder | 3 | 0,030529 | 0,029531 | +3,4% |
| Transformer encoder | 5 | 0,030524 | 0,029479 | +3,5% |

Ambas arquitecturas completan el mismo patrón que LSTM y GRU: ninguna mejora sobre
el naive con el feature set acotado. Ni la incorporación de un componente
convolucional (CNN-LSTM) ni la de un mecanismo de atención (Transformer encoder, sección 3.4.6)
encuentran estructura adicional que las arquitecturas puramente recurrentes no hayan
encontrado ya.

### 5.4. Síntesis comparativa

Consolidando las secciones 5.1 a 5.3: de los diez modelos evaluados sobre los
horizontes de 1, 3 y 5 días hábiles —nueve orientados a la dirección del retorno
(ARIMA/SARIMA, SVM, Random Forest, XGBoost, LightGBM, LSTM, GRU, CNN-LSTM, Transformer encoder)
y uno a su volatilidad condicional (GARCH)—, **no se encontró una mejora consistente
frente al pronóstico de retorno cero, bajo los datos, modelos, horizontes y
protocolo evaluados** (Tabla 5.7). Las desviaciones puntuales más notorias (XGBoost
y LightGBM en $h=1$, Tabla 5.3) se explican por sobreajuste leve y se reducen a un
empate virtual en los horizontes más largos. Esta formulación es deliberadamente
acotada: un RMSE en línea con el naive no permite, por sí solo, afirmar que el
índice no es predecible ni que no existe señal en los datos — solo que, bajo este
protocolo específico, ningún modelo la explotó mejor que predecir cero.

**Tabla 5.7.** Síntesis: variación de RMSE vs. naive por modelo y horizonte (celda
en blanco donde no aplica).

| Modelo | Paradigma | $h=1$ | $h=3$ | $h=5$ |
|---|---|---:|---:|---:|
| ARIMA/SARIMA | Estadístico | -0,1% | 0,0% | 0,0% |
| GARCH (volatilidad) | Estadístico | +0,9% | +1,2% | +1,3% |
| SVM | ML clásico | +0,5% | +1,1% | +1,0% |
| Random Forest | ML clásico | -0,0% | +0,6% | +0,4% |
| XGBoost | ML clásico | +3,6% | +0,9% | +0,6% |
| LightGBM | ML clásico | +4,1% | +0,1% | +0,7% |
| LSTM | Deep Learning | +0,8% | +0,6% | +1,4% |
| GRU | Deep Learning | +6,4% | +2,3% | +2,5% |
| CNN-LSTM | Deep Learning | +1,6% | +2,8% | +1,2% |
| Transformer encoder | Deep Learning | +2,6% | +3,4% | +3,5% |

*(Ver `docs/figures/rmse_comparison.png` para la versión gráfica de esta tabla, con
un panel por horizonte.)*

#### 5.4.1. Dimensión de dirección: hit-rate

La Tabla 5.7 mide magnitud del error (RMSE/MAE), no si el signo pronosticado
coincide con el real — un RMSE en línea con el naive no demuestra, por sí solo,
ausencia de capacidad para anticipar la dirección del retorno. Para evaluar esa
dimensión específicamente, se calculó el hit-rate (porcentaje de días en los que
`sign(predicción) = sign(retorno real)`) de los nueve modelos orientados a
dirección, con un test binomial de dos colas contra la hipótesis nula de 50% de
aciertos, sobre las mismas predicciones de validación de la Tabla 5.7 (n=294 por
celda).

**Tabla 5.8.** Hit-rate y significancia (test binomial vs. 50%), conjunto de
validación.

| Modelo | $h=1$ | $h=3$ | $h=5$ |
|---|---:|---:|---:|
| ARIMA/SARIMA | 49,3% (p=0,86) | 50,7% (p=0,86) | 52,4% (p=0,45) |
| SVM | 49,0% (p=0,77) | 47,3% (p=0,38) | 47,3% (p=0,38) |
| Random Forest | 54,1% (p=0,18) | 50,0% (p=1,00) | 52,0% (p=0,52) |
| XGBoost | 53,4% (p=0,27) | 55,4% (p=0,07) | 46,3% (p=0,22) |
| LightGBM | 54,4% (p=0,14) | 51,7% (p=0,60) | 51,4% (p=0,68) |
| LSTM | 52,7% (p=0,38) | 51,4% (p=0,68) | 48,0% (p=0,52) |
| GRU | 52,0% (p=0,52) | 46,3% (p=0,22) | 47,3% (p=0,38) |
| CNN-LSTM | 49,3% (p=0,86) | 46,6% (p=0,27) | 46,6% (p=0,27) |
| Transformer encoder | 48,6% (p=0,68) | 47,6% (p=0,45) | 51,4% (p=0,68) |

**Ninguna de las 27 combinaciones (modelo × horizonte) alcanza significancia
convencional** ($p<0{,}05$); el valor más bajo (XGBoost, $h=3$, $p=0{,}07$) tampoco la
alcanza, y con 27 pruebas sin corrección por comparaciones múltiples sería
esperable encontrar 1-2 falsos positivos por azar si la verdadera tasa de acierto
fuera 50% — no se encontró ninguno. Esto aporta evidencia propia de la dimensión
de dirección, independiente del RMSE: bajo el protocolo evaluado, tampoco se
detectó capacidad de anticipar el signo del retorno por encima del azar.

Esta conclusión tampoco se extiende, sin más, a la volatilidad: la ausencia de
autocorrelación lineal en el retorno (ARIMA, sección 5.1) y la ausencia de hit-rate
direccional no implican nada sobre la varianza condicional, que es una pregunta
distinta y se trata por separado (GARCH, Tabla 5.7, fila "volatilidad") — ni sobre
dependencias no lineales que un test de hit-rate agregado, igual que el RMSE, no
está diseñado para detectar de forma aislada por sí solo.

#### 5.4.2. Lectura del resultado

Dos observaciones contextualizan este resultado, con el cuidado de no extender su
alcance más allá de lo efectivamente evaluado:

1. **La consistencia entre métodos independientes es evidencia de que el patrón no
   depende de un algoritmo puntual, pero no aísla la causa.** Diez métodos con
   supuestos distintos —lineales y no lineales, con y sin memoria explícita de
   secuencia, basados en árboles, en distancias, en convoluciones o en atención—
   convergen en el mismo resultado, lo que hace poco probable que se trate de una
   mala elección de arquitectura o de hiperparámetros en un modelo específico. Sin
   embargo, los diez comparten el mismo dataset, el mismo pipeline de construcción
   de features y el mismo protocolo de validación — esa coincidencia **no permite
   descartar una limitación común** (del dato disponible o de alguna decisión de
   procesamiento compartida) como explicación alternativa a "no hay señal
   explotable en el fenómeno".
2. **Cuando se sube la capacidad del modelo sin subir la señal disponible, el
   resultado es una degradación, no un empate** (XGBoost/LightGBM en $h=1$, Tabla
   5.3; LSTM/GRU con el feature set completo, Tabla 5.5) — un patrón adicional,
   consistente con sobreajuste sobre un conjunto de entrenamiento acotado (~1.600
   filas), más que con la mera ausencia de señal.

Si se busca encuadrar el resultado en la literatura de eficiencia de mercados, el
encuadre correcto es el de la **forma semifuerte** de la hipótesis, no la débil: la
forma débil se restringe a la información contenida en precios y volúmenes
pasados, mientras que varios de los modelos evaluados incorporan variables
macroeconómicas públicas (riesgo país, tasas, tipos de cambio, futuros) — un
conjunto de información estrictamente más amplio. Incluso bajo ese encuadre más
exigente, esto se presenta como una lectura posible del resultado, no como una
conclusión que el diseño experimental de este trabajo esté en condiciones de
demostrar.

**Implicancia para la Fase 5 del proyecto (comparación y selección de modelo
final):** **corregido (4-nov-2026, Punto 10 del feedback de los directores)** — la
formulación original de este párrafo afirmaba que "un ensamble no puede generar
señal que no está presente en sus modelos de entrada", como una imposibilidad
teórica. Eso no es correcto: una combinación de modelos puede reducir el error
de pronóstico incluso si ninguno de sus integrantes supera individualmente al
naive, siempre que sus errores no estén perfectamente correlacionados entre sí
—es el mismo principio de reducción de varianza que sostiene a Random Forest o
a cualquier método de ensamble (sección 3.3.4)—. La decisión correcta de
encuadrar es de **alcance y costo**, no de imposibilidad: desarrollar y validar
un ensamble (correlación de errores entre los nueve modelos de dirección, peso
óptimo o *stacking*, validación sin fuga adicional) es un trabajo no trivial
que, dado que ninguno de los modelos de entrada individualmente supera al naive
de forma significativa (sección 5.4.1), tiene un retorno esperado incierto
frente a su costo. Esto sigue cambiando el alcance esperable de la Fase 5
respecto de lo previsto originalmente en el Plan de Trabajo Final (que preveía
desarrollo de ensamble y selección de un modelo ganador), pero la redefinición
debe documentarse como una decisión de priorización, no como una conclusión
que se desprenda necesariamente de los resultados de Bloque 2. Es, al momento
de escribir este capítulo, un punto todavía abierto a discutir con la
dirección.

---

*(Con esta sub-entrega se completa el Capítulo 5. Queda pendiente el Capítulo 6,
Conclusión y trabajos futuros —sujeto a la redacción final pospuesta, ver nota de
estado al inicio del documento— y el Capítulo 7, Bibliografía.)*
