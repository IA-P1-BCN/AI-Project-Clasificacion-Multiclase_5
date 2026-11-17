---
title: Forest Cover Type Classifier
emoji: 🌲
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: Multiclass forest cover type prediction (UCI Covertype)
---

# Forest Cover Type Classifier

Streamlit frontend + FastAPI backend serving the RandomForest pipeline trained
on the UCI Covertype dataset (7 classes, 54 features).

Source code, model card and deployment guide:
<https://github.com/IA-P1-BCN/AI-Project-Clasificacion-Multiclase_5>
(see `docs/APP.md`, section *Deployment*).

This Space only contains this `README.md` and a `Dockerfile` that clones the
GitHub repository at build time. The trained model is downloaded at startup
from the URL in the `MODEL_URL` Space variable.
