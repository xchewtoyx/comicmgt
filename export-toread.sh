#!/bin/bash
# Copyright 2013 Russell Heilling

count=$1
tmpfile=$(mktemp)

grep -v '^x ' $HOME/Dropbox/todo/todo.txt > $tmpfile

toread=$(tail -$count $tmpfile | awk 'ORS="," {print $1}' | sed s/,$//)
rm $tmpfile
calibredb export --dont-write-opf --dont-save-cover --template='{title}' $toread
