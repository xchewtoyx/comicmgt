#!/usr/bin/python

import os
import sys

# This is the default setup for all of calibre's built in tools.
PATHS = os.environ.get('CALIBRE_PYTHON_PATH',
                       '/opt/calibre/lib/python2.7:'
                       '/opt/calibre/lib/python2.7/plat-linux2:'
                       '/opt/calibre/lib/python2.7/lib-dynload:'
                       '/opt/calibre/lib/python2.7/site-packages')

for path in PATHS.split(':'):
  if path not in sys.path:
    sys.path.insert(0, path)

sys.resources_location = os.environ.get('CALIBRE_RESOURCES_PATH', '/opt/calibre/resources')
sys.extensions_location = os.environ.get('CALIBRE_EXTENSIONS_PATH', '/opt/calibre/lib/python2.7/site-packages/calibre/plugins')
sys.executables_location = os.environ.get('CALIBRE_EXECUTABLES_PATH', '/usr/bin')
