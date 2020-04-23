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

# Callback registerd with 'missing-reference'. 
def fixRSTLinkInMD(app, env, node, contnode):
    refTarget = node.get('reftarget')
    filePath = refTarget.lstrip("/")
    if '.rst' in refTarget and "://" not in refTarget:
    # This occurs when a .rst file is referenced from a .md file
    # Currently unable to check if file exists as no file
    # context is provided and links are relative. 
    #
    # Example: [Application examples](examples/readme.rst)
    #
    # TODO: Generate list and check them in fixLocalMDAnchors
    #
        contnode['refuri'] = contnode['refuri'].replace('.rst','.html')
        contnode['internal'] = "True"
        return contnode
    else:
    # This occurs when a file is referenced for download from an .md file.
    # Construct a list of them and short-circuit the warning. The files 
    # are moved later (need file location context). To avoid warnings,
    # write .md files, make the links absolute. This only marks them fixed
    # if it can verify that they exist.
    #
    # Example: [Makefile](/Makefile)
    #
        if isfile(filePath):
            uris2check.append(filePath) 
            return contnode


def normalizePath(docPath,uriPath):
    if "#" in uriPath:
    # Strip out anchors
        uriPath = uriPath.split("#")[0]
    if uriPath.startswith("/"):
    # It's an absolute path
        return uriPath.lstrip("/") #path to file from project directory
    else:
    # It's a relative path
        docDir = dirname(docPath)
        return join(docDir,uriPath) #path to file from referencing file


# Callback registerd with 'doctree-resolved'. 
def fixLocalMDAnchors(app, doctree, docname):
    for node in doctree.traverse(nodes.reference):
        uri = node.get('refuri')
        filePath = normalizePath(docname,uri)
        if isfile(filePath):
        # Only do this if the file exists.
        #
        # TODO: Pop a warning if the file doesn't exist. 
        #
            if '.md' in uri and '://' not in uri: 
            # Make sure .md file links that weren't caught are converted.
            # These occur when creating an explicit link to an .md file
            # from an .rst file. By default these are not validated by Sphinx
            # or recommonmark. Only toctree references are validated.
            #
            # Only include this code if .md files are being converted to html
            #
            # Example: `Google Cloud Engine <gce.md>`__
            #
                node['refuri'] = node['refuri'].replace('.md','.html')
            else: 
            # If there are links to local files other than .md (.rst files are caught
            # when warnings are fired), move the files into the Sphinx project, so
            # they can be accessed. 
            #
            # Example: [Makefile](/Makefile)
            #
                newFileDir = join(app.outdir,dirname(filePath)) # where to move the file in Sphinx output.
                newFilePath = join(app.outdir,filePath)
                newURI = uri # if the path is relative no need to change it.
                if uri.startswith("/"):
                # It's an absolute path. Need to make it relative.
                    uri = uri.lstrip("/")
                    docDirDepth = len(docname.split("/")) - 1
                    newURI = "../"*docDirDepth + uri
                if not isdir(newFileDir):
                    makedirs(newFileDir)                

                copyfile(filePath,newFilePath)
                node['refuri'] = newURI

