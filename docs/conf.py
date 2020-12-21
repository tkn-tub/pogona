# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('..'))


# -- Project information -----------------------------------------------------

with open("../version.txt", 'r') as fh:
    version = fh.read().strip()

project = 'Pogona'
copyright = '2020 Data Communications and Networking (TKN), TU Berlin'
author = 'Lukas Stratmann, Jan Peter Drees, Fabian Bronner'

# The full version, including alpha/beta/rc tags
release = '0.1.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',  # generate from docstrings
    'sphinx.ext.autosummary',  # for summary tables
    # 'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx.ext.mathjax',
    # 'autodocsumm',
    'sphinx_rtd_theme',
]

autodoc_default_options = {
    'member-order': 'groupwise',
    'undoc-members': True,  # don't hide undocumented members
    'members': True,  # show members by default
    'attributes': True,
    'show-inheritance': True,
    'imported-members': True,
    'inherited-members': True,
    'special-members': '__init__',
    # 'autosummary': True,  # for 'autodocsumm' extension (separate package)
    # 'autosummary_generate': True,
}
autosummary_generate = True
# autoclass_content = 'class'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

numfig = True


# -- LaTeX -------------------------------------------------------------------

# latex_elements = {
#     'preamble': r'''
# \usepackage{
# ''',
# }


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']
