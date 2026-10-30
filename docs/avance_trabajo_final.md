# Avance de Trabajo Final — Predicción del Índice ROFEX 20

**Maestría en Explotación de Datos y Gestión del Conocimiento — Universidad Austral**

**Alumno:** Matías Humberto Tibaldo
**Directora:** Fernanda Mendez — **Co-Director:** Rodrigo Del Rosso
**Documento de avance — Versión 3**
**Fecha:** 21 de septiembre de 2026

---

## 0. Propósito de este documento

El Plan de Trabajo Final (versión preliminar 3, marzo de 2026) estableció en su
sección 9 la metodología general del proyecto y en su sección 10 un plan de trabajo
tentativo de seis fases. Este documento reporta el avance metodológico concreto
logrado en las dos primeras fases de ejecución —consolidación y procesamiento de
datos (Fase 1), e ingeniería de features (Fase 2)— y actualiza el plan de trabajo en
función de los tiempos reales observados.

A diferencia de un informe de estado puntual, este documento está pensado como
**construcción continua**: se irá extendiendo en cada hito de avance (modelos
estadísticos y de machine learning, deep learning, selección de modelo final), de modo
que al llegar a la etapa de redacción de la tesis buena parte del contenido
metodológico ya esté consolidado y validado con la dirección. La correspondencia entre
cada hito y este documento está detallada en el plan de acción adjunto
(`docs/plan_de_accion.md`).

Respecto de la Versión 1 (agosto de 2026), la Versión 2 agregó la sección 3
(Metodología de ingeniería de features) y actualizó las secciones 1, 4 (luego 5), 5
(luego 6) y 6 (luego 7) en función del cierre de la Fase 2.

Respecto de la Versión 2 (septiembre de 2026), esta versión agrega la sección 4
completa (Metodología y resultados de modelado, Fases 3-4 — Bloque 2: modelos
estadísticos, Machine Learning clásico y Deep Learning) y actualiza en consecuencia
las secciones 5 (Implicancias metodológicas, antes 4), 6 (Actualización del plan de
trabajo, antes 5), 7 (Puntos de validación pendientes, antes 6) y 8 (Próxima
actualización, antes 7).

## 1. Estado de avance respecto del Plan de Trabajo Final

Las Fases 1 a 4 del plan original se encuentran completas: Fase 1 ("Datos"), Fase 2
("Ingeniería de Features"), y Fases 3 y 4 (modelos estadísticos/Machine Learning
clásico y Deep Learning, ejecutadas en paralelo según lo descripto en la sección 6).
La Fase 1 (8 semanas previstas) demandó aproximadamente trece; la Fase 2 (4 semanas
previstas) se completó en poco más de dos semanas (20 de agosto al 5 de septiembre de
2026); las Fases 3 y 4 (6 semanas previstas cada una, en paralelo) se completaron en
apenas diez días (5 al 15 de septiembre de 2026) — un ritmo sustancialmente más rápido
que el estimado en el plan original, que se explica principalmente por reutilizar un
protocolo de validación común entre familias de modelos (ver sección 4) en lugar de
diseñar cada modelo de forma aislada.

Concretamente, además de lo ya reportado en la Versión 2 de este documento (Fase 1:
consolidación de composición histórica, ingesta OHLCV, ajuste por eventos
corporativos, módulo de procesamiento; Fase 2: indicadores técnicos, features macro,
diferenciación fraccional, particionamiento temporal), se completó en Fases 3-4:

- Una corrección adicional de datos de origen (composición del índice en septiembre
  de 2019), detectada durante la preparación de esta etapa e incorporada al dataset
  de modelado antes de las corridas reportadas en este documento (sección 4.1).
- **Track A** (modelos estadísticos y de Machine Learning clásico): ARIMA/SARIMA y
  GARCH sobre la serie del índice; SVM, Random Forest, XGBoost y LightGBM sobre el
  dataset multivariado completo (sección 4.2).
- **Track B** (Deep Learning): LSTM, GRU, un híbrido convolucional-recurrente
  (CNN-LSTM) y una evaluación preliminar de arquitectura basada en atención
  ("TFT-lite") (sección 4.3).
- Una exploración acotada de horizontes de predicción más largos (10 y 21 días
  hábiles), evaluada y descartada del alcance del proyecto (sección 4.4).
- Herramientas de visualización —estáticas para la tesis e interactivas en el
  dashboard del proyecto— que cubren la totalidad de modelos y horizontes corridos
  hasta el momento (sección 4.5).
- Una síntesis consolidada de los diez métodos evaluados en Bloque 2, que constituye
  el hallazgo metodológico central del proyecto hasta la fecha (sección 4.6).

Sigue la Fase 5 ("Comparación y selección"): framework de evaluación multicriterio,
evaluación de ensamble y selección del modelo final, todavía sin código desarrollado
(ver sección 6).

## 2. Metodología de datos: decisiones adoptadas en la consolidación y el procesamiento

*(Sección sin cambios respecto de la Versión 1 — se conserva por completitud del
documento.)*

### 2.1 Tratamiento de discontinuidades en las series de precios

Las series OHLCV provistas por la plataforma de Primary S.A. no presentan un
comportamiento uniforme respecto del ajuste retroactivo por eventos corporativos. Para
identificar discontinuidades no explicadas por la dinámica normal del mercado se
diseñó un procedimiento de detección empírica: se calculó la variación porcentual
entre el precio de cierre de una jornada y el de apertura de la jornada hábil
siguiente, y se marcaron como anómalas aquellas variaciones superiores al 30%.

Cada alerta fue clasificada manualmente contrastando fuentes internas
(`base.dividendos2.csv`) y externas (investing.com, digrin.com) en tres categorías
disjuntas: splits no ajustados por la API, movimientos de mercado genuinos asociados
a eventos macroeconómicos y políticos (la corrida post-PASO de agosto de 2019 y la
suba post-elecciones de noviembre de 2023), y un caso de dato erróneo puntual (BBAR,
11/06/2019).

Para los splits confirmados se implementó un esquema de **ajuste backward**: los
precios posteriores al evento permanecen sin modificación y los anteriores se
multiplican por el inverso del ratio de split, con acumulación multiplicativa cuando
existe más de un evento en la historia de un mismo ticker. Se definieron dos criterios
de aplicación —ajustar únicamente los splits ocurridos mientras el ticker integraba
el índice (Enfoque A), o ajustar la totalidad de la serie histórica del ticker
(Enfoque B)— adoptándose el Enfoque A como criterio por defecto, dado que el objeto de
estudio es el índice y no las acciones individuales fuera de su período de membresía.

Un hallazgo relevante para la interpretación posterior de resultados es que las series
de la API ya incorporan el ajuste por dividendos en efectivo: se verificó, mediante
inspección de la serie de TGSU2 en fechas de pago de dividendos conocidas, la ausencia
de discontinuidades abruptas asociadas a esos eventos.

### 2.2 Dividendos en acciones como splits encubiertos

En consulta directa con el equipo que administra el índice en Primary S.A. se
estableció que los eventos de dividendo en acciones (tipo "AC") con monto igual o
superior a 1 deben tratarse metodológicamente como splits —multiplicando la cantidad
de acciones del componente en el índice— y no mediante la fórmula estándar de ajuste
por dividendo, que licuaría incorrectamente su participación. Se identificó un caso
histórico (BYMA, julio de 2022) en el que este criterio no había sido aplicado
correctamente en su momento, y un segundo caso (BYMA, mayo de 2024, split 5:1) que no
se encuentra registrado en la fuente de dividendos habitual y requirió tratamiento
manual. Queda pendiente la solicitud a Primary S.A. de un registro adicional de
dividendos en especie que podría contener eventos similares no capturados hasta el momento.

### 2.3 Corrección del cambio de base del índice (octubre de 2023)

La Guía Metodológica del Índice ROFEX 20 documenta un único cambio de base en la
historia del índice, vigente desde el 9 de octubre de 2023, mediante el cual el
divisor se redefinió y las cantidades teóricas de los componentes se dividieron por
diez. Al reconstruir el índice como sumatoria de precio por cantidad para cada
componente y contrastarlo contra el valor spot oficial, se detectó una desviación
exacta del 90% durante siete jornadas hábiles (29/09/2023 al 06/10/2023), explicada
por una diferencia entre la fecha en que los datos de composición ya reflejaban la
nueva base y la fecha de vigencia efectiva de la circular correspondiente.

Se optó por corregir este desajuste en la capa de procesamiento —preservando la
inmutabilidad de los datos crudos, principio de diseño del proyecto— acotando la
corrección al rango de fechas afectado. Tras la corrección, de catorce jornadas con
error de reconstrucción superior al 1% quedaron ocho con error residual de hasta
3,25% (concentradas en noviembre de 2022 y mayo de 2024), cuyo análisis puntual
permanece pendiente (ver sección 6).

### 2.4 Tratamiento de la membresía histórica en el índice

La composición del RFX20 cambia cuatrimestralmente según criterios de liquidez. Se
evaluaron dos estrategias para representar este hecho en el dataset: filtrar las
observaciones a los períodos de efectiva membresía, o conservar la serie histórica
completa de cada ticker acompañada de una variable indicadora booleana (`in_index`).
Se adoptó la segunda alternativa, por tres razones que se consideran relevantes para
la etapa de modelado: preserva información sobre la dinámica de entrada y salida del
índice, que puede ser en sí misma predictiva de liquidez y capitalización relativa;
traslada la decisión de filtrar o no a cada modelo individual, en línea con el
principio de modularidad del proyecto; y facilita el análisis exploratorio sobre la
serie completa. Esta decisión deberá declararse explícitamente en cada modelo que
utilice series por ticker, dado que impacta en la interpretación de sus resultados.

### 2.5 Variables macroeconómicas disponibles

Se consolidaron series diarias de tipo de cambio en sus distintas modalidades (oficial,
bancos privados, informal, MEP, contado con liquidación), riesgo país y tasa de plazo
fijo, junto con la variación mensual del índice de precios al consumidor y el índice
Merval como referencia de mercado local. Estas series constituyen la base para las
variables macroeconómicas previstas en la sección de Metodología del plan original
(tipos de cambio, tasas de interés, inflación, riesgo país) y para los features
derivados —spreads cambiarios, term spread— descriptos en la sección 3.

## 3. Metodología de ingeniería de features (Fase 2)

Esta sección desarrolla, con el nivel de detalle metodológico que corresponde a la
tesis, las decisiones tomadas durante la Fase 2, construida en cuatro etapas
sucesivas y validadas contra los datos reales. El detalle técnico de cada una está
registrado como documento de decisión independiente en `docs/decisions/`.

### 3.1 Indicadores técnicos calculados en dos niveles: componentes e índice

El plan original describía los indicadores técnicos como una tarea sobre los 27
componentes del índice. Se decidió calcularlos **también sobre la propia serie del
índice RFX20**, con el argumento de que el RFX20 reconstruido es una combinación
lineal de sus componentes: un indicador calculado sobre el spot del índice no
constituye información externa a la composición, sino una lectura agregada de la
misma serie a nivel índice en lugar de nivel componente. Esta decisión responde a que
el momentum propio del índice suele ser, en la literatura de forecasting financiero,
la clase de feature individual con mayor poder predictivo, y habilita además un
baseline metodológico relevante para la tesis: contrastar un modelo "solo técnico del
índice" contra el modelo completo con features de composición para cuantificar el
aporte de desagregar por componente.

Los indicadores calculados fueron: medias móviles simples (10, 20 y 50 ruedas, tal
como especifica el plan original), RSI (14 ruedas), MACD (parámetros 12/26/9 por
default de la librería) y Bandas de Bollinger (20 ruedas, 2 desvíos estándar), junto
con volatilidad realizada (desvío estándar móvil del retorno logarítmico, mismas
ventanas 10/20/50 que las medias móviles, para no introducir un tercer conjunto de
parámetros sin justificación). Se aprovechó además esta etapa para construir el
target del índice (retornos logarítmicos forward a 1, 3 y 5 días hábiles), que no
existía previamente en el dataset procesado. Ver `docs/decisions/technical_indicators_scope.md`.

### 3.2 Features macroeconómicos derivados

A partir de las series macro consolidadas en Fase 1 (sección 2.5) se derivaron
spreads cambiarios (oficial/informal, oficial/MEP, oficial/CCL y MEP/CCL, calculados
de forma consistente sobre el precio de venta), y se incorporaron las series de tasa
BADLAR y TAMAR —sumadas manualmente por el alumno y validadas sin nulls ni
duplicados, con TAMAR arrancando en octubre de 2024, aproximadamente diez meses
después de la discontinuación de la tasa LELIQ que reemplaza, un gap real de la serie
y no un error de datos.

Un hallazgo metodológico relevante surgió al alinear estas series, de frecuencias
heterogéneas (diaria con gaps, mensual), contra el calendario diario del índice
mediante `join_asof` con estrategia backward: una primera implementación que combinaba
las fuentes con joins completos (`full join`) introducía valores nulos espurios en
fechas donde solo una fuente había publicado dato ese día, "tapando" el último valor
realmente conocido en lugar de dejar que el asof lo recuperara. Se corrigió aplicando
relleno hacia adelante (`forward fill`) dentro de cada fuente antes de la unión,
preservando correctamente los nulos genuinos de series que todavía no habían
comenzado a existir (por ejemplo, MEP antes de octubre de 2018). Este tipo de error
—silencioso, porque no produce fallas sino datos plausibles pero incorrectos— se
documenta explícitamente por su relevancia para la validación de cualquier feature
derivado de fuentes de frecuencia heterogénea en etapas futuras. Ver
`docs/decisions/macro_features_etapa2.md`.

La variación mensual del IPC se incorporó respetando el lag de publicación real: una
tabla exacta de fechas de difusión de INDEC para el período diciembre de 2023 a mayo
de 2026, y una aproximación documentada (cierre de mes más doce días corridos,
ajustada al día hábil siguiente) para el período 2018 a noviembre de 2023, donde no
se contó con el calendario de difusión exacto. Esta distinción de precisión entre
ambos períodos debe declararse en la sección de metodología de la tesis.

### 3.3 Reinterpretación de "volatilidad implícita" como tasa implícita y term spread de futuros

El plan original preveía una variable de volatilidad implícita derivada de futuros
del RFX20, condicionada a obtener acceso a una fuente con histórico de contratos. El
alumno proveyó acceso a la API pública de MatbaRofex (Circular Nro. 889), que expone
precios de cierre diarios por contrato de futuro junto con una tasa de interés
implícita calculada por el propio mercado (`impliedRate`, del tipo F = S × (1+r)^(t/365)).

Se constató que el RFX20 no cuenta con un mercado de opciones con volumen operable,
por lo que no existe un instrumento del cual derivar una volatilidad implícita en
sentido estricto —la volatilidad implícita se obtiene invirtiendo un modelo de
pricing de opciones, no de futuros. En consecuencia, se reinterpretó la variable
prevista en el plan original como dos features derivados de la curva de futuros: la
tasa implícita del contrato de vencimiento más próximo (front-month, determinado
directamente de los datos —el contrato de menor año/mes que efectivamente cotizó ese
día— sin mantener un calendario de vencimientos separado), y el term spread entre esa
tasa y la del siguiente contrato disponible el mismo día, como proxy de expectativas
de devaluación e inflación a distintos plazos. La primera fecha con datos de futuros
disponibles en la fuente es el 2 de enero de 2020; ambos features son nulos para
fechas anteriores. Esta reinterpretación —motivada por una limitación real del
mercado subyacente y no por una decisión de conveniencia técnica— debe declararse
explícitamente en la sección de metodología, dado que se aparta de lo previsto en el
Plan de Trabajo Final. Ver `docs/decisions/futures_implied_rate.md` y
`docs/decisions/macro_features_etapa2.md`.

### 3.4 Exploración de diferenciación fraccional

Se evaluó, como exploración acotada y no bloqueante prevista en el plan de acción, si
una diferenciación fraccional (Fixed-Width Window Fracdiff, López de Prado)
sobre el log-precio del índice permite alcanzar estacionariedad conservando más
memoria de la serie original que la diferenciación completa (d=1, equivalente al
log-return usado como target). Sobre una grilla de d entre 0 y 1, el valor mínimo
que logra estacionariedad (test ADF, p=0.0165) es **d=0.35**, con una correlación de
0.56 respecto de la serie original, frente a 0.03 de la diferenciación completa —una
diferencia sustancial (~16 veces mayor), aunque la correlación absoluta resultante es
moderada y no concluyente por sí sola.

Se decidió no productivizar este resultado como feature en esta etapa: se retomará
si el Track A de la Fase 3 (modelos ARIMA/SARIMA) lo requiere como input alternativo
al log-return estándar, momento en el que existirá un consumidor concreto que
justifique la decisión. Ver `docs/decisions/fractional_differentiation.md`.

**Actualización (septiembre de 2026):** con Track A ya cerrado (sección 4.2), ese
consumidor concreto no llegó a materializarse — el baseline ARIMA/SARIMA no encontró
estructura explotable ni siquiera sobre el log-return estándar (orden ganador (0,0,0),
ver sección 4.2.1), por lo que no había razón para introducir una transformación
adicional. La exploración de diferenciación fraccional queda cerrada, sin
productivizar, con el resultado ya documentado (d=0.35) como aporte metodológico de
la tesis en sí mismo, más que como insumo de un modelo concreto.

### 3.5 Particionamiento temporal y consolidación del dataset de modelado

El plan original preveía un split train/validation/test estático 70/15/15. Al
aplicarlo sobre el historial disponible, el corte de entrenamiento caía cinco días
antes de las elecciones presidenciales de noviembre de 2023 —evento macro ya
identificado como relevante en la sección 2.1—, de modo que el modelo nunca vería en
entrenamiento el régimen post-electoral completo (devaluación de diciembre de 2023 y
la dinámica de mercado 2024-2026 en su totalidad).

La resolución adoptada combina dos decisiones. Primero, se incorporaron datos
genuinamente nuevos —nunca antes presentes en el proyecto— obtenidos vía un servicio
de datos en tiempo real de MatbaRofex provisto por el alumno, que permitieron extender
el spot del índice desde el 17 de abril hasta el 25 de agosto de 2026 (86 jornadas).
Este tramo se define como conjunto de **test 100% out-of-sample real**, en lugar de
un recorte del historial existente. Segundo, sobre el resto del historial (3 de abril
de 2018 a 17 de abril de 2026) se aplicó un split cronológico 85/15 para
entrenamiento y validación, con el corte de entrenamiento el 28 de enero de 2025 —
incluyendo ahora sí todo el régimen post-electoral 2023-2025 en el conjunto de
entrenamiento.

Se deja constancia, para las fases de modelado que siguen, de que este split
constituye una herramienta de selección y evaluación honesta del modelo, y no una
exclusión permanente de esos datos: **el modelo final elegido deberá reentrenarse con
el dataset completo** antes de su uso en producción. La fecha de corte del conjunto
de test se fijó como constante explícita y no se recalculará automáticamente si en el
futuro se incorporan más datos históricos al pipeline. Ver
`docs/decisions/temporal_split_and_consolidation.md` y `docs/decisions/rfx20_ws_backfill.md`.

El dataset final de modelado (`features_long.parquet`) consolida la serie del índice
(indicadores técnicos, volatilidad, target) y los features macroeconómicos sobre un
calendario común de 2041 jornadas, sin pivotar los 27 componentes a formato ancho —
decisión que evita comprometerse de antemano a un esquema de aproximadamente 800
columnas sin un consumidor concreto que lo requiera; los componentes permanecen
disponibles en formato largo aparte, siguiendo el mismo criterio "wide + long
persistidos, cada modelo elige" ya adoptado en la Fase 1.

Como hallazgo colateral del backfill, se identificó que la composición vigente del
índice al 25 de agosto de 2026 incorpora un componente nuevo (ECOG), incorporado
alrededor de mayo de 2026 y todavía no reflejado en la lista de 27 tickers
consolidada en Fase 1. Se amplió la ingesta el mismo día (28 tickers), quedando
disponible en el dataset por componente para cualquier etapa que lo requiera —
ver `docs/decisions/rfx20_ws_backfill.md`. No fue necesario para el dataset final de
Fase 2, que no incluye componentes individuales (`features_long.parquet`, Opción A).

### 3.6 Sobre el uso de infraestructura provista directamente por Primary S.A.

El backfill descripto en 3.5 utilizó un servicio con certificado TLS con cadena
incompleta, provisto directamente por la infraestructura de Primary S.A./MatbaRofex.
Se deshabilitó la verificación TLS de forma explícita y documentada para estas
conexiones puntuales, decisión razonable dado que se trata de un endpoint interno
provisto por el propio alumno y no de una fuente de terceros no confiable, pero que
se registra aquí por tratarse de una decisión de seguridad relevante para la
documentación técnica del proyecto.

## 4. Metodología y resultados de modelado (Fases 3-4, Bloque 2)

Esta sección desarrolla la metodología y los resultados de las Fases 3 (modelos
estadísticos y de Machine Learning clásico) y 4 (Deep Learning) del plan original,
ejecutadas en paralelo bajo la denominación operativa "Bloque 2" (Track A + Track B,
ver `docs/plan_de_accion.md`) entre el 5 y el 15 de septiembre de 2026. Todos los
resultados numéricos reportados en esta sección fueron recalculados por el director
de este documento directamente sobre los archivos de predicciones persistidos
(`results/track_a/`, `results/track_a_ml/`, `results/track_b/`), en lugar de
transcribirse de los documentos de decisión individuales, para asegurar que reflejan
el estado corregido del dataset descripto en 4.1 y no una cifra parcial de un
documento que pudo quedar desactualizado. El detalle metodológico completo de cada
modelo está registrado en un documento de decisión independiente en
`docs/decisions/`, referenciado en cada subsección.

### 4.1 Corrección de datos previa a la etapa de modelado: composición del índice, septiembre de 2019

Durante la exploración de variables objetivo alternativas para la Fase 5 (Bloque 3)
se detectaron dos outliers extremos y simétricos en el `log_return` del índice
(+62,6% el 23/09/2019, seguido de -64,1% el 30/09/2019) sin ningún evento macro
documentado que los explicara. La investigación —comparación entre el índice
reconstruido y el spot oficial, contraste del `close` de la composición histórica
contra el OHLCV canónico de los 20 componentes de esa fecha, y confirmación contra el
servicio histórico de MatbaRofex— identificó un error de origen en el archivo de
composición histórica (`cartera_historica_201909XX.csv`) para el período 23 al 27 de
septiembre de 2019: el `close` embebido en la composición se desvía del OHLCV
canónico en los 20 componentes simultáneamente, con ratios completamente dispares
entre sí (desde 0,2x hasta 46x del valor correcto) y sin coherencia direccional entre
tickers — un patrón incompatible con un movimiento de mercado real, y confirmado como
error de la fuente —no de la ingesta del proyecto— contra el propio API histórico de
MatbaRofex.

Siguiendo el mismo criterio ya establecido para los casos de BBAR (sección 2.1) y el
cambio de base de octubre de 2023 (sección 2.3), la corrección se aplicó en la capa de
`processing/`, de forma declarativa desde `config/data_corrections.yaml`, sin editar
ningún archivo de `data/raw/`. El dataset de features fue reconstruido en su totalidad
con esta corrección incorporada (`features.runner` re-ejecutado) antes de generar
cualquiera de los resultados reportados en las secciones 4.2 a 4.4. Ver
`docs/decisions/sept2019_composicion_corrupta.md` para el detalle completo de la
investigación, incluyendo tres hallazgos menores derivados del mismo análisis
(recomposición de cartera desfasada un día hábil, un tercer split de BYMA no
documentado hasta ahora —ya incorporado a `data_corrections.yaml`— y dos desvíos
menores sin investigar en profundidad, MIRG y un cluster de mayo de 2024), listados
como pendientes en la sección 7.

### 4.2 Track A: modelos estadísticos y de Machine Learning clásico

#### 4.2.1 Modelos estadísticos: ARIMA/SARIMA y GARCH

**ARIMA/SARIMA.** Se separó explícitamente la selección de orden (grid search por AIC,
una sola vez sobre el `log_return` completo de train: 288 candidatos, no
estacionales y estacionales con periodicidad semanal) del walk-forward de evaluación
(reestimación diaria de coeficientes con el orden ya fijo, ventana expansiva sobre el
split de validación, 294/294 refits exitosos). El orden ganador por AIC fue
**(0,0,0), sin componente estacional**: ningún candidato con estructura
autorregresiva, de media móvil o estacional superó a la ausencia total de estructura.
Con ese orden, y sin término de tendencia, el pronóstico puntual del modelo es
matemáticamente cero en cualquier horizonte — el único parámetro estimado es la
varianza del error (`sigma2 = 0.0045`).

El diagnóstico estadístico del modelo ajustado (test de Jarque-Bera, asimetría de
-23,93, curtosis de 821, test de heterocedasticidad) rechaza con fuerza la
normalidad de los residuos y la varianza constante — evidencia que debe declararse
explícitamente en la sección de metodología de la tesis, dado que ARIMA (y varios
modelos posteriores) asumen errores gaussianos. El rechazo del supuesto de varianza
constante es, además, la motivación metodológica concreta para ajustar GARCH a
continuación: son preguntas distintas (media condicional vs. varianza condicional)
sobre la misma serie. Ver `docs/decisions/arima_baseline_track_a.md`.

**GARCH.** Dado que ARIMA no encontró estructura en la media condicional, se ajustó
un GARCH de media cero directamente sobre `log_return`. Una comparación experimental
por AIC entre innovaciones Normales y t-Student (9 candidatos cada una) resultó
contundente a favor de t-Student (AIC 8029,78 vs. 10258,68), consistente con la
curtosis extrema ya observada — la distribución Normal se descartó de las corridas
siguientes. El orden ganador fue **GARCH(1,1)** con distribución t-Student:
`ω=1,2254`, `α=0,1235`, `β=0,7343`, `ν=4,57`. La persistencia (`α+β=0,858`) implica
una vida media de shocks de volatilidad de aproximadamente 4,5 ruedas —moderada
frente a los valores de 0,95-0,99 habituales en índices de mercados desarrollados—,
y el grado de libertad bajo de la t confirma colas muy pesadas. Se evaluó contra el
retorno al cuadrado (proxy estándar de varianza realizada cuando no se dispone de
datos intradiarios), con RMSE y QLIKE (Patton, 2011) como métricas, y un naive de
referencia de varianza constante (varianza incondicional de train). Ver
`docs/decisions/garch_volatility_track_a.md`.

**Resultado (val, walk-forward diario, sobre el dataset ya corregido según 4.1):**

| Modelo | Horizonte | RMSE | RMSE naive | Var. vs. naive |
|---|---|---:|---:|---:|
| ARIMA/SARIMA | 1 | 0,029536 | 0,029553 | -0,1% |
| ARIMA/SARIMA | 3 | 0,029531 | 0,029531 | 0,0% |
| ARIMA/SARIMA | 5 | 0,029479 | 0,029479 | 0,0% |
| GARCH (varianza) | 1 | 0,0027724 | 0,0027481 | +0,9% |
| GARCH (varianza) | 3 | 0,0027799 | 0,0027484 | +1,2% |
| GARCH (varianza) | 5 | 0,0027849 | 0,0027487 | +1,3% |

Ninguno de los dos modelos estadísticos supera a su naive respectivo. Se verificó
adicionalmente que la comparación de GARCH no depende de una definición
particularmente injusta del naive: un naive alternativo con la varianza calculada
sobre train winsorizado (recorte 1%/99%, para reducir la sensibilidad a outliers)
resulta igual o levemente peor que el naive crudo, y GARCH sigue sin superar a
ninguno de los dos — la comparación es robusta a esta variante metodológica.

#### 4.2.2 Machine Learning clásico: SVM, Random Forest, XGBoost, LightGBM

A diferencia de ARIMA/GARCH (univariados, solo la propia serie del índice), estos
cuatro modelos son multivariados: consumen el dataset completo de `features_long.parquet`
(indicadores técnicos, volatilidad realizada, features macro). Dado que se pidió
explícitamente que estos modelos fueran robustos, replicables y fáciles de explicar,
se definió un protocolo único, compartido por los cuatro (`docs/decisions/ml_feature_engineering_track_a.md`):

- Un modelo independiente por horizonte y por algoritmo (12 modelos en total), en
  vez de un único modelo multi-output.
- Los indicadores de nivel de precio (medias móviles, Bandas de Bollinger) se
  re-expresan como razón relativa al cierre del mismo día antes de entrenar, para no
  introducir la tendencia no estacionaria del precio nominal del índice (que pasó de
  ~30.000 a niveles muy superiores por inflación/devaluación a lo largo de 2018-2026)
  como si fuera señal.
- **Nunca se imputan datos faltantes genuinos.** Las columnas con gaps estructurales
  reales (tasa implícita y term spread de futuros, TAMAR, spreads del dólar MEP,
  nulos en aproximadamente 30% de train por ausencia real de la fuente en esos
  períodos) se pasan sin modificar a los modelos que aceptan valores nulos de forma
  nativa (Random Forest, XGBoost, LightGBM), y se excluyen del feature set de SVM
  (que no admite `NaN`) en lugar de completarse con un valor inventado. Se agrega
  además una columna binaria de disponibilidad para los modelos de árbol.
- Selección de hiperparámetros por `RandomizedSearchCV` sobre `TimeSeriesSplit`
  (validación cruzada temporal expansiva) dentro de train, con semilla fija para
  replicabilidad exacta; el split de validación no participa de la búsqueda y se
  reserva para una única evaluación comparable entre las cuatro familias.
- Importancia de variables uniforme por *permutation importance*, calculada sobre
  validación con semilla fija — el único método aplicable por igual a los cuatro
  estimadores, lo que permite comparar qué variables pesan más en cada familia con el
  mismo criterio.

**Resultado (val, sobre el dataset ya corregido según 4.1):**

| Modelo | Horizonte | RMSE | RMSE naive | Var. vs. naive |
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
horizontes. XGBoost y LightGBM muestran una desviación algo mayor en h=1 (+3,6% y
+4,1% de RMSE respectivamente) que se reduce a un empate virtual en h=3 y h=5 — un
patrón compatible con sobreajuste leve sobre un dataset de tamaño moderado (~1.600
filas de entrenamiento), más pronunciado en el horizonte más cercano y ruidoso, antes
que con una degradación estructural del modelo. En ninguno de los cuatro modelos las
importancias por permutación resultan estables entre horizontes: ningún feature se
repite consistentemente como el más relevante, lo que es más compatible con ruido de
la búsqueda de hiperparámetros que con una señal genuina y estable.

### 4.3 Track B: Deep Learning

Track B evalúa si una arquitectura capaz de modelar dependencia secuencial explícita
—que ninguno de los modelos de la sección 4.2 intenta: los de árbol/SVM tratan cada
fila como independiente, ARIMA solo modela autocorrelación lineal— encuentra
estructura que Track A no encontró. El protocolo, compartido por las cuatro
arquitecturas evaluadas, difiere del de Track A ML en varios puntos deliberados:

- **Feature set deliberadamente acotado en el baseline inicial:** `log_return` +
  volatilidad realizada (ventanas 10/20/50) únicamente —sin macro ni indicadores
  técnicos—, para aislar si la arquitectura secuencial por sí sola aporta algo sobre
  la señal más simple posible, antes de pagar el costo de complejidad de sumar más
  variables.
- **Windowing:** ventanas deslizantes de `lookback` días construidas sobre la serie
  completa; el split de la última fila de cada ventana determina a qué partición
  pertenece.
- **Lookback elegido empíricamente** por grid `{10, 20, 30}`, seleccionado por
  pérdida de un split de *early stopping* tallado del 15% más reciente de train —
  nunca por el split de validación, que se reserva para una única evaluación
  comparable con el resto de Bloque 2.
- **Escalado** (`StandardScaler`) ajustado solo sobre la porción de entrenamiento
  efectivamente usada para entrenar, aplicado sin refit a las demás particiones.
- Un modelo por horizonte, entrenamiento único con *early stopping* (no refit diario
  tipo walk-forward, que sería computacionalmente injustificado para una red).

#### 4.3.1 LSTM y GRU sobre el feature set acotado

**Resultado (val):**

| Modelo | Horizonte | RMSE | RMSE naive | Var. vs. naive |
|---|---|---:|---:|---:|
| LSTM | 1 | 0,029803 | 0,029553 | +0,8% |
| LSTM | 3 | 0,029709 | 0,029531 | +0,6% |
| LSTM | 5 | 0,029903 | 0,029479 | +1,4% |
| GRU | 1 | 0,031437 | 0,029553 | +6,4% |
| GRU | 3 | 0,030199 | 0,029531 | +2,3% |
| GRU | 5 | 0,030202 | 0,029479 | +2,5% |

Ambas arquitecturas quedan en el mismo orden de magnitud que el naive, sin una
mejora consistente; GRU se aparta algo más que LSTM en h=1, dentro de un rango
comparable al ya observado en Track A ML. No hay evidencia de que la elección de
celda recurrente cambie la conclusión de fondo. Ver `docs/decisions/lstm_baseline_track_b.md`
y `docs/decisions/track_b_etapa2_gru_full_features.md`.

#### 4.3.2 Exploración del feature set completo: degradación, no solo empate

Se evaluó reintroducir el feature set completo de Track A ML (24 predictores, mismo
tratamiento de gaps estructurales por exclusión) en ambas arquitecturas, para
distinguir si la falta de mejora de 4.3.1 se debía al feature set acotado o era un
límite más estructural.

| Modelo | Horizonte | RMSE | RMSE naive | Var. vs. naive |
|---|---|---:|---:|---:|
| LSTM (feature set completo) | 1 | 0,068980 | 0,029553 | +133% |
| LSTM (feature set completo) | 3 | 0,054863 | 0,029531 | +86% |
| LSTM (feature set completo) | 5 | 0,060326 | 0,029479 | +105% |
| GRU (feature set completo) | 1 | 0,075682 | 0,029553 | +156% |
| GRU (feature set completo) | 3 | 0,071396 | 0,029531 | +142% |
| GRU (feature set completo) | 5 | 0,063343 | 0,029479 | +115% |

A diferencia del empate del feature set acotado, sumar 24 predictores **degrada
sustancialmente** el resultado en ambas arquitecturas (RMSE 2 a 2,5 veces el del
naive). La inspección de las predicciones descartó un problema de escala o de fuga
de información: el modelo converge a una predicción con sesgo sistemático que no
generaliza a validación, el patrón clásico de sobreajuste sobre un dataset de
~1.600 filas con una dimensionalidad de entrada muy superior una vez expandida por
las ventanas temporales — el mismo fenómeno ya observado con XGBoost en Track A, acá
agravado por la dimensión temporal. El feature set acotado queda confirmado como la
opción correcta para Track B con esta cantidad de datos disponible; no se recomienda
retomar esta línea sin agregar regularización explícita (dropout, weight decay) o
reducir drásticamente la dimensionalidad de entrada. Ver
`docs/decisions/track_b_etapa2_gru_full_features.md`.

#### 4.3.3 Arquitecturas híbridas y basadas en atención: CNN-LSTM y "TFT-lite"

Como paso exploratorio final de Track B, se evaluaron un híbrido convolucional-recurrente
(`CNNLSTMRegressor`: una capa `Conv1d` seguida de una LSTM, arquitectura estándar sin
reducción de alcance) y una arquitectura basada en atención, deliberadamente acotada
y denominada **"TFT-lite"** para no sobre-representarla en la tesis: un Temporal
Fusion Transformer completo (Lim et al., 2019) incluye redes de selección de
variables, *gating*, un encoder de covariables estáticas y salidas por cuantiles —
pensado para múltiples series y entidades con covariables estáticas, ninguna de las
cuales aplica a este dataset de una sola serie con ~1.600 filas de entrenamiento. Se
implementó en cambio una proyección lineal + encoding posicional sinusoidal + un
`TransformerEncoderLayer` de PyTorch + cabeza lineal, tomando de TFT únicamente el
mecanismo de atención. Ambas arquitecturas se evaluaron sobre el feature set acotado
(el que no mostró degradación en 4.3.2).

| Modelo | Horizonte | RMSE | RMSE naive | Var. vs. naive |
|---|---|---:|---:|---:|
| CNN-LSTM | 1 | 0,030018 | 0,029553 | +1,6% |
| CNN-LSTM | 3 | 0,030362 | 0,029531 | +2,8% |
| CNN-LSTM | 5 | 0,029818 | 0,029479 | +1,2% |
| TFT-lite | 1 | 0,030330 | 0,029553 | +2,6% |
| TFT-lite | 3 | 0,030529 | 0,029531 | +3,4% |
| TFT-lite | 5 | 0,030524 | 0,029479 | +3,5% |

Ambas arquitecturas completan el mismo patrón que LSTM y GRU: ninguna mejora sobre el
naive con el feature set acotado. Ver `docs/decisions/track_b_etapa3_tft_hibrido.md`.

### 4.4 Extensión a horizontes de predicción más largos (10 y 21 días hábiles) — evaluada y descartada

Antes de cerrar Track A se evaluó, con una condición de salida explícita acordada de
antemano ("si no hay mejoras, se desestima esta línea y se sigue con Deep Learning"),
si horizontes intermedios (10 días ≈ dos semanas, 21 días ≈ un mes de ruedas)
mostraban señal que los horizontes de 1/3/5 días no mostraron. Se construyó un
dataset aparte (`features_long_ext.parquet`, sin fusionar al canónico) para poder
descartar el experimento sin afectar nada ya cerrado, y se corrigieron dos aspectos
del protocolo compartido que se generalizan a cualquier corrida futura, incluidos los
horizontes canónicos: la detección dinámica (en lugar de hardcodeada) de las columnas
de retorno forward a excluir del feature set, que a horizontes largos hubiera
producido fuga de información severa; y un ajuste de purga (`purged_splits`, López de
Prado) sobre `TimeSeriesSplit`, necesario porque a h=10/21 el solapamiento entre el
final de un fold de entrenamiento y el inicio del de validación deja de ser
despreciable.

**Resultado (val, RMSE vs. naive, cualitativo):**

| Horizonte | ARIMA | GARCH | SVM | Random Forest | XGBoost | LightGBM |
|---|---|---|---|---|---|---|
| 10 días | Empatado | Mejor (~-39%) | Peor | ≈Empatado (RMSE), peor MAE | Sustancialmente peor (+31%, sobreajuste) | Peor |
| 21 días | Empatado | Mejor (~-40%) | Peor | Peor | ≈Empatado | Peor |

El patrón de dirección (ARIMA/SVM/RF/XGBoost/LightGBM sin mejora consistente) es
idéntico al de 1/3/5 días, por lo que la lectura de esa dimensión no cambia. **Nota
importante de trazabilidad:** este experimento se ejecutó el 8 de septiembre de 2026,
antes de detectarse y corregirse el problema de datos descripto en la sección 4.1. A
diferencia de los diez métodos de la sección 4.2-4.3 (evaluados a 1/3/5 días), **esta
extensión a horizontes largos no fue re-corrida** después de la corrección. Dado que
el mecanismo identificado en 4.1 afecta directamente al cálculo de la varianza
incondicional que actúa como naive de GARCH, es razonable esperar que la magnitud
reportada aquí para GARCH (~39-40% mejor que el naive) esté sobreestimada por el mismo
motivo ya corregido para el horizonte corto —no debe citarse en la tesis como
resultado numérico vigente sin re-ejecutar el experimento (ver punto 9 de la sección
7)—. La decisión de descartar esta línea de horizontes largos del alcance del
proyecto no depende de esa cifra puntual y se mantiene sin cambios: el patrón de
ausencia de señal direccional es consistente con o sin ese resultado. Ver
`docs/decisions/long_horizons_track_a.md`.

Se decidió no incorporar `features_long_ext.parquet` al dataset canónico ni adoptar
horizontes largos como parte del alcance de predicción del proyecto — el foco
declarado (1 a 5 días hábiles) se mantiene sin cambios respecto del Plan de Trabajo
Final. El código de la exploración, la corrección del bug de fuga y el purge de CV se
conservan como mejoras permanentes del protocolo compartido.

### 4.5 Herramientas de visualización de resultados

En paralelo al cierre de Bloque 2, y con antelación a lo previsto en el cronograma
(estaba planificado como parte de la Fase 5), se construyó una capa de visualización
con cobertura completa de los modelos y horizontes de esta sección:

- `evaluation/results_loader.py` unifica las predicciones de validación de todas las
  familias de modelos —persistidas originalmente con convenciones de nombres
  distintas entre sí— en un único esquema largo, usado tanto por las figuras
  estáticas como por el dashboard interactivo, evitando duplicar en dos lugares la
  lógica de qué archivos existen y cómo se leen.
- `evaluation/figures.py` genera figuras estáticas en `docs/figures/` pensadas para
  incorporarse directamente a la tesis: comparación de RMSE por familia de modelo
  contra el naive (un panel por horizonte), predicho vs. real por horizonte (todos
  los modelos de retorno superpuestos) y una figura específica de volatilidad GARCH.
- Una nueva sección "Modelos" en el dashboard de Streamlit del proyecto (`app.py`)
  ofrece el equivalente interactivo, con pestañas de resumen, predicho vs. real
  (selector de modelo y horizonte) y volatilidad GARCH.
- Ambos formatos comparten una misma paleta de colores por familia (estadístico,
  ML clásico, Deep Learning) para que la identidad de cada serie sea reconocible de
  una figura a otra.

Esta capa es reutilizable para la Fase 5 (Bloque 3): el mismo `results_loader.py`
puede alimentar el framework de evaluación multicriterio cuando se defina su alcance
(ver sección 7, punto 8).

### 4.6 Síntesis de Bloque 2: hallazgo central del proyecto hasta la fecha

Consolidando las secciones 4.2 a 4.4: de los diez métodos evaluados sobre los
horizontes canónicos de 1, 3 y 5 días hábiles —nueve orientados a la dirección del
retorno (ARIMA/SARIMA, SVM, Random Forest, XGBoost, LightGBM, LSTM, GRU, CNN-LSTM,
"TFT-lite") y uno a su volatilidad condicional (GARCH)—, **ninguno mejora de forma
consistente sobre su respectivo naive** en los tres horizontes evaluados. Las
desviaciones puntuales observadas (XGBoost y LightGBM en h=1, del orden de +4%) se
explican por sobreajuste leve y se reducen a un empate virtual en los horizontes más
largos, no por una señal explotable que se pierda en el resto de los modelos. A
diferencia de lo que anticipaba el Plan de Trabajo Final —que un enfoque de Machine
Learning o Deep Learning superaría a los métodos estadísticos clásicos—, el resultado
observado es una convergencia de los tres paradigmas (estadístico, ML clásico, Deep
Learning) hacia el mismo naive, tanto en dirección como en volatilidad.

Este resultado se considera válido y defendible para la tesis, no una falla del
proyecto, por tres razones que deben desarrollarse en la sección de resultados:

1. **La consistencia entre métodos independientes es la forma más fuerte de evidencia
   negativa disponible en Machine Learning aplicado.** Diez métodos con supuestos
   completamente distintos —lineales y no lineales, con y sin memoria explícita de
   secuencia, basados en árboles, en distancias, en convoluciones o en atención—
   convergiendo en la misma conclusión descarta que se trate de una mala elección de
   arquitectura o de hiperparámetros en un modelo puntual.
2. **Cuando se sube la capacidad del modelo sin subir la señal disponible, el
   resultado es una degradación, no un empate** (XGBoost sin *early stopping* en
   Track A, LSTM/GRU con el feature set completo en Track B) — evidencia adicional,
   no solo ausencia de evidencia, de que la señal buscada no está en los datos con
   esta granularidad.
3. **El resultado es consistente con la hipótesis de mercados eficientes en su forma
   débil**: en un índice líder y líquido como el RFX20 no sería sorprendente que su
   dirección diaria no sea explicable con información pública ya rezagada (precios,
   indicadores técnicos, variables macroeconómicas publicadas) — sería más
   sorprendente lo contrario. El proyecto no asume esta hipótesis de antemano, pero
   sus resultados son coherentes con ella.

**Implicancia directa para la Fase 5 (Bloque 3, comparación y selección):** un
ensamble no puede generar señal que no está presente en sus modelos de entrada —
combinar diez modelos que ya empatan con su naive no debería superarlo, ni del lado
de dirección ni del lado de volatilidad. Esto cambia sustancialmente el alcance
esperable de la Fase 5 respecto de lo previsto en el Plan de Trabajo Final (que
preveía desarrollo de ensamble y selección de un modelo ganador), y debe discutirse
explícitamente con la dirección antes de iniciar el desarrollo de esa fase (ver
sección 7, punto 8). Ver `docs/decisions/track_a_b_sintesis_direccion_volatilidad.md`
para el detalle completo de esta síntesis.

## 5. Implicancias metodológicas para la tesis

Las decisiones descriptas en las secciones anteriores no son de naturaleza
puramente técnica: condicionan la interpretación de la variable objetivo (retornos
logarítmicos) y de los features derivados, y deben declararse explícitamente en la
sección de metodología del trabajo final. En particular:

- El Enfoque A de ajuste retroactivo por splits implica que los retornos calculados
  para un ticker reflejan su comportamiento como componente del índice y no
  necesariamente su historia bursátil completa.
- El criterio de dividendos en acciones como splits encubiertos fue validado
  empíricamente con el equipo que administra el índice, pero no está documentado en
  fuentes públicas, por lo que su justificación recae enteramente en este trabajo.
- La corrección del cambio de base resuelve la mayor parte de la discrepancia
  detectada, pero deja un residuo no explicado que debe comunicarse como limitación
  conocida antes que como error resuelto.
- La reinterpretación de "volatilidad implícita" como tasa implícita y term spread de
  futuros (sección 3.3) se aparta de lo previsto en el Plan de Trabajo Final por una
  limitación real del mercado subyacente (ausencia de opciones con volumen), y debe
  presentarse como tal —no como una feature equivalente bajo otro nombre.
- La decisión de no productivizar la diferenciación fraccional (sección 3.4) quedó
  cerrada al terminar Track A sin haber requerido esa transformación —el hallazgo
  (d=0,35) se presenta como aporte metodológico exploratorio en sí mismo.
- El diseño del conjunto de test como datos genuinamente nuevos (sección 3.5), en
  lugar de un recorte del historial, fortalece la validez de la evaluación
  out-of-sample y debe destacarse como fortaleza metodológica del diseño experimental.
- El protocolo compartido entre los cuatro modelos de ML clásico (sección 4.2.2) y
  entre las cuatro arquitecturas de Deep Learning (sección 4.3) —mismo criterio de
  imputación, misma validación cruzada temporal, misma métrica de importancia de
  variables— es lo que permite presentar la tabla comparativa de la sección 4.6 como
  una comparación homogénea entre paradigmas, y debe explicitarse como decisión de
  diseño deliberada en la sección de metodología, no darse por sentada.
- El hallazgo central de Bloque 2 (sección 4.6) —ningún método mejora de forma
  consistente sobre el naive, ni en dirección ni en volatilidad— reencuadra el aporte
  de la tesis: de una herramienta de predicción funcional (como sugiere la
  formulación original de los objetivos del Plan de Trabajo Final) a una comparación
  metodológica rigurosa entre paradigmas en un mercado emergente, con un resultado
  negativo consistente como hallazgo académico legítimo. Este reencuadre debe
  discutirse explícitamente con la dirección (ver sección 7, punto 7) antes de
  redactar las secciones de introducción y objetivos de la tesis final.
- La corrección de datos de composición de septiembre de 2019 (sección 4.1), al igual
  que las de la sección 2, refuerza que toda conclusión de Bloque 2 está condicionada
  a la calidad del dataset de entrada verificada hasta la fecha — quedan pendientes
  menores de calidad de datos (recomposición desfasada, MIRG, cluster de mayo de
  2024) que no se auditaron todavía y que deben mencionarse como limitación conocida
  del alcance de validación de datos.

## 6. Actualización del plan de trabajo

Los tiempos reales de ejecución de la Fase 1 (aproximadamente trece semanas frente a
las ocho previstas) motivaron, en la Versión 1 de este documento, un ajuste del plan
de las fases restantes para mantener el objetivo de presentación antes de diciembre de
2026. La Fase 2 se ejecutó en el tiempo previsto (poco más de dos semanas frente a
las tres a cuatro estimadas). Las Fases 3 y 4 (Bloque 2), en cambio, se completaron en
apenas diez días (5 al 15 de septiembre de 2026) frente a las doce semanas previstas
en total (seis cada una) en el Plan de Trabajo Final —incluso corriéndolas en
paralelo, como ya preveía la reorganización acordada—, lo que deja un margen de
calendario considerable antes de la fecha objetivo de presentación. Ese margen no se
trasladó automáticamente a un inicio anticipado de la Fase 5: como se desarrolla en la
sección 4.6, el resultado de Bloque 2 (ningún método supera al naive, ni en dirección
ni en volatilidad) deja sin base buena parte de lo que la Fase 5 preveía hacer
(desarrollo de ensamble, selección de un modelo ganador), por lo que su alcance debe
redefinirse con la dirección antes de comenzar a programar, en lugar de iniciar
código bajo los supuestos originales del plan. El detalle operativo completo está
desarrollado en `docs/plan_de_accion.md`.

| Etapa | Ventana | Contenido | Estado |
|---|---|---|---|
| Ingeniería de features (Fase 2) | 20 ago – 10 sep 2026 | Indicadores técnicos, volatilidad realizada, features macro derivados | **Completa** (cerrada 26 ago) |
| Modelos estadísticos/ML y Deep Learning (Fases 3-4, en paralelo) | 5 – 15 sep 2026 (ventana original: 11 sep – 29 oct) | ARIMA/SARIMA, GARCH, SVM, RF, XGBoost, LightGBM / LSTM, GRU, CNN-LSTM, "TFT-lite" | **Completa**, más de cinco semanas antes de lo previsto |
| Comparación y selección (Fase 5) | Ventana original: 30 oct – 12 nov 2026 — a redefinir | Evaluación multicriterio, ensamble, selección de modelo final | **Pendiente de redefinir alcance con la dirección** antes de iniciar desarrollo (ver sección 7, punto 8) |
| Cierre y consolidación (Fase 6) | 13 nov – 28 nov 2026 (sin cambios) | Consolidación de lo redactado, incorporación de devoluciones, revisión final | Pendiente |

## 7. Puntos de validación pendientes con la dirección

1. Idoneidad del Enfoque A de ajuste por splits (sección 2.1) como criterio a sostener
   en la tesis, frente a la alternativa de declararlo como supuesto metodológico a
   discutir en limitaciones. *(pendiente desde Versión 1)*
2. Prioridad relativa del análisis de las ocho jornadas con error residual de
   reconstrucción (sección 2.3): profundizar antes de avanzar, o documentar como
   limitación conocida y continuar. *(pendiente desde Versión 1)*
3. Conformidad con la reinterpretación de "volatilidad implícita" como tasa implícita
   y term spread de futuros (sección 3.3), dado que se aparta de lo previsto en el
   Plan de Trabajo Final. *(pendiente desde Versión 2)*
4. Conformidad con el diseño del split temporal y, en particular, con el uso de datos
   backfilleados vía servicio en tiempo real de MatbaRofex como conjunto de test
   (sección 3.5), incluyendo la decisión de seguridad asociada (sección 3.6).
   *(pendiente desde Versión 2)*
5. *(Resuelto en Versión 2)* El componente ECOG se incorporó a la ingesta el mismo
   día en que se detectó.
6. *(Resuelto en esta versión)* La exploración de diferenciación fraccional
   (sección 3.4) cerró sin productivizarse: Track A no encontró el consumidor
   concreto (un modelo ARIMA con estructura explotable) que hubiera justificado
   retomarla.
7. **Nuevo.** Conformidad con presentar el hallazgo central de Bloque 2 (sección 4.6)
   —ningún método mejora de forma consistente sobre el naive, ni en dirección ni en
   volatilidad— como resultado válido y defendible para la tesis, y con el reencuadre
   que esto implica para las secciones de motivación y objetivos del Plan de Trabajo
   Final original, que planteaban una herramienta de predicción funcional como
   entregable central.
8. **Nuevo — bloqueante para iniciar la Fase 5.** Alcance de la Fase 5 (Bloque 3,
   comparación y selección) dado el resultado de Bloque 2: un ensamble no tiene base
   sobre la que mejorar del lado de dirección, y no queda ningún modelo positivo de
   volatilidad para explorar combinaciones de ese lado tampoco. Definir con la
   dirección qué constituye "framework de evaluación multicriterio" y "selección de
   modelo final" en este escenario antes de iniciar el desarrollo.
9. **Nuevo.** La extensión a horizontes largos (10/21 días, sección 4.4) no fue
   re-corrida después de la corrección de datos de septiembre de 2019 —a diferencia
   de los diez métodos de 1/3/5 días, sí re-corridos—. La magnitud reportada de GARCH
   en ese experimento (~39-40% mejor que el naive) probablemente esté sobreestimada
   por el mismo mecanismo ya corregido para el horizonte corto. No bloquea nada
   operativamente (la línea ya está descartada del alcance del proyecto), pero no
   debe citarse en la tesis como resultado numérico vigente sin re-ejecutar el
   experimento sobre el dataset corregido.
10. **Nuevo.** Pendientes menores de calidad de datos identificados junto con la
    corrección de septiembre de 2019 (sección 4.1): recomposición de cartera
    desfasada un día hábil (alcance no auditado en el resto de la serie 2018-2026),
    desvío crónico de MIRG sin investigar, y un cluster menor de desvíos en mayo de
    2024. Ninguno es bloqueante para Bloque 2; prioridad relativa a definir con la
    dirección, en la misma línea que el punto 2.

## 8. Próxima actualización

La siguiente revisión de este documento incorporará el resultado de la conversación
con la dirección sobre el alcance de la Fase 5 (punto 8 de la sección 7) y, una vez
definido, la metodología y los resultados del framework de evaluación multicriterio
y de la selección de modelo final, prevista para el cierre de esa fase (Checkpoint 3
de `docs/plan_de_accion.md`, originalmente estimado para mediados de noviembre de
2026, sujeto a la redefinición de alcance pendiente).
