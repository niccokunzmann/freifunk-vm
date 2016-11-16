#!/usr/bin/python3
from bottle import post, get, run, request, static_file, redirect, route
import os
import sys
import shutil

APPLICATION = "freifunk-vm"
HERE = os.path.dirname(__file__) or os.getcwd()
ZIP_PATH = "/" + APPLICATION + ".zip"
STATIC_FILES = os.path.join(HERE, "static")

@route('/')
def index():
    return redirect("/static/index.html")

@route('/static/<filename>')
def static(filename):
    return static_file(filename, root=STATIC_FILES)


@get('/source')
def get_source_redirect():
    """Download the source of this application."""
    redirect(ZIP_PATH)

@get(ZIP_PATH)
def get_source():
    """Download the source of this application."""
    # from http://stackoverflow.com/questions/458436/adding-folders-to-a-zip-file-using-python#6511788
    path = (shutil.make_archive("/tmp/" + APPLICATION, "zip", HERE))
    return static_file(path, root="/")

def main():
    run(host='', port=80, debug=True)

if __name__ == "__main__":
    main()
