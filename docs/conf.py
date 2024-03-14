# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

project = 'Speedwagon (UIUC Prescon Distribution)'
copyright = '2024, a'
author = 'a'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'workflowssummary',
    'sphinx.ext.doctest',
]

templates_path = ['_templates']
exclude_patterns = []

sys.path.append(os.path.abspath('exts'))

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']


latex_documents = [
    ('index', f'Speedwagon(UIUC_Prescon_Distribution).tex',
     f'{project} Documentation',
     "University of Illinois at Urbana Champaign",
     'manual'),
]

latex_logo = '_static/full_mark_horz_bw.png'