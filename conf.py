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
from os.path import isdir, isfile, join, basename, dirname
from os import makedirs
from shutil import copyfile

uris2check = []

with open('conf.json') as jsonFile:
    conf = json.load(jsonFile)

for item in conf:
    globals()[item] = (conf[item])

def setup(app):
    app.connect('doctree-resolved',fixLocalMDAnchors)
    app.connect('missing-reference',fixRSTLinkInMD)

def fixRSTLinkInMD(app, env, node, contnode):
    refTarget = node.get('reftarget')
    if '.rst' in refTarget and 'https://' not in refTarget:
        contnode['refuri'] = contnode['refuri'].replace('.rst','.html')
        contnode['internal'] = "True"
        return contnode
    else:
        filePath = refTarget.lstrip("/")
        if isfile(filePath):
            uris2check.append(filePath)
            return contnode


def fixLocalMDAnchors(app, doctree, docname):
    print(uris2check)
    for node in doctree.traverse(nodes.reference):
        uri = node.get('refuri')
        if '.md' in uri and 'https://' not in uri:
            node['refuri'] = node['refuri'].replace('.md','.html')
        else:
            filePath = uri.lstrip("/")
            uriDir = dirname(uri).lstrip("/")
            if isfile(filePath):
                print(app.outdir)
                newFileDir = join(app.outdir,dirname(uriDir))
                if not isdir(newFileDir):
                    makedirs(newFileDir)
                fileName = basename(uri)
                newFilePath = join(newFileDir,fileName)
                copyfile(filePath,newFilePath)
                dirDepth = len(docname.split("/")) - 1
                newUri = ".."*dirDepth + uri
                print('depth: ',dirDepth)
                print('filename: ',fileName)
                print('new path: ', newUri)
                print('new file path: ', newFilePath)
                print('docname: ', docname)
                print("**************************\n")

