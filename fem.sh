#!/bin/bash
# Copyright 2013 Russell Heilling

ID=$1
TITLE=$2

fetch-ebook-metadata -t "$TITLE" -o opf | calibredb set_metadata $ID /dev/stdin
