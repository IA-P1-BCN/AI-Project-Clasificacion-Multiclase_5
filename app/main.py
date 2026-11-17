"""Streamlit frontend for the Covertype prediction app (ticket #33).

Collects the 12 compact features of a 30x30 m forest cell, calls the FastAPI
backend (ticket #34) at /predict, and shows the predicted cover type with its
photo, botanical facts, confidence and per-class probabilities. UI strings are
in Spanish; the species names come from `src/target_encoding.py` (single source
of truth).
"""
import os
import sys
from pathlib import Path

import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # the training modules live in the flat src/ package

from target_encoding import CLASS_NAMES  # noqa: E402

API_URL = os.getenv("API_URL", "http://localhost:8000")

# One correctly-classified cell per cover type, spread across the confidence
# spectrum so the demo shows the model's full behaviour: clear cells (high
# confidence) and borderline cells (low confidence). All rows are real training
# cells that the untuned Random Forest of the export (#32) predicts correctly.
EXAMPLES = {
    1: {
        "Elevation": 3153, "Aspect": 138, "Slope": 7,
        "Horizontal_Distance_To_Hydrology": 247,
        "Vertical_Distance_To_Hydrology": 9,
        "Horizontal_Distance_To_Roadways": 5941,
        "Hillshade_9am": 231, "Hillshade_Noon": 238, "Hillshade_3pm": 140,
        "Horizontal_Distance_To_Fire_Points": 947,
        "Wilderness_Area": 1, "Soil_Type": 29,
    },
    2: {
        "Elevation": 2929, "Aspect": 310, "Slope": 12,
        "Horizontal_Distance_To_Hydrology": 67,
        "Vertical_Distance_To_Hydrology": 11,
        "Horizontal_Distance_To_Roadways": 4930,
        "Hillshade_9am": 186, "Hillshade_Noon": 231, "Hillshade_3pm": 185,
        "Horizontal_Distance_To_Fire_Points": 2151,
        "Wilderness_Area": 1, "Soil_Type": 29,
    },
    3: {
        "Elevation": 2618, "Aspect": 35, "Slope": 16,
        "Horizontal_Distance_To_Hydrology": 234,
        "Vertical_Distance_To_Hydrology": 102,
        "Horizontal_Distance_To_Roadways": 1390,
        "Hillshade_9am": 216, "Hillshade_Noon": 202, "Hillshade_3pm": 117,
        "Horizontal_Distance_To_Fire_Points": 1745,
        "Wilderness_Area": 3, "Soil_Type": 10,
    },
    4: {
        "Elevation": 2052, "Aspect": 122, "Slope": 29,
        "Horizontal_Distance_To_Hydrology": 42,
        "Vertical_Distance_To_Hydrology": 16,
        "Horizontal_Distance_To_Roadways": 658,
        "Hillshade_9am": 254, "Hillshade_Noon": 203, "Hillshade_3pm": 56,
        "Horizontal_Distance_To_Fire_Points": 693,
        "Wilderness_Area": 4, "Soil_Type": 1,
    },
    5: {
        "Elevation": 2919, "Aspect": 81, "Slope": 15,
        "Horizontal_Distance_To_Hydrology": 150,
        "Vertical_Distance_To_Hydrology": 26,
        "Horizontal_Distance_To_Roadways": 4696,
        "Hillshade_9am": 239, "Hillshade_Noon": 212, "Hillshade_3pm": 99,
        "Horizontal_Distance_To_Fire_Points": 1829,
        "Wilderness_Area": 1, "Soil_Type": 29,
    },
    6: {
        "Elevation": 2576, "Aspect": 322, "Slope": 12,
        "Horizontal_Distance_To_Hydrology": 201,
        "Vertical_Distance_To_Hydrology": 58,
        "Horizontal_Distance_To_Roadways": 1921,
        "Hillshade_9am": 190, "Hillshade_Noon": 228, "Hillshade_3pm": 178,
        "Horizontal_Distance_To_Fire_Points": 679,
        "Wilderness_Area": 3, "Soil_Type": 4,
    },
    7: {
        "Elevation": 3140, "Aspect": 183, "Slope": 5,
        "Horizontal_Distance_To_Hydrology": 30,
        "Vertical_Distance_To_Hydrology": 3,
        "Horizontal_Distance_To_Roadways": 2224,
        "Hillshade_9am": 221, "Hillshade_Noon": 243, "Hillshade_3pm": 157,
        "Horizontal_Distance_To_Fire_Points": 2701,
        "Wilderness_Area": 1, "Soil_Type": 23,
    },
}

# Botanical facts per cover type (displayed under the prediction). The 7 labels
# of the dataset are forest cover types: Spruce/Fir and Cottonwood/Willow are
# mixed stands, and Krummholz is a growth form, not a single species.
# "images" holds one photo per species; Cottonwood/Willow has two (side by side).
SPECIES_INFO = {
    1: {
        "scientific": "Picea engelmannii + Abies lasiocarpa",
        "height": "20–40 m",
        "note": "Bosque mixto de alta montaña, en zonas frías y húmedas.",
        "unique": "Pícea y abeto conviven en un mismo tipo de bosque.",
        "images": [
            {"url": "https://commons.wikimedia.org/wiki/Special:FilePath/Engelmann_spruce_on_the_PCT%2C_Washington.JPG?width=640", "caption": None},
        ],
    },
    2: {
        "scientific": "Pinus contorta",
        "height": "hasta 30 m",
        "note": "Pino de tronco recto; el más abundante del parque.",
        "unique": "Sus conos se abren con el calor del fuego (serotinia).",
        "images": [
            {"url": "https://naturaledge.watersheds.ca/wp-content/uploads/2019/09/Lodgepole-800x800.jpg", "caption": None},
        ],
    },
    3: {
        "scientific": "Pinus ponderosa",
        "height": "30–70 m",
        "note": "Pino grande de corteza anaranjada, de laderas secas.",
        "unique": "Su corteza desprende aroma a vainilla.",
        "images": [
            {"url": "https://commons.wikimedia.org/wiki/Special:FilePath/Pinus_ponderosa_15932.JPG?width=640", "caption": None},
        ],
    },
    4: {
        "scientific": "Populus spp. + Salix spp.",
        "height": "15–30 m",
        "note": "Árboles de ribera, junto a ríos y arroyos.",
        "unique": "Dos especies que conviven junto al agua.",
        "images": [
            {"url": "https://fieldingtreecare.com/wp-content/uploads/2022/12/cottonwoodtree.jpg", "caption": "Álamo (Populus)"},
            {"url": "https://images.squarespace-cdn.com/content/v1/5c3cd4ad3c3a53acbfcbb6bb/1611685517425-0PX3OP9NLSWZWGBEARES/weeping-willow.jpg", "caption": "Sauce (Salix)"},
        ],
    },
    5: {
        "scientific": "Populus tremuloides",
        "height": "15–30 m",
        "note": "Árbol caducifolio de hojas que tiemblan con el viento.",
        "unique": "Un clon puede ocupar hectáreas (el bosque «Pando» es un solo organismo).",
        "images": [
            {"url": "https://commons.wikimedia.org/wiki/Special:FilePath/2013-10-06_15_04_21_Aspens_during_autumn_along_the_Changing_Canyon_Nature_Trail_in_Lamoille_Canyon%2C_Nevada.jpg?width=640", "caption": None},
        ],
    },
    6: {
        "scientific": "Pseudotsuga menziesii",
        "height": "60–100 m",
        "note": "Conífera de gran tamaño; no es un abeto verdadero.",
        "unique": "Conos con brácteas de tres puntas (parecen patitas de ratón).",
        "images": [
            {"url": "https://images.squarespace-cdn.com/content/v1/5c3cd4ad3c3a53acbfcbb6bb/1616527182467-GE9HOAR6DDYNK72NNCRI/1200px-Pseudotsuga_glauca_forest.jpg", "caption": None},
        ],
    },
    7: {
        "scientific": "— (forma de crecimiento)",
        "height": "1–3 m",
        "note": "Árboles enanos y retorcidos en la línea de árboles.",
        "unique": "No es una especie: es la forma enana que adopta el árbol por viento y frío.",
        "images": [
            {"url": "https://commons.wikimedia.org/wiki/Special:FilePath/Pinus_albicaulis_7872.JPG?width=640", "caption": None},
        ],
    },
}

# Reverse map (class name -> cover type 1-7) used to show the runner-up photo.
NAME_TO_COVER_TYPE = {name: cover_type for cover_type, name in CLASS_NAMES.items()}

# Fixed height (px) of the vertical photo rectangle; object-fit: cover crops the
# source image to fill it, so every photo has the same size regardless of its shape.
PHOTO_HEIGHT = 380
# Height (px) of the landscape photos used when a cover type has two species
# (Cottonwood/Willow): stacked vertically, each wider than tall.
PHOTO_HEIGHT_WIDE = 180

# (form key, Spanish label, min, max) for the 10 numeric inputs.
NUMERIC_FIELDS = [
    ("Elevation", "Elevación (m)", 0, 5000),
    ("Aspect", "Orientación (°)", 0, 360),
    ("Slope", "Pendiente (°)", 0, 90),
    ("Horizontal_Distance_To_Hydrology", "Distancia horizontal al agua (m)", 0, 10000),
    ("Vertical_Distance_To_Hydrology", "Distancia vertical al agua (m)", -500, 1000),
    ("Horizontal_Distance_To_Roadways", "Distancia a carreteras (m)", 0, 10000),
    ("Hillshade_9am", "Sombra a las 9:00 (índice 0–255)", 0, 255),
    ("Hillshade_Noon", "Sombra al mediodía (índice 0–255)", 0, 255),
    ("Hillshade_3pm", "Sombra a las 15:00 (índice 0–255)", 0, 255),
    ("Horizontal_Distance_To_Fire_Points", "Distancia a puntos de incendio (m)", 0, 10000),
]

# Initial form state: a representative cell of the most frequent class (Lodgepole Pine).
DEFAULT_EXAMPLE = 2

# The 12 payload keys, in the order the backend expects them.
PAYLOAD_KEYS = [key for key, *_ in NUMERIC_FIELDS] + ["Wilderness_Area", "Soil_Type"]


def _fill_form(cover_type: int) -> None:
    """Copy a typical cell of `cover_type` into the form state."""
    for key, value in EXAMPLES[cover_type].items():
        st.session_state[key] = value


def _payload_from_state() -> dict:
    """Build the request payload from the current form state."""
    return {key: st.session_state[key] for key in PAYLOAD_KEYS}


def _post_predict(payload: dict) -> dict | None:
    """POST the payload to the backend and return the parsed response, or None on failure."""
    try:
        response = requests.post(f"{API_URL}/predict", json=payload, timeout=15)
    except requests.exceptions.ConnectionError:
        st.error(
            "No se pudo conectar con el backend. Asegúrate de que FastAPI está "
            f"corriendo (`uvicorn app.api:app --port 8000`) y accesible en {API_URL}."
        )
        return None
    if response.status_code == 200:
        return response.json()
    if response.status_code == 503:
        st.error("El backend no tiene el modelo cargado. Ejecuta `python src/export_model.py` (#32).")
        return None
    st.error(f"El backend respondió con error {response.status_code}: {response.text}")
    return None


def _confidence_style(confidence: float) -> tuple[str, str]:
    """Return (color, label) for a confidence value in 0..1."""
    pct = confidence * 100
    if pct >= 80:
        return "#2e7d32", "Confianza alta"
    if pct >= 60:
        return "#f9a825", "Confianza media"
    return "#e53935", "Confianza baja"


def _photo_html(url: str, alt: str, caption: str | None = None, height: int = PHOTO_HEIGHT) -> str:
    """Return HTML for a fixed-size photo that crops to fill via object-fit."""
    html = (
        f"<img src='{url}' alt='{alt}' "
        f"style='width:100%; height:{height}px; object-fit:cover; "
        f"border-radius:8px; display:block;' />"
    )
    if caption:
        html += (
            f"<div style='text-align:center; font-size:12px; color:#666; "
            f"margin-top:4px;'>{caption}</div>"
        )
    return html


def _show_result(result: dict) -> None:
    """Render the species card (facts + photo), confidence, top-2 and probability bars."""
    cover_type = result["cover_type"]
    predicted = result["class_name"]
    confidence = float(result["confidence"])
    probabilities = result["probabilities"]
    info = SPECIES_INFO[cover_type]
    images = info["images"]

    # Species card: botanical facts on the left, photo(s) on the right.
    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.markdown(f"### 🌲 {predicted}")
        st.markdown(f"*{info['scientific']}*")
        st.markdown(
            f"- **Altura:** {info['height']}\n"
            f"- **Hábitat:** {info['note']}\n"
            f"- **Seña única:** {info['unique']}"
        )
    with col_right:
        if len(images) == 1:
            st.markdown(_photo_html(images[0]["url"], predicted, images[0]["caption"]), unsafe_allow_html=True)
        else:
            for img in images:
                st.markdown(_photo_html(img["url"], img["caption"], img["caption"], height=PHOTO_HEIGHT_WIDE), unsafe_allow_html=True)

    # Highlighted confidence.
    color, label = _confidence_style(confidence)
    st.markdown(
        f"<div style='text-align:center; padding:10px 0 14px;'>"
        f"<div style='font-size:56px; font-weight:800; line-height:1; color:{color};'>{confidence * 100:.1f}%</div>"
        f"<div style='font-size:15px; margin-top:6px; color:{color};'>{label}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Top-2: when the runner-up is close (>= 20 %), show both photos.
    ordered = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    if len(ordered) >= 2 and ordered[1][1] >= 0.20:
        second_name, second_prob = ordered[1]
        second_ct = NAME_TO_COVER_TYPE[second_name]
        st.markdown("#### 🤔 Las dos opciones más probables")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(_photo_html(SPECIES_INFO[cover_type]["images"][0]["url"], predicted), unsafe_allow_html=True)
            st.caption(f"1ª · {predicted} ({confidence * 100:.0f}%)")
        with c2:
            st.markdown(_photo_html(SPECIES_INFO[second_ct]["images"][0]["url"], second_name), unsafe_allow_html=True)
            st.caption(f"2ª · {second_name} ({second_prob * 100:.0f}%)")

    # Probability bars (only classes with at least one vote).
    st.markdown("#### Probabilidad por especie")
    nonzero = [(name, float(prob)) for name, prob in ordered if prob > 0]
    if not nonzero:
        st.info("Ninguna clase obtuvo votos del modelo.")
        return
    rows = []
    for name, prob in nonzero:
        pct = prob * 100
        rows.append(
            f'<div style="margin-bottom:9px;">'
            f'<div style="display:flex; justify-content:space-between; font-size:14px;">'
            f'<span style="font-weight:600;">{name}</span><span>{pct:.1f}%</span></div>'
            f'<div style="background:#d7e8d4; border-radius:6px; height:16px; overflow:hidden;">'
            f'<div style="width:{pct}%; height:100%; border-radius:6px; '
            f'background:linear-gradient(90deg, #66bb6a, #2e7d32); animation:grow .7s ease-out;"></div>'
            f'</div></div>'
        )
    st.markdown(
        "<style>@keyframes grow{from{width:0;}}</style>" + "".join(rows),
        unsafe_allow_html=True,
    )


# --- Page ---
st.set_page_config(page_title="Predicción de cobertura forestal", page_icon="🌲", layout="centered")

st.title("🌲 Predicción de cobertura forestal")
st.caption(
    "Introduce las características de una celda de 30×30 m del bosque Roosevelt "
    "(Colorado) y el modelo predice la especie de árbol dominante (1 de 7)."
)

# One-time initialization of the form state with a representative cell.
for key, value in EXAMPLES[DEFAULT_EXAMPLE].items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- Example buttons (rendered before the form so they can pre-fill it) ---
st.subheader("🌳 Cargar un ejemplo")
st.caption(
    "Las variables provienen de un sistema de información geográfica (GIS) y no "
    "se miden a pie de campo: cada botón carga una celda típica de su especie."
)
clicked = None
for row in ((1, 2, 3, 4), (5, 6, 7)):
    columns = st.columns(len(row))
    for cover_type, column in zip(row, columns):
        with column:
            if st.button(
                CLASS_NAMES[cover_type],
                key=f"example_{cover_type}",
                use_container_width=True,
                help=f"Cargar los valores típicos de {CLASS_NAMES[cover_type]}.",
            ):
                clicked = cover_type

if clicked is not None:
    _fill_form(clicked)

st.divider()

# --- Predict ---
if st.button("🔎 Predecir cobertura forestal", type="primary", use_container_width=True):
    result = _post_predict(_payload_from_state())
    if result is not None:
        _show_result(result)

st.divider()

# --- Form (collapsible: the demo fills it via the example buttons) ---
with st.expander("📋 Características de la celda (opcional)"):
    st.caption("Los botones de ejemplo rellenan estos valores automáticamente.")
    col_a, col_b = st.columns(2)
    for index, (key, label, minimum, maximum) in enumerate(NUMERIC_FIELDS):
        with col_a if index % 2 == 0 else col_b:
            st.number_input(label, min_value=minimum, max_value=maximum, step=1, key=key)
    st.selectbox(
        "Zona silvestre (Wilderness Area, 1–4)", options=list(range(1, 5)), key="Wilderness_Area"
    )
    st.selectbox(
        "Tipo de suelo (Soil Type, 1–40)", options=list(range(1, 41)), key="Soil_Type"
    )

st.divider()
st.caption(
    "Modelo: Random Forest entrenado con el dataset *Forest Cover Type* (UCI). "
    "Cada predicción se guarda automáticamente en la base de datos (#37)."
)
