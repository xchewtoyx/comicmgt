#!/usr/bin/python

import os
import sys

# This is the default setup for all of calibre's built in tools.
PATH = os.environ.get('CALIBRE_PYTHON_PATH', '/usr/lib/calibre')
if PATH not in sys.path:
    sys.path.insert(0, PATH)

sys.resources_location = os.environ.get('CALIBRE_RESOURCES_PATH', '/usr/share/calibre')
sys.extensions_location = os.environ.get('CALIBRE_EXTENSIONS_PATH', '/usr/lib/calibre/calibre/plugins')
sys.executables_location = os.environ.get('CALIBRE_EXECUTABLES_PATH', '/usr/bin')
