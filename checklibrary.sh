#!/bin/bash
# Copyright 2013 Russell Heilling.

COMICMGTDIR=$HOME/git/comicmgt-public

calibredb list -s identifiers:comicvine:true -f title -w 800 \
               --sort-by pubdate --ascending | \
    sed 's/ \+$//; s/:[^#]\+$//' | $COMICMGTDIR/ooo.py -r
