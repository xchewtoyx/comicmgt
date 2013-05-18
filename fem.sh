#!/bin/bash

ID=$1
TITLE=$2

fetch-ebook-metadata -t "$TITLE" -o opf | calibredb set_metadata $ID /dev/stdin
