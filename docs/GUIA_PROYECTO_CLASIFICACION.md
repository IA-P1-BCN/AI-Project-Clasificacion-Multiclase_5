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
| 3 | Preprocesado | ⬜ Por documentar (hay trabajo hecho en el repo) |
| 4 | Feature engineering y selección | ✅ Documentado (#18) |
| 5 | Baseline | ⬜ Por documentar (hay trabajo hecho en el repo) |
| 6 | Entrenamiento y validación | 🟡 Parte rellena (desbalanceo #17); modelos por documentar |
| 7 | Ajuste de hiperparámetros | ⬜ |
| 8 | Evaluación final | ⬜ |
| 9 | Análisis de errores e interpretación | ⬜ |
| 10 | Despliegue y monitoreo | 🟡 API hecha (#34), CI en curso (#41) |

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
| R2 | **Un solo split para todos** | Todos los modelos deben usar las mismas particiones. | Baselines y MLP usan su propio split; hay un ticket (#23) para unificarlo. | ⬜ Unificar con `data_split.py` |
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

**Evidencia:** issue #7 · PR #54 · `src/data_audit.py` · `docs/EDA.md` (Dataset audit).

**Responsable:** @Leandroletoile y equipo.

---

#### D2.2 · Distribución de clases y desbalance  (✅)

**Decisión:** tratar el desbalance como hecho central. Clase 2: 283.301 filas (48,76 %); clase 4: 2.747 (0,47 %); proporción ~1:103. Las clases 1 y 2 suman ~85 %. La métrica principal es macro F1 y los splits y la validación cruzada deben ser estratificados.

**Justificación:** el accuracy engaña (predecir siempre la clase 2 ya da ~49 %). En el EDA no se balanceó nada: solo se recomendó comparar pesos de clase y remuestreo (este solo sobre train).

**Explicación sencilla:** si el 85 % del examen es de dos temas, una buena nota general no prueba que sepas el resto.

**Evidencia:** issue #8 · PR #56 · `src/class_distribution.py` · `docs/figures/class_distribution.png`. Se aplicó en #16 (split, ver D1.3 y D1.4) y #19 (StratifiedKFold, ver D1.9).

**Responsable:** @Leandroletoile y equipo.

---

#### D2.3 · Qué variables separan las clases  (✅)

**Decisión:** medir cada variable numérica con **eta cuadrado** (η², la parte de su varianza explicada por la clase) y revisar correlaciones. `Elevation` 0,616; `Horizontal_Distance_To_Roadways` 0,096; `Slope` 0,074; `Horizontal_Distance_To_Fire_Points` 0,070; `Aspect` 0,005.

**Justificación:** da una primera jerarquía de variables. Límite reconocido: η² solo ve diferencias de medias, y las 44 binarias no se evaluaron contra la clase.

**Explicación sencilla:** le preguntamos a cada variable "¿cuánto cambias según el tipo de bosque?". La altitud respondió "muchísimo"; casi todas las demás, "poco".

**Evidencia:** issue #9 · PR #58 · `src/class_eda.py` · `docs/EDA.md` (Feature analysis).

**Responsable:** @Leandroletoile y equipo.

---

#### D2.4 · Distribuciones, atípicos y PCA  (✅)

**Decisión:** describir cada variable con asimetría, curtosis y regla del IQR, y proyectar con PCA. Ninguna es claramente normal. Más asimétricas: `Vertical_Distance_To_Hydrology` (1,79; curtosis 5,25), `Fire_Points` (1,29) y `Horizontal_Distance_To_Hydrology` (1,14). El IQR marca hasta 5,4 % de filas y **no se eliminó ningún atípico**. PCA: PC1 25,9 %, PC2 21,5 %; PC10 ≈ 0 %.

**Justificación:** con 581.012 filas los tests de normalidad rechazan cualquier dato real, así que no se usaron. Borrar sin evidencia podría quitar ejemplos de clases minoritarias.

**Explicación sencilla:** raro no es error: aquí los valores raros son terrenos poco comunes.

**Evidencia:** issue #10 · PR #59 · `src/statistical_insights.py` · `docs/figures/`.

**Responsable:** @Leandroletoile y equipo.

---

#### D2.5 · Hallazgos y recomendaciones para M3  (✅)

**Decisión:** cerrar el EDA con una tabla de hallazgos y 5 recomendaciones, todas "por confirmar por el equipo": split y CV estratificados con macro F1; nada que imputar ni deduplicar; escalar solo para modelos lineales y de distancia; candidatas de feature engineering (seno/coseno de `Aspect`, distancia combinada al agua, redundancia de hillshade); verificar la dependencia lineal antes de quitar un hillshade.

**Justificación:** el EDA vale si alimenta decisiones posteriores. Se dejaron explícitas sus limitaciones.

**Explicación sencilla:** el EDA termina con una lista de tareas para la fase siguiente.

**Evidencia:** issue #11 · PR #61 · `docs/EDA.md` (Findings). Descarga del dataset en el README (#60), correcciones en PR #62.

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
| ¿Mi modelo necesita este paso o lo maneja solo? | ⬜ |
| ¿Estoy ajustando algo con datos que no debería ver (el test)? | ⬜ |
| ¿Imputar con la media distorsiona esta variable? | ⬜ |

#### D3.1 · (nombre de la decisión)  (⬜)

**Decisión:**

**Justificación:**

**Explicación sencilla:**

**Evidencia:**

**Responsable:**

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

# Paso 7 · Ajuste de hiperparámetros

> **Idea en una frase:** probar distintas "configuraciones" del modelo para ver cuál rinde mejor, siempre con validación cruzada y **sin mirar el test**.

**Herramientas:** `GridSearchCV` (pocos parámetros), `RandomizedSearchCV` u `Optuna` (muchos).

**Preguntas de la guía:**

| Pregunta | Respuesta |
|---|---|
| ¿Vale la pena el tiempo? (suele mejorar menos que tener buenos datos y buenas variables) | ⬜ |
| ¿Estamos sobreajustando a la validación de tanto probar combinaciones? | ⬜ |

#### D7.1 · (nombre de la decisión)  (⬜)

**Decisión:**

**Justificación:**

**Explicación sencilla:**

**Evidencia:**

**Responsable:**

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
| ¿La métrica coincide con la definida en el Paso 0 (macro F1)? | ⬜ |
| ¿Rinde igual en todos los subgrupos? ¿Hay sesgo? | ⬜ |
| ¿El resultado en test es parecido al de validación? Si cae mucho, hubo fuga u overfitting. | ⬜ |
| ¿Se cumple overfitting < 5 %? | ⬜ |

#### D8.1 · (nombre de la decisión)  (⬜)

**Decisión:**

**Justificación:**

**Explicación sencilla:**

**Evidencia:**

**Responsable:**

---

# Paso 9 · Análisis de errores e interpretación

> **Idea en una frase:** mirar **dónde y por qué** se equivoca el modelo, y comprobar que se apoya en variables con sentido.

**Preguntas de la guía:**

| Pregunta | Respuesta |
|---|---|
| ¿Los casos mal clasificados tienen algo en común? | ⬜ |
| ¿El modelo se apoya en variables que tienen sentido? (importancia de variables, SHAP) | ⬜ |
| ¿Aprendió algo absurdo? | ⬜ |
| ¿Qué datos adicionales ayudarían a corregir los errores? | ⬜ |

#### D9.1 · (nombre de la decisión)  (⬜)

**Decisión:**

**Justificación:**

**Explicación sencilla:**

**Evidencia:**

**Responsable:**

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
| ¿Cómo sabremos que el modelo empezó a fallar? | ⬜ Hoy solo existe `GET /health`, que dice si el servicio y el modelo están cargados. No se guardan predicciones ni se detecta *data drift*. |
| ¿Cada cuánto hay que reentrenar? | ⬜ Por decidir. |
| ¿Qué pasa si el modelo se equivoca? ¿Hay revisión humana? | La API devuelve `confidence` y las probabilidades de las 7 clases, para que una persona revise los casos dudosos. La revisión humana no está implementada. ⬜ |

#### D10.1 · API con FastAPI y dos endpoints  (✅)

**Decisión:** exponer el modelo con FastAPI en `app/api.py`: `GET /health` (`status`, `model_loaded`, `detail`) y `POST /predict`, que devuelve `cover_type` (1–7), `class_name`, `confidence` y `probabilities`.

**Justificación:** separar el modelo de la interfaz permite que la app, scripts o cualquier cliente lo usen igual. `/health` permite comprobar el servicio sin predecir.

**Explicación sencilla:** una ventanilla: entra el formulario con los datos del terreno y sale el tipo de bosque, con qué tan seguro está el modelo.

**Evidencia:** issue #34 · PR #81 · `app/api.py`, `app/serving.py`, `app/schemas.py` · `docs/APP.md`.

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

#### D10.3 · Contrato del modelo exportado  (🟡)

**Decisión:** la API carga `models/model.joblib` (ruta cambiable con `MODEL_PATH`), que debe recibir las 54 variables crudas en el orden de entrenamiento, tener `predict_proba` y `classes_`, y declarar `feature_names_in_` igual a esas 54. Las clases pueden venir 1–7 o 0–6 (se decodifican con `target_encoding`). Si el modelo falta o no cumple, la API arranca igual, `/health` informa `model_loaded: false` y `/predict` responde 503.

**Justificación:** permite avanzar sin esperar al modelo final (#32). Si el pipeline guardado incluye `add_features`, debe aceptar las 54 columnas crudas, no 62 (ver D4.5).

**Explicación sencilla:** la API es el enchufe y el modelo el aparato; dejamos escrito qué forma debe tener el enchufe.

**Evidencia:** PR #81 · `docs/APP.md`. Probado con un XGBoost de reemplazo, no con el modelo definitivo.

**Responsable:** @Leandroletoile y equipo. **Abierto:** quién entrega #32 y si exporta 1–7 o 0–6.

---

#### D10.4 · Integración continua con GitHub Actions  (🟡)

**Decisión:** `.github/workflows/ci.yml` corre en cada push y PR con dos trabajos:
1. Instala las dependencias fijadas en Python 3.11, ejecuta `scripts/check_imports.py` (importa todos los módulos de `src/` y `app/`) y corre `pytest` solo si hay tests.
2. Construye la imagen Docker sin publicarla.

Todavía no hay despliegue automático (CD).

**Justificación:** con ramas paralelas, una comprobación automática detecta antes de fusionar un import roto, una dependencia mal fijada o un Dockerfile que no construye. Hay pocos tests, así que el chequeo de imports es la red mínima.

**Explicación sencilla:** un revisor automático que comprueba que el proyecto sigue arrancando.

**Evidencia:** issue #41 · `.github/workflows/ci.yml` · `specs/feature-41-ci-cd-pipeline.md`. Los criterios de la spec quedan sin marcar hasta ver la primera ejecución en verde.

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

Además, `pydantic` no está fijado y su compatibilidad con fastapi 0.112.2 no está probada. La CI instala las versiones fijadas, así que será la primera prueba real.

**Justificación:** un modelo guardado con `joblib` en una versión puede fallar al abrirse en otra. Conviene entrenar y servir en el mismo entorno (el Docker).

**Explicación sencilla:** la receta fija una versión de cada ingrediente, pero cada uno cocina con la que tiene en casa.

**Evidencia:** `requirements.txt` · `pip list` de cada equipo.

**Responsable:** equipo (decidir si se fijan las versiones al entorno real o se mantienen).

---

# Los 5 errores más comunes (checklist de equipo)

- [ ] **1. Preprocesar antes del split** (fuga de datos). → Primero se reparte, luego se preprocesa. **Estado: parcial.** Las variables de #18 no aprenden nada de los datos. El EDA usó el dataset completo (ver R1).
- [ ] **2. Usar accuracy con clases desbalanceadas.** → Usamos macro F1 (D0.4). **Estado: cumplido en nuestra parte** (macro F1 y revisión por clase, D2.2 y D4.4).
- [ ] **3. Hacer SMOTE antes de la validación cruzada.** → Solo dentro de cada fold de train.
- [ ] **4. Mirar el test para tomar decisiones.** → El test se usa una sola vez, al final. **Estado: cumplido en #18:** la selección usó solo CV sobre train y la validación como chequeo; el test no se tocó.
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
