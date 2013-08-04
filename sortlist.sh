#!/bin/bash

TODODIR=$HOME/Dropbox/todo

calibre-debug ~/git/comicmgt/sort-readlist.py -- \
    -c dc52:18053 -c rising:42011 \
    -c image:34852,54135 \
    -c webhead:45101,39301 \
    -i $TODODIR/todo.txt -o $TODODIR/streams "$@"

if ! diff -q $TODODIR/todo.txt $TODODIR/streams; then
    exec diff -u $TODODIR/todo.txt $TODODIR/streams  | less
    echo -n "Install new version? (y/N)"
    read _install
    if [ "$_install" = "y" -o "$_install" = "Y" ]; then
        cp $TODODIR/streams $TODODIR/todo.txt
    fi
fi
