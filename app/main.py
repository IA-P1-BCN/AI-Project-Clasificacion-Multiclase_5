"""Placeholder Streamlit app.

This exists so that `docker compose up` launches a working base environment
from day one (M0). The real multiclass classification UI is built in M6.
"""

import streamlit as st

st.set_page_config(page_title="Multiclass Classification · Team 5", page_icon="🌲")

st.title("🌲 Multiclass Classification — Team 5")
st.success("Base environment is up and running.")

st.markdown(
    """
    This is the **M0 placeholder app**. The development environment
    (Python 3.11 + Docker) is ready.

    **Next milestones**
    - **M1** — Problem definition & dataset
    - **M2** — Audit & EDA
    - **M3** — Cleaning & preprocessing
    - **M4** — Model training & comparison
    - **M5** — Evaluation & error analysis
    - **M6** — Application & production (this UI will live here)
    """
)
