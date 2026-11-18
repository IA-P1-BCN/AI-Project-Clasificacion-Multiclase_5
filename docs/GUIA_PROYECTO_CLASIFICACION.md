# Guía viva del proyecto de clasificación multiclase

> Documento de equipo. Sigue los pasos de la *Guía de un proyecto de clasificación en ML* y sirve para **dejar por escrito qué decidimos, por qué, y qué significa cada cosa**. Lo rellenamos entre todos a medida que avanzamos.
>
> **Repositorio:** https://github.com/IA-P1-BCN/AI-Project-Clasificacion-Multiclase_5
> **Dataset:** Forest Cover Type (Covertype), UCI Machine Learning Repository

---

## Cómo usar este documento

1. Cada vez que el equipo toma una decisión, se añade un bloque con el formato de abajo en el paso que corresponda.
2. Las **palabras técnicas** aparecen explicadas en el [Glosario](#glosario) del final. Si falta alguna, añadidla.
3. Si una decisión depende de un commit o un PR, ponedlo en **Evidencia** (así cualquiera puede ir a verlo).
4. Si algo no está decidido todavía, se deja en estado ⬜ y se anota quién lo decide.

### Leyenda de estados

| Icono | Significado |
|---|---|
| ✅ | Decidido y documentado |
| 🟡 | En curso o decidido a medias |
| ⬜ | Pendiente de decidir o de rellenar |

### Formato de cada decisión (copiar y pegar)

```markdown
#### Dx.y · Nombre corto de la decisión  (✅ / 🟡 / ⬜)

**Decisión:** qué hemos decidido, en una frase.

**Justificación:** por qué lo hemos elegido (y qué alternativas descartamos).

**Explicación sencilla:** qué es esto y por qué se hace, como si se lo explicáramos a alguien que empieza.

**Evidencia:** ticket, PR, commit o fichero donde se ve.

**Responsable:** quién lo hizo / quién lo decide.
```

---

## Vista general

| # | Paso | Estado |
|---|---|---|
| 0 | Definir el problema | 🟡 Parte rellena, 4 decisiones por tomar |
| 1 | Datos y split | 🟡 Parte rellena, 3 puntos por revisar |
| 2 | EDA (análisis exploratorio) | ✅ Documentado (queda R1 por decidir) |
| 3 | Preprocesado | 🟡 Nulos/duplicados (#12) y escalado (#14) documentados; faltan atípicos (#13) y target encoding (#15) |
| 4 | Feature engineering y selección | ✅ Documentado (#18) |
| 5 | Baseline | ⬜ Por documentar (hay trabajo hecho en el repo) |
| 6 | Entrenamiento y validación | 🟡 Desbalanceo (#17), regresión logística (#20) y red neuronal (#24) documentados; faltan árboles y shortlist (#21–#23) |
| 7 | Ajuste de hiperparámetros | ✅ Random Forest y XGBoost afinados con RandomizedSearchCV (#29) |
| 8 | Evaluación final | ✅ Métricas finales y matriz de confusión documentadas (#25); falta cierre formal de overfitting (#28) |
| 9 | Análisis de errores e interpretación | ✅ Errores (#27) e interpretación con SHAP aproximado (#30) documentados |
| 10 | Despliegue y monitoreo | 🟡 API (#34) con base de datos (#37), feedback y métricas (#35), pipeline exportado (#32), CI en verde (#41), orquestación con Compose (#38), guías de ejecución (#46, #47), monitoreo de drift (#53) y test end-to-end (#42); falta el despliegue en la nube (#39) |

---

# Paso 0 · Definir el problema

> **Idea en una frase:** antes de tocar datos, hay que tener claro qué queremos predecir, para qué, y cómo sabremos que lo hemos conseguido. Si el problema está mal planteado, un buen modelo no sirve de nada.

## 0.1 Decisiones tomadas

#### D0.1 · Qué queremos predecir  (✅)

**Decisión:** predecir el **tipo de cobertura forestal** (la especie de árbol dominante) de una celda de 30 × 30 metros del Roosevelt National Forest (Colorado, EE. UU.), a partir de datos cartográficos y ambientales (altitud, pendiente, tipo de suelo, distancias, etc.).

**Justificación:** es un problema real, con una aplicación clara (gestión forestal, mapas ecológicos, planificación de recursos) y con datos públicos bien documentados.

**Explicación sencilla:** imagina que dividimos el bosque en cuadraditos del tamaño de un campo pequeño. Para cada cuadradito conocemos su altitud, su pendiente, si está cerca de un río, etc. El modelo debe "adivinar" qué tipo de árbol domina ahí, sin tener que ir a mirarlo.

**Evidencia:** `SPEC.md` §2 · issue #2 · commit `3f86f44` · PR #57.

**Responsable:** equipo.

---

#### D0.2 · Tipo de problema: clasificación multiclase con 7 clases  (✅)

**Decisión:** es un problema **supervisado** de **clasificación multiclase**. Cada celda pertenece a **una sola** de 7 clases:

| Código | Clase |
|---|---|
| 1 | Spruce/Fir (abeto/pícea) |
| 2 | Lodgepole Pine (pino contorta) |
| 3 | Ponderosa Pine (pino ponderosa) |
| 4 | Cottonwood/Willow (álamo/sauce) |
| 5 | Aspen (álamo temblón) |
| 6 | Douglas-fir (abeto de Douglas) |
| 7 | Krummholz (vegetación achaparrada de alta montaña) |

**Justificación:** el enunciado exige mínimo 3 clases excluyentes entre sí; aquí hay 7 y ninguna celda puede ser de dos tipos a la vez (por eso es *multiclase* y no *multietiqueta*).

**Explicación sencilla:**
- *Supervisado* = el modelo aprende con ejemplos que ya tienen la respuesta correcta.
- *Binaria* = 2 respuestas posibles (sí/no). *Multiclase* = 3 o más, y solo una es la correcta. *Multietiqueta* = varias respuestas pueden ser verdad a la vez (por ejemplo, una película que es "comedia" y "romance").

**Evidencia:** `SPEC.md` §2 · `specs/ontology.md`.

**Responsable:** equipo.

---

#### D0.3 · Dataset elegido: Forest Cover Type (Covertype)  (✅)

**Decisión:** usar Covertype (UCI, dataset nº 31), en lugar de Wine o Dry Bean.

**Justificación:**

| Criterio | Wine | Dry Bean | **Covertype** |
|---|---|---|---|
| Filas | 178 | 13.611 | **581.012** |
| Variables | 13 | 16 | **54** |
| Clases | 3 | 7 | **7** |
| Desbalanceo (clase mayor : menor) | casi equilibrado | ~1 : 7 | **~1 : 103** |
| Tipos de variables | todas numéricas | todas numéricas | **10 numéricas + 44 binarias** |

- **Tamaño:** tener muchos datos permite hacer un buen reparto train/validación/test y validación cruzada. Wine es demasiado pequeño para una evaluación convincente.
- **Desbalanceo fuerte:** obliga a usar métricas por clase y no solo accuracy, y hace que técnicas como los pesos de clase tengan sentido.
- **Variables mixtas:** obliga a construir un preprocesado de verdad (escalar solo las numéricas, sin fugas de datos).
- **Contrapartida:** es más pesado de entrenar y más difícil, pero eso encaja con los niveles Medio y superiores del enunciado.

**Explicación sencilla:** *desbalanceado* significa que hay clases muy frecuentes y otras casi raras. En Covertype, casi la mitad de las celdas (48,76 %) son "Lodgepole Pine" y solo el 0,47 % son "Cottonwood/Willow". Si el modelo se limita a decir siempre "Lodgepole Pine", acertaría casi la mitad de las veces sin aprender nada útil. Por eso este dataset es un buen reto.

**Evidencia:** `docs/DATASET_SELECTION.md` · issue #3 · PR #71. Fuente y versión: `data/README.md` · issue #4 · PR #64. Diccionario de datos: `docs/DATA_DICTIONARY.md` · issue #5 · PR #72.

**Responsable:** @carovasq (selección), equipo.

---

#### D0.4 · Métrica principal: macro F1  (✅)

**Decisión:** la métrica principal es el **macro F1**. Además se reportan accuracy, precision, recall y F1 por clase, y la matriz de confusión.

**Justificación:** con clases tan desbalanceadas, el accuracy engaña. En nuestros baselines:

| Baseline | Accuracy | Macro F1 |
|---|---|---|
| `DummyClassifier` (siempre la clase mayoritaria) | 0,4876 | **0,0937** |
| `DummyClassifier` (aleatorio respetando proporciones) | 0,3770 | 0,1426 |

El baseline "siempre la mayoritaria" tiene el mejor accuracy pero el peor macro F1, porque nunca acierta ninguna clase pequeña.

**Explicación sencilla:**
- **Accuracy** = % de aciertos totales. Es fácil de entender, pero las clases grandes pesan mucho y las pequeñas casi no cuentan.
- **Precision** = de todo lo que el modelo dijo que era clase X, cuánto lo era de verdad.
- **Recall** = de todo lo que de verdad era clase X, cuánto encontró el modelo.
- **F1** = una sola nota que mezcla precision y recall.
- **Macro F1** = se calcula el F1 de cada clase por separado y se hace la media. Así **cada clase vale lo mismo**, sea grande o pequeña.

**Evidencia:** `docs/MODELING.md` · PR #69.

**Responsable:** equipo.

---

#### D0.5 · Criterio de éxito: overfitting menor al 5 %  (✅)

**Decisión:** la diferencia entre el resultado en entrenamiento y en validación debe ser **inferior al 5 %**.

**Justificación:** es un requisito del enunciado del proyecto y una puerta de calidad (*quality gate*) en `SPEC.md` §7.

**Explicación sencilla:** el *overfitting* (sobreajuste) es cuando el modelo "se aprende de memoria" los ejemplos de entrenamiento en vez de entender el patrón. Se nota porque saca muy buena nota en entrenamiento y mucha peor en datos nuevos. Como si un estudiante se memorizara las respuestas del examen de prueba: en ese examen saca 10, pero en el examen real no sabe resolver nada distinto.

**Evidencia:** `SPEC.md` §2 y §7 · briefing del proyecto.

**Responsable:** equipo.

---

#### D0.6 · Referencia mínima a superar (baseline)  (✅)

**Decisión:** cualquier modelo serio tiene que ganar a los `DummyClassifier` y a una regresión logística simple.

**Justificación:** si un modelo complicado no mejora claramente a algo trivial, no compensa su coste.

**Explicación sencilla:** un *baseline* es la "vara de medir" mínima. Es la respuesta más tonta posible (por ejemplo, "siempre digo la clase más común"). Si nuestro modelo no la supera, no hemos aprendido nada.

**Evidencia:** `docs/MODELING.md` · PR #69.

**Responsable:** equipo.

---

## 0.2 Preguntas de la guía todavía sin responder

> Estas preguntas vienen de la guía y **no están respondidas en el repo**. Para cada una hay una **propuesta de partida** que el equipo debe discutir y aceptar, cambiar o descartar.

#### D0.7 · ¿Qué error cuesta más?  (⬜)

**Decisión:** *por decidir.*

**Propuesta para discutir:** confundir las clases minoritarias (por ejemplo, Cottonwood/Willow, solo el 0,47 %) podría ser más grave que confundir las dos más comunes, porque son las más difíciles de detectar y pasarían desapercibidas. Eso justificaría macro F1 y recall por clase.

**Justificación:** *(rellenar tras la decisión).*

**Explicación sencilla:** no todos los errores pesan igual. En medicina, no detectar una enfermedad es mucho peor que una falsa alarma. Aquí hay que pensar: ¿es peor ignorar un tipo de bosque raro, o "ver" uno que no existe?

**Evidencia:** —

**Responsable:** ⬜

---

#### D0.8 · ¿Qué decisión se tomará con la predicción?  (⬜)

**Decisión:** *por decidir.*

**Propuesta para discutir:** ahora mismo el objetivo está a nivel general ("apoyar la gestión forestal"). Convendría concretarlo, por ejemplo: "un técnico forestal introduce las características de una zona y usa la predicción para priorizar qué zonas inspeccionar".

**Justificación:** *(rellenar)*

**Explicación sencilla:** un modelo es útil cuando alguien hace algo distinto gracias a él. Pensar en esa persona y esa acción ayuda a decidir qué métrica importa y cómo debe ser la aplicación.

**Evidencia:** —

**Responsable:** ⬜

---

#### D0.9 · ¿Tendremos cada variable disponible al predecir?  (🟡)

**Decisión:** propuesta: sí. Las 54 variables son cartográficas (altitud, pendiente, orientación, sombreado, distancias, zona silvestre y tipo de suelo). Describen el terreno y ninguna se calcula después de conocer el tipo de bosque, así que no hay fuga por esa vía. Las 8 variables nuevas de #18 (ver D4.2) se calculan solo con `Elevation` y tres distancias.

**A decidir por el equipo:** la API pide al usuario los 10 valores numéricos. Un usuario real normalmente no conoce, por ejemplo, el sombreado a las 9 am. Hay que decidir si esos valores se rellenan por defecto, se calculan desde otros o se piden todos.

**Justificación:** *(confirmar entre todos).*

**Explicación sencilla:** si una variable solo se conoce *después* de saber la respuesta (por ejemplo, un campo que se rellena al terminar un proceso), el modelo parecería genial en el laboratorio y fallaría en la vida real. A eso se le llama trampa o *data leakage*.

**Evidencia:** `app/schemas.py` · PR #81 · D4.5.

**Responsable:** ⬜ confirmar.

---

#### D0.10 · ¿Qué resultado cuenta como "suficientemente bueno"?  (⬜)

**Decisión:** *por decidir.*

**Propuesta para discutir:** además del overfitting < 5 %, fijar un **macro F1 mínimo** objetivo (por ejemplo, un valor que mejore claramente el obtenido por los modelos actuales, que están en `docs/MODELING.md`).

**Justificación:** *(rellenar)*

**Explicación sencilla:** sin un número objetivo, nunca sabemos cuándo parar de mejorar el modelo.

**Evidencia:** —

**Responsable:** ⬜

---

# Paso 1 · Datos y split

> **Idea en una frase:** antes de explorar o preparar los datos, los **separamos en tres partes** (entrenar, validar, probar) y guardamos una parte intacta para el examen final. Así evitamos engañarnos a nosotros mismos.

## 1.1 Decisiones tomadas

#### D1.1 · Origen y trazabilidad de los datos  (✅)

**Decisión:** los datos vienen de la **UCI Machine Learning Repository** (dataset 31). El fichero original no se guarda en Git; se descarga siempre con un procedimiento documentado y se verifica con un **checksum**.

| | |
|---|---|
| Autores | Jock A. Blackard, Denis J. Dean, Charles W. Anderson (Colorado State University) |
| Licencia | CC BY 4.0 (se puede usar citando la fuente) |
| DOI | 10.24432/C50K5N |
| Fichero | `covtype.data`, 75.169.317 bytes (71,7 MiB) |
| Contenido | 581.012 filas × 55 columnas (54 variables + la clase `Cover_Type`) |
| Descargado el | 2026-11-12 |
| Nulos y duplicados | 0 y 0 |

**Justificación:** para que todo el equipo trabaje con **exactamente los mismos datos** y cualquiera pueda reproducir los resultados. Los datos pesan demasiado y no deben versionarse en Git (`data/raw/` está en `.gitignore`).

**Explicación sencilla:** un *checksum* (SHA-256) es como una huella digital del fichero. Si dos personas calculan la misma huella, tienen el mismo fichero idéntico. Si no coincide, alguien tiene una versión distinta o corrupta.

**Evidencia:** `data/README.md` · issue #4 · PR #64 · `python src/data_audit.py`.

**Responsable:** equipo.

---

#### D1.2 · ¿Hay suficientes filas para el número de variables?  (✅)

**Decisión:** sí. Tenemos 581.012 filas para 54 variables.

**Justificación:** una regla informal dice que se necesitan muchas más filas que variables para que el modelo aprenda patrones y no ruido. Aquí sobran. Incluso la clase más rara tiene unas 410 filas en el test.

**Explicación sencilla:** si tuviéramos 50 filas y 54 variables, el modelo podría encontrar "patrones" por pura casualidad. Con cientos de miles de filas, los patrones que encuentra son mucho más fiables.

**Evidencia:** `docs/DATASET_SELECTION.md` · `specs/feature-16-...` (decisión de ratios).

**Responsable:** equipo.

---

#### D1.3 · Reparto 70 % / 15 % / 15 %  (✅)

**Decisión:** dividir los datos en tres conjuntos:

| Conjunto | Para qué sirve | % | Filas |
|---|---|---|---|
| **Train** (entrenamiento) | El modelo aprende aquí | 70 % | 406.708 |
| **Validation** (validación) | Comparar modelos y ajustar parámetros | 15 % | 87.152 |
| **Test** | Examen final, **una sola vez** | 15 % | 87.152 |

**Justificación:** con tantos datos, un 15 % de test (≈ 87.000 filas) es suficiente para medir con fiabilidad incluso la clase más rara (≈ 410 filas), y el 70 % de train (≈ 406.000 filas) es más que suficiente para entrenar.

**Explicación sencilla:** piensa en un curso:
- **Train** = los ejercicios que practicas en clase.
- **Validation** = el simulacro de examen, con el que ves cómo vas y corriges tu forma de estudiar.
- **Test** = el examen final. Solo lo haces una vez; si miraras las preguntas antes, la nota ya no sería honesta.

**Evidencia:** `src/data_split.py` · `docs/PREPROCESSING.md` (sección *Train/validation/test split*) · issue #16 · commits `851d585`, `e056d20` · PR #68.

**Responsable:** @nagicome03.

---

#### D1.4 · Split estratificado por la clase `Cover_Type`  (✅)

**Decisión:** el reparto usa `stratify=y`, de modo que **cada conjunto mantiene las mismas proporciones de clases** que el dataset completo.

**Justificación:** como el dataset está muy desbalanceado (1 : 103), un reparto al azar simple podría dejar muy pocos ejemplos (o ninguno) de una clase rara en el test o en la validación, y no podríamos medirla.

**Explicación sencilla:** *estratificar* es como repartir caramelos de colores entre tres bolsas asegurándote de que **cada bolsa tiene la misma proporción de cada color**. Sin eso, una bolsa podría quedarse sin ningún caramelo rojo.

**Evidencia:** `src/data_split.py` (`split_train_val_test`) · PR #68.

**Responsable:** @nagicome03.

---

#### D1.5 · Semilla fija: `random_state=42`  (✅)

**Decisión:** el reparto usa una semilla fija (42).

**Justificación:** para que todo el equipo obtenga **los mismos conjuntos** y los resultados sean comparables y reproducibles.

**Explicación sencilla:** el ordenador "mezcla" los datos al azar. Una *semilla* (seed) es el punto de partida de ese azar: con la misma semilla, la mezcla sale **igual** cada vez. Es como barajar siempre un mazo de cartas y que salga el mismo orden. El número 42 es solo una convención.

**Evidencia:** `src/data_split.py` (`RANDOM_STATE = 42`).

**Responsable:** @nagicome03.

---

#### D1.6 · Primero se separa el test, luego la validación  (✅)

**Decisión:** el split se hace en dos pasos: primero se aparta el 15 % de test; del 85 % restante se aparta la validación (15/85 ≈ 17,6 % de lo que queda), y el resto es train.

**Justificación:** garantiza que los tres conjuntos **no se solapan**: ninguna fila está en dos a la vez.

**Explicación sencilla:** si una misma pregunta estuviera en el simulacro y en el examen final, la nota del examen no demostraría nada. Aquí nos aseguramos de que cada fila está en un solo conjunto.

**Evidencia:** `src/data_split.py` · `specs/feature-16-...`

**Responsable:** @nagicome03.

---

#### D1.7 · Comprobación automática de la estratificación  (✅)

**Decisión:** la función `check_stratification()` lanza un error si alguna proporción de clase se desvía más de 0,05 puntos porcentuales del dataset completo.

**Justificación:** no basta con *pedir* que el split sea estratificado; hay que **comprobarlo**.

**Resultado (12-nov-2026):** la comprobación pasó, con desviaciones menores de 0,001 puntos porcentuales en todas las particiones.

**Explicación sencilla:** es como contar los caramelos de cada bolsa al final para confirmar que el reparto salió bien.

**Evidencia:** `python src/data_split.py` · `specs/feature-16-...`

**Responsable:** @nagicome03.

---

#### D1.8 · El split no ajusta nada (sin fugas de datos)  (✅)

**Decisión:** `data_split.py` solo reparte filas; no calcula medias, escalas ni nada que "aprenda" de los datos.

**Justificación:** cualquier cálculo que use información del test antes de tiempo contamina el resultado (*data leakage*).

**Explicación sencilla:** *data leakage* (fuga de datos) es cuando el modelo "ve" sin querer información del examen final. Es como estudiar con las respuestas del examen: la nota sale genial, pero no vale nada.

**Evidencia:** `src/data_split.py` · `specs/feature-16-...`

**Responsable:** @nagicome03.

---

#### D1.9 · Validación cruzada estratificada (referencia)  (✅, se detalla en el Paso 6)

**Decisión:** para comparar modelos se usa `StratifiedKFold` de 5 folds sobre el conjunto de train.

**Explicación sencilla:** la *validación cruzada* divide el train en 5 trozos y entrena 5 veces, usando cada vez un trozo distinto como "mini-validación". Así el resultado no depende de la suerte de un único reparto.

**Evidencia:** `docs/MODELING.md`.

---

## 1.2 Puntos a revisar por el equipo

> Estas cuestiones aparecen al comparar lo que hemos hecho con lo que pide la guía. No son errores graves necesariamente; son cosas para **decidir y dejar por escrito**.

| # | Punto | Qué dice la guía | Qué hay en el repo | Estado |
|---|---|---|---|---|
| R1 | **EDA solo con train** | El EDA debe hacerse únicamente sobre el conjunto de entrenamiento. | Los scripts del EDA (`class_eda.py`, `class_distribution.py`, `statistical_insights.py`, `data_audit.py`) cargan el dataset completo (581.012 filas) porque el split se mergeó después (PR #68). **Riesgo bajo:** el EDA solo describió y recomendó, nada se ajustó con esas cifras (el escalado y el recorte de atípicos hacen *fit* sobre train) y con este tamaño las estadísticas de train y del total son casi iguales. La excepción posible es la clase 4 (2.747 filas). | 🟡 Decidir entre (1) dejarlo como limitación o (2) repetir los scripts del EDA sobre train y comprobar que las conclusiones no cambian (barato, los scripts ya existen). |
| R2 | **Un solo split para todos** | Todos los modelos deben usar las mismas particiones. | `logistic_regression.py` (#20), `random_forest.py` (#21), `neural_network.py` (#24), `model_comparison.py` (#23), `imbalance_handling.py` (#17), `export_model.py` (#32) y `final_metrics.py` (#25) ya usan el split canónico de `data_split.py` (#16: 406.708 train / 87.152 val / 87.152 test). Solo `baseline.py` (#19) y `gradient_boosting.py` (#22) tenían un split propio, pero fueron reevaluados sobre el split canónico en `model_comparison.py` (#23). | ✅ Unificado en la comparativa (#23) y en la evaluación final (#25) |
| R3 | **¿Filas relacionadas entre sí?** | Si hay varias filas de la misma persona/zona, separar por grupos; si hay tiempo, partir por fecha. | No está documentado si las celdas vecinas pueden estar relacionadas. | ⬜ Anotar "no aplica" con justificación, o decidir |
| R4 | **Test guardado y sin tocar** | No usar el test hasta el final. | No hay constancia escrita de la regla. | ⬜ Acordar y escribir la regla |

**Por qué importa R1, explicado fácil:** si miramos todos los datos (incluido lo que luego será el test) para decidir cosas, estamos "espiando" el examen aunque sea un poco. Los resultados finales podrían salir algo más optimistas de lo real. En nuestro caso el riesgo se considera bajo (ver la fila R1), pero hay que dejarlo por escrito.

---

# Paso 2 · EDA (análisis exploratorio)

> **Idea en una frase:** mirar los datos de entrenamiento con calma (tablas y gráficos) para entenderlos antes de modelar. **Solo con el conjunto train.**

**Qué mirar (checklist):**

- [x] Forma y tipos de datos
- [x] Variable objetivo: conteo de clases y desbalanceo
- [x] Nulos
- [x] Duplicados
- [x] Distribuciones (histogramas, asimetría, curtosis)
- [ ] Variables categóricas: conteos y categorías raras (las 44 binarias se auditaron pero no se analizaron contra la clase)
- [x] Relación de cada variable con el objetivo (gráficos por clase, eta cuadrado)
- [x] Correlaciones entre variables

**Preguntas de la guía:**

| Pregunta | Respuesta |
|---|---|
| ¿Algún valor no tiene sentido (edad negativa, fecha futura)? | No se vio ninguno. `Vertical_Distance_To_Hydrology` tiene negativos, que son válidos (terreno por debajo del agua más cercana). No se hizo un chequeo formal de rangos. (D2.4) |
| ¿Hay columnas que "saben demasiado" (sospecha de *data leakage*)? | No: las 54 son cartográficas, ninguna se conoce después de la clase (ver D0.9). |
| ¿Hay columnas inútiles (ID, constantes)? | No hay ID. ⬜ Falta comprobar si algún indicador de suelo tiene muy pocos o ningún 1. |
| ¿Los outliers son errores o casos reales importantes? | Parecen colas largas de variables sesgadas, hasta 5,4 % de filas por IQR. No se eliminaron. (D2.4) |
| ¿Qué variables parecen separar mejor las clases? | `Elevation` (η² 0,616). Después `Roadways` (0,096), `Slope` (0,074) y `Fire_Points` (0,070). (D2.3) |
| ¿Hay variables redundantes (muy correlacionadas)? | Ningún par supera \|0,8\| (máximo `Hillshade_9am`/`Hillshade_3pm`, −0,78), pero PC10 ≈ 0 % sugiere una dependencia lineal entre numéricas, sin verificar. (D2.3, D2.4) |

#### D2.1 · Auditoría del dataset  (✅)

**Decisión:** auditar sin modificar nada: 581.012 filas × 55 columnas (54 variables + `Cover_Type`), todo `int64`, 0 nulos y 0 duplicados. No se imputó ni se eliminó nada.

**Justificación:** antes de limpiar hay que saber qué limpiar. Las cifras coinciden con los metadatos de UCI. El archivo no trae cabecera: los nombres salen de `covtype.info`.

**Explicación sencilla:** contamos las piezas de la caja antes de armar el puzzle: están todas, ninguna repetida ni vacía.

**Evidencia:** issue #7 · PR #54 · `src/data_audit.py` · `docs/EDA.md` (Dataset audit) · `specs/feature-7-audit-dataset.md`.

**Responsable:** @Leandroletoile y equipo.

---

#### D2.2 · Distribución de clases y desbalance  (✅)

**Decisión:** tratar el desbalance como hecho central. Clase 2: 283.301 filas (48,76 %); clase 4: 2.747 (0,47 %); proporción ~1:103. Las clases 1 y 2 suman ~85 %. La métrica principal es macro F1 y los splits y la validación cruzada deben ser estratificados.

**Justificación:** el accuracy engaña (predecir siempre la clase 2 ya da ~49 %). En el EDA no se balanceó nada: solo se recomendó comparar pesos de clase y remuestreo (este solo sobre train).

**Explicación sencilla:** si el 85 % del examen es de dos temas, una buena nota general no prueba que sepas el resto.

**Evidencia:** issue #8 · PR #56 · `src/class_distribution.py` · `docs/figures/class_distribution.png` · `specs/feature-8-class-distribution.md`. Se aplicó en #16 (split, ver D1.3 y D1.4) y #19 (StratifiedKFold, ver D1.9).

**Responsable:** @Leandroletoile y equipo.

---

#### D2.3 · Qué variables separan las clases  (✅)

**Decisión:** medir cada variable numérica con **eta cuadrado** (η², la parte de su varianza explicada por la clase) y revisar correlaciones. `Elevation` 0,616; `Horizontal_Distance_To_Roadways` 0,096; `Slope` 0,074; `Horizontal_Distance_To_Fire_Points` 0,070; `Aspect` 0,005.

**Justificación:** da una primera jerarquía de variables. Límite reconocido: η² solo ve diferencias de medias, y las 44 binarias no se evaluaron contra la clase.

**Explicación sencilla:** le preguntamos a cada variable "¿cuánto cambias según el tipo de bosque?". La altitud respondió "muchísimo"; casi todas las demás, "poco".

**Evidencia:** issue #9 · PR #58 · `src/class_eda.py` · `docs/EDA.md` (Feature analysis) · `specs/feature-9-class-eda.md`.

**Responsable:** @Leandroletoile y equipo.

---

#### D2.4 · Distribuciones, atípicos y PCA  (✅)

**Decisión:** describir cada variable con asimetría, curtosis y regla del IQR, y proyectar con PCA. Ninguna es claramente normal. Más asimétricas: `Vertical_Distance_To_Hydrology` (1,79; curtosis 5,25), `Fire_Points` (1,29) y `Horizontal_Distance_To_Hydrology` (1,14). El IQR marca hasta 5,4 % de filas y **no se eliminó ningún atípico**. PCA: PC1 25,9 %, PC2 21,5 %; PC10 ≈ 0 %.

**Justificación:** con 581.012 filas los tests de normalidad rechazan cualquier dato real, así que no se usaron. Borrar sin evidencia podría quitar ejemplos de clases minoritarias.

**Explicación sencilla:** raro no es error: aquí los valores raros son terrenos poco comunes.

**Evidencia:** issue #10 · PR #59 · `src/statistical_insights.py` · `docs/figures/` · `specs/feature-10-statistical-insights.md`.

**Responsable:** @Leandroletoile y equipo.

---

#### D2.5 · Hallazgos y recomendaciones para M3  (✅)

**Decisión:** cerrar el EDA con una tabla de hallazgos y 5 recomendaciones, todas "por confirmar por el equipo": split y CV estratificados con macro F1; nada que imputar ni deduplicar; escalar solo para modelos lineales y de distancia; candidatas de feature engineering (seno/coseno de `Aspect`, distancia combinada al agua, redundancia de hillshade); verificar la dependencia lineal antes de quitar un hillshade.

**Justificación:** el EDA vale si alimenta decisiones posteriores. Se dejaron explícitas sus limitaciones.

**Explicación sencilla:** el EDA termina con una lista de tareas para la fase siguiente.

**Evidencia:** issue #11 · PR #61 · `docs/EDA.md` (Findings) · `specs/feature-11-document-eda-findings.md`. Descarga del dataset en el README (#60), correcciones en PR #62.

**Responsable:** @Leandroletoile y equipo.

---

# Paso 3 · Preprocesado

> **Idea en una frase:** preparar los datos para que el modelo pueda usarlos (rellenar huecos, escalar, codificar). **Regla de oro: se "ajusta" (fit) solo con train y luego se "aplica" (transform) a validación y test.**

**Opciones habituales:**

| Problema | Opciones |
|---|---|
| Nulos numéricos | Mediana, media, KNN imputer |
| Nulos categóricos | Moda o categoría "desconocido" |
| Categóricas | One-hot (pocas categorías), ordinal (si hay orden), target encoding (muchas, con cuidado) |
| Escala | StandardScaler o MinMaxScaler (necesario para regresión logística, SVM, KNN y redes; no para árboles) |
| Outliers | Dejarlos, recortar (*winsorizing*) o transformar con log |
| Asimetría | Log o Box-Cox / Yeo-Johnson |

**Preguntas de la guía:**

| Pregunta | Respuesta |
|---|---|
| ¿Mi modelo necesita este paso o lo maneja solo? | Los modelos lineales (`LogisticRegression`, #20) y las redes neuronales (`MLPClassifier`, #24) **sí necesitan escalado**; sin él la regresión logística ni siquiera converge en 1.000 iteraciones (macro F1 cae de 0,5257 a 0,3296). Los modelos de árboles (Random Forest, XGBoost, LightGBM) cortan por umbrales y **no necesitan escalado**. (D3.2) |
| ¿Estoy ajustando algo con datos que no debería ver (el test)? | No. `build_preprocessor()` devuelve el `ColumnTransformer` **sin ajustar** (*unfitted*) y se mete dentro de un `Pipeline` de scikit-learn, de modo que cada `fit` (en validación cruzada o en el entrenamiento final) calcula medias y desviaciones típicas **solo con `X_train`**. No se guardó ningún CSV preescalado en `data/processed/` precisamente para evitar ajustar antes del split. (D3.2) |
| ¿Imputar con la media distorsiona esta variable? | No aplica: el dataset tiene 0 nulos explícitos y 0 nulos encubiertos en los grupos one-hot. Para datos futuros en producción, `clean()` lanza error ante nulos en vez de inventar una imputación silenciosa. (D3.1) |

#### D3.1 · Verificación de nulos, ceros y duplicados  (✅)

**Decisión:** no imputar ni eliminar ninguna fila del dataset original (quedan las 581.012 filas intactas), y dejar la función defensiva `clean()` que elimina duplicados exactos y falla en voz alta (`ValueError`) si aparecen nulos en datos futuros.

**Justificación:** además de comprobar que hay 0 `NaN` y 0 filas duplicadas o contradictorias (mismas 54 variables con distinta clase), se comprobaron **nulos encubiertos**:
- En las 44 binarias: toda fila tiene exactamente una `Wilderness_Area` activa (suma = 1) y un `Soil_Type` activo (suma = 1).
- En las 10 numéricas: se contaron los ceros (`Vertical_Distance_To_Hydrology` tiene 38.665 ceros; `Horizontal_Distance_To_Hydrology`, 24.603; `Aspect`, 4.914; `Hillshade_3pm`, 1.338), pero **no son nulos disfrazados**, sino valores físicos válidos dentro del rango documentado (estar a 0 m del agua, orientación norte 0°, sombra total).

**Explicación sencilla:** antes de cocinar revisamos que no falte ningún ingrediente ni venga ninguno repetido. Como todo está limpio, no tocamos nada, pero dejamos un "detector" en la puerta por si en el futuro entran datos sucios desde la app.

**Evidencia:** issue #12 · PR #65 · `src/data_cleaning.py` (`missing_report`, `duplicate_report`, `clean`) · `docs/PREPROCESSING.md` (*Missing values and duplicates*) · `specs/feature-12-missing-values-duplicates.md`.

**Responsable:** @levifvy.

---

#### D3.2 · Escalado con `StandardScaler` solo en las 10 numéricas y dentro del `Pipeline`  (✅)

**Decisión:** escalar únicamente las 10 `NUMERIC_FEATURES` con `StandardScaler` y dejar pasar sin tocar (`"passthrough"`) las 44 `BINARY_FEATURES`, dentro de un `ColumnTransformer` sin ajustar (`build_preprocessor("standard")`) que se encadena en un `Pipeline`.

**Justificación:**
- **Por qué escalar:** las numéricas tienen escalas muy distintas (`Elevation` ronda 2.960 m con desviación 280; `Slope` ronda 14° con desviación 7,5). Sin escalar, `LogisticRegression` no converge en 1.000 iteraciones (macro F1 0,3296).
- **Por qué `StandardScaler`:** en una prueba sobre muestra estratificada de 60.000 filas con regresión logística, `StandardScaler` (macro F1 0,5257, converge en 233 iteraciones) y `RobustScaler` (0,5253, 182 iteraciones) empatan y superan a `MinMaxScaler` (0,4987, peor en clases minoritarias). `StandardScaler` es el estándar para modelos lineales regularizados y redes.
- **Por qué no tocar las 44 binarias ni el target:** las binarias ya valen 0 o 1; estandarizar un suelo raro (casi todo ceros) metería valores gigantes en los pocos unos y rompería su significado de indicador sí/no.
- **Sin fuga de datos (*no leakage*):** verificado con `check_scaling()`: tras ajustar en train, las numéricas de train tienen media 0 y desviación 1 exactas, mientras que en test las medias van de −0,0077 a +0,0030 y las desviaciones de 0,9970 a 1,0054 (prueba de que el test no se usó en el `fit`).

**Explicación sencilla:** si mezclas metros (miles) con grados (decenas), un modelo lineal se cree que los metros importan cien veces más solo porque el número es más grande. Poner las 10 medidas en la misma escala (media 0, paso 1) las iguala, pero calculando esa regla solo con los datos de estudio (`train`).

**Evidencia:** issue #14 · PR #66 · `src/feature_scaling.py` (`build_preprocessor`, `scale_train_test`, `check_scaling`, `compare_scalers`) · `docs/PREPROCESSING.md` (*Feature scaling*) · `specs/feature-14-feature-scaling.md`.

**Responsable:** @levifvy.

---

# Paso 4 · Feature engineering y selección

> **Idea en una frase:** crear variables nuevas más informativas (ratios, diferencias, combinaciones) y quitar las que sobran.

**Preguntas de la guía:**

| Pregunta | Respuesta |
|---|---|
| ¿Qué sabe un experto del dominio que el modelo no puede adivinar? | Que la altitud relativa al agua describe el terreno, y que `Aspect` es un ángulo. (D4.1) |
| ¿Puedo combinar variables (por ejemplo, distancia total a agua y carretera)? | Sí: las diferencias entre `Elevation` y las distancias al agua, y las sumas y diferencias de distancias, subieron el macro F1 en +0,0151 y +0,0282. (D4.2) |
| ¿Sobran variables? (constantes, muy correlacionadas, poco importantes) | No se quitó ninguna: con 20, 30 o 40 variables el resultado empeora. (D4.3) |
| ¿Cada nueva variable estará disponible al predecir en producción? | Sí. Las 8 nuevas usan solo `Elevation` y tres distancias, que la app pide. (D0.9) |

#### D4.1 · Candidatas de variables nuevas, por grupos  (✅)

**Decisión:** probar seis grupos de variables derivadas:
- `aspect_circular`: seno y coseno de `Aspect`.
- `hydrology_distance`: distancia combinada al agua.
- `hydrology_ratio`: cociente vertical/horizontal.
- `elevation_offsets`: `Elevation` menos las distancias al agua.
- `distance_combinations`: sumas y diferencias entre distancias.
- `category_ids`: un id de suelo y uno de zona en vez de 44 binarias.

**Justificación:** salen del EDA (`Aspect` es un ángulo, las distancias al agua se correlacionan) y del dominio. Probar por grupos permite saber qué idea funciona y cuál no.

**Explicación sencilla:** además de los datos crudos, le damos al modelo pistas ya calculadas.

**Evidencia:** issue #18 · PR #75 · `src/feature_engineering.py` (`FEATURE_GROUPS`).

**Responsable:** @Leandroletoile y equipo.

---

#### D4.2 · Regla de screening y grupos elegidos  (✅)

**Decisión:** un grupo se queda si mejora el macro F1 en ≥ 0,002 **y** más que la desviación estándar de la línea base. Validación cruzada estratificada de 5 folds (semilla 42) sobre train con XGBoost. Línea base: 0,8489 ± 0,0027.

| Grupo | Cambio en macro F1 | Resultado |
|---|---|---|
| `aspect_circular` | −0,0004 | descartado |
| `hydrology_distance` | −0,0018 | descartado |
| `hydrology_ratio` | +0,0013 | descartado |
| `elevation_offsets` | +0,0151 | **elegido** |
| `distance_combinations` | +0,0282 | **elegido** |
| `category_ids` | +0,0027 | descartado (en el límite) |
| todos juntos | +0,0389 | referencia |

**Justificación:** una regla fija escrita *antes* de mirar resultados evita elegir a gusto. Contra lo que sugería el EDA, el seno/coseno de `Aspect` y la distancia combinada al agua no ayudaron.

**Explicación sencilla:** una pista entra solo si mejora más que el ruido normal de repetir el examen.

**Evidencia:** PR #75 · `screen_groups`.

**Responsable:** @Leandroletoile y equipo.

---

#### D4.3 · No eliminar ninguna variable  (✅)

**Decisión:** conservar todas (54 originales + 8 nuevas = 62). Subconjuntos por importancia de ganancia, evaluados en validación: 20 → 0,7582; 30 → 0,8420; 40 → 0,8734; 62 → 0,8817.

**Justificación:** quitar variables empeoraba claramente. La importancia por ganancia favorece a las variables continuas, por eso no fue criterio único.

**Explicación sencilla:** probamos equipos más chicos y siempre rendía mejor el completo.

**Evidencia:** PR #75 · `rank_features`, `compare_subsets`.

**Responsable:** @Leandroletoile y equipo.

---

#### D4.4 · Confirmación con otra semilla y con validación  (✅)

**Decisión:** no fiarse de una sola corrida. CV con semilla 7: 0,8478 → 0,8865 (+0,0387). En validación (no usada para elegir): 0,8520 → 0,8817 (+0,0297). Las clases 5 y 6 ganan más (+0,056 y +0,053); la 4 baja un poco (−0,0050).

**Justificación:** la validación queda como chequeo independiente. No se usó el test.

**Explicación sencilla:** repetimos el examen con otro profesor y preguntas nuevas, y la mejora siguió.

**Evidencia:** PR #75 · `confirm_with_other_folds`, `holdout_check`.

**Responsable:** @Leandroletoile y equipo.

---

#### D4.5 · Las variables nuevas van antes del escalado  (✅)

**Decisión:** el feature engineering se aplica sobre datos crudos, **antes** del escalado y del recorte de atípicos. `build_preprocessor` (#14) y `build_outlier_preprocessor` (#13) usan `ColumnTransformer(remainder="drop")`, así que descartan las columnas nuevas si van antes (entran 62, salen 54). Se probó.

**Justificación:** las diferencias entre distancias tienen sentido solo en unidades originales.

**Explicación sencilla:** primero se calculan las pistas, después se cambian las unidades.

**Evidencia:** `docs/PREPROCESSING.md` · PR #75.

**Responsable:** @Leandroletoile y equipo.

---

#### D4.6 · Limitaciones e hipótesis sin probar  (🟡)

**Decisión:** dejar por escrito lo no demostrado:
- (a) Que los árboles construyan sumas y diferencias con dificultad es una hipótesis.
- (b) LightGBM fue errático con valores por defecto, así que se usó XGBoost y no se sabe si los grupos ayudan igual a otros modelos.
- (c) El experimento corrió con scikit-learn 1.9.1, xgboost 3.4.1 y pandas 3.1.1, distintos de `requirements.txt` (ver D10.5).

**Justificación:** cada resultado debe decir con qué modelo y entorno se obtuvo.

**Explicación sencilla:** sabemos que funciona con este modelo; falta ver si con los demás también.

**Evidencia:** PR #75 · spec del ticket.

**Responsable:** @Leandroletoile y equipo.

---

# Paso 5 · Baseline

> **Idea en una frase:** antes de usar modelos sofisticados, medir qué tal lo haría algo muy simple. Es la "vara de medir" mínima.

**Preguntas de la guía:**

| Pregunta | Respuesta |
|---|---|
| ¿Mi modelo complejo supera claramente al baseline? Si no, no compensa. | ⬜ |
| Si el dummy tiene un accuracy muy alto, ¿es que el problema está desbalanceado? | ⬜ (ver D0.4) |

#### D5.1 · (nombre de la decisión)  (⬜)

**Decisión:**

**Justificación:**

**Explicación sencilla:**

**Evidencia:**

**Responsable:**

---

# Paso 6 · Entrenamiento y validación

> **Idea en una frase:** probar varias familias de modelos y compararlas de forma justa con validación cruzada estratificada.

**Familias de modelos habituales:**

| Modelo | Dónde destaca |
|---|---|
| Regresión logística | Baseline, interpretable, datos lineales |
| Árbol de decisión | Interpretable, pero sobreajusta |
| Random Forest | Robusto, poco ajuste |
| Gradient Boosting (XGBoost, LightGBM) | Suele ganar en datos tabulares |
| SVM / KNN | Datasets pequeños o medianos |
| Redes neuronales | Imágenes, texto, audio o muchísimos datos |

**Si hay desbalanceo (de más simple a más complejo):**
1. `class_weight="balanced"`
2. Cambiar el umbral de decisión
3. Remuestreo (SMOTE, undersampling), **solo dentro de cada fold de train**, nunca antes del split

**Preguntas de la guía:**

| Pregunta | Respuesta |
|---|---|
| ¿La diferencia entre modelos es real o está dentro del ruido de la validación cruzada? | ⬜ |
| ¿Hay sobreajuste? (train muy alto, validación mucho más bajo) | ⬜ |
| ¿Hay subajuste? (ambos bajos) | ⬜ |
| ¿Necesitamos un modelo explicable? | ⬜ |

#### D6.1 · No aplicar class weights ni SMOTE (desbalanceo)  (✅)

**Decisión:** no aplicar ninguna técnica de desbalanceo: los modelos de árbol del shortlist (Random Forest y XGBoost) ya manejan bien el desbalance por sí solos.

**Justificación:** se probaron pesos de clase inversos ("balanced") sobre Random Forest y XGBoost con validación cruzada de 5 folds. Random Forest: macro F1 casi idéntico (0,9123 → 0,9103, dentro del ruido) y accuracy baja 1,08 puntos. XGBoost: macro F1 baja claramente (0,8489 → 0,8005). El peso de la clase 4 llega a ×30 y sobrecorrige: cambia precision por recall sin ganancia neta. SMOTE se descarta además por añadir la dependencia `imbalanced-learn` y crear muestras sintéticas que pueden sobreajustar los árboles. El issue era condicional ("if needed"), así que la estrategia aplicada es **ninguna**.

**Explicación sencilla:** una clase puede ser *rara* pero *fácil de reconocer*. Cottonwood/Willow (0,47 %) crece junto al agua a poca altitud, y Random Forest la acierta con F1 0,87 sin ninguna ayuda. Dar más peso a las clases raras hizo que el modelo "gritara" más veces "¡Cottonwood!", pero también que se equivocara más llamando Cottonwood a árboles que no lo eran. El balance final (macro F1) no mejoró, así que no compensa.

**Evidencia:** issue #17 · `src/imbalance_handling.py` · `docs/PREPROCESSING.md` (sección *Imbalance handling*) · `specs/feature-17-m3-imbalance-handling.md`.

**Responsable:** @nagicome03.

---

#### D6.2 · Modelo supervisado simple: Regresión Logística multinomial  (✅)

**Decisión:** entrenar un `Pipeline` con `build_preprocessor("standard")` (#14) + `LogisticRegression(max_iter=1000, random_state=42)` (pérdida multinomial, regularización L2 con `C=1.0`) sobre las 406.708 filas del train canónico (#16) bajo el protocolo común de 5 folds estratificados (#19).

**Justificación:** antes de pasar a árboles complejos o redes, hace falta una referencia supervisada lineal que supere claramente a los `DummyClassifier` (macro F1 0,0937 y 0,1426).
- **Resultado (5-fold CV en train):** accuracy **0,7248 ± 0,0008**, macro F1 **0,5324 ± 0,0037** (converge en 223–269 iteraciones por fold, muy por debajo de `max_iter=1000`).
- **Lectura por clase:** separa de forma aceptable las clases mayoritarias (F1 de 0,7047 en Spruce/Fir y 0,7736 en Lodgepole Pine), pero fracasa en las minoritarias que no son linealmente separables: **Aspen (clase 5) tiene recall 0,0063 y F1 0,0123**, y Douglas-fir (clase 6) tiene F1 0,3480. Esto demuestra que hacen falta fronteras de decisión no lineales.

**Explicación sencilla:** la regresión logística intenta separar los tipos de bosque trazando "líneas rectas". Supera de largo a adivinar al azar (sube el macro F1 de 0,14 a 0,53), pero como en la naturaleza los bosques no se separan con líneas rectas, casi nunca detecta el álamo temblón (*Aspen*). Sirve como suelo supervisado que los modelos potentes deben batir.

**Evidencia:** issue #20 · PR #73 · `src/logistic_regression.py` · `docs/MODELING.md` (*Simple model: Logistic Regression*) · `specs/feature-20-train-logistic-regression.md`.

**Responsable:** @levifvy.

---

#### D6.3 · Red neuronal: Perceptrón Multicapa (MLP) con *early stopping*  (✅)

**Decisión:** entrenar un `Pipeline` con `build_preprocessor("standard")` (#14) + `MLPClassifier(hidden_layer_sizes=(128, 64), batch_size=512, max_iter=200, early_stopping=True, validation_fraction=0.1, n_iter_no_change=10, random_state=42)` sobre el train canónico (#16) con el protocolo de 5 folds (#19).

**Justificación:**
- **Por qué MLP y no CNN:** el enunciado pide "CNN si el dataset es visual"; como Covertype es tabular (54 columnas cartográficas), corresponde una red densa (MLP) con dos capas ocultas ReLU (128 y 64 neuronas) y salida *softmax* de 7 clases. Usamos scikit-learn para no añadir dependencias pesadas (PyTorch/TensorFlow).
- **Control del sobreajuste sin fuga de datos:** `early_stopping=True` separa internamente un 10 % estratificado **de las propias filas de entrenamiento de cada fold** y detiene el entrenamiento tras 10 épocas sin mejora (en el train completo paró en la época 99 de 200). Ni la validación ni el test del proyecto se tocan.
- **Resultado (5-fold CV en train):** accuracy **0,9035 ± 0,0049**, macro F1 **0,8557 ± 0,0090**.
- **Comparación con ensembles:** supera en macro F1 a XGBoost (0,8514) y LightGBM (0,8261) en el mismo split y les saca +3,4 puntos de accuracy porque distingue mejor las dos clases mayoritarias, pero queda por detrás de Random Forest (macro F1 0,9124) y tarda ~1 hora en CV (≈10 minutos por ajuste en CPU).

**Explicación sencilla:** una red neuronal conecta dos capas de "neuronas" artificiales que sí pueden dibujar fronteras curvas complejas. Para que no memorice los datos, vigila un 10 % interno de su propio entrenamiento y frena sola cuando deja de mejorar (en la vuelta 99 de 200). Queda segunda de todos los modelos probados, empatada en la práctica con XGBoost pero bastante más lenta de entrenar.

**Evidencia:** issue #24 · PR #74 · `src/neural_network.py` · `docs/MODELING.md` (*Neural network (MLP)*) · `specs/feature-24-neural-network-mlp.md`.

**Responsable:** @levifvy.

---

# Paso 7 · Ajuste de hiperparámetros

> **Idea en una frase:** probar distintas "configuraciones" del modelo para ver cuál rinde mejor, siempre con validación cruzada y **sin mirar el test**.

**Herramientas:** `GridSearchCV` (pocos parámetros), `RandomizedSearchCV` u `Optuna` (muchos).

**Preguntas de la guía:**

| Pregunta | Respuesta |
|---|---|
| ¿Vale la pena el tiempo? (suele mejorar menos que tener buenos datos y buenas variables) | ✅ Sí: Random Forest +2,0 pp y XGBoost +7,5 pp de macro F1, ambos más estables (D7.1) |
| ¿Estamos sobreajustando a la validación de tanto probar combinaciones? | ✅ Se reconoce el sesgo: la búsqueda elige la mejor combinación sobre los mismos folds, así que el número afinado es optimista; el veredicto imparcial lo dan #28 (validación) y #25 (test) (D7.1) |

#### D7.1 · Afinar Random Forest y XGBoost con RandomizedSearchCV  (✅)

**Decisión:** afinar los dos modelos del shortlist (Random Forest primario, XGBoost secundario) con `RandomizedSearchCV` bajo el protocolo común (5 folds estratificados, macro F1), sobre el train canónico y sin tocar validación ni test.

**Justificación:**
- **Método `RandomizedSearchCV`:** sin dependencia nueva (`Optuna` se descarta) y con presupuesto controlable; `GridSearchCV` sería combinatoriamente demasiado lento para Random Forest en 406.708 filas.
- **Presupuesto rápido:** Random Forest `n_iter=10` y XGBoost `n_iter=30` (se redujo del exhaustivo 40/50 para no esperar horas).
- **Resultado (5-fold CV, macro F1):**
  - Random Forest: **0,9123 → 0,9326** (+2,0 puntos) y más estable (std 0,0029 → 0,0019).
  - XGBoost: **0,8489 → 0,9240** (+7,5 puntos) y más estable (std 0,0027 → 0,0016).
- **Mejores parámetros:** RF `n_estimators=400, max_depth=50, min_samples_leaf=1, min_samples_split=5, max_features=None`; XGBoost `learning_rate=0.05, n_estimators=300, max_depth=12, subsample=0.8, colsample_bytree=0.8, min_child_weight=3, reg_lambda=0, reg_alpha=1`.
- **Sin fuga:** la búsqueda solo ajusta sobre `X_train`/`y_train`; el número afinado es un pelín optimista (elegimos la mejor combinación sobre esos folds) — el veredicto imparcial lo dan #28 (validación) y #25 (test).

**Explicación sencilla:** el modelo por defecto ya iba bien, pero venía "de fábrica". Probar varias configuraciones y quedarnos con la mejor fue como ajustar los mandos: Random Forest ganó 2 puntos de macro F1 usando más árboles (400) y dejando que cada árbol evalúe las 54 variables (`max_features=None`) en vez de una muestra; el tope de profundidad 50 apenas recorta los árboles con 406 mil filas, así que la mejora se atribuye a las variables como hipótesis (la búsqueda no aísla qué parámetro la causó). XGBoost subió 7,5 puntos, pero partía de un default flojo (0,8489), así que conviene no sobrevenderlo. Ambos quedaron además más estables entre los distintos pliegues.

**Evidencia:** issue #29 · `src/hyperparameter_optimization.py` · `docs/MODELING.md` (*Hyperparameter optimization*) · `specs/feature-29-m5-hyperparameter-optimization-gridsearchcv-randomizedsearch-optuna.md`.

**Responsable:** @nagicome03.

---

# Paso 8 · Evaluación final

> **Idea en una frase:** con el mejor modelo ya elegido, hacer **una sola vez** el examen en el conjunto de test.

**Qué métrica usar y cuándo:**

| Métrica | Úsala cuando |
|---|---|
| Accuracy | Clases balanceadas |
| Precision | Los falsos positivos duelen |
| Recall | Los falsos negativos duelen |
| F1 | Quieres equilibrio entre precision y recall |
| ROC-AUC | Comparar modelos sin fijar umbral |
| PR-AUC | Clases muy desbalanceadas |
| Matriz de confusión | Siempre, para ver dónde se equivoca |

**Preguntas de la guía:**

| Pregunta | Respuesta |
|---|---|
| ¿La métrica coincide con la definida en el Paso 0 (macro F1)? | Sí: se reporta **macro F1** como métrica principal (0,9186 en validación y **0,9199 en test**), junto con accuracy, precision/recall/F1 por clase y la matriz de confusión 7×7 (en conteos y en % por fila). (D8.1) |
| ¿Rinde igual en todos los subgrupos? ¿Hay sesgo? | Rinde muy alto en las clases mayoritarias y alpinas (F1 en test: 0,9584 en Lodgepole Pine, 0,9559 en Krummholz, 0,9497 en Spruce/Fir) y algo más bajo en **Aspen** (clase 5, F1 0,8410, recall 75,56 %, que se confunde un 21,77 % de las veces con Lodgepole Pine) y **Cottonwood/Willow** (clase 4, F1 0,8767, recall 85,44 %, confundida un 12,14 % con Ponderosa Pine). (D8.1) |
| ¿El resultado en test es parecido al de validación? Si cae mucho, hubo fuga u overfitting. | Es prácticamente idéntico: validación da accuracy **0,9520** y macro F1 **0,9186**; el conjunto de test (87.152 filas nunca vistas) da accuracy **0,9510** (−0,10 pp) y macro F1 **0,9199** (+0,13 pp). No hay caída en test. (D8.1) |
| ¿Se cumple overfitting < 5 %? | Sí: la diferencia de accuracy entre train (1,0000) y validación (0,9520) es **+0,0480 (+4,80 puntos porcentuales)**, por debajo del límite del 5 %. (D8.1; cierre formal en #28) |

#### D8.1 · Métricas finales y matriz de confusión en validación y test  (✅)

**Decisión:** evaluar el pipeline primario del shortlist (`RandomForestClassifier` de 100 árboles, ajustado exclusivamente sobre las 406.708 filas de `train`) sobre las particiones de `validation` (87.152 filas) y `test` (87.152 filas), registrando las métricas globales, las métricas por clase y las matrices de confusión 7×7 en conteos absolutos y en porcentaje normalizado por fila.

| Partición | Filas | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) |
|---|---:|---:|---:|---:|---:|
| `train` | 406.708 | 1,0000 | 1,0000 | 1,0000 | 1,0000 |
| `validation` | 87.152 | 0,9520 | 0,9416 | 0,8990 | 0,9186 |
| `test` | 87.152 | 0,9510 | 0,9423 | 0,9012 | **0,9199** |

**Métricas por clase en `test` (87.152 filas):**

| `Cover_Type` | Clase | Precision | Recall | F1 | Soporte |
|---|---|---:|---:|---:|---:|
| 1 | Spruce/Fir | 0,9621 | 0,9376 | 0,9497 | 31.776 |
| 2 | Lodgepole Pine | 0,9454 | 0,9718 | 0,9584 | 42.495 |
| 3 | Ponderosa Pine | 0,9340 | 0,9627 | 0,9481 | 5.363 |
| 4 | Cottonwood/Willow | 0,9003 | 0,8544 | 0,8767 | 412 |
| 5 | Aspen | 0,9480 | 0,7556 | 0,8410 | 1.424 |
| 6 | Douglas-fir | 0,9380 | 0,8825 | 0,9094 | 2.605 |
| 7 | Krummholz | 0,9686 | 0,9435 | 0,9559 | 3.077 |

**Justificación:**
- **Sin fuga de datos:** el modelo se entrena una sola vez con `(X_train, y_train)` a través de `export_model.fit_pipeline`. `validation` y `test` solo pasan por `.predict()`.
- **Doble vista de la matriz de confusión:** con un desbalanceo 1:103, la matriz en conteos muestra dónde está el mayor volumen de errores (la confusión cruzada entre las dos clases gigantes, 1.895 filas de Spruce/Fir predichas como Lodgepole Pine y 997 al revés), mientras que la matriz normalizada por fila (% de recall) revela qué clases pequeñas se escapan más (el 21,77 % de Aspen se predice como Lodgepole Pine y el 12,14 % de Cottonwood/Willow como Ponderosa Pine), dejando la base lista para el análisis de errores (#27).
- **Gap de sobreajuste:** `train (1,0000) - validation (0,9520) = +0,0480` (+4,80 pp < 5 %).

**Explicación sencilla:** una vez elegido el mejor modelo, le hacemos el simulacro (`validation`) y el examen final (`test`) con 87.152 parcelas nuevas cada uno. En ambos acierta el 95 % de las parcelas y supera el 0,91 de nota media por clase (macro F1), demostrando que aprendió patrones reales del bosque y no solo de memoria.

**Evidencia:** issue #25 · `src/final_metrics.py` (`python src/final_metrics.py`) · `docs/MODELING.md` (*Results*) · `specs/feature-25-compute-final-metrics.md`.

**Responsable:** @levifvy.

---

# Paso 9 · Análisis de errores e interpretación

> **Idea en una frase:** mirar **dónde y por qué** se equivoca el modelo, y comprobar que se apoya en variables con sentido.

**Preguntas de la guía:**

| Pregunta | Respuesta |
|---|---|
| ¿Los casos mal clasificados tienen algo en común? | ✅ Sí. En validación hay 4.180 errores y el 66,9 % es la confusión entre Spruce/Fir y Lodgepole Pine. Cada clase minoritaria pierde casi siempre contra una sola vecina (Aspen → Lodgepole Pine, 87,9 % de sus errores). Los errores tienen menos confianza (media 0,624 frente a 0,889 en los aciertos). Ver D9.1. |
| ¿El modelo se apoya en variables que tienen sentido? (importancia de variables, SHAP) | ✅ `Elevation` domina en la importancia por impureza, por permutación y en el SHAP aproximado; después vienen las distancias a carreteras, a puntos de fuego y a hidrología. Es coherente con que la altitud separa especies, pero el SHAP es una aproximación (ver D9.2). |
| ¿Aprendió algo absurdo? | 🟡 No vimos nada absurdo en lo revisado: el efecto de `Elevation` sobre Lodgepole Pine es positivo entre unos 2.500 y 3.000 m y negativo fuera de ese rango, coherente con el solape de altitudes con Spruce/Fir. Falta que lo revise alguien con conocimiento del dominio. |
| ¿Qué datos adicionales ayudarían a corregir los errores? | 🟡 Las propuestas de #27 son afinar la frontera Spruce/Fir→Lodgepole (ajuste de hiperparámetros, variables nuevas), tratar por pareja a las clases minoritarias y mostrar la confianza en la app. Ninguna está probada todavía; datos nuevos por decidir. |

#### D9.1 · Dónde se equivoca el modelo (análisis de errores)  (✅)

**Decisión:** analizar los errores del modelo exportado (#32, Random Forest ajustado solo con `train`) sobre la partición de **validación** (87.152 filas, 4.180 errores), con `python src/error_analysis.py`. Se miran tres cosas: los pares de clases más confundidos, el contraste de `Elevation` en el par dominante y la confianza (`predict_proba` máximo) de aciertos y errores. Los resultados y tres propuestas de mejora están en `docs/MODELING.md` (*Error analysis*).

**Justificación:** la métrica global (macro F1 0,9186) no dice dónde falla. Saber que dos tercios de los errores están en una sola frontera permite dirigir el trabajo (ajuste, variables nuevas) en lugar de mejorar a ciegas.

**Explicación sencilla:** en vez de mirar la nota media del examen, se miran las preguntas falladas: casi todas son del mismo tema, distinguir dos especies parecidas que viven a altitudes parecidas.

**Evidencia:** issue #27 · PR #96 · `src/error_analysis.py` · `docs/figures/error_analysis.png` · `docs/MODELING.md` · `specs/feature-27-m5-error-analysis.md`. Spruce/Fir → Lodgepole Pine son 1.852 errores y Lodgepole Pine → Spruce/Fir 943: 2.795 de 4.180 (66,9 %). Los Spruce/Fir mal clasificados tienen una altitud media de 2.941 m, casi la de Lodgepole Pine (2.920 m), frente a 3.139 m en los Spruce/Fir acertados. Los errores se concentran cerca de una confianza de 0,5 a 0,65, pero queda una cola de errores seguros (por ejemplo Krummholz → Spruce/Fir con 0,98). Las propuestas son diagnóstico: aplicarlas no era parte del ticket.

**Responsable:** @carovasq.

---

#### D9.2 · Interpretación con SHAP aproximado  (🟡)

**Decisión:** calcular SHAP sobre 2.000 filas de validación (`random_state=42`) con `shap.TreeExplainer` en modo aproximado (atribución de Saabas), con `python src/shap_interpretability.py`, y guardar tres figuras: barras de importancia, *beeswarm* de Lodgepole Pine y dependencia de `Elevation`. Se fija `shap==0.49.1`, la última versión compatible con `numpy==1.26.4`.

**Justificación:** SHAP añade el **signo** y la **clase** a las importancias de #26. El SHAP exacto tarda unos 3 s por fila en este bosque (profundidad máxima 64), es decir, horas para una muestra útil; la versión aproximada es inmediata. Queda parcial porque la aproximación no es SHAP exacto y no se comparó con él: las tres primeras variables coinciden con la importancia por permutación (#26), pero eso no basta como prueba.

**Explicación sencilla:** la importancia dice qué variables pesan; SHAP dice además hacia qué clase empujan y cuánto, caso por caso. Usamos un cálculo rápido y aproximado: sirve para ver la tendencia, no para fiarse de cada decimal.

**Evidencia:** issue #30 · PR #99 · `src/shap_interpretability.py` · `docs/figures/shap_summary_bar.png`, `shap_beeswarm.png` y `shap_dependence_elevation.png` · `docs/MODELING.md` (*Model interpretability (SHAP)*) · `specs/feature-30-m5-model-interpretability-shap.md`. `Elevation` tiene un SHAP medio de 0,0618, unas 2,5 veces el de `Horizontal_Distance_To_Roadways` (0,0242); le siguen los puntos de fuego (0,0202) y la hidrología. Para Lodgepole Pine el efecto de `Elevation` es positivo entre unos 2.500 y 3.000 m y negativo por encima y por debajo.

**Responsable:** @carovasq.

---

# Paso 10 · Despliegue y monitoreo

> **Idea en una frase:** poner el modelo a disposición de otras personas (nuestra app) y vigilar que siga funcionando bien con el tiempo.

**Qué hacer:**
- Guardar el **pipeline completo** (preprocesado + modelo) con `joblib`, no solo el modelo.
- Exponerlo como app (Streamlit) y/o API (FastAPI).
- Vigilar el *data drift* y el rendimiento en el tiempo.

**Preguntas de la guía:**

| Pregunta | Respuesta |
|---|---|
| ¿Cómo sabremos que el modelo empezó a fallar? | 🟡 Cada predicción de `POST /predict` se guarda en la base de datos (tabla `predictions`, #37) y `GET /health` informa si el modelo y la base están disponibles. Con `POST /feedback` se registra la clase real de una predicción y `GET /metrics` calcula con ese feedback la exactitud en vivo, la cobertura, la confianza media y la exactitud por clase (#35). Falta la detección de *data drift* y una alerta automática. |
| ¿Cada cuánto hay que reentrenar? | ⬜ Por decidir. |
| ¿Qué pasa si el modelo se equivoca? ¿Hay revisión humana? | La API devuelve `confidence` y las probabilidades de las 7 clases, para que una persona revise los casos dudosos. La revisión humana no está implementada. ⬜ |

#### D10.1 · API con FastAPI: predicción y estado  (✅)

**Decisión:** exponer el modelo con FastAPI en `app/api.py`: `GET /health` (`status`, `model_loaded`, `db_connected`, `detail`, `db_detail`) y `POST /predict`, que devuelve `cover_type` (1–7), `class_name`, `confidence`, `probabilities` y `prediction_id` (la fila guardada en la base de datos, #37; `null` si la base no está disponible). Desde #35 la API tiene además `POST /feedback` y `GET /metrics` (ver D10.7).

**Justificación:** separar el modelo de la interfaz permite que la app, scripts o cualquier cliente lo usen igual. `/health` permite comprobar el servicio sin predecir.

**Explicación sencilla:** una ventanilla: entra el formulario con los datos del terreno y sale el tipo de bosque, con qué tan seguro está el modelo.

**Evidencia:** issue #34 · PRs #81 y #90 · `app/api.py`, `app/serving.py`, `app/schemas.py` · `docs/APP.md`.

**Responsable:** @Leandroletoile y equipo.

---

#### D10.2 · Validación de la entrada  (✅)

**Decisión:** Pydantic valida cada campo con el nombre del dataset y un rango:

| Campo | Rango |
|---|---|
| `Elevation` | 0–5000 |
| `Aspect` | 0–360 |
| `Slope` | 0–90 |
| `Hillshade_*` | 0–255 |
| Distancias horizontales | 0–10000 |
| `Vertical_Distance_To_Hydrology` | −500–1000 |
| Zona silvestre | 1–4 |
| Suelo | 1–40 |

La zona y el suelo se convierten a las 44 columnas binarias. Los campos desconocidos se rechazan. Entrada inválida → código 422.

**Justificación:** nadie debería escribir 44 ceros y unos, y un valor imposible no debe llegar al modelo. Los rangos son un límite de seguridad, no una garantía de realismo.

**Explicación sencilla:** un formulario que no deja enviar una pendiente de 400 grados.

**Evidencia:** PR #81 · `PredictionRequest` en `app/schemas.py`. Probado a mano con 200 y 422.

**Responsable:** @Leandroletoile y equipo.

---

#### D10.3 · Contrato y exportación del pipeline del modelo  (✅)

**Decisión:**
1. **Contrato de carga (#34):** la API carga `models/model.joblib` (ruta cambiable con `MODEL_PATH`), que debe recibir las 54 variables crudas en el orden de entrenamiento (`feature_names_in_ == FEATURES`), exponer `predict_proba` y `classes_`, y devolver etiquetas `1–7` (o `0–6`). Si el fichero falta o no cumple, la API arranca igual, `/health` informa `model_loaded: false` y `/predict` responde 503.
2. **Exportación reproducible (#32):** `python src/export_model.py` entrena exclusivamente sobre `X_train, y_train` (406.708 filas) un `Pipeline` formado por un `ColumnTransformer` passthrough de las 54 `FEATURES` y el modelo primario del shortlist (`RandomForestClassifier(n_estimators=100, random_state=42)`), manteniendo las clases originales **`Cover_Type` de `1–7`**. Serializa el pipeline en `models/model.joblib` (`joblib.dump(..., compress=3)`, 136,3 MB) junto con `models/model_metadata.json` (versión `0.1.0`, fecha UTC, SHA-256 del binario, versiones de librerías, métricas en validación —accuracy 0,9520, macro F1 0,9186— y el mapeo `índice de predict_proba -> Cover_Type 1..7 -> nombre de especie`). Al terminar, ejecuta `check_contract()`, que carga el fichero con `app.serving.load_model()` y comprueba que las probabilidades coinciden exactamente con las del pipeline en memoria.

**Justificación:** separar el contrato (#34) del script de exportación (#32) permitió construir la API sin bloquearse, y comprobar el contrato automáticamente al final de `export_model.py` garantiza que el artefacto generado nunca rompe la API. No se sube `.joblib` a Git (`.gitignore`): cualquiera lo regenera con un comando y el SHA-256 de `model_metadata.json` ata los metadatos al fichero exacto.

**Explicación sencilla:** la API es el enchufe y el modelo es el aparato. En #34 definimos la forma del enchufe y en #32 empaquetamos el modelo definitivo dentro de su caja (`model.joblib`) con su etiqueta de fábrica (`model_metadata.json`), probando que al enchufarlo enciende a la primera.

**Evidencia:** issues #34 y #32 · PRs #81 y #85 · `src/export_model.py`, `app/serving.py` · `docs/APP.md` (*Model export*) · `specs/feature-32-export-model-pipeline.md`.

**Responsable:** @Leandroletoile (#34) y @levifvy (#32).

---

#### D10.4 · Integración continua con GitHub Actions  (✅)

**Decisión:** `.github/workflows/ci.yml` corre en cada push y PR con dos trabajos:
1. Instala las dependencias fijadas en Python 3.11, ejecuta `scripts/check_imports.py` (importa todos los módulos de `src/` y `app/`) y corre `pytest` solo si hay tests.
2. Construye la imagen Docker sin publicarla.

Todavía no hay despliegue automático (CD).

**Justificación:** con ramas paralelas, una comprobación automática detecta antes de fusionar un import roto, una dependencia mal fijada o un Dockerfile que no construye. Hay pocos tests, así que el chequeo de imports es la red mínima.

**Explicación sencilla:** un revisor automático que comprueba que el proyecto sigue arrancando.

**Evidencia:** issue #41 · `.github/workflows/ci.yml` · `specs/feature-41-ci-cd-pipeline.md`. Observado el 16-nov-2026: la CI corre en cada PR y en cada push a `develop`; en `develop` (commit `54f2d74`, CI #18) los dos trabajos están en verde con las versiones fijadas de `requirements.txt` (Python 3.11). Queda sin comprobar el cuarto criterio de la spec: que un cambio que rompa un import haga fallar el check.

**Responsable:** @Leandroletoile y equipo.

---

#### D10.5 · Entorno local distinto del fijado  (🟡)

**Decisión:** reconocer la diferencia entre lo que usamos en local y lo que fija `requirements.txt`:

| Librería | Local | `requirements.txt` |
|---|---|---|
| scikit-learn | 1.9.1 | 1.5.1 |
| xgboost | 3.4.1 | 2.1.1 |
| lightgbm | 4.7.0 | 4.5.0 |
| pandas | 3.1.1 | 2.2.2 |
| fastapi | 0.162.5 | 0.112.2 |
| numpy | — | 1.26.4 |

Además, `pydantic` y `scipy` no estaban fijados. Desde #46 lo están (`pydantic==2.14.3`, `scipy==1.17.1`, las versiones que resuelve hoy una construcción limpia de Docker, las mismas que instala la CI), y la prueba de clon limpio pasa con ellas. Lo que sigue pendiente es decidir si se alinea el entorno local con el fijado.

**Justificación:** un modelo guardado con `joblib` en una versión puede fallar al abrirse en otra. Conviene entrenar y servir en el mismo entorno (el Docker).

**Explicación sencilla:** la receta fija una versión de cada ingrediente, pero cada uno cocina con la que tiene en casa.

**Evidencia:** `requirements.txt` · `pip list` de cada equipo.

**Responsable:** equipo (decidir si se fijan las versiones al entorno real o se mantienen).

---

#### D10.6 · Reproducibilidad: versiones fijadas y pasos de ejecución  (✅)

**Decisión:** dejar `requirements.txt` con todas las librerías que usa el código fijadas con `==` (se agregaron `pydantic` y `scipy`), documentar cómo ejecutar el proyecto con Docker y sin Docker en `docs/REPRODUCIBILITY.md`, y comprobarlo desde un clon limpio.

**Justificación:**
- **Solo lo que faltaba:** las librerías directas ya estaban fijadas; los huecos eran `pydantic` (lo importa el código y FastAPI solo lo acota por debajo de 3) y `scipy` (lo necesita scikit-learn y no tiene tope). Un fichero de bloqueo completo sería un segundo archivo que mantener; se puede añadir si aparece deriva.
- **Python 3.11 es la referencia** (Docker, CI y `.python-version`). La 3.12 funciona (la exportación de #32 corrió en ella); la 3.13 no, porque `numpy` 1.26.4 y `scikit-learn` 1.5.1 no tienen ruedas para ella.
- **El primer intento de clon limpio falló:** el puerto 3306 de un equipo estaba ocupado por un MySQL local. Se hizo configurable (`MYSQL_PORT`, por defecto 3306) en `docker-compose.yml` y `.env.example`.
- **Resultado de la prueba:** la imagen se construye con los pines nuevos; los 24 módulos importan; la exportación da accuracy 0,9520 y macro F1 0,9186; `/health` informa modelo y base de datos conectados; `/predict` devuelve `cover_type` 2 con confianza 0,95.
- **Límites conocidos:** el dataset se descarga a mano; el modelo se entrena en cada clon (no está en Git); la app de Streamlit sigue siendo el placeholder de M0 y no se abrió en el navegador durante la prueba.

**Explicación sencilla:** una receta que dice la versión exacta de cada ingrediente y los pasos para cocinarla. Para saber si funciona, la cocinamos en una cocina vacía.

**Evidencia:** issue #46 · `requirements.txt` · `docs/REPRODUCIBILITY.md` · `specs/feature-46-reproducibility-requirements-run-steps.md`.

**Responsable:** @Leandroletoile y equipo.

---

#### D10.7 · Feedback y métricas de producción  (✅)

**Decisión:** añadir a la API `POST /feedback`, que recibe `prediction_id`, `true_cover_type` (1 a 7) y un `comment` opcional y guarda la clase real, y `GET /metrics`, que devuelve el número de predicciones y de feedbacks, la cobertura del feedback, la exactitud medida sobre el feedback (`live_accuracy`), la confianza media y la exactitud por clase. Un `prediction_id` que no existe da 404, una clase fuera de 1 a 7 da 422 y una base de datos caída da 503. Sin datos, las proporciones salen `null` en lugar de dar error.

**Justificación:** sin la clase real no se puede saber si el modelo acierta en producción. Se reutilizó el almacenamiento de #37 y solo se añadió la lectura agregada (`feedback_metrics()`), con consultas que funcionan igual en SQLite y en MySQL. La interfaz que llame a estos endpoints no forma parte de este ticket.

**Explicación sencilla:** un buzón para decir "la respuesta correcta era esta" y un marcador que cuenta cuántas veces acertó el modelo según esas respuestas.

**Evidencia:** issue #35 · PR #102 · `app/api.py`, `app/schemas.py`, `src/database.py` · `docs/APP.md` · `specs/feature-35-m6-feedback-collection-system.md` (la spec indica que `python src/database.py` comprueba `feedback_metrics()`).

**Responsable:** @carovasq.

---

#### D10.8 · Guía de uso de Docker  (✅)

**Decisión:** reunir en `docs/DOCKER.md` lo necesario para ejecutar el proyecto con Docker Compose: arranque rápido, qué hace cada servicio (`api`, `app`, `db`) y cada volumen, variables de entorno, la imagen, comandos habituales, una tabla de problemas y soluciones, y los límites conocidos. Se enlaza desde `README.md` y `docs/REPRODUCIBILITY.md`.

**Justificación:** los fallos que encontramos al probar desde cero eran de entorno y no de código: Docker Desktop apagado, el puerto 3306 ocupado por un MySQL local (se resuelve con `MYSQL_PORT=3307`, #46), un nombre de contenedor ya usado por otra copia del proyecto, o `exec` sobre un servicio que no arrancó. Dejarlos escritos con su mensaje de error evita repetir el diagnóstico.

**Explicación sencilla:** el manual de la caja: qué hay dentro, cómo se enciende y qué mirar cuando una luz se pone roja.

**Evidencia:** issue #47 · PR #100 · `docs/DOCKER.md` · `specs/feature-47-docker-compose-usage-docs.md`. Probado en Windows con Docker Desktop (Compose v5.5.1): `docker compose up -d --build` levantó `app` y `db` (healthy en 16 s) con los puertos 8501 y 3307, `src/database.py` pasó dentro del contenedor y una segunda copia de la pila falló con el conflicto de nombre que recoge la tabla. Las filas que describen el comportamiento estándar de Docker no se ejecutaron (la spec las lista).

**Responsable:** @Leandroletoile y equipo.

---

#### D10.9 · Orquestación con Docker Compose: API y frontend como servicios  (✅)

**Decisión:** añadir a `docker-compose.yml` el servicio `api` (`uvicorn app.api:app` en el puerto 8000) junto a `app` (Streamlit, 8501) y `db`. Los dos primeros comparten la misma imagen y solo cambia el comando. El arranque se ordena con healthchecks: `api` espera a `db` y `app` espera a que `api` esté healthy. `./models` se monta en solo lectura en `api` y escribible en `app`, que es donde se ejecutan la exportación y el reentrenamiento.

**Justificación:** así `docker compose up` levanta toda la aplicación sin pasos manuales, y una sola imagen evita mantener dos Dockerfile. Limitación: la API carga el modelo solo al arrancar, por eso tras exportar un modelo nuevo hay que ejecutar `docker compose restart api` y esperar a que esté healthy (20 a 40 segundos). Las páginas de Docker se actualizaron para reflejarlo.

**Explicación sencilla:** antes había que encender la API a mano en una segunda terminal; ahora arranca sola, y la pantalla espera a que la API esté lista.

**Evidencia:** issue #38 · PR #104 y PR #105 (correcciones de revisión) · `docker-compose.yml`, `Dockerfile`, `.env.example`, `docs/APP.md` · `specs/feature-38-m6-dockerize-application.md` · `specs/docs-compose-api-service.md`. Probado en Windows con Docker Desktop: con el modelo ya exportado, `docker compose up -d` levantó los tres servicios en 29 s (`db` healthy a los 6,6 s y `api` a los 27,3 s), `GET /health` devolvió `model_loaded: true` y `db_connected: true`, y `POST /predict` con el ejemplo de `docs/APP.md` devolvió la clase 2 (Lodgepole Pine, confianza 0,95). Sin modelo, `/health` da `model_loaded: false` y, tras exportar, sigue igual hasta reiniciar `api`.

**Responsable:** @carovasq.

---

#### D10.10 · Test A/B entre dos modelos  (✅)

**Decisión:** comparar en producción dos modelos con un test A/B. A (control) es el Random Forest 0.1.0 sin ajustar y B (challenger) es el XGBoost 0.2.0 ajustado en #29, exportado a `models/model_b.joblib` con `src/export_challenger.py`. La variable `AB_TRAFFIC_B` (0 a 1, por defecto 0 = apagado) fija qué parte de las peticiones de `POST /predict` va a B, elegida al azar. La variante se guarda en la columna `variant` de `predictions` y se devuelve en la respuesta. `GET /ab/results` da la exactitud en vivo de cada variante, calculada con el feedback de #35, y la decisión. Regla: al menos 200 feedbacks por variante y solo hay ganador si el test z de dos proporciones da p < 0,05 y la diferencia es de al menos 0,5 puntos; si no, el resultado es `inconclusive`.

**Justificación:** se reutilizó el almacenamiento y el feedback que ya existían, de modo que el test no añade ninguna dependencia nueva. Se eligió XGBoost como challenger porque es otra familia de modelos y pesa 19,6 MB frente a los 136,3 MB del Random Forest actual. Resultados con el conjunto de validación (seed 42): A tiene exactitud 0,9520 y macro F1 0,9186, y B tiene 0,9471 y 0,9244. Con 10.000 peticiones simuladas la regla dice `inconclusive` (-0,78 puntos, p = 0,08) porque faltan datos; con 60.000 dice `winner_A` (-0,66 puntos, p = 0,0002). Un control A/A, donde B sirve el mismo modelo que A, no declara ganador. Para detectar medio punto hacen falta unos 30.000 feedbacks por variante.

**Limitación:** la regla decide por exactitud porque es lo que mide el feedback de cada petición, pero la métrica principal del proyecto es el macro F1, y en ella B es mejor. El ganador es un veredicto de exactitud, no de macro F1; calcular el macro F1 en vivo por variante queda sin implementar. En la simulación la clase real de cada fila hace de feedback, mientras que en producción el feedback sería parcial y quizá sesgado. 🟡 en este punto: falta probarlo con tráfico real.

**Explicación sencilla:** probar dos recetas dando cada una a la mitad de los clientes y contar cuál aprueba más. Con pocos clientes no se puede saber quién gana; con muchos sí.

**Evidencia:** issue #52 · `src/ab_testing.py`, `src/ab_simulation.py`, `src/export_challenger.py`, `src/database.py`, `app/api.py` · `docs/AB_TESTING.md` · `specs/feature-52-m8-ab-testing-between-models.md` · `tests/test_ab_testing.py`. Probado en Windows con Docker Desktop: con `AB_TRAFFIC_B=0.5`, 40 peticiones se repartieron 24 a A y 16 a B, `?variant=B` devolvió B, `?variant=C` dio 422 y una fila guardada antes de la migración quedó como variante A en MySQL.

**Responsable:** @Leandroletoile.

---

#### D10.11 · Monitoreo de data drift con alertas  (✅)

**Decisión:** medir el cambio de las entradas con el PSI (Population Stability Index) de cada una de las 12 variables del modelo contra el conjunto de entrenamiento (406.708 filas, solo train). Las numéricas se dividen en 10 deciles del train y las categóricas (`Wilderness_Area`, `Soil_Type`) tienen un grupo por categoría, juntando en "otros" las de menos del 1 %. Umbrales: menos de 0,1 es `ok`, de 0,1 a 0,25 es `warning` y desde 0,25 es `alert`. Se evalúan ventanas de 500 predicciones consecutivas (mínimo 200; si hay menos, `insufficient_data`). La API revisa la última ventana en segundo plano cada 500 predicciones (`DRIFT_CHECK_EVERY`), escribe la alerta en el log y, si hay `DRIFT_WEBHOOK_URL`, la envía a un webhook de Slack o Discord. `GET /drift` muestra el estado y el PSI de cada variable por ventana, y `python src/drift_monitoring.py {build|check|simulate}` hace lo mismo desde la terminal (`check` termina con código 1 solo si hay `alert`).

**Justificación:** el PSI no necesita etiquetas, así que funciona desde la primera petición; el feedback de #35 llega tarde y es parcial. Es una métrica estándar, comparable entre variables y sin dependencias nuevas. Los umbrales son los habituales y se comprobaron con datos reales: sin drift, 200 de 200 ventanas salieron `ok` (PSI máximo típico 0,04, percentil 95 de 0,062); con la elevación desplazada +100 m se detecta el 100 % de las ventanas, con +150 m casi todas llegan a `alert`, y con +50 m solo el 8 % (es 0,18 desviaciones estándar); cambiar el tipo de suelo en el 30 % de las filas da PSI 0,86. La referencia completa contra sí misma da 0,0003.

**Limitación:** solo detecta cambios en las entradas, no cambios en la relación entre entradas y clase (concept drift). La referencia no se rehace sola al reenviar un modelo reentrenado (#36): hay que volver a ejecutar `build`. Las alertas van al log y al webhook, no se guarda un historial en la base de datos. El PSI depende de cómo se agrupan los valores y los umbrales son una convención. 🟡 en este punto: se probó con desplazamientos simulados y con peticiones idénticas, no con tráfico real, y el webhook se probó contra un receptor local, no contra Slack ni Discord.

**Explicación sencilla:** es como comparar la foto de los clientes de hoy con la foto de los clientes con los que se aprendió. Si los clientes nuevos son muy distintos de los que el modelo conoció, suena una alarma, aunque todavía no sepamos si el modelo se equivoca más.

**Evidencia:** issue #53 · `src/drift_monitoring.py`, `src/database.py` (`prediction_inputs`), `app/api.py`, `app/schemas.py` · `docs/DRIFT_MONITORING.md` · `specs/feature-53-m8-data-drift-monitoring-with-alerts.md` · `tests/test_drift_monitoring.py` (75 tests pasan en total). Probado en Windows con Docker Desktop y MySQL: con ventana y chequeo de 200, 400 peticiones idénticas dejaron `/drift` en `alert` (12 variables, PSI máximo 8,46), el chequeo automático escribió `Data drift ALERT` en el log de la API (ids 401-600), el webhook llegó a un receptor local con el JSON completo y `check` terminó con código 1.

**Responsable:** @Leandroletoile.

---

#### D10.12 · Test end-to-end de la API con datos nuevos  (✅)

**Decisión:** añadir un test automático (`tests/test_end_to_end.py`) que recorre la API real de punta a punta —validación de FastAPI, capa de serving, modelo y respuesta— con datos que el modelo nunca vio.

**Justificación:** es la forma reproducible de comprobar que la app/API predice bien con datos nuevos. Usa el `TestClient` de FastAPI (sin levantar Docker a mano) y corre en la CI (#41). Tiene dos capas:
- **Sintética (siempre corre):** entrena el pipeline con el 70 % de los datos sintéticos del `conftest` y predice el 30 % restante. Resultado observado: **91 % de acierto en 126 filas**.
- **Real (gateada):** con `models/model.joblib` y `data/raw/covtype.data`, predice 300 filas del **test set real** (nunca visto). Resultado observado: **97 % en 300 filas** (el modelo tiene ~95 % de acierto offline).
- La base de datos se aísla en un SQLite temporal, así que el test no toca la BD real.

**Limitación:** la capa real no corre en la CI (allí no hay modelo exportado), así que en CI solo se ejecuta la sintética. La muestra real son 300 filas del test split, no el conjunto completo. La UI de Streamlit no se prueba (solo la API). Y usar el test split es una comprobación puntual que no influye en ninguna decisión: el test se sigue usando una sola vez, como pide el checklist (punto 4).

**Explicación sencilla:** es como hacerle al modelo un examen final de verdad: le damos parcelas nuevas (que nunca vio) por la misma "ventanilla" que usa la app, y comprobamos si acierta la especie. Lo hacemos automático para que la CI lo repita en cada cambio.

**Evidencia:** issue #42 · `tests/test_end_to_end.py` · `requirements.txt` (`httpx==0.27.2`) · `docs/TESTING.md`.

**Responsable:** @nagicome03.

---

# Los 5 errores más comunes (checklist de equipo)

- [ ] **1. Preprocesar antes del split** (fuga de datos). → Primero se reparte, luego se preprocesa. **Estado: parcial.** `feature_scaling.py` (#14), `logistic_regression.py` (#20), `neural_network.py` (#24), `export_model.py` (#32) y `final_metrics.py` (#25) ajustan exclusivamente sobre `train` dentro de un `Pipeline`. Las variables de #18 no aprenden nada de los datos. El EDA usó el dataset completo (ver R1).
- [x] **2. Usar accuracy con clases desbalanceadas.** → Usamos macro F1 (D0.4). **Estado: cumplido** en EDA, preprocesado, comparativa (#23) y evaluación final en validación/test (#25, macro F1 0,9186 / 0,9199 y tabla por clase).
- [ ] **3. Hacer SMOTE antes de la validación cruzada.** → Solo dentro de cada fold de train.
- [x] **4. Mirar el test para tomar decisiones.** → El test se usa una sola vez, al final. **Estado: cumplido:** el escalado (#14), los modelos (#20–#24), el feature engineering (#18), los pesos de clase (#17) y la exportación (#32) no tocaron el test; el test solo se evaluó al final en `src/final_metrics.py` (#25).
- [ ] **5. No definir qué error cuesta más antes de empezar.** → Pendiente: D0.7.

---

# Glosario

> Pensado para quien empieza. Si aparece una palabra nueva en el proyecto, añadidla aquí.

## Conceptos del Paso 0 y 1

| Término | Qué significa (en sencillo) |
|---|---|
| **Aprendizaje supervisado** | El modelo aprende a partir de ejemplos que ya traen la respuesta correcta (la "etiqueta"). |
| **Clasificación** | Predecir una categoría (por ejemplo, "tipo de árbol"), no un número. |
| **Clasificación binaria** | Solo hay 2 categorías posibles (sí/no). |
| **Clasificación multiclase** | Hay 3 o más categorías y cada ejemplo pertenece a **una sola**. |
| **Multietiqueta** | Un ejemplo puede tener varias categorías a la vez. No es nuestro caso. |
| **Variable (feature)** | Una columna de datos que el modelo usa para predecir (altitud, pendiente...). |
| **Variable objetivo (target)** | La columna que queremos predecir. En nuestro caso, `Cover_Type`. |
| **Clase** | Cada una de las respuestas posibles de la variable objetivo (7 en nuestro caso). |
| **Dataset desbalanceado** | Unas clases tienen muchísimos ejemplos y otras muy pocos. |
| **Variable binaria / one-hot** | Una categoría repartida en columnas de 0 y 1 (1 = "es este tipo de suelo"). |
| **Train / Validation / Test** | Las tres partes en que repartimos los datos: entrenar, comparar modelos, y examen final. |
| **Split** | El reparto de los datos en esas tres partes. |
| **Estratificar** | Repartir manteniendo en cada parte las mismas proporciones de clases. |
| **Semilla (`random_state`, seed)** | Número que fija el azar para que los resultados se repitan igual. |
| **Reproducibilidad** | Que otra persona pueda repetir lo que hicimos y obtener lo mismo. |
| **Checksum (SHA-256)** | "Huella digital" de un fichero para comprobar que es idéntico al original. |
| **Data leakage (fuga de datos)** | Que el modelo vea, sin querer, información del test o del futuro. Hace que los resultados parezcan mejores de lo que son. |
| **Overfitting (sobreajuste)** | El modelo se "memoriza" el entrenamiento y falla con datos nuevos. |
| **Underfitting (subajuste)** | El modelo es demasiado simple y rinde mal incluso en el entrenamiento. |
| **Baseline** | Modelo muy simple que sirve de referencia mínima a superar. |
| **DummyClassifier** | Baseline de scikit-learn que "adivina" sin aprender (por ejemplo, siempre la clase más común). |
| **Quality gate** | Condición mínima que debe cumplirse para dar algo por bueno (por ejemplo, overfitting < 5 %). |

## Métricas

| Término | Qué significa (en sencillo) |
|---|---|
| **Accuracy** | % de aciertos totales. Engaña si hay clases muy desbalanceadas. |
| **Precision** | De lo que el modelo marcó como clase X, cuánto era realmente X. |
| **Recall** | De lo que realmente era clase X, cuánto encontró el modelo. |
| **F1** | Nota única que combina precision y recall. |
| **Macro F1** | Media de los F1 de cada clase; todas las clases pesan igual. |
| **Matriz de confusión** | Tabla que muestra qué clases se confunden con cuáles. |
| **Falso positivo** | El modelo dice "es X" y no lo es. |
| **Falso negativo** | El modelo dice "no es X" y sí lo era. |

## Conceptos de pasos posteriores

| Término | Qué significa (en sencillo) |
|---|---|
| **EDA** | Análisis exploratorio: mirar los datos con tablas y gráficos para entenderlos. |
| **Outlier** | Valor muy raro, muy lejos de los demás. Puede ser un error o un caso real. |
| **Imputar** | Rellenar valores que faltan con una estimación (media, mediana...). |
| **Escalar (StandardScaler / MinMaxScaler)** | Poner las variables en rangos parecidos para que una no domine a las otras. |
| **Pipeline** | Cadena de pasos (preprocesado + modelo) que se aplica siempre en el mismo orden. |
| **fit / transform** | `fit` = el paso aprende de los datos (por ejemplo, calcula la media); `transform` = aplica lo aprendido. |
| **Feature engineering** | Crear variables nuevas a partir de las existentes. |
| **Validación cruzada (cross-validation)** | Entrenar varias veces con distintos trozos del train para obtener un resultado más estable. |
| **StratifiedKFold** | Validación cruzada que mantiene las proporciones de clases en cada trozo. |
| **Hiperparámetros** | Ajustes del modelo que decidimos nosotros antes de entrenar (por ejemplo, profundidad de un árbol). |
| **GridSearchCV / RandomizedSearchCV / Optuna** | Herramientas que prueban combinaciones de hiperparámetros para encontrar la mejor. |
| **Ensemble** | Combinar muchos modelos pequeños para obtener uno más fuerte (Random Forest, XGBoost, LightGBM). |
| **SMOTE** | Técnica que crea ejemplos artificiales de las clases pequeñas para equilibrar el entrenamiento. |
| **class_weight** | Hace que el modelo dé más importancia a los errores en clases pequeñas. |
| **Feature importance** | Ranking de qué variables usa más el modelo. |
| **SHAP** | Técnica para explicar cuánto influye cada variable en cada predicción. |
| **Data drift** | Que los datos reales cambien con el tiempo respecto a los de entrenamiento. |
| **joblib** | Librería para guardar el modelo/pipeline entrenado en un fichero y volver a cargarlo. |
| **Streamlit / FastAPI** | Herramientas para crear la aplicación web (Streamlit) y la API de predicción (FastAPI). |
| **Docker** | Herramienta para empaquetar el proyecto y que funcione igual en cualquier ordenador. |
| **Eta cuadrado (η²)** | Qué parte de la variación de una variable se explica por la clase. 0 = nada, 1 = todo. |
| **Asimetría (skewness)** | Si la distribución tiene la cola larga hacia un lado. |
| **Curtosis** | Cuán pesadas son las colas, es decir, cuántos valores extremos hay. |
| **IQR (rango intercuartílico)** | Distancia entre el cuartil 25 y el 75. La regla 1,5×IQR marca valores raros, pero raro no es error. |
| **PCA** | Resume muchas variables numéricas en pocas direcciones; sirve para ver dependencias entre ellas. |
| **Importancia por ganancia (gain/MDI)** | Cuánto mejora el modelo cada vez que usa una variable. Tiende a favorecer a las variables continuas. |
| **Screening de grupos** | Probar cada grupo de variables nuevas por separado con una regla fija antes de decidir cuáles se quedan. |
| **Transformador sin estado** | Paso que calcula cada fila por sí sola y no aprende nada de los datos, así que no puede filtrar información del test. |
| **`ColumnTransformer(remainder="drop")`** | Preprocesador que descarta las columnas que no nombró. Por eso las variables nuevas se perderían si van después de él. |
| **API / endpoint** | La ventanilla por la que otros programas piden predicciones. Cada ruta (`/health`, `/predict`) es un endpoint. |
| **Pydantic** | Librería que valida el tipo y el rango de cada dato antes de usarlo. |
| **Códigos 200 / 422 / 503** | Todo bien / entrada inválida / el servicio no puede responder (por ejemplo, no hay modelo). |
| **CI (integración continua) / workflow** | Comprobación automática en cada cambio subido al repo; el workflow es el archivo `.yml` de GitHub Actions que dice qué pasos corre. |
| **Build de Docker** | Armar la imagen (programa + dependencias). Si arma, la "caja" funciona. |
| **Convergencia (del optimizador)** | Momento en que el algoritmo iterativo (como la regresión logística) ya encontró su mejor solución y deja de cambiar antes de agotar el límite de intentos (`max_iter`). |
| **Perceptrón Multicapa (MLP)** | Red neuronal para datos en tablas, formada por varias capas de neuronas conectadas que aprenden combinaciones no lineales. |
| **Early stopping (parada temprana)** | Frenar el entrenamiento de una red neuronal en cuanto deja de mejorar en un pequeño subconjunto interno de validación, para evitar que memorice (`overfitting`). |
| **Matriz de confusión normalizada por fila** | Matriz de confusión donde cada fila suma 100 %: la diagonal muestra el *recall* de cada clase y el resto de celdas muestra con qué otra especie se confunde en proporción. |
