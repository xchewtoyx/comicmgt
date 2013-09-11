#!/bin/bash
# Copyright 2013 Russell Heilling

COMICMGT_DIR=$HOME/git/comicmgt-public

calibre-debug -e $COMICMGT_DIR/comicpull.py -- "$@"
