#!/bin/bash
# Copyright 2013 Russell Heilling
month=$1
titles=$(calibredb list -f pubdate | awk 'BEGIN {ORS=","} $2 ~ /^'$month'/ {print $1}' | sed s/,$//)
calibredb export --dont-write-opf --dont-save-cover --template='{title}' $titles 
