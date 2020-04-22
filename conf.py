# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

import json
from docutils import nodes

with open('conf.json') as jsonFile:
    conf = json.load(jsonFile)

for item in conf:
    globals()[item] = (conf[item])

def setup(app):
    app.connect('doctree-resolved',fixLocalMDAnchors)

def fixLocalMDAnchors(app, doctree, docname):
    for node in doctree.traverse(nodes.reference):
        uri = node.get('refuri')
        if '.md#' in uri and 'https://' not in uri:
            print(uri)
            node['refuri'] = node['refuri'].replace('.md#','.html#')
        if '.rst' in uri and 'https://' not in uri:
            node['refuri'] = node['refuri'].replace('.rst','.html')
