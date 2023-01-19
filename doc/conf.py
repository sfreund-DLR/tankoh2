# SPDX-FileCopyrightText: 2022 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: MIT

import os, sys
here = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(here, 'src'))

#===============================================================================
# if sphinx should be started standalone (not via setup.py), use these variables
#===============================================================================
from tankoh2 import name, author, version

projectName = name

# # The master toctree document.
# master_doc = name
authors = author
# 
# # The short X.Y version.
version = version
# # The full version, including alpha/beta/rc tags.
release = version
#===============================================================================
# end standalone variables
#===============================================================================

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build','.svn', # exclude other main documents
                    ]


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# # If your extensions are in another directory, add it here.
# sys.path.append(os.path.join(fileDir,'..','_static','sphinxext'))

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',  'sphinx.ext.imgmath',
              'sphinx.ext.coverage','sphinx.ext.viewcode',
              #'sphinx.ext.graphviz',#,'graphviz_custom',
              'sphinx.ext.autosummary',
              'sphinx.ext.todo','sphinx.ext.doctest',
              'sphinx.ext.intersphinx', 
#               'customroles', 
              'sphinx.ext.inheritance_diagram',
              'sphinxcontrib.bibtex',
              ]

#=======================================================================================================================
# numfig attributes
# 
# you can also reference numbered figures
# https://bitbucket.org/arjones6/sphinx-numfig/wiki/Home
#=======================================================================================================================
#number_figures = True
numfig = True
math_numfig = True
numfig_format={'figure': 'Figure %s ', 'table':  'Table %s',
               'code-block': 'Listing %s',
               'section':    'Section %s',
               }
numfig_secnum_depth = 1
#math_eqref_format = "Eq.{number}"
#figure_caption_prefix = 'Figure'


#=======================================================================================================================
# inheritance_diagram_custom attributes
#=======================================================================================================================
#inheritance graph attributes
inheritance_graph_attrs = dict(rankdir="TB", size='"8.0, 8.0"', fontsize=14,
                               ratio='compress')
inheritance_node_attrs = dict(shape='record', fontsize=16,
                              style='filled') 

# dot output format ['svg'|'png']
graphviz_output_format = 'svg'

#=======================================================================================================================
# autoclass options
#=======================================================================================================================
# generate autosummary pages
autosummary_generate=True

# http://sphinx.pocoo.org/ext/autodoc.html#confval-autoclass_content
#autoclass_content = 'both'

#order of modules and class members
autodoc_member_order = 'groupwise'


# autodoc_default_options
#The default options for autodoc directives. 
#They are applied to all autodoc directives automatically. 
#It must be a dictionary which maps option names to the values.
autodoc_default_options = {
#    'show-inheritance': True,
#    'inherited-members': False,
}


#=======================================================================================================================
# general sphinx settings
#=======================================================================================================================
# turn on todos
todo_include_todos = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# General information about the project.
import datetime
now = datetime.datetime.now()
copyright = str(now.year)+', DLR - Institute of Composite Structures and Adaptive Systems'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# html_theme = 'default'
#html_theme = 'sphinxdoc'
html_theme = "sphinx_rtd_theme"
#html_theme = 'agogo'
#html_theme = 'agogo_custom'
#html_theme = 'sphinxdoc_custom'
#html_theme = 'scipy'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['./_templates']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None
#html_logo = 'icon.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = 'icon.ico'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None



# -- Options for LaTeX output --------------------------------------------------

bibtex_bibfiles = ['library.bib']

# The paper size ('letter' or 'a4').
latex_paper_size = 'a4'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None
latex_logo = 'icon.png'

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
latex_preamble = '''
% math packages for formulas in surrogate.rst
\\usepackage{amsmath}
\\usepackage{amssymb}

'''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True



