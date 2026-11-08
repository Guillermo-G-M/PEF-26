"""Configuración de Sphinx para la documentación de `dupfinder` (Parcial 2, Fase 4)."""

import os
import sys

# Fallback por si la doc se buildea sin `pip install -e .` hecho antes.
sys.path.insert(0, os.path.abspath("../src"))

project = "dupfinder"
copyright = "2026, Parcial 1 y 2 - Programación Eficiente"
author = "dupfinder"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # lee docstrings estilo Google (las de la Fase 2)
    "sphinx.ext.viewcode",  # agrega un link "[source]" al código de cada función
]

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True

autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

language = "es"
# Evita que reST convierta "--threshold" (flags de la CLI) en un guion largo.
smartquotes = False

html_theme = "furo"
html_static_path = ["_static"]
