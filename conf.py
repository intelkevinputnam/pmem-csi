
import json
import os
import sys
from os import getenv
#support for modified code block
from pygments.lexers.shell import BashSessionLexer
from sphinx.highlighting import lexers

def setup(app):
   app.add_css_file("override.css")

#############
#
# Add a special lexer to add a class to console lexer
#
#############

class copyAllConsole (BashSessionLexer):
    name = 'ShellSession'

lexers['ShellSession'] = copyAllConsole(startinLine=True)

# Get settings from conf.json

with open('conf.json') as jsonFile:
    conf = json.load(jsonFile)

for item in conf:
    globals()[item] = (conf[item])

sphinx_md_useGitHubURL = True
baseBranch = "devel"
commitSHA = getenv('GITHUB_SHA')
githubBaseURL = 'https://github.com/' + (getenv('GITHUB_REPOSITORY') or 'intel/pmem-csi') + '/'
githubFileURL = githubBaseURL + "blob/"
githubDirURL = githubBaseURL + "tree/"
if commitSHA:
    githubFileURL = githubFileURL + commitSHA + "/"
    githubDirURL = githubDirURL + commitSHA + "/"
else:
    githubFileURL = githubFileURL + baseBranch + "/"
    githubDirURL = githubDirURL + baseBranch + "/"
sphinx_md_githubFileURL = githubFileURL
sphinx_md_githubDirURL = githubDirURL