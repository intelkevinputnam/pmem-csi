from os import getcwd
from shutil import copyfile
from pathlib import Path


import os.path

badRefsFileName = "bad-refs.txt"
homeDir = getcwd()
targetDir = os.path.join(homeDir,"_output/html/")

def findRefs():
    with open(badRefsFileName) as refFile:
        badCount = 0
        count = 0
        for line in refFile:
            lineBits = line.split(":")
            pathOfSource = os.path.abspath(lineBits[0].strip() + ":" + lineBits[1].strip())
            relSourcePath = "/" + str(os.path.dirname(os.path.relpath(lineBits[0].strip())))
            refPath = lineBits[-1].strip()
            pathToFile = os.path.abspath(str(homeDir) + relSourcePath + "/" + refPath)
            if not os.path.isfile(pathToFile):
                print("Failed to match file (" + str(pathToFile) + ") to reference in " + str(pathOfSource) + ".")
                badCount += 1
                continue
            relPath = os.path.relpath(pathToFile,start=homeDir)
            newPath = os.path.join(targetDir,relPath)
            Path(os.path.dirname(newPath)).mkdir(parents=True, exist_ok=True)
            copyfile(pathToFile,newPath)
            count += 1
    print(str(count) + " files copied to fix refs.")
    print("Failed to copy " + str(badCount) + " missing files.")

findRefs()
