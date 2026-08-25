# Avance de Trabajo Final — Predicción del Índice ROFEX 20

**Maestría en Explotación de Datos y Gestión del Conocimiento — Universidad Austral**

**Alumno:** Matías Humberto Tibaldo
**Directora:** Fernanda Mendez — **Co-Director:** Rodrigo Del Rosso
**Documento de avance — Versión 1**
**Fecha:** agosto de 2026

---

## 0. Propósito de este documento

El Plan de Trabajo Final (versión preliminar 3, marzo de 2026) estableció en su
sección 9 la metodología general del proyecto y en su sección 10 un plan de trabajo
tentativo de seis fases. Este documento tiene como propósito reportar el avance
metodológico concreto logrado en la primera fase de ejecución —consolidación y
procesamiento de datos— y actualizar el plan de trabajo en función de los tiempos
reales observados.

A diferencia de un informe de estado puntual, este documento está pensado como
**construcción continua**: se irá extendiendo en cada hito de avance (ingeniería de
features, modelos estadísticos y de machine learning, deep learning, selección de
modelo final), de modo que al llegar a la etapa de redacción de la tesis buena parte
del contenido metodológico ya esté consolidado y validado con la dirección. La
correspondencia entre cada hito y este documento está detallada en el plan de acción
adjunto (`docs/plan_de_accion.md`).

## 1. Estado de avance respecto del Plan de Trabajo Final

La Fase 1 del plan original ("Datos", 8 semanas) contemplaba la recopilación y
consolidación de datos base, la obtención de variables macro y eventos corporativos,
la limpieza e integración temporal, y el análisis exploratorio inicial. Esta fase se
encuentra sustancialmente completa, con un alcance adicional: se incorporó ya en esta
etapa parte del tratamiento que la Fase 2 ("Ingeniería de Features") reservaba para
las variables dummy de eventos macroeconómicos, dado que su detección estaba
directamente ligada al proceso de validación de splits.

Concretamente, se completaron:

- La consolidación de la composición histórica del índice (27 tickers, 2018 a la
  fecha), incluyendo las series de divisor y valor spot oficial publicadas por Primary S.A.
- La ingesta de series OHLCV diarias de los 27 componentes.
- El módulo de ajuste por eventos corporativos (splits y dividendos encubiertos).
- El módulo de procesamiento de series (`processing/`), que produce retornos
  logarítmicos, variables dummy de eventos macroeconómicos, datasets consolidados en
  formato ancho y largo, y una reconstrucción del índice a partir de sus componentes,
  utilizada como mecanismo de validación cruzada frente al valor spot oficial.
- La consolidación de un conjunto de variables macroeconómicas diarias y mensuales
  (tipo de cambio en sus distintas modalidades, riesgo país, tasa de plazo fijo,
  inflación mensual, índice Merval) que constituyen la base para las variables
  predictoras macro previstas en la sección de Metodología del plan original.

La etapa de ingeniería de features (Fase 2) inicia en la semana en curso.

## 2. Metodología de datos: decisiones adoptadas en la consolidación y el procesamiento

Esta sección desarrolla, con el nivel de detalle metodológico que corresponde a la
tesis, las decisiones tomadas durante la Fase 1. El detalle técnico de cada una está
registrado como documento de decisión independiente en `docs/decisions/`, que
constituye la fuente primaria de esta sección.

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
3,25% (concentradas en noviembre de 2022 y mayo de 2024), cuyo análisis puntual queda
pendiente y se plantea como punto de validación con la dirección en la sección 4.

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
derivados —spreads cambiarios, term spread— previstos para la Fase 2.

## 3. Implicancias metodológicas para la tesis

Las decisiones descriptas en la sección anterior no son de naturaleza puramente
técnica: condicionan la interpretación de la variable objetivo (retornos
logarítmicos) y deben declararse explícitamente en la sección de metodología del
trabajo final, tal como el propio Plan de Trabajo Final anticipaba para el caso del
ajuste por splits. En particular, el Enfoque A de ajuste retroactivo implica que los
retornos calculados para un ticker reflejan su comportamiento como componente del
índice y no necesariamente su historia bursátil completa; el criterio de dividendos
AC como splits encubiertos fue validado empíricamente con el equipo que administra el
índice, pero no está documentado en fuentes públicas, por lo que su justificación
recae enteramente en este trabajo; y la corrección del cambio de base, si bien resuelve
la mayor parte de la discrepancia detectada, deja un residuo no explicado que debe
comunicarse como limitación conocida antes que como error resuelto.

## 4. Actualización del plan de trabajo

Los tiempos reales de ejecución de la Fase 1 (aproximadamente trece semanas, frente a
las ocho previstas originalmente) obligan a un ajuste del plan de trabajo de las fases
restantes si se pretende mantener el objetivo de presentación antes de diciembre de
2026. El ajuste no reduce el alcance definido en el Plan de Trabajo Final —se
mantienen las tres familias de modelos, los criterios de evaluación multicriterio y el
horizonte de predicción de 1 a 5 días hábiles como foco principal— sino que reorganiza
su ejecución de dos maneras: (i) las Fases 3 y 4 (modelos estadísticos/ML y modelos de
Deep Learning), que el propio Plan de Trabajo Final contemplaba como potencialmente
solapables, se ejecutan en paralelo en lugar de secuencialmente; y (ii) la redacción de
las secciones metodológicas de la tesis, que la Fase 6 reservaba para el tramo final,
se realiza de manera continua desde esta etapa, con devoluciones periódicas de la
dirección en cada hito. El detalle operativo de este ajuste está desarrollado en
`docs/plan_de_accion.md`.

| Etapa | Ventana | Contenido |
|---|---|---|
| Ingeniería de features (Fase 2) | 20 ago – 10 sep 2026 | Indicadores técnicos, volatilidad realizada, features macro derivados |
| Modelos estadísticos/ML y Deep Learning (Fases 3-4, en paralelo) | 11 sep – 29 oct 2026 | ARIMA/SARIMA, GARCH, SVM, RF, XGBoost, LightGBM / LSTM, GRU, evaluación preliminar de arquitecturas con atención |
| Comparación y selección (Fase 5) | 30 oct – 12 nov 2026 | Evaluación multicriterio, ensemble, selección de modelo final |
| Cierre y consolidación (Fase 6) | 13 nov – 28 nov 2026 | Consolidación de lo redactado, incorporación de devoluciones, revisión final |

## 5. Puntos de validación pendientes con la dirección

1. Idoneidad del Enfoque A de ajuste por splits (sección 2.1) como criterio a sostener
   en la tesis, frente a la alternativa de declararlo como supuesto metodológico a
   discutir en limitaciones.
2. Prioridad relativa del análisis de las ocho jornadas con error residual de
   reconstrucción (sección 2.3): profundizar antes de avanzar a features, o
   documentar como limitación conocida y continuar.
3. Disponibilidad del spread de futuros RFX20/ABR26 como fuente de volatilidad
   implícita, prevista en el Anexo de la Fase 3 del Plan de Trabajo Final.
4. Conformidad con la reorganización del plan de trabajo descripta en la sección 4
   (paralelización de Fases 3 y 4, redacción continua) como vía para sostener el
   objetivo de presentación antes de diciembre de 2026.

## 6. Próxima actualización

La siguiente revisión de este documento incorporará la metodología de la Fase 2
(ingeniería de features), prevista para el cierre del primer hito del plan de acción
(alrededor del 10 de septiembre de 2026).
