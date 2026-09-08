# Avance de Trabajo Final — Predicción del Índice ROFEX 20

**Maestría en Explotación de Datos y Gestión del Conocimiento — Universidad Austral**

**Alumno:** Matías Humberto Tibaldo
**Directora:** Fernanda Mendez — **Co-Director:** Rodrigo Del Rosso
**Documento de avance — Versión 2**
**Fecha:** septiembre de 2026

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

Respecto de la Versión 1 (agosto de 2026), esta versión agrega la sección 3
(Metodología de ingeniería de features) y actualiza las secciones 1, 4 (ahora 5), 5
(ahora 6) y 6 (ahora 7) en función del cierre de la Fase 2.

## 1. Estado de avance respecto del Plan de Trabajo Final

La Fase 1 ("Datos") y la Fase 2 ("Ingeniería de Features") del plan original se
encuentran completas. La Fase 1 (8 semanas previstas) demandó aproximadamente trece;
la Fase 2 (4 semanas previstas) se completó en poco más de dos semanas (20 de agosto
al 5 de septiembre de 2026), construida deliberadamente por etapas para validar cada
bloque de features contra los datos reales antes de sumar el siguiente.

Concretamente, además de lo ya reportado en la Versión 1 de este documento (Fase 1:
consolidación de composición histórica, ingesta OHLCV, ajuste por eventos
corporativos, módulo de procesamiento), se completó en Fase 2:

- Indicadores técnicos (medias móviles, RSI, MACD, Bandas de Bollinger) y volatilidad
  realizada, calculados tanto sobre los 27 componentes como sobre la serie del propio
  índice, junto con la construcción del target del índice (retornos logarítmicos
  forward a 1, 3 y 5 días hábiles).
- Un conjunto de features macroeconómicos derivados: spreads cambiarios, riesgo país,
  tasas de referencia (plazo fijo, BADLAR, TAMAR), inflación mensual con ajuste por
  lag de publicación, y una reinterpretación de "volatilidad implícita" como tasa
  implícita y term spread de la curva de futuros del propio RFX20.
- Una exploración acotada de diferenciación fraccional sobre el log-precio del
  índice, no productivizada por el momento.
- El particionamiento temporal train/validation/test y la consolidación del dataset
  final de modelado (`features_long.parquet`), incorporando además un backfill de
  datos genuinamente nuevos que permite un conjunto de test 100% out-of-sample.

La Fase 3 (modelos estadísticos y de machine learning clásico) y la Fase 4 (modelos
de Deep Learning) —reorganizadas para ejecutarse en paralelo, según lo descripto en la
sección 5— inician en la semana en curso.

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

## 4. Implicancias metodológicas para la tesis

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
- La decisión de no productivizar la diferenciación fraccional (sección 3.4) es
  provisoria y está condicionada a las necesidades del Track A de la Fase 3; si se
  retoma, corresponde documentar en qué modelo se usó y por qué.
- El diseño del conjunto de test como datos genuinamente nuevos (sección 3.5), en
  lugar de un recorte del historial, fortalece la validez de la evaluación
  out-of-sample y debe destacarse como fortaleza metodológica del diseño experimental.

## 5. Actualización del plan de trabajo

Los tiempos reales de ejecución de la Fase 1 (aproximadamente trece semanas frente a
las ocho previstas) motivaron, en la Versión 1 de este documento, un ajuste del plan
de las fases restantes para mantener el objetivo de presentación antes de diciembre de
2026. La Fase 2, en cambio, se ejecutó en el tiempo previsto (poco más de dos semanas
frente a las tres a cuatro estimadas), lo que no modifica el cronograma ya
comunicado. El ajuste no reduce el alcance definido en el Plan de Trabajo Final —se
mantienen las tres familias de modelos, los criterios de evaluación multicriterio y el
horizonte de predicción de 1 a 5 días hábiles como foco principal— y conserva la
reorganización ya acordada: Fases 3 y 4 en paralelo, y redacción continua de las
secciones metodológicas de la tesis desde la Fase 1 en adelante. El detalle operativo
está desarrollado en `docs/plan_de_accion.md`.

| Etapa | Ventana | Contenido | Estado |
|---|---|---|---|
| Ingeniería de features (Fase 2) | 20 ago – 10 sep 2026 | Indicadores técnicos, volatilidad realizada, features macro derivados | **Completa** (cerrada 26 ago) |
| Modelos estadísticos/ML y Deep Learning (Fases 3-4, en paralelo) | 11 sep – 29 oct 2026 | ARIMA/SARIMA, GARCH, SVM, RF, XGBoost, LightGBM / LSTM, GRU, evaluación preliminar de arquitecturas con atención | Inicia esta semana |
| Comparación y selección (Fase 5) | 30 oct – 12 nov 2026 | Evaluación multicriterio, ensemble, selección de modelo final | Pendiente |
| Cierre y consolidación (Fase 6) | 13 nov – 28 nov 2026 | Consolidación de lo redactado, incorporación de devoluciones, revisión final | Pendiente |

## 6. Puntos de validación pendientes con la dirección

1. Idoneidad del Enfoque A de ajuste por splits (sección 2.1) como criterio a sostener
   en la tesis, frente a la alternativa de declararlo como supuesto metodológico a
   discutir en limitaciones. *(pendiente desde Versión 1)*
2. Prioridad relativa del análisis de las ocho jornadas con error residual de
   reconstrucción (sección 2.3): profundizar antes de avanzar, o documentar como
   limitación conocida y continuar. *(pendiente desde Versión 1 — no se avanzó,
   dado que no bloqueaba la Fase 2)*
3. Conformidad con la reinterpretación de "volatilidad implícita" como tasa implícita
   y term spread de futuros (sección 3.3), dado que se aparta de lo previsto en el
   Plan de Trabajo Final.
4. Conformidad con el diseño del split temporal y, en particular, con el uso de datos
   backfilleados vía servicio en tiempo real de MatbaRofex como conjunto de test
   (sección 3.5), incluyendo la decisión de seguridad asociada (sección 3.6).
5. *(Resuelto — ya no es un punto de validación pendiente)* El componente ECOG
   (sección 3.5) se incorporó a la ingesta el mismo día en que se detectó; queda
   disponible para cualquier fase de modelado que necesite la composición
   individual actualizada.
6. Conformidad con mantener la exploración de diferenciación fraccional (sección 3.4)
   como no productivizada, sujeta a que el Track A de la Fase 3 la requiera.

*(El punto 3 de la Versión 1, sobre disponibilidad del spread de futuros RFX20/ABR26
como fuente de volatilidad implícita, se da por resuelto: ver sección 3.3.)*

## 7. Próxima actualización

La siguiente revisión de este documento incorporará la metodología y los resultados
preliminares del Track A de la Fase 3 (modelos estadísticos y de machine learning
clásico), prevista para el cierre de ese track a mediados de octubre de 2026
(Checkpoint 2 de `docs/plan_de_accion.md`).
